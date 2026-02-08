# -*- coding: utf-8 -*-
"""
Менеджер синхронизации данных
Обеспечивает real-time синхронизацию между клиентами через API
"""

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
import traceback


class SyncManager(QObject):
    """
    Менеджер синхронизации данных с сервером.

    Функции:
    - Периодический опрос сервера для получения обновлений
    - Отслеживание блокировок записей (concurrent editing)
    - Отслеживание онлайн-пользователей
    - Уведомление UI об изменениях данных
    """

    # Сигналы для уведомления UI об изменениях
    data_updated = pyqtSignal(str, list)  # (entity_type, list of updated items)
    clients_updated = pyqtSignal(list)
    contracts_updated = pyqtSignal(list)
    employees_updated = pyqtSignal(list)
    crm_cards_updated = pyqtSignal(list)
    supervision_cards_updated = pyqtSignal(list)

    # Сигналы для concurrent editing
    record_locked = pyqtSignal(str, int, str)  # (entity_type, entity_id, locked_by_user)
    record_unlocked = pyqtSignal(str, int)  # (entity_type, entity_id)

    # Сигналы для онлайн-статуса
    online_users_updated = pyqtSignal(list)  # Список онлайн пользователей
    connection_status_changed = pyqtSignal(bool)  # True = online, False = offline

    # Константы
    DEFAULT_SYNC_INTERVAL = 30000  # 30 секунд (было 5 - слишком агрессивно)
    HEARTBEAT_INTERVAL = 60000  # 60 секунд для heartbeat (было 30)
    LOCK_TIMEOUT = 120  # 2 минуты - время жизни блокировки

    def __init__(self, api_client, employee_id: int, parent=None):
        """
        Инициализация менеджера синхронизации.

        Args:
            api_client: Экземпляр APIClient для работы с сервером
            employee_id: ID текущего сотрудника
            parent: Родительский QObject
        """
        super().__init__(parent)

        self.api_client = api_client
        self.employee_id = employee_id
        self.last_sync_timestamp: Optional[datetime] = None
        self.is_running = False
        self.is_connected = False

        # Таймеры
        self._sync_timer = QTimer(self)
        self._sync_timer.timeout.connect(self._sync_data)

        self._heartbeat_timer = QTimer(self)
        self._heartbeat_timer.timeout.connect(self._send_heartbeat)

        # Кэш блокировок
        self._locked_records: Dict[str, Dict[int, str]] = {}  # {entity_type: {entity_id: locked_by}}

        # Кэш онлайн пользователей
        self._online_users: List[Dict[str, Any]] = []

        # Обработчики обновлений для разных типов сущностей
        self._update_handlers: Dict[str, List[Callable]] = {
            'clients': [],
            'contracts': [],
            'employees': [],
            'crm_cards': [],
            'supervision_cards': [],
            'payments': [],
        }

        # Типы сущностей для синхронизации
        self._sync_entity_types = ['clients', 'contracts', 'employees']

    def start(self, sync_interval: int = None):
        """
        Запустить синхронизацию.

        Args:
            sync_interval: Интервал синхронизации в миллисекундах
        """
        if self.is_running:
            return

        self.is_running = True
        self.last_sync_timestamp = datetime.utcnow()

        interval = sync_interval or self.DEFAULT_SYNC_INTERVAL

        # Запускаем таймеры
        self._sync_timer.start(interval)
        self._heartbeat_timer.start(self.HEARTBEAT_INTERVAL)

        # Сразу отправляем heartbeat
        self._send_heartbeat()

        print(f"[SyncManager] Запущен с интервалом {interval}ms")

    def stop(self):
        """Остановить синхронизацию"""
        if not self.is_running:
            return

        self.is_running = False
        self._sync_timer.stop()
        self._heartbeat_timer.stop()

        # Освобождаем все блокировки текущего пользователя
        self._release_all_locks()

        print("[SyncManager] Остановлен")

    def _sync_data(self):
        """Синхронизация данных с сервером"""
        if not self.api_client or not self.last_sync_timestamp:
            return

        # Пропускаем sync если API в offline режиме
        if not self.api_client.is_online:
            return

        try:
            # Получаем обновления (без retry для sync - не критично)
            result = self.api_client.sync(
                last_sync_timestamp=self.last_sync_timestamp,
                entity_types=self._sync_entity_types,
                retry=False,  # Отключаем retry для фоновой синхронизации
                timeout=3  # Короткий таймаут для sync
            )

            # Обновляем статус соединения
            if not self.is_connected:
                self.is_connected = True
                self.connection_status_changed.emit(True)

            # Обновляем timestamp
            if result.get('timestamp'):
                self.last_sync_timestamp = datetime.fromisoformat(
                    result['timestamp'].replace('Z', '+00:00')
                )

            # Обрабатываем обновления по типам сущностей (только если есть данные)
            clients = result.get('clients', [])
            if clients:
                self.clients_updated.emit(clients)
                self.data_updated.emit('clients', clients)

            contracts = result.get('contracts', [])
            if contracts:
                self.contracts_updated.emit(contracts)
                self.data_updated.emit('contracts', contracts)

            employees = result.get('employees', [])
            if employees:
                self.employees_updated.emit(employees)
                self.data_updated.emit('employees', employees)

        except Exception as e:
            # Обновляем статус соединения
            if self.is_connected:
                self.is_connected = False
                self.connection_status_changed.emit(False)
            # Не спамим в консоль при каждой ошибке sync
            pass

    def _send_heartbeat(self):
        """Отправка heartbeat для поддержания онлайн-статуса"""
        if not self.api_client:
            return

        # Пропускаем heartbeat если API в offline режиме
        if not self.api_client.is_online:
            return

        try:
            # Обновляем свой статус и получаем список онлайн пользователей
            # ИСПРАВЛЕНИЕ 04.02.2026: Увеличен таймаут с 3 до 10 сек
            # 3 сек слишком мало при нестабильной сети - вызывает частые offline
            # mark_offline=False чтобы heartbeat не переводил в offline режим
            result = self.api_client._request(
                'POST',
                f"{self.api_client.base_url}/api/heartbeat",
                json={'employee_id': self.employee_id},
                retry=False,
                timeout=10,
                mark_offline=False  # Heartbeat не должен переводить в offline
            )

            if result.status_code == 200:
                data = result.json()
                online_users = data.get('online_users', [])

                # Обновляем кэш и уведомляем
                if online_users != self._online_users:
                    self._online_users = online_users
                    self.online_users_updated.emit(online_users)

        except Exception as e:
            # Heartbeat ошибки не критичны - не выводим в консоль
            # чтобы не засорять лог при нестабильной сети
            pass

    # ==========================================
    # CONCURRENT EDITING (Блокировки записей)
    # ==========================================

    def lock_record(self, entity_type: str, entity_id: int) -> bool:
        """
        Заблокировать запись для редактирования.

        Args:
            entity_type: Тип сущности ('client', 'contract', 'employee', etc.)
            entity_id: ID записи

        Returns:
            True если блокировка успешна, False если запись уже заблокирована
        """
        if not self.api_client:
            return True  # В оффлайн режиме всегда разрешаем

        try:
            response = self.api_client._request(
                'POST',
                f"{self.api_client.base_url}/api/locks",
                json={
                    'entity_type': entity_type,
                    'entity_id': entity_id,
                    'employee_id': self.employee_id
                },
                retry=False,
                timeout=5
            )

            if response.status_code == 200:
                # Добавляем в локальный кэш
                if entity_type not in self._locked_records:
                    self._locked_records[entity_type] = {}
                self._locked_records[entity_type][entity_id] = str(self.employee_id)
                return True

            elif response.status_code == 409:
                # Запись уже заблокирована
                data = response.json()
                locked_by = data.get('locked_by', 'другим пользователем')
                self.record_locked.emit(entity_type, entity_id, locked_by)
                return False

        except Exception as e:
            print(f"[SyncManager] Ошибка блокировки: {e}")
            return True  # В случае ошибки разрешаем (оптимистичный подход)

        return True

    def unlock_record(self, entity_type: str, entity_id: int):
        """
        Разблокировать запись после редактирования.

        Args:
            entity_type: Тип сущности
            entity_id: ID записи
        """
        if not self.api_client:
            return

        try:
            self.api_client._request(
                'DELETE',
                f"{self.api_client.base_url}/api/locks/{entity_type}/{entity_id}",
                retry=False,
                timeout=5
            )

            # Удаляем из локального кэша
            if entity_type in self._locked_records:
                self._locked_records[entity_type].pop(entity_id, None)

            self.record_unlocked.emit(entity_type, entity_id)

        except Exception as e:
            print(f"[SyncManager] Ошибка разблокировки: {e}")

    def is_record_locked(self, entity_type: str, entity_id: int) -> tuple:
        """
        Проверить, заблокирована ли запись.

        Args:
            entity_type: Тип сущности
            entity_id: ID записи

        Returns:
            (is_locked: bool, locked_by: Optional[str])
        """
        if not self.api_client:
            return (False, None)

        try:
            response = self.api_client._request(
                'GET',
                f"{self.api_client.base_url}/api/locks/{entity_type}/{entity_id}",
                retry=False,
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                return (data.get('is_locked', False), data.get('locked_by'))

        except Exception:
            pass

        return (False, None)

    def _release_all_locks(self):
        """Освободить все блокировки текущего пользователя"""
        if not self.api_client:
            return

        try:
            self.api_client._request(
                'DELETE',
                f"{self.api_client.base_url}/api/locks/user/{self.employee_id}",
                retry=False,
                timeout=5
            )
        except Exception as e:
            print(f"[SyncManager] Ошибка освобождения блокировок: {e}")

        self._locked_records.clear()

    # ==========================================
    # ONLINE USERS
    # ==========================================

    def get_online_users(self) -> List[Dict[str, Any]]:
        """Получить список онлайн пользователей из кэша"""
        return self._online_users.copy()

    def get_online_users_count(self) -> int:
        """Получить количество онлайн пользователей"""
        return len(self._online_users)

    # ==========================================
    # SUBSCRIPTION API
    # ==========================================

    def subscribe(self, entity_type: str, handler: Callable):
        """
        Подписаться на обновления определенного типа сущностей.

        Args:
            entity_type: Тип сущности ('clients', 'contracts', etc.)
            handler: Функция-обработчик, принимающая список обновленных записей
        """
        if entity_type in self._update_handlers:
            self._update_handlers[entity_type].append(handler)

    def unsubscribe(self, entity_type: str, handler: Callable):
        """
        Отписаться от обновлений.

        Args:
            entity_type: Тип сущности
            handler: Функция-обработчик для удаления
        """
        if entity_type in self._update_handlers:
            try:
                self._update_handlers[entity_type].remove(handler)
            except ValueError:
                pass

    def set_sync_entity_types(self, entity_types: List[str]):
        """
        Установить типы сущностей для синхронизации.

        Args:
            entity_types: Список типов ('clients', 'contracts', 'employees')
        """
        self._sync_entity_types = entity_types

    def force_sync(self):
        """Принудительно запустить синхронизацию"""
        self._sync_data()

    def set_sync_interval(self, interval_ms: int):
        """
        Изменить интервал синхронизации.

        Args:
            interval_ms: Новый интервал в миллисекундах
        """
        if self.is_running:
            self._sync_timer.stop()
            self._sync_timer.start(interval_ms)


class EditLockContext:
    """
    Контекстный менеджер для блокировки записи на время редактирования.

    Использование:
        with EditLockContext(sync_manager, 'client', 123) as lock:
            if lock.acquired:
                # Редактирование
                ...
            else:
                # Показать сообщение о блокировке
                show_message(f"Запись редактируется: {lock.locked_by}")
    """

    def __init__(self, sync_manager: SyncManager, entity_type: str, entity_id: int):
        self.sync_manager = sync_manager
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.acquired = False
        self.locked_by = None

    def __enter__(self):
        if self.sync_manager:
            self.acquired = self.sync_manager.lock_record(self.entity_type, self.entity_id)
            if not self.acquired:
                _, self.locked_by = self.sync_manager.is_record_locked(
                    self.entity_type, self.entity_id
                )
        else:
            self.acquired = True  # Без sync_manager всегда разрешаем
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.acquired and self.sync_manager:
            self.sync_manager.unlock_record(self.entity_type, self.entity_id)
        return False
