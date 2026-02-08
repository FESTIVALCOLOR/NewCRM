# -*- coding: utf-8 -*-
"""
Менеджер offline-режима для CRM приложения.
Обеспечивает работу приложения при отсутствии связи с сервером.
"""

import json
import sqlite3
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


class ConnectionStatus(Enum):
    """Статус подключения к серверу"""
    ONLINE = "online"
    OFFLINE = "offline"
    CONNECTING = "connecting"
    SYNCING = "syncing"


class OperationType(Enum):
    """Тип операции в очереди"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class OperationStatus(Enum):
    """Статус операции в очереди"""
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    FAILED = "failed"
    CONFLICT = "conflict"


class OfflineManager(QObject):
    """
    Менеджер offline-режима.

    Функции:
    - Отслеживание статуса подключения к серверу
    - Очередь отложенных операций при работе offline
    - Автоматическая синхронизация при восстановлении связи
    - Разрешение конфликтов
    """

    # Сигналы для UI
    connection_status_changed = pyqtSignal(str)  # ConnectionStatus.value
    pending_operations_changed = pyqtSignal(int)  # количество ожидающих операций
    sync_progress = pyqtSignal(int, int, str)  # current, total, message
    sync_completed = pyqtSignal(bool, str)  # success, message
    conflict_detected = pyqtSignal(dict)  # данные о конфликте

    # Интервал проверки подключения (мс)
    CHECK_INTERVAL = 60000  # 60 секунд (было 30 - слишком часто при offline)

    # Таймаут для проверки подключения (сек)
    PING_TIMEOUT = 2  # (было 5 - слишком долго)

    # Таймаут для операций синхронизации (сек)
    SYNC_TIMEOUT = 10  # Увеличенный таймаут для синхронизации после восстановления связи

    # Максимальное количество ошибок синхронизации перед переходом в offline
    MAX_SYNC_ERRORS = 3

    def __init__(self, db_path: str, api_client=None):
        """
        Args:
            db_path: Путь к локальной SQLite базе данных
            api_client: Экземпляр APIClient (может быть None при инициализации)
        """
        super().__init__()

        self.db_path = db_path
        self.api_client = api_client
        self._status = ConnectionStatus.OFFLINE
        self._check_timer = None
        self._sync_lock = threading.Lock()
        self._is_syncing = False

        # Инициализация таблицы очереди операций
        self._init_operations_queue_table()

        # Таймер проверки подключения
        self._check_timer = QTimer()
        self._check_timer.timeout.connect(self._check_connection)

    def _get_connection(self) -> sqlite3.Connection:
        """Получить соединение с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_operations_queue_table(self):
        """Создание таблицы очереди операций"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS offline_operations_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                data TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                synced_at TEXT,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                server_entity_id INTEGER
            )
        """)

        # Индексы для быстрого поиска
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_offline_queue_status
            ON offline_operations_queue(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_offline_queue_entity
            ON offline_operations_queue(entity_type, entity_id)
        """)

        conn.commit()
        conn.close()

        print("[OFFLINE] Таблица очереди операций инициализирована")

    @property
    def status(self) -> ConnectionStatus:
        """Текущий статус подключения"""
        return self._status

    @status.setter
    def status(self, value: ConnectionStatus):
        """Установить статус подключения"""
        if self._status != value:
            old_status = self._status
            self._status = value
            print(f"[OFFLINE] Статус изменён: {old_status.value} -> {value.value}")
            self.connection_status_changed.emit(value.value)

    def set_api_client(self, api_client):
        """Установить API клиент"""
        self.api_client = api_client

    def start_monitoring(self):
        """Запустить мониторинг подключения"""
        print("[OFFLINE] Запуск мониторинга подключения")
        self._check_connection()
        self._check_timer.start(self.CHECK_INTERVAL)

    def stop_monitoring(self):
        """Остановить мониторинг подключения"""
        print("[OFFLINE] Остановка мониторинга подключения")
        if self._check_timer:
            self._check_timer.stop()

    def _check_connection(self):
        """Проверить подключение к серверу"""
        if not self.api_client:
            self.status = ConnectionStatus.OFFLINE
            return

        if self._is_syncing:
            return

        # ИСПРАВЛЕНИЕ 30.01.2026: Используем force_online_check() из API Client
        # вместо собственной логики ping. Это гарантирует координацию
        # между OfflineManager и APIClient.
        try:
            # Используем новый метод force_online_check если доступен
            if hasattr(self.api_client, 'force_online_check'):
                is_online = self.api_client.force_online_check()
            else:
                # Fallback на старую логику для совместимости
                import requests
                session = requests.Session()
                session.trust_env = False

                response = session.get(
                    f"{self.api_client.base_url}/",
                    timeout=self.PING_TIMEOUT,
                    verify=False
                )
                is_online = response.status_code == 200

            if is_online:
                was_offline = self.status == ConnectionStatus.OFFLINE
                self.status = ConnectionStatus.ONLINE

                # ИСПРАВЛЕНИЕ 30.01.2026: Используем reset_offline_cache()
                # для полной синхронизации статуса
                if hasattr(self.api_client, 'reset_offline_cache'):
                    self.api_client.reset_offline_cache()
                elif hasattr(self.api_client, '_last_offline_time'):
                    self.api_client._last_offline_time = None
                    self.api_client._is_online = True

                # Если были offline и есть ожидающие операции - синхронизируем
                if was_offline:
                    pending_count = self.get_pending_operations_count()
                    if pending_count > 0:
                        print(f"[OFFLINE] Восстановлено подключение, {pending_count} операций в очереди")
                        self._start_sync()
            else:
                self.status = ConnectionStatus.OFFLINE

        except Exception as e:
            # Не спамим в консоль при каждой ошибке проверки
            if self.status != ConnectionStatus.OFFLINE:
                print(f"[OFFLINE] Нет подключения к серверу")
            self.status = ConnectionStatus.OFFLINE

    def is_online(self) -> bool:
        """Проверить, есть ли подключение к серверу"""
        return self.status == ConnectionStatus.ONLINE

    def queue_operation(self, operation_type: OperationType, entity_type: str,
                       entity_id: Optional[int], data: Dict[str, Any]) -> int:
        """
        Добавить операцию в очередь.

        Args:
            operation_type: Тип операции (create/update/delete)
            entity_type: Тип сущности (client/contract/crm_card и т.д.)
            entity_id: ID сущности (None для create)
            data: Данные операции

        Returns:
            ID операции в очереди
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO offline_operations_queue
            (operation_type, entity_type, entity_id, data, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            operation_type.value,
            entity_type,
            entity_id,
            json.dumps(data, ensure_ascii=False, default=str),
            OperationStatus.PENDING.value,
            datetime.now().isoformat()
        ))

        operation_id = cursor.lastrowid
        conn.commit()
        conn.close()

        print(f"[OFFLINE] Операция добавлена в очередь: {operation_type.value} {entity_type} #{entity_id}")

        # Уведомляем UI об изменении количества операций
        self.pending_operations_changed.emit(self.get_pending_operations_count())

        return operation_id

    def get_pending_operations_count(self) -> int:
        """Получить количество ожидающих операций"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM offline_operations_queue
            WHERE status = ?
        """, (OperationStatus.PENDING.value,))

        count = cursor.fetchone()[0]
        conn.close()

        return count

    def get_pending_operations(self) -> List[Dict[str, Any]]:
        """Получить список ожидающих операций"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM offline_operations_queue
            WHERE status = ?
            ORDER BY created_at ASC
        """, (OperationStatus.PENDING.value,))

        operations = []
        for row in cursor.fetchall():
            operations.append({
                'id': row['id'],
                'operation_type': row['operation_type'],
                'entity_type': row['entity_type'],
                'entity_id': row['entity_id'],
                'data': json.loads(row['data']),
                'status': row['status'],
                'created_at': row['created_at'],
                'retry_count': row['retry_count']
            })

        conn.close()
        return operations

    def _start_sync(self):
        """Запустить синхронизацию отложенных операций"""
        if self._is_syncing:
            print("[OFFLINE] Синхронизация уже выполняется")
            return

        # Запускаем в отдельном потоке
        sync_thread = threading.Thread(target=self._sync_pending_operations)
        sync_thread.daemon = True
        sync_thread.start()

    def _sync_pending_operations(self):
        """Синхронизировать отложенные операции с сервером"""
        with self._sync_lock:
            if self._is_syncing:
                return
            self._is_syncing = True

        try:
            self.status = ConnectionStatus.SYNCING

            operations = self.get_pending_operations()
            total = len(operations)

            if total == 0:
                self.sync_completed.emit(True, "Нет операций для синхронизации")
                return

            print(f"[OFFLINE] Начало синхронизации {total} операций")

            synced = 0
            failed = 0

            for i, op in enumerate(operations):
                self.sync_progress.emit(i + 1, total, f"Синхронизация {op['entity_type']}...")

                success = self._sync_single_operation(op)

                if success:
                    synced += 1
                else:
                    failed += 1

                # Небольшая задержка между операциями
                time.sleep(0.1)

            message = f"Синхронизировано: {synced}, ошибок: {failed}"
            print(f"[OFFLINE] {message}")

            # Улучшенная логика: не переходим в offline если хотя бы часть операций прошла
            if synced > 0:
                # Часть операций прошла - остаемся online
                self.sync_completed.emit(failed == 0, message)
                # Неудачные операции останутся в очереди и будут повторены позже
            elif failed > 0 and failed >= self.MAX_SYNC_ERRORS:
                # Все операции провалились - возможно проблема с сетью
                print(f"[OFFLINE] Все {failed} операций провалились, проверяем соединение...")
                self.sync_completed.emit(False, message)
            else:
                self.sync_completed.emit(failed == 0, message)

            self.pending_operations_changed.emit(self.get_pending_operations_count())

        except Exception as e:
            print(f"[OFFLINE] Ошибка синхронизации: {e}")
            self.sync_completed.emit(False, str(e))

        finally:
            self._is_syncing = False
            self._check_connection()

    def _sync_single_operation(self, operation: Dict[str, Any]) -> bool:
        """
        Синхронизировать одну операцию.

        Returns:
            True если успешно, False если ошибка
        """
        op_id = operation['id']
        op_type = operation['operation_type']
        entity_type = operation['entity_type']
        entity_id = operation['entity_id']
        data = operation['data']

        try:
            # Обновляем статус на "syncing"
            self._update_operation_status(op_id, OperationStatus.SYNCING)

            # Выполняем операцию на сервере
            result = self._execute_server_operation(op_type, entity_type, entity_id, data)

            if result['success']:
                # Обновляем статус на "synced"
                self._update_operation_status(
                    op_id,
                    OperationStatus.SYNCED,
                    server_entity_id=result.get('server_id')
                )

                # Если это была операция создания, обновляем локальный ID
                if op_type == OperationType.CREATE.value and result.get('server_id'):
                    self._update_local_entity_id(entity_type, entity_id, result['server_id'])

                return True
            else:
                # Обновляем статус на "failed"
                self._update_operation_status(
                    op_id,
                    OperationStatus.FAILED,
                    error_message=result.get('error', 'Unknown error')
                )
                return False

        except Exception as e:
            print(f"[OFFLINE] Ошибка синхронизации операции {op_id}: {e}")
            self._update_operation_status(op_id, OperationStatus.FAILED, error_message=str(e))
            return False

    def _execute_server_operation(self, op_type: str, entity_type: str,
                                  entity_id: Optional[int], data: Dict) -> Dict[str, Any]:
        """
        Выполнить операцию на сервере.

        Returns:
            Dict с результатом: {'success': bool, 'server_id': int, 'error': str}
        """
        if not self.api_client:
            return {'success': False, 'error': 'API client not available'}

        # Временно увеличиваем таймаут для синхронизации
        original_timeout = self.api_client.DEFAULT_TIMEOUT
        self.api_client.DEFAULT_TIMEOUT = self.SYNC_TIMEOUT

        try:
            # Маппинг операций на методы API
            if entity_type == 'client':
                return self._sync_client_operation(op_type, entity_id, data)
            elif entity_type == 'contract':
                return self._sync_contract_operation(op_type, entity_id, data)
            elif entity_type == 'crm_card':
                return self._sync_crm_card_operation(op_type, entity_id, data)
            elif entity_type == 'supervision_card':
                return self._sync_supervision_card_operation(op_type, entity_id, data)
            elif entity_type == 'employee':
                return self._sync_employee_operation(op_type, entity_id, data)
            elif entity_type == 'payment':
                return self._sync_payment_operation(op_type, entity_id, data)
            elif entity_type == 'yandex_folder':
                return self._sync_yandex_folder_operation(op_type, entity_id, data)
            else:
                return {'success': False, 'error': f'Unknown entity type: {entity_type}'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

        finally:
            # Восстанавливаем оригинальный таймаут
            self.api_client.DEFAULT_TIMEOUT = original_timeout

    def _sync_client_operation(self, op_type: str, entity_id: int, data: Dict) -> Dict:
        """Синхронизация операции с клиентом"""
        if op_type == OperationType.CREATE.value:
            result = self.api_client.create_client(data)
            if result:
                return {'success': True, 'server_id': result.get('id')}
            return {'success': False, 'error': 'Failed to create client'}

        elif op_type == OperationType.UPDATE.value:
            result = self.api_client.update_client(entity_id, data)
            if result:
                return {'success': True, 'server_id': entity_id}
            return {'success': False, 'error': 'Failed to update client'}

        elif op_type == OperationType.DELETE.value:
            success = self.api_client.delete_client(entity_id)
            return {'success': success, 'error': None if success else 'Failed to delete client'}

        return {'success': False, 'error': 'Unknown operation type'}

    def _sync_contract_operation(self, op_type: str, entity_id: int, data: Dict) -> Dict:
        """Синхронизация операции с договором"""
        if op_type == OperationType.CREATE.value:
            result = self.api_client.create_contract(data)
            if result:
                return {'success': True, 'server_id': result.get('id')}
            return {'success': False, 'error': 'Failed to create contract'}

        elif op_type == OperationType.UPDATE.value:
            result = self.api_client.update_contract(entity_id, data)
            if result:
                return {'success': True, 'server_id': entity_id}
            return {'success': False, 'error': 'Failed to update contract'}

        elif op_type == OperationType.DELETE.value:
            success = self.api_client.delete_contract(entity_id)
            return {'success': success, 'error': None if success else 'Failed to delete contract'}

        return {'success': False, 'error': 'Unknown operation type'}

    def _sync_crm_card_operation(self, op_type: str, entity_id: int, data: Dict) -> Dict:
        """Синхронизация операции с CRM карточкой"""
        if op_type == OperationType.UPDATE.value:
            result = self.api_client.update_crm_card(entity_id, data)
            if result:
                return {'success': True, 'server_id': entity_id}
            return {'success': False, 'error': 'Failed to update CRM card'}

        return {'success': False, 'error': 'Unknown operation type for CRM card'}

    def _sync_supervision_card_operation(self, op_type: str, entity_id: int, data: Dict) -> Dict:
        """Синхронизация операции с карточкой надзора"""
        if op_type == OperationType.UPDATE.value:
            result = self.api_client.update_supervision_card(entity_id, data)
            if result:
                return {'success': True, 'server_id': entity_id}
            return {'success': False, 'error': 'Failed to update supervision card'}

        return {'success': False, 'error': 'Unknown operation type for supervision card'}

    def _sync_payment_operation(self, op_type: str, entity_id: int, data: Dict) -> Dict:
        """Синхронизация операции с платежом"""
        if op_type == OperationType.CREATE.value:
            result = self.api_client.create_payment(data)
            if result:
                return {'success': True, 'server_id': result.get('id')}
            return {'success': False, 'error': 'Failed to create payment'}

        elif op_type == OperationType.UPDATE.value:
            result = self.api_client.update_payment(entity_id, data)
            if result:
                return {'success': True, 'server_id': entity_id}
            return {'success': False, 'error': 'Failed to update payment'}

        elif op_type == OperationType.DELETE.value:
            # Удаляем платеж по ID (source хранится для информации, но API принимает только ID)
            result = self.api_client.delete_payment(entity_id)
            success = result is not None
            return {'success': success, 'error': None if success else 'Failed to delete payment'}

        return {'success': False, 'error': 'Unknown operation type for payment'}

    def _sync_employee_operation(self, op_type: str, entity_id: int, data: Dict) -> Dict:
        """Синхронизация операции с сотрудником"""
        if op_type == OperationType.CREATE.value:
            result = self.api_client.create_employee(data)
            if result:
                return {'success': True, 'server_id': result.get('id')}
            return {'success': False, 'error': 'Failed to create employee'}

        elif op_type == OperationType.UPDATE.value:
            result = self.api_client.update_employee(entity_id, data)
            if result:
                return {'success': True, 'server_id': entity_id}
            return {'success': False, 'error': 'Failed to update employee'}

        elif op_type == OperationType.DELETE.value:
            success = self.api_client.delete_employee(entity_id)
            return {'success': success, 'error': None if success else 'Failed to delete employee'}

        return {'success': False, 'error': 'Unknown operation type for employee'}

    def _sync_yandex_folder_operation(self, op_type: str, entity_id: int, data: Dict) -> Dict:
        """Синхронизация операции с папкой Яндекс.Диска"""
        try:
            from utils.yandex_disk import YandexDiskManager
            from config import YANDEX_DISK_TOKEN

            if not YANDEX_DISK_TOKEN:
                return {'success': False, 'error': 'Yandex Disk token not configured'}

            yd = YandexDiskManager(YANDEX_DISK_TOKEN)

            if op_type == OperationType.UPDATE.value:
                # Переименование/перемещение папки
                old_path = data.get('old_path')
                new_path = data.get('new_path')

                if not old_path or not new_path:
                    return {'success': False, 'error': 'Missing old_path or new_path'}

                success = yd.move_folder(old_path, new_path)
                if success:
                    print(f"[YANDEX] Папка переименована: {old_path} -> {new_path}")
                    return {'success': True, 'server_id': entity_id}
                return {'success': False, 'error': 'Failed to rename Yandex folder'}

            elif op_type == OperationType.CREATE.value:
                # Создание папки
                folder_path = data.get('folder_path')
                if not folder_path:
                    return {'success': False, 'error': 'Missing folder_path'}

                success = yd.create_folder(folder_path)
                if success:
                    print(f"[YANDEX] Папка создана: {folder_path}")
                    return {'success': True, 'server_id': entity_id}
                return {'success': False, 'error': 'Failed to create Yandex folder'}

            elif op_type == OperationType.DELETE.value:
                # Удаление папки
                folder_path = data.get('folder_path')
                if not folder_path:
                    return {'success': False, 'error': 'Missing folder_path'}

                success = yd.delete_folder(folder_path)
                if success:
                    print(f"[YANDEX] Папка удалена: {folder_path}")
                    return {'success': True, 'server_id': entity_id}
                return {'success': False, 'error': 'Failed to delete Yandex folder'}

            return {'success': False, 'error': 'Unknown operation type for yandex_folder'}

        except Exception as e:
            print(f"[YANDEX] Ошибка синхронизации: {e}")
            return {'success': False, 'error': str(e)}

    def _update_operation_status(self, operation_id: int, status: OperationStatus,
                                 error_message: str = None, server_entity_id: int = None):
        """Обновить статус операции в очереди"""
        conn = self._get_connection()
        cursor = conn.cursor()

        update_fields = ["status = ?"]
        params = [status.value]

        if status == OperationStatus.SYNCED:
            update_fields.append("synced_at = ?")
            params.append(datetime.now().isoformat())

        if error_message:
            update_fields.append("error_message = ?")
            params.append(error_message)
            update_fields.append("retry_count = retry_count + 1")

        if server_entity_id:
            update_fields.append("server_entity_id = ?")
            params.append(server_entity_id)

        params.append(operation_id)

        cursor.execute(f"""
            UPDATE offline_operations_queue
            SET {', '.join(update_fields)}
            WHERE id = ?
        """, params)

        conn.commit()
        conn.close()

    def _update_local_entity_id(self, entity_type: str, local_id: int, server_id: int):
        """
        Обновить локальный ID сущности на серверный.
        Вызывается после успешного создания сущности на сервере.
        """
        if local_id == server_id:
            return

        conn = self._get_connection()
        cursor = conn.cursor()

        table_map = {
            'client': 'clients',
            'contract': 'contracts',
            'crm_card': 'crm_cards',
            'supervision_card': 'supervision_cards',
            'payment': 'payments'
        }

        table = table_map.get(entity_type)
        if table:
            try:
                cursor.execute(f"UPDATE {table} SET id = ? WHERE id = ?", (server_id, local_id))
                conn.commit()
                print(f"[OFFLINE] Обновлён ID {entity_type}: {local_id} -> {server_id}")
            except Exception as e:
                print(f"[OFFLINE] Ошибка обновления ID: {e}")

        conn.close()

    def clear_synced_operations(self):
        """Очистить синхронизированные операции из очереди"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM offline_operations_queue
            WHERE status = ?
        """, (OperationStatus.SYNCED.value,))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        print(f"[OFFLINE] Удалено {deleted} синхронизированных операций")
        return deleted

    def retry_failed_operations(self):
        """Повторить неудавшиеся операции"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Сбрасываем статус failed операций на pending (максимум 3 попытки)
        cursor.execute("""
            UPDATE offline_operations_queue
            SET status = ?
            WHERE status = ? AND retry_count < 3
        """, (OperationStatus.PENDING.value, OperationStatus.FAILED.value))

        updated = cursor.rowcount
        conn.commit()
        conn.close()

        print(f"[OFFLINE] {updated} операций поставлено на повтор")

        if updated > 0 and self.is_online():
            self._start_sync()

        return updated

    def get_operation_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Получить историю операций"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM offline_operations_queue
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        operations = []
        for row in cursor.fetchall():
            operations.append({
                'id': row['id'],
                'operation_type': row['operation_type'],
                'entity_type': row['entity_type'],
                'entity_id': row['entity_id'],
                'data': json.loads(row['data']) if row['data'] else {},
                'status': row['status'],
                'created_at': row['created_at'],
                'synced_at': row['synced_at'],
                'error_message': row['error_message'],
                'retry_count': row['retry_count']
            })

        conn.close()
        return operations

    def force_sync(self):
        """Принудительная синхронизация"""
        if self.is_online():
            self._start_sync()
        else:
            print("[OFFLINE] Невозможно синхронизировать: нет подключения")


# Глобальный экземпляр менеджера
_offline_manager: Optional[OfflineManager] = None


def get_offline_manager() -> Optional[OfflineManager]:
    """Получить глобальный экземпляр OfflineManager"""
    return _offline_manager


def init_offline_manager(db_path: str, api_client=None) -> OfflineManager:
    """Инициализировать глобальный OfflineManager"""
    global _offline_manager
    _offline_manager = OfflineManager(db_path, api_client)
    return _offline_manager
