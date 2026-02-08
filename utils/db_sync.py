# -*- coding: utf-8 -*-
"""
Модуль синхронизации локальной и серверной баз данных.
Выполняет двустороннюю синхронизацию при входе в систему.
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import traceback

# Импорт логгера
try:
    from utils.logger import app_logger, log_database_operation
except ImportError:
    import logging
    app_logger = logging.getLogger('sync')
    def log_database_operation(*args, **kwargs): pass


class DatabaseSynchronizer:
    """
    Синхронизатор баз данных.

    Загружает данные с сервера в локальную БД при входе.
    Поддерживает синхронизацию: клиентов, договоров, сотрудников, CRM карточек.
    """

    def __init__(self, db_manager, api_client):
        """
        Args:
            db_manager: Экземпляр DatabaseManager для работы с локальной БД
            api_client: Экземпляр APIClient для работы с сервером
        """
        self.db = db_manager
        self.api = api_client
        self.sync_log = []

    def sync_all(self, progress_callback=None) -> Dict[str, Any]:
        """
        Выполнить полную синхронизацию всех данных.

        Args:
            progress_callback: Функция обратного вызова для отображения прогресса
                              Принимает (current_step, total_steps, message)

        Returns:
            Dict с результатами синхронизации:
                - success: bool
                - synced: Dict с количеством синхронизированных записей
                - errors: List ошибок
        """
        result = {
            'success': True,
            'synced': {
                'employees': 0,
                'clients': 0,
                'contracts': 0,
                'crm_cards': 0,
                'supervision_cards': 0,
                'payments': 0,
                'rates': 0,
                'project_files': 0,
                'salaries': 0,
                'stage_executors': 0,
                'approval_deadlines': 0,
                'action_history': 0,
                'supervision_history': 0
            },
            'errors': []
        }

        total_steps = 14
        current_step = 0

        def report_progress(message):
            nonlocal current_step
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, message)
            app_logger.info(f"[SYNC] [{current_step}/{total_steps}] {message}")

        try:
            # 1. Синхронизация сотрудников
            report_progress("Синхронизация сотрудников...")
            count = self._sync_employees()
            result['synced']['employees'] = count

            # 2. Синхронизация клиентов
            report_progress("Синхронизация клиентов...")
            count = self._sync_clients()
            result['synced']['clients'] = count

            # 3. Синхронизация договоров
            report_progress("Синхронизация договоров...")
            count = self._sync_contracts()
            result['synced']['contracts'] = count

            # 4. Синхронизация CRM карточек
            report_progress("Синхронизация CRM карточек...")
            count = self._sync_crm_cards()
            result['synced']['crm_cards'] = count

            # 5. Синхронизация карточек надзора
            report_progress("Синхронизация карточек надзора...")
            count = self._sync_supervision_cards()
            result['synced']['supervision_cards'] = count

            # 6. Синхронизация тарифов
            report_progress("Синхронизация тарифов...")
            count = self._sync_rates()
            result['synced']['rates'] = count

            # 7. Синхронизация платежей
            report_progress("Синхронизация платежей...")
            count = self._sync_payments()
            result['synced']['payments'] = count

            # 8. Синхронизация файлов проектов
            report_progress("Синхронизация файлов проектов...")
            count = self._sync_project_files()
            result['synced']['project_files'] = count

            # 9. Синхронизация зарплат
            report_progress("Синхронизация зарплат...")
            count = self._sync_salaries()
            result['synced']['salaries'] = count

            # 10. Синхронизация исполнителей стадий
            report_progress("Синхронизация исполнителей стадий...")
            count = self._sync_stage_executors()
            result['synced']['stage_executors'] = count

            # 11. Синхронизация дедлайнов согласования
            report_progress("Синхронизация дедлайнов согласования...")
            count = self._sync_approval_stage_deadlines()
            result['synced']['approval_deadlines'] = count

            # 12. Синхронизация истории действий
            report_progress("Синхронизация истории действий...")
            count = self._sync_action_history()
            result['synced']['action_history'] = count

            # 13. Синхронизация истории проектов надзора
            report_progress("Синхронизация истории надзора...")
            count = self._sync_supervision_project_history()
            result['synced']['supervision_history'] = count

            # 14. Завершение
            report_progress("Синхронизация завершена")

        except Exception as e:
            result['success'] = False
            result['errors'].append(str(e))
            app_logger.error(f"[SYNC ERROR] {e}")
            traceback.print_exc()

        return result

    def verify_integrity(self) -> Dict[str, Any]:
        """
        Проверка целостности данных между локальной и серверной БД.

        Returns:
            Dict с результатами проверки
        """
        checker = IntegrityChecker(self.db, self.api)
        return checker.check()

    def _sync_employees(self) -> int:
        """Синхронизация сотрудников с сервера в локальную БД"""
        try:
            # Получаем данные с сервера
            server_employees = self.api.get_employees(limit=1000)

            if not server_employees:
                return 0

            conn = self.db.connect()
            cursor = conn.cursor()

            synced_count = 0

            for emp in server_employees:
                try:
                    server_id = emp['id']
                    server_login = emp.get('login')

                    # Проверяем существование по ID
                    cursor.execute("SELECT id, login FROM employees WHERE id = ?", (server_id,))
                    exists_by_id = cursor.fetchone()

                    # Также проверяем по login (если login есть)
                    exists_by_login = None
                    if server_login:
                        cursor.execute("SELECT id, login FROM employees WHERE login = ? AND id != ?",
                                      (server_login, server_id))
                        exists_by_login = cursor.fetchone()

                    # Если есть запись с таким же login но другим ID - удаляем её
                    # (серверная версия имеет приоритет)
                    if exists_by_login:
                        old_id = exists_by_login[0]
                        cursor.execute("DELETE FROM employees WHERE id = ?", (old_id,))
                        app_logger.info(f"[SYNC] Удалена дублирующая запись сотрудника ID={old_id} (login={server_login})")

                    if exists_by_id:
                        # Обновляем существующую запись
                        cursor.execute("""
                            UPDATE employees SET
                                full_name = ?,
                                phone = ?,
                                email = ?,
                                status = ?,
                                position = ?,
                                department = ?,
                                legal_status = ?,
                                hire_date = ?,
                                payment_details = ?,
                                login = ?,
                                role = ?,
                                birth_date = ?,
                                address = ?,
                                secondary_position = ?,
                                updated_at = ?
                            WHERE id = ?
                        """, (
                            emp.get('full_name'),
                            emp.get('phone'),
                            emp.get('email'),
                            emp.get('status'),
                            emp.get('position'),
                            emp.get('department'),
                            emp.get('legal_status'),
                            emp.get('hire_date'),
                            emp.get('payment_details'),
                            emp.get('login'),
                            emp.get('role'),
                            emp.get('birth_date'),
                            emp.get('address'),
                            emp.get('secondary_position'),
                            datetime.now().isoformat(),
                            server_id
                        ))
                    else:
                        # Вставляем новую запись
                        cursor.execute("""
                            INSERT INTO employees (
                                id, full_name, phone, email, status, position,
                                department, legal_status, hire_date, payment_details,
                                login, role, birth_date, address, secondary_position,
                                created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            server_id,
                            emp.get('full_name'),
                            emp.get('phone'),
                            emp.get('email'),
                            emp.get('status'),
                            emp.get('position'),
                            emp.get('department'),
                            emp.get('legal_status'),
                            emp.get('hire_date'),
                            emp.get('payment_details'),
                            emp.get('login'),
                            emp.get('role'),
                            emp.get('birth_date'),
                            emp.get('address'),
                            emp.get('secondary_position'),
                            datetime.now().isoformat(),
                            datetime.now().isoformat()
                        ))

                    synced_count += 1

                except Exception as e:
                    app_logger.info(f"[SYNC] Ошибка синхронизации сотрудника {emp.get('id')}: {e}")

            conn.commit()
            self.db.close()

            return synced_count

        except Exception as e:
            app_logger.info(f"[SYNC] Ошибка синхронизации сотрудников: {e}")
            return 0

    def _sync_clients(self) -> int:
        """Синхронизация клиентов с сервера в локальную БД"""
        try:
            # Получаем данные с сервера
            server_clients = self.api.get_clients(limit=10000)

            if server_clients is None:
                return 0

            conn = self.db.connect()
            cursor = conn.cursor()

            # Удаляем клиентов, которых нет на сервере
            if server_clients:
                server_ids = set(c['id'] for c in server_clients)
                cursor.execute("SELECT id FROM clients")
                local_ids = set(row[0] for row in cursor.fetchall())
                ids_to_delete = local_ids - server_ids
                if ids_to_delete:
                    cursor.execute(f"DELETE FROM clients WHERE id IN ({','.join('?' * len(ids_to_delete))})",
                                  tuple(ids_to_delete))
                    app_logger.info(f"[SYNC] Удалено {len(ids_to_delete)} устаревших клиентов")
            else:
                # Если на сервере нет клиентов, очищаем локальную таблицу
                cursor.execute("DELETE FROM clients")

            synced_count = 0

            for client in server_clients:
                try:
                    # Проверяем существование по ID
                    cursor.execute("SELECT id FROM clients WHERE id = ?", (client['id'],))
                    exists = cursor.fetchone()

                    if exists:
                        # Обновляем существующую запись
                        cursor.execute("""
                            UPDATE clients SET
                                client_type = ?,
                                full_name = ?,
                                phone = ?,
                                email = ?,
                                passport_series = ?,
                                passport_number = ?,
                                passport_issued_by = ?,
                                passport_issued_date = ?,
                                registration_address = ?,
                                organization_type = ?,
                                organization_name = ?,
                                inn = ?,
                                ogrn = ?,
                                account_details = ?,
                                responsible_person = ?,
                                updated_at = ?
                            WHERE id = ?
                        """, (
                            client.get('client_type'),
                            client.get('full_name'),
                            client.get('phone'),
                            client.get('email'),
                            client.get('passport_series'),
                            client.get('passport_number'),
                            client.get('passport_issued_by'),
                            client.get('passport_issued_date'),
                            client.get('registration_address'),
                            client.get('organization_type'),
                            client.get('organization_name'),
                            client.get('inn'),
                            client.get('ogrn'),
                            client.get('account_details'),
                            client.get('responsible_person'),
                            datetime.now().isoformat(),
                            client['id']
                        ))
                    else:
                        # Вставляем новую запись
                        cursor.execute("""
                            INSERT INTO clients (
                                id, client_type, full_name, phone, email,
                                passport_series, passport_number, passport_issued_by,
                                passport_issued_date, registration_address,
                                organization_type, organization_name, inn, ogrn,
                                account_details, responsible_person,
                                created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            client['id'],
                            client.get('client_type'),
                            client.get('full_name'),
                            client.get('phone'),
                            client.get('email'),
                            client.get('passport_series'),
                            client.get('passport_number'),
                            client.get('passport_issued_by'),
                            client.get('passport_issued_date'),
                            client.get('registration_address'),
                            client.get('organization_type'),
                            client.get('organization_name'),
                            client.get('inn'),
                            client.get('ogrn'),
                            client.get('account_details'),
                            client.get('responsible_person'),
                            datetime.now().isoformat(),
                            datetime.now().isoformat()
                        ))

                    synced_count += 1

                except Exception as e:
                    app_logger.info(f"[SYNC] Ошибка синхронизации клиента {client.get('id')}: {e}")

            conn.commit()
            self.db.close()

            return synced_count

        except Exception as e:
            app_logger.info(f"[SYNC] Ошибка синхронизации клиентов: {e}")
            return 0

    def _sync_contracts(self) -> int:
        """Синхронизация договоров с сервера в локальную БД"""
        try:
            # Получаем данные с сервера
            server_contracts = self.api.get_contracts(limit=10000)

            conn = self.db.connect()
            cursor = conn.cursor()

            # Удаляем договоры, которых нет на сервере
            if server_contracts:
                server_ids = set(c['id'] for c in server_contracts)
                cursor.execute("SELECT id FROM contracts")
                local_ids = set(row[0] for row in cursor.fetchall())
                ids_to_delete = local_ids - server_ids
                if ids_to_delete:
                    cursor.execute(f"DELETE FROM contracts WHERE id IN ({','.join('?' * len(ids_to_delete))})",
                                  tuple(ids_to_delete))
                    app_logger.info(f"[SYNC] Удалено {len(ids_to_delete)} устаревших договоров")
            else:
                cursor.execute("DELETE FROM contracts")
                conn.commit()
                self.db.close()
                return 0

            synced_count = 0

            for contract in server_contracts:
                try:
                    # Проверяем существование по ID
                    cursor.execute("SELECT id FROM contracts WHERE id = ?", (contract['id'],))
                    exists = cursor.fetchone()

                    if exists:
                        # Обновляем существующую запись
                        cursor.execute("""
                            UPDATE contracts SET
                                client_id = ?,
                                project_type = ?,
                                agent_type = ?,
                                city = ?,
                                contract_number = ?,
                                contract_date = ?,
                                address = ?,
                                area = ?,
                                total_amount = ?,
                                advance_payment = ?,
                                additional_payment = ?,
                                third_payment = ?,
                                contract_period = ?,
                                comments = ?,
                                status = ?,
                                termination_reason = ?,
                                measurement_image_link = ?,
                                measurement_file_name = ?,
                                measurement_yandex_path = ?,
                                measurement_date = ?,
                                contract_file_link = ?,
                                tech_task_link = ?,
                                updated_at = ?
                            WHERE id = ?
                        """, (
                            contract.get('client_id'),
                            contract.get('project_type'),
                            contract.get('agent_type'),
                            contract.get('city'),
                            contract.get('contract_number'),
                            contract.get('contract_date'),
                            contract.get('address'),
                            contract.get('area'),
                            contract.get('total_amount'),
                            contract.get('advance_payment'),
                            contract.get('additional_payment'),
                            contract.get('third_payment'),
                            contract.get('contract_period'),
                            contract.get('comments'),
                            contract.get('status'),
                            contract.get('termination_reason'),
                            contract.get('measurement_image_link'),
                            contract.get('measurement_file_name'),
                            contract.get('measurement_yandex_path'),
                            contract.get('measurement_date'),
                            contract.get('contract_file_link'),
                            contract.get('tech_task_link'),
                            datetime.now().isoformat(),
                            contract['id']
                        ))
                    else:
                        # Вставляем новую запись
                        cursor.execute("""
                            INSERT INTO contracts (
                                id, client_id, project_type, agent_type, city,
                                contract_number, contract_date, address, area,
                                total_amount, advance_payment, additional_payment,
                                third_payment, contract_period, comments, status,
                                termination_reason, measurement_image_link,
                                measurement_file_name, measurement_yandex_path,
                                measurement_date, contract_file_link, tech_task_link,
                                created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            contract['id'],
                            contract.get('client_id'),
                            contract.get('project_type'),
                            contract.get('agent_type'),
                            contract.get('city'),
                            contract.get('contract_number'),
                            contract.get('contract_date'),
                            contract.get('address'),
                            contract.get('area'),
                            contract.get('total_amount'),
                            contract.get('advance_payment'),
                            contract.get('additional_payment'),
                            contract.get('third_payment'),
                            contract.get('contract_period'),
                            contract.get('comments'),
                            contract.get('status'),
                            contract.get('termination_reason'),
                            contract.get('measurement_image_link'),
                            contract.get('measurement_file_name'),
                            contract.get('measurement_yandex_path'),
                            contract.get('measurement_date'),
                            contract.get('contract_file_link'),
                            contract.get('tech_task_link'),
                            datetime.now().isoformat(),
                            datetime.now().isoformat()
                        ))

                    synced_count += 1

                except Exception as e:
                    app_logger.info(f"[SYNC] Ошибка синхронизации договора {contract.get('id')}: {e}")

            conn.commit()
            self.db.close()

            return synced_count

        except Exception as e:
            app_logger.info(f"[SYNC] Ошибка синхронизации договоров: {e}")
            return 0

    def _sync_crm_cards(self) -> int:
        """Синхронизация CRM карточек с сервера в локальную БД"""
        try:
            synced_count = 0
            all_server_ids = set()

            # Синхронизируем карточки для обоих типов проектов
            for project_type in ['Индивидуальный', 'Шаблонный']:
                try:
                    server_cards = self.api.get_crm_cards(project_type)

                    if not server_cards:
                        continue

                    # Собираем все ID с сервера
                    for card in server_cards:
                        all_server_ids.add(card['id'])

                    conn = self.db.connect()
                    cursor = conn.cursor()

                    for card in server_cards:
                        try:
                            # Проверяем существование по ID
                            cursor.execute("SELECT id FROM crm_cards WHERE id = ?", (card['id'],))
                            exists = cursor.fetchone()

                            if exists:
                                # Обновляем существующую запись
                                cursor.execute("""
                                    UPDATE crm_cards SET
                                        contract_id = ?,
                                        column_name = ?,
                                        deadline = ?,
                                        tags = ?,
                                        is_approved = ?,
                                        approval_deadline = ?,
                                        approval_stages = ?,
                                        project_data_link = ?,
                                        tech_task_file = ?,
                                        tech_task_date = ?,
                                        survey_date = ?,
                                        senior_manager_id = ?,
                                        sdp_id = ?,
                                        gap_id = ?,
                                        manager_id = ?,
                                        surveyor_id = ?,
                                        order_position = ?,
                                        updated_at = ?
                                    WHERE id = ?
                                """, (
                                    card.get('contract_id'),
                                    card.get('column_name'),
                                    card.get('deadline'),
                                    card.get('tags'),
                                    1 if card.get('is_approved') else 0,
                                    card.get('approval_deadline'),
                                    card.get('approval_stages') if isinstance(card.get('approval_stages'), str) else None,
                                    card.get('project_data_link'),
                                    card.get('tech_task_file'),
                                    card.get('tech_task_date'),
                                    card.get('survey_date'),
                                    card.get('senior_manager_id'),
                                    card.get('sdp_id'),
                                    card.get('gap_id'),
                                    card.get('manager_id'),
                                    card.get('surveyor_id'),
                                    card.get('order_position'),
                                    datetime.now().isoformat(),
                                    card['id']
                                ))
                            else:
                                # Вставляем новую запись
                                cursor.execute("""
                                    INSERT INTO crm_cards (
                                        id, contract_id, column_name, deadline, tags,
                                        is_approved, approval_deadline, approval_stages,
                                        project_data_link, tech_task_file, tech_task_date,
                                        survey_date, senior_manager_id, sdp_id, gap_id,
                                        manager_id, surveyor_id, order_position,
                                        created_at, updated_at
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    card['id'],
                                    card.get('contract_id'),
                                    card.get('column_name'),
                                    card.get('deadline'),
                                    card.get('tags'),
                                    1 if card.get('is_approved') else 0,
                                    card.get('approval_deadline'),
                                    card.get('approval_stages') if isinstance(card.get('approval_stages'), str) else None,
                                    card.get('project_data_link'),
                                    card.get('tech_task_file'),
                                    card.get('tech_task_date'),
                                    card.get('survey_date'),
                                    card.get('senior_manager_id'),
                                    card.get('sdp_id'),
                                    card.get('gap_id'),
                                    card.get('manager_id'),
                                    card.get('surveyor_id'),
                                    card.get('order_position'),
                                    datetime.now().isoformat(),
                                    datetime.now().isoformat()
                                ))

                            synced_count += 1

                        except Exception as e:
                            app_logger.info(f"[SYNC] Ошибка синхронизации CRM карточки {card.get('id')}: {e}")

                    conn.commit()
                    self.db.close()

                except Exception as e:
                    app_logger.info(f"[SYNC] Ошибка получения CRM карточек ({project_type}): {e}")

            # Удаляем CRM карточки, которых нет на сервере
            if all_server_ids:
                conn = self.db.connect()
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM crm_cards")
                local_ids = set(row[0] for row in cursor.fetchall())
                ids_to_delete = local_ids - all_server_ids
                if ids_to_delete:
                    cursor.execute(f"DELETE FROM crm_cards WHERE id IN ({','.join('?' * len(ids_to_delete))})",
                                  tuple(ids_to_delete))
                    app_logger.info(f"[SYNC] Удалено {len(ids_to_delete)} устаревших CRM карточек")
                conn.commit()
                self.db.close()

            return synced_count

        except Exception as e:
            app_logger.info(f"[SYNC] Ошибка синхронизации CRM карточек: {e}")
            return 0

    def _sync_supervision_cards(self) -> int:
        """Синхронизация карточек надзора с сервера в локальную БД"""
        try:
            # Получаем данные с сервера
            server_cards = self.api.get_supervision_cards(status='active')

            conn = self.db.connect()
            cursor = conn.cursor()

            # Удаляем карточки надзора, которых нет на сервере
            if server_cards:
                server_ids = set(c['id'] for c in server_cards)
                cursor.execute("SELECT id FROM supervision_cards")
                local_ids = set(row[0] for row in cursor.fetchall())
                ids_to_delete = local_ids - server_ids
                if ids_to_delete:
                    cursor.execute(f"DELETE FROM supervision_cards WHERE id IN ({','.join('?' * len(ids_to_delete))})",
                                  tuple(ids_to_delete))
                    app_logger.info(f"[SYNC] Удалено {len(ids_to_delete)} устаревших карточек надзора")
            else:
                cursor.execute("DELETE FROM supervision_cards")
                conn.commit()
                self.db.close()
                return 0

            synced_count = 0

            for card in server_cards:
                try:
                    # Проверяем существование по ID
                    cursor.execute("SELECT id FROM supervision_cards WHERE id = ?", (card['id'],))
                    exists = cursor.fetchone()

                    if exists:
                        # Обновляем существующую запись
                        cursor.execute("""
                            UPDATE supervision_cards SET
                                contract_id = ?,
                                column_name = ?,
                                deadline = ?,
                                tags = ?,
                                senior_manager_id = ?,
                                dan_id = ?,
                                dan_completed = ?,
                                is_paused = ?,
                                pause_reason = ?,
                                paused_at = ?,
                                updated_at = ?
                            WHERE id = ?
                        """, (
                            card.get('contract_id'),
                            card.get('column_name'),
                            card.get('deadline'),
                            card.get('tags'),
                            card.get('senior_manager_id'),
                            card.get('dan_id'),
                            1 if card.get('dan_completed') else 0,
                            1 if card.get('is_paused') else 0,
                            card.get('pause_reason'),
                            card.get('paused_at'),
                            datetime.now().isoformat(),
                            card['id']
                        ))
                    else:
                        # Вставляем новую запись
                        cursor.execute("""
                            INSERT INTO supervision_cards (
                                id, contract_id, column_name, deadline, tags,
                                senior_manager_id, dan_id, dan_completed,
                                is_paused, pause_reason, paused_at,
                                created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            card['id'],
                            card.get('contract_id'),
                            card.get('column_name'),
                            card.get('deadline'),
                            card.get('tags'),
                            card.get('senior_manager_id'),
                            card.get('dan_id'),
                            1 if card.get('dan_completed') else 0,
                            1 if card.get('is_paused') else 0,
                            card.get('pause_reason'),
                            card.get('paused_at'),
                            datetime.now().isoformat(),
                            datetime.now().isoformat()
                        ))

                    synced_count += 1

                except Exception as e:
                    app_logger.info(f"[SYNC] Ошибка синхронизации карточки надзора {card.get('id')}: {e}")

            conn.commit()
            self.db.close()

            return synced_count

        except Exception as e:
            app_logger.info(f"[SYNC] Ошибка синхронизации карточек надзора: {e}")
            return 0

    def _sync_rates(self) -> int:
        """Синхронизация тарифов с сервера в локальную БД"""
        try:
            # Получаем данные с сервера
            server_rates = self.api.get_rates()

            if not server_rates:
                return 0

            conn = self.db.connect()
            cursor = conn.cursor()

            synced_count = 0

            for rate in server_rates:
                try:
                    # Проверяем существование по ID
                    cursor.execute("SELECT id FROM rates WHERE id = ?", (rate['id'],))
                    exists = cursor.fetchone()

                    # Маппинг полей сервера на локальную БД
                    # Сервер: price -> локальная БД: fixed_price
                    fixed_price = rate.get('price') or rate.get('fixed_price')

                    if exists:
                        # Обновляем существующую запись
                        cursor.execute("""
                            UPDATE rates SET
                                project_type = ?,
                                role = ?,
                                stage_name = ?,
                                area_from = ?,
                                area_to = ?,
                                fixed_price = ?,
                                rate_per_m2 = ?,
                                city = ?,
                                surveyor_price = ?,
                                updated_at = ?
                            WHERE id = ?
                        """, (
                            rate.get('project_type'),
                            rate.get('role'),
                            rate.get('stage_name'),
                            rate.get('area_from'),
                            rate.get('area_to'),
                            fixed_price,
                            rate.get('rate_per_m2'),
                            rate.get('city'),
                            rate.get('surveyor_price'),
                            datetime.now().isoformat(),
                            rate['id']
                        ))
                    else:
                        # Вставляем новую запись
                        cursor.execute("""
                            INSERT INTO rates (
                                id, project_type, role, stage_name,
                                area_from, area_to, fixed_price, rate_per_m2,
                                city, surveyor_price,
                                created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            rate['id'],
                            rate.get('project_type'),
                            rate.get('role'),
                            rate.get('stage_name'),
                            rate.get('area_from'),
                            rate.get('area_to'),
                            fixed_price,
                            rate.get('rate_per_m2'),
                            rate.get('city'),
                            rate.get('surveyor_price'),
                            datetime.now().isoformat(),
                            datetime.now().isoformat()
                        ))

                    synced_count += 1

                except Exception as e:
                    app_logger.info(f"[SYNC] Ошибка синхронизации тарифа {rate.get('id')}: {e}")

            conn.commit()
            self.db.close()

            return synced_count

        except Exception as e:
            app_logger.info(f"[SYNC] Ошибка синхронизации тарифов: {e}")
            return 0

    def _sync_payments(self) -> int:
        """Синхронизация платежей с сервера в локальную БД"""
        try:
            # Получаем данные с сервера
            server_payments = self.api.get_all_payments()

            if not server_payments:
                return 0

            conn = self.db.connect()
            cursor = conn.cursor()

            # Получаем ID всех платежей с сервера
            server_ids = set(p['id'] for p in server_payments)

            # Удаляем платежи, которых нет на сервере
            cursor.execute("SELECT id FROM payments")
            local_ids = set(row[0] for row in cursor.fetchall())
            ids_to_delete = local_ids - server_ids
            if ids_to_delete:
                cursor.execute(f"DELETE FROM payments WHERE id IN ({','.join('?' * len(ids_to_delete))})",
                              tuple(ids_to_delete))
                app_logger.info(f"[SYNC] Удалено {len(ids_to_delete)} устаревших платежей")

            synced_count = 0

            for payment in server_payments:
                try:
                    cursor.execute("SELECT id FROM payments WHERE id = ?", (payment['id'],))
                    exists = cursor.fetchone()

                    # Подготовка данных с обработкой None значений
                    payment_data = {
                        'contract_id': payment.get('contract_id'),
                        'crm_card_id': payment.get('crm_card_id'),
                        'supervision_card_id': payment.get('supervision_card_id'),
                        'employee_id': payment.get('employee_id'),
                        'role': payment.get('role') or '',
                        'stage_name': payment.get('stage_name') or '',
                        'calculated_amount': payment.get('calculated_amount') or 0.0,
                        'manual_amount': payment.get('manual_amount') or 0.0,
                        'final_amount': payment.get('final_amount') or 0.0,
                        'is_manual': payment.get('is_manual', False),
                        'payment_type': payment.get('payment_type') or '',
                        'report_month': payment.get('report_month') or '',
                        'payment_status': payment.get('payment_status') or '',
                        'is_paid': payment.get('is_paid', False),
                        'paid_date': payment.get('paid_date'),
                        'paid_by': payment.get('paid_by'),
                        'reassigned': payment.get('reassigned', False),
                        'old_employee_id': payment.get('old_employee_id'),
                    }

                    if exists:
                        cursor.execute("""
                            UPDATE payments SET
                                contract_id = ?,
                                crm_card_id = ?,
                                supervision_card_id = ?,
                                employee_id = ?,
                                role = ?,
                                stage_name = ?,
                                calculated_amount = ?,
                                manual_amount = ?,
                                final_amount = ?,
                                is_manual = ?,
                                payment_type = ?,
                                report_month = ?,
                                payment_status = ?,
                                is_paid = ?,
                                paid_date = ?,
                                paid_by = ?,
                                reassigned = ?,
                                old_employee_id = ?,
                                updated_at = ?
                            WHERE id = ?
                        """, (
                            payment_data['contract_id'],
                            payment_data['crm_card_id'],
                            payment_data['supervision_card_id'],
                            payment_data['employee_id'],
                            payment_data['role'],
                            payment_data['stage_name'],
                            payment_data['calculated_amount'],
                            payment_data['manual_amount'],
                            payment_data['final_amount'],
                            payment_data['is_manual'],
                            payment_data['payment_type'],
                            payment_data['report_month'],
                            payment_data['payment_status'],
                            payment_data['is_paid'],
                            payment_data['paid_date'],
                            payment_data['paid_by'],
                            payment_data['reassigned'],
                            payment_data['old_employee_id'],
                            datetime.now().isoformat(),
                            payment['id']
                        ))
                    else:
                        cursor.execute("""
                            INSERT INTO payments (
                                id, contract_id, crm_card_id, supervision_card_id,
                                employee_id, role, stage_name,
                                calculated_amount, manual_amount, final_amount,
                                is_manual, payment_type, report_month, payment_status,
                                is_paid, paid_date, paid_by,
                                reassigned, old_employee_id,
                                created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            payment['id'],
                            payment_data['contract_id'],
                            payment_data['crm_card_id'],
                            payment_data['supervision_card_id'],
                            payment_data['employee_id'],
                            payment_data['role'],
                            payment_data['stage_name'],
                            payment_data['calculated_amount'],
                            payment_data['manual_amount'],
                            payment_data['final_amount'],
                            payment_data['is_manual'],
                            payment_data['payment_type'],
                            payment_data['report_month'],
                            payment_data['payment_status'],
                            payment_data['is_paid'],
                            payment_data['paid_date'],
                            payment_data['paid_by'],
                            payment_data['reassigned'],
                            payment_data['old_employee_id'],
                            datetime.now().isoformat(),
                            datetime.now().isoformat()
                        ))

                    synced_count += 1

                except Exception as e:
                    app_logger.info(f"[SYNC] Ошибка синхронизации платежа {payment.get('id')}: {e}")

            conn.commit()
            self.db.close()

            return synced_count

        except Exception as e:
            app_logger.info(f"[SYNC] Ошибка синхронизации платежей: {e}")
            return 0

    def _sync_project_files(self) -> int:
        """Синхронизация файлов проектов с сервера в локальную БД"""
        try:
            # Получаем все файлы с сервера
            server_files = self.api.get_all_project_files()

            if not server_files:
                return 0

            conn = self.db.connect()
            cursor = conn.cursor()

            # Получаем ID всех файлов с сервера
            server_ids = set(f['id'] for f in server_files)

            # Удаляем файлы, которых нет на сервере
            cursor.execute("SELECT id FROM project_files")
            local_ids = set(row[0] for row in cursor.fetchall())
            ids_to_delete = local_ids - server_ids
            if ids_to_delete:
                cursor.execute(f"DELETE FROM project_files WHERE id IN ({','.join('?' * len(ids_to_delete))})",
                              tuple(ids_to_delete))
                app_logger.info(f"[SYNC] Удалено {len(ids_to_delete)} устаревших файлов")

            synced_count = 0

            for file in server_files:
                try:
                    cursor.execute("SELECT id FROM project_files WHERE id = ?", (file['id'],))
                    exists = cursor.fetchone()

                    if exists:
                        cursor.execute("""
                            UPDATE project_files SET
                                contract_id = ?,
                                stage = ?,
                                file_type = ?,
                                public_link = ?,
                                yandex_path = ?,
                                file_name = ?,
                                preview_cache_path = ?,
                                file_order = ?,
                                variation = ?
                            WHERE id = ?
                        """, (
                            file.get('contract_id'),
                            file.get('stage'),
                            file.get('file_type'),
                            file.get('public_link'),
                            file.get('yandex_path'),
                            file.get('file_name'),
                            file.get('preview_cache_path'),
                            file.get('file_order', 0),
                            file.get('variation', 1),
                            file['id']
                        ))
                    else:
                        cursor.execute("""
                            INSERT INTO project_files (
                                id, contract_id, stage, file_type, public_link,
                                yandex_path, file_name, preview_cache_path,
                                file_order, variation
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            file['id'],
                            file.get('contract_id'),
                            file.get('stage'),
                            file.get('file_type'),
                            file.get('public_link'),
                            file.get('yandex_path'),
                            file.get('file_name'),
                            file.get('preview_cache_path'),
                            file.get('file_order', 0),
                            file.get('variation', 1)
                        ))

                    synced_count += 1

                except Exception as e:
                    app_logger.info(f"[SYNC] Ошибка синхронизации файла {file.get('id')}: {e}")

            conn.commit()
            self.db.close()

            return synced_count

        except Exception as e:
            app_logger.info(f"[SYNC] Ошибка синхронизации файлов проектов: {e}")
            return 0

    def _sync_salaries(self) -> int:
        """Синхронизация зарплат с сервера в локальную БД"""
        try:
            server_salaries = self.api.get_salaries()

            if not server_salaries:
                return 0

            conn = self.db.connect()
            cursor = conn.cursor()

            # Удаляем записи, которых нет на сервере
            server_ids = set(s['id'] for s in server_salaries)
            cursor.execute("SELECT id FROM salaries")
            local_ids = set(row[0] for row in cursor.fetchall())
            ids_to_delete = local_ids - server_ids
            if ids_to_delete:
                cursor.execute(f"DELETE FROM salaries WHERE id IN ({','.join('?' * len(ids_to_delete))})",
                              tuple(ids_to_delete))

            synced_count = 0

            for salary in server_salaries:
                try:
                    cursor.execute("SELECT id FROM salaries WHERE id = ?", (salary['id'],))
                    exists = cursor.fetchone()

                    if exists:
                        cursor.execute("""
                            UPDATE salaries SET
                                employee_id = ?,
                                contract_id = ?,
                                amount = ?,
                                salary_type = ?,
                                period = ?,
                                status = ?,
                                payment_date = ?,
                                updated_at = ?
                            WHERE id = ?
                        """, (
                            salary.get('employee_id'),
                            salary.get('contract_id'),
                            salary.get('amount'),
                            salary.get('salary_type'),
                            salary.get('period'),
                            salary.get('status'),
                            salary.get('payment_date'),
                            datetime.now().isoformat(),
                            salary['id']
                        ))
                    else:
                        cursor.execute("""
                            INSERT INTO salaries (
                                id, employee_id, contract_id, amount, salary_type,
                                period, status, payment_date, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            salary['id'],
                            salary.get('employee_id'),
                            salary.get('contract_id'),
                            salary.get('amount'),
                            salary.get('salary_type'),
                            salary.get('period'),
                            salary.get('status'),
                            salary.get('payment_date'),
                            datetime.now().isoformat(),
                            datetime.now().isoformat()
                        ))

                    synced_count += 1

                except Exception as e:
                    app_logger.info(f"[SYNC] Ошибка синхронизации зарплаты {salary.get('id')}: {e}")

            conn.commit()
            self.db.close()

            return synced_count

        except Exception as e:
            app_logger.info(f"[SYNC] Ошибка синхронизации зарплат: {e}")
            return 0

    def _sync_stage_executors(self) -> int:
        """Синхронизация исполнителей стадий с сервера в локальную БД"""
        try:
            server_executors = self.api.get_all_stage_executors()

            if not server_executors:
                return 0

            conn = self.db.connect()
            cursor = conn.cursor()

            # Удаляем записи, которых нет на сервере
            server_ids = set(e['id'] for e in server_executors)
            cursor.execute("SELECT id FROM stage_executors")
            local_ids = set(row[0] for row in cursor.fetchall())
            ids_to_delete = local_ids - server_ids
            if ids_to_delete:
                cursor.execute(f"DELETE FROM stage_executors WHERE id IN ({','.join('?' * len(ids_to_delete))})",
                              tuple(ids_to_delete))
                app_logger.info(f"[SYNC] Удалено {len(ids_to_delete)} устаревших исполнителей стадий")

            synced_count = 0

            for executor in server_executors:
                try:
                    cursor.execute("SELECT id FROM stage_executors WHERE id = ?", (executor['id'],))
                    exists = cursor.fetchone()

                    if exists:
                        cursor.execute("""
                            UPDATE stage_executors SET
                                crm_card_id = ?,
                                stage_name = ?,
                                executor_id = ?,
                                assigned_date = ?,
                                assigned_by = ?,
                                deadline = ?,
                                completed = ?,
                                completed_date = ?,
                                submitted_date = ?
                            WHERE id = ?
                        """, (
                            executor.get('crm_card_id'),
                            executor.get('stage_name'),
                            executor.get('executor_id'),
                            executor.get('assigned_date'),
                            executor.get('assigned_by'),
                            executor.get('deadline'),
                            1 if executor.get('completed') else 0,
                            executor.get('completed_date'),
                            executor.get('submitted_date'),
                            executor['id']
                        ))
                    else:
                        cursor.execute("""
                            INSERT INTO stage_executors (
                                id, crm_card_id, stage_name, executor_id,
                                assigned_date, assigned_by, deadline,
                                completed, completed_date, submitted_date
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            executor['id'],
                            executor.get('crm_card_id'),
                            executor.get('stage_name'),
                            executor.get('executor_id'),
                            executor.get('assigned_date'),
                            executor.get('assigned_by'),
                            executor.get('deadline'),
                            1 if executor.get('completed') else 0,
                            executor.get('completed_date'),
                            executor.get('submitted_date')
                        ))

                    synced_count += 1

                except Exception as e:
                    app_logger.info(f"[SYNC] Ошибка синхронизации исполнителя {executor.get('id')}: {e}")

            conn.commit()
            self.db.close()

            return synced_count

        except Exception as e:
            app_logger.info(f"[SYNC] Ошибка синхронизации исполнителей стадий: {e}")
            return 0

    def _sync_approval_stage_deadlines(self) -> int:
        """Синхронизация дедлайнов согласования с сервера в локальную БД"""
        try:
            server_deadlines = self.api.get_all_approval_deadlines()

            if not server_deadlines:
                return 0

            conn = self.db.connect()
            cursor = conn.cursor()

            # Удаляем записи, которых нет на сервере
            server_ids = set(d['id'] for d in server_deadlines)
            cursor.execute("SELECT id FROM approval_stage_deadlines")
            local_ids = set(row[0] for row in cursor.fetchall())
            ids_to_delete = local_ids - server_ids
            if ids_to_delete:
                cursor.execute(f"DELETE FROM approval_stage_deadlines WHERE id IN ({','.join('?' * len(ids_to_delete))})",
                              tuple(ids_to_delete))
                app_logger.info(f"[SYNC] Удалено {len(ids_to_delete)} устаревших дедлайнов согласования")

            synced_count = 0

            for deadline in server_deadlines:
                try:
                    cursor.execute("SELECT id FROM approval_stage_deadlines WHERE id = ?", (deadline['id'],))
                    exists = cursor.fetchone()

                    if exists:
                        cursor.execute("""
                            UPDATE approval_stage_deadlines SET
                                crm_card_id = ?,
                                stage_name = ?,
                                deadline = ?,
                                is_completed = ?,
                                completed_date = ?
                            WHERE id = ?
                        """, (
                            deadline.get('crm_card_id'),
                            deadline.get('stage_name'),
                            deadline.get('deadline'),
                            1 if deadline.get('is_completed') else 0,
                            deadline.get('completed_date'),
                            deadline['id']
                        ))
                    else:
                        cursor.execute("""
                            INSERT INTO approval_stage_deadlines (
                                id, crm_card_id, stage_name, deadline,
                                is_completed, completed_date, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            deadline['id'],
                            deadline.get('crm_card_id'),
                            deadline.get('stage_name'),
                            deadline.get('deadline'),
                            1 if deadline.get('is_completed') else 0,
                            deadline.get('completed_date'),
                            deadline.get('created_at', datetime.now().isoformat())
                        ))

                    synced_count += 1

                except Exception as e:
                    app_logger.info(f"[SYNC] Ошибка синхронизации дедлайна {deadline.get('id')}: {e}")

            conn.commit()
            self.db.close()

            return synced_count

        except Exception as e:
            app_logger.info(f"[SYNC] Ошибка синхронизации дедлайнов согласования: {e}")
            return 0

    def _sync_action_history(self) -> int:
        """Синхронизация истории действий с сервера в локальную БД"""
        try:
            server_history = self.api.get_all_action_history()

            if not server_history:
                return 0

            conn = self.db.connect()
            cursor = conn.cursor()

            # Удаляем записи, которых нет на сервере
            server_ids = set(h['id'] for h in server_history)
            cursor.execute("SELECT id FROM action_history")
            local_ids = set(row[0] for row in cursor.fetchall())
            ids_to_delete = local_ids - server_ids
            if ids_to_delete:
                cursor.execute(f"DELETE FROM action_history WHERE id IN ({','.join('?' * len(ids_to_delete))})",
                              tuple(ids_to_delete))
                app_logger.info(f"[SYNC] Удалено {len(ids_to_delete)} устаревших записей истории действий")

            synced_count = 0

            for history in server_history:
                try:
                    cursor.execute("SELECT id FROM action_history WHERE id = ?", (history['id'],))
                    exists = cursor.fetchone()

                    if exists:
                        cursor.execute("""
                            UPDATE action_history SET
                                user_id = ?,
                                action_type = ?,
                                entity_type = ?,
                                entity_id = ?,
                                description = ?,
                                action_date = ?
                            WHERE id = ?
                        """, (
                            history.get('user_id'),
                            history.get('action_type'),
                            history.get('entity_type'),
                            history.get('entity_id'),
                            history.get('description'),
                            history.get('action_date'),
                            history['id']
                        ))
                    else:
                        cursor.execute("""
                            INSERT INTO action_history (
                                id, user_id, action_type, entity_type,
                                entity_id, description, action_date
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            history['id'],
                            history.get('user_id'),
                            history.get('action_type'),
                            history.get('entity_type'),
                            history.get('entity_id'),
                            history.get('description'),
                            history.get('action_date', datetime.now().isoformat())
                        ))

                    synced_count += 1

                except Exception as e:
                    app_logger.info(f"[SYNC] Ошибка синхронизации истории {history.get('id')}: {e}")

            conn.commit()
            self.db.close()

            return synced_count

        except Exception as e:
            app_logger.info(f"[SYNC] Ошибка синхронизации истории действий: {e}")
            return 0

    def _sync_supervision_project_history(self) -> int:
        """Синхронизация истории проектов надзора с сервера в локальную БД"""
        try:
            server_history = self.api.get_all_supervision_history()

            if not server_history:
                return 0

            conn = self.db.connect()
            cursor = conn.cursor()

            # Удаляем записи, которых нет на сервере
            server_ids = set(h['id'] for h in server_history)
            cursor.execute("SELECT id FROM supervision_project_history")
            local_ids = set(row[0] for row in cursor.fetchall())
            ids_to_delete = local_ids - server_ids
            if ids_to_delete:
                cursor.execute(f"DELETE FROM supervision_project_history WHERE id IN ({','.join('?' * len(ids_to_delete))})",
                              tuple(ids_to_delete))
                app_logger.info(f"[SYNC] Удалено {len(ids_to_delete)} устаревших записей истории надзора")

            synced_count = 0

            for history in server_history:
                try:
                    cursor.execute("SELECT id FROM supervision_project_history WHERE id = ?", (history['id'],))
                    exists = cursor.fetchone()

                    if exists:
                        cursor.execute("""
                            UPDATE supervision_project_history SET
                                supervision_card_id = ?,
                                entry_type = ?,
                                message = ?,
                                created_by = ?,
                                created_at = ?
                            WHERE id = ?
                        """, (
                            history.get('supervision_card_id'),
                            history.get('entry_type'),
                            history.get('message'),
                            history.get('created_by'),
                            history.get('created_at'),
                            history['id']
                        ))
                    else:
                        cursor.execute("""
                            INSERT INTO supervision_project_history (
                                id, supervision_card_id, entry_type,
                                message, created_by, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            history['id'],
                            history.get('supervision_card_id'),
                            history.get('entry_type'),
                            history.get('message'),
                            history.get('created_by'),
                            history.get('created_at', datetime.now().isoformat())
                        ))

                    synced_count += 1

                except Exception as e:
                    app_logger.info(f"[SYNC] Ошибка синхронизации истории надзора {history.get('id')}: {e}")

            conn.commit()
            self.db.close()

            return synced_count

        except Exception as e:
            app_logger.info(f"[SYNC] Ошибка синхронизации истории проектов надзора: {e}")
            return 0


def sync_on_login(db_manager, api_client, progress_callback=None) -> Dict[str, Any]:
    """
    Функция для вызова синхронизации при входе в систему.

    Args:
        db_manager: Экземпляр DatabaseManager
        api_client: Экземпляр APIClient (уже авторизованный)
        progress_callback: Функция обратного вызова для прогресса

    Returns:
        Результат синхронизации
    """
    synchronizer = DatabaseSynchronizer(db_manager, api_client)
    return synchronizer.sync_all(progress_callback)


def verify_data_integrity(db_manager, api_client) -> Dict[str, Any]:
    """
    Проверка целостности данных между локальной и серверной БД.

    Args:
        db_manager: Экземпляр DatabaseManager
        api_client: Экземпляр APIClient

    Returns:
        Dict с результатами проверки:
            - is_synced: bool - данные синхронизированы
            - discrepancies: List - список расхождений
            - local_counts: Dict - количество записей в локальной БД
            - server_counts: Dict - количество записей на сервере
    """
    synchronizer = DatabaseSynchronizer(db_manager, api_client)
    return synchronizer.verify_integrity()


class IntegrityChecker:
    """
    Класс для проверки целостности данных.
    Может использоваться для периодической проверки синхронизации.
    """

    def __init__(self, db_manager, api_client):
        self.db = db_manager
        self.api = api_client
        self.last_check_result = None

    def check(self) -> Dict[str, Any]:
        """Выполнить проверку целостности"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'is_synced': True,
            'discrepancies': [],
            'local_counts': {},
            'server_counts': {}
        }

        tables_to_check = [
            ('employees', lambda: self.api.get_employees(limit=10000)),
            ('clients', lambda: self.api.get_clients(limit=10000)),
            ('contracts', lambda: self.api.get_contracts(limit=10000)),
            ('crm_cards', lambda: self._get_all_crm_cards()),
            ('supervision_cards', lambda: self.api.get_supervision_cards(limit=10000)),
            ('payments', lambda: self.api.get_all_payments()),
            ('rates', lambda: self.api.get_rates()),
        ]

        conn = self.db.connect()
        cursor = conn.cursor()

        for table_name, api_getter in tables_to_check:
            try:
                # Получаем количество записей локально
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                local_count = cursor.fetchone()[0]
                result['local_counts'][table_name] = local_count

                # Получаем количество записей с сервера
                try:
                    server_data = api_getter()
                    server_count = len(server_data) if server_data else 0
                except Exception as e:
                    print(f"[INTEGRITY] Ошибка получения {table_name} с сервера: {e}")
                    server_count = -1  # Ошибка

                result['server_counts'][table_name] = server_count

                # Сравниваем
                if server_count >= 0 and local_count != server_count:
                    result['is_synced'] = False
                    discrepancy = {
                        'table': table_name,
                        'local_count': local_count,
                        'server_count': server_count,
                        'difference': local_count - server_count
                    }
                    result['discrepancies'].append(discrepancy)
                    print(f"[INTEGRITY WARNING] {table_name}: локально={local_count}, сервер={server_count}")

            except Exception as e:
                print(f"[INTEGRITY ERROR] Ошибка проверки {table_name}: {e}")

        self.db.close()
        self.last_check_result = result

        # Логируем результат
        if result['is_synced']:
            print("[INTEGRITY] Данные синхронизированы")
        else:
            print(f"[INTEGRITY] Обнаружены расхождения: {len(result['discrepancies'])} таблиц")

        return result

    def _get_all_crm_cards(self) -> List[Dict]:
        """Получить все CRM карточки (все типы проектов)"""
        all_cards = []
        for project_type in ['Дизайн-проект', 'Комплектация', 'Надзор']:
            try:
                cards = self.api.get_crm_cards(project_type)
                if cards:
                    all_cards.extend(cards)
            except Exception:
                pass
        return all_cards

    def get_sync_status_summary(self) -> str:
        """Получить краткую сводку о статусе синхронизации"""
        if not self.last_check_result:
            return "Проверка не выполнялась"

        result = self.last_check_result
        if result['is_synced']:
            return "Данные синхронизированы"

        discrepancies = result['discrepancies']
        summary_parts = []
        for d in discrepancies:
            diff = d['difference']
            direction = "больше локально" if diff > 0 else "больше на сервере"
            summary_parts.append(f"{d['table']}: {abs(diff)} {direction}")

        return "Расхождения: " + "; ".join(summary_parts)
