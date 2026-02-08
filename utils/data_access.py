"""
Унифицированный доступ к данным (API или локальная БД)
Автоматически выбирает источник данных в зависимости от наличия api_client
Поддерживает offline-режим с очередью отложенных операций
"""
from typing import Optional, List, Dict, Any
from database.db_manager import DatabaseManager
from PyQt5.QtCore import QObject, pyqtSignal

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

        # Подключаем сигналы OfflineManager если доступен
        om = get_offline_manager()
        if om:
            om.connection_status_changed.connect(self._on_offline_manager_status_changed)
            om.pending_operations_changed.connect(self.pending_operations_changed.emit)

    def _on_offline_manager_status_changed(self, status: str):
        """Обработчик изменения статуса от OfflineManager"""
        is_online = status == 'online'
        if self._is_online != is_online:
            self._is_online = is_online
            self.connection_status_changed.emit(is_online)

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
        """Добавить операцию в очередь для синхронизации"""
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

    # ==================== КЛИЕНТЫ ====================

    def get_all_clients(self) -> List[Dict]:
        """Получить всех клиентов"""
        if self.api_client:
            return self.api_client.get_clients(skip=0, limit=10000)
        return self.db.get_all_clients()

    def get_client(self, client_id: int) -> Optional[Dict]:
        """Получить клиента по ID"""
        if self.api_client:
            return self.api_client.get_client(client_id)
        return self.db.get_client_by_id(client_id)

    def create_client(self, client_data: Dict) -> Optional[Dict]:
        """Создать клиента"""
        # Сначала сохраняем локально
        client_id = self.db.add_client(client_data)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.create_client(client_data)
                if result:
                    # Обновляем локальный ID на серверный если отличается
                    server_id = result.get('id')
                    if server_id and server_id != client_id:
                        self._update_local_id('clients', client_id, server_id)
                    return result
            except Exception as e:
                print(f"[DataAccess] Ошибка API create_client: {e}")
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
            print(f"[DataAccess] Обновлён ID в {table}: {local_id} -> {server_id}")
        except Exception as e:
            print(f"[DataAccess] Ошибка обновления ID: {e}")

    def update_client(self, client_id: int, client_data: Dict) -> bool:
        """Обновить клиента"""
        # Сначала обновляем локально
        self.db.update_client(client_id, client_data)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.update_client(client_id, client_data)
                return result is not None
            except Exception as e:
                print(f"[DataAccess] Ошибка API update_client: {e}")
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
                print(f"[DataAccess] Ошибка API delete_client: {e}")
                self._queue_operation('delete', 'client', client_id, {})
        elif self.api_client:
            self._queue_operation('delete', 'client', client_id, {})

        return True

    # ==================== ДОГОВОРА ====================

    def get_all_contracts(self) -> List[Dict]:
        """Получить все договора"""
        if self.api_client:
            return self.api_client.get_contracts(skip=0, limit=10000)
        return self.db.get_all_contracts()

    def get_contract(self, contract_id: int) -> Optional[Dict]:
        """Получить договор по ID"""
        if self.api_client:
            return self.api_client.get_contract(contract_id)
        return self.db.get_contract_by_id(contract_id)

    def create_contract(self, contract_data: Dict) -> Optional[Dict]:
        """Создать договор"""
        # Сначала сохраняем локально
        contract_id = self.db.add_contract(contract_data)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.create_contract(contract_data)
                if result:
                    server_id = result.get('id')
                    if server_id and server_id != contract_id:
                        self._update_local_id('contracts', contract_id, server_id)
                    return result
            except Exception as e:
                print(f"[DataAccess] Ошибка API create_contract: {e}")
                self._queue_operation('create', 'contract', contract_id, contract_data)
        elif self.api_client:
            self._queue_operation('create', 'contract', contract_id, contract_data)

        return {'id': contract_id, **contract_data} if contract_id else None

    def update_contract(self, contract_id: int, contract_data: Dict) -> bool:
        """Обновить договор"""
        # Сначала обновляем локально
        self.db.update_contract(contract_id, contract_data)

        if self.is_online and self.api_client:
            try:
                result = self.api_client.update_contract(contract_id, contract_data)
                return result is not None
            except Exception as e:
                print(f"[DataAccess] Ошибка API update_contract: {e}")
                self._queue_operation('update', 'contract', contract_id, contract_data)
        elif self.api_client:
            self._queue_operation('update', 'contract', contract_id, contract_data)

        return True

    def delete_contract(self, contract_id: int) -> bool:
        """Удалить договор"""
        if self.api_client:
            return self.api_client.delete_contract(contract_id)
        # Локально используется delete_order
        crm_card_id = self.db.get_crm_card_id_by_contract(contract_id)
        return self.db.delete_order(contract_id, crm_card_id)

    def check_contract_number_exists(self, contract_number: str, exclude_id: int = None) -> bool:
        """Проверить существование номера договора"""
        if self.api_client:
            return self.api_client.check_contract_number_exists(contract_number, exclude_id)
        return self.db.check_contract_number_exists(contract_number, exclude_id)

    # ==================== СОТРУДНИКИ ====================

    def get_all_employees(self) -> List[Dict]:
        """Получить всех сотрудников"""
        if self.api_client:
            return self.api_client.get_employees(skip=0, limit=10000)
        return self.db.get_all_employees()

    def get_employees_by_position(self, position: str) -> List[Dict]:
        """Получить сотрудников по должности"""
        if self.api_client:
            return self.api_client.get_employees_by_position(position)
        return self.db.get_employees_by_position(position)

    def get_employee(self, employee_id: int) -> Optional[Dict]:
        """Получить сотрудника по ID"""
        if self.api_client:
            return self.api_client.get_employee(employee_id)
        return self.db.get_employee_by_id(employee_id)

    def create_employee(self, employee_data: Dict) -> Optional[Dict]:
        """Создать сотрудника"""
        if self.api_client:
            return self.api_client.create_employee(employee_data)
        employee_id = self.db.add_employee(employee_data)
        return {'id': employee_id, **employee_data} if employee_id else None

    def update_employee(self, employee_id: int, employee_data: Dict) -> bool:
        """Обновить сотрудника"""
        if self.api_client:
            result = self.api_client.update_employee(employee_id, employee_data)
            return result is not None
        return self.db.update_employee(employee_id, employee_data)

    def delete_employee(self, employee_id: int) -> bool:
        """Удалить сотрудника"""
        if self.api_client:
            return self.api_client.delete_employee(employee_id)
        return self.db.delete_employee(employee_id)

    # ==================== CRM КАРТОЧКИ ====================

    def get_crm_cards(self, project_type: str) -> List[Dict]:
        """Получить CRM карточки по типу проекта"""
        if self.api_client:
            return self.api_client.get_crm_cards(project_type)
        return self.db.get_crm_cards_by_project_type(project_type)

    def get_crm_card(self, card_id: int) -> Optional[Dict]:
        """Получить CRM карточку по ID"""
        if self.api_client:
            return self.api_client.get_crm_card(card_id)
        return self.db.get_crm_card_data(card_id)

    def get_archived_crm_cards(self, project_type: str) -> List[Dict]:
        """Получить архивные CRM карточки"""
        if self.api_client:
            return self.api_client.get_crm_cards(project_type)  # API фильтрует сам
        return self.db.get_archived_crm_cards(project_type)

    def create_crm_card(self, card_data: Dict) -> Optional[Dict]:
        """Создать CRM карточку"""
        if self.api_client:
            return self.api_client.create_crm_card(card_data)
        card_id = self.db.add_crm_card(card_data)
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
                print(f"[DataAccess] Ошибка API update_crm_card: {e}")
                self._queue_operation('update', 'crm_card', card_id, updates)
        elif self.api_client:
            self._queue_operation('update', 'crm_card', card_id, updates)

        return True

    def delete_crm_card(self, card_id: int) -> bool:
        """Удалить CRM карточку"""
        if self.api_client:
            return self.api_client.delete_crm_card(card_id)
        contract_id = self.db.get_contract_id_by_crm_card(card_id)
        return self.db.delete_order(contract_id, card_id) if contract_id else False

    def update_crm_card_column(self, card_id: int, column: str) -> bool:
        """Переместить карточку в другую колонку"""
        if self.api_client:
            result = self.api_client.update_crm_card(card_id, {'column_position': column})
            return result is not None
        return self.db.update_crm_card_column(card_id, column)

    def get_contract_id_by_crm_card(self, card_id: int) -> Optional[int]:
        """Получить ID договора по ID CRM карточки"""
        if self.api_client:
            card = self.api_client.get_crm_card(card_id)
            return card.get('contract_id') if card else None
        return self.db.get_contract_id_by_crm_card(card_id)

    # ==================== SUPERVISION КАРТОЧКИ ====================

    def get_supervision_cards_active(self) -> List[Dict]:
        """Получить активные карточки надзора"""
        if self.api_client:
            return self.api_client.get_supervision_cards(status="active")
        return self.db.get_supervision_cards_active()

    def get_supervision_cards_archived(self) -> List[Dict]:
        """Получить архивные карточки надзора"""
        if self.api_client:
            return self.api_client.get_supervision_cards(status="archived")
        return self.db.get_supervision_cards_archived()

    def get_supervision_card(self, card_id: int) -> Optional[Dict]:
        """Получить карточку надзора по ID"""
        if self.api_client:
            return self.api_client.get_supervision_card(card_id)
        return self.db.get_supervision_card_data(card_id)

    def create_supervision_card(self, card_data: Dict) -> Optional[Dict]:
        """Создать карточку надзора"""
        if self.api_client:
            return self.api_client.create_supervision_card(card_data)
        card_id = self.db.add_supervision_card(card_data)
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
                print(f"[DataAccess] Ошибка API update_supervision_card: {e}")
                self._queue_operation('update', 'supervision_card', card_id, updates)
        elif self.api_client:
            self._queue_operation('update', 'supervision_card', card_id, updates)

        return True

    def update_supervision_card_column(self, card_id: int, column: str) -> bool:
        """Переместить карточку надзора в другую колонку"""
        if self.api_client:
            result = self.api_client.update_supervision_card(card_id, {'column_position': column})
            return result is not None
        return self.db.update_supervision_card_column(card_id, column)

    # ==================== ПЛАТЕЖИ ====================

    def get_payments_for_contract(self, contract_id: int) -> List[Dict]:
        """Получить платежи по договору"""
        if self.api_client:
            return self.api_client.get_payments_for_contract(contract_id)
        return self.db.get_payments_for_contract(contract_id)

    def create_payment(self, payment_data: Dict) -> Optional[Dict]:
        """Создать платёж"""
        if self.api_client:
            return self.api_client.create_payment(payment_data)
        payment_id = self.db.add_payment(payment_data)
        return {'id': payment_id, **payment_data} if payment_id else None

    def update_payment(self, payment_id: int, payment_data: Dict) -> bool:
        """Обновить платёж"""
        if self.api_client:
            result = self.api_client.update_payment(payment_id, payment_data)
            return result is not None
        return self.db.update_payment(payment_id, payment_data)

    def delete_payment(self, payment_id: int) -> bool:
        """Удалить платёж"""
        if self.api_client:
            result = self.api_client.delete_payment(payment_id)
            return result is not None
        return self.db.delete_payment(payment_id)

    # ==================== ИСТОРИЯ ДЕЙСТВИЙ ====================

    def get_action_history(self, entity_type: str, entity_id: int) -> List[Dict]:
        """Получить историю действий"""
        if self.api_client:
            return self.api_client.get_action_history(entity_type, entity_id)
        return self.db.get_action_history(entity_type, entity_id)

    def add_action_history(self, user_id: int, action_type: str, entity_type: str,
                          entity_id: int, description: str = None) -> bool:
        """Добавить запись в историю действий"""
        if self.api_client:
            history_data = {
                'user_id': user_id,
                'action_type': action_type,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'description': description
            }
            result = self.api_client.create_action_history(history_data)
            return result is not None
        return self.db.add_action_history(user_id, action_type, entity_type, entity_id, description)

    # ==================== ИСТОРИЯ НАДЗОРА ====================

    def get_supervision_history(self, card_id: int) -> List[Dict]:
        """Получить историю карточки надзора"""
        if self.api_client:
            return self.api_client.get_supervision_history(card_id)
        return self.db.get_supervision_history(card_id)

    def add_supervision_history(self, card_id: int, user_id: int, action_type: str,
                               description: str = None) -> bool:
        """Добавить запись в историю надзора"""
        if self.api_client:
            history_data = {
                'user_id': user_id,
                'action_type': action_type,
                'description': description
            }
            result = self.api_client.add_supervision_history(card_id, history_data)
            return result is not None
        return self.db.add_supervision_history(card_id, user_id, action_type, description)

    # ==================== СТАВКИ ====================

    def get_rates(self, project_type: str = None, role: str = None) -> List[Dict]:
        """Получить ставки"""
        if self.api_client:
            return self.api_client.get_rates(project_type, role)
        return self.db.get_rates(project_type, role)

    def get_rate(self, rate_id: int) -> Optional[Dict]:
        """Получить ставку по ID"""
        if self.api_client:
            return self.api_client.get_rate(rate_id)
        return self.db.get_rate_by_id(rate_id)

    def create_rate(self, rate_data: Dict) -> Optional[Dict]:
        """Создать ставку"""
        if self.api_client:
            return self.api_client.create_rate(rate_data)
        rate_id = self.db.add_rate(rate_data)
        return {'id': rate_id, **rate_data} if rate_id else None

    def update_rate(self, rate_id: int, rate_data: Dict) -> bool:
        """Обновить ставку"""
        if self.api_client:
            result = self.api_client.update_rate(rate_id, rate_data)
            return result is not None
        return self.db.update_rate(rate_id, rate_data)

    def delete_rate(self, rate_id: int) -> bool:
        """Удалить ставку"""
        if self.api_client:
            return self.api_client.delete_rate(rate_id)
        return self.db.delete_rate(rate_id)

    # ==================== ЗАРПЛАТЫ ====================

    def get_salaries(self, report_month: str = None, employee_id: int = None) -> List[Dict]:
        """Получить зарплаты"""
        if self.api_client:
            return self.api_client.get_salaries(report_month, employee_id)
        return self.db.get_salaries(report_month, employee_id)

    def get_salary(self, salary_id: int) -> Optional[Dict]:
        """Получить зарплату по ID"""
        if self.api_client:
            return self.api_client.get_salary(salary_id)
        return self.db.get_salary_by_id(salary_id)

    def create_salary(self, salary_data: Dict) -> Optional[Dict]:
        """Создать запись о зарплате"""
        if self.api_client:
            return self.api_client.create_salary(salary_data)
        salary_id = self.db.add_salary(salary_data)
        return {'id': salary_id, **salary_data} if salary_id else None

    def update_salary(self, salary_id: int, salary_data: Dict) -> bool:
        """Обновить запись о зарплате"""
        if self.api_client:
            result = self.api_client.update_salary(salary_id, salary_data)
            return result is not None
        return self.db.update_salary(salary_id, salary_data)

    def delete_salary(self, salary_id: int) -> bool:
        """Удалить запись о зарплате"""
        if self.api_client:
            return self.api_client.delete_salary(salary_id)
        return self.db.delete_salary(salary_id)

    # ==================== АГЕНТЫ ====================

    def get_all_agents(self) -> List[Dict]:
        """Получить всех агентов"""
        if self.api_client:
            agent_types = self.api_client.get_agent_types()
            return [{'name': a} for a in agent_types]
        return self.db.get_all_agents()

    def get_agent_color(self, agent_name: str) -> Optional[str]:
        """Получить цвет агента"""
        # API не поддерживает цвета агентов, используем локальную БД
        return self.db.get_agent_color(agent_name)

    # ==================== СТАДИИ ====================

    def get_stage_history(self, card_id: int) -> List[Dict]:
        """Получить историю стадий"""
        if self.api_client:
            return self.api_client.get_stage_executors(card_id)
        return self.db.get_stage_history(card_id)

    def get_accepted_stages(self, card_id: int) -> List[Dict]:
        """Получить принятые стадии"""
        # Этот метод специфичен для локальной БД
        return self.db.get_accepted_stages(card_id)

    def get_submitted_stages(self, card_id: int) -> List[Dict]:
        """Получить сданные стадии"""
        # Этот метод специфичен для локальной БД
        return self.db.get_submitted_stages(card_id)

    def update_stage_executor_deadline(self, card_id: int, stage_name: str,
                                       executor_id: int = None, deadline: str = None) -> bool:
        """Обновить дедлайн исполнителя стадии"""
        if self.api_client:
            update_data = {}
            if executor_id is not None:
                update_data['executor_id'] = executor_id
            if deadline is not None:
                update_data['deadline'] = deadline
            result = self.api_client.update_stage_executor(card_id, stage_name, update_data)
            return result is not None
        return self.db.update_stage_executor_deadline(card_id, stage_name, executor_id, deadline)

    # ==================== ФАЙЛЫ ====================

    def get_contract_files(self, contract_id: int, stage: str = None) -> List[Dict]:
        """Получить файлы договора"""
        if self.api_client:
            return self.api_client.get_contract_files(contract_id, stage)
        return self.db.get_contract_files(contract_id, stage)

    def create_file_record(self, file_data: Dict) -> Optional[Dict]:
        """Создать запись о файле"""
        if self.api_client:
            return self.api_client.create_file_record(file_data)
        file_id = self.db.add_contract_file(file_data)
        return {'id': file_id, **file_data} if file_id else None

    def delete_file_record(self, file_id: int) -> bool:
        """Удалить запись о файле"""
        if self.api_client:
            return self.api_client.delete_file_record(file_id)
        return self.db.delete_contract_file(file_id)

    # ==================== ШАБЛОНЫ ПРОЕКТОВ ====================

    def get_project_templates(self, contract_id: int) -> List[Dict]:
        """Получить шаблоны проекта"""
        # API пока не поддерживает, используем локальную БД
        return self.db.get_project_templates(contract_id)

    def add_project_template(self, contract_id: int, url: str) -> bool:
        """Добавить шаблон проекта"""
        # API пока не поддерживает, используем локальную БД
        return self.db.add_project_template(contract_id, url)

    def delete_project_template(self, template_id: int) -> bool:
        """Удалить шаблон проекта"""
        # API пока не поддерживает, используем локальную БД
        return self.db.delete_project_template(template_id)

    # ==================== СТАТИСТИКА ====================

    def get_dashboard_statistics(self, year: int = None, month: int = None,
                                 quarter: int = None, project_type: str = None) -> Dict:
        """Получить статистику для дашборда"""
        if self.api_client:
            return self.api_client.get_dashboard_statistics(year, month, quarter, project_type)
        return self.db.get_dashboard_statistics(year, month, quarter, project_type)

    def get_supervision_statistics(self, address: str = None, dan_id: int = None,
                                  manager_id: int = None) -> Dict:
        """Получить статистику надзора"""
        # API пока не поддерживает, используем локальную БД
        return self.db.get_supervision_statistics_filtered(address, dan_id, manager_id)

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
