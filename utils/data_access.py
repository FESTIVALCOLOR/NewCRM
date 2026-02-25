"""
Унифицированный доступ к данным (API или локальная БД)
Автоматически выбирает источник данных в зависимости от наличия api_client
Поддерживает offline-режим с очередью отложенных операций
"""
from typing import Optional, List, Dict, Any
from database.db_manager import DatabaseManager
from PyQt5.QtCore import QObject, pyqtSignal
from utils.api_client import APIAuthError


def _safe_log(msg):
    """Безопасный вывод в консоль (не ломает except-блоки на Windows charmap)"""
    try:
        print(msg)
    except (UnicodeEncodeError, OSError, AttributeError):
        pass

# Импорт OfflineManager (ленивый для избежания циклических импортов)
_offline_manager = None


def get_offline_manager():
    """Получить экземпляр OfflineManager"""
    global _offline_manager
    if _offline_manager is None:
        try:
            from utils.offline_manager import get_offline_manager as get_om
            _offline_manager = get_om()
        except ImportError:
            pass
    return _offline_manager


class DataAccess(QObject):
    """
    Класс для унифицированного доступа к данным.
    Если api_client доступен - использует API, иначе локальную БД.
    Поддерживает offline-режим с очередью отложенных операций.
    """

    # Сигналы для UI
    connection_status_changed = pyqtSignal(bool)  # True = online, False = offline
    operation_queued = pyqtSignal(str, str)  # entity_type, operation_type
    pending_operations_changed = pyqtSignal(int)  # количество ожидающих операций

    def __init__(self, api_client=None, db: DatabaseManager = None, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.db = db or DatabaseManager()
        self._is_online = api_client is not None
        # Флаг: при True чтение идёт из локальной БД (мгновенно),
        # API используется только для записи. Устанавливается при первом показе табов.
        self.prefer_local = False

        # ПРИМЕЧАНИЕ: Ранее каждый DataAccess подключался к OfflineManager.pending_operations_changed
        # и connection_status_changed. Это создавало десятки stale-коннекций от уничтоженных
        # DataAccess (диалоги и т.д.), что приводило к segfault при emit() — access violation
        # на удалённых QObject. Удалено: is_online проверяет OfflineManager напрямую (line ~77),
        # а pending_operations_changed DataAccess никем не слушается.

    @property
    def is_multi_user(self) -> bool:
        """Проверяет, работаем ли в многопользовательском режиме"""
        return self.api_client is not None

    @property
    def is_online(self) -> bool:
        """Проверяет, есть ли подключение к серверу"""
        om = get_offline_manager()
        if om:
            return om.is_online()
        return self._is_online and self.api_client is not None

    def _queue_operation(self, op_type: str, entity_type: str, entity_id: int, data: Dict):
        """Добавить операцию в очередь для синхронизации.

        ВАЖНО: Если вызывается из except-блока, проверяет тип исключения.
        В очередь попадают ТОЛЬКО сетевые ошибки (APIConnectionError, APITimeoutError).
        Бизнес-ошибки (409 Conflict, 400 Bad Request и т.д.) НЕ ставятся в очередь,
        т.к. при синхронизации они снова вернут ту же ошибку (бесконечный retry).
        """
        import sys
        exc_type, exc_value, _ = sys.exc_info()
        if exc_type is not None:
            # Вызвано из except-блока — проверяем тип ошибки
            from utils.api_client.exceptions import APIConnectionError, APITimeoutError
            if not issubclass(exc_type, (APIConnectionError, APITimeoutError)):
                _safe_log(f"[DataAccess] Бизнес-ошибка ({exc_type.__name__}), НЕ в очередь: {exc_value}")
                return

        om = get_offline_manager()
        if om:
            from utils.offline_manager import OperationType
            op_enum = OperationType(op_type)
            om.queue_operation(op_enum, entity_type, entity_id, data)
            self.operation_queued.emit(entity_type, op_type)

    def get_pending_operations_count(self) -> int:
        """Получить количество ожидающих операций"""
        om = get_offline_manager()
        if om:
            return om.get_pending_operations_count()
        return 0

    def force_sync(self):
        """Принудительная синхронизация отложенных операций"""
        om = get_offline_manager()
        if om:
            om.force_sync()

    def _should_use_api(self) -> bool:
        """Проверяет, нужно ли обращаться к API для чтения.
        Если prefer_local=True, читаем из локальной БД (мгновенно)."""
        return self.api_client is not None and not self.prefer_local

    # ==================== КЛИЕНТЫ ====================

    def get_all_clients(self, skip: int = 0, limit: int = 10000) -> List[Dict]:
        """Получить всех клиентов.

        Параметры skip/limit позволяют получать данные постранично.
        По умолчанию limit=10000 для обратной совместимости (загрузка всех записей).
        """
        if self._should_use_api():
            try:
                return self.api_client.get_clients(skip=skip, limit=limit)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_all_clients, fallback: {e}")
        return self.db.get_all_clients(skip=skip, limit=limit)

    def get_clients_paginated(
        self, skip: int = 0, limit: int = 100
    ) -> tuple:
        """Получить клиентов с информацией о пагинации.

        Возвращает кортеж (список клиентов, общее количество записей).
        В сетевом режиме использует заголовок X-Total-Count от сервера.
        В автономном режиме подсчитывает total через запрос к локальной БД.
        """
        if self._should_use_api():
            try:
                return self.api_client.get_clients_paginated(skip=skip, limit=limit)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_clients_paginated, fallback: {e}")
        # Автономный режим: данные и total из локальной БД
        clients = self.db.get_all_clients(skip=skip, limit=limit)
        total = self.db.get_clients_count()
        return clients, total

    def get_client(self, client_id: int) -> Optional[Dict]:
        """Получить клиента по ID"""
        if self._should_use_api():
            try:
                return self.api_client.get_client(client_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_client, fallback: {e}")
        return self.db.get_client_by_id(client_id)

    def get_contracts_count_by_client(self, client_id: int) -> int:
        """Получить количество договоров клиента"""
        if self._should_use_api():
            try:
                contracts = self.api_client.get_contracts()
                return sum(1 for c in contracts if c.get('client_id') == client_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_contracts_count_by_client, fallback: {e}")
        if hasattr(self.db, 'get_contracts_count_by_client'):
            return self.db.get_contracts_count_by_client(client_id)
        return 0

    def get_contracts_count(
        self,
        status: Optional[str] = None,
        project_type: Optional[str] = None,
        year: Optional[int] = None
    ) -> int:
        """Получить общее количество договоров (API-first, fallback на локальную БД)"""
        if self._should_use_api():
            try:
                return self.api_client.get_contracts_count(
                    status=status,
                    project_type=project_type,
                    year=year
                )
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_contracts_count, fallback: {e}")
        if self.db and hasattr(self.db, 'get_contracts_count'):
            try:
                return self.db.get_contracts_count(
                    status=status,
                    project_type=project_type,
                    year=year
                )
            except Exception as e:
                _safe_log(f"[DataAccess] DB error get_contracts_count: {e}")
        return 0

    def create_client(self, client_data: Dict) -> Optional[Dict]:
        """Создать клиента"""
        # Сначала сохраняем локально
        client_id = self.db.add_client(client_data)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.create_client(client_data)
                if result:
                    # Защита: API может вернуть list вместо dict
                    if isinstance(result, list):
                        result = result[0] if result else {}
                    # Обновляем локальный ID на серверный если отличается
                    server_id = result.get('id') if isinstance(result, dict) else None
                    if server_id and server_id != client_id:
                        self._update_local_id('clients', client_id, server_id)
                    return result
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API create_client: {e}")
                self._queue_operation('create', 'client', client_id, client_data)
        elif self.api_client:
            # Offline режим - добавляем в очередь
            self._queue_operation('create', 'client', client_id, client_data)

        return {'id': client_id, **client_data} if client_id else None

    def _update_local_id(self, table: str, local_id: int, server_id: int):
        """Обновить локальный ID на серверный"""
        if local_id == server_id:
            return
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute(f"UPDATE {table} SET id = ? WHERE id = ?", (server_id, local_id))
            conn.commit()
            self.db.close()
            _safe_log(f"[DataAccess] Обновлён ID в {table}: {local_id} -> {server_id}")
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка обновления ID: {e}")

    def update_client(self, client_id: int, client_data: Dict) -> bool:
        """Обновить клиента"""
        # Сначала обновляем локально
        self.db.update_client(client_id, client_data)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.update_client(client_id, client_data)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API update_client: {e}")
                self._queue_operation('update', 'client', client_id, client_data)
        elif self.api_client:
            # Offline режим
            self._queue_operation('update', 'client', client_id, client_data)

        return True

    def delete_client(self, client_id: int) -> bool:
        """Удалить клиента"""
        # Сначала удаляем локально
        self.db.delete_client(client_id)

        if self.is_online and self.api_client:
            try:
                return self.api_client.delete_client(client_id)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API delete_client: {e}")
                self._queue_operation('delete', 'client', client_id, {})
        elif self.api_client:
            self._queue_operation('delete', 'client', client_id, {})

        return True

    # ==================== ДОГОВОРА ====================

    def get_all_contracts(self, skip: int = 0, limit: int = 10000) -> List[Dict]:
        """Получить все договора.

        Параметры skip/limit позволяют получать данные постранично.
        По умолчанию limit=10000 для обратной совместимости (загрузка всех записей).
        """
        if self._should_use_api():
            try:
                return self.api_client.get_contracts(skip=skip, limit=limit)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_all_contracts, fallback: {e}")
        return self.db.get_all_contracts(skip=skip, limit=limit)

    def get_contracts_paginated(
        self, skip: int = 0, limit: int = 100
    ) -> tuple:
        """Получить договора с информацией о пагинации.

        Возвращает кортеж (список договоров, общее количество записей).
        В сетевом режиме использует заголовок X-Total-Count от сервера.
        В автономном режиме подсчитывает total через запрос к локальной БД.
        """
        if self._should_use_api():
            try:
                return self.api_client.get_contracts_paginated(skip=skip, limit=limit)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_contracts_paginated, fallback: {e}")
        # Автономный режим: данные и total из локальной БД
        contracts = self.db.get_all_contracts(skip=skip, limit=limit)
        total = self.db.get_contracts_count()
        return contracts, total

    def get_contract(self, contract_id: int) -> Optional[Dict]:
        """Получить договор по ID"""
        if self._should_use_api():
            try:
                return self.api_client.get_contract(contract_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_contract, fallback: {e}")
        return self.db.get_contract_by_id(contract_id)

    def create_contract(self, contract_data: Dict) -> Optional[Dict]:
        """Создать договор"""
        # Сначала сохраняем локально (add_contract также создаёт CRM карточку)
        contract_id = self.db.add_contract(contract_data)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.create_contract(contract_data)
                if result:
                    # Защита: API может вернуть list вместо dict
                    if isinstance(result, list):
                        result = result[0] if result else {}
                    server_id = result.get('id') if isinstance(result, dict) else None
                    if server_id and server_id != contract_id:
                        self._update_local_id('contracts', contract_id, server_id)

                    # Проверяем что CRM карточка была создана на сервере
                    # (сервер создаёт её атомарно, но на всякий случай)
                    self._ensure_crm_card_exists(result, contract_data)

                    return result
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API create_contract: {e}")
                self._queue_operation('create', 'contract', contract_id, contract_data)
        elif self.api_client:
            self._queue_operation('create', 'contract', contract_id, contract_data)

        return {'id': contract_id, **contract_data} if contract_id else None

    def _ensure_crm_card_exists(self, contract_result: Dict, contract_data: Dict):
        """Проверить что CRM карточка создана для договора, создать если нет"""
        try:
            project_type = contract_data.get('project_type', '')
            if project_type == 'Авторский надзор':
                return  # Для надзора используется SupervisionCard

            contract_id = contract_result.get('id') if isinstance(contract_result, dict) else None
            if not contract_id:
                return

            # Проверяем наличие CRM карточки через API
            cards = self.api_client.get_crm_cards(project_type)
            has_card = any(
                (c.get('contract_id') == contract_id)
                for c in (cards if isinstance(cards, list) else [])
            )

            if not has_card:
                _safe_log(f"[DataAccess] CRM карточка для договора {contract_id} не найдена, создаём...")
                self.api_client.create_crm_card({
                    'contract_id': contract_id,
                    'column_name': 'Новый заказ'
                })
                _safe_log(f"[DataAccess] CRM карточка для договора {contract_id} создана")
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка проверки CRM карточки: {e}")

    def update_contract(self, contract_id: int, contract_data: Dict) -> bool:
        """Обновить договор"""
        # Сначала обновляем локально
        self.db.update_contract(contract_id, contract_data)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.update_contract(contract_id, contract_data)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API update_contract: {e}")
                self._queue_operation('update', 'contract', contract_id, contract_data)
        elif self.api_client:
            self._queue_operation('update', 'contract', contract_id, contract_data)

        return True

    def delete_contract(self, contract_id: int) -> bool:
        """Удалить договор"""
        if self.is_online and self.api_client:
            try:
                result = self.api_client.delete_contract(contract_id)
                if result:
                    # Также удаляем локально для консистентности кэша
                    crm_card_id = self.db.get_crm_card_id_by_contract(contract_id)
                    self.db.delete_order(contract_id, crm_card_id)
                    return True
                return False
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API delete_contract: {e}")
                self._queue_operation('delete', 'contract', contract_id, {})
                crm_card_id = self.db.get_crm_card_id_by_contract(contract_id)
                return self.db.delete_order(contract_id, crm_card_id)
        elif self.api_client:
            # Offline-режим: удаляем локально и ставим в очередь
            self._queue_operation('delete', 'contract', contract_id, {})
            crm_card_id = self.db.get_crm_card_id_by_contract(contract_id)
            return self.db.delete_order(contract_id, crm_card_id)
        # Только локальная БД
        crm_card_id = self.db.get_crm_card_id_by_contract(contract_id)
        return self.db.delete_order(contract_id, crm_card_id)

    def check_contract_number_exists(self, contract_number: str, exclude_id: int = None) -> bool:
        """Проверить существование номера договора"""
        if self._should_use_api():
            try:
                return self.api_client.check_contract_number_exists(contract_number, exclude_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error check_contract_number_exists, fallback: {e}")
        return self.db.check_contract_number_exists(contract_number, exclude_id)

    # ==================== СОТРУДНИКИ ====================

    def get_all_employees(self) -> List[Dict]:
        """Получить всех сотрудников"""
        if self._should_use_api():
            try:
                return self.api_client.get_employees(skip=0, limit=10000)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_all_employees, fallback: {e}")
        return self.db.get_all_employees()

    def get_employees_by_position(self, position: str) -> List[Dict]:
        """Получить сотрудников по должности"""
        if self._should_use_api():
            try:
                return self.api_client.get_employees_by_position(position)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_employees_by_position, fallback: {e}")
        return self.db.get_employees_by_position(position)

    def get_employee(self, employee_id: int) -> Optional[Dict]:
        """Получить сотрудника по ID"""
        if self._should_use_api():
            try:
                return self.api_client.get_employee(employee_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_employee, fallback: {e}")
        return self.db.get_employee_by_id(employee_id)

    def create_employee(self, employee_data: Dict) -> Optional[Dict]:
        """Создать сотрудника"""
        employee_id = self.db.add_employee(employee_data)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.create_employee(employee_data)
                if result:
                    # Защита: API может вернуть list вместо dict
                    if isinstance(result, list):
                        result = result[0] if result else {}
                    server_id = result.get('id') if isinstance(result, dict) else None
                    if server_id and server_id != employee_id:
                        self._update_local_id('employees', employee_id, server_id)
                    return result
            except Exception as e:
                _safe_log(f"[DataAccess] API error create_employee: {e}")
                self._queue_operation('create', 'employee', employee_id, employee_data)
        elif self.api_client:
            self._queue_operation('create', 'employee', employee_id, employee_data)

        return {'id': employee_id, **employee_data} if employee_id else None

    def update_employee(self, employee_id: int, employee_data: Dict) -> bool:
        """Обновить сотрудника"""
        self.db.update_employee(employee_id, employee_data)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.update_employee(employee_id, employee_data)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] API error update_employee: {e}")
                self._queue_operation('update', 'employee', employee_id, employee_data)
        elif self.api_client:
            self._queue_operation('update', 'employee', employee_id, employee_data)

        return True

    def get_employee_active_assignments(self, employee_id: int) -> List[Dict]:
        """Получить список активных назначений сотрудника"""
        try:
            if self._should_use_api():
                try:
                    cards = self.api_client.get_crm_cards('Индивидуальный') + self.api_client.get_crm_cards('Шаблонный')
                    result = []
                    for card in cards:
                        team = card.get('team', []) or []
                        for member in team:
                            if member.get('executor_id') == employee_id and member.get('status') != 'completed':
                                result.append({'card_id': card.get('id'), 'contract_number': card.get('contract_number', ''), 'stage': member.get('stage_name', '')})
                    return result
                except Exception:
                    pass
            # Fallback: локальная БД
            return self.db.get_employee_active_assignments(employee_id) if hasattr(self.db, 'get_employee_active_assignments') else []
        except Exception:
            return []

    def delete_employee(self, employee_id: int) -> bool:
        """Удалить сотрудника"""
        self.db.delete_employee(employee_id)

        if self.is_online and self.api_client:
            try:
                return self.api_client.delete_employee(employee_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error delete_employee: {e}")
                self._queue_operation('delete', 'employee', employee_id, {})
        elif self.api_client:
            self._queue_operation('delete', 'employee', employee_id, {})

        return True

    # ==================== CRM КАРТОЧКИ ====================

    def get_crm_cards(self, project_type: str) -> List[Dict]:
        """Получить CRM карточки по типу проекта"""
        if self._should_use_api():
            try:
                return self.api_client.get_crm_cards(project_type)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_crm_cards, fallback: {e}")
        return self.db.get_crm_cards_by_project_type(project_type)

    def get_crm_card(self, card_id: int) -> Optional[Dict]:
        """Получить CRM карточку по ID"""
        if self._should_use_api():
            try:
                return self.api_client.get_crm_card(card_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_crm_card, fallback: {e}")
        return self.db.get_crm_card_data(card_id)

    def get_archived_crm_cards(self, project_type: str) -> List[Dict]:
        """Получить архивные CRM карточки"""
        if self._should_use_api():
            try:
                return self.api_client.get_archived_crm_cards(project_type)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_archived_crm_cards, fallback: {e}")
        return self.db.get_archived_crm_cards(project_type)

    def create_crm_card(self, card_data: Dict) -> Optional[Dict]:
        """Создать CRM карточку"""
        # Сначала сохраняем локально
        card_id = self.db.add_crm_card(card_data)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.create_crm_card(card_data)
                if result:
                    # Защита: API может вернуть list вместо dict
                    if isinstance(result, list):
                        result = result[0] if result else {}
                    server_id = result.get('id') if isinstance(result, dict) else None
                    if server_id and server_id != card_id:
                        self._update_local_id('crm_cards', card_id, server_id)
                    return result
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API create_crm_card: {e}")
                self._queue_operation('create', 'crm_card', card_id, card_data)
        elif self.api_client:
            self._queue_operation('create', 'crm_card', card_id, card_data)

        return {'id': card_id, **card_data} if card_id else None

    def update_crm_card(self, card_id: int, updates: Dict) -> bool:
        """Обновить CRM карточку"""
        # Сначала обновляем локально
        self.db.update_crm_card(card_id, updates)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.update_crm_card(card_id, updates)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API update_crm_card: {e}")
                self._queue_operation('update', 'crm_card', card_id, updates)
        elif self.api_client:
            self._queue_operation('update', 'crm_card', card_id, updates)

        return True

    def delete_crm_card(self, card_id: int) -> bool:
        """Удалить CRM карточку"""
        # Сначала удаляем локально
        contract_id = self.db.get_contract_id_by_crm_card(card_id)
        if contract_id:
            self.db.delete_order(contract_id, card_id)

        if self.is_online and self.api_client:
            try:
                self.api_client.delete_crm_card(card_id)
                return True
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API delete_crm_card: {e}")
                self._queue_operation('delete', 'crm_card', card_id, {})
        elif self.api_client:
            self._queue_operation('delete', 'crm_card', card_id, {})

        return True

    def update_crm_card_column(self, card_id: int, column: str) -> bool:
        """Переместить карточку в другую колонку"""
        # Сначала обновляем локально
        self.db.update_crm_card_column(card_id, column)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.update_crm_card(card_id, {'column_name': column})
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API update_crm_card_column: {e}")
                self._queue_operation('update', 'crm_card', card_id, {'column_name': column})
        elif self.api_client:
            self._queue_operation('update', 'crm_card', card_id, {'column_name': column})

        return True

    # ==================== CRM WORKFLOW ====================

    def move_crm_card(self, card_id: int, column: str) -> bool:
        """Переместить CRM карточку в другую колонку (через workflow или напрямую)"""
        # Сначала обновляем локально
        self.db.update_crm_card_column(card_id, column)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.move_crm_card(card_id, column)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API move_crm_card: {e}")
                self._queue_operation('update', 'crm_card', card_id, {'column_name': column, '_action': 'move'})
        elif self.api_client:
            self._queue_operation('update', 'crm_card', card_id, {'column_name': column, '_action': 'move'})

        return True

    def get_workflow_state(self, card_id: int) -> Optional[Dict]:
        """Получить состояние workflow карточки (только API)"""
        if not self.api_client:
            _safe_log("[DataAccess] get_workflow_state: API недоступен")
            return None
        try:
            return self.api_client.get_workflow_state(card_id)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка API get_workflow_state: {e}")
            return None

    def workflow_submit(self, card_id: int) -> Optional[Dict]:
        """Отправить карточку на проверку (только API)"""
        if not self.api_client:
            _safe_log("[DataAccess] workflow_submit: API недоступен")
            return None
        try:
            return self.api_client.workflow_submit(card_id)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка API workflow_submit: {e}")
            return None

    def workflow_accept(self, card_id: int) -> Optional[Dict]:
        """Принять карточку (только API)"""
        if not self.api_client:
            _safe_log("[DataAccess] workflow_accept: API недоступен")
            return None
        try:
            return self.api_client.workflow_accept(card_id)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка API workflow_accept: {e}")
            return None

    def workflow_reject(self, card_id: int, stage_name: str = None, reason: str = None,
                        corrections_path: str = None) -> Optional[Dict]:
        """Отклонить карточку (только API).
        stage_name и reason — не передаются на сервер (сервер авто-определяет стадию из карточки).
        corrections_path — путь к папке правок на Яндекс.Диске."""
        if not self.api_client:
            _safe_log("[DataAccess] workflow_reject: API недоступен")
            return None
        try:
            return self.api_client.workflow_reject(card_id, corrections_path=corrections_path or '')
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка API workflow_reject: {e}")
            return None

    def workflow_client_send(self, card_id: int) -> Optional[Dict]:
        """Отправить клиенту (только API)"""
        if not self.api_client:
            _safe_log("[DataAccess] workflow_client_send: API недоступен")
            return None
        try:
            return self.api_client.workflow_client_send(card_id)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка API workflow_client_send: {e}")
            return None

    def workflow_client_ok(self, card_id: int) -> Optional[Dict]:
        """Подтверждение от клиента (только API)"""
        if not self.api_client:
            _safe_log("[DataAccess] workflow_client_ok: API недоступен")
            return None
        try:
            return self.api_client.workflow_client_ok(card_id)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка API workflow_client_ok: {e}")
            return None

    def get_contract_id_by_crm_card(self, card_id: int) -> Optional[int]:
        """Получить ID договора по ID CRM карточки"""
        if self._should_use_api():
            try:
                card = self.api_client.get_crm_card(card_id)
                return card.get('contract_id') if card else None
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_contract_id_by_crm_card, fallback: {e}")
        return self.db.get_contract_id_by_crm_card(card_id)

    # ==================== SUPERVISION КАРТОЧКИ ====================

    def get_supervision_cards_active(self) -> List[Dict]:
        """Получить активные карточки надзора"""
        if self._should_use_api():
            try:
                return self.api_client.get_supervision_cards(status="active")
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_supervision_cards_active, fallback: {e}")
        return self.db.get_supervision_cards_active()

    def get_supervision_cards_archived(self) -> List[Dict]:
        """Получить архивные карточки надзора"""
        if self._should_use_api():
            try:
                return self.api_client.get_supervision_cards(status="archived")
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_supervision_cards_archived, fallback: {e}")
        return self.db.get_supervision_cards_archived()

    def get_supervision_card(self, card_id: int) -> Optional[Dict]:
        """Получить карточку надзора по ID"""
        if self._should_use_api():
            try:
                return self.api_client.get_supervision_card(card_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_supervision_card, fallback: {e}")
        return self.db.get_supervision_card_data(card_id)

    def create_supervision_card(self, card_data) -> Optional[Dict]:
        """Создать карточку надзора (принимает Dict или int contract_id)"""
        if isinstance(card_data, int):
            card_data = {'contract_id': card_data, 'column_name': 'Новый заказ'}
        # Сначала сохраняем локально
        card_id = self.db.add_supervision_card(card_data)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.create_supervision_card(card_data)
                if result:
                    # Защита: API может вернуть list вместо dict
                    if isinstance(result, list):
                        result = result[0] if result else {}
                    server_id = result.get('id') if isinstance(result, dict) else None
                    if server_id and server_id != card_id:
                        self._update_local_id('supervision_cards', card_id, server_id)
                    return result
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API create_supervision_card: {e}")
                self._queue_operation('create', 'supervision_card', card_id, card_data)
        elif self.api_client:
            self._queue_operation('create', 'supervision_card', card_id, card_data)

        return {'id': card_id, **card_data} if card_id else None

    def update_supervision_card(self, card_id: int, updates: Dict) -> bool:
        """Обновить карточку надзора"""
        # Сначала обновляем локально
        self.db.update_supervision_card(card_id, updates)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.update_supervision_card(card_id, updates)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API update_supervision_card: {e}")
                self._queue_operation('update', 'supervision_card', card_id, updates)
        elif self.api_client:
            self._queue_operation('update', 'supervision_card', card_id, updates)

        return True

    def update_supervision_card_column(self, card_id: int, column: str) -> bool:
        """Переместить карточку надзора в другую колонку"""
        # Сначала обновляем локально
        self.db.update_supervision_card_column(card_id, column)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.update_supervision_card(card_id, {'column_name': column})
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API update_supervision_card_column: {e}")
                self._queue_operation('update', 'supervision_card', card_id, {'column_name': column})
        elif self.api_client:
            self._queue_operation('update', 'supervision_card', card_id, {'column_name': column})

        return True

    # ==================== SUPERVISION ACTIONS ====================

    def move_supervision_card(self, card_id: int, column: str) -> bool:
        """Переместить карточку надзора через специализированный метод"""
        # Сначала обновляем локально
        try:
            self.db.update_supervision_card_column(card_id, column)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка DB move_supervision_card: {e}")

        if self.is_online and self.api_client:
            try:
                result = self.api_client.move_supervision_card(card_id, column)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API move_supervision_card: {e}")
                self._queue_operation('update', 'supervision_card', card_id,
                                      {'column_name': column, '_action': 'move'})
        elif self.api_client:
            self._queue_operation('update', 'supervision_card', card_id,
                                  {'column_name': column, '_action': 'move'})

        return True

    def complete_supervision_stage(self, card_id: int, **kwargs) -> Optional[Dict]:
        """Завершить стадию надзора"""
        # Сначала сохраняем локально
        stage_name = kwargs.get('stage_name')
        try:
            self.db.complete_supervision_stage(card_id, stage_name=stage_name)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка DB complete_supervision_stage: {e}")

        if self.is_online and self.api_client:
            try:
                return self.api_client.complete_supervision_stage(card_id, **kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API complete_supervision_stage: {e}")
                self._queue_operation('update', 'supervision_card', card_id,
                                      {'_action': 'complete_stage', 'stage_name': stage_name})
        elif self.api_client:
            self._queue_operation('update', 'supervision_card', card_id,
                                  {'_action': 'complete_stage', 'stage_name': stage_name})

        return {'success': True}

    def reset_supervision_stage_completion(self, card_id: int) -> bool:
        """Сбросить отметку выполнения стадии надзора"""
        # Сначала сбрасываем локально
        try:
            self.db.reset_supervision_stage_completion(card_id)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка DB reset_supervision_stage_completion: {e}")

        if self.is_online and self.api_client:
            try:
                result = self.api_client.reset_supervision_stage_completion(card_id)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API reset_supervision_stage_completion: {e}")
                self._queue_operation('update', 'supervision_card', card_id,
                                      {'_action': 'reset_stage_completion'})
        elif self.api_client:
            self._queue_operation('update', 'supervision_card', card_id,
                                  {'_action': 'reset_stage_completion'})

        return True

    def pause_supervision_card(self, card_id: int, reason: str = None, employee_id: int = None) -> Optional[Dict]:
        """Поставить карточку надзора на паузу.
        employee_id — используется только в offline (DB). В online сервер определяет из JWT."""
        # Сначала сохраняем локально
        try:
            self.db.pause_supervision_card(card_id, reason or '', employee_id or 0)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка DB pause_supervision_card: {e}")

        if self.is_online and self.api_client:
            try:
                return self.api_client.pause_supervision_card(card_id, reason or '')
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API pause_supervision_card: {e}")
                self._queue_operation('update', 'supervision_card', card_id,
                                      {'_action': 'pause', 'reason': reason or ''})
        elif self.api_client:
            self._queue_operation('update', 'supervision_card', card_id,
                                  {'_action': 'pause', 'reason': reason or ''})

        return {'success': True}

    def resume_supervision_card(self, card_id: int, employee_id: int = None) -> Optional[Dict]:
        """Возобновить карточку надзора после паузы"""
        # Сначала возобновляем локально
        try:
            self.db.resume_supervision_card(card_id, employee_id)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка DB resume_supervision_card: {e}")

        if self.is_online and self.api_client:
            try:
                return self.api_client.resume_supervision_card(card_id, employee_id)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API resume_supervision_card: {e}")
                self._queue_operation('update', 'supervision_card', card_id,
                                      {'_action': 'resume', 'employee_id': employee_id})
        elif self.api_client:
            self._queue_operation('update', 'supervision_card', card_id,
                                  {'_action': 'resume', 'employee_id': employee_id})

        return {'success': True}

    def delete_supervision_order(self, contract_id: int, supervision_card_id: int = None) -> bool:
        """Удалить выезд из карточки надзора"""
        # Сначала удаляем локально
        try:
            self.db.delete_supervision_order(contract_id, supervision_card_id)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка DB delete_supervision_order: {e}")

        if self.is_online and self.api_client:
            try:
                result = self.api_client.delete_supervision_order(contract_id, supervision_card_id)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API delete_supervision_order: {e}")
                self._queue_operation('delete', 'supervision_card', supervision_card_id or contract_id,
                                      {'contract_id': contract_id, '_action': 'delete_order'})
        elif self.api_client:
            self._queue_operation('delete', 'supervision_card', supervision_card_id or contract_id,
                                  {'contract_id': contract_id, '_action': 'delete_order'})

        return True

    def get_contract_id_by_supervision_card(self, card_id: int) -> Optional[int]:
        """Получить ID договора по ID карточки надзора"""
        if self.api_client:
            try:
                return self.api_client.get_contract_id_by_supervision_card(card_id)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API get_contract_id_by_supervision_card: {e}")
        try:
            return self.db.get_contract_id_by_supervision_card(card_id)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка DB get_contract_id_by_supervision_card: {e}")
            return None

    def get_supervision_addresses(self) -> List[str]:
        """Получить список адресов карточек надзора"""
        if self.api_client:
            try:
                return self.api_client.get_supervision_addresses()
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API get_supervision_addresses: {e}")
        try:
            return self.db.get_supervision_addresses()
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка DB get_supervision_addresses: {e}")
            return []

    def get_supervision_statistics_filtered(self, period=None, year=None, quarter=None, month=None,
                                            address_id=None, stage=None, executor_id=None,
                                            manager_id=None, status=None) -> Dict:
        """Получить отфильтрованную статистику надзора"""
        if self.api_client:
            try:
                return self.api_client.get_supervision_statistics_filtered(
                    year=year, quarter=quarter, month=month,
                    agent_type=stage, city=None, address=address_id,
                    executor_id=executor_id, manager_id=manager_id, status=status)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API get_supervision_statistics_filtered: {e}")
        try:
            return self.db.get_supervision_statistics_filtered(
                period, year, quarter, month, address_id, stage, executor_id, manager_id, status)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка DB get_supervision_statistics_filtered: {e}")
            return {}

    # ==================== ПЛАТЕЖИ ====================

    def get_payments_for_contract(self, contract_id: int) -> List[Dict]:
        """Получить платежи по договору"""
        if self._should_use_api():
            try:
                return self.api_client.get_payments_for_contract(contract_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_payments_for_contract, fallback: {e}")
        return self.db.get_payments_for_contract(contract_id)

    def create_payment(self, payment_data: Dict) -> Optional[Dict]:
        """Создать платёж"""
        # Сначала сохраняем локально
        payment_id = self.db.add_payment(payment_data)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.create_payment(payment_data)
                if result:
                    # Защита: API может вернуть list вместо dict
                    if isinstance(result, list):
                        result = result[0] if result else {}
                    server_id = result.get('id') if isinstance(result, dict) else None
                    if server_id and server_id != payment_id:
                        self._update_local_id('payments', payment_id, server_id)
                    return result
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API create_payment: {e}")
                self._queue_operation('create', 'payment', payment_id, payment_data)
        elif self.api_client:
            self._queue_operation('create', 'payment', payment_id, payment_data)

        return {'id': payment_id, **payment_data} if payment_id else None

    def update_payment(self, payment_id: int, payment_data: Dict) -> bool:
        """Обновить платёж"""
        # Сначала обновляем локально
        self.db.update_payment(payment_id, payment_data)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.update_payment(payment_id, payment_data)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API update_payment: {e}")
                self._queue_operation('update', 'payment', payment_id, payment_data)
        elif self.api_client:
            self._queue_operation('update', 'payment', payment_id, payment_data)

        return True

    def delete_payment(self, payment_id: int) -> bool:
        """Удалить платёж"""
        # Сначала удаляем локально
        self.db.delete_payment(payment_id)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.delete_payment(payment_id)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API delete_payment: {e}")
                self._queue_operation('delete', 'payment', payment_id, {})
        elif self.api_client:
            self._queue_operation('delete', 'payment', payment_id, {})

        return True

    def get_payment(self, payment_id: int) -> Optional[Dict]:
        """Получить платёж по ID"""
        if self._should_use_api():
            try:
                return self.api_client.get_payment(payment_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_payment, fallback: {e}")
        return self.db.get_payment(payment_id)

    def get_payments_by_type(self, payment_type: str, project_type_filter: str = None) -> List[Dict]:
        """Получить платежи по типу"""
        if self._should_use_api():
            try:
                return self.api_client.get_payments_by_type(payment_type, project_type_filter=project_type_filter)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_payments_by_type, fallback: {e}")
        return self.db.get_payments_by_type(payment_type, project_type_filter)

    def get_payments_by_supervision_card(self, card_id: int) -> List[Dict]:
        """Получить платежи по карточке надзора"""
        if self._should_use_api():
            try:
                return self.api_client.get_payments_by_supervision_card(card_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_payments_by_supervision_card, fallback: {e}")
        return self.db.get_payments_by_supervision_card(card_id)

    def get_payments_for_supervision(self, contract_id: int) -> List[Dict]:
        """Получить платежи надзора по договору"""
        if self._should_use_api():
            try:
                return self.api_client.get_payments_for_supervision(contract_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_payments_for_supervision, fallback: {e}")
        return self.db.get_payments_for_supervision(contract_id)

    def get_payments_for_crm(self, contract_id: int) -> List[Dict]:
        """Получить платежи CRM по договору"""
        if self._should_use_api():
            try:
                return self.api_client.get_payments_for_crm(contract_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_payments_for_crm, fallback: {e}")
        return self.db.get_payments_for_crm(contract_id)

    def get_year_payments(self, year: int, include_null_month: bool = False) -> List[Dict]:
        """Получить платежи за год"""
        if self._should_use_api():
            try:
                return self.api_client.get_year_payments(year, include_null_month=include_null_month)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_year_payments, fallback: {e}")
        return self.db.get_year_payments(year, include_null_month)

    def mark_payment_as_paid(self, payment_id: int, employee_id: int = None) -> bool:
        """Отметить платёж как оплаченный"""
        # Сначала отмечаем локально
        self.db.mark_payment_as_paid(payment_id, employee_id or 0)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.mark_payment_as_paid(payment_id, employee_id or 0)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API mark_payment_as_paid: {e}")
                self._queue_operation('update', 'payment', payment_id,
                                      {'_action': 'mark_paid', 'employee_id': employee_id})
        elif self.api_client:
            self._queue_operation('update', 'payment', payment_id,
                                  {'_action': 'mark_paid', 'employee_id': employee_id})

        return True

    def create_payment_record(self, contract_id: int, employee_id: int, role: str,
                             stage_name: str = None, payment_type: str = 'Полная оплата',
                             report_month: str = None, crm_card_id: int = None,
                             supervision_card_id: int = None) -> Optional[Dict]:
        """Создать платёж с расширенными параметрами"""
        payment_data = {
            'contract_id': contract_id, 'employee_id': employee_id, 'role': role,
            'stage_name': stage_name, 'payment_type': payment_type,
            'report_month': report_month, 'crm_card_id': crm_card_id,
            'supervision_card_id': supervision_card_id
        }
        # Сначала сохраняем локально
        local_result = None
        try:
            local_result = self.db.create_payment_record(
                contract_id, employee_id, role, stage_name=stage_name,
                payment_type=payment_type, report_month=report_month,
                crm_card_id=crm_card_id, supervision_card_id=supervision_card_id)
        except Exception as e:
            _safe_log(f"[DataAccess] DB error create_payment_record: {e}")

        if self.is_online and self.api_client:
            try:
                result = self.api_client.create_payment_record(
                    contract_id, employee_id, role, stage_name=stage_name,
                    payment_type=payment_type, report_month=report_month,
                    crm_card_id=crm_card_id, supervision_card_id=supervision_card_id)
                return result
            except Exception as e:
                _safe_log(f"[DataAccess] API error create_payment_record: {e}")
                payment_id = local_result.get('id') if isinstance(local_result, dict) else 0
                self._queue_operation('create', 'payment', payment_id, payment_data)
        elif self.api_client:
            payment_id = local_result.get('id') if isinstance(local_result, dict) else 0
            self._queue_operation('create', 'payment', payment_id, payment_data)

        return local_result

    def update_payment_manual(self, payment_id: int, amount: float, report_month: str = None) -> bool:
        """Обновить сумму платежа вручную"""
        # Сначала обновляем локально (включая report_month)
        self.db.update_payment_manual(payment_id, amount, report_month=report_month)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.update_payment_manual(payment_id, amount, report_month)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API update_payment_manual: {e}")
                self._queue_operation('update', 'payment', payment_id,
                                      {'_action': 'manual_amount', 'amount': amount,
                                       'report_month': report_month})
        elif self.api_client:
            self._queue_operation('update', 'payment', payment_id,
                                  {'_action': 'manual_amount', 'amount': amount,
                                   'report_month': report_month})

        return True

    def calculate_payment_amount(self, contract_id, employee_id, role,
                                  stage_name=None, supervision_card_id=None) -> Optional[Dict]:
        """Рассчитать сумму платежа"""
        if self._should_use_api():
            try:
                return self.api_client.calculate_payment_amount(
                    contract_id, employee_id, role,
                    stage_name=stage_name, supervision_card_id=supervision_card_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error calculate_payment_amount, fallback: {e}")
        return self.db.calculate_payment_amount(
            contract_id, employee_id, role,
            stage_name=stage_name, supervision_card_id=supervision_card_id)

    def recalculate_payments(self, contract_id: int = None, role: str = None) -> Optional[Dict]:
        """Пересчитать платежи (только API)"""
        if self.api_client:
            try:
                return self.api_client.recalculate_payments(contract_id=contract_id, role=role)
            except Exception as e:
                _safe_log(f"[DataAccess] API error recalculate_payments: {e}")
                return None
        _safe_log("[DataAccess] recalculate_payments: API недоступен")
        return None

    def set_payments_report_month(self, contract_id: int, month: str) -> bool:
        """Установить отчётный месяц для платежей (только API)"""
        if self.api_client:
            try:
                result = self.api_client.set_payments_report_month(contract_id, month)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] API error set_payments_report_month: {e}")
                return False
        _safe_log("[DataAccess] set_payments_report_month: API недоступен")
        return False

    # ==================== ИСТОРИЯ ДЕЙСТВИЙ ====================

    def get_action_history(self, entity_type: str, entity_id: int) -> List[Dict]:
        """Получить историю действий"""
        if self._should_use_api():
            try:
                return self.api_client.get_action_history(entity_type, entity_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_action_history, fallback: {e}")
        return self.db.get_action_history(entity_type, entity_id)

    def add_action_history(self, user_id: int, action_type: str, entity_type: str,
                          entity_id: int, description: str = None) -> bool:
        """Добавить запись в историю действий"""
        history_data = {
            'user_id': user_id,
            'action_type': action_type,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'description': description
        }
        # Сначала сохраняем локально
        self.db.add_action_history(user_id, action_type, entity_type, entity_id, description)

        if self.is_online and self.api_client:
            try:
                self.api_client.create_action_history(history_data)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API add_action_history: {e}")
                self._queue_operation('create', 'action_history', entity_id, history_data)
        elif self.api_client:
            self._queue_operation('create', 'action_history', entity_id, history_data)

        return True

    # ==================== ИСТОРИЯ НАДЗОРА ====================

    def get_supervision_history(self, card_id: int) -> List[Dict]:
        """Получить историю карточки надзора"""
        if self._should_use_api():
            try:
                return self.api_client.get_supervision_history(card_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_supervision_history, fallback: {e}")
        return self.db.get_supervision_history(card_id)

    def add_supervision_history(self, card_id: int, user_id: int, action_type: str,
                               description: str = None) -> bool:
        """Добавить запись в историю надзора"""
        history_data = {
            'card_id': card_id,
            'entry_type': action_type,
            'message': description or "",
            'employee_id': user_id
        }
        # Сначала сохраняем локально
        self.db.add_supervision_history(card_id, action_type, description or "", user_id)

        if self.is_online and self.api_client:
            try:
                self.api_client.add_supervision_history(
                    card_id, entry_type=action_type,
                    message=description or "", employee_id=user_id)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API add_supervision_history: {e}")
                self._queue_operation('create', 'supervision_history', card_id, history_data)
        elif self.api_client:
            self._queue_operation('create', 'supervision_history', card_id, history_data)

        return True

    # ==================== СТАВКИ ====================

    def get_rates(self, project_type: str = None, role: str = None) -> List[Dict]:
        """Получить ставки"""
        if self._should_use_api():
            try:
                return self.api_client.get_rates(project_type, role)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_rates, fallback: {e}")
        return self.db.get_rates(project_type, role)

    def get_rate(self, rate_id: int) -> Optional[Dict]:
        """Получить ставку по ID"""
        if self._should_use_api():
            try:
                return self.api_client.get_rate(rate_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_rate, fallback: {e}")
        return self.db.get_rate_by_id(rate_id)

    def create_rate(self, rate_data: Dict) -> Optional[Dict]:
        """Создать ставку"""
        # Сначала сохраняем локально
        rate_id = self.db.add_rate(rate_data)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.create_rate(rate_data)
                if result:
                    # Защита: API может вернуть list вместо dict
                    if isinstance(result, list):
                        result = result[0] if result else {}
                    server_id = result.get('id') if isinstance(result, dict) else None
                    if server_id and server_id != rate_id:
                        self._update_local_id('rates', rate_id, server_id)
                    return result
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API create_rate: {e}")
                self._queue_operation('create', 'rate', rate_id, rate_data)
        elif self.api_client:
            self._queue_operation('create', 'rate', rate_id, rate_data)

        return {'id': rate_id, **rate_data} if rate_id else None

    def update_rate(self, rate_id: int, rate_data: Dict) -> bool:
        """Обновить ставку"""
        # Сначала обновляем локально
        self.db.update_rate(rate_id, rate_data)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.update_rate(rate_id, rate_data)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API update_rate: {e}")
                self._queue_operation('update', 'rate', rate_id, rate_data)
        elif self.api_client:
            self._queue_operation('update', 'rate', rate_id, rate_data)

        return True

    def delete_rate(self, rate_id: int) -> bool:
        """Удалить ставку"""
        # Сначала удаляем локально
        self.db.delete_rate(rate_id)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.delete_rate(rate_id)
                return result if isinstance(result, bool) else True
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API delete_rate: {e}")
                self._queue_operation('delete', 'rate', rate_id, {})
        elif self.api_client:
            self._queue_operation('delete', 'rate', rate_id, {})

        return True

    def get_template_rates(self, role: str = None) -> List[Dict]:
        """Получить шаблонные ставки"""
        if self._should_use_api():
            try:
                return self.api_client.get_template_rates(role)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_template_rates, fallback: {e}")
        return self.db.get_template_rates(role)

    def save_template_rate(self, role: str, area_from: float, area_to: float, price: float) -> Optional[Dict]:
        """Сохранить шаблонную ставку (только API)"""
        if self.api_client:
            try:
                return self.api_client.save_template_rate(role, area_from, area_to, price)
            except Exception as e:
                _safe_log(f"[DataAccess] API error save_template_rate: {e}")
                return None
        _safe_log("[DataAccess] save_template_rate: API недоступен")
        return None

    def save_individual_rate(self, role: str, rate_per_m2: float, stage_name: str = None) -> Optional[Dict]:
        """Сохранить индивидуальную ставку (только API)"""
        if self.api_client:
            try:
                return self.api_client.save_individual_rate(role, rate_per_m2, stage_name)
            except Exception as e:
                _safe_log(f"[DataAccess] API error save_individual_rate: {e}")
                return None
        _safe_log("[DataAccess] save_individual_rate: API недоступен")
        return None

    def delete_individual_rate(self, role: str, stage_name: str = None) -> bool:
        """Удалить индивидуальную ставку (только API)"""
        if self.api_client:
            try:
                result = self.api_client.delete_individual_rate(role, stage_name)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] API error delete_individual_rate: {e}")
                return False
        _safe_log("[DataAccess] delete_individual_rate: API недоступен")
        return False

    def save_surveyor_rate(self, city: str, price: float) -> Optional[Dict]:
        """Сохранить ставку геодезиста (только API)"""
        if self.api_client:
            try:
                return self.api_client.save_surveyor_rate(city, price)
            except Exception as e:
                _safe_log(f"[DataAccess] API error save_surveyor_rate: {e}")
                return None
        _safe_log("[DataAccess] save_surveyor_rate: API недоступен")
        return None

    def save_supervision_rate(self, stage: str, exec_rate: float, mgr_rate: float) -> Optional[Dict]:
        """Сохранить ставку надзора (только API)"""
        if self.api_client:
            try:
                return self.api_client.save_supervision_rate(stage, exec_rate, mgr_rate)
            except Exception as e:
                _safe_log(f"[DataAccess] API error save_supervision_rate: {e}")
                return None
        _safe_log("[DataAccess] save_supervision_rate: API недоступен")
        return None

    # ==================== ЗАРПЛАТЫ ====================

    def get_salaries(self, report_month: str = None, employee_id: int = None) -> List[Dict]:
        """Получить зарплаты"""
        if self._should_use_api():
            try:
                return self.api_client.get_salaries(report_month, employee_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_salaries, fallback: {e}")
        return self.db.get_salaries(report_month, employee_id)

    def get_salary(self, salary_id: int) -> Optional[Dict]:
        """Получить зарплату по ID"""
        if self._should_use_api():
            try:
                return self.api_client.get_salary(salary_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_salary, fallback: {e}")
        return self.db.get_salary_by_id(salary_id)

    def create_salary(self, salary_data: Dict) -> Optional[Dict]:
        """Создать запись о зарплате"""
        # Сначала сохраняем локально
        salary_id = self.db.add_salary(salary_data)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.create_salary(salary_data)
                if result:
                    # Защита: API может вернуть list вместо dict
                    if isinstance(result, list):
                        result = result[0] if result else {}
                    server_id = result.get('id') if isinstance(result, dict) else None
                    if server_id and server_id != salary_id:
                        self._update_local_id('salaries', salary_id, server_id)
                    return result
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API create_salary: {e}")
                self._queue_operation('create', 'salary', salary_id, salary_data)
        elif self.api_client:
            self._queue_operation('create', 'salary', salary_id, salary_data)

        return {'id': salary_id, **salary_data} if salary_id else None

    def update_salary(self, salary_id: int, salary_data: Dict) -> bool:
        """Обновить запись о зарплате"""
        # Сначала обновляем локально
        self.db.update_salary(salary_id, salary_data)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.update_salary(salary_id, salary_data)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API update_salary: {e}")
                self._queue_operation('update', 'salary', salary_id, salary_data)
        elif self.api_client:
            self._queue_operation('update', 'salary', salary_id, salary_data)

        return True

    def delete_salary(self, salary_id: int) -> bool:
        """Удалить запись о зарплате"""
        # Сначала удаляем локально
        self.db.delete_salary(salary_id)

        if self.is_online and self.api_client:
            try:
                return self.api_client.delete_salary(salary_id)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API delete_salary: {e}")
                self._queue_operation('delete', 'salary', salary_id, {})
        elif self.api_client:
            self._queue_operation('delete', 'salary', salary_id, {})

        return True

    # ==================== АГЕНТЫ ====================

    def get_all_agents(self) -> List[Dict]:
        """Получить всех агентов (с id, name, color)"""
        if self.api_client:
            try:
                return self.api_client.get_all_agents()
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_all_agents, fallback: {e}")
        return self.db.get_all_agents()

    def get_agent_color(self, agent_name: str) -> Optional[str]:
        """Получить цвет агента.
        Сначала ищем в локальной БД (кешированный lookup, мгновенно).
        Fallback на API только если в локальной БД нет данных.
        Причина: SQLite agents.name хранит краткое имя (ФЕСТИВАЛЬ),
        а API возвращает full_name сотрудника — они могут не совпадать.
        """
        # Сначала локальная БД (кешированный dict, O(1))
        color = self.db.get_agent_color(agent_name)
        if color:
            return color
        # Fallback на API только если локально не нашли
        if self.api_client:
            try:
                return self.api_client.get_agent_color(agent_name)
            except Exception:
                pass
        return None

    def add_agent(self, name: str, color: str = None) -> Optional[Dict]:
        """Добавить агента"""
        # Сначала сохраняем локально
        local_result = None
        try:
            local_result = self.db.add_agent(name, color)
        except Exception as e:
            _safe_log(f"[DataAccess] DB add_agent: {e}")

        if self.is_online and self.api_client:
            try:
                return self.api_client.add_agent(name, color)
            except Exception as e:
                _safe_log(f"[DataAccess] API add_agent: {e}")
                self._queue_operation('create', 'agent', 0, {'name': name, 'color': color})
        elif self.api_client:
            self._queue_operation('create', 'agent', 0, {'name': name, 'color': color})

        return local_result

    def update_agent_color(self, name: str, color: str) -> bool:
        """Обновить цвет агента"""
        # Сначала обновляем локально
        try:
            self.db.update_agent_color(name, color)
        except Exception as e:
            _safe_log(f"[DataAccess] DB update_agent_color: {e}")

        if self.is_online and self.api_client:
            try:
                return self.api_client.update_agent_color(name, color)
            except Exception as e:
                _safe_log(f"[DataAccess] API update_agent_color: {e}")
                self._queue_operation('update', 'agent', 0, {'name': name, 'color': color})
        elif self.api_client:
            self._queue_operation('update', 'agent', 0, {'name': name, 'color': color})

        return True

    def delete_agent(self, agent_id: int) -> bool:
        """Удалить агента (мягкое удаление)"""
        if self.api_client:
            try:
                return self.api_client.delete_agent(agent_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API delete_agent error: {e}")
        if self.db:
            try:
                return self.db.delete_agent(agent_id)
            except Exception as e:
                _safe_log(f"[DataAccess] DB delete_agent error: {e}")
        return False

    def get_agent_types(self) -> List[str]:
        """Получить типы агентов"""
        if self.api_client:
            try:
                return self.api_client.get_agent_types()
            except Exception as e:
                _safe_log(f"[DataAccess] API get_agent_types: {e}")
        if self.db:
            try:
                return self.db.get_agent_types()
            except Exception as e:
                _safe_log(f"[DataAccess] DB get_agent_types: {e}")
        return []

    # ==================== ГОРОДА ====================

    def get_all_cities(self) -> List[Dict]:
        """Получить все города"""
        if self.api_client:
            try:
                cities = self.api_client.get_all_cities()
                if cities:
                    return cities
            except Exception as e:
                _safe_log(f"[DataAccess] API get_all_cities error, fallback: {e}")
        # Fallback на локальную БД
        if self.db:
            try:
                return self.db.get_all_cities()
            except Exception as e:
                _safe_log(f"[DataAccess] DB get_all_cities error: {e}")
        # Последний fallback — config.py
        try:
            from config import CITIES
            return [{"id": i, "name": c, "status": "активный"} for i, c in enumerate(CITIES, 1)]
        except Exception:
            return []

    def add_city(self, name: str) -> bool:
        """Добавить город"""
        result = False
        if self.db:
            try:
                result = self.db.add_city(name)
            except Exception as e:
                _safe_log(f"[DataAccess] DB add_city error: {e}")
        if self.api_client:
            try:
                api_result = self.api_client.add_city(name)
                result = result or api_result
            except Exception as e:
                _safe_log(f"[DataAccess] API add_city error: {e}")
                if not result:
                    self._queue_operation('create', 'city', None, {'name': name})
                    result = True
        return result

    def delete_city(self, city_id: int) -> bool:
        """Удалить город"""
        if self.api_client:
            try:
                return self.api_client.delete_city(city_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API delete_city error: {e}")
        if self.db:
            try:
                return self.db.delete_city(city_id)
            except Exception as e:
                _safe_log(f"[DataAccess] DB delete_city error: {e}")
        return False

    # ==================== СТАДИИ ====================

    def get_stage_history(self, card_id: int) -> List[Dict]:
        """Получить историю стадий"""
        if self._should_use_api():
            try:
                return self.api_client.get_stage_history(card_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_stage_history, fallback: {e}")
        return self.db.get_stage_history(card_id)

    def get_accepted_stages(self, card_id: int) -> List[Dict]:
        """Получить принятые стадии"""
        if self._should_use_api():
            try:
                return self.api_client.get_accepted_stages(card_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API get_accepted_stages, fallback: {e}")
        try:
            return self.db.get_accepted_stages(card_id)
        except Exception as e:
            _safe_log(f"[DataAccess] DB get_accepted_stages: {e}")
            return []

    def get_submitted_stages(self, card_id: int) -> List[Dict]:
        """Получить сданные стадии"""
        if self._should_use_api():
            try:
                return self.api_client.get_submitted_stages(card_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API get_submitted_stages, fallback: {e}")
        try:
            return self.db.get_submitted_stages(card_id)
        except Exception as e:
            _safe_log(f"[DataAccess] DB get_submitted_stages: {e}")
            return []

    def update_stage_executor_deadline(self, card_id: int, stage_name: str,
                                       deadline: str = None, executor_id: int = None) -> bool:
        """Обновить дедлайн исполнителя стадии"""
        # Сначала сохраняем локально
        self.db.update_stage_executor_deadline(card_id, stage_name, deadline,
                                               executor_id=executor_id)

        if self.is_online and self.api_client:
            try:
                update_data = {}
                if deadline is not None:
                    update_data['deadline'] = deadline
                if executor_id is not None:
                    update_data['executor_id'] = executor_id
                result = self.api_client.update_stage_executor(card_id, stage_name, update_data)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] API error update_stage_executor_deadline: {e}")
                self._queue_operation('update', 'stage_executor', card_id,
                                      {'card_id': card_id, 'stage_name': stage_name,
                                       'deadline': deadline, 'executor_id': executor_id,
                                       '_action': 'update'})
        elif self.api_client:
            self._queue_operation('update', 'stage_executor', card_id,
                                  {'card_id': card_id, 'stage_name': stage_name,
                                   'deadline': deadline, 'executor_id': executor_id,
                                   '_action': 'update'})

        return True

    # ==================== STAGE EXECUTORS ====================

    def assign_stage_executor(self, card_id: int, data: Dict) -> Optional[Dict]:
        """Назначить исполнителя на стадию"""
        # Сначала сохраняем локально
        try:
            self.db.assign_stage_executor(
                card_id,
                data.get('stage_name', ''),
                data.get('executor_id'),
                data.get('assigned_by'),
                data.get('deadline'))
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка DB assign_stage_executor: {e}")

        if self.is_online and self.api_client:
            try:
                return self.api_client.assign_stage_executor(card_id, data)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API assign_stage_executor: {e}")
                self._queue_operation('create', 'stage_executor', card_id,
                                      {'card_id': card_id, '_action': 'assign', **data})
        elif self.api_client:
            self._queue_operation('create', 'stage_executor', card_id,
                                  {'card_id': card_id, '_action': 'assign', **data})

        return {'success': True}

    def complete_stage_for_executor(self, card_id: int, stage_name: str, executor_id: int = None) -> Optional[Dict]:
        """Отметить стадию выполненной для исполнителя"""
        # Сначала сохраняем локально
        try:
            self.db.complete_stage_for_executor(card_id, stage_name, executor_id)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка DB complete_stage_for_executor: {e}")

        if self.is_online and self.api_client:
            try:
                result = self.api_client.complete_stage_for_executor(card_id, stage_name, executor_id)
                if isinstance(result, bool):
                    return {'success': result} if result else None
                return result
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API complete_stage_for_executor: {e}")
                self._queue_operation('update', 'stage_executor', card_id,
                                      {'card_id': card_id, 'stage_name': stage_name,
                                       'executor_id': executor_id, '_action': 'complete'})
        elif self.api_client:
            self._queue_operation('update', 'stage_executor', card_id,
                                  {'card_id': card_id, 'stage_name': stage_name,
                                   'executor_id': executor_id, '_action': 'complete'})

        return {'success': True}

    def get_incomplete_stage_executors(self, card_id: int, stage_name: str) -> list:
        """S-05: Получить незавершённых исполнителей стадии"""
        try:
            return self.db.get_incomplete_stage_executors(card_id, stage_name)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка get_incomplete_stage_executors: {e}")
            return []

    def get_stage_completion_info(self, card_id: int, stage_name: str) -> dict:
        """S-05: Получить информацию о завершении стадии"""
        try:
            return self.db.get_stage_completion_info(card_id, stage_name)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка get_stage_completion_info: {e}")
            return {'stage': None, 'approval': None}

    def auto_accept_stage(self, card_id: int, stage_name: str, accepted_by_id: int, project_type: str = None) -> int:
        """S-05: Автоматическое принятие стадии руководителем"""
        try:
            return self.db.auto_accept_stage(card_id, stage_name, accepted_by_id, project_type)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка auto_accept_stage: {e}")
            return 0

    def reset_stage_completion(self, card_id: int) -> bool:
        """Сбросить отметку выполнения стадии"""
        # Сначала сбрасываем локально
        try:
            self.db.reset_stage_completion(card_id)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка DB reset_stage_completion: {e}")

        if self.is_online and self.api_client:
            try:
                result = self.api_client.reset_stage_completion(card_id)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API reset_stage_completion: {e}")
                self._queue_operation('update', 'stage_executor', card_id,
                                      {'card_id': card_id, '_action': 'reset'})
        elif self.api_client:
            self._queue_operation('update', 'stage_executor', card_id,
                                  {'card_id': card_id, '_action': 'reset'})

        return True

    def reset_designer_completion(self, card_id: int) -> bool:
        """Сбросить отметку выполнения дизайнера"""
        # Сначала сбрасываем локально
        try:
            self.db.reset_designer_completion(card_id)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка DB reset_designer_completion: {e}")

        if self.is_online and self.api_client:
            try:
                result = self.api_client.reset_designer_completion(card_id)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API reset_designer_completion: {e}")
                self._queue_operation('update', 'stage_executor', card_id,
                                      {'card_id': card_id, '_action': 'reset_designer'})
        elif self.api_client:
            self._queue_operation('update', 'stage_executor', card_id,
                                  {'card_id': card_id, '_action': 'reset_designer'})

        return True

    def reset_draftsman_completion(self, card_id: int) -> bool:
        """Сбросить отметку выполнения чертёжника"""
        # Сначала сбрасываем локально
        try:
            self.db.reset_draftsman_completion(card_id)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка DB reset_draftsman_completion: {e}")

        if self.is_online and self.api_client:
            try:
                result = self.api_client.reset_draftsman_completion(card_id)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API reset_draftsman_completion: {e}")
                self._queue_operation('update', 'stage_executor', card_id,
                                      {'card_id': card_id, '_action': 'reset_draftsman'})
        elif self.api_client:
            self._queue_operation('update', 'stage_executor', card_id,
                                  {'card_id': card_id, '_action': 'reset_draftsman'})

        return True

    def reset_approval_stages(self, card_id: int) -> bool:
        """Сбросить стадии согласования"""
        # Сначала сбрасываем локально
        try:
            self.db.reset_approval_stages(card_id)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка DB reset_approval_stages: {e}")

        if self.is_online and self.api_client:
            try:
                result = self.api_client.reset_approval_stages(card_id)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API reset_approval_stages: {e}")
                self._queue_operation('update', 'stage_executor', card_id,
                                      {'card_id': card_id, '_action': 'reset_approval'})
        elif self.api_client:
            self._queue_operation('update', 'stage_executor', card_id,
                                  {'card_id': card_id, '_action': 'reset_approval'})

        return True

    def save_manager_acceptance(self, card_id: int, stage_name: str,
                               executor_name: str, manager_id: int) -> Optional[Dict]:
        """Сохранить приёмку менеджера"""
        # Сначала сохраняем локально
        try:
            self.db.save_manager_acceptance(card_id, stage_name, executor_name, manager_id)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка DB save_manager_acceptance: {e}")

        if self.is_online and self.api_client:
            try:
                result = self.api_client.save_manager_acceptance(card_id, stage_name, executor_name, manager_id)
                if isinstance(result, bool):
                    return {'success': result} if result else None
                return result
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API save_manager_acceptance: {e}")
                self._queue_operation('update', 'stage_executor', card_id,
                                      {'card_id': card_id, 'stage_name': stage_name,
                                       'executor_name': executor_name, 'manager_id': manager_id,
                                       '_action': 'accept'})
        elif self.api_client:
            self._queue_operation('update', 'stage_executor', card_id,
                                  {'card_id': card_id, 'stage_name': stage_name,
                                   'executor_name': executor_name, 'manager_id': manager_id,
                                   '_action': 'accept'})

        return {'success': True}

    def get_previous_executor_by_position(self, card_id: int, position: str) -> Optional[Dict]:
        """Получить предыдущего исполнителя по должности (только локальная БД)"""
        try:
            return self.db.get_previous_executor_by_position(card_id, position)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка DB get_previous_executor_by_position: {e}")
            return None

    def get_crm_statistics_filtered(self, project_type=None, period=None, year=None,
                                     quarter=None, month=None, project_id=None,
                                     executor_id=None, stage_name=None, status_filter=None) -> Dict:
        """Получить отфильтрованную статистику CRM"""
        if self.api_client:
            try:
                return self.api_client.get_crm_statistics_filtered(
                    project_type, period, year, quarter=quarter, month=month,
                    project_id=project_id, executor_id=executor_id,
                    stage_name=stage_name, status_filter=status_filter)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API get_crm_statistics_filtered: {e}")
        try:
            return self.db.get_crm_statistics_filtered(
                project_type, period, year, quarter, month, project_id,
                executor_id, stage_name, status_filter)
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка DB get_crm_statistics_filtered: {e}")
            return {}

    # ==================== ФАЙЛЫ ====================

    def get_contract_files(self, contract_id: int, stage: str = None) -> List[Dict]:
        """Получить файлы договора"""
        if self._should_use_api():
            try:
                return self.api_client.get_contract_files(contract_id, stage)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_contract_files, fallback: {e}")
        return self.db.get_contract_files(contract_id, stage)

    def create_file_record(self, file_data: Dict) -> Optional[Dict]:
        """Создать запись о файле"""
        # Сначала сохраняем локально
        file_id = self.db.add_contract_file(file_data)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.create_file_record(file_data)
                if result:
                    # Защита: API может вернуть list вместо dict
                    if isinstance(result, list):
                        result = result[0] if result else {}
                    server_id = result.get('id') if isinstance(result, dict) else None
                    if server_id and server_id != file_id:
                        self._update_local_id('project_files', file_id, server_id)
                    return result
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API create_file_record: {e}")
                self._queue_operation('create', 'project_file', file_id, file_data)
        elif self.api_client:
            self._queue_operation('create', 'project_file', file_id, file_data)

        return {'id': file_id, **file_data} if file_id else None

    def delete_file_record(self, file_id: int) -> bool:
        """Удалить запись о файле"""
        # Сначала удаляем локально
        self.db.delete_project_file(file_id)

        if self.is_online and self.api_client:
            try:
                return self.api_client.delete_file_record(file_id)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API delete_file_record: {e}")
                self._queue_operation('delete', 'project_file', file_id, {})
        elif self.api_client:
            self._queue_operation('delete', 'project_file', file_id, {})

        return True

    def get_project_files(self, contract_id: int, stage: str = None) -> List[Dict]:
        """Получить файлы проекта"""
        if self._should_use_api():
            try:
                return self.api_client.get_project_files(contract_id, stage)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_project_files, fallback: {e}")
        return self.db.get_project_files(contract_id, stage)

    def add_project_file(self, data: Dict = None, **kwargs) -> Optional[Dict]:
        """Добавить файл проекта (принимает Dict или именованные аргументы)"""
        if data is None:
            data = kwargs
        # Сначала сохраняем локально
        local_result = None
        try:
            local_result = self.db.add_project_file(**data)
        except Exception as e:
            _safe_log(f"[DataAccess] DB error add_project_file: {e}")

        file_id = (local_result.get('id') if isinstance(local_result, dict) else local_result) if local_result else 0

        if self.is_online and self.api_client:
            try:
                result = self.api_client.add_project_file(**data)
                return result
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API add_project_file: {e}")
                self._queue_operation('create', 'project_file', file_id, data)
        elif self.api_client:
            self._queue_operation('create', 'project_file', file_id, data)

        return local_result

    def scan_contract_files(self, contract_id: int, scope: str = None) -> Optional[Dict]:
        """Сканировать файлы договора на Яндекс.Диске (только API)"""
        if self.api_client:
            try:
                return self.api_client.scan_contract_files(contract_id, scope)
            except Exception as e:
                _safe_log(f"[DataAccess] API error scan_contract_files: {e}")
                return None
        _safe_log("[DataAccess] scan_contract_files: API недоступен")
        return None

    def get_yandex_public_link(self, path: str) -> Optional[str]:
        """Получить публичную ссылку на файл Яндекс.Диска (только API)"""
        if self.api_client:
            try:
                result = self.api_client.get_yandex_public_link(path)
                # API возвращает Dict — извлекаем URL
                if isinstance(result, dict):
                    return result.get('public_url') or result.get('url') or result.get('href')
                return result
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_yandex_public_link: {e}")
                return None
        _safe_log("[DataAccess] get_yandex_public_link: API недоступен")
        return None

    def delete_yandex_file(self, path: str) -> bool:
        """Удалить файл с Яндекс.Диска (только API)"""
        if self.api_client:
            try:
                result = self.api_client.delete_yandex_file(path)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] API error delete_yandex_file: {e}")
                return False
        _safe_log("[DataAccess] delete_yandex_file: API недоступен")
        return False

    def validate_files(self, file_ids: list, auto_clean: bool = False) -> list:
        """Пакетная проверка существования файлов на Яндекс.Диске"""
        if self._should_use_api():
            try:
                return self.api_client.validate_files(file_ids, auto_clean)
            except Exception as e:
                _safe_log(f"[DataAccess] API error validate_files: {e}")
                return []
        return []

    # ==================== ШАБЛОНЫ ПРОЕКТОВ ====================

    def get_project_templates(self, contract_id: int) -> List[Dict]:
        """Получить шаблоны проекта"""
        if self._should_use_api():
            try:
                return self.api_client.get_project_templates(contract_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API get_project_templates, fallback: {e}")
        try:
            return self.db.get_project_templates(contract_id)
        except Exception as e:
            _safe_log(f"[DataAccess] DB get_project_templates: {e}")
            return []

    def add_project_template(self, contract_id: int, url: str) -> bool:
        """Добавить шаблон проекта"""
        # Сначала сохраняем локально
        try:
            self.db.add_project_template(contract_id, url)
        except Exception as e:
            _safe_log(f"[DataAccess] DB add_project_template: {e}")

        if self.is_online and self.api_client:
            try:
                result = self.api_client.add_project_template(contract_id, url)
                return result is not None
            except Exception as e:
                _safe_log(f"[DataAccess] API add_project_template: {e}")
                self._queue_operation('create', 'project_template', contract_id,
                                      {'contract_id': contract_id, 'url': url})
        elif self.api_client:
            self._queue_operation('create', 'project_template', contract_id,
                                  {'contract_id': contract_id, 'url': url})

        return True

    def delete_project_template(self, template_id: int) -> bool:
        """Удалить шаблон проекта"""
        # Сначала удаляем локально
        try:
            self.db.delete_project_template(template_id)
        except Exception as e:
            _safe_log(f"[DataAccess] DB delete_project_template: {e}")

        if self.is_online and self.api_client:
            try:
                result = self.api_client.delete_project_template(template_id)
                return bool(result)
            except Exception as e:
                _safe_log(f"[DataAccess] API delete_project_template: {e}")
                self._queue_operation('delete', 'project_template', template_id, {})
        elif self.api_client:
            self._queue_operation('delete', 'project_template', template_id, {})

        return True

    # ==================== СТАТИСТИКА ====================

    def get_dashboard_statistics(self, year: int = None, month: int = None,
                                 quarter: int = None, project_type: str = None) -> Dict:
        """Получить статистику для дашборда"""
        if self._should_use_api():
            try:
                return self.api_client.get_dashboard_statistics(
                    year=year, month=month, quarter=quarter, agent_type=project_type)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_dashboard_statistics, fallback: {e}")
        return self.db.get_dashboard_statistics(year=year, month=month,
                                                quarter=quarter, project_type=project_type)

    def get_supervision_statistics(self, address: str = None, dan_id: int = None,
                                  manager_id: int = None) -> Dict:
        """Получить статистику надзора (упрощённая версия)"""
        try:
            return self.db.get_supervision_statistics_filtered(
                None, None, None, None, address, None, dan_id, manager_id, None)
        except Exception as e:
            _safe_log(f"[DataAccess] DB error get_supervision_statistics: {e}")
            return {}

    def get_clients_dashboard_stats(self, **kwargs) -> Dict:
        """Получить статистику дашборда клиентов"""
        if self.api_client:
            try:
                return self.api_client.get_clients_dashboard_stats(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] API get_clients_dashboard_stats: {e}")
        if self.db:
            try:
                return self.db.get_clients_dashboard_stats(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] DB get_clients_dashboard_stats: {e}")
        return {}

    def get_contracts_dashboard_stats(self, **kwargs) -> Dict:
        """Получить статистику дашборда договоров"""
        if self.api_client:
            try:
                return self.api_client.get_contracts_dashboard_stats(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] API get_contracts_dashboard_stats: {e}")
        if self.db:
            try:
                return self.db.get_contracts_dashboard_stats(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] DB get_contracts_dashboard_stats: {e}")
        return {}

    def get_crm_dashboard_stats(self, **kwargs) -> Dict:
        """Получить статистику дашборда CRM"""
        if self.api_client:
            try:
                return self.api_client.get_crm_dashboard_stats(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] API get_crm_dashboard_stats: {e}")
        if self.db:
            try:
                return self.db.get_crm_dashboard_stats(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] DB get_crm_dashboard_stats: {e}")
        return {}

    def get_employees_dashboard_stats(self) -> Dict:
        """Получить статистику дашборда сотрудников"""
        if self.api_client:
            try:
                return self.api_client.get_employees_dashboard_stats()
            except Exception as e:
                _safe_log(f"[DataAccess] API get_employees_dashboard_stats: {e}")
        if self.db:
            try:
                return self.db.get_employees_dashboard_stats()
            except Exception as e:
                _safe_log(f"[DataAccess] DB get_employees_dashboard_stats: {e}")
        return {}

    def get_salaries_dashboard_stats(self, **kwargs) -> Dict:
        """Получить сводную статистику дашборда зарплат"""
        if self.api_client:
            try:
                return self.api_client.get_salaries_dashboard_stats(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] API get_salaries_dashboard_stats: {e}")
        if self.db:
            try:
                return self.db.get_salaries_dashboard_stats(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] DB get_salaries_dashboard_stats: {e}")
        return {}

    def get_salaries_individual_stats(self, **kwargs) -> Dict:
        """Получить индивидуальную статистику зарплат"""
        if self.api_client:
            try:
                return self.api_client.get_salaries_individual_stats(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] API get_salaries_individual_stats: {e}")
        if self.db:
            try:
                return self.db.get_salaries_individual_stats(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] DB get_salaries_individual_stats: {e}")
        return {}

    def get_salaries_salary_stats(self, **kwargs) -> Dict:
        """Получить статистику по выплатам зарплат"""
        if self.api_client:
            try:
                return self.api_client.get_salaries_salary_stats(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] API get_salaries_salary_stats: {e}")
        if self.db:
            try:
                return self.db.get_salaries_salary_stats(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] DB get_salaries_salary_stats: {e}")
        return {}

    def get_salaries_supervision_stats(self, **kwargs) -> Dict:
        """Получить статистику зарплат по надзору"""
        if self.api_client:
            try:
                return self.api_client.get_salaries_supervision_stats(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] API get_salaries_supervision_stats: {e}")
        if self.db:
            try:
                return self.db.get_salaries_supervision_stats(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] DB get_salaries_supervision_stats: {e}")
        return {}

    def get_salaries_template_stats(self, **kwargs) -> Dict:
        """Получить статистику зарплат по шаблонам"""
        if self.api_client:
            try:
                return self.api_client.get_salaries_template_stats(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] API get_salaries_template_stats: {e}")
        if self.db:
            try:
                return self.db.get_salaries_template_stats(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] DB get_salaries_template_stats: {e}")
        return {}

    def get_salaries_all_payments_stats(self, **kwargs) -> Dict:
        """Получить статистику по всем выплатам"""
        if self.api_client:
            try:
                return self.api_client.get_salaries_all_payments_stats(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] API get_salaries_all_payments_stats: {e}")
        if self.db:
            try:
                return self.db.get_salaries_all_payments_stats(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] DB get_salaries_all_payments_stats: {e}")
        return {}

    def get_employee_report_data(self, employee_id: int = None, project_type: str = None,
                                period: str = None, year: int = None,
                                quarter: int = None, month: int = None) -> Dict:
        """Получить данные отчёта по сотруднику

        Примечание: employee_id пока не поддерживается ни API, ни DB — зарезервирован для будущего
        """
        if self.api_client:
            try:
                return self.api_client.get_employee_report_data(
                    project_type, period, year, quarter=quarter, month=month)
            except Exception as e:
                _safe_log(f"[DataAccess] API get_employee_report_data: {e}")
        if self.db:
            try:
                return self.db.get_employee_report_data(
                    project_type, period, year, quarter, month)
            except Exception as e:
                _safe_log(f"[DataAccess] DB get_employee_report_data: {e}")
        return {}

    def get_project_statistics(self, **kwargs) -> Dict:
        """Получить статистику по проектам"""
        if self.api_client:
            try:
                return self.api_client.get_project_statistics(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] API get_project_statistics: {e}")
        if self.db:
            try:
                return self.db.get_project_statistics(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] DB get_project_statistics: {e}")
        return {}

    def get_supervision_statistics_report(self, **kwargs) -> Dict:
        """Получить отчёт по статистике надзора"""
        if self.api_client:
            try:
                return self.api_client.get_supervision_statistics(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] API get_supervision_statistics_report: {e}")
        if self.db:
            try:
                return self.db.get_supervision_statistics_report(**kwargs)
            except Exception as e:
                _safe_log(f"[DataAccess] DB get_supervision_statistics_report: {e}")
        return {}

    # ==================== ТАБЛИЦА СРОКОВ (CRM) ====================

    def get_project_timeline(self, contract_id: int) -> List[Dict]:
        """Получить таблицу сроков проекта"""
        if self._should_use_api():
            try:
                return self.api_client.get_project_timeline(contract_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_project_timeline, fallback: {e}")
        return self.db.get_project_timeline(contract_id)

    def init_project_timeline(self, contract_id: int, data: Dict) -> Optional[Dict]:
        """Инициализировать таблицу сроков из шаблона"""
        if self._should_use_api():
            try:
                return self.api_client.init_project_timeline(contract_id, data)
            except Exception as e:
                _safe_log(f"[DataAccess] API error init_project_timeline, fallback local: {e}")
        # K5: Offline fallback — сохраняем в локальную БД
        try:
            entries = data.get('entries', [])
            if entries:
                self.db.init_project_timeline(contract_id, entries)
                return {"status": "ok_local", "count": len(entries)}
        except Exception as e:
            _safe_log(f"[DataAccess] Local fallback init_project_timeline error: {e}")
        return None

    def reinit_project_timeline(self, contract_id: int, data: Dict) -> Optional[Dict]:
        """Пересоздать таблицу сроков (удалить и создать заново)"""
        if self._should_use_api():
            try:
                return self.api_client.reinit_project_timeline(contract_id, data)
            except Exception as e:
                _safe_log(f"[DataAccess] API error reinit_project_timeline: {e}")
        return None

    def update_timeline_entry(self, contract_id: int, stage_code: str, data: Dict) -> bool:
        """Обновить запись таблицы сроков"""
        # Сначала обновляем локально
        self.db.update_timeline_entry(contract_id, stage_code, data)

        if self.is_online and self.api_client:
            try:
                self.api_client.update_timeline_entry(contract_id, stage_code, data)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API update_timeline_entry: {e}")
                # Добавляем в очередь для синхронизации при восстановлении связи
                self._queue_operation('update', 'timeline_entry', contract_id, {
                    'contract_id': contract_id,
                    'stage_code': stage_code,
                    **data
                })
        elif self.api_client:
            self._queue_operation('update', 'timeline_entry', contract_id, {
                'contract_id': contract_id,
                'stage_code': stage_code,
                **data
            })

        return True

    def get_timeline_summary(self, contract_id: int) -> Dict:
        """Получить сводку по таблице сроков"""
        if self._should_use_api():
            try:
                return self.api_client.get_timeline_summary(contract_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_timeline_summary, fallback: {e}")
        # M1: Offline fallback — строим сводку из локальных данных
        try:
            entries = self.db.get_project_timeline(contract_id)
            if entries:
                total = len([e for e in entries if e.get('executor_role') != 'header'])
                filled = len([e for e in entries if e.get('actual_date')])
                return {'total_entries': total, 'filled_entries': filled, 'progress': round(filled / total * 100, 1) if total else 0}
        except Exception:
            pass
        return {}

    def export_timeline_excel(self, contract_id: int) -> bytes:
        """Экспорт таблицы сроков в Excel"""
        if self.api_client:
            try:
                return self.api_client.export_timeline_excel(contract_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error export_timeline_excel: {e}")
        return b''

    def export_timeline_pdf(self, contract_id: int) -> bytes:
        """Экспорт таблицы сроков в PDF"""
        if self.api_client:
            try:
                return self.api_client.export_timeline_pdf(contract_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error export_timeline_pdf: {e}")
        return b''

    # ==================== ТАБЛИЦА СРОКОВ (НАДЗОР) ====================

    def get_supervision_timeline(self, card_id: int) -> List[Dict]:
        """Получить таблицу сроков надзора"""
        if self._should_use_api():
            try:
                return self.api_client.get_supervision_timeline(card_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_supervision_timeline, fallback: {e}")
        return self.db.get_supervision_timeline(card_id)

    def init_supervision_timeline(self, card_id: int, data: Dict = None) -> Optional[Dict]:
        """Инициализировать таблицу сроков надзора"""
        if self._should_use_api():
            try:
                return self.api_client.init_supervision_timeline(card_id, data)
            except Exception as e:
                _safe_log(f"[DataAccess] API error init_supervision_timeline, fallback local: {e}")
        # K5: Offline fallback — сохраняем в локальную БД
        try:
            entries = (data or {}).get('entries', [])
            if entries:
                self.db.init_supervision_timeline(card_id, entries)
                return {"status": "ok_local", "count": len(entries)}
        except Exception as e:
            _safe_log(f"[DataAccess] Local fallback init_supervision_timeline error: {e}")
        return None

    def update_supervision_timeline_entry(self, card_id: int, stage_code: str, data: Dict) -> bool:
        """Обновить запись таблицы сроков надзора"""
        # Сначала обновляем локально
        self.db.update_supervision_timeline_entry(card_id, stage_code, data)

        if self.is_online and self.api_client:
            try:
                self.api_client.update_supervision_timeline_entry(card_id, stage_code, data)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API update_supervision_timeline_entry: {e}")
                # Добавляем в очередь для синхронизации при восстановлении связи
                self._queue_operation('update', 'supervision_timeline_entry', card_id, {
                    'card_id': card_id,
                    'stage_code': stage_code,
                    **data
                })
        elif self.api_client:
            self._queue_operation('update', 'supervision_timeline_entry', card_id, {
                'card_id': card_id,
                'stage_code': stage_code,
                **data
            })

        return True

    def get_supervision_timeline_summary(self, card_id: int) -> Dict:
        """Получить сводку по таблице сроков надзора"""
        if self._should_use_api():
            try:
                return self.api_client.get_supervision_timeline_summary(card_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error get_supervision_timeline_summary: {e}")
        # Offline fallback: строим сводку из локальных данных
        try:
            entries = self.db.get_supervision_timeline(card_id)
            if entries:
                total = len(entries)
                filled = sum(1 for e in entries if e.get('actual_date'))
                progress = round(filled / total * 100) if total > 0 else 0
                return {'total_stages': total, 'completed_stages': filled, 'progress': progress}
        except Exception:
            pass
        return {}

    def export_supervision_timeline_excel(self, card_id: int) -> bytes:
        """Экспорт таблицы сроков надзора в Excel"""
        if self.api_client:
            try:
                return self.api_client.export_supervision_timeline_excel(card_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error export_supervision_timeline_excel: {e}")
        return b''

    def export_supervision_timeline_pdf(self, card_id: int) -> bytes:
        """Экспорт таблицы сроков надзора в PDF"""
        if self.api_client:
            try:
                return self.api_client.export_supervision_timeline_pdf(card_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API error export_supervision_timeline_pdf: {e}")
        return b''

    # ==================== ПРЯМОЙ ДОСТУП К БД (для сложных запросов) ====================

    def execute_raw_query(self, query: str, params: tuple = None) -> List[Dict]:
        """
        Выполнить прямой SQL запрос к локальной БД.
        ВНИМАНИЕ: Используйте только когда нет API-эквивалента!
        """
        conn = self.db.connect()
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        result = cursor.fetchall()
        conn.close()
        return [dict(row) for row in result]

    def execute_raw_update(self, query: str, params: tuple = None) -> int:
        """
        Выполнить прямой SQL UPDATE/INSERT к локальной БД.
        ВНИМАНИЕ: Используйте только когда нет API-эквивалента!
        Возвращает количество затронутых строк.
        """
        conn = self.db.connect()
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        rowcount = cursor.rowcount
        conn.commit()
        conn.close()
        return rowcount

    # =========================
    # ГЛОБАЛЬНЫЙ ПОИСК
    # =========================

    def global_search(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """Полнотекстовый поиск по клиентам, договорам, CRM карточкам"""
        if self.api_client:
            try:
                return self.api_client.search(query, limit)
            except Exception:
                pass
        # Fallback: локальный поиск по SQLite
        return self.db.global_search(query, limit)

    # =========================
    # СТАТИСТИКА (расширенная)
    # =========================

    def get_funnel_statistics(self, year: int = None, project_type: str = None) -> Dict[str, Any]:
        """Статистика воронки проектов"""
        if self.api_client:
            try:
                return self.api_client.get_funnel_statistics(year, project_type)
            except Exception:
                pass
        return self.db.get_funnel_statistics(year, project_type)

    def get_executor_load(self, year: int = None, month: int = None) -> List[Dict[str, Any]]:
        """Нагрузка на исполнителей"""
        if self.api_client:
            try:
                return self.api_client.get_executor_load(year, month)
            except Exception:
                pass
        return self.db.get_executor_load(year, month)

    # =========================
    # МЕССЕНДЖЕР
    # =========================

    def create_messenger_chat(self, crm_card_id: int, messenger_type: str = "telegram",
                               members: list = None) -> Optional[Dict]:
        """Создать чат автоматически"""
        if self._should_use_api():
            try:
                return self.api_client.create_messenger_chat(crm_card_id, messenger_type, members)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка create_messenger_chat: {e}")
        return None

    def bind_messenger_chat(self, crm_card_id: int, invite_link: str,
                             messenger_type: str = "telegram", members: list = None) -> Optional[Dict]:
        """Привязать существующий чат"""
        if self._should_use_api():
            try:
                return self.api_client.bind_messenger_chat(crm_card_id, invite_link, messenger_type, members)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка bind_messenger_chat: {e}")
        return None

    def get_messenger_chat(self, crm_card_id: int) -> Optional[Dict]:
        """Получить чат по CRM-карточке"""
        if self.api_client:
            try:
                return self.api_client.get_messenger_chat_by_card(crm_card_id)
            except Exception:
                pass
        return None

    def get_supervision_chat(self, supervision_card_id: int) -> Optional[Dict]:
        """Получить чат по карточке надзора"""
        if self.api_client:
            try:
                return self.api_client.get_supervision_chat(supervision_card_id)
            except Exception:
                pass
        return None

    def create_supervision_chat(self, supervision_card_id: int, messenger_type: str = "telegram",
                                 members: list = None) -> Optional[Dict]:
        """Создать чат для карточки надзора"""
        if self._should_use_api():
            try:
                return self.api_client.create_supervision_chat(supervision_card_id, messenger_type, members)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка create_supervision_chat: {e}")
        return None

    def delete_messenger_chat(self, chat_id: int) -> Optional[Dict]:
        """Удалить чат"""
        if self._should_use_api():
            try:
                return self.api_client.delete_messenger_chat(chat_id)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка delete_messenger_chat: {e}")
        return None

    def send_messenger_message(self, chat_id: int, text: str) -> Optional[Dict]:
        """Отправить сообщение в чат"""
        if self._should_use_api():
            try:
                return self.api_client.send_messenger_message(chat_id, text)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка send_messenger_message: {e}")
        return None

    def get_messenger_scripts(self, project_type: str = None) -> List[Dict]:
        """Получить скрипты мессенджера"""
        if self.api_client:
            try:
                return self.api_client.get_messenger_scripts(project_type)
            except Exception:
                pass
        return []

    def get_messenger_settings(self) -> List[Dict]:
        """Получить настройки мессенджера"""
        if self.api_client:
            try:
                return self.api_client.get_messenger_settings()
            except Exception:
                pass
        return []

    def update_messenger_settings(self, settings: list) -> Optional[Dict]:
        """Обновить настройки мессенджера"""
        if self._should_use_api():
            try:
                return self.api_client.update_messenger_settings(settings)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка update_messenger_settings: {e}")
        return None

    def get_messenger_status(self) -> Dict:
        """Статус сервисов мессенджера"""
        if self.api_client:
            try:
                return self.api_client.get_messenger_status()
            except Exception:
                pass
        return {"telegram_bot_available": False, "telegram_mtproto_available": False, "email_available": False}

    def create_messenger_script(self, data: Dict) -> Optional[Dict]:
        """Создать скрипт мессенджера"""
        if self.api_client:
            try:
                return self.api_client.create_messenger_script(data)
            except Exception as e:
                _safe_log(f"[DataAccess] API create_messenger_script: {e}")
        else:
            _safe_log("[DataAccess] create_messenger_script: API недоступен")
        return None

    def update_messenger_script(self, script_id: int, data: Dict) -> Optional[Dict]:
        """Обновить скрипт мессенджера"""
        if self.api_client:
            try:
                return self.api_client.update_messenger_script(script_id, data)
            except Exception as e:
                _safe_log(f"[DataAccess] API update_messenger_script: {e}")
        else:
            _safe_log("[DataAccess] update_messenger_script: API недоступен")
        return None

    def delete_messenger_script(self, script_id: int) -> bool:
        """Удалить скрипт мессенджера"""
        if self.api_client:
            try:
                return self.api_client.delete_messenger_script(script_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API delete_messenger_script: {e}")
        else:
            _safe_log("[DataAccess] delete_messenger_script: API недоступен")
        return False

    def mtproto_send_code(self) -> Dict:
        """Шаг 1: Отправить код подтверждения для MTProto"""
        if self.api_client:
            try:
                return self.api_client.mtproto_send_code()
            except Exception as e:
                _safe_log(f"[DataAccess] API error mtproto_send_code: {e}")
                return {"error": str(e)}
        return {"error": "API не доступен"}

    def mtproto_resend_sms(self) -> Dict:
        """Переотправить код по SMS"""
        if self.api_client:
            try:
                return self.api_client.mtproto_resend_sms()
            except Exception as e:
                _safe_log(f"[DataAccess] API error mtproto_resend_sms: {e}")
                return {"error": str(e)}
        return {"error": "API не доступен"}

    def mtproto_verify_code(self, code: str) -> Dict:
        """Шаг 2: Подтвердить код MTProto"""
        if self.api_client:
            try:
                return self.api_client.mtproto_verify_code(code)
            except Exception as e:
                _safe_log(f"[DataAccess] API error mtproto_verify_code: {e}")
                return {"error": str(e)}
        return {"error": "API не доступен"}

    def mtproto_session_status(self) -> Dict:
        """Проверить статус MTProto сессии"""
        if self.api_client:
            try:
                return self.api_client.mtproto_session_status()
            except Exception as e:
                _safe_log(f"[DataAccess] API error mtproto_session_status: {e}")
                return {"valid": False}
        return {"valid": False}

    # =========================
    # АДМИНИСТРИРОВАНИЕ
    # =========================

    def get_role_permissions_matrix(self) -> Dict[str, Any]:
        """Получить матрицу прав по ролям"""
        if self.api_client:
            try:
                return self.api_client.get_role_permissions_matrix()
            except Exception:
                pass
        return {"roles": {}}

    def save_role_permissions_matrix(self, data: dict) -> Optional[Dict]:
        """Сохранить матрицу прав по ролям"""
        if self._should_use_api():
            try:
                return self.api_client.save_role_permissions_matrix(data)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка save_role_permissions_matrix: {e}")
        return None

    def get_employee_permissions(self, employee_id: int) -> Optional[Dict]:
        """Получить персональные права сотрудника"""
        if self.api_client:
            try:
                return self.api_client.get_employee_permissions(employee_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API get_employee_permissions: {e}")
        if self.db:
            try:
                return self.db.get_employee_permissions(employee_id)
            except Exception as e:
                _safe_log(f"[DataAccess] DB get_employee_permissions: {e}")
        return None

    def set_employee_permissions(self, employee_id: int, permissions) -> bool:
        """Установить персональные права сотрудника

        Args:
            employee_id: ID сотрудника
            permissions: Список прав (List[str]) или Dict с ключом 'permissions'
        """
        # Нормализация: извлекаем список из dict если передан dict
        if isinstance(permissions, dict):
            permissions = permissions.get('permissions', list(permissions.values()))

        # Сначала сохраняем локально
        try:
            self.db.set_employee_permissions(employee_id, permissions)
        except Exception as e:
            _safe_log(f"[DataAccess] DB set_employee_permissions: {e}")

        if self.is_online and self.api_client:
            try:
                return self.api_client.set_employee_permissions(employee_id, permissions)
            except Exception as e:
                _safe_log(f"[DataAccess] API set_employee_permissions: {e}")
                self._queue_operation('update', 'permission', employee_id,
                                      {'employee_id': employee_id, 'permissions': permissions})
        elif self.api_client:
            self._queue_operation('update', 'permission', employee_id,
                                  {'employee_id': employee_id, 'permissions': permissions})

        return True

    def reset_employee_permissions(self, employee_id: int) -> bool:
        """Сбросить персональные права сотрудника к ролевым (только API)"""
        if self.api_client:
            try:
                return self.api_client.reset_employee_permissions(employee_id)
            except Exception as e:
                _safe_log(f"[DataAccess] API reset_employee_permissions: {e}")
        else:
            _safe_log("[DataAccess] reset_employee_permissions: API недоступен")
        return False

    def get_permission_definitions(self) -> List[Dict]:
        """Получить описание всех прав системы (только API)"""
        if self.api_client:
            try:
                return self.api_client.get_permission_definitions()
            except Exception as e:
                _safe_log(f"[DataAccess] API get_permission_definitions: {e}")
        else:
            _safe_log("[DataAccess] get_permission_definitions: API недоступен")
        return []

    def get_norm_days_template(self, project_type: str, project_subtype: str, agent_type: str = 'Все агенты') -> Dict[str, Any]:
        """Получить шаблон нормо-дней"""
        if self._should_use_api():
            try:
                return self.api_client.get_norm_days_template(project_type, project_subtype, agent_type)
            except Exception as e:
                _safe_log(f"[DataAccess] API get_norm_days_template: {e}")
        # Offline fallback — читаем из локальной SQLite
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT * FROM norm_days_templates
                   WHERE project_type = ? AND project_subtype = ? AND agent_type = ?
                   ORDER BY sort_order''',
                (project_type, project_subtype, agent_type)
            )
            rows = cursor.fetchall()
            self.db.close()
            entries = [dict(r) for r in rows]
            if not entries and agent_type != 'Все агенты':
                # Fallback на "Все агенты"
                cursor2 = self.db.connect().cursor()
                cursor2.execute(
                    '''SELECT * FROM norm_days_templates
                       WHERE project_type = ? AND project_subtype = ? AND agent_type = ?
                       ORDER BY sort_order''',
                    (project_type, project_subtype, 'Все агенты')
                )
                entries = [dict(r) for r in cursor2.fetchall()]
                self.db.close()
            return {"entries": entries}
        except Exception as e:
            _safe_log(f"[DataAccess] SQLite get_norm_days_template: {e}")
        return {"entries": []}

    def save_norm_days_template(self, data: Dict[str, Any]) -> Optional[Dict]:
        """Сохранить шаблон нормо-дней"""
        if self._should_use_api():
            try:
                return self.api_client.save_norm_days_template(data)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка save_norm_days_template: {e}")
        return None

    def preview_norm_days_template(self, project_type: str, project_subtype: str, area: float, agent_type: str = 'Все агенты') -> Dict[str, Any]:
        """Превью нормо-дней для конкретной площади"""
        if self.api_client:
            try:
                return self.api_client.preview_norm_days_template(project_type, project_subtype, area, agent_type)
            except Exception:
                pass
        return {"entries": [], "contract_term": 0, "k_coefficient": 0}

    def reset_norm_days_template(self, project_type: str, project_subtype: str, agent_type: str = 'Все агенты') -> Optional[Dict]:
        """Сбросить шаблон нормо-дней к формулам"""
        if self._should_use_api():
            try:
                return self.api_client.reset_norm_days_template(project_type, project_subtype, agent_type)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка reset_norm_days_template: {e}")
        return None

    # ==================== ПРОЧЕЕ ====================

    def get_contract_years(self) -> List[int]:
        """Получить список лет, в которых есть договора"""
        if self.api_client:
            try:
                return self.api_client.get_contract_years()
            except Exception as e:
                _safe_log(f"[DataAccess] API get_contract_years: {e}")
        if self.db:
            try:
                return self.db.get_contract_years()
            except Exception as e:
                _safe_log(f"[DataAccess] DB get_contract_years: {e}")
        return []

    def get_cities(self) -> List[str]:
        """Получить список городов (только API)"""
        if self.api_client:
            try:
                return self.api_client.get_cities()
            except Exception as e:
                _safe_log(f"[DataAccess] API get_cities: {e}")
        else:
            _safe_log("[DataAccess] get_cities: API недоступен")
        return []

    def get_current_user(self) -> Optional[Dict]:
        """Получить текущего авторизованного пользователя (только API)"""
        if self.api_client:
            try:
                return self.api_client.get_current_user()
            except Exception as e:
                _safe_log(f"[DataAccess] API get_current_user: {e}")
        else:
            _safe_log("[DataAccess] get_current_user: API недоступен")
        return None

    # ==================== ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ ====================

    def delete_order(self, contract_id: int, crm_card_id: int = None) -> bool:
        """Полное удаление заказа (договор + CRM карточка)"""
        # Сначала удаляем локально
        self.db.delete_order(contract_id, crm_card_id)

        if self.is_online and self.api_client:
            try:
                if crm_card_id:
                    self.api_client.delete_crm_card(crm_card_id)
                self.api_client.delete_contract(contract_id)
                return True
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API delete_order: {e}")
                if crm_card_id:
                    self._queue_operation('delete', 'crm_card', crm_card_id, {})
                self._queue_operation('delete', 'contract', contract_id, {})
        elif self.api_client:
            if crm_card_id:
                self._queue_operation('delete', 'crm_card', crm_card_id, {})
            self._queue_operation('delete', 'contract', contract_id, {})

        return True

    def delete_project_file(self, file_id: int) -> Optional[Dict]:
        """Удалить файл стадии проекта. Возвращает данные файла (yandex_path и т.д.)"""
        # Сначала удаляем локально (получаем данные файла для возврата)
        local_result = self.db.delete_project_file(file_id)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.delete_project_file(file_id)
                return result or local_result
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API delete_project_file: {e}")
                self._queue_operation('delete', 'project_file', file_id, {})
        elif self.api_client:
            self._queue_operation('delete', 'project_file', file_id, {})

        return local_result

    def get_projects_by_type(self, project_type: str) -> List[Dict]:
        """Получить список проектов по типу для статистики"""
        if self.api_client:
            try:
                return self.api_client.get_projects_by_type(project_type)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API get_projects_by_type: {e}")
        return self.db.get_projects_by_type(project_type)

    def get_supervision_cards(self, status: str = "active") -> List[Dict]:
        """Получить карточки авторского надзора (active/archived/all)"""
        if self.api_client:
            try:
                return self.api_client.get_supervision_cards(status=status)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API get_supervision_cards: {e}")
        if status == "archived":
            return self.db.get_archived_supervision_cards() if hasattr(self.db, 'get_archived_supervision_cards') else []
        return self.db.get_active_supervision_cards() if hasattr(self.db, 'get_active_supervision_cards') else []

    def update_stage_executor(self, card_id: int, stage_name: str, update_data: Dict) -> Optional[Dict]:
        """Обновить исполнителя стадии (переназначение)"""
        # Сначала обновляем локально
        executor_id = update_data.get('executor_id')
        deadline = update_data.get('deadline')
        completed = update_data.get('completed', False)
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            # M3: Точное совпадение stage_name вместо LIKE
            cursor.execute(
                '''UPDATE stage_executors SET executor_id=?, deadline=?, completed=?, completed_date=NULL
                   WHERE crm_card_id=? AND stage_name=?''',
                (executor_id, deadline, 1 if completed else 0, card_id, stage_name)
            )
            conn.commit()
            self.db.close()
        except Exception as e:
            _safe_log(f"[DataAccess] Ошибка локального update_stage_executor: {e}")
            try:
                self.db.close()
            except Exception:
                pass

        if self.is_online and self.api_client:
            try:
                return self.api_client.update_stage_executor(card_id, stage_name, update_data)
            except Exception as e:
                _safe_log(f"[DataAccess] Ошибка API update_stage_executor: {e}")
                self._queue_operation('update', 'stage_executor', card_id,
                                      {'card_id': card_id, 'stage_name': stage_name,
                                       '_action': 'update', **update_data})
        elif self.api_client:
            self._queue_operation('update', 'stage_executor', card_id,
                                  {'card_id': card_id, 'stage_name': stage_name,
                                   '_action': 'update', **update_data})

        return {'success': True}
