"""
Скрипт миграции данных из локальной SQLite в PostgreSQL на сервере
Переносит все данные через REST API
"""
import sqlite3
import sys
from datetime import datetime
from utils.api_client import APIClient
from config import API_BASE_URL

class DataMigrator:
    def __init__(self, sqlite_path: str, api_url: str, admin_login: str, admin_password: str):
        self.sqlite_path = sqlite_path
        self.api_client = APIClient(api_url)
        self.admin_login = admin_login
        self.admin_password = admin_password
        self.stats = {
            'employees': {'total': 0, 'migrated': 0, 'errors': 0},
            'clients': {'total': 0, 'migrated': 0, 'errors': 0},
            'contracts': {'total': 0, 'migrated': 0, 'errors': 0},
            'crm_cards': {'total': 0, 'migrated': 0, 'errors': 0},
            'supervision_cards': {'total': 0, 'migrated': 0, 'errors': 0},
        }

    def connect_sqlite(self):
        """Подключение к SQLite базе"""
        print(f"\nConnecting to SQLite: {self.sqlite_path}")
        self.conn = sqlite3.connect(self.sqlite_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        print("[OK] Connected to SQLite")

    def authenticate(self):
        """Аутентификация на сервере"""
        print(f"\nAuthenticating to server: {self.api_client.base_url}")
        try:
            result = self.api_client.login(self.admin_login, self.admin_password)
            print(f"[OK] Logged in: {result['full_name']} ({result['role']})")
            return True
        except Exception as e:
            print(f"[ERROR] Authentication failed: {e}")
            return False

    def migrate_employees(self):
        """Миграция сотрудников"""
        print("\n" + "="*60)
        print("MIGRATING EMPLOYEES")
        print("="*60)

        # Получить всех сотрудников из SQLite
        self.cursor.execute("""
            SELECT id, full_name, phone, email, address, birth_date,
                   login, position, secondary_position, department, role,
                   status, hire_date, created_at, updated_at
            FROM employees
            WHERE login != 'admin'
        """)

        employees = self.cursor.fetchall()
        self.stats['employees']['total'] = len(employees)

        print(f"Found employees: {len(employees)}")

        # Словарь для маппинга старых ID в новые
        self.employee_id_map = {}

        for emp in employees:
            try:
                # Подготовка данных (используем только поля из старой схемы)
                employee_data = {
                    'full_name': emp['full_name'],
                    'phone': emp['phone'] or '+7 000 000-00-00',
                    'email': emp['email'],
                    'address': emp['address'],
                    'birth_date': emp['birth_date'],
                    'login': emp['login'],
                    'password': 'change_me_123',  # Временный пароль
                    'position': emp['position'],
                    'secondary_position': emp['secondary_position'],
                    'department': emp['department'],
                    'role': emp['role'],
                    'salary_type': 'fixed',  # Значение по умолчанию
                    'base_salary': 0.0,
                    'hourly_rate': 0.0,
                    'commission_rate': 0.0,
                    'status': emp['status'],
                    'hire_date': emp['hire_date'],
                    'termination_date': None,
                    'notes': ''
                }

                # Отправка на сервер
                print(f"  [DEBUG] Creating employee: login={employee_data['login']}, name={employee_data['full_name']}")
                result = self.api_client.create_employee(employee_data)

                # Сохранить маппинг ID
                old_id = emp['id']
                new_id = result['id']
                self.employee_id_map[old_id] = new_id

                self.stats['employees']['migrated'] += 1
                print(f"  [OK] {emp['full_name']} (ID: {old_id} -> {new_id})")

            except Exception as e:
                self.stats['employees']['errors'] += 1
                import traceback
                error_detail = traceback.format_exc()
                print(f"  [ERROR] {emp['full_name']}:")
                print(f"    {str(e)}")
                if "detail" in str(e):
                    print(f"    Full error: {error_detail[-500:]}")

        print(f"\nEmployees: {self.stats['employees']['migrated']}/{self.stats['employees']['total']} migrated")

    def migrate_clients(self):
        """Миграция клиентов"""
        print("\n" + "="*60)
        print("MIGRATING CLIENTS")
        print("="*60)

        # Получить всех клиентов из SQLite
        self.cursor.execute("""
            SELECT id, client_type, full_name, phone, email,
                   passport_series, passport_number, passport_issued_by, passport_issued_date,
                   registration_address, organization_type, organization_name, inn, ogrn,
                   account_details, responsible_person, created_at, updated_at
            FROM clients
        """)

        clients = self.cursor.fetchall()
        self.stats['clients']['total'] = len(clients)

        print(f"Found clients: {len(clients)}")

        # Словарь для маппинга старых ID в новые
        self.client_id_map = {}

        for client in clients:
            try:
                # Подготовка данных (из локальной схемы)
                client_data = {
                    'client_type': client['client_type'],
                    'full_name': client['full_name'],
                    'phone': client['phone'],
                    'email': client['email'],
                    'passport_series': client['passport_series'],
                    'passport_number': client['passport_number'],
                    'passport_issued_by': client['passport_issued_by'],
                    'passport_issued_date': client['passport_issued_date'],
                    'registration_address': client['registration_address'],
                    'organization_type': client['organization_type'],
                    'organization_name': client['organization_name'],
                    'inn': client['inn'],
                    'ogrn': client['ogrn'],
                    'account_details': client['account_details'],
                    'responsible_person': client['responsible_person']
                }

                # Отправка на сервер
                result = self.api_client.create_client(client_data)

                # Сохранить маппинг ID
                old_id = client['id']
                new_id = result['id']
                self.client_id_map[old_id] = new_id

                self.stats['clients']['migrated'] += 1
                print(f"  [OK] {client['full_name']} (ID: {old_id} -> {new_id})")

            except Exception as e:
                self.stats['clients']['errors'] += 1
                print(f"  [ERROR] {client['full_name']}: {e}")

        print(f"\nClients: {self.stats['clients']['migrated']}/{self.stats['clients']['total']} migrated")

    def migrate_contracts(self):
        """Миграция договоров"""
        print("\n" + "="*60)
        print("MIGRATING CONTRACTS")
        print("="*60)

        # Получить все договоры из SQLite
        self.cursor.execute("""
            SELECT id, client_id, project_type, agent_type, city, contract_number, contract_date,
                   address, area, total_amount, advance_payment, additional_payment, third_payment,
                   contract_period, comments, contract_file_link, tech_task_link, status,
                   termination_reason, created_at, updated_at, status_changed_date,
                   yandex_folder_path, measurement_image_link, measurement_date,
                   measurement_file_name, measurement_yandex_path, tech_task_file_name,
                   tech_task_yandex_path, contract_file_name, contract_file_yandex_path,
                   template_contract_file_name, template_contract_file_yandex_path,
                   template_contract_file_link, references_yandex_path,
                   photo_documentation_yandex_path
            FROM contracts
        """)

        contracts = self.cursor.fetchall()
        self.stats['contracts']['total'] = len(contracts)

        print(f"Found contracts: {len(contracts)}")

        for contract in contracts:
            try:
                # Подготовка данных (все поля из локальной БД)
                contract_data = {
                    'client_id': self.client_id_map.get(contract['client_id']),
                    'manager_id': None,  # В локальной БД нет manager_id
                    'project_type': contract['project_type'],
                    'agent_type': contract['agent_type'],
                    'city': contract['city'],
                    'contract_number': contract['contract_number'],
                    'contract_date': contract['contract_date'],
                    'address': contract['address'],
                    'area': float(contract['area']) if contract['area'] else None,
                    'total_amount': float(contract['total_amount']) if contract['total_amount'] else None,
                    'advance_payment': float(contract['advance_payment']) if contract['advance_payment'] else None,
                    'additional_payment': float(contract['additional_payment']) if contract['additional_payment'] else None,
                    'third_payment': float(contract['third_payment']) if contract['third_payment'] else None,
                    'contract_period': int(contract['contract_period']) if contract['contract_period'] else None,
                    'comments': contract['comments'],
                    'contract_file_link': contract['contract_file_link'],
                    'contract_file_name': contract['contract_file_name'],
                    'contract_file_yandex_path': contract['contract_file_yandex_path'],
                    'template_contract_file_link': contract['template_contract_file_link'],
                    'template_contract_file_name': contract['template_contract_file_name'],
                    'template_contract_file_yandex_path': contract['template_contract_file_yandex_path'],
                    'tech_task_link': contract['tech_task_link'],
                    'tech_task_file_name': contract['tech_task_file_name'],
                    'tech_task_yandex_path': contract['tech_task_yandex_path'],
                    'measurement_image_link': contract['measurement_image_link'],
                    'measurement_date': contract['measurement_date'],
                    'measurement_file_name': contract['measurement_file_name'],
                    'measurement_yandex_path': contract['measurement_yandex_path'],
                    'references_yandex_path': contract['references_yandex_path'],
                    'photo_documentation_yandex_path': contract['photo_documentation_yandex_path'],
                    'status': contract['status'],
                    'status_changed_date': contract['status_changed_date'],
                    'termination_reason': contract['termination_reason'],
                    'yandex_folder_path': contract['yandex_folder_path']
                }

                # Пропустить если клиент не мигрирован
                if not contract_data['client_id']:
                    print(f"  [SKIP] Contract #{contract['contract_number']}: client not found")
                    self.stats['contracts']['errors'] += 1
                    continue

                # Отправка на сервер
                result = self.api_client.create_contract(contract_data)

                self.stats['contracts']['migrated'] += 1
                print(f"  [OK] Contract #{contract['contract_number']} (ID: {contract['id']} -> {result['id']})")

            except Exception as e:
                self.stats['contracts']['errors'] += 1
                print(f"  [ERROR] Contract #{contract['contract_number']}: {e}")

        print(f"\nContracts: {self.stats['contracts']['migrated']}/{self.stats['contracts']['total']} migrated")

    def migrate_crm_cards(self):
        """Миграция CRM карточек"""
        print("\n" + "="*60)
        print("MIGRATING CRM CARDS")
        print("="*60)

        # Получить все CRM карточки из SQLite
        self.cursor.execute("""
            SELECT id, contract_id, column_name, deadline, tags, is_approved,
                   senior_manager_id, sdp_id, gap_id, manager_id, surveyor_id,
                   approval_deadline, approval_stages, project_data_link,
                   tech_task_file, tech_task_date, survey_date, order_position
            FROM crm_cards
        """)

        cards = self.cursor.fetchall()
        self.stats['crm_cards']['total'] = len(cards)

        print(f"Found CRM cards: {len(cards)}")

        for card in cards:
            try:
                # Подготовка данных
                card_data = {
                    'contract_id': card['contract_id'],
                    'column_name': card['column_name'] or 'Новый заказ',
                    'deadline': card['deadline'],
                    'tags': card['tags'],
                    'is_approved': bool(card['is_approved']),
                    'senior_manager_id': card['senior_manager_id'],
                    'sdp_id': card['sdp_id'],
                    'gap_id': card['gap_id'],
                    'manager_id': card['manager_id'],
                    'surveyor_id': card['surveyor_id'],
                    'approval_deadline': card['approval_deadline'],
                    'approval_stages': card['approval_stages'],
                    'project_data_link': card['project_data_link'],
                    'tech_task_file': card['tech_task_file'],
                    'tech_task_date': card['tech_task_date'],
                    'survey_date': card['survey_date'],
                    'order_position': card['order_position'] or 0
                }

                # Отправка на сервер
                result = self.api_client.create_crm_card(card_data)

                self.stats['crm_cards']['migrated'] += 1
                print(f"  [OK] CRM Card for contract #{card['contract_id']} (ID: {card['id']} -> {result['id']})")

            except Exception as e:
                self.stats['crm_cards']['errors'] += 1
                error_msg = str(e)
                if "уже существует" in error_msg or "already exists" in error_msg:
                    print(f"  [SKIP] CRM Card for contract #{card['contract_id']}: already exists")
                else:
                    print(f"  [ERROR] CRM Card for contract #{card['contract_id']}: {e}")

        print(f"\nCRM Cards: {self.stats['crm_cards']['migrated']}/{self.stats['crm_cards']['total']} migrated")

    def migrate_supervision_cards(self):
        """Миграция карточек авторского надзора"""
        print("\n" + "="*60)
        print("MIGRATING SUPERVISION CARDS")
        print("="*60)

        # Получить все карточки надзора из SQLite
        self.cursor.execute("""
            SELECT id, contract_id, column_name, deadline, tags,
                   senior_manager_id, dan_id, dan_completed,
                   is_paused, pause_reason, paused_at
            FROM supervision_cards
        """)

        cards = self.cursor.fetchall()
        self.stats['supervision_cards']['total'] = len(cards)

        print(f"Found Supervision cards: {len(cards)}")

        for card in cards:
            try:
                # Подготовка данных
                card_data = {
                    'contract_id': card['contract_id'],
                    'column_name': card['column_name'] or 'Новый заказ',
                    'deadline': card['deadline'],
                    'tags': card['tags'],
                    'senior_manager_id': card['senior_manager_id'],
                    'dan_id': card['dan_id'],
                    'dan_completed': bool(card['dan_completed']),
                    'is_paused': bool(card['is_paused']),
                    'pause_reason': card['pause_reason']
                }

                # Отправка на сервер
                result = self.api_client.create_supervision_card(card_data)

                self.stats['supervision_cards']['migrated'] += 1
                print(f"  [OK] Supervision Card for contract #{card['contract_id']} (ID: {card['id']} -> {result['id']})")

            except Exception as e:
                self.stats['supervision_cards']['errors'] += 1
                error_msg = str(e)
                if "уже существует" in error_msg or "already exists" in error_msg:
                    print(f"  [SKIP] Supervision Card for contract #{card['contract_id']}: already exists")
                else:
                    print(f"  [ERROR] Supervision Card for contract #{card['contract_id']}: {e}")

        print(f"\nSupervision Cards: {self.stats['supervision_cards']['migrated']}/{self.stats['supervision_cards']['total']} migrated")

    def print_summary(self):
        """Вывести итоговую статистику"""
        print("\n" + "="*60)
        print("MIGRATION SUMMARY")
        print("="*60)

        for entity, stats in self.stats.items():
            total = stats['total']
            migrated = stats['migrated']
            errors = stats['errors']

            if total > 0:
                success_rate = (migrated / total) * 100
                print(f"\n{entity.upper()}:")
                print(f"  Total: {total}")
                print(f"  Migrated: {migrated} ({success_rate:.1f}%)")
                print(f"  Errors: {errors}")

        print("\n" + "="*60)
        print("[OK] Migration completed!")
        print("="*60)

    def run(self):
        """Запуск миграции"""
        print("\n" + "="*60)
        print("DATA MIGRATION: SQLite -> PostgreSQL")
        print("="*60)
        print(f"Source: {self.sqlite_path}")
        print(f"Server: {self.api_client.base_url}")
        print("="*60)

        # Подключение
        self.connect_sqlite()

        if not self.authenticate():
            print("\n[ERROR] Cannot authenticate. Migration cancelled.")
            return False

        # Миграция данных
        try:
            self.migrate_employees()
            self.migrate_clients()
            self.migrate_contracts()
            self.migrate_crm_cards()
            self.migrate_supervision_cards()

            # Итоги
            self.print_summary()

            return True

        except Exception as e:
            print(f"\n[ERROR] Critical error: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            self.conn.close()
            print("\n[OK] SQLite connection closed")


def main():
    """Точка входа"""
    print("\n" + "="*60)
    print("DATA MIGRATION SCRIPT")
    print("="*60)

    # Настройки
    SQLITE_PATH = "interior_studio.db"
    ADMIN_LOGIN = "admin"
    ADMIN_PASSWORD = "admin123"

    print(f"\nSettings:")
    print(f"  SQLite database: {SQLITE_PATH}")
    print(f"  API server: {API_BASE_URL}")
    print(f"  Admin login: {ADMIN_LOGIN}")
    print(f"\nStarting migration automatically...")

    # Создание мигратора
    migrator = DataMigrator(
        sqlite_path=SQLITE_PATH,
        api_url=API_BASE_URL,
        admin_login=ADMIN_LOGIN,
        admin_password=ADMIN_PASSWORD
    )

    # Запуск
    success = migrator.run()

    if success:
        print("\n*** Migration completed successfully! ***")
        print("\nIMPORTANT:")
        print("1. All employees got temporary password: change_me_123")
        print("2. Ask them to change password on first login")
        print("3. Check the data in the application")
    else:
        print("\n*** Migration completed with errors ***")
        print("Check logs above for details")


if __name__ == '__main__':
    main()
