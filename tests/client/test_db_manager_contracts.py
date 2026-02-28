# -*- coding: utf-8 -*-
"""
Покрытие database/db_manager.py — CRUD договоров, CRM-карточек.
~40 тестов.

Тестируемые методы:
  Договоры: add_contract, get_all_contracts, get_contract_by_id,
            check_contract_number_exists, get_next_contract_number,
            update_contract, get_contract_years, get_contracts_count
  CRM:      get_crm_card_data, get_crm_card_id_by_contract,
            get_contract_id_by_crm_card, update_crm_card,
            update_crm_card_column, get_crm_cards_by_project_type,
            get_archived_crm_cards
"""

import pytest
import sys
import os
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from unittest.mock import patch, MagicMock
from datetime import datetime


# ============================================================================
# Глобальный флаг миграций нужно сбрасывать между тестами,
# иначе второй DatabaseManager не выполнит миграции и таблицы не создадутся.
# ============================================================================
@pytest.fixture(autouse=True)
def reset_migrations_flag():
    """Сбрасываем глобальный флаг _migrations_completed перед каждым тестом."""
    import database.db_manager as dm_module
    dm_module._migrations_completed = False
    yield
    dm_module._migrations_completed = False


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def db(tmp_path):
    """Создать DatabaseManager с временной SQLite БД.

    Порядок инициализации (как в tests/db/conftest.py):
    1. Создаём DatabaseManager БЕЗ миграций (_migrations_completed = True)
    2. initialize_database() — создаёт основные таблицы
    3. Запускаем все ALTER-миграции вручную (таблицы уже существуют)
    Мокаем YANDEX_DISK_TOKEN = '' чтобы не вызывать YandexDiskManager.
    """
    import database.db_manager as dm_module

    # Шаг 1: Подавляем миграции в конструкторе (таблиц ещё нет)
    dm_module._migrations_completed = True

    db_path = str(tmp_path / 'test.db')
    with patch('database.db_manager.YANDEX_DISK_TOKEN', ''):
        manager = dm_module.DatabaseManager(db_path=db_path)

        # Шаг 2: Создаём базовые таблицы
        manager.initialize_database()

        # Шаг 3: Запускаем все ALTER-миграции (таблицы уже существуют)
        # Gated-миграции (требуют database/migrations.py)
        for method_name in [
            'add_approval_deadline_field',
            'add_approval_stages_field',
            'create_approval_deadlines_table',
            'add_project_data_link_field',
        ]:
            try:
                getattr(manager, method_name)()
            except Exception:
                pass

        # Standalone-миграции
        manager.add_third_payment_field()
        manager.add_birth_date_column()
        manager.add_address_column()
        manager.add_secondary_position_column()
        manager.add_status_changed_date_column()
        manager.add_tech_task_fields()
        manager.add_survey_date_column()
        manager.create_supervision_table_migration()
        manager.fix_supervision_cards_column_name()
        manager.create_supervision_history_table()
        manager.create_manager_acceptance_table()
        manager.create_payments_system_tables()
        manager.add_reassigned_field_to_payments()
        manager.add_submitted_date_to_stage_executors()
        manager.add_stage_field_to_payments()
        manager.add_contract_file_columns()
        manager.create_project_files_table()
        manager.create_project_templates_table()
        manager.create_timeline_tables()
        manager.add_project_subtype_to_contracts()
        manager.add_floors_to_contracts()
        manager.create_stage_workflow_state_table()
        manager.create_messenger_tables()
        manager.create_performance_indexes()
        manager.add_missing_fields_rates_payments_salaries()

        manager.connect()

    yield manager

    dm_module._migrations_completed = False


@pytest.fixture
def db_with_client(db):
    """БД с одним клиентом — для создания договоров."""
    client_data = {
        'client_type': 'Физ. лицо',
        'full_name': 'Тестовый Клиент',
        'phone': '+79001234567',
        'email': 'test@test.ru',
    }
    client_id = db.add_client(client_data)
    return db, client_id


def _make_contract_data(client_id, **overrides):
    """Хелпер: минимальный набор полей для add_contract."""
    data = {
        'client_id': client_id,
        'project_type': 'Индивидуальный',
        'contract_number': '№001-2025',
        'contract_date': '2025-06-01',
        'address': 'ул. Тестовая, 1',
        'area': 120,
        'total_amount': 500000,
        'contract_period': 60,
        'status': 'Новый заказ',
    }
    data.update(overrides)
    return data


# ============================================================================
# ТЕСТЫ: add_contract + автоматическая CRM-карточка
# ============================================================================

class TestAddContract:
    """Создание договора и автоматическое создание CRM-карточки."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_add_contract_returns_id(self, db_with_client):
        """add_contract возвращает целочисленный ID."""
        db, client_id = db_with_client
        contract_id = db.add_contract(_make_contract_data(client_id))
        assert isinstance(contract_id, int)
        assert contract_id > 0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_add_contract_creates_crm_card(self, db_with_client):
        """При создании договора автоматически создаётся CRM-карточка."""
        db, client_id = db_with_client
        contract_id = db.add_contract(_make_contract_data(client_id))
        card_id = db.get_crm_card_id_by_contract(contract_id)
        assert card_id is not None

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_crm_card_default_column(self, db_with_client):
        """CRM-карточка создаётся в колонке 'Новый заказ'."""
        db, client_id = db_with_client
        contract_id = db.add_contract(_make_contract_data(client_id))
        card_id = db.get_crm_card_id_by_contract(contract_id)
        card = db.get_crm_card_data(card_id)
        assert card['column_name'] == 'Новый заказ'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_add_contract_saves_all_fields(self, db_with_client):
        """Проверяем, что все ключевые поля сохраняются в БД."""
        db, client_id = db_with_client
        data = _make_contract_data(
            client_id,
            address='пр. Ленина, 42',
            area=200,
            total_amount=1000000,
            city='Москва',
        )
        contract_id = db.add_contract(data)
        contract = db.get_contract_by_id(contract_id)
        assert contract['address'] == 'пр. Ленина, 42'
        assert contract['area'] == 200
        assert contract['total_amount'] == 1000000
        assert contract['city'] == 'Москва'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_add_contract_default_status(self, db_with_client):
        """Статус по умолчанию — 'Новый заказ'."""
        db, client_id = db_with_client
        data = _make_contract_data(client_id)
        data.pop('status', None)
        contract_id = db.add_contract(data)
        contract = db.get_contract_by_id(contract_id)
        assert contract['status'] == 'Новый заказ'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_add_multiple_contracts(self, db_with_client):
        """Создание нескольких договоров — у каждого своя CRM-карточка."""
        db, client_id = db_with_client
        id1 = db.add_contract(_make_contract_data(client_id, contract_number='№001-2025'))
        id2 = db.add_contract(_make_contract_data(client_id, contract_number='№002-2025'))
        assert id1 != id2
        card1 = db.get_crm_card_id_by_contract(id1)
        card2 = db.get_crm_card_id_by_contract(id2)
        assert card1 is not None
        assert card2 is not None
        assert card1 != card2

    @patch('database.db_manager.YANDEX_DISK_TOKEN', 'fake-token')
    @patch('database.db_manager.YandexDiskManager')
    def test_add_contract_with_yandex_disk_mock(self, mock_yd_cls, db_with_client):
        """Если YANDEX_DISK_TOKEN задан, YandexDiskManager вызывается, но не ломает создание."""
        mock_yd = MagicMock()
        mock_yd.build_contract_folder_path.return_value = '/test/path'
        mock_yd.create_contract_folder_structure.return_value = True
        mock_yd_cls.return_value = mock_yd

        db, client_id = db_with_client
        data = _make_contract_data(
            client_id,
            agent_type='FESTIVAL',
            address='ул. Тест, 1',
            area=100,
        )
        contract_id = db.add_contract(data)
        assert contract_id > 0
        # Проверяем, что путь сохранился
        contract = db.get_contract_by_id(contract_id)
        assert contract['yandex_folder_path'] == '/test/path'


# ============================================================================
# ТЕСТЫ: get_all_contracts
# ============================================================================

class TestGetAllContracts:
    """Получение списка договоров."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_empty_db_returns_empty_list(self, db):
        """Пустая БД — пустой список."""
        result = db.get_all_contracts()
        assert result == []

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_returns_all_contracts(self, db_with_client):
        """Возвращает все созданные договоры."""
        db, client_id = db_with_client
        db.add_contract(_make_contract_data(client_id, contract_number='№001-2025'))
        db.add_contract(_make_contract_data(client_id, contract_number='№002-2025'))
        result = db.get_all_contracts()
        assert len(result) == 2

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_pagination_skip(self, db_with_client):
        """Пагинация — skip пропускает записи."""
        db, client_id = db_with_client
        for i in range(5):
            db.add_contract(_make_contract_data(client_id, contract_number=f'№{i:03d}-2025'))
        result = db.get_all_contracts(skip=3)
        assert len(result) == 2

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_pagination_limit(self, db_with_client):
        """Пагинация — limit ограничивает количество."""
        db, client_id = db_with_client
        for i in range(5):
            db.add_contract(_make_contract_data(client_id, contract_number=f'№{i:03d}-2025'))
        result = db.get_all_contracts(limit=2)
        assert len(result) == 2

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_includes_client_name(self, db_with_client):
        """Результат содержит имя клиента через JOIN."""
        db, client_id = db_with_client
        db.add_contract(_make_contract_data(client_id))
        result = db.get_all_contracts()
        assert result[0]['full_name'] == 'Тестовый Клиент'


# ============================================================================
# ТЕСТЫ: get_contract_by_id
# ============================================================================

class TestGetContractById:
    """Получение договора по ID."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_existing_contract(self, db_with_client):
        """Существующий договор возвращается как dict."""
        db, client_id = db_with_client
        cid = db.add_contract(_make_contract_data(client_id))
        contract = db.get_contract_by_id(cid)
        assert contract is not None
        assert contract['id'] == cid

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_nonexistent_contract(self, db):
        """Несуществующий ID — возвращает None."""
        result = db.get_contract_by_id(99999)
        assert result is None


# ============================================================================
# ТЕСТЫ: check_contract_number_exists
# ============================================================================

class TestCheckContractNumberExists:
    """Проверка уникальности номера договора."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_number_does_not_exist(self, db):
        """В пустой БД номер не существует."""
        assert db.check_contract_number_exists('№001-2025') is False

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_number_exists(self, db_with_client):
        """После добавления договора номер существует."""
        db, client_id = db_with_client
        db.add_contract(_make_contract_data(client_id, contract_number='№001-2025'))
        assert db.check_contract_number_exists('№001-2025') is True

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_exclude_id(self, db_with_client):
        """exclude_id исключает договор из проверки (сценарий редактирования)."""
        db, client_id = db_with_client
        cid = db.add_contract(_make_contract_data(client_id, contract_number='№001-2025'))
        # С исключением своего ID — не существует (можно сохранить свой номер)
        assert db.check_contract_number_exists('№001-2025', exclude_id=cid) is False

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_exclude_id_other_contract(self, db_with_client):
        """exclude_id не помогает, если номер принадлежит другому договору."""
        db, client_id = db_with_client
        cid1 = db.add_contract(_make_contract_data(client_id, contract_number='№001-2025'))
        cid2 = db.add_contract(_make_contract_data(client_id, contract_number='№002-2025'))
        # Пытаемся установить номер первого на второй — конфликт
        assert db.check_contract_number_exists('№001-2025', exclude_id=cid2) is True


# ============================================================================
# ТЕСТЫ: get_next_contract_number
# ============================================================================

class TestGetNextContractNumber:
    """Автоинкремент номера договора."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_first_contract_of_year(self, db):
        """Для нового года первый номер = 1."""
        result = db.get_next_contract_number(2025)
        assert result == 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_increment_after_existing(self, db_with_client):
        """После создания №003-2025 следующий = 4."""
        db, client_id = db_with_client
        db.add_contract(_make_contract_data(client_id, contract_number='№003-2025'))
        result = db.get_next_contract_number(2025)
        assert result == 4

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_different_years_independent(self, db_with_client):
        """Номера для разных годов — независимы."""
        db, client_id = db_with_client
        db.add_contract(_make_contract_data(client_id, contract_number='№005-2025'))
        # Для 2026 года договоров нет — начинаем с 1
        result = db.get_next_contract_number(2026)
        assert result == 1


# ============================================================================
# ТЕСТЫ: update_contract
# ============================================================================

class TestUpdateContract:
    """Обновление договора."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_update_simple_fields(self, db_with_client):
        """Обновление адреса и площади."""
        db, client_id = db_with_client
        cid = db.add_contract(_make_contract_data(client_id))
        db.update_contract(cid, {'address': 'Новый адрес', 'area': 300})
        contract = db.get_contract_by_id(cid)
        assert contract['address'] == 'Новый адрес'
        assert contract['area'] == 300

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_update_status_sets_date(self, db_with_client):
        """При статусе СДАН автоматически устанавливается status_changed_date."""
        db, client_id = db_with_client
        cid = db.add_contract(_make_contract_data(client_id))
        db.update_contract(cid, {'status': 'СДАН'})
        contract = db.get_contract_by_id(cid)
        assert contract['status'] == 'СДАН'
        assert contract['status_changed_date'] is not None

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_update_status_supervision_creates_card(self, db_with_client):
        """Статус АВТОРСКИЙ НАДЗОР автоматически создаёт карточку надзора."""
        db, client_id = db_with_client
        cid = db.add_contract(_make_contract_data(client_id))
        db.update_contract(cid, {'status': 'АВТОРСКИЙ НАДЗОР'})
        # Проверяем, что карточка надзора была создана
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM supervision_cards WHERE contract_id = ?', (cid,))
        row = cursor.fetchone()
        db.close()
        assert row is not None


# ============================================================================
# ТЕСТЫ: get_contract_years
# ============================================================================

class TestGetContractYears:
    """Получение списка годов из договоров."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_empty_db_returns_current_and_next(self, db):
        """Даже без договоров — текущий и следующий год."""
        years = db.get_contract_years()
        current_year = datetime.now().year
        assert current_year in years
        assert current_year + 1 in years

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_includes_contract_year(self, db_with_client):
        """Год из даты договора включён в результат."""
        db, client_id = db_with_client
        db.add_contract(_make_contract_data(client_id, contract_date='2020-03-15'))
        years = db.get_contract_years()
        assert 2020 in years

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_sorted_descending(self, db_with_client):
        """Годы отсортированы от нового к старому."""
        db, client_id = db_with_client
        db.add_contract(_make_contract_data(client_id, contract_date='2018-01-01'))
        years = db.get_contract_years()
        assert years == sorted(years, reverse=True)


# ============================================================================
# ТЕСТЫ: get_contracts_count
# ============================================================================

class TestGetContractsCount:
    """Подсчёт договоров с фильтрами."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_empty_db(self, db):
        """Пустая БД — 0."""
        assert db.get_contracts_count() == 0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_count_all(self, db_with_client):
        """Подсчёт всех договоров."""
        db, client_id = db_with_client
        db.add_contract(_make_contract_data(client_id, contract_number='№001-2025'))
        db.add_contract(_make_contract_data(client_id, contract_number='№002-2025'))
        assert db.get_contracts_count() == 2

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_filter_by_status(self, db_with_client):
        """Фильтр по статусу."""
        db, client_id = db_with_client
        db.add_contract(_make_contract_data(client_id, contract_number='№001-2025', status='Новый заказ'))
        db.add_contract(_make_contract_data(client_id, contract_number='№002-2025', status='СДАН'))
        assert db.get_contracts_count(status='Новый заказ') == 1
        assert db.get_contracts_count(status='СДАН') == 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_filter_by_project_type(self, db_with_client):
        """Фильтр по типу проекта."""
        db, client_id = db_with_client
        db.add_contract(_make_contract_data(client_id, contract_number='№001-2025', project_type='Индивидуальный'))
        db.add_contract(_make_contract_data(client_id, contract_number='№002-2025', project_type='Шаблонный'))
        assert db.get_contracts_count(project_type='Индивидуальный') == 1
        assert db.get_contracts_count(project_type='Шаблонный') == 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_filter_by_year(self, db_with_client):
        """Фильтр по году даты договора."""
        db, client_id = db_with_client
        db.add_contract(_make_contract_data(client_id, contract_number='№001-2025', contract_date='2025-03-01'))
        db.add_contract(_make_contract_data(client_id, contract_number='№002-2024', contract_date='2024-11-15'))
        assert db.get_contracts_count(year=2025) == 1
        assert db.get_contracts_count(year=2024) == 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_combined_filters(self, db_with_client):
        """Комбинация фильтров: статус + тип проекта."""
        db, client_id = db_with_client
        db.add_contract(_make_contract_data(
            client_id, contract_number='№001-2025',
            status='Новый заказ', project_type='Индивидуальный',
        ))
        db.add_contract(_make_contract_data(
            client_id, contract_number='№002-2025',
            status='СДАН', project_type='Индивидуальный',
        ))
        db.add_contract(_make_contract_data(
            client_id, contract_number='№003-2025',
            status='Новый заказ', project_type='Шаблонный',
        ))
        # Только «Новый заказ» + «Индивидуальный»
        assert db.get_contracts_count(status='Новый заказ', project_type='Индивидуальный') == 1


# ============================================================================
# ТЕСТЫ: CRM-карточки — get / update
# ============================================================================

class TestCrmCardData:
    """Чтение и связь CRM-карточек с договорами."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_crm_card_data(self, db_with_client):
        """get_crm_card_data возвращает dict с полями карточки."""
        db, client_id = db_with_client
        cid = db.add_contract(_make_contract_data(client_id))
        card_id = db.get_crm_card_id_by_contract(cid)
        card = db.get_crm_card_data(card_id)
        assert card is not None
        assert card['contract_id'] == cid
        assert 'column_name' in card

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_crm_card_data_nonexistent(self, db):
        """Несуществующий card_id — None."""
        result = db.get_crm_card_data(99999)
        assert result is None

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_crm_card_id_by_contract(self, db_with_client):
        """Обратная связь: contract → card."""
        db, client_id = db_with_client
        cid = db.add_contract(_make_contract_data(client_id))
        card_id = db.get_crm_card_id_by_contract(cid)
        assert card_id is not None
        assert isinstance(card_id, int)

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_crm_card_id_nonexistent(self, db):
        """Несуществующий contract_id — None."""
        result = db.get_crm_card_id_by_contract(99999)
        assert result is None

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_contract_id_by_crm_card(self, db_with_client):
        """Обратная связь: card → contract."""
        db, client_id = db_with_client
        cid = db.add_contract(_make_contract_data(client_id))
        card_id = db.get_crm_card_id_by_contract(cid)
        result = db.get_contract_id_by_crm_card(card_id)
        assert result == cid

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_contract_id_by_crm_card_nonexistent(self, db):
        """Несуществующий crm_card_id — None."""
        result = db.get_contract_id_by_crm_card(99999)
        assert result is None


# ============================================================================
# ТЕСТЫ: update_crm_card
# ============================================================================

class TestUpdateCrmCard:
    """Обновление полей CRM-карточки."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_update_tags(self, db_with_client):
        """Обновление тегов карточки."""
        db, client_id = db_with_client
        cid = db.add_contract(_make_contract_data(client_id))
        card_id = db.get_crm_card_id_by_contract(cid)
        db.update_crm_card(card_id, {'tags': 'срочно,vip'})
        card = db.get_crm_card_data(card_id)
        assert card['tags'] == 'срочно,vip'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_update_deadline(self, db_with_client):
        """Обновление дедлайна карточки."""
        db, client_id = db_with_client
        cid = db.add_contract(_make_contract_data(client_id))
        card_id = db.get_crm_card_id_by_contract(cid)
        db.update_crm_card(card_id, {'deadline': '2025-12-31'})
        card = db.get_crm_card_data(card_id)
        assert card['deadline'] == '2025-12-31'


# ============================================================================
# ТЕСТЫ: update_crm_card_column — перемещение между колонками
# ============================================================================

class TestUpdateCrmCardColumn:
    """Перемещение карточки между колонками CRM-доски."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_move_to_another_column(self, db_with_client):
        """Перемещение из 'Новый заказ' в 'Замер'."""
        db, client_id = db_with_client
        cid = db.add_contract(_make_contract_data(client_id))
        card_id = db.get_crm_card_id_by_contract(cid)
        db.update_crm_card_column(card_id, 'Замер')
        card = db.get_crm_card_data(card_id)
        assert card['column_name'] == 'Замер'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_move_to_waiting_saves_previous(self, db_with_client):
        """При переходе в 'В ожидании' сохраняется previous_column."""
        db, client_id = db_with_client
        cid = db.add_contract(_make_contract_data(client_id))
        card_id = db.get_crm_card_id_by_contract(cid)
        # Сначала переходим в 'Замер'
        db.update_crm_card_column(card_id, 'Замер')
        # Затем в 'В ожидании' — предыдущая колонка должна сохраниться
        db.update_crm_card_column(card_id, 'В ожидании')
        card = db.get_crm_card_data(card_id)
        assert card['column_name'] == 'В ожидании'
        assert card['previous_column'] == 'Замер'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_return_from_waiting_clears_previous(self, db_with_client):
        """При возврате из 'В ожидании' очищается previous_column."""
        db, client_id = db_with_client
        cid = db.add_contract(_make_contract_data(client_id))
        card_id = db.get_crm_card_id_by_contract(cid)
        db.update_crm_card_column(card_id, 'Замер')
        db.update_crm_card_column(card_id, 'В ожидании')
        db.update_crm_card_column(card_id, 'Концепция')
        card = db.get_crm_card_data(card_id)
        assert card['column_name'] == 'Концепция'
        assert card['previous_column'] is None


# ============================================================================
# ТЕСТЫ: get_crm_cards_by_project_type
# ============================================================================

class TestGetCrmCardsByProjectType:
    """Получение активных CRM-карточек по типу проекта."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_returns_active_cards(self, db_with_client):
        """Возвращает карточки активных договоров."""
        db, client_id = db_with_client
        db.add_contract(_make_contract_data(client_id, project_type='Индивидуальный'))
        cards = db.get_crm_cards_by_project_type('Индивидуальный')
        assert len(cards) == 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_excludes_archived(self, db_with_client):
        """Не включает СДАН / РАСТОРГНУТ."""
        db, client_id = db_with_client
        cid = db.add_contract(_make_contract_data(
            client_id, contract_number='№001-2025',
            project_type='Индивидуальный',
        ))
        db.update_contract(cid, {'status': 'СДАН'})
        cards = db.get_crm_cards_by_project_type('Индивидуальный')
        assert len(cards) == 0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_filters_by_project_type(self, db_with_client):
        """Фильтрует по типу проекта."""
        db, client_id = db_with_client
        db.add_contract(_make_contract_data(
            client_id, contract_number='№001-2025',
            project_type='Индивидуальный',
        ))
        db.add_contract(_make_contract_data(
            client_id, contract_number='№002-2025',
            project_type='Шаблонный',
        ))
        cards_ind = db.get_crm_cards_by_project_type('Индивидуальный')
        cards_tpl = db.get_crm_cards_by_project_type('Шаблонный')
        assert len(cards_ind) == 1
        assert len(cards_tpl) == 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_empty_result(self, db):
        """Нет договоров — пустой список."""
        cards = db.get_crm_cards_by_project_type('Индивидуальный')
        assert cards == []


# ============================================================================
# ТЕСТЫ: get_archived_crm_cards
# ============================================================================

class TestGetArchivedCrmCards:
    """Получение архивных CRM-карточек."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_no_archived(self, db_with_client):
        """Без архивных — пустой список."""
        db, client_id = db_with_client
        db.add_contract(_make_contract_data(client_id, project_type='Индивидуальный'))
        archived = db.get_archived_crm_cards('Индивидуальный')
        assert archived == []

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_returns_archived_cards(self, db_with_client):
        """СДАН попадает в архив."""
        db, client_id = db_with_client
        cid = db.add_contract(_make_contract_data(
            client_id, contract_number='№001-2025',
            project_type='Индивидуальный',
        ))
        db.update_contract(cid, {'status': 'СДАН'})
        archived = db.get_archived_crm_cards('Индивидуальный')
        assert len(archived) == 1
        assert archived[0]['status'] == 'СДАН'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_terminated_in_archive(self, db_with_client):
        """РАСТОРГНУТ тоже попадает в архив."""
        db, client_id = db_with_client
        cid = db.add_contract(_make_contract_data(
            client_id, contract_number='№001-2025',
            project_type='Индивидуальный',
        ))
        db.update_contract(cid, {'status': 'РАСТОРГНУТ'})
        archived = db.get_archived_crm_cards('Индивидуальный')
        assert len(archived) == 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_archive_filters_by_project_type(self, db_with_client):
        """Архив фильтруется по типу проекта."""
        db, client_id = db_with_client
        cid1 = db.add_contract(_make_contract_data(
            client_id, contract_number='№001-2025',
            project_type='Индивидуальный',
        ))
        cid2 = db.add_contract(_make_contract_data(
            client_id, contract_number='№002-2025',
            project_type='Шаблонный',
        ))
        db.update_contract(cid1, {'status': 'СДАН'})
        db.update_contract(cid2, {'status': 'СДАН'})
        archived_ind = db.get_archived_crm_cards('Индивидуальный')
        archived_tpl = db.get_archived_crm_cards('Шаблонный')
        assert len(archived_ind) == 1
        assert len(archived_tpl) == 1


# ============================================================================
# ТЕСТЫ: полный lifecycle
# ============================================================================

class TestFullLifecycle:
    """Полный цикл: create → update → archive."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_contract_lifecycle(self, db_with_client):
        """Договор: создание → CRM-карточка → перемещение → СДАН → архив."""
        db, client_id = db_with_client

        # 1. Создание
        cid = db.add_contract(_make_contract_data(
            client_id, contract_number='№010-2025',
            project_type='Индивидуальный',
        ))
        assert cid > 0

        # 2. CRM-карточка автоматически создана
        card_id = db.get_crm_card_id_by_contract(cid)
        assert card_id is not None

        # 3. Перемещение по колонкам
        db.update_crm_card_column(card_id, 'Замер')
        db.update_crm_card_column(card_id, 'Концепция')
        card = db.get_crm_card_data(card_id)
        assert card['column_name'] == 'Концепция'

        # 4. Обновление договора — адрес
        db.update_contract(cid, {'address': 'Обновлённый адрес'})
        contract = db.get_contract_by_id(cid)
        assert contract['address'] == 'Обновлённый адрес'

        # 5. Архивация — СДАН
        db.update_contract(cid, {'status': 'СДАН'})
        # Больше не в активных
        active = db.get_crm_cards_by_project_type('Индивидуальный')
        assert len(active) == 0
        # Теперь в архиве
        archived = db.get_archived_crm_cards('Индивидуальный')
        assert len(archived) == 1
        assert archived[0]['contract_number'] == '№010-2025'
