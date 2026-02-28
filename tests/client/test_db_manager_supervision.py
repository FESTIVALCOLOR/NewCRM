# -*- coding: utf-8 -*-
"""
Покрытие database/db_manager.py — надзор, стадии, timeline, поиск, статистика, агенты, города.
~60 тестов. Реальная SQLite через tmp_path, без моков.

Тестируемые методы:
  Надзор:     create_supervision_card, get_supervision_cards_active,
              get_supervision_cards_archived, update_supervision_card,
              update_supervision_card_column, pause_supervision_card,
              resume_supervision_card, add_supervision_history,
              get_supervision_history
  Стадии:     assign_stage_executor, complete_stage_for_executor,
              get_stage_history
  Timeline:   init_project_timeline, get_project_timeline,
              update_timeline_entry
  Поиск:      global_search
  Статистика: get_dashboard_statistics, get_general_statistics
  Агенты:     get_all_agents, add_agent, delete_agent
  Города:     get_all_cities, add_city, delete_city
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from unittest.mock import patch
from datetime import datetime


# ============================================================================
# Глобальный флаг миграций — сбрасываем между тестами
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

    Порядок: подавить миграции в конструкторе → initialize_database →
    запустить все ALTER-миграции вручную.
    """
    import database.db_manager as dm_module

    # Подавляем миграции в конструкторе (таблиц ещё нет)
    dm_module._migrations_completed = True

    db_path = str(tmp_path / 'test.db')
    with patch('database.db_manager.YANDEX_DISK_TOKEN', ''):
        manager = dm_module.DatabaseManager(db_path=db_path)

        # Создаём базовые таблицы
        manager.initialize_database()

        # Запускаем все ALTER-миграции (таблицы уже существуют)
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

        manager.add_third_payment_field()
        manager.add_birth_date_column()
        manager.add_address_column()
        manager.add_secondary_position_column()
        manager.add_status_changed_date_column()
        manager.add_tech_task_fields()
        manager.add_survey_date_column()
        manager.create_supervision_table_migration()
        # Повторный вызов — добавляет ALTER для previous_column и других полей
        # (первый вызов создаёт таблицу, второй добавляет колонки через ALTER)
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
        manager.add_agents_status_field()
        manager.migrate_add_cities_table()

        manager.connect()

    yield manager

    dm_module._migrations_completed = False


@pytest.fixture
def db_with_contract(db):
    """БД с клиентом и договором — базовое предусловие для надзора и CRM."""
    client_data = {
        'client_type': 'Физ. лицо',
        'full_name': 'Тестовый Клиент',
        'phone': '+79001234567',
        'email': 'test@test.ru',
    }
    client_id = db.add_client(client_data)

    with patch('database.db_manager.YANDEX_DISK_TOKEN', ''):
        contract_id = db.add_contract({
            'client_id': client_id,
            'project_type': 'Индивидуальный',
            'contract_number': '№001-2026',
            'contract_date': '2026-01-15',
            'address': 'ул. Тестовая, 1',
            'area': 120,
            'total_amount': 500000,
            'contract_period': 60,
            'status': 'АВТОРСКИЙ НАДЗОР',
            'city': 'СПБ',
            'agent_type': 'ПЕТРОВИЧ',
        })

    return db, client_id, contract_id


@pytest.fixture
def db_with_supervision(db_with_contract):
    """БД с клиентом, договором и карточкой надзора."""
    db, client_id, contract_id = db_with_contract
    card_id = db.create_supervision_card(contract_id)
    return db, client_id, contract_id, card_id


@pytest.fixture
def db_with_crm_card(db_with_contract):
    """БД с клиентом, договором и CRM-карточкой (для стадий)."""
    db, client_id, contract_id = db_with_contract
    crm_card_id = db.get_crm_card_id_by_contract(contract_id)
    return db, client_id, contract_id, crm_card_id


@pytest.fixture
def db_with_employee(db):
    """БД с одним сотрудником."""
    emp_data = {
        'full_name': 'Петров Пётр',
        'login': 'petrov',
        'password': 'test123',
        'position': 'Дизайнер',
    }
    emp_id = db.add_employee(emp_data)
    return db, emp_id


# ============================================================================
# Хелперы
# ============================================================================

def _make_employee(db, name='Тестовый Сотрудник', login=None, position='Дизайнер'):
    """Быстрое создание сотрудника."""
    login = login or name.lower().replace(' ', '_')
    return db.add_employee({
        'full_name': name,
        'login': login,
        'password': 'test123',
        'position': position,
    })


# ============================================================================
# ТЕСТЫ: Надзор (supervision)
# ============================================================================

class TestCreateSupervisionCard:
    """Создание карточки авторского надзора."""

    def test_create_returns_id(self, db_with_contract):
        """create_supervision_card возвращает целочисленный ID."""
        db, _, contract_id = db_with_contract
        card_id = db.create_supervision_card(contract_id)
        assert isinstance(card_id, int)
        assert card_id > 0

    def test_create_duplicate_returns_existing_id(self, db_with_supervision):
        """Повторный вызов для того же договора возвращает существующий ID."""
        db, _, contract_id, card_id = db_with_supervision
        card_id2 = db.create_supervision_card(contract_id)
        assert card_id2 == card_id

    def test_create_sets_default_column(self, db_with_supervision):
        """Карточка создаётся в колонке 'Новый заказ'."""
        db, _, _, card_id = db_with_supervision
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT column_name FROM supervision_cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        db.close()
        assert row['column_name'] == 'Новый заказ'

    def test_create_for_nonexistent_contract(self, db):
        """Создание для несуществующего договора — не падает, возвращает ID (или None)."""
        # Пустая БД — contract_id=9999 не существует
        result = db.create_supervision_card(9999)
        # Метод не проверяет FK, поэтому может вернуть ID
        assert result is not None


class TestGetSupervisionCards:
    """Получение карточек надзора: активные и архивные."""

    def test_active_cards_returns_list(self, db_with_supervision):
        """get_supervision_cards_active возвращает список с карточкой."""
        db, _, _, _ = db_with_supervision
        cards = db.get_supervision_cards_active()
        assert isinstance(cards, list)
        assert len(cards) >= 1

    def test_active_cards_contain_contract_number(self, db_with_supervision):
        """Активные карточки содержат номер договора из JOIN."""
        db, _, _, _ = db_with_supervision
        cards = db.get_supervision_cards_active()
        assert cards[0]['contract_number'] == '№001-2026'

    def test_active_cards_contain_address(self, db_with_supervision):
        """Активные карточки содержат адрес из JOIN."""
        db, _, _, _ = db_with_supervision
        cards = db.get_supervision_cards_active()
        assert cards[0]['address'] == 'ул. Тестовая, 1'

    def test_archived_cards_empty_initially(self, db_with_supervision):
        """Архивных карточек нет пока статус = 'АВТОРСКИЙ НАДЗОР'."""
        db, _, _, _ = db_with_supervision
        archived = db.get_supervision_cards_archived()
        assert isinstance(archived, list)
        assert len(archived) == 0

    def test_archived_cards_after_status_change(self, db_with_supervision):
        """После смены статуса на 'СДАН' карточка попадает в архив."""
        db, _, contract_id, _ = db_with_supervision
        # Меняем статус договора на 'СДАН'
        conn = db.connect()
        conn.execute('UPDATE contracts SET status = ? WHERE id = ?', ('СДАН', contract_id))
        conn.commit()
        db.close()

        archived = db.get_supervision_cards_archived()
        assert len(archived) >= 1
        assert archived[0]['status'] == 'СДАН'

    def test_active_disappears_after_archive(self, db_with_supervision):
        """После смены статуса на 'СДАН' карточка пропадает из активных."""
        db, _, contract_id, _ = db_with_supervision
        conn = db.connect()
        conn.execute('UPDATE contracts SET status = ? WHERE id = ?', ('СДАН', contract_id))
        conn.commit()
        db.close()

        active = db.get_supervision_cards_active()
        assert len(active) == 0


class TestUpdateSupervisionCard:
    """Обновление полей карточки надзора."""

    def test_update_deadline(self, db_with_supervision):
        """update_supervision_card обновляет deadline."""
        db, _, _, card_id = db_with_supervision
        db.update_supervision_card(card_id, {'deadline': '2026-12-31'})

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT deadline FROM supervision_cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        db.close()
        assert row['deadline'] == '2026-12-31'

    def test_update_sets_updated_at(self, db_with_supervision):
        """update_supervision_card обновляет поле updated_at."""
        db, _, _, card_id = db_with_supervision
        db.update_supervision_card(card_id, {'tags': 'срочный'})

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT updated_at FROM supervision_cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        db.close()
        assert row['updated_at'] is not None

    def test_update_dan_id(self, db_with_supervision):
        """Установка dan_id через update."""
        db, _, _, card_id = db_with_supervision
        emp_id = _make_employee(db, 'ДАН Тест', 'dan_test', 'ДАН')
        db.update_supervision_card(card_id, {'dan_id': emp_id})

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT dan_id FROM supervision_cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        db.close()
        assert row['dan_id'] == emp_id


class TestUpdateSupervisionCardColumn:
    """Обновление колонки карточки надзора с логикой previous_column."""

    def test_move_to_stage(self, db_with_supervision):
        """Перемещение в стадию обновляет column_name."""
        db, _, _, card_id = db_with_supervision
        db.update_supervision_card_column(card_id, 'Стадия 1: Закупка керамогранита')

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT column_name FROM supervision_cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        db.close()
        assert row['column_name'] == 'Стадия 1: Закупка керамогранита'

    def test_pause_saves_previous_column(self, db_with_supervision):
        """При переходе 'В ожидании' сохраняется previous_column."""
        db, _, _, card_id = db_with_supervision
        # Сначала двигаем в стадию
        db.update_supervision_card_column(card_id, 'Стадия 2: Закупка сантехники')
        # Потом ставим на ожидание
        db.update_supervision_card_column(card_id, 'В ожидании')

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT column_name, previous_column FROM supervision_cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        db.close()
        assert row['column_name'] == 'В ожидании'
        assert row['previous_column'] == 'Стадия 2: Закупка сантехники'

    def test_resume_clears_previous_column(self, db_with_supervision):
        """При выходе из 'В ожидании' previous_column очищается."""
        db, _, _, card_id = db_with_supervision
        db.update_supervision_card_column(card_id, 'Стадия 3: Закупка оборудования')
        db.update_supervision_card_column(card_id, 'В ожидании')
        db.update_supervision_card_column(card_id, 'Стадия 4: Закупка дверей и окон')

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT column_name, previous_column FROM supervision_cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        db.close()
        assert row['column_name'] == 'Стадия 4: Закупка дверей и окон'
        assert row['previous_column'] is None

    def test_regular_move_no_previous(self, db_with_supervision):
        """Обычное перемещение (не в ожидание) не трогает previous_column."""
        db, _, _, card_id = db_with_supervision
        db.update_supervision_card_column(card_id, 'Стадия 1: Закупка керамогранита')
        db.update_supervision_card_column(card_id, 'Стадия 2: Закупка сантехники')

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT previous_column FROM supervision_cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        db.close()
        # previous_column не устанавливается при обычном перемещении
        assert row['previous_column'] is None


class TestPauseResumeSupervision:
    """Приостановка и возобновление карточки надзора."""

    def test_pause_sets_is_paused(self, db_with_supervision):
        """pause_supervision_card устанавливает is_paused = 1."""
        db, _, _, card_id = db_with_supervision
        emp_id = _make_employee(db, 'Менеджер Паузы', 'mgr_pause', 'Старший менеджер проектов')
        db.pause_supervision_card(card_id, 'Ждём поставку', emp_id)

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT is_paused, pause_reason FROM supervision_cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        db.close()
        assert row['is_paused'] == 1
        assert row['pause_reason'] == 'Ждём поставку'

    def test_pause_creates_history_entry(self, db_with_supervision):
        """pause_supervision_card добавляет запись в историю."""
        db, _, _, card_id = db_with_supervision
        emp_id = _make_employee(db, 'Менеджер Истории', 'mgr_hist', 'Старший менеджер проектов')
        db.pause_supervision_card(card_id, 'Причина паузы', emp_id)

        history = db.get_supervision_history(card_id)
        assert len(history) >= 1
        assert history[0]['entry_type'] == 'pause'
        assert 'Причина: Причина паузы' in history[0]['message']

    def test_resume_clears_is_paused(self, db_with_supervision):
        """resume_supervision_card устанавливает is_paused = 0."""
        db, _, _, card_id = db_with_supervision
        emp_id = _make_employee(db, 'Менеджер Резюме', 'mgr_resume', 'Старший менеджер проектов')
        db.pause_supervision_card(card_id, 'Пауза', emp_id)
        db.resume_supervision_card(card_id, emp_id)

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT is_paused FROM supervision_cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        db.close()
        assert row['is_paused'] == 0

    def test_resume_keeps_pause_reason(self, db_with_supervision):
        """После resume pause_reason остаётся для истории."""
        db, _, _, card_id = db_with_supervision
        emp_id = _make_employee(db, 'Менеджер КП', 'mgr_kp', 'Старший менеджер проектов')
        db.pause_supervision_card(card_id, 'Историческая причина', emp_id)
        db.resume_supervision_card(card_id, emp_id)

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT pause_reason FROM supervision_cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        db.close()
        # pause_reason НЕ сбрасывается при resume — остаётся в истории
        assert row['pause_reason'] == 'Историческая причина'

    def test_resume_creates_history_entry(self, db_with_supervision):
        """resume_supervision_card добавляет запись в историю."""
        db, _, _, card_id = db_with_supervision
        emp_id = _make_employee(db, 'Менеджер РИ', 'mgr_ri', 'Старший менеджер проектов')
        db.pause_supervision_card(card_id, 'Пауза', emp_id)
        db.resume_supervision_card(card_id, emp_id)

        history = db.get_supervision_history(card_id)
        types = [h['entry_type'] for h in history]
        assert 'resume' in types


class TestSupervisionHistory:
    """История проекта надзора."""

    def test_add_history_and_get(self, db_with_supervision):
        """Добавление записи и получение истории."""
        db, _, _, card_id = db_with_supervision
        emp_id = _make_employee(db, 'Историк', 'historian', 'Менеджер')
        db.add_supervision_history(card_id, 'note', 'Заметка о проекте', emp_id)

        history = db.get_supervision_history(card_id)
        assert len(history) == 1
        assert history[0]['entry_type'] == 'note'
        assert history[0]['message'] == 'Заметка о проекте'

    def test_history_ordered_desc(self, db_with_supervision):
        """История отсортирована по дате DESC (новые сверху)."""
        db, _, _, card_id = db_with_supervision
        emp_id = _make_employee(db, 'Хронолог', 'chronolog', 'Менеджер')
        # Вставляем с разными created_at для предсказуемой сортировки
        conn = db.connect()
        conn.execute(
            "INSERT INTO supervision_project_history (supervision_card_id, entry_type, message, created_by, created_at) VALUES (?, ?, ?, ?, '2026-01-01 10:00:00')",
            (card_id, 'first', 'Первая', emp_id)
        )
        conn.execute(
            "INSERT INTO supervision_project_history (supervision_card_id, entry_type, message, created_by, created_at) VALUES (?, ?, ?, ?, '2026-02-01 10:00:00')",
            (card_id, 'second', 'Вторая', emp_id)
        )
        conn.commit()
        db.close()

        history = db.get_supervision_history(card_id)
        assert len(history) == 2
        # ORDER BY created_at DESC — новая (февраль) сверху
        assert history[0]['message'] == 'Вторая'
        assert history[1]['message'] == 'Первая'

    def test_history_includes_employee_name(self, db_with_supervision):
        """История содержит имя сотрудника через JOIN."""
        db, _, _, card_id = db_with_supervision
        emp_id = _make_employee(db, 'Сотрудник ФИО', 'fio_test', 'Менеджер')
        db.add_supervision_history(card_id, 'info', 'Тест', emp_id)

        history = db.get_supervision_history(card_id)
        assert history[0]['created_by_name'] == 'Сотрудник ФИО'

    def test_empty_history(self, db_with_supervision):
        """Пустая история возвращает пустой список."""
        db, _, _, card_id = db_with_supervision
        history = db.get_supervision_history(card_id)
        assert history == []


# ============================================================================
# ТЕСТЫ: Стадии (stage_executors)
# ============================================================================

class TestAssignStageExecutor:
    """Назначение исполнителя на стадию."""

    def test_assign_executor(self, db_with_crm_card):
        """assign_stage_executor создаёт запись в stage_executors."""
        db, _, _, crm_card_id = db_with_crm_card
        executor_id = _make_employee(db, 'Дизайнер А', 'designer_a', 'Дизайнер')
        manager_id = _make_employee(db, 'СМП А', 'smp_a', 'Старший менеджер проектов')

        db.assign_stage_executor(crm_card_id, 'Дизайн концепция', executor_id, manager_id, '2026-03-01')

        # Проверяем через get_stage_history
        history = db.get_stage_history(crm_card_id)
        assert len(history) == 1
        assert history[0]['stage_name'] == 'Дизайн концепция'
        assert history[0]['executor_name'] == 'Дизайнер А'

    def test_assign_multiple_executors(self, db_with_crm_card):
        """Назначение нескольких исполнителей на разные стадии."""
        db, _, _, crm_card_id = db_with_crm_card
        exec1 = _make_employee(db, 'Дизайнер Б', 'designer_b', 'Дизайнер')
        exec2 = _make_employee(db, 'Чертёжник А', 'draftsman_a', 'Чертёжник')
        mgr = _make_employee(db, 'СМП Б', 'smp_b', 'Старший менеджер проектов')

        db.assign_stage_executor(crm_card_id, 'Дизайн концепция', exec1, mgr, '2026-03-01')
        db.assign_stage_executor(crm_card_id, 'Рабочие чертежи', exec2, mgr, '2026-04-01')

        history = db.get_stage_history(crm_card_id)
        assert len(history) == 2
        stages = [h['stage_name'] for h in history]
        assert 'Дизайн концепция' in stages
        assert 'Рабочие чертежи' in stages


class TestCompleteStage:
    """Завершение стадии исполнителем."""

    def test_complete_stage_marks_completed(self, db_with_crm_card):
        """complete_stage_for_executor устанавливает completed = 1."""
        db, _, _, crm_card_id = db_with_crm_card
        exec_id = _make_employee(db, 'Дизайнер В', 'designer_v', 'Дизайнер')
        mgr_id = _make_employee(db, 'СМП В', 'smp_v', 'Старший менеджер проектов')

        db.assign_stage_executor(crm_card_id, 'Дизайн концепция', exec_id, mgr_id, '2026-03-01')
        db.complete_stage_for_executor(crm_card_id, 'Дизайн концепция', exec_id)

        history = db.get_stage_history(crm_card_id)
        assert history[0]['completed'] == 1

    def test_complete_stage_sets_completed_date(self, db_with_crm_card):
        """complete_stage_for_executor устанавливает completed_date."""
        db, _, _, crm_card_id = db_with_crm_card
        exec_id = _make_employee(db, 'Дизайнер Г', 'designer_g', 'Дизайнер')
        mgr_id = _make_employee(db, 'СМП Г', 'smp_g', 'Старший менеджер проектов')

        db.assign_stage_executor(crm_card_id, 'Рабочие чертежи', exec_id, mgr_id, '2026-04-01')
        db.complete_stage_for_executor(crm_card_id, 'Рабочие чертежи', exec_id)

        history = db.get_stage_history(crm_card_id)
        assert history[0]['completed_date'] is not None

    def test_complete_nonexistent_stage(self, db_with_crm_card):
        """Завершение несуществующей стадии — не падает."""
        db, _, _, crm_card_id = db_with_crm_card
        # Нет назначения — вызов не должен бросить исключение
        db.complete_stage_for_executor(crm_card_id, 'Несуществующая', 999)


class TestGetStageHistory:
    """Получение истории стадий проекта."""

    def test_empty_history(self, db_with_crm_card):
        """Пустая история возвращает пустой список."""
        db, _, _, crm_card_id = db_with_crm_card
        history = db.get_stage_history(crm_card_id)
        assert history == []

    def test_history_ordered_by_date(self, db_with_crm_card):
        """История отсортирована по assigned_date ASC."""
        db, _, _, crm_card_id = db_with_crm_card
        exec1 = _make_employee(db, 'Первый', 'first_exec', 'Дизайнер')
        exec2 = _make_employee(db, 'Второй', 'second_exec', 'Чертёжник')
        mgr = _make_employee(db, 'МГР', 'mgr_order', 'Старший менеджер проектов')

        db.assign_stage_executor(crm_card_id, 'Стадия А', exec1, mgr, '2026-02-01')
        db.assign_stage_executor(crm_card_id, 'Стадия Б', exec2, mgr, '2026-03-01')

        history = db.get_stage_history(crm_card_id)
        assert len(history) == 2
        assert history[0]['stage_name'] == 'Стадия А'
        assert history[1]['stage_name'] == 'Стадия Б'


# ============================================================================
# ТЕСТЫ: Timeline
# ============================================================================

class TestProjectTimeline:
    """Таблица сроков проекта: init, get, update."""

    def _sample_entries(self):
        """Примеры записей timeline."""
        return [
            {
                'stage_code': 'SURVEY',
                'stage_name': 'Замер',
                'stage_group': 'Подготовка',
                'substage_group': '',
                'executor_role': 'Замерщик',
                'is_in_contract_scope': True,
                'sort_order': 1,
                'raw_norm_days': 3,
                'cumulative_days': 3,
                'norm_days': 3,
            },
            {
                'stage_code': 'CONCEPT',
                'stage_name': 'Дизайн концепция',
                'stage_group': 'Проектирование',
                'substage_group': 'Основное',
                'executor_role': 'Дизайнер',
                'is_in_contract_scope': True,
                'sort_order': 2,
                'raw_norm_days': 14,
                'cumulative_days': 17,
                'norm_days': 14,
            },
            {
                'stage_code': 'DRAWINGS',
                'stage_name': 'Рабочие чертежи',
                'stage_group': 'Проектирование',
                'substage_group': 'Основное',
                'executor_role': 'Чертёжник',
                'is_in_contract_scope': True,
                'sort_order': 3,
                'raw_norm_days': 10,
                'cumulative_days': 27,
                'norm_days': 10,
            },
        ]

    def test_init_timeline(self, db_with_contract):
        """init_project_timeline создаёт записи."""
        db, _, contract_id = db_with_contract
        result = db.init_project_timeline(contract_id, self._sample_entries())
        assert result is True

    def test_get_timeline(self, db_with_contract):
        """get_project_timeline возвращает вставленные записи."""
        db, _, contract_id = db_with_contract
        db.init_project_timeline(contract_id, self._sample_entries())
        timeline = db.get_project_timeline(contract_id)
        assert len(timeline) == 3

    def test_timeline_ordered_by_sort_order(self, db_with_contract):
        """Записи timeline отсортированы по sort_order."""
        db, _, contract_id = db_with_contract
        db.init_project_timeline(contract_id, self._sample_entries())
        timeline = db.get_project_timeline(contract_id)
        assert timeline[0]['stage_code'] == 'SURVEY'
        assert timeline[1]['stage_code'] == 'CONCEPT'
        assert timeline[2]['stage_code'] == 'DRAWINGS'

    def test_timeline_fields_saved(self, db_with_contract):
        """Все поля сохраняются корректно."""
        db, _, contract_id = db_with_contract
        db.init_project_timeline(contract_id, self._sample_entries())
        timeline = db.get_project_timeline(contract_id)

        survey = timeline[0]
        assert survey['stage_name'] == 'Замер'
        assert survey['stage_group'] == 'Подготовка'
        assert survey['executor_role'] == 'Замерщик'
        assert survey['norm_days'] == 3

    def test_init_timeline_idempotent(self, db_with_contract):
        """Повторный init не дублирует записи (INSERT OR IGNORE)."""
        db, _, contract_id = db_with_contract
        db.init_project_timeline(contract_id, self._sample_entries())
        db.init_project_timeline(contract_id, self._sample_entries())
        timeline = db.get_project_timeline(contract_id)
        assert len(timeline) == 3

    def test_update_timeline_entry(self, db_with_contract):
        """update_timeline_entry обновляет поля записи."""
        db, _, contract_id = db_with_contract
        db.init_project_timeline(contract_id, self._sample_entries())

        result = db.update_timeline_entry(contract_id, 'SURVEY', {
            'actual_date': '2026-02-01',
            'actual_days': 2,
            'status': 'Выполнено',
        })
        assert result is True

        timeline = db.get_project_timeline(contract_id)
        survey = timeline[0]
        assert survey['actual_date'] == '2026-02-01'
        assert survey['actual_days'] == 2
        assert survey['status'] == 'Выполнено'

    def test_update_nonexistent_entry(self, db_with_contract):
        """Обновление несуществующей записи — возвращает False."""
        db, _, contract_id = db_with_contract
        db.init_project_timeline(contract_id, self._sample_entries())
        result = db.update_timeline_entry(contract_id, 'NONEXISTENT', {'status': 'Тест'})
        assert result is False

    def test_empty_timeline(self, db_with_contract):
        """Пустой timeline для договора — пустой список."""
        db, _, contract_id = db_with_contract
        timeline = db.get_project_timeline(contract_id)
        assert timeline == []


# ============================================================================
# ТЕСТЫ: Поиск
# ============================================================================

class TestGlobalSearch:
    """Глобальный поиск по клиентам, договорам, CRM-карточкам."""

    def test_search_by_client_name(self, db_with_contract):
        """Поиск по имени клиента."""
        db, _, _ = db_with_contract
        result = db.global_search('Тестовый')
        assert result['total'] >= 1
        types = [r['type'] for r in result['results']]
        assert 'client' in types

    def test_search_by_contract_number(self, db_with_contract):
        """Поиск по номеру договора."""
        db, _, _ = db_with_contract
        result = db.global_search('001-2026')
        assert result['total'] >= 1
        types = [r['type'] for r in result['results']]
        assert 'contract' in types

    def test_search_by_address(self, db_with_contract):
        """Поиск по адресу (находит договор и CRM-карточку)."""
        db, _, _ = db_with_contract
        result = db.global_search('Тестовая')
        assert result['total'] >= 1

    def test_search_empty_query(self, db_with_contract):
        """Пустой запрос возвращает пустой результат."""
        db, _, _ = db_with_contract
        result = db.global_search('')
        assert result['total'] == 0
        assert result['results'] == []

    def test_search_short_query(self, db_with_contract):
        """Слишком короткий запрос (1 символ) — пустой результат."""
        db, _, _ = db_with_contract
        result = db.global_search('Т')
        assert result['total'] == 0

    def test_search_no_results(self, db_with_contract):
        """Поиск несуществующего — пустой результат."""
        db, _, _ = db_with_contract
        result = db.global_search('ZZZZZZZZZZZ')
        assert result['total'] == 0

    def test_search_with_limit(self, db_with_contract):
        """Параметр limit ограничивает количество результатов."""
        db, _, _ = db_with_contract
        result = db.global_search('Тестов', limit=1)
        assert len(result['results']) <= 1

    def test_search_returns_crm_card(self, db_with_contract):
        """Поиск находит CRM-карточки через JOIN с договорами."""
        db, _, _ = db_with_contract
        result = db.global_search('Тестовая')
        types = [r['type'] for r in result['results']]
        assert 'crm_card' in types


# ============================================================================
# ТЕСТЫ: Статистика
# ============================================================================

class TestDashboardStatistics:
    """Статистика дашборда."""

    def test_empty_db_returns_zeros(self, db):
        """Пустая БД — все значения = 0."""
        stats = db.get_dashboard_statistics()
        assert stats['individual_orders'] == 0
        assert stats['template_orders'] == 0
        assert stats['supervision_orders'] == 0

    def test_counts_individual_projects(self, db_with_contract):
        """Подсчёт индивидуальных проектов."""
        db, _, _ = db_with_contract
        stats = db.get_dashboard_statistics()
        assert stats['individual_orders'] >= 1

    def test_counts_supervision_projects(self, db_with_contract):
        """Подсчёт проектов авторского надзора."""
        db, _, _ = db_with_contract
        stats = db.get_dashboard_statistics()
        assert stats['supervision_orders'] >= 1

    def test_filter_by_year(self, db_with_contract):
        """Фильтрация по году."""
        db, _, _ = db_with_contract
        stats = db.get_dashboard_statistics(year=2026)
        assert stats['individual_orders'] >= 1

    def test_filter_by_wrong_year(self, db_with_contract):
        """Фильтр по несуществующему году — 0 результатов."""
        db, _, _ = db_with_contract
        stats = db.get_dashboard_statistics(year=2020)
        assert stats['individual_orders'] == 0

    def test_area_calculation(self, db_with_contract):
        """Площадь подсчитывается корректно."""
        db, _, _ = db_with_contract
        stats = db.get_dashboard_statistics()
        assert stats['individual_area'] >= 120


class TestGeneralStatistics:
    """Общая статистика."""

    def test_empty_db(self, db):
        """Пустая БД — все нули."""
        stats = db.get_general_statistics(year=2026, quarter=None, month=None)
        assert stats['total_completed'] == 0
        assert stats['total_area'] == 0
        assert stats['active_projects'] == 0

    def test_with_data(self, db_with_contract):
        """С данными — считает по статусам."""
        db, _, _ = db_with_contract
        stats = db.get_general_statistics(year=2026, quarter=None, month=None)
        # Договор со статусом 'АВТОРСКИЙ НАДЗОР' считается как completed
        assert stats['total_completed'] >= 1

    def test_by_city(self, db_with_contract):
        """Группировка по городам."""
        db, _, _ = db_with_contract
        stats = db.get_general_statistics(year=2026, quarter=None, month=None)
        assert 'СПБ' in stats['by_city']

    def test_by_project_type(self, db_with_contract):
        """Группировка по типу проекта."""
        db, _, _ = db_with_contract
        stats = db.get_general_statistics(year=2026, quarter=None, month=None)
        assert 'Индивидуальный' in stats['by_project_type']


# ============================================================================
# ТЕСТЫ: Агенты
# ============================================================================

class TestAgents:
    """CRUD агентов."""

    def test_get_all_agents_default(self, db):
        """В БД по умолчанию есть seed-агенты (ПЕТРОВИЧ, ФЕСТИВАЛЬ)."""
        agents = db.get_all_agents()
        assert isinstance(agents, list)
        names = [a['name'] for a in agents]
        assert 'ПЕТРОВИЧ' in names
        assert 'ФЕСТИВАЛЬ' in names

    def test_add_agent(self, db):
        """Добавление нового агента."""
        result = db.add_agent('НОВЫЙ АГЕНТ', '#00FF00')
        assert result is True

        agents = db.get_all_agents()
        names = [a['name'] for a in agents]
        assert 'НОВЫЙ АГЕНТ' in names

    def test_add_agent_color(self, db):
        """Цвет агента сохраняется."""
        db.add_agent('ЦВЕТНОЙ', '#AABBCC')
        agents = db.get_all_agents()
        colored = [a for a in agents if a['name'] == 'ЦВЕТНОЙ']
        assert len(colored) == 1
        assert colored[0]['color'] == '#AABBCC'

    def test_delete_agent_soft(self, db):
        """Мягкое удаление — статус меняется на 'удалён'."""
        db.add_agent('УДАЛЯЕМЫЙ', '#FF0000')
        agents = db.get_all_agents()
        agent = [a for a in agents if a['name'] == 'УДАЛЯЕМЫЙ'][0]

        result = db.delete_agent(agent['id'])
        assert result is True

        # После удаления get_all_agents может не показывать удалённых
        # (зависит от реализации — проверяем через прямой запрос)
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT status FROM agents WHERE id = ?', (agent['id'],))
        row = cursor.fetchone()
        db.close()
        assert row[0] == 'удалён'

    def test_get_all_agents_returns_full_name(self, db):
        """get_all_agents возвращает full_name (алиас name)."""
        agents = db.get_all_agents()
        for agent in agents:
            assert 'full_name' in agent
            assert agent['full_name'] == agent['name']

    def test_add_duplicate_agent_fails(self, db):
        """Добавление агента с дублирующим именем — ошибка (UNIQUE)."""
        db.add_agent('ДУБЛЬ', '#111111')
        result = db.add_agent('ДУБЛЬ', '#222222')
        # Возвращает False при ошибке
        assert result is False


# ============================================================================
# ТЕСТЫ: Города
# ============================================================================

class TestCities:
    """CRUD городов."""

    def test_get_all_cities_default(self, db):
        """В БД по умолчанию есть seed-города (СПБ, МСК, ВН)."""
        cities = db.get_all_cities()
        assert isinstance(cities, list)
        names = [c['name'] for c in cities]
        assert 'СПБ' in names
        assert 'МСК' in names

    def test_add_city(self, db):
        """Добавление нового города."""
        result = db.add_city('Казань')
        assert result is True

        cities = db.get_all_cities()
        names = [c['name'] for c in cities]
        assert 'Казань' in names

    def test_add_duplicate_city_ignored(self, db):
        """INSERT OR IGNORE — дубликат не создаётся, rowcount = 0."""
        db.add_city('Уникальный')
        result = db.add_city('Уникальный')
        assert result is False  # rowcount == 0

    def test_delete_city_soft(self, db):
        """Мягкое удаление — статус меняется на 'удалён'."""
        db.add_city('Удаляемый')
        cities = db.get_all_cities()
        city = [c for c in cities if c['name'] == 'Удаляемый'][0]

        result = db.delete_city(city['id'])
        assert result is True

        # Удалённый город не должен появляться в get_all_cities (фильтр status = 'активный')
        cities_after = db.get_all_cities()
        names_after = [c['name'] for c in cities_after]
        assert 'Удаляемый' not in names_after

    def test_city_status_field(self, db):
        """У городов есть поле status = 'активный'."""
        cities = db.get_all_cities()
        for city in cities:
            assert city['status'] == 'активный'

    def test_delete_nonexistent_city(self, db):
        """Удаление несуществующего города — не падает."""
        result = db.delete_city(99999)
        assert result is True  # UPDATE ничего не обновил, но не упал


# ============================================================================
# ТЕСТЫ: Полный lifecycle надзора
# ============================================================================

class TestSupervisionLifecycle:
    """Полный жизненный цикл: создание -> обновление -> пауза -> возобновление -> архив."""

    def test_full_lifecycle(self, db_with_contract):
        """Создание, перемещение, пауза, возобновление, архивирование."""
        db, _, contract_id = db_with_contract
        emp_id = _make_employee(db, 'Менеджер LC', 'mgr_lc', 'Старший менеджер проектов')

        # 1. Создание
        card_id = db.create_supervision_card(contract_id)
        assert card_id is not None

        # 2. Перемещение по стадиям
        db.update_supervision_card_column(card_id, 'Стадия 1: Закупка керамогранита')
        db.update_supervision_card_column(card_id, 'Стадия 2: Закупка сантехники')

        # 3. Пауза
        db.pause_supervision_card(card_id, 'Ожидание поставки', emp_id)
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT is_paused FROM supervision_cards WHERE id = ?', (card_id,))
        assert cursor.fetchone()['is_paused'] == 1
        db.close()

        # 4. Возобновление
        db.resume_supervision_card(card_id, emp_id)
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT is_paused FROM supervision_cards WHERE id = ?', (card_id,))
        assert cursor.fetchone()['is_paused'] == 0
        db.close()

        # 5. Архивирование (смена статуса договора)
        conn = db.connect()
        conn.execute('UPDATE contracts SET status = ? WHERE id = ?', ('СДАН', contract_id))
        conn.commit()
        db.close()

        # 6. Проверяем архив и историю
        archived = db.get_supervision_cards_archived()
        assert len(archived) >= 1

        history = db.get_supervision_history(card_id)
        assert len(history) >= 2  # pause + resume
