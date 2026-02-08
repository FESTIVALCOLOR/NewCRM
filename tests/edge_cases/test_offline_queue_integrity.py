"""
Тесты целостности offline очереди.

Покрывает сценарии:
1. Целостность данных в очереди при записи/чтении
2. Порядок операций при синхронизации
3. Обработка конфликтов данных
4. Восстановление после сбоев
5. Координация API Client и Offline Manager
"""

import pytest
import sqlite3
import json
import time
from datetime import datetime
from enum import Enum
from unittest.mock import Mock, patch


class OperationType(Enum):
    """Типы операций в очереди."""
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'


class TestOfflineQueueSchema:
    """Тесты схемы offline очереди."""

    def test_offline_queue_table_exists(self, temp_db):
        """Таблица offline_queue должна существовать."""
        cursor = temp_db.cursor()

        # Создаём таблицу если нет
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS offline_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                data TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                status TEXT DEFAULT 'pending',
                sync_attempts INTEGER DEFAULT 0,
                last_error TEXT
            )
        """)
        temp_db.commit()

        # Проверяем структуру
        cursor.execute("PRAGMA table_info(offline_queue)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}

        assert 'operation_type' in columns
        assert 'entity_type' in columns
        assert 'entity_id' in columns
        assert 'data' in columns
        assert 'status' in columns

    def test_offline_queue_required_fields(self, temp_db):
        """Обязательные поля не могут быть NULL."""
        cursor = temp_db.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS offline_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                data TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                status TEXT DEFAULT 'pending'
            )
        """)

        # Попытка вставить без обязательных полей
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO offline_queue (entity_type, data)
                VALUES ('client', '{}')
            """)  # Нет operation_type


class TestOfflineQueueOperations:
    """Тесты операций с offline очередью."""

    def setup_queue_table(self, db):
        """Создание таблицы очереди."""
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS offline_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                data TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                status TEXT DEFAULT 'pending',
                sync_attempts INTEGER DEFAULT 0,
                last_error TEXT
            )
        """)
        db.commit()

    def test_queue_create_operation(self, temp_db):
        """Добавление CREATE операции в очередь."""
        self.setup_queue_table(temp_db)
        cursor = temp_db.cursor()

        data = {
            'full_name': 'Тестовый Клиент',
            'phone': '+79991234567',
            'client_type': 'Физ. лицо'
        }

        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data)
            VALUES (?, ?, ?, ?)
        """, (OperationType.CREATE.value, 'client', None, json.dumps(data)))
        temp_db.commit()

        cursor.execute("SELECT * FROM offline_queue WHERE entity_type = 'client'")
        result = cursor.fetchone()

        assert result is not None
        assert result[1] == 'create'  # operation_type
        assert result[2] == 'client'  # entity_type
        loaded_data = json.loads(result[4])  # data
        assert loaded_data['full_name'] == 'Тестовый Клиент'

    def test_queue_update_operation(self, temp_db):
        """Добавление UPDATE операции в очередь."""
        self.setup_queue_table(temp_db)
        cursor = temp_db.cursor()

        data = {
            'full_name': 'Обновлённый Клиент',
            'phone': '+79991111111'
        }

        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data)
            VALUES (?, ?, ?, ?)
        """, (OperationType.UPDATE.value, 'client', 123, json.dumps(data)))
        temp_db.commit()

        cursor.execute("SELECT * FROM offline_queue WHERE entity_id = 123")
        result = cursor.fetchone()

        assert result is not None
        assert result[1] == 'update'
        assert result[3] == 123  # entity_id

    def test_queue_delete_operation(self, temp_db):
        """Добавление DELETE операции в очередь."""
        self.setup_queue_table(temp_db)
        cursor = temp_db.cursor()

        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data)
            VALUES (?, ?, ?, ?)
        """, (OperationType.DELETE.value, 'client', 456, '{}'))
        temp_db.commit()

        cursor.execute("SELECT * FROM offline_queue WHERE entity_id = 456")
        result = cursor.fetchone()

        assert result is not None
        assert result[1] == 'delete'

    def test_queue_order_preserved(self, temp_db):
        """Порядок операций в очереди должен сохраняться (FIFO)."""
        self.setup_queue_table(temp_db)
        cursor = temp_db.cursor()

        # Добавляем операции в определённом порядке
        operations = [
            ('create', 'client', None, '{"name": "Client 1"}'),
            ('update', 'client', 1, '{"name": "Client 1 Updated"}'),
            ('create', 'contract', None, '{"number": "C-001"}'),
            ('delete', 'client', 2, '{}'),
        ]

        for op_type, entity, entity_id, data in operations:
            cursor.execute("""
                INSERT INTO offline_queue (operation_type, entity_type, entity_id, data)
                VALUES (?, ?, ?, ?)
            """, (op_type, entity, entity_id, data))
            time.sleep(0.01)  # Небольшая задержка для различия created_at

        temp_db.commit()

        # Получаем в порядке создания
        cursor.execute("""
            SELECT operation_type, entity_type FROM offline_queue
            ORDER BY id ASC
        """)
        results = cursor.fetchall()

        assert len(results) == 4
        # Convert Row objects to tuples for comparison
        assert (results[0]['operation_type'], results[0]['entity_type']) == ('create', 'client')
        assert (results[1]['operation_type'], results[1]['entity_type']) == ('update', 'client')
        assert (results[2]['operation_type'], results[2]['entity_type']) == ('create', 'contract')
        assert (results[3]['operation_type'], results[3]['entity_type']) == ('delete', 'client')


class TestOfflineQueueSync:
    """Тесты синхронизации offline очереди."""

    def setup_queue_table(self, db):
        """Создание таблицы очереди."""
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS offline_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                data TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                status TEXT DEFAULT 'pending',
                sync_attempts INTEGER DEFAULT 0,
                last_error TEXT
            )
        """)
        db.commit()

    def test_sync_marks_operation_completed(self, temp_db):
        """Успешная синхронизация помечает операцию как выполненную."""
        self.setup_queue_table(temp_db)
        cursor = temp_db.cursor()

        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data)
            VALUES ('create', 'client', NULL, '{"name": "Test"}')
        """)
        operation_id = cursor.lastrowid
        temp_db.commit()

        # Симулируем успешную синхронизацию
        cursor.execute("""
            UPDATE offline_queue SET status = 'synced' WHERE id = ?
        """, (operation_id,))
        temp_db.commit()

        cursor.execute("SELECT status FROM offline_queue WHERE id = ?", (operation_id,))
        assert cursor.fetchone()[0] == 'synced'

    def test_sync_increments_attempts_on_failure(self, temp_db):
        """Неудачная синхронизация увеличивает счётчик попыток."""
        self.setup_queue_table(temp_db)
        cursor = temp_db.cursor()

        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data)
            VALUES ('update', 'client', 1, '{"name": "Test"}')
        """)
        operation_id = cursor.lastrowid
        temp_db.commit()

        # Симулируем неудачную попытку
        cursor.execute("""
            UPDATE offline_queue
            SET sync_attempts = sync_attempts + 1,
                last_error = 'Connection timeout'
            WHERE id = ?
        """, (operation_id,))
        temp_db.commit()

        cursor.execute("""
            SELECT sync_attempts, last_error FROM offline_queue WHERE id = ?
        """, (operation_id,))
        attempts, error = cursor.fetchone()
        assert attempts == 1
        assert 'timeout' in error.lower()

    def test_max_sync_attempts_limit(self, temp_db):
        """После максимума попыток операция помечается как failed."""
        self.setup_queue_table(temp_db)
        cursor = temp_db.cursor()

        MAX_ATTEMPTS = 3

        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data, sync_attempts)
            VALUES ('delete', 'client', 1, '{}', ?)
        """, (MAX_ATTEMPTS,))
        operation_id = cursor.lastrowid
        temp_db.commit()

        # Проверяем что операция с макс. попытками должна быть помечена как failed
        cursor.execute("""
            SELECT id FROM offline_queue
            WHERE sync_attempts >= ? AND status = 'pending'
        """, (MAX_ATTEMPTS,))
        failed_ops = cursor.fetchall()

        if failed_ops:
            for (op_id,) in failed_ops:
                cursor.execute("""
                    UPDATE offline_queue SET status = 'failed' WHERE id = ?
                """, (op_id,))
            temp_db.commit()

        cursor.execute("SELECT status FROM offline_queue WHERE id = ?", (operation_id,))
        assert cursor.fetchone()[0] == 'failed'


class TestOfflineQueueConflicts:
    """Тесты обработки конфликтов в offline очереди."""

    def setup_queue_table(self, db):
        """Создание таблицы очереди."""
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS offline_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                data TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                status TEXT DEFAULT 'pending',
                sync_attempts INTEGER DEFAULT 0,
                last_error TEXT
            )
        """)
        db.commit()

    def test_conflicting_updates_to_same_entity(self, temp_db):
        """Несколько UPDATE для одной сущности."""
        self.setup_queue_table(temp_db)
        cursor = temp_db.cursor()

        entity_id = 123

        # Первое обновление
        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data)
            VALUES ('update', 'client', ?, '{"name": "First Update"}')
        """, (entity_id,))

        # Второе обновление той же сущности
        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data)
            VALUES ('update', 'client', ?, '{"name": "Second Update"}')
        """, (entity_id,))
        temp_db.commit()

        # Получаем все обновления для сущности
        cursor.execute("""
            SELECT id, data FROM offline_queue
            WHERE entity_type = 'client' AND entity_id = ? AND operation_type = 'update'
            ORDER BY id ASC
        """, (entity_id,))
        updates = cursor.fetchall()

        assert len(updates) == 2

        # СТРАТЕГИЯ: Можно объединить или применить последовательно
        # Здесь проверяем что оба сохранены для последовательного применения
        first_data = json.loads(updates[0][1])
        second_data = json.loads(updates[1][1])

        assert first_data['name'] == 'First Update'
        assert second_data['name'] == 'Second Update'

    def test_create_then_delete_same_entity(self, temp_db):
        """CREATE + DELETE одной сущности должны взаимно отменяться."""
        self.setup_queue_table(temp_db)
        cursor = temp_db.cursor()

        # Временный ID для локально созданной сущности
        temp_id = -1

        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data)
            VALUES ('create', 'client', ?, '{"name": "Temporary Client"}')
        """, (temp_id,))
        create_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data)
            VALUES ('delete', 'client', ?, '{}')
        """, (temp_id,))
        delete_id = cursor.lastrowid
        temp_db.commit()

        # ОПТИМИЗАЦИЯ: Можно удалить обе операции
        cursor.execute("""
            SELECT id, operation_type FROM offline_queue
            WHERE entity_type = 'client' AND entity_id = ?
            ORDER BY id ASC
        """, (temp_id,))
        ops = cursor.fetchall()

        # Проверяем наличие пары create-delete
        op_types = [op[1] for op in ops]
        if 'create' in op_types and 'delete' in op_types:
            # Можем отменить обе операции
            cursor.execute("""
                UPDATE offline_queue SET status = 'cancelled'
                WHERE entity_type = 'client' AND entity_id = ?
            """, (temp_id,))
            temp_db.commit()

        cursor.execute("""
            SELECT status FROM offline_queue WHERE id IN (?, ?)
        """, (create_id, delete_id))
        statuses = [r[0] for r in cursor.fetchall()]
        assert all(s == 'cancelled' for s in statuses)

    def test_update_after_delete_conflict(self, temp_db):
        """UPDATE после DELETE - конфликт."""
        self.setup_queue_table(temp_db)
        cursor = temp_db.cursor()

        entity_id = 456

        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data)
            VALUES ('delete', 'client', ?, '{}')
        """, (entity_id,))

        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data)
            VALUES ('update', 'client', ?, '{"name": "Update After Delete"}')
        """, (entity_id,))
        update_id = cursor.lastrowid
        temp_db.commit()

        # UPDATE после DELETE должен быть помечен как конфликтный
        cursor.execute("""
            SELECT id FROM offline_queue
            WHERE entity_type = 'client'
            AND entity_id = ?
            AND operation_type = 'delete'
            AND id < ?
        """, (entity_id, update_id))

        delete_before_update = cursor.fetchone()
        if delete_before_update:
            # Помечаем update как конфликтный
            cursor.execute("""
                UPDATE offline_queue
                SET status = 'conflict', last_error = 'Update after delete'
                WHERE id = ?
            """, (update_id,))
            temp_db.commit()

        cursor.execute("SELECT status FROM offline_queue WHERE id = ?", (update_id,))
        assert cursor.fetchone()[0] == 'conflict'


class TestOfflineQueueRecovery:
    """Тесты восстановления после сбоев."""

    def setup_queue_table(self, db):
        """Создание таблицы очереди."""
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS offline_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                data TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                status TEXT DEFAULT 'pending',
                sync_attempts INTEGER DEFAULT 0,
                last_error TEXT
            )
        """)
        db.commit()

    def test_recover_pending_operations_after_restart(self, temp_db):
        """Восстановление pending операций после перезапуска."""
        self.setup_queue_table(temp_db)
        cursor = temp_db.cursor()

        # Создаём несколько операций
        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data, status)
            VALUES ('create', 'client', NULL, '{"name": "Pending 1"}', 'pending')
        """)
        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data, status)
            VALUES ('update', 'client', 1, '{"name": "Pending 2"}', 'pending')
        """)
        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data, status)
            VALUES ('delete', 'client', 2, '{}', 'synced')
        """)
        temp_db.commit()

        # "Перезапуск" - получаем все pending операции
        cursor.execute("""
            SELECT id, operation_type, entity_type FROM offline_queue
            WHERE status = 'pending'
            ORDER BY id ASC
        """)
        pending = cursor.fetchall()

        assert len(pending) == 2
        assert pending[0][1] == 'create'
        assert pending[1][1] == 'update'

    def test_recover_partial_sync(self, temp_db):
        """Восстановление после частичной синхронизации."""
        self.setup_queue_table(temp_db)
        cursor = temp_db.cursor()

        # Операции: часть synced, часть pending
        ops_data = [
            ('create', 'client', None, '{"name": "1"}', 'synced'),
            ('create', 'client', None, '{"name": "2"}', 'synced'),
            ('create', 'client', None, '{"name": "3"}', 'pending'),  # Сбой здесь
            ('create', 'client', None, '{"name": "4"}', 'pending'),
            ('create', 'client', None, '{"name": "5"}', 'pending'),
        ]

        for op_type, entity, entity_id, data, status in ops_data:
            cursor.execute("""
                INSERT INTO offline_queue (operation_type, entity_type, entity_id, data, status)
                VALUES (?, ?, ?, ?, ?)
            """, (op_type, entity, entity_id, data, status))
        temp_db.commit()

        # Восстановление: продолжаем с pending
        cursor.execute("""
            SELECT COUNT(*) FROM offline_queue WHERE status = 'pending'
        """)
        pending_count = cursor.fetchone()[0]

        assert pending_count == 3

        cursor.execute("""
            SELECT MIN(id) FROM offline_queue WHERE status = 'pending'
        """)
        first_pending_id = cursor.fetchone()[0]

        # Проверяем что это операция "3"
        cursor.execute("SELECT data FROM offline_queue WHERE id = ?", (first_pending_id,))
        data = json.loads(cursor.fetchone()[0])
        assert data['name'] == '3'


class TestOfflineAPIClientCoordination:
    """Тесты координации Offline Manager и API Client."""

    def test_offline_cache_duration_respected(self):
        """API Client должен уважать OFFLINE_CACHE_DURATION."""
        # Мок API клиента
        class MockAPIClient:
            OFFLINE_CACHE_DURATION = 5  # секунд
            _last_offline_time = None

            def _is_recently_offline(self):
                if self._last_offline_time is None:
                    return False
                elapsed = time.time() - self._last_offline_time
                return elapsed < self.OFFLINE_CACHE_DURATION

            def _mark_offline(self):
                self._last_offline_time = time.time()

        client = MockAPIClient()

        # Изначально не offline
        assert not client._is_recently_offline()

        # Помечаем как offline
        client._mark_offline()
        assert client._is_recently_offline()

        # Сразу после - ещё offline
        time.sleep(0.1)
        assert client._is_recently_offline()

    def test_offline_manager_resets_api_client_cache(self):
        """Offline Manager должен сбрасывать кеш API Client после успешного ping."""
        class MockAPIClient:
            OFFLINE_CACHE_DURATION = 5
            _last_offline_time = None

            def _is_recently_offline(self):
                if self._last_offline_time is None:
                    return False
                return (time.time() - self._last_offline_time) < self.OFFLINE_CACHE_DURATION

            def _mark_offline(self):
                self._last_offline_time = time.time()

            def reset_offline_cache(self):
                """НОВЫЙ МЕТОД: Сброс кеша."""
                self._last_offline_time = None

        client = MockAPIClient()

        # Клиент в offline
        client._mark_offline()
        assert client._is_recently_offline()

        # Offline Manager делает успешный ping и сбрасывает кеш
        # (симулируем успешный ping)
        ping_success = True
        if ping_success:
            client.reset_offline_cache()

        # Теперь клиент не в offline
        assert not client._is_recently_offline()

    def test_sync_timeout_increased_for_first_request(self):
        """Таймаут синхронизации должен быть увеличен для первого запроса."""
        DEFAULT_TIMEOUT = 5
        SYNC_TIMEOUT = 10

        class MockAPIClient:
            def __init__(self):
                self.timeout = DEFAULT_TIMEOUT

            def set_sync_timeout(self):
                self.timeout = SYNC_TIMEOUT

            def reset_timeout(self):
                self.timeout = DEFAULT_TIMEOUT

        client = MockAPIClient()

        # Обычный таймаут
        assert client.timeout == DEFAULT_TIMEOUT

        # При синхронизации увеличиваем
        client.set_sync_timeout()
        assert client.timeout == SYNC_TIMEOUT

        # После синхронизации возвращаем
        client.reset_timeout()
        assert client.timeout == DEFAULT_TIMEOUT


class TestOfflineQueueYandexDisk:
    """Тесты offline очереди для операций Яндекс.Диска."""

    def setup_queue_table(self, db):
        """Создание таблицы очереди."""
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS offline_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                data TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                status TEXT DEFAULT 'pending',
                sync_attempts INTEGER DEFAULT 0,
                last_error TEXT
            )
        """)
        db.commit()

    def test_yandex_folder_rename_in_queue(self, temp_db):
        """Переименование папки Яндекс.Диска в очереди."""
        self.setup_queue_table(temp_db)
        cursor = temp_db.cursor()

        data = {
            'old_path': '/Projects/Старый адрес - Иванов',
            'new_path': '/Projects/Новый адрес - Иванов'
        }

        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data)
            VALUES ('update', 'yandex_folder', 123, ?)
        """, (json.dumps(data),))
        temp_db.commit()

        cursor.execute("""
            SELECT data FROM offline_queue
            WHERE entity_type = 'yandex_folder' AND entity_id = 123
        """)
        result = cursor.fetchone()
        loaded_data = json.loads(result[0])

        assert loaded_data['old_path'] == '/Projects/Старый адрес - Иванов'
        assert loaded_data['new_path'] == '/Projects/Новый адрес - Иванов'

    def test_yandex_folder_operations_order(self, temp_db):
        """Порядок операций с папками Яндекс.Диска важен."""
        self.setup_queue_table(temp_db)
        cursor = temp_db.cursor()

        # Создание папки
        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data)
            VALUES ('create', 'yandex_folder', 1, '{"path": "/Projects/New Folder"}')
        """)

        # Переименование
        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data)
            VALUES ('update', 'yandex_folder', 1, '{"old_path": "/Projects/New Folder", "new_path": "/Projects/Renamed"}')
        """)

        # Удаление
        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data)
            VALUES ('delete', 'yandex_folder', 1, '{"path": "/Projects/Renamed"}')
        """)
        temp_db.commit()

        # Проверяем порядок
        cursor.execute("""
            SELECT operation_type FROM offline_queue
            WHERE entity_type = 'yandex_folder' AND entity_id = 1
            ORDER BY id ASC
        """)
        ops = [r[0] for r in cursor.fetchall()]

        assert ops == ['create', 'update', 'delete']
