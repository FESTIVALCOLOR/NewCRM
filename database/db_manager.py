import sqlite3
from datetime import datetime
import json
import threading
from PyQt5.QtCore import QDate
from utils.password_utils import hash_password, verify_password
from utils.yandex_disk import YandexDiskManager
from config import YANDEX_DISK_TOKEN

class DatabaseManager:
    def __init__(self, db_path='interior_studio.db'):
        self.db_path = db_path
        self.connection = None
        
        # ========== КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ ==========
        # Создаем alias для совместимости со старым кодом
        self.conn = None  # Добавляем атрибут
        # =============================================

        # Выполняем миграции при инициализации
        self.run_migrations()
        self.create_supervision_table_migration()
        self.fix_supervision_cards_column_name()
        self.create_supervision_history_table()
        self.create_manager_acceptance_table()
        self.create_payments_system_tables()
        self.add_reassigned_field_to_payments()
        self.add_submitted_date_to_stage_executors()

    def run_migrations(self):
        """Запуск миграций базы данных"""
        try:
            import os
            if os.path.exists('database/migrations.py'):
                # Проверяем, нужна ли миграция
                conn = self.connect()
                cursor = conn.cursor()
                
                # Миграция №1: status и termination_reason
                cursor.execute("PRAGMA table_info(contracts)")
                columns = [column[1] for column in cursor.fetchall()]
                self.close()
                
                if 'status' not in columns or 'termination_reason' not in columns:
                    from database.migrations import add_contract_status_fields
                    add_contract_status_fields(self.db_path)
            
                # ========== НОВАЯ МИГРАЦИЯ №2 ==========
                # Добавляем поле approval_deadline в crm_cards
                self.add_approval_deadline_field()
                # =======================================

                # ========== МИГРАЦИЯ №3 ==========
                self.add_approval_stages_field()
                # =================================
                
                # ========== МИГРАЦИЯ №4: Таблица дедлайнов согласования ==========
                self.create_approval_deadlines_table()
                # =================================================================

                # ========== МИГРАЦИЯ №5 ==========
                self.add_project_data_link_field()
                # =================================

                # ========== МИГРАЦИЯ: third_payment =======
                self.add_third_payment_field()
                # ==========================================

                # ========== МИГРАЦИЯ: birth_date ==========
                self.add_birth_date_column()
                # ==========================================
                
                # ========== МИГРАЦИЯ: address ==========
                self.add_address_column()
                # =======================================
                
                # ========== МИГРАЦИЯ: secondary_position ==========
                self.add_secondary_position_column()
                # ==================================================

                # ========== МИГРАЦИЯ: status_changed_date ==========
                self.add_status_changed_date_column()
                # ===================================================

                # ========== МИГРАЦИЯ: tech_task fields ==========
                self.add_tech_task_fields()
                # ================================================

                # ========== МИГРАЦИЯ: survey_date ==========
                self.add_survey_date_column()
                # ===========================================

                # ========== МИГРАЦИЯ: project_files table ==========
                self.create_project_files_table()
                # ====================================================

        except Exception as e:
            print(f"[WARN] Предупреждение при миграции: {e}")

    def add_third_payment_field(self):
        """Миграция: добавление поля third_payment"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute("PRAGMA table_info(contracts)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'third_payment' not in columns:
                print("[>] Выполняется миграция: добавление third_payment...")
                cursor.execute("ALTER TABLE contracts ADD COLUMN third_payment REAL DEFAULT 0")
                conn.commit()
                print("[OK] Поле third_payment добавлено")
            else:
                print("[OK] Поле third_payment уже существует")
            
            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка миграции third_payment: {e}")
    
    def connect(self):
        """Подключение к БД"""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.conn = self.connection  # Alias для совместимости
        return self.connection
    
    def close(self):
        """Закрытие соединения"""
        if self.connection:
            self.connection.close()
    
    def initialize_database(self):
        """Создание всех таблиц"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Таблица сотрудников
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            status TEXT DEFAULT 'активный',
            position TEXT NOT NULL,
            department TEXT NOT NULL,
            legal_status TEXT,
            hire_date DATE,
            payment_details TEXT,
            login TEXT UNIQUE,
            password TEXT,
            role TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Таблица клиентов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_type TEXT NOT NULL,
            full_name TEXT,
            phone TEXT NOT NULL,
            email TEXT,
            passport_series TEXT,
            passport_number TEXT,
            passport_issued_by TEXT,
            passport_issued_date DATE,
            registration_address TEXT,
            organization_type TEXT,
            organization_name TEXT,
            inn TEXT,
            ogrn TEXT,
            account_details TEXT,
            responsible_person TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Таблица договоров
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            project_type TEXT NOT NULL,
            agent_type TEXT,
            city TEXT,
            contract_number TEXT UNIQUE NOT NULL,
            contract_date DATE,
            address TEXT,
            area REAL,
            total_amount REAL,
            advance_payment REAL,
            additional_payment REAL,
            third_payment REAL,  -- ← НОВОЕ ПОЛЕ
            contract_period INTEGER,
            comments TEXT,
            contract_file_link TEXT,
            tech_task_link TEXT,
            status TEXT DEFAULT 'Новый заказ',
            termination_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
        ''')
        
        # Таблица CRM (карточки проектов)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS crm_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER NOT NULL,
            column_name TEXT NOT NULL,
            deadline DATE,
            tags TEXT,
            is_approved BOOLEAN DEFAULT 0,
            senior_manager_id INTEGER,
            sdp_id INTEGER,
            gap_id INTEGER,
            manager_id INTEGER,
            surveyor_id INTEGER,
            order_position INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id)
        )
        ''')
        
        # Таблица исполнителей по стадиям
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS stage_executors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crm_card_id INTEGER NOT NULL,
            stage_name TEXT NOT NULL,
            executor_id INTEGER NOT NULL,
            assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            assigned_by INTEGER NOT NULL,
            deadline DATE,
            completed BOOLEAN DEFAULT 0,
            completed_date TIMESTAMP,
            FOREIGN KEY (crm_card_id) REFERENCES crm_cards(id),
            FOREIGN KEY (executor_id) REFERENCES employees(id),
            FOREIGN KEY (assigned_by) REFERENCES employees(id)
        )
        ''')
        
        # Таблица CRM надзора
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS crm_supervision (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER NOT NULL,
            column_name TEXT NOT NULL,
            deadline DATE,
            tags TEXT,
            is_approved BOOLEAN DEFAULT 0,
            is_purchased BOOLEAN DEFAULT 0,
            executor_id INTEGER,
            order_position INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id),
            FOREIGN KEY (executor_id) REFERENCES employees(id)
        )
        ''')
        
        # Таблица зарплат
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS salaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER,
            employee_id INTEGER NOT NULL,
            payment_type TEXT NOT NULL,
            stage_name TEXT,
            amount REAL NOT NULL,
            advance_payment REAL,
            report_month TEXT NOT NULL,
            comments TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id),
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
        ''')
        
        # Таблица истории действий (для аудита)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS action_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            description TEXT,
            action_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES employees(id)
        )
        ''')
        
        # Создание администратора по умолчанию
        # ВАЖНО: Пароль теперь хэшируется!
        default_password_hash = hash_password('admin')
        cursor.execute('''
        INSERT OR IGNORE INTO employees
        (full_name, phone, position, department, login, password, role, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('Администратор', '+7 (000) 000-00-00', 'Руководитель студии',
              'Руководящий отдел', 'admin', default_password_hash, 'Администратор', 'активный'))

        # ИСПРАВЛЕНИЕ: Таблица агентов с цветами
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            color TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Добавляем агентов по умолчанию с цветами
        cursor.execute('SELECT COUNT(*) as count FROM agents')
        if cursor.fetchone()['count'] == 0:
            cursor.execute('''
            INSERT INTO agents (name, color) VALUES
            ('ПЕТРОВИЧ', '#FFA500'),
            ('ФЕСТИВАЛЬ', '#FF69B4')
            ''')
            print("✓ Агенты по умолчанию добавлены с цветами")

        conn.commit()
        self.close()
        print("База данных успешно инициализирована!")
    
    # Методы для работы с сотрудниками
    def add_employee(self, employee_data):
        """Добавление сотрудника В БАЗУ ДАННЫХ"""
        conn = self.connect()
        cursor = conn.cursor()
        
        position = employee_data['position']
        
        # Определяем основной отдел по ПЕРВОЙ должности
        if position in ['Руководитель студии', 'Старший менеджер проектов', 'СДП', 'ГАП']:
            department = 'Административный отдел'
        elif position in ['Дизайнер', 'Чертёжник']:
            department = 'Проектный отдел'
        elif position in ['Менеджер', 'ДАН', 'Замерщик']:
            department = 'Исполнительный отдел'
        else:
            department = 'Другое'
        
        # Хэшируем пароль перед сохранением
        password = employee_data.get('password', '')
        password_hash = hash_password(password) if password else ''

        cursor.execute('''
        INSERT INTO employees
        (full_name, phone, email, address, birth_date, status, position, secondary_position,
         department, login, password)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            employee_data['full_name'],
            employee_data.get('phone', ''),
            employee_data.get('email', ''),
            employee_data.get('address', ''),
            employee_data.get('birth_date', ''),
            employee_data.get('status', 'активный'),
            employee_data['position'],
            employee_data.get('secondary_position', ''),
            department,
            employee_data.get('login', ''),
            password_hash
        ))
        
        conn.commit()
        employee_id = cursor.lastrowid
        self.close()
        return employee_id
    
    def get_employee_by_login(self, login, password):
        """
        Получение сотрудника по логину и паролю
        Теперь с безопасной проверкой хэшированного пароля
        """
        conn = self.connect()
        cursor = conn.cursor()

        # Сначала получаем сотрудника по логину
        cursor.execute('''
        SELECT * FROM employees
        WHERE login = ? AND status = 'активный'
        ''', (login,))

        employee = cursor.fetchone()
        self.close()

        # Если сотрудник не найден, возвращаем None
        if not employee:
            return None

        # Проверяем пароль с помощью безопасной функции
        # employee[11] - это индекс поля password в таблице
        stored_password = employee[11] if len(employee) > 11 else None

        if stored_password and verify_password(password, stored_password):
            # ВАЖНО: Преобразуем Row в словарь для совместимости с остальным кодом
            return dict(employee)

        # Пароль неверный
        return None
    
    def get_employees_by_department(self, department):
        """Получение сотрудников по отделу"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM employees 
        WHERE department = ? 
        ORDER BY position, full_name
        ''', (department,))
        
        employees = [dict(row) for row in cursor.fetchall()]
        self.close()
        return employees
    
    def get_employees_by_position(self, position):
        """Получение сотрудников по должности (ВКЛЮЧАЯ ВТОРУЮ ДОЛЖНОСТЬ)"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # ========== ИСПРАВЛЕНИЕ: ИЩЕМ ПО ОБЕИМ ДОЛЖНОСТЯМ ==========
        cursor.execute('''
        SELECT * FROM employees 
        WHERE (position = ? OR secondary_position = ?) 
          AND status = 'активный'
        ORDER BY full_name
        ''', (position, position))
        # ============================================================
        
        employees = [dict(row) for row in cursor.fetchall()]
        self.close()
        
        # ========== ОТЛАДКА ==========
        print(f"🔍 Поиск сотрудников с должностью '{position}':")
        for emp in employees:
            pos_display = emp['position']
            if emp.get('secondary_position'):
                pos_display += f"/{emp['secondary_position']}"
            print(f"   [OK] {emp['full_name']} ({pos_display})")
        if not employees:
            print(f"   [WARN] Не найдено сотрудников!")
        print("="*60)
        # =============================
        
        return employees
    
    # Методы для работы с клиентами
    def add_client(self, client_data):
        """Добавление клиента"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO clients 
        (client_type, full_name, phone, email, passport_series, passport_number,
         passport_issued_by, passport_issued_date, registration_address,
         organization_type, organization_name, inn, ogrn, account_details,
         responsible_person)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            client_data['client_type'],
            client_data.get('full_name', ''),
            client_data['phone'],
            client_data.get('email', ''),
            client_data.get('passport_series', ''),
            client_data.get('passport_number', ''),
            client_data.get('passport_issued_by', ''),
            client_data.get('passport_issued_date', ''),
            client_data.get('registration_address', ''),
            client_data.get('organization_type', ''),
            client_data.get('organization_name', ''),
            client_data.get('inn', ''),
            client_data.get('ogrn', ''),
            client_data.get('account_details', ''),
            client_data.get('responsible_person', '')
        ))
        
        conn.commit()
        client_id = cursor.lastrowid
        self.close()
        return client_id
    
    def get_all_clients(self):
        """Получение всех клиентов"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM clients ORDER BY id DESC')
        clients = [dict(row) for row in cursor.fetchall()]
        self.close()
        return clients
    
    # Методы для работы с договорами
    def add_contract(self, contract_data):
        """Добавление договора"""
        conn = self.connect()
        cursor = conn.cursor()

        # Генерируем путь к папке на Яндекс.Диске (быстро, без обращения к API)
        yandex_folder_path = None
        if YANDEX_DISK_TOKEN and contract_data.get('agent_type') and contract_data.get('address') and contract_data.get('area'):
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                yandex_folder_path = yd.build_contract_folder_path(
                    agent_type=contract_data.get('agent_type'),
                    project_type=contract_data['project_type'],
                    city=contract_data.get('city', ''),
                    address=contract_data.get('address', ''),
                    area=contract_data.get('area', 0),
                    status=contract_data.get('status')
                )
            except Exception as e:
                print(f"[ERROR] Ошибка при генерации пути папки: {e}")

        cursor.execute('''
        INSERT INTO contracts
        (client_id, project_type, agent_type, city, contract_number, contract_date,
         address, area, total_amount, advance_payment, additional_payment,
         contract_period, comments, contract_file_link, tech_task_link, yandex_folder_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            contract_data['client_id'],
            contract_data['project_type'],
            contract_data.get('agent_type', ''),
            contract_data.get('city', ''),
            contract_data['contract_number'],
            contract_data.get('contract_date', datetime.now().date()),
            contract_data.get('address', ''),
            contract_data.get('area', 0),
            contract_data.get('total_amount', 0),
            contract_data.get('advance_payment', 0),
            contract_data.get('additional_payment', 0),
            contract_data.get('contract_period', 0),
            contract_data.get('comments', ''),
            contract_data.get('contract_file_link', ''),
            contract_data.get('tech_task_link', ''),
            yandex_folder_path
        ))

        conn.commit()
        contract_id = cursor.lastrowid

        # Автоматически создаем карточку в CRM
        self._create_crm_card(contract_id, contract_data['project_type'])

        # Создаем папку на Яндекс.Диске в фоновом потоке (не блокирует UI)
        if yandex_folder_path:
            def create_folder_async():
                try:
                    yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                    success = yd.create_contract_folder_structure(
                        agent_type=contract_data.get('agent_type'),
                        project_type=contract_data['project_type'],
                        city=contract_data.get('city', ''),
                        address=contract_data.get('address', ''),
                        area=contract_data.get('area', 0),
                        status=contract_data.get('status')
                    )
                    if success:
                        print(f"[OK] Папка создана на Яндекс.Диске: {yandex_folder_path}")
                    else:
                        print("[WARN] Не удалось создать папку на Яндекс.Диске")
                except Exception as e:
                    print(f"[ERROR] Ошибка при создании папки на Яндекс.Диске: {e}")

            thread = threading.Thread(target=create_folder_async, daemon=True)
            thread.start()

        self.close()
        return contract_id
    
    def _create_crm_card(self, contract_id, project_type):
        """Создание карточки в CRM"""
        cursor = self.connection.cursor()

        # ========== АВТОМАТИЧЕСКИЙ РАСЧЕТ ДЕДЛАЙНА ПРИ СОЗДАНИИ ==========
        deadline = None
        try:
            from utils.date_utils import calculate_deadline

            # Получаем данные договора для расчета дедлайна
            cursor.execute('''
            SELECT contract_date, contract_period
            FROM contracts
            WHERE id = ?
            ''', (contract_id,))

            row = cursor.fetchone()
            if row:
                contract_date = row['contract_date']
                contract_period = row['contract_period']

                # Рассчитываем дедлайн (на момент создания нет даты замера и ТЗ)
                if contract_date and contract_period:
                    calculated_deadline = calculate_deadline(
                        contract_date,
                        None,  # survey_date
                        None,  # tech_task_date
                        contract_period
                    )

                    if calculated_deadline:
                        deadline = calculated_deadline.strftime('%Y-%m-%d')
                        print(f"[OK] Автоматически рассчитан начальный дедлайн: {deadline}")
        except Exception as e:
            print(f"[WARN] Ошибка расчета дедлайна при создании карточки: {e}")
            import traceback
            traceback.print_exc()
        # =================================================================

        cursor.execute('''
        INSERT INTO crm_cards (contract_id, column_name, deadline)
        VALUES (?, 'Новый заказ', ?)
        ''', (contract_id, deadline))

        self.connection.commit()
    
    # Дополнительные методы для CRM, отчетов, зарплат...
    # (продолжение кода в следующем блоке)
    # Дополнение к классу DatabaseManager

    def delete_client(self, client_id):
        """Удаление клиента"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM clients WHERE id = ?', (client_id,))
        conn.commit()
        self.close()
    
    def update_client(self, client_id, client_data):
        """Обновление клиента"""
        conn = self.connect()
        cursor = conn.cursor()

        # БЕЗОПАСНОСТЬ: Whitelist разрешённых полей для защиты от SQL-инъекций
        ALLOWED_FIELDS = {
            'client_type', 'full_name', 'phone', 'email',
            'passport_series', 'passport_number', 'registration_address',
            'organization_name', 'inn', 'ogrn'
        }

        # Фильтруем только разрешённые поля
        validated_data = {k: v for k, v in client_data.items() if k in ALLOWED_FIELDS}

        if not validated_data:
            print("[WARN] Нет данных для обновления")
            self.close()
            return

        set_clause = ', '.join([f'{key} = ?' for key in validated_data.keys()])
        values = list(validated_data.values()) + [client_id]

        cursor.execute(f'UPDATE clients SET {set_clause} WHERE id = ?', values)
        conn.commit()
        self.close()
    
    def get_client_by_id(self, client_id):
        """Получение клиента по ID"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
        client = cursor.fetchone()
        self.close()
        
        return dict(client) if client else None
    
    def get_all_contracts(self):
        """Получение всех договоров"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT c.*, cl.full_name, cl.organization_name, cl.client_type
        FROM contracts c
        LEFT JOIN clients cl ON c.client_id = cl.id
        ORDER BY c.id DESC
        ''')
        
        contracts = [dict(row) for row in cursor.fetchall()]
        self.close()
        return contracts
    
    def check_contract_number_exists(self, contract_number):
        """Проверка существования номера договора"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) as count FROM contracts WHERE contract_number = ?', (contract_number,))
            exists = cursor.fetchone()['count'] > 0
            self.close()
            
            return exists
        except Exception as e:
            print(f"Ошибка проверки номера договора: {e}")
            return False

    def get_next_contract_number(self, year):
        """Получение следующего номера договора для года"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Ищем все договоры за год
            cursor.execute('''
            SELECT contract_number FROM contracts 
            WHERE contract_number LIKE ?
            ORDER BY id DESC
            LIMIT 1
            ''', (f'%{year}',))
            
            last = cursor.fetchone()
            self.close()
            
            if last:
                # Извлекаем номер из формата "№001-2024"
                try:
                    number_part = last['contract_number'].split('-')[0].replace('№', '').strip()
                    return int(number_part) + 1
                except Exception:
                    return 1
            else:
                return 1
                
        except Exception as e:
            print(f"Ошибка получения номера договора: {e}")
            return 1    
        
    def update_contract(self, contract_id, updates):
        """Обновление данных договора"""
        conn = self.connect()
        cursor = conn.cursor()

        # Если изменяется статус на Сдан/Расторгнут/Авторский надзор, сохраняем дату
        if 'status' in updates:
            new_status = updates['status']
            if new_status in ['СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР']:
                # Проверяем, не установлена ли уже дата
                cursor.execute("SELECT status_changed_date FROM contracts WHERE id = ?", (contract_id,))
                result = cursor.fetchone()
                if result and not result[0]:  # Если дата еще не установлена
                    from datetime import datetime
                    updates['status_changed_date'] = datetime.now().strftime('%Y-%m-%d')
                    print(f"[INFO] Установлена дата закрытия договора: {updates['status_changed_date']}")

        # Формируем SQL запрос динамически
        set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values())
        values.append(contract_id)

        query = f"UPDATE contracts SET {set_clause} WHERE id = ?"

        cursor.execute(query, values)
        conn.commit()

        # ========== АВТОМАТИЧЕСКИЙ ПЕРЕСЧЕТ ДЕДЛАЙНА ==========
        # Если изменяются contract_date или contract_period, пересчитываем дедлайн карточки
        if 'contract_date' in updates or 'contract_period' in updates:
            try:
                from utils.date_utils import calculate_deadline

                # Получаем ID карточки и данные для расчета
                cursor.execute('''
                SELECT cc.id as card_id, cc.survey_date, cc.tech_task_date,
                       c.contract_date, c.contract_period
                FROM crm_cards cc
                JOIN contracts c ON cc.contract_id = c.id
                WHERE c.id = ?
                ''', (contract_id,))

                row = cursor.fetchone()
                if row:
                    card_id = row['card_id']
                    contract_date = row['contract_date']
                    contract_period = row['contract_period']
                    survey_date = row['survey_date']
                    tech_task_date = row['tech_task_date']

                    # Рассчитываем новый дедлайн
                    if contract_date and contract_period:
                        new_deadline = calculate_deadline(
                            contract_date,
                            survey_date,
                            tech_task_date,
                            contract_period
                        )

                        if new_deadline:
                            # Обновляем дедлайн карточки
                            deadline_str = new_deadline.strftime('%Y-%m-%d')
                            cursor.execute('UPDATE crm_cards SET deadline = ? WHERE id = ?', (deadline_str, card_id))
                            conn.commit()
                            print(f"[OK] Автоматически пересчитан дедлайн карточки {card_id} после изменения договора: {deadline_str}")
            except Exception as e:
                print(f"[WARN] Ошибка пересчета дедлайна при обновлении договора: {e}")
                import traceback
                traceback.print_exc()
        # =====================================================

        # ========== ПЕРЕМЕЩЕНИЕ ПАПКИ НА ЯНДЕКС.ДИСКЕ ==========
        # Проверяем, изменились ли поля, влияющие на путь к папке
        folder_affecting_fields = ['agent_type', 'project_type', 'city', 'address', 'area', 'status']
        if any(field in updates for field in folder_affecting_fields):
            if YANDEX_DISK_TOKEN:
                try:
                    # Получаем текущие данные договора
                    cursor.execute('''
                    SELECT agent_type, project_type, city, address, area, status, yandex_folder_path
                    FROM contracts WHERE id = ?
                    ''', (contract_id,))
                    contract = cursor.fetchone()

                    # Создаем менеджер Яндекс.Диска
                    yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                    if contract and contract['yandex_folder_path']:
                        old_path = contract['yandex_folder_path']

                        # Формируем новый путь с учетом обновлений
                        new_path = yd.build_contract_folder_path(
                            agent_type=contract['agent_type'],
                            project_type=contract['project_type'],
                            city=contract['city'],
                            address=contract['address'],
                            area=contract['area'],
                            status=contract['status']
                        )

                        # Если путь изменился, создаем новую папку и удаляем старую
                        if old_path != new_path:
                            # Сначала обновляем путь в БД
                            cursor.execute('UPDATE contracts SET yandex_folder_path = ? WHERE id = ?',
                                         (new_path, contract_id))
                            conn.commit()

                            # Создаем новую папку, копируем содержимое и удаляем старую в фоновом потоке
                            def relocate_folder_async():
                                try:
                                    yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                                    # Создаем новую папку в новом месте
                                    success = yd.create_contract_folder_structure(
                                        agent_type=contract['agent_type'],
                                        project_type=contract['project_type'],
                                        city=contract['city'],
                                        address=contract['address'],
                                        area=contract['area'],
                                        status=contract['status']
                                    )

                                    if success:
                                        print(f"[OK] Создана новая папка: {new_path}")

                                        # Копируем содержимое старой папки в новую
                                        print(f"[INFO] Копирование содержимого из {old_path}...")
                                        if yd.copy_folder_contents(old_path, new_path):
                                            print(f"[OK] Содержимое скопировано")

                                            # Удаляем старую папку только после успешного копирования
                                            if yd.delete_folder(old_path):
                                                print(f"[OK] Удалена старая папка: {old_path}")
                                            else:
                                                print(f"[WARN] Не удалось удалить старую папку: {old_path}")
                                        else:
                                            print(f"[WARN] Ошибка копирования содержимого, старая папка не удалена")
                                    else:
                                        print(f"[WARN] Не удалось создать новую папку на Яндекс.Диске")

                                except Exception as e:
                                    print(f"[ERROR] Ошибка при перемещении папки: {e}")

                            thread = threading.Thread(target=relocate_folder_async, daemon=True)
                            thread.start()

                    elif contract and not contract['yandex_folder_path']:
                        # Если папки не было, генерируем путь и создаем в фоновом режиме
                        new_path = yd.build_contract_folder_path(
                            agent_type=contract['agent_type'],
                            project_type=contract['project_type'],
                            city=contract['city'],
                            address=contract['address'],
                            area=contract['area'],
                            status=contract['status']
                        )

                        # Обновляем путь в БД
                        cursor.execute('UPDATE contracts SET yandex_folder_path = ? WHERE id = ?',
                                     (new_path, contract_id))
                        conn.commit()

                        # Создаем папку в фоновом потоке
                        def create_folder_async():
                            try:
                                yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                                success = yd.create_contract_folder_structure(
                                    agent_type=contract['agent_type'],
                                    project_type=contract['project_type'],
                                    city=contract['city'],
                                    address=contract['address'],
                                    area=contract['area'],
                                    status=contract['status']
                                )
                                if success:
                                    print(f"[OK] Папка создана на Яндекс.Диске: {new_path}")
                                else:
                                    print(f"[WARN] Не удалось создать папку на Яндекс.Диске")
                            except Exception as e:
                                print(f"[ERROR] Ошибка при создании папки: {e}")

                        thread = threading.Thread(target=create_folder_async, daemon=True)
                        thread.start()

                except Exception as e:
                    print(f"[ERROR] Ошибка при работе с папкой на Яндекс.Диске: {e}")
                    import traceback
                    traceback.print_exc()
        # ========================================================

        self.close()

        print(f"[OK] Договор {contract_id} обновлен: {updates}")
            
    def update_crm_card(self, card_id, updates):
        """Обновление карточки CRM"""
        conn = self.connect()
        cursor = conn.cursor()
        
        set_clause = ', '.join([f'{key} = ?' for key in updates.keys()])
        values = list(updates.values()) + [card_id]
        
        cursor.execute(f'UPDATE crm_cards SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?', values)
        conn.commit()

        # ========== АВТОМАТИЧЕСКИЙ РАСЧЕТ ДЕДЛАЙНА ==========
        # Если изменяются даты (survey_date или tech_task_date), пересчитываем дедлайн
        if 'survey_date' in updates or 'tech_task_date' in updates:
            try:
                from utils.date_utils import calculate_deadline

                # Получаем данные карточки и договора
                cursor.execute('''
                SELECT cc.contract_id, cc.survey_date, cc.tech_task_date,
                       c.contract_date, c.contract_period
                FROM crm_cards cc
                JOIN contracts c ON cc.contract_id = c.id
                WHERE cc.id = ?
                ''', (card_id,))

                row = cursor.fetchone()
                if row:
                    contract_date = row['contract_date']
                    contract_period = row['contract_period']
                    survey_date = row['survey_date']
                    tech_task_date = row['tech_task_date']

                    # Рассчитываем новый дедлайн
                    if contract_date and contract_period:
                        new_deadline = calculate_deadline(
                            contract_date,
                            survey_date,
                            tech_task_date,
                            contract_period
                        )

                        if new_deadline:
                            # Обновляем дедлайн
                            deadline_str = new_deadline.strftime('%Y-%m-%d')
                            cursor.execute('UPDATE crm_cards SET deadline = ? WHERE id = ?', (deadline_str, card_id))
                            conn.commit()
                            print(f"[OK] Автоматически пересчитан дедлайн для карточки {card_id}: {deadline_str}")
            except Exception as e:
                print(f"[WARN] Ошибка автоматического расчета дедлайна: {e}")
                import traceback
                traceback.print_exc()
        # ===================================================

        # ========== НОВОЕ: СОЗДАНИЕ ВЫПЛАТ ДЛЯ РУКОВОДИТЕЛЕЙ ==========
        try:
            # Получаем данные карточки и договора
            cursor.execute('SELECT contract_id FROM crm_cards WHERE id = ?', (card_id,))
            row = cursor.fetchone()
            if row:
                contract_id = row['contract_id']
                
                # Получаем данные договора
                cursor.execute('SELECT project_type FROM contracts WHERE id = ?', (contract_id,))
                contract = cursor.fetchone()
                
                if contract:
                    project_type = contract['project_type']
                    
                    # Создаем выплаты для назначенных руководителей
                    roles_mapping = {
                        'senior_manager_id': 'Старший менеджер проектов',
                        'sdp_id': 'СДП',
                        'gap_id': 'ГАП',
                        'manager_id': 'Менеджер'
                    }
                    
                    for field, role in roles_mapping.items():
                        if field in updates and updates[field]:
                            employee_id = updates[field]

                            # ИСПРАВЛЕНИЕ: СДП - аванс и доплата
                            if role == 'СДП':
                                # Проверяем, нет ли уже аванса
                                cursor.execute('''
                                SELECT id FROM payments
                                WHERE contract_id = ? AND employee_id = ? AND role = ? AND payment_type = 'Аванс'
                                ''', (contract_id, employee_id, role))

                                existing_advance = cursor.fetchone()

                                if not existing_advance:
                                    # Получаем полную сумму
                                    full_amount = self.calculate_payment_amount(contract_id, employee_id, role)

                                    # ИСПРАВЛЕНИЕ: Создаем оплату даже если тариф = 0
                                    if full_amount == 0:
                                        print(f"[WARN] Тариф для СДП = 0 или не установлен. Создаем оплату с нулевой суммой")

                                    advance_amount = full_amount / 2
                                    balance_amount = full_amount / 2

                                    # Создаем аванс
                                    from PyQt5.QtCore import QDate
                                    current_month = QDate.currentDate().toString('yyyy-MM')

                                    conn_inner = self.connect()
                                    cursor_inner = conn_inner.cursor()

                                    cursor_inner.execute('''
                                    INSERT INTO payments
                                    (contract_id, employee_id, role, calculated_amount,
                                     final_amount, payment_type, report_month)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                    ''', (contract_id, employee_id, role, advance_amount,
                                          advance_amount, 'Аванс', current_month))

                                    # Создаем доплату
                                    cursor_inner.execute('''
                                    INSERT INTO payments
                                    (contract_id, employee_id, role, calculated_amount,
                                     final_amount, payment_type, report_month)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                    ''', (contract_id, employee_id, role, balance_amount,
                                          balance_amount, 'Доплата', ''))

                                    conn_inner.commit()
                                    self.close()

                                    print(f"[OK] Созданы аванс и доплата для СДП (ID={employee_id})")
                            else:
                                # Для остальных ролей - полная оплата
                                # Проверяем, нет ли уже выплаты
                                cursor.execute('''
                                SELECT id FROM payments
                                WHERE contract_id = ? AND employee_id = ? AND role = ?
                                ''', (contract_id, employee_id, role))

                                existing = cursor.fetchone()

                                if not existing:
                                    # Создаем выплату
                                    self.create_payment_record(
                                        contract_id,
                                        employee_id,
                                        role,
                                        payment_type='Полная оплата',
                                        report_month=None
                                    )
                                    print(f"[OK] Создана выплата для {role} (ID={employee_id})")
                    
                    conn.commit()
        except Exception as e:
            print(f"[WARN] Ошибка создания выплат для руководителей: {e}")
            import traceback
            traceback.print_exc()
        # ==============================================================
        
        self.close()
        
        print(f"[OK] Карточка {card_id} обновлена: {updates}")
    
    def update_crm_card_column(self, card_id, column_name):
        """Обновление колонки карточки"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE crm_cards 
        SET column_name = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
        ''', (column_name, card_id))
        
        conn.commit()
        self.close()
    
    def assign_stage_executor(self, card_id, stage_name, executor_id, assigned_by, deadline):
        """Назначение исполнителя на стадию"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO stage_executors 
        (crm_card_id, stage_name, executor_id, assigned_by, deadline)
        VALUES (?, ?, ?, ?, ?)
        ''', (card_id, stage_name, executor_id, assigned_by, deadline))
        
        conn.commit()
        self.close()
    
    def get_contract_id_by_crm_card(self, crm_card_id):
        """Получение ID договора по ID карточки CRM"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('SELECT contract_id FROM crm_cards WHERE id = ?', (crm_card_id,))
        row = cursor.fetchone()
        self.close()
        
        if row:
            return row['contract_id']
        return None
    
    def get_contract_by_id(self, contract_id):
        """Получение договора по ID"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM contracts WHERE id = ?', (contract_id,))
        contract = cursor.fetchone()
        self.close()
        
        return dict(contract) if contract else None
    
    def create_supervision_card(self, contract_id):
        """Создание карточки авторского надзора"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Проверяем, существует ли УЖЕ карточка (любая, не только активная)
            cursor.execute('''
            SELECT id, column_name
            FROM supervision_cards
            WHERE contract_id = ?
            ''', (contract_id,))
            existing = cursor.fetchone()
            
            if existing:
                print(f"[WARN] Карточка надзора ID={existing['id']} для договора {contract_id} уже существует")
                print(f"  Обновляем column_name на 'Новый заказ' (было: '{existing['column_name']}')")
                
                # Обновляем колонку на "Новый заказ" (сбрасываем на первую стадию)
                cursor.execute('''
                UPDATE supervision_cards
                SET column_name = 'Новый заказ', 
                    dan_completed = 0,
                    is_paused = 0,
                    pause_reason = NULL,
                    paused_at = NULL,
                    updated_at = datetime('now')
                WHERE id = ?
                ''', (existing['id'],))
                
                conn.commit()
                self.close()
                
                print(f"[OK] Карточка надзора ID={existing['id']} обновлена -> 'Новый заказ'")
                return existing['id']
            
            # Создаем новую карточку
            cursor.execute('''
            INSERT INTO supervision_cards (contract_id, column_name, created_at)
            VALUES (?, 'Новый заказ', datetime('now'))
            ''', (contract_id,))
            
            conn.commit()
            card_id = cursor.lastrowid
            self.close()
            
            print(f"[OK] Создана НОВАЯ карточка надзора ID={card_id} для договора {contract_id}")
            return card_id
            
        except Exception as e:
            print(f"[ERROR] Ошибка создания/обновления карточки надзора: {e}")
            import traceback
            traceback.print_exc()
            return None
        
    def get_supervision_cards(self):
        """Получение карточек CRM надзора"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT cs.*, c.contract_number, c.address, c.area, c.city, c.agent_type,
               e.full_name as executor_name
        FROM crm_supervision cs
        JOIN contracts c ON cs.contract_id = c.id
        LEFT JOIN employees e ON cs.executor_id = e.id
        ORDER BY cs.order_position
        ''')
        
        cards = [dict(row) for row in cursor.fetchall()]
        self.close()
        return cards
    
    def update_supervision_card(self, card_id, updates):
        """Обновление карточки надзора"""
        conn = self.connect()
        cursor = conn.cursor()
        
        set_clause = ', '.join([f'{key} = ?' for key in updates.keys()])
        values = list(updates.values()) + [card_id]
        
        cursor.execute(f'UPDATE crm_supervision SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?', values)
        conn.commit()
        self.close()
    
    def get_general_statistics(self, year, quarter, month):
        """Получение общей статистики"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Формируем WHERE для периода
        where_clause = self.build_period_where(year, quarter, month)
        
        # Всего выполненных
        cursor.execute(f'''
        SELECT COUNT(*) as total FROM contracts 
        WHERE status IN ('СДАН', 'АВТОРСКИЙ НАДЗОР')
        {where_clause}
        ''')
        total_completed = cursor.fetchone()['total']
        
        # Общая площадь
        cursor.execute(f'''
        SELECT SUM(area) as total FROM contracts 
        WHERE status IN ('СДАН', 'АВТОРСКИЙ НАДЗОР')
        {where_clause}
        ''')
        total_area = cursor.fetchone()['total'] or 0
        
        # Активные проекты
        cursor.execute('''
        SELECT COUNT(*) as total FROM contracts 
        WHERE status NOT IN ('СДАН', 'АВТОРСКИЙ НАДЗОР', 'РАСТОРГНУТ')
        ''')
        active_projects = cursor.fetchone()['total']
        
        # Расторгнуто за год
        cursor.execute('''
        SELECT COUNT(*) as total FROM contracts 
        WHERE status = 'РАСТОРГНУТ' AND strftime('%Y', updated_at) = ?
        ''', (str(year),))
        cancelled_projects = cursor.fetchone()['total']
        
        # По типам проектов
        cursor.execute(f'''
        SELECT project_type, COUNT(*) as count FROM contracts 
        WHERE status IN ('СДАН', 'АВТОРСКИЙ НАДЗОР')
        {where_clause}
        GROUP BY project_type
        ''')
        by_project_type = {row['project_type']: row['count'] for row in cursor.fetchall()}
        
        # По городам
        cursor.execute(f'''
        SELECT city, COUNT(*) as count FROM contracts 
        WHERE status IN ('СДАН', 'АВТОРСКИЙ НАДЗОР')
        {where_clause}
        GROUP BY city
        ''')
        by_city = {row['city']: row['count'] for row in cursor.fetchall()}
        
        self.close()
        
        return {
            'total_completed': total_completed,
            'total_area': total_area,
            'active_projects': active_projects,
            'cancelled_projects': cancelled_projects,
            'by_project_type': by_project_type,
            'by_city': by_city
        }
    
    def build_period_where(self, year, quarter, month):
        """Построение WHERE для периода"""
        if month and month != 'Все':
            return f" AND strftime('%Y-%m', contract_date) = '{year}-{month:02d}'"
        elif quarter and quarter != 'Все':
            q_months = {
                'Q1': (1, 3),
                'Q2': (4, 6),
                'Q3': (7, 9),
                'Q4': (10, 12)
            }
            start, end = q_months[quarter]
            return f" AND strftime('%Y', contract_date) = '{year}' AND CAST(strftime('%m', contract_date) AS INTEGER) BETWEEN {start} AND {end}"
        else:
            return f" AND strftime('%Y', contract_date) = '{year}'"
    
    def get_crm_statistics(self, project_type, period, year, month):
        """Получение статистики CRM"""
        conn = self.connect()
        cursor = conn.cursor()
        
        where_clause = self.build_period_where(year, None, month)
        
        cursor.execute(f'''
        SELECT se.*, 
               e1.full_name as executor_name,
               e2.full_name as assigned_by_name,
               c.contract_number || ' - ' || c.address as project_info
        FROM stage_executors se
        JOIN employees e1 ON se.executor_id = e1.id
        JOIN employees e2 ON se.assigned_by = e2.id
        JOIN crm_cards cc ON se.crm_card_id = cc.id
        JOIN contracts c ON cc.contract_id = c.id
        WHERE c.project_type = ?
        {where_clause}
        ORDER BY se.assigned_date DESC
        ''', (project_type,))
        
        stats = [dict(row) for row in cursor.fetchall()]
        self.close()
        return stats
    
    def get_crm_statistics_filtered(self, project_type, period, year, quarter, month, 
                                    project_id, executor_id, stage_name, status_filter):
        """Получение статистики CRM с фильтрацией"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Базовый WHERE
        where_clauses = ['c.project_type = ?']
        params = [project_type]
        
        # Фильтр по периоду
        if period == 'Год':
            where_clauses.append("strftime('%Y', se.assigned_date) = ?")
            params.append(str(year))
        elif period == 'Квартал' and quarter:
            q_months = {
                'Q1': (1, 3), 'Q2': (4, 6), 'Q3': (7, 9), 'Q4': (10, 12)
            }
            start, end = q_months[quarter]
            where_clauses.append(f"strftime('%Y', se.assigned_date) = ? AND CAST(strftime('%m', se.assigned_date) AS INTEGER) BETWEEN {start} AND {end}")
            params.append(str(year))
        elif period == 'Месяц' and month:
            where_clauses.append("strftime('%Y-%m', se.assigned_date) = ?")
            params.append(f'{year}-{month:02d}')
        
        # Фильтр по проекту
        if project_id:
            where_clauses.append('c.id = ?')
            params.append(project_id)
        
        # Фильтр по исполнителю
        if executor_id:
            where_clauses.append('se.executor_id = ?')
            params.append(executor_id)
        
        # Фильтр по стадии
        if stage_name:
            where_clauses.append('se.stage_name = ?')
            params.append(stage_name)
        
        # Фильтр по статусу
        if status_filter == 'Выполнено':
            where_clauses.append('se.completed = 1')
        elif status_filter == 'В работе':
            where_clauses.append('se.completed = 0 AND se.deadline >= date("now")')
        elif status_filter == 'Просрочено':
            where_clauses.append('se.completed = 0 AND se.deadline < date("now")')
        
        where_clause = ' AND '.join(where_clauses)
        
        query = f'''
        SELECT se.assigned_date, se.deadline, se.completed, se.completed_date,
               se.stage_name,
               e1.full_name as executor_name,
               e2.full_name as assigned_by_name,
               c.contract_number || ' - ' || c.address as project_info
        FROM stage_executors se
        JOIN employees e1 ON se.executor_id = e1.id
        JOIN employees e2 ON se.assigned_by = e2.id
        JOIN crm_cards cc ON se.crm_card_id = cc.id
        JOIN contracts c ON cc.contract_id = c.id
        WHERE {where_clause}
        ORDER BY se.assigned_date DESC
        '''
        
        cursor.execute(query, params)
        
        stats = [dict(row) for row in cursor.fetchall()]
        self.close()
        return stats
    
    def complete_stage_for_executor(self, crm_card_id, stage_name, executor_id):
        """Отметка стадии как выполненной исполнителем"""
        conn = self.connect()
        cursor = conn.cursor()

        # ОТЛАДКА: Проверяем, есть ли запись перед обновлением
        cursor.execute('''
        SELECT id, completed FROM stage_executors
        WHERE crm_card_id = ? AND stage_name = ? AND executor_id = ?
        ''', (crm_card_id, stage_name, executor_id))

        existing = cursor.fetchone()
        if existing:
            print(f"[DEBUG] Найдена запись в stage_executors: ID={existing['id']}, completed={existing['completed']}")
        else:
            print(f"[WARN] Не найдена запись в stage_executors для crm_card_id={crm_card_id}, stage='{stage_name}', executor={executor_id}")

        cursor.execute('''
        UPDATE stage_executors
        SET completed = 1, completed_date = datetime('now')
        WHERE crm_card_id = ? AND stage_name = ? AND executor_id = ?
        ''', (crm_card_id, stage_name, executor_id))

        rows_updated = cursor.rowcount
        conn.commit()
        self.close()

        if rows_updated > 0:
            print(f"[OK] Стадия '{stage_name}' отмечена как выполненная для исполнителя {executor_id} (обновлено строк: {rows_updated})")
        else:
            print(f"[WARN] Стадия '{stage_name}' НЕ ОБНОВЛЕНА (возможно, запись не найдена)")

    def get_projects_by_type(self, project_type):
        """Получение списка проектов по типу"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT DISTINCT c.id as contract_id, c.contract_number, c.address, c.city
        FROM contracts c
        JOIN crm_cards cc ON cc.contract_id = c.id
        WHERE c.project_type = ?
        ORDER BY c.contract_number DESC
        ''', (project_type,))
        
        projects = [dict(row) for row in cursor.fetchall()]
        self.close()
        return projects
    
    def get_crm_cards_by_project_type(self, project_type):
        """Получение карточек по типу проекта (ТОЛЬКО АКТИВНЫЕ, исключая архив)"""
        print(f"\n[DB] ════════════════════════════════════════")
        print(f"[DB] 📋 Запрос: Активные карточки типа '{project_type}'")
        
        conn = self.connect()
        cursor = conn.cursor()
        
        # 1. Проверяем ОБЩЕЕ количество карточек
        cursor.execute('SELECT COUNT(*) as total FROM crm_cards')
        total_cards = cursor.fetchone()['total']
        print(f"[DB] ├─ Всего карточек в таблице: {total_cards}")
        
        # 2. Проверяем количество договоров с таким типом
        cursor.execute('SELECT COUNT(*) as total FROM contracts WHERE project_type = ?', (project_type,))
        total_contracts = cursor.fetchone()['total']
        print(f"[DB] ├─ Договоров с типом '{project_type}': {total_contracts}")
        
        # 3. Проверяем статусы договоров
        cursor.execute('''
        SELECT status, COUNT(*) as count 
        FROM contracts 
        WHERE project_type = ? 
        GROUP BY status
        ''', (project_type,))
        status_counts = cursor.fetchall()
        print(f"[DB] ├─ Статусы договоров:")
        for row in status_counts:
            print(f"[DB] │  • {row['status'] or 'NULL/Пусто'}: {row['count']} шт.")
        
        # 4. ОСНОВНОЙ ЗАПРОС (ИСПРАВЛЕННЫЙ)
        query = '''
        SELECT cc.id as id, cc.contract_id, cc.column_name, cc.deadline, cc.tags,
               cc.is_approved, cc.approval_deadline, cc.approval_stages,
               cc.project_data_link,  -- ← НОВОЕ
               cc.senior_manager_id, cc.sdp_id, cc.gap_id,
               cc.manager_id, cc.surveyor_id,
               c.contract_number, c.address, c.area, c.city, c.agent_type,
               c.project_type, c.status as contract_status,
               e1.full_name as senior_manager_name,
               e2.full_name as sdp_name,
               e3.full_name as gap_name,
               e4.full_name as manager_name,
               e5.full_name as surveyor_name,
               
               -- ДИЗАЙНЕР
               (SELECT e.full_name 
                FROM stage_executors se 
                JOIN employees e ON se.executor_id = e.id
                WHERE se.crm_card_id = cc.id 
                  AND se.stage_name LIKE '%концепция%'
                ORDER BY se.id DESC LIMIT 1) as designer_name,
               
               (SELECT se.completed 
                FROM stage_executors se
                WHERE se.crm_card_id = cc.id 
                  AND se.stage_name LIKE '%концепция%'
                ORDER BY se.id DESC LIMIT 1) as designer_completed,
               
               -- ========== НОВОЕ: ДЕДЛАЙН ДИЗАЙНЕРА ==========
               (SELECT se.deadline 
                FROM stage_executors se
                WHERE se.crm_card_id = cc.id 
                  AND se.stage_name LIKE '%концепция%'
                ORDER BY se.id DESC LIMIT 1) as designer_deadline,
               
               -- ЧЕРТЁЖНИК
               (SELECT e.full_name 
                FROM stage_executors se 
                JOIN employees e ON se.executor_id = e.id
                WHERE se.crm_card_id = cc.id 
                  AND (se.stage_name LIKE '%чертежи%' OR se.stage_name LIKE '%планировочные%')
                ORDER BY se.id DESC LIMIT 1) as draftsman_name,
               
               (SELECT se.completed 
                FROM stage_executors se
                WHERE se.crm_card_id = cc.id 
                  AND (se.stage_name LIKE '%чертежи%' OR se.stage_name LIKE '%планировочные%')
                ORDER BY se.id DESC LIMIT 1) as draftsman_completed,
               
               -- ========== НОВОЕ: ДЕДЛАЙН ЧЕРТЁЖНИКА ==========
               (SELECT se.deadline
                FROM stage_executors se
                WHERE se.crm_card_id = cc.id
                  AND (se.stage_name LIKE '%чертежи%' OR se.stage_name LIKE '%планировочные%')
                ORDER BY se.id DESC LIMIT 1) as draftsman_deadline,

               -- ========== ПОЛЯ ДЛЯ ТЗ И ЗАМЕРА (из crm_cards для совместимости) ==========
               cc.tech_task_file,
               cc.tech_task_date,
               cc.survey_date,

               -- ========== ПОЛЯ ДЛЯ ТЗ И ЗАМЕРА (из contracts - новые данные) ==========
               c.tech_task_link,
               c.tech_task_file_name,
               c.tech_task_yandex_path,
               c.measurement_image_link,
               c.measurement_file_name,
               c.measurement_yandex_path,
               c.measurement_date

        FROM crm_cards cc
        JOIN contracts c ON cc.contract_id = c.id
        LEFT JOIN employees e1 ON cc.senior_manager_id = e1.id
        LEFT JOIN employees e2 ON cc.sdp_id = e2.id
        LEFT JOIN employees e3 ON cc.gap_id = e3.id
        LEFT JOIN employees e4 ON cc.manager_id = e4.id
        LEFT JOIN employees e5 ON cc.surveyor_id = e5.id
        WHERE c.project_type = ? 
          AND (c.status IS NULL OR c.status = '' OR c.status NOT IN ('СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР'))
        ORDER BY cc.order_position, cc.id
        '''
        
        cursor.execute(query, (project_type,))
        rows = cursor.fetchall()
        
        print(f"[DB] └─ [OK] Результат запроса: {len(rows)} активных карточек")
        
        cards = []
        for row in rows:
            card = dict(row)
            cards.append(card)
            print(f"[DB]    • ID={card['id']} | Колонка: '{card['column_name']}' | "
                  f"Дизайнер: {card.get('designer_name', 'Не назначен')} "
                  f"({'[OK] сдано' if card.get('designer_completed') else 'в работе'}) | "
                  f"Чертёжник: {card.get('draftsman_name', 'Не назначен')} "
                  f"({'[OK] сдано' if card.get('draftsman_completed') else 'в работе'})")
        
        if not cards:
            print(f"[DB] [WARN] ВНИМАНИЕ: Нет активных карточек!")
        
        print(f"[DB] ════════════════════════════════════════\n")
        
        self.close()
        return cards
    
    def get_archived_crm_cards(self, project_type):
        """Получение архивных карточек (СДАН, РАСТОРГНУТ)"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT cc.id, cc.contract_id, c.contract_number, c.address, c.area,
               c.city, c.agent_type, c.project_type, c.status, c.termination_reason,
               cc.deadline, cc.tags, c.contract_date, c.status_changed_date,
               e1.full_name as senior_manager_name,
               e2.full_name as sdp_name,
               e3.full_name as gap_name,
               e4.full_name as manager_name,
               e5.full_name as surveyor_name,
               GROUP_CONCAT(DISTINCT CASE 
                   WHEN se.stage_name LIKE '%концепция%' 
                   THEN e6.full_name 
                   END) as designer_name,
               GROUP_CONCAT(DISTINCT CASE 
                   WHEN se.stage_name LIKE '%чертежи%' OR se.stage_name LIKE '%планировочные%'
                   THEN e7.full_name 
                   END) as draftsman_name
        FROM crm_cards cc
        JOIN contracts c ON cc.contract_id = c.id
        LEFT JOIN employees e1 ON cc.senior_manager_id = e1.id
        LEFT JOIN employees e2 ON cc.sdp_id = e2.id
        LEFT JOIN employees e3 ON cc.gap_id = e3.id
        LEFT JOIN employees e4 ON cc.manager_id = e4.id
        LEFT JOIN employees e5 ON cc.surveyor_id = e5.id
        LEFT JOIN stage_executors se ON se.crm_card_id = cc.id
        LEFT JOIN employees e6 ON se.executor_id = e6.id AND se.stage_name LIKE '%концепция%'
        LEFT JOIN employees e7 ON se.executor_id = e7.id AND (se.stage_name LIKE '%чертежи%' OR se.stage_name LIKE '%планировочные%')
        WHERE c.project_type = ? 
          AND c.status IN ('СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР')
        GROUP BY cc.id
        ORDER BY cc.id DESC
        ''', (project_type,))
        
        rows = cursor.fetchall()
        self.close()
        
        return [dict(row) for row in rows]

    def get_stage_history(self, crm_card_id):
        """Получение истории стадий проекта"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT se.stage_name, se.assigned_date, se.deadline, se.submitted_date, se.completed, se.completed_date,
                   e1.full_name as executor_name,
                   e2.full_name as assigned_by_name
            FROM stage_executors se
            LEFT JOIN employees e1 ON se.executor_id = e1.id
            LEFT JOIN employees e2 ON se.assigned_by = e2.id
            WHERE se.crm_card_id = ?
            ORDER BY se.assigned_date ASC
            ''', (crm_card_id,))
            
            rows = cursor.fetchall()
            self.close()
            
            return [dict(row) for row in rows] if rows else []
        except Exception as e:
            print(f"Ошибка получения истории стадий: {e}")
            return []

    def get_previous_executor_by_position(self, crm_card_id, position):
        """Получение предыдущего исполнителя той же должности из предыдущих стадий"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT DISTINCT se.executor_id
            FROM stage_executors se
            JOIN employees e ON se.executor_id = e.id
            WHERE se.crm_card_id = ?
              AND e.position = ?
            ORDER BY se.assigned_date DESC
            LIMIT 1
            ''', (crm_card_id, position))

            row = cursor.fetchone()
            self.close()

            return row['executor_id'] if row else None
        except Exception as e:
            print(f"Ошибка получения предыдущего исполнителя: {e}")
            return None

    def get_all_employees(self):
        """Получение всех сотрудников"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM employees ORDER BY department, position, full_name')
        employees = [dict(row) for row in cursor.fetchall()]
        self.close()
        return employees
    
    def update_employee(self, employee_id, employee_data):
        """Обновление сотрудника"""
        conn = self.connect()
        cursor = conn.cursor()
        
        set_clause = ', '.join([f'{key} = ?' for key in employee_data.keys()])
        values = list(employee_data.values()) + [employee_id]
        
        cursor.execute(f'UPDATE employees SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?', values)
        conn.commit()
        self.close()
    
    def check_login_exists(self, login):
        """Проверка существования логина"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as count FROM employees WHERE login = ?', (login,))
        exists = cursor.fetchone()['count'] > 0
        self.close()
        return exists
    
    def get_all_payments(self, month, year):
        """Получение всех выплат из всех источников"""
        conn = self.connect()
        cursor = conn.cursor()

        # Объединяем выплаты из payments (CRM основная и надзор) и salaries (оклады)
        cursor.execute('''
        SELECT
            'CRM' as source,
            p.id,
            p.employee_id,
            e.full_name as employee_name,
            e.position,
            c.agent_type as payment_type,
            p.final_amount as amount,
            p.report_month,
            c.address,
            c.contract_number,
            c.project_type,
            p.stage_name,
            p.payment_type as payment_subtype,
            p.payment_status
        FROM payments p
        JOIN employees e ON p.employee_id = e.id
        LEFT JOIN crm_cards cc ON p.crm_card_id = cc.id
        LEFT JOIN supervision_cards sc ON p.supervision_card_id = sc.id
        LEFT JOIN contracts c ON COALESCE(cc.contract_id, sc.contract_id) = c.id
        WHERE p.report_month LIKE ?
        AND (p.crm_card_id IS NOT NULL OR p.supervision_card_id IS NOT NULL)

        UNION ALL

        SELECT
            'Оклад' as source,
            s.id,
            s.employee_id,
            e.full_name as employee_name,
            e.position,
            c.agent_type as payment_type,
            s.amount,
            s.report_month,
            c.address,
            c.contract_number,
            s.project_type,
            s.stage_name,
            NULL as payment_subtype,
            s.payment_status
        FROM salaries s
        JOIN employees e ON s.employee_id = e.id
        LEFT JOIN contracts c ON s.contract_id = c.id
        WHERE s.report_month LIKE ?

        ORDER BY 2 DESC
        ''', (f'{year}-{month:02d}%', f'{year}-{month:02d}%'))

        payments = [dict(row) for row in cursor.fetchall()]
        self.close()
        return payments
    
    def get_year_payments(self, year):
        """Получение выплат за год из всех источников"""
        conn = self.connect()
        cursor = conn.cursor()

        # Объединяем выплаты из payments (CRM) и salaries (оклады)
        cursor.execute('''
        SELECT
            p.final_amount as amount
        FROM payments p
        WHERE p.report_month LIKE ?
        AND (p.crm_card_id IS NOT NULL OR p.supervision_card_id IS NOT NULL)

        UNION ALL

        SELECT
            s.amount
        FROM salaries s
        WHERE s.report_month LIKE ?
        ''', (f'{year}%', f'{year}%'))

        payments = [dict(row) for row in cursor.fetchall()]
        self.close()
        return payments
    
    def get_payments_by_type(self, payment_type):
        """Получение выплат по типу"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT s.*, e.full_name as employee_name, e.position,
               c.contract_number, c.address, c.area, c.city
        FROM salaries s
        JOIN employees e ON s.employee_id = e.id
        LEFT JOIN contracts c ON s.contract_id = c.id
        WHERE s.payment_type = ?
        ORDER BY s.id DESC
        ''', (payment_type,))
        
        payments = [dict(row) for row in cursor.fetchall()]
        self.close()
        return payments
    
    def add_salary(self, salary_data):
        """Добавление выплаты"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO salaries
        (contract_id, employee_id, payment_type, stage_name, amount,
         advance_payment, report_month, comments, project_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            salary_data.get('contract_id'),
            salary_data['employee_id'],
            salary_data['payment_type'],
            salary_data.get('stage_name'),
            salary_data['amount'],
            salary_data.get('advance_payment', 0),
            salary_data.get('report_month', ''),
            salary_data.get('comments', ''),
            salary_data.get('project_type', 'Индивидуальный')
        ))
        
        conn.commit()
        self.close()
    
    def update_salary(self, salary_id, salary_data):
        """Обновление выплаты"""
        conn = self.connect()
        cursor = conn.cursor()
        
        set_clause = ', '.join([f'{key} = ?' for key in salary_data.keys()])
        values = list(salary_data.values()) + [salary_id]
        
        cursor.execute(f'UPDATE salaries SET {set_clause} WHERE id = ?', values)
        conn.commit()
        self.close()
    
    def delete_payment(self, payment_id):
        """Удаление выплаты"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM salaries WHERE id = ?', (payment_id,))
        conn.commit()
        self.close()
    
    def get_employee_report_data(self, project_type, period, year, quarter, month):
        """Получение данных для отчета по сотрудникам"""
        conn = self.connect()
        cursor = conn.cursor()
        
        where_clause = self.build_period_where(year, quarter, month)
        
        # Выполненные заказы
        cursor.execute(f'''
        SELECT e.full_name as employee_name, e.position, COUNT(se.id) as count
        FROM stage_executors se
        JOIN employees e ON se.executor_id = e.id
        JOIN crm_cards cc ON se.crm_card_id = cc.id
        JOIN contracts c ON cc.contract_id = c.id
        WHERE c.project_type = ? AND se.completed = 1
        {where_clause}
        GROUP BY se.executor_id
        ORDER BY count DESC
        ''', (project_type,))
        completed = [dict(row) for row in cursor.fetchall()]
        
        # Площадь
        cursor.execute(f'''
        SELECT e.full_name as employee_name, e.position, SUM(c.area) as total_area
        FROM stage_executors se
        JOIN employees e ON se.executor_id = e.id
        JOIN crm_cards cc ON se.crm_card_id = cc.id
        JOIN contracts c ON cc.contract_id = c.id
        WHERE c.project_type = ? AND se.completed = 1
        {where_clause}
        GROUP BY se.executor_id
        ORDER BY total_area DESC
        ''', (project_type,))
        area = [dict(row) for row in cursor.fetchall()]
        
        # Просрочки дедлайнов
        cursor.execute(f'''
        SELECT e.full_name as employee_name,
               COUNT(*) as overdue_count,
               AVG(julianday(se.completed_date) - julianday(se.deadline)) as avg_overdue_days
        FROM stage_executors se
        JOIN employees e ON se.executor_id = e.id
        JOIN crm_cards cc ON se.crm_card_id = cc.id
        JOIN contracts c ON cc.contract_id = c.id
        WHERE c.project_type = ? 
              AND se.completed = 1 
              AND se.completed_date > se.deadline
        {where_clause}
        GROUP BY se.executor_id
        ORDER BY overdue_count DESC
        ''', (project_type,))
        deadlines = [dict(row) for row in cursor.fetchall()]
        
        # Зарплаты
        cursor.execute(f'''
        SELECT e.full_name as employee_name, e.position, SUM(s.amount) as total_salary
        FROM salaries s
        JOIN employees e ON s.employee_id = e.id
        WHERE s.payment_type LIKE ?
        {where_clause.replace('contract_date', 'report_month')}
        GROUP BY s.employee_id
        ORDER BY total_salary DESC
        ''', (f'%{project_type}%',))
        salaries = [dict(row) for row in cursor.fetchall()]
        
        self.close()
        
        return {
            'completed': completed,
            'area': area,
            'deadlines': deadlines,
            'salaries': salaries
        }
    


    def add_approval_deadline_field(self):
        """Миграция: добавление поля approval_deadline в crm_cards"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Проверяем, есть ли уже это поле
            cursor.execute("PRAGMA table_info(crm_cards)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'approval_deadline' not in columns:
                print("[>] Выполняется миграция: добавление approval_deadline...")
                cursor.execute("ALTER TABLE crm_cards ADD COLUMN approval_deadline DATE")
                conn.commit()
                print("[OK] Поле approval_deadline добавлено")
            else:
                print("[OK] Поле approval_deadline уже существует")
            
            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка миграции approval_deadline: {e}")
            import traceback
            traceback.print_exc()
            
    def add_approval_stages_field(self):
        """Миграция: добавление поля approval_stages в crm_cards"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute("PRAGMA table_info(crm_cards)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'approval_stages' not in columns:
                print("[>] Выполняется миграция: добавление approval_stages...")
                cursor.execute("ALTER TABLE crm_cards ADD COLUMN approval_stages TEXT")
                conn.commit()
                print("[OK] Поле approval_stages добавлено")
            else:
                print("[OK] Поле approval_stages уже существует")
            
            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка миграции approval_stages: {e}")
            
    def create_approval_deadlines_table(self):
        """Создание таблицы для дедлайнов этапов согласования"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS approval_stage_deadlines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crm_card_id INTEGER NOT NULL,
                stage_name TEXT NOT NULL,
                deadline DATE NOT NULL,
                is_completed BOOLEAN DEFAULT 0,
                completed_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (crm_card_id) REFERENCES crm_cards(id)
            )
            ''')
            
            conn.commit()
            self.close()
            print("[OK] Таблица approval_stage_deadlines создана")
        except Exception as e:
            print(f"[WARN] Ошибка создания таблицы approval_stage_deadlines: {e}")
            
    def get_approval_stage_deadlines(self, crm_card_id):
        """Получение дедлайнов по стадиям согласования"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT stage_name, deadline, is_completed, completed_date
            FROM approval_stage_deadlines
            WHERE crm_card_id = ?
            ORDER BY deadline ASC
            ''', (crm_card_id,))
            
            rows = cursor.fetchall()
            self.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Ошибка получения дедлайнов согласования: {e}")
            return []

    def complete_approval_stage(self, crm_card_id, stage_name):
        """Отметка стадии согласования как завершенной"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE approval_stage_deadlines
            SET is_completed = 1, completed_date = datetime('now')
            WHERE crm_card_id = ? AND stage_name = ?
            ''', (crm_card_id, stage_name))
            
            conn.commit()
            self.close()
            print(f"[OK] Стадия согласования '{stage_name}' завершена")
        except Exception as e:
            print(f"Ошибка завершения стадии согласования: {e}")
          
    def sync_approval_stages_to_json(self, crm_card_id):
        """Синхронизация этапов согласования в JSON (для совместимости)"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Получаем ВСЕ этапы (включая согласованные)
            cursor.execute('''
            SELECT stage_name FROM approval_stage_deadlines
            WHERE crm_card_id = ?
            ORDER BY id ASC
            ''', (crm_card_id,))
            
            rows = cursor.fetchall()
            stage_names = [row['stage_name'] for row in rows]
            
            # Сохраняем в JSON
            if stage_names:
                stages_json = json.dumps(stage_names, ensure_ascii=False)
                
                cursor.execute('''
                UPDATE crm_cards
                SET approval_stages = ?
                WHERE id = ?
                ''', (stages_json, crm_card_id))
                
                conn.commit()
            
            self.close()
        except Exception as e:
            print(f"Ошибка синхронизации этапов: {e}")
    
    def get_approval_statistics(self, project_type, period, year, quarter, month, project_id=None):
        """Получение статистики по согласованиям"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Формируем WHERE для периода
            where_clauses = ['c.project_type = ?']
            params = [project_type]
            
            if period == 'Год':
                where_clauses.append("strftime('%Y', asd.created_at) = ?")
                params.append(str(year))
            elif period == 'Квартал' and quarter:
                q_months = {'Q1': (1, 3), 'Q2': (4, 6), 'Q3': (7, 9), 'Q4': (10, 12)}
                start, end = q_months[quarter]
                where_clauses.append(f"strftime('%Y', asd.created_at) = ? AND CAST(strftime('%m', asd.created_at) AS INTEGER) BETWEEN {start} AND {end}")
                params.append(str(year))
            elif period == 'Месяц' and month:
                where_clauses.append("strftime('%Y-%m', asd.created_at) = ?")
                params.append(f'{year}-{month:02d}')
            
            # ========== НОВОЕ: ФИЛЬТР ПО ПРОЕКТУ ==========
            if project_id:
                where_clauses.append('c.id = ?')
                params.append(project_id)
            # =============================================
            
            where_clause = ' AND '.join(where_clauses)
            
            query = f'''
            SELECT asd.stage_name, asd.deadline, asd.is_completed, asd.completed_date,
                   asd.created_at as assigned_date,
                   c.contract_number || ' - ' || c.address as project_info
            FROM approval_stage_deadlines asd
            JOIN crm_cards cc ON asd.crm_card_id = cc.id
            JOIN contracts c ON cc.contract_id = c.id
            WHERE {where_clause}
            ORDER BY asd.created_at DESC
            '''
            
            cursor.execute(query, params)
            
            stats = [dict(row) for row in cursor.fetchall()]
            self.close()
            
            return stats
            
        except Exception as e:
            print(f"Ошибка получения статистики согласований: {e}")
            return []
        
    def update_stage_executor_deadline(self, crm_card_id, stage_keyword, deadline):
        """Обновление дедлайна исполнителя"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Сначала найдем, какие записи есть для этой карточки (для отладки)
            cursor.execute('''
            SELECT id, stage_name, executor_id, completed, deadline
            FROM stage_executors
            WHERE crm_card_id = ?
            ORDER BY id DESC
            ''', (crm_card_id,))
            
            records = cursor.fetchall()
            print(f"\n[UPDATE DEADLINE] Карточка {crm_card_id}, ищем ключевое слово: '{stage_keyword}'")
            print(f"[UPDATE DEADLINE] Найдено записей в stage_executors: {len(records)}")
            for rec in records:
                print(f"  • ID={rec['id']}, Стадия='{rec['stage_name']}', Дедлайн={rec['deadline']}, Завершено={rec['completed']}")
            
            # Обновляем дедлайн по ключевому слову
            search_pattern = f'%{stage_keyword}%'
            
            cursor.execute('''
            UPDATE stage_executors
            SET deadline = ?
            WHERE crm_card_id = ? 
              AND stage_name LIKE ?
              AND completed = 0
            ''', (deadline, crm_card_id, search_pattern))
            
            rows_affected = cursor.rowcount
            
            conn.commit()
            self.close()
            
            if rows_affected > 0:
                print(f"[OK] Дедлайн исполнителя обновлен: {rows_affected} записей -> {deadline}")
            else:
                print(f"[WARN] Не найдено активных записей для обновления (паттерн: {search_pattern})")
            
            return rows_affected > 0
        except Exception as e:
            print(f"[ERROR] Ошибка обновления дедлайна исполнителя: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def add_project_data_link_field(self):
        """Миграция: добавление поля project_data_link в crm_cards"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute("PRAGMA table_info(crm_cards)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'project_data_link' not in columns:
                print("[>] Выполняется миграция: добавление project_data_link...")
                cursor.execute("ALTER TABLE crm_cards ADD COLUMN project_data_link TEXT")
                conn.commit()
                print("[OK] Поле project_data_link добавлено")
            else:
                print("[OK] Поле project_data_link уже существует")
            
            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка миграции project_data_link: {e}")
            
    def get_crm_card_id_by_contract(self, contract_id):
        """Получение ID CRM карточки по ID договора"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM crm_cards WHERE contract_id = ?', (contract_id,))
            row = cursor.fetchone()
            self.close()
            
            return row['id'] if row else None
        except Exception as e:
            print(f"Ошибка получения CRM карточки: {e}")
            return None

    def delete_order(self, contract_id, crm_card_id=None):
        """Полное удаление заказа из системы"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            print(f"\n🗑️ УДАЛЕНИЕ ЗАКАЗА:")
            print(f"   Contract ID: {contract_id}")
            print(f"   CRM Card ID: {crm_card_id}")

            # 1. Удаляем все связанные записи исполнителей
            if crm_card_id:
                cursor.execute('DELETE FROM stage_executors WHERE crm_card_id = ?', (crm_card_id,))
                print(f"   [OK] Удалены исполнители стадий")

                # 2. Удаляем дедлайны этапов согласования
                cursor.execute('DELETE FROM approval_stage_deadlines WHERE crm_card_id = ?', (crm_card_id,))
                print(f"   [OK] Удалены дедлайны согласований")

                # 3. Удаляем CRM карточку
                cursor.execute('DELETE FROM crm_cards WHERE id = ?', (crm_card_id,))
                print(f"   [OK] Удалена CRM карточка")

            # 4. Удаляем записи зарплат
            cursor.execute('DELETE FROM salaries WHERE contract_id = ?', (contract_id,))
            print(f"   [OK] Удалены записи зарплат")

            # 5. Удаляем папку на Яндекс.Диске (асинхронно)
            if YANDEX_DISK_TOKEN:
                try:
                    cursor.execute('SELECT yandex_folder_path FROM contracts WHERE id = ?', (contract_id,))
                    result = cursor.fetchone()
                    if result and result['yandex_folder_path']:
                        folder_path = result['yandex_folder_path']

                        # Удаляем папку в фоновом потоке (не блокирует UI)
                        def delete_folder_async():
                            try:
                                yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                                if yd.delete_folder(folder_path):
                                    print(f"   [OK] Удалена папка на Яндекс.Диске: {folder_path}")
                                else:
                                    print(f"   [WARN] Не удалось удалить папку на Яндекс.Диске")
                            except Exception as e:
                                print(f"   [ERROR] Ошибка удаления папки: {e}")

                        thread = threading.Thread(target=delete_folder_async, daemon=True)
                        thread.start()
                except Exception as e:
                    print(f"   [WARN] Ошибка при подготовке удаления папки на Яндекс.Диске: {e}")

            # 6. Удаляем договор
            cursor.execute('DELETE FROM contracts WHERE id = ?', (contract_id,))
            print(f"   [OK] Удален договор")

            conn.commit()
            self.close()

            print(f"   [SUCCESS] Заказ полностью удален из системы\n")

        except Exception as e:
            print(f"[ERROR] Ошибка удаления заказа: {e}")
            import traceback
            traceback.print_exc()
            raise e

    def delete_supervision_order(self, contract_id, supervision_card_id=None):
        """Полное удаление заказа надзора из системы"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            print(f"\n🗑️ УДАЛЕНИЕ ЗАКАЗА НАДЗОРА:")
            print(f"   Contract ID: {contract_id}")
            print(f"   Supervision Card ID: {supervision_card_id}")

            # 1. Удаляем историю проекта надзора
            if supervision_card_id:
                cursor.execute('DELETE FROM supervision_project_history WHERE supervision_card_id = ?', (supervision_card_id,))
                print(f"   [OK] Удалена история проекта надзора")

                # 2. Удаляем оплаты связанные с карточкой надзора
                cursor.execute('DELETE FROM payments WHERE supervision_card_id = ?', (supervision_card_id,))
                print(f"   [OK] Удалены оплаты надзора")

                # 3. Удаляем карточку надзора
                cursor.execute('DELETE FROM supervision_cards WHERE id = ?', (supervision_card_id,))
                print(f"   [OK] Удалена карточка надзора")

            # 4. Удаляем записи зарплат по контракту
            cursor.execute('DELETE FROM salaries WHERE contract_id = ?', (contract_id,))
            print(f"   [OK] Удалены записи зарплат")

            # 5. Удаляем договор
            cursor.execute('DELETE FROM contracts WHERE id = ?', (contract_id,))
            print(f"   [OK] Удален договор")

            conn.commit()
            self.close()

            print(f"   [SUCCESS] Заказ надзора полностью удален из системы\n")

        except Exception as e:
            print(f"[ERROR] Ошибка удаления заказа надзора: {e}")
            import traceback
            traceback.print_exc()
            raise e
        
    # ========== МЕТОДЫ ДЛЯ CRM АВТОРСКОГО НАДЗОРА ==========
    def create_supervision_table_migration(self):
        """Миграция: обновление таблицы supervision_cards"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Проверяем, существует ли таблица
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='supervision_cards'")
            exists = cursor.fetchone()
            
            if not exists:
                print("[>] Создание таблицы supervision_cards...")
                cursor.execute('''
                CREATE TABLE supervision_cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_id INTEGER NOT NULL,
                    column_name TEXT NOT NULL DEFAULT 'Новый заказ',
                    deadline DATE,
                    tags TEXT,
                    senior_manager_id INTEGER,
                    dan_id INTEGER,
                    dan_completed BOOLEAN DEFAULT 0,
                    is_paused BOOLEAN DEFAULT 0,
                    pause_reason TEXT,
                    paused_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (contract_id) REFERENCES contracts(id),
                    FOREIGN KEY (senior_manager_id) REFERENCES employees(id),
                    FOREIGN KEY (dan_id) REFERENCES employees(id)
                )
                ''')
                conn.commit()
                print("[OK] Таблица supervision_cards создана")
            else:
                # Проверяем наличие новых полей
                cursor.execute("PRAGMA table_info(supervision_cards)")
                columns = [col[1] for col in cursor.fetchall()]
                
                new_fields = {
                    'senior_manager_id': 'INTEGER',
                    'dan_id': 'INTEGER',
                    'dan_completed': 'BOOLEAN DEFAULT 0',
                    'is_paused': 'BOOLEAN DEFAULT 0',
                    'pause_reason': 'TEXT',
                    'paused_at': 'TIMESTAMP'
                }
                
                for field, field_type in new_fields.items():
                    if field not in columns:
                        print(f"[>] Добавление поля {field}...")
                        cursor.execute(f"ALTER TABLE supervision_cards ADD COLUMN {field} {field_type}")
                        print(f"[OK] Поле {field} добавлено")
                
                conn.commit()
            
            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка миграции supervision_cards: {e}")
            import traceback
            traceback.print_exc()
            
    def create_supervision_history_table(self):
        """Создание таблицы истории проектов надзора"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS supervision_project_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supervision_card_id INTEGER NOT NULL,
                entry_type TEXT NOT NULL,
                message TEXT NOT NULL,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supervision_card_id) REFERENCES supervision_cards(id),
                FOREIGN KEY (created_by) REFERENCES employees(id)
            )
            ''')
            
            conn.commit()
            self.close()
            print("[OK] Таблица supervision_project_history создана")
            
        except Exception as e:
            print(f"[WARN] Ошибка создания таблицы supervision_project_history: {e}")
       
    def fix_supervision_cards_column_name(self):
        """Миграция: исправление column_name для существующих карточек надзора"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            print("[>] Проверка и исправление column_name в supervision_cards...")
            
            # Обновляем все старые карточки с неправильным column_name
            cursor.execute('''
            UPDATE supervision_cards
            SET column_name = 'Новый заказ', updated_at = datetime('now')
            WHERE column_name NOT IN (
                'Новый заказ', 'В ожидании',
                'Стадия 1: Закупка керамогранита', 'Стадия 2: Закупка сантехники',
                'Стадия 3: Закупка оборудования', 'Стадия 4: Закупка дверей и окон',
                'Стадия 5: Закупка настенных материалов', 'Стадия 6: Закупка напольных материалов',
                'Стадия 7: Лепного декора', 'Стадия 8: Освещения',
                'Стадия 9: бытовой техники', 'Стадия 10: Закупка заказной мебели',
                'Стадия 11: Закупка фабричной мебели', 'Стадия 12: Закупка декора',
                'Выполненный проект'
            )
            ''')
            
            fixed_count = cursor.rowcount
            
            if fixed_count > 0:
                print(f"[OK] Исправлено {fixed_count} карточек надзора (установлено 'Новый заказ')")
            else:
                print("[OK] Все карточки надзора уже имеют правильные значения column_name")
            
            conn.commit()
            self.close()
            
        except Exception as e:
            print(f"[ERROR] Ошибка миграции column_name: {e}")
            import traceback
            traceback.print_exc()
            
    def create_supervision_card(self, contract_id):
        """Создание карточки авторского надзора"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Проверяем, существует ли уже АКТИВНАЯ карточка надзора
            cursor.execute('''
            SELECT sc.id, c.status 
            FROM supervision_cards sc
            JOIN contracts c ON sc.contract_id = c.id
            WHERE sc.contract_id = ? AND c.status = 'АВТОРСКИЙ НАДЗОР'
            ''', (contract_id,))
            existing = cursor.fetchone()
            
            if existing:
                print(f"[WARN] Активная карточка надзора для договора {contract_id} уже существует (ID={existing['id']})")
                self.close()
                return existing['id']
            
            # Создаем новую карточку в колонке "Новый заказ"
            cursor.execute('''
            INSERT INTO supervision_cards (contract_id, column_name, created_at)
            VALUES (?, 'Новый заказ', datetime('now'))
            ''', (contract_id,))
            
            conn.commit()
            card_id = cursor.lastrowid
            self.close()
            
            print(f"[OK] Создана карточка надзора ID={card_id} для договора {contract_id} в колонке 'Новый заказ'")
            return card_id
            
        except Exception as e:
            print(f"[ERROR] Ошибка создания карточки надзора: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_supervision_cards_active(self):
        """Получение активных карточек надзора (НЕ архив)"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT sc.*, 
               sc.dan_completed,  -- ← ДОБАВЬТЕ ЭТУ СТРОКУ
               c.contract_number, c.address, c.area, c.city, c.agent_type, c.status,
               e1.full_name as senior_manager_name,
               e2.full_name as dan_name
        FROM supervision_cards sc
        JOIN contracts c ON sc.contract_id = c.id
        LEFT JOIN employees e1 ON sc.senior_manager_id = e1.id
        LEFT JOIN employees e2 ON sc.dan_id = e2.id
        WHERE c.status = 'АВТОРСКИЙ НАДЗОР'
        ORDER BY sc.id DESC
        ''')
        
        cards = [dict(row) for row in cursor.fetchall()]
        self.close()
        return cards
    
    def get_supervision_cards_archived(self):
        """Получение архивных карточек надзора"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT sc.*,
               c.contract_number, c.address, c.area, c.city, c.agent_type, c.status, c.termination_reason, c.contract_date, c.status_changed_date,
               e1.full_name as senior_manager_name,
               e2.full_name as dan_name  -- ← Добавили ДАН'а
        FROM supervision_cards sc
        JOIN contracts c ON sc.contract_id = c.id
        LEFT JOIN employees e1 ON sc.senior_manager_id = e1.id
        LEFT JOIN employees e2 ON sc.dan_id = e2.id
        WHERE c.status IN ('СДАН', 'РАСТОРГНУТ')
        ORDER BY sc.id DESC
        ''')
        
        cards = [dict(row) for row in cursor.fetchall()]
        self.close()
        return cards
    
    def update_supervision_card(self, card_id, updates):
        """Обновление карточки надзора"""
        conn = self.connect()
        cursor = conn.cursor()
        
        set_clause = ', '.join([f'{key} = ?' for key in updates.keys()])
        values = list(updates.values()) + [card_id]
        
        cursor.execute(f'UPDATE supervision_cards SET {set_clause}, updated_at = datetime("now") WHERE id = ?', values)
        conn.commit()
        self.close()

    def update_supervision_card_column(self, card_id, column_name):
        """Обновление колонки карточки надзора"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE supervision_cards 
        SET column_name = ?, updated_at = datetime("now")
        WHERE id = ?
        ''', (column_name, card_id))
        
        conn.commit()
        self.close()
        
    def pause_supervision_card(self, card_id, reason, employee_id):
        """Приостановка карточки надзора"""
        updates = {
            'is_paused': 1,
            'pause_reason': reason,
            'paused_at': 'datetime("now")'
        }
        self.update_supervision_card(card_id, updates)
        
        # Добавляем запись в историю
        self.add_supervision_history(
            card_id,
            'pause',
            f"Проект приостановлен. Причина: {reason}",
            employee_id
        )

    def resume_supervision_card(self, card_id, employee_id):
        """Возобновление карточки надзора"""
        updates = {
            'is_paused': 0
            # НЕ сбрасываем pause_reason - оставляем в истории
        }
        self.update_supervision_card(card_id, updates)
        
        # Добавляем запись в историю
        self.add_supervision_history(
            card_id,
            'resume',
            "Проект возобновлен",
            employee_id
        )
        
    def get_supervision_statistics(self, period, year, quarter, month):
        """Статистика CRM надзора"""
        conn = self.connect()
        cursor = conn.cursor()
        
        where_clause = self.build_period_where(year, quarter, month).replace('contract_date', 'sc.created_at')
        
        query = f'''
        SELECT sc.id, sc.column_name, sc.deadline, sc.is_paused,
               c.contract_number, c.address, c.area, c.city, c.status,
               e1.full_name as senior_manager_name,
               e2.full_name as dan_name
        FROM supervision_cards sc
        JOIN contracts c ON sc.contract_id = c.id
        LEFT JOIN employees e1 ON sc.senior_manager_id = e1.id
        LEFT JOIN employees e2 ON sc.dan_id = e2.id
        WHERE 1=1 {where_clause}
        ORDER BY sc.id DESC
        '''
        
        cursor.execute(query)
        stats = [dict(row) for row in cursor.fetchall()]
        self.close()
        
        return stats

    def get_contract_id_by_supervision_card(self, card_id):
        """Получение ID договора по карточке надзора"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('SELECT contract_id FROM supervision_cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        self.close()
        
        return row['contract_id'] if row else None
    
    def complete_supervision_stage(self, card_id):
        """Отметка стадии надзора как сданной"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE supervision_cards
        SET dan_completed = 1, updated_at = datetime("now")
        WHERE id = ?
        ''', (card_id,))
        
        conn.commit()
        self.close()
        print(f"[OK] Стадия надзора ID={card_id} отмечена как сданная")

    def reset_supervision_stage_completion(self, card_id):
        """Сброс отметки о сдаче (при перемещении на новую стадию)"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE supervision_cards
        SET dan_completed = 0, updated_at = datetime("now")
        WHERE id = ?
        ''', (card_id,))
        
        conn.commit()
        self.close()
        print(f"[OK] Отметка о сдаче сброшена для карточки ID={card_id}")
    
    def add_supervision_history(self, card_id, entry_type, message, employee_id):
        """Добавление записи в историю проекта надзора"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO supervision_project_history 
            (supervision_card_id, entry_type, message, created_by)
            VALUES (?, ?, ?, ?)
            ''', (card_id, entry_type, message, employee_id))
            
            conn.commit()
            self.close()
            print(f"[OK] История проекта обновлена: {entry_type}")
            
        except Exception as e:
            print(f"[ERROR] Ошибка добавления записи в историю: {e}")
            import traceback
            traceback.print_exc()

    def get_supervision_history(self, card_id):
        """Получение истории проекта"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT sph.*, e.full_name as created_by_name
            FROM supervision_project_history sph
            LEFT JOIN employees e ON sph.created_by = e.id
            WHERE sph.supervision_card_id = ?
            ORDER BY sph.created_at DESC
            ''', (card_id,))
            
            rows = cursor.fetchall()
            self.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"[ERROR] Ошибка получения истории: {e}")
            return []

    def add_action_history(self, user_id, action_type, entity_type, entity_id, description):
        """Добавление записи в историю действий (action_history)"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute('''
            INSERT INTO action_history
            (user_id, action_type, entity_type, entity_id, description)
            VALUES (?, ?, ?, ?, ?)
            ''', (user_id, action_type, entity_type, entity_id, description))

            conn.commit()
            self.close()
            print(f"[OK] История действия добавлена: {action_type} - {entity_type} #{entity_id}")

        except Exception as e:
            print(f"[ERROR] Ошибка добавления записи в историю: {e}")
            import traceback
            traceback.print_exc()

    def get_supervision_addresses(self):
        """Получение списка адресов для фильтра"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT DISTINCT c.id as contract_id, c.contract_number, c.address
        FROM supervision_cards sc
        JOIN contracts c ON sc.contract_id = c.id
        ORDER BY c.contract_number DESC
        ''')
        
        addresses = [dict(row) for row in cursor.fetchall()]
        self.close()
        return addresses

    def get_supervision_statistics_filtered(self, period, year, quarter, month,
                                            address_id, stage, executor_id, manager_id, status):
        """Статистика с фильтрами"""
        conn = self.connect()
        cursor = conn.cursor()
        
        where_clauses = []
        params = []
        
        # Фильтр по периоду
        if period == 'Год':
            where_clauses.append("strftime('%Y', sc.created_at) = ?")
            params.append(str(year))
        elif period == 'Квартал' and quarter:
            q_months = {'Q1': (1, 3), 'Q2': (4, 6), 'Q3': (7, 9), 'Q4': (10, 12)}
            start, end = q_months[quarter]
            where_clauses.append(f"strftime('%Y', sc.created_at) = ? AND CAST(strftime('%m', sc.created_at) AS INTEGER) BETWEEN {start} AND {end}")
            params.append(str(year))
        elif period == 'Месяц' and month:
            where_clauses.append("strftime('%Y-%m', sc.created_at) = ?")
            params.append(f'{year}-{month:02d}')
        
        # Фильтр по адресу
        if address_id:
            where_clauses.append('c.id = ?')
            params.append(address_id)
        
        # Фильтр по стадии
        if stage:
            where_clauses.append('sc.column_name = ?')
            params.append(stage)
        
        # Фильтр по исполнителю
        if executor_id:
            where_clauses.append('sc.dan_id = ?')
            params.append(executor_id)
        
        # Фильтр по менеджеру
        if manager_id:
            where_clauses.append('sc.senior_manager_id = ?')
            params.append(manager_id)
        
        # Фильтр по статусу
        if status == 'Приостановлено':
            where_clauses.append('sc.is_paused = 1')
        elif status == 'Работа сдана':
            where_clauses.append('sc.dan_completed = 1')
        elif status == 'В работе':
            where_clauses.append('sc.is_paused = 0 AND sc.dan_completed = 0')
        
        where_clause = ' AND '.join(where_clauses) if where_clauses else '1=1'
        
        query = f'''
        SELECT sc.id, sc.column_name, sc.deadline, sc.is_paused, sc.dan_completed,
               c.contract_number, c.address, c.area, c.city, c.status,
               e1.full_name as senior_manager_name,
               e2.full_name as dan_name
        FROM supervision_cards sc
        JOIN contracts c ON sc.contract_id = c.id
        LEFT JOIN employees e1 ON sc.senior_manager_id = e1.id
        LEFT JOIN employees e2 ON sc.dan_id = e2.id
        WHERE {where_clause}
        ORDER BY sc.id DESC
        '''
        
        cursor.execute(query, params)
        stats = [dict(row) for row in cursor.fetchall()]
        self.close()
        
        return stats
    
    def reset_stage_completion(self, crm_card_id):
        """Сброс всех отметок о завершении при перемещении"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE stage_executors
        SET completed = 0, completed_date = NULL
        WHERE crm_card_id = ?
        ''', (crm_card_id,))
        
        conn.commit()
        self.close()
        print(f"[OK] Все отметки о завершении сброшены для карточки {crm_card_id}")

    def reset_designer_completion(self, crm_card_id):
        """Сброс отметки о завершении дизайнером"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE stage_executors
        SET completed = 0, completed_date = NULL
        WHERE crm_card_id = ? AND stage_name LIKE '%концепция%'
        ''', (crm_card_id,))
        
        conn.commit()
        self.close()
        print(f"[OK] Отметка дизайнера сброшена для карточки {crm_card_id}")

    def reset_draftsman_completion(self, crm_card_id):
        """Сброс отметки о завершении чертёжником"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE stage_executors
        SET completed = 0, completed_date = NULL
        WHERE crm_card_id = ? AND (stage_name LIKE '%чертежи%' OR stage_name LIKE '%планировочные%')
        ''', (crm_card_id,))
        
        conn.commit()
        self.close()
        print(f"[OK] Отметка чертёжника сброшена для карточки {crm_card_id}")
        
    def create_manager_acceptance_table(self):
        """Создание таблицы принятия работ менеджером"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS manager_stage_acceptance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crm_card_id INTEGER NOT NULL,
                stage_name TEXT NOT NULL,
                executor_name TEXT NOT NULL,
                accepted_by INTEGER NOT NULL,
                accepted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (crm_card_id) REFERENCES crm_cards(id),
                FOREIGN KEY (accepted_by) REFERENCES employees(id)
            )
            ''')
            
            conn.commit()
            self.close()
            print("[OK] Таблица manager_stage_acceptance создана")
            
        except Exception as e:
            print(f"[WARN] Ошибка создания таблицы manager_stage_acceptance: {e}")
            
    def save_manager_acceptance(self, crm_card_id, stage_name, executor_name, manager_id):
        """Сохранение принятия работы менеджером"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO manager_stage_acceptance 
            (crm_card_id, stage_name, executor_name, accepted_by)
            VALUES (?, ?, ?, ?)
            ''', (crm_card_id, stage_name, executor_name, manager_id))
            
            conn.commit()
            self.close()
            print(f"[OK] Принятие стадии '{stage_name}' сохранено")
            
        except Exception as e:
            print(f"[ERROR] Ошибка сохранения принятия: {e}")
            import traceback
            traceback.print_exc()

    def get_submitted_stages(self, crm_card_id):
        """Получение списка сданных, но еще не принятых стадий"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT se.stage_name, e.full_name as executor_name,
                   DATE(se.submitted_date) as submitted_date
            FROM stage_executors se
            LEFT JOIN employees e ON se.executor_id = e.id
            WHERE se.crm_card_id = ?
              AND se.submitted_date IS NOT NULL
              AND se.completed = 0
            ORDER BY se.submitted_date DESC
            ''', (crm_card_id,))

            rows = cursor.fetchall()
            self.close()

            return [dict(row) for row in rows]

        except Exception as e:
            print(f"[ERROR] Ошибка получения сданных стадий: {e}")
            return []

    def get_accepted_stages(self, crm_card_id):
        """Получение списка принятых стадий"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # ИСПРАВЛЕНИЕ: Убрали некорректный JOIN с se.executor_name (такой колонки нет)
            cursor.execute('''
            SELECT msa.stage_name, msa.executor_name, msa.accepted_date,
                   e.full_name as accepted_by_name,
                   e.position as accepted_by_position,
                   (SELECT se.submitted_date
                    FROM stage_executors se
                    JOIN employees emp ON se.executor_id = emp.id
                    WHERE se.crm_card_id = msa.crm_card_id
                      AND se.stage_name = msa.stage_name
                      AND emp.full_name = msa.executor_name
                    LIMIT 1) as submitted_date
            FROM manager_stage_acceptance msa
            LEFT JOIN employees e ON msa.accepted_by = e.id
            WHERE msa.crm_card_id = ?
            ORDER BY msa.accepted_date ASC
            ''', (crm_card_id,))

            rows = cursor.fetchall()
            self.close()

            return [dict(row) for row in rows]

        except Exception as e:
            print(f"[ERROR] Ошибка получения принятых стадий: {e}")
            return []
            
    def get_crm_card_data(self, card_id):
        """Получение данных карточки для проверок"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT cc.*,
                   (SELECT se.completed 
                    FROM stage_executors se
                    WHERE se.crm_card_id = cc.id 
                      AND se.stage_name LIKE '%концепция%'
                    ORDER BY se.id DESC LIMIT 1) as designer_completed,
                   
                   (SELECT se.completed 
                    FROM stage_executors se
                    WHERE se.crm_card_id = cc.id 
                      AND (se.stage_name LIKE '%чертежи%' OR se.stage_name LIKE '%планировочные%')
                    ORDER BY se.id DESC LIMIT 1) as draftsman_completed
            FROM crm_cards cc
            WHERE cc.id = ?
            ''', (card_id,))
            
            row = cursor.fetchone()
            self.close()
            
            return dict(row) if row else None
            
        except Exception as e:
            print(f"[ERROR] Ошибка получения данных карточки: {e}")
            return None
            
    def check_contract_number_exists(self, contract_number):
        """Проверка существования номера договора"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) as count FROM contracts WHERE contract_number = ?', (contract_number,))
            exists = cursor.fetchone()['count'] > 0
            self.close()
            
            return exists
        except Exception as e:
            print(f"Ошибка проверки номера договора: {e}")
            return False
        
    def get_dashboard_statistics(self):
        """Получение общей статистики для Dashboard за все время"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Индивидуальные проекты
            cursor.execute('''
            SELECT 
                COUNT(*) as count,
                SUM(c.area) as total_area
            FROM contracts c
            WHERE c.project_type = 'Индивидуальный'
            ''')
            individual = cursor.fetchone()
            
            # Шаблонные проекты
            cursor.execute('''
            SELECT 
                COUNT(*) as count,
                SUM(c.area) as total_area
            FROM contracts c
            WHERE c.project_type = 'Шаблонный'
            ''')
            template = cursor.fetchone()
            
            # Авторский надзор
            cursor.execute('''
            SELECT 
                COUNT(DISTINCT c.id) as count,
                SUM(c.area) as total_area
            FROM contracts c
            WHERE c.status = 'АВТОРСКИЙ НАДЗОР'
            ''')
            supervision = cursor.fetchone()
            
            self.close()
            
            return {
                'individual_orders': individual['count'] if individual else 0,
                'individual_area': individual['total_area'] if individual and individual['total_area'] else 0,
                'template_orders': template['count'] if template else 0,
                'template_area': template['total_area'] if template and template['total_area'] else 0,
                'supervision_orders': supervision['count'] if supervision else 0,
                'supervision_area': supervision['total_area'] if supervision and supervision['total_area'] else 0
            }
            
        except Exception as e:
            print(f"[ERROR] Ошибка получения статистики dashboard: {e}")
            import traceback
            traceback.print_exc()
            return {
                'individual_orders': 0,
                'individual_area': 0,
                'template_orders': 0,
                'template_area': 0,
                'supervision_orders': 0,
                'supervision_area': 0
            }
        
    def get_project_statistics(self, project_type, year, quarter, month, agent_type=None, city=None):
        """Статистика индивидуальных/шаблонных (активные + архив из CRM)"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            print(f"\n{'='*60}")
            print(f"📊 GET_PROJECT_STATISTICS вызван:")
            print(f"   project_type={project_type}")
            print(f"   year={year}, quarter={quarter}, month={month}")
            print(f"   agent_type={agent_type}, city={city}")
            
            where_clauses = ['c.project_type = ?']
            params = [project_type]
            
            # ========== ФИЛЬТР ПО ПЕРИОДУ ==========
            if month:
                where_clauses.append("strftime('%Y-%m', c.contract_date) = ?")
                params.append(f'{year}-{month:02d}')
                print(f"   → Фильтр: МЕСЯЦ {year}-{month:02d}")
            elif quarter:
                q_months = {'Q1': (1, 3), 'Q2': (4, 6), 'Q3': (7, 9), 'Q4': (10, 12)}
                start, end = q_months[quarter]
                where_clauses.append(f"strftime('%Y', c.contract_date) = ? AND CAST(strftime('%m', c.contract_date) AS INTEGER) BETWEEN {start} AND {end}")
                params.append(str(year))
                print(f"   → Фильтр: КВАРТАЛ {quarter} ({year})")
            elif year:
                where_clauses.append("strftime('%Y', c.contract_date) = ?")
                params.append(str(year))
                print(f"   → Фильтр: ГОД {year}")
            else:
                print(f"   → Фильтр: ВСЁ ВРЕМЯ (без фильтра по дате)")
            
            if agent_type:
                where_clauses.append('c.agent_type = ?')
                params.append(agent_type)
                print(f"   → Фильтр: agent_type={agent_type}")
            if city:
                where_clauses.append('c.city = ?')
                params.append(city)
                print(f"   → Фильтр: city={city}")
            
            where_clause = ' AND '.join(where_clauses)
            print(f"   WHERE: {where_clause}")
            print(f"   PARAMS: {params}")
            
            # ========== ВСЕГО ЗАКАЗОВ ==========
            query = f'SELECT COUNT(*) as total FROM contracts c WHERE {where_clause}'
            print(f"\n   SQL: {query}")
            cursor.execute(query, params)
            total_orders = cursor.fetchone()['total']
            print(f"   [OK] Всего заказов: {total_orders}")
            
            cursor.execute(f'SELECT SUM(c.area) as total FROM contracts c WHERE {where_clause}', params)
            total_area = cursor.fetchone()['total'] or 0
            print(f"   [OK] Общая площадь: {total_area:.0f} м²")
            
            # ========== АКТИВНЫЕ ==========
            cursor.execute(f'''
            SELECT COUNT(*) as total FROM contracts c
            WHERE {where_clause}
              AND (c.status IS NULL OR c.status = '' OR c.status = 'В работе' OR c.status = 'Новый заказ')
            ''', params)
            active = cursor.fetchone()['total']
            print(f"   [OK] Активные: {active}")
            
            # ========== ВЫПОЛНЕННЫЕ ==========
            cursor.execute(f'''
            SELECT COUNT(*) as total FROM contracts c
            WHERE {where_clause}
              AND c.status IN ('СДАН', 'АВТОРСКИЙ НАДЗОР')
            ''', params)
            completed = cursor.fetchone()['total']
            print(f"   [OK] Выполненные: {completed}")
            
            # ========== РАСТОРГНУТО ==========
            cursor.execute(f'''
            SELECT COUNT(*) as total FROM contracts c
            WHERE {where_clause}
              AND c.status = 'РАСТОРГНУТ'
            ''', params)
            cancelled = cursor.fetchone()['total']
            print(f"   [OK] Расторгнуто: {cancelled}")
            
            # ========== ПРОСРОЧКИ ==========
            cursor.execute(f'''
            SELECT COUNT(DISTINCT c.id) as total
            FROM stage_executors se
            JOIN crm_cards cc ON se.crm_card_id = cc.id
            JOIN contracts c ON cc.contract_id = c.id
            WHERE {where_clause}
              AND se.completed = 0
              AND se.deadline < date('now')
            ''', params)
            overdue = cursor.fetchone()['total']
            print(f"   [OK] Просрочки: {overdue}")
            
            # По городам
            cursor.execute(f'''
            SELECT c.city, COUNT(*) as count
            FROM contracts c
            WHERE {where_clause} AND c.city IS NOT NULL AND c.city != ''
            GROUP BY c.city
            ''', params)
            by_cities = {row['city']: row['count'] for row in cursor.fetchall()}
            
            # По агентам
            cursor.execute(f'''
            SELECT c.agent_type, COUNT(*) as count
            FROM contracts c
            WHERE {where_clause} AND c.agent_type IS NOT NULL AND c.agent_type != ''
            GROUP BY c.agent_type
            ''', params)
            by_agents = {row['agent_type']: row['count'] for row in cursor.fetchall()}
            
            # ========== ВРЕМЯ В СТАДИЯХ ==========
            where_stages = where_clause if where_clause != 'c.project_type = ?' else f'c.project_type = ?'
            
            cursor.execute(f'''
            SELECT cc.column_name,
                   SUM(julianday(COALESCE(cc.updated_at, 'now')) - julianday(cc.created_at)) * 0.71 as total_days
            FROM crm_cards cc
            JOIN contracts c ON cc.contract_id = c.id
            WHERE {where_stages}
            GROUP BY cc.column_name
            ''', params)
            by_stages = {row['column_name']: row['total_days'] for row in cursor.fetchall()}
            
            self.close()
            
            print(f"{'='*60}\n")
            
            return {
                'total_orders': total_orders,
                'total_area': total_area,
                'active': active,
                'completed': completed,
                'cancelled': cancelled,
                'overdue': overdue,
                'by_cities': by_cities,
                'by_agents': by_agents,
                'by_stages': by_stages
            }
            
        except Exception as e:
            print(f"[ERROR] ОШИБКА get_project_statistics: {e}")
            import traceback
            traceback.print_exc()
            return {
                'total_orders': 0, 'total_area': 0, 'active': 0,
                'completed': 0, 'cancelled': 0, 'overdue': 0,
                'by_cities': {}, 'by_agents': {}, 'by_stages': {}
            }

    def get_supervision_statistics_report(self, year, quarter, month, agent_type=None, city=None):
        """Статистика надзора (ТОЛЬКО из supervision_cards)"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            print(f"\n{'='*60}")
            print(f"📊 GET_SUPERVISION_STATISTICS вызван:")
            print(f"   year={year}, quarter={quarter}, month={month}")
            print(f"   agent_type={agent_type}, city={city}")
            
            where_clauses = []
            params = []
            
            # ========== ФИЛЬТР ПО ПЕРИОДУ ==========
            if month:
                where_clauses.append("strftime('%Y-%m', c.contract_date) = ?")
                params.append(f'{year}-{month:02d}')
                print(f"   → Фильтр: МЕСЯЦ {year}-{month:02d}")
            elif quarter:
                q_months = {'Q1': (1, 3), 'Q2': (4, 6), 'Q3': (7, 9), 'Q4': (10, 12)}
                start, end = q_months[quarter]
                where_clauses.append(f"strftime('%Y', c.contract_date) = ? AND CAST(strftime('%m', c.contract_date) AS INTEGER) BETWEEN {start} AND {end}")
                params.append(str(year))
                print(f"   → Фильтр: КВАРТАЛ {quarter} ({year})")
            elif year:
                where_clauses.append("strftime('%Y', c.contract_date) = ?")
                params.append(str(year))
                print(f"   → Фильтр: ГОД {year}")
            else:
                print(f"   → Фильтр: ВСЁ ВРЕМЯ")
            
            if agent_type:
                where_clauses.append('c.agent_type = ?')
                params.append(agent_type)
            if city:
                where_clauses.append('c.city = ?')
                params.append(city)
            
            where_clause = ' AND '.join(where_clauses) if where_clauses else '1=1'
            print(f"   WHERE: {where_clause}")
            
            # ========== ВСЕГО ЗАКАЗОВ НАДЗОРА ==========
            cursor.execute(f'''
            SELECT COUNT(DISTINCT sc.id) as total
            FROM supervision_cards sc
            JOIN contracts c ON sc.contract_id = c.id
            WHERE {where_clause}
            ''', params)
            total_orders = cursor.fetchone()['total']
            print(f"   [OK] Всего: {total_orders}")
            
            cursor.execute(f'''
            SELECT SUM(c.area) as total
            FROM supervision_cards sc
            JOIN contracts c ON sc.contract_id = c.id
            WHERE {where_clause}
            ''', params)
            total_area = cursor.fetchone()['total'] or 0
            
            # ========== АКТИВНЫЕ ==========
            cursor.execute(f'''
            SELECT COUNT(DISTINCT sc.id) as total
            FROM supervision_cards sc
            JOIN contracts c ON sc.contract_id = c.id
            WHERE {where_clause}
              AND c.status = 'АВТОРСКИЙ НАДЗОР'
            ''', params)
            active = cursor.fetchone()['total']
            print(f"   [OK] Активные: {active}")
            
            # ========== ВЫПОЛНЕННЫЕ ==========
            cursor.execute(f'''
            SELECT COUNT(DISTINCT sc.id) as total
            FROM supervision_cards sc
            JOIN contracts c ON sc.contract_id = c.id
            WHERE {where_clause}
              AND c.status = 'СДАН'
            ''', params)
            completed = cursor.fetchone()['total']
            print(f"   [OK] Выполненные: {completed}")
            
            # ========== РАСТОРГНУТО ==========
            cursor.execute(f'''
            SELECT COUNT(DISTINCT sc.id) as total
            FROM supervision_cards sc
            JOIN contracts c ON sc.contract_id = c.id
            WHERE {where_clause}
              AND c.status = 'РАСТОРГНУТ'
            ''', params)
            cancelled = cursor.fetchone()['total']
            
            # ========== ПРОСРОЧКИ ==========
            cursor.execute(f'''
            SELECT COUNT(DISTINCT sc.id) as total
            FROM supervision_cards sc
            JOIN contracts c ON sc.contract_id = c.id
            WHERE {where_clause}
              AND sc.deadline IS NOT NULL
              AND sc.deadline < date('now')
              AND c.status = 'АВТОРСКИЙ НАДЗОР'
            ''', params)
            overdue = cursor.fetchone()['total']
            
            # По городам
            cursor.execute(f'''
            SELECT c.city, COUNT(DISTINCT sc.id) as count
            FROM supervision_cards sc
            JOIN contracts c ON sc.contract_id = c.id
            WHERE {where_clause} AND c.city IS NOT NULL AND c.city != ''
            GROUP BY c.city
            ''', params)
            by_cities = {row['city']: row['count'] for row in cursor.fetchall()}
            
            # По агентам
            cursor.execute(f'''
            SELECT c.agent_type, COUNT(DISTINCT sc.id) as count
            FROM supervision_cards sc
            JOIN contracts c ON sc.contract_id = c.id
            WHERE {where_clause} AND c.agent_type IS NOT NULL AND c.agent_type != ''
            GROUP BY c.agent_type
            ''', params)
            by_agents = {row['agent_type']: row['count'] for row in cursor.fetchall()}
            
            # ========== ВРЕМЯ В СТАДИЯХ ==========
            cursor.execute(f'''
            SELECT sc.column_name,
                   SUM(julianday(COALESCE(sc.updated_at, 'now')) - julianday(sc.created_at)) * 0.71 as total_days
            FROM supervision_cards sc
            JOIN contracts c ON sc.contract_id = c.id
            WHERE {where_clause}
            GROUP BY sc.column_name
            ''', params if params else [])
            by_stages = {row['column_name']: row['total_days'] for row in cursor.fetchall()}
            
            self.close()
            
            print(f"{'='*60}\n")
            
            return {
                'total_orders': total_orders,
                'total_area': total_area,
                'active': active,
                'completed': completed,
                'cancelled': cancelled,
                'overdue': overdue,
                'by_cities': by_cities,
                'by_agents': by_agents,
                'by_stages': by_stages
            }
            
        except Exception as e:
            print(f"[ERROR] КРИТИЧЕСКАЯ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
            return {
                'total_orders': 0, 'total_area': 0, 'active': 0,
                'completed': 0, 'cancelled': 0, 'overdue': 0,
                'by_cities': {}, 'by_agents': {}, 'by_stages': {}
            }
            
    def add_birth_date_column(self):
        """Добавление столбца birth_date в таблицу employees"""
        try:
            conn = self.connect()  # ← ПРАВИЛЬНО: создаем подключение
            cursor = conn.cursor()
            
            # Проверяем, есть ли уже поле
            cursor.execute("PRAGMA table_info(employees)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'birth_date' not in columns:
                print("[>] Выполняется миграция: добавление birth_date...")
                cursor.execute("ALTER TABLE employees ADD COLUMN birth_date TEXT")
                conn.commit()
                print("[OK] Поле birth_date добавлено")
            else:
                print("[OK] Поле birth_date уже существует")
            
            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка добавления birth_date: {e}")
            import traceback
            traceback.print_exc()
            
    def add_address_column(self):
        """Добавление столбца address в таблицу employees"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Проверяем, есть ли уже поле
            cursor.execute("PRAGMA table_info(employees)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'address' not in columns:
                print("[>] Выполняется миграция: добавление address...")
                cursor.execute("ALTER TABLE employees ADD COLUMN address TEXT")
                conn.commit()
                print("[OK] Поле address добавлено")
            else:
                print("[OK] Поле address уже существует")
            
            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка добавления address: {e}")
            import traceback
            traceback.print_exc()
            
    def add_secondary_position_column(self):
        """Добавление столбца secondary_position в таблицу employees"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(employees)")
            columns = [column[1] for column in cursor.fetchall()]

            if 'secondary_position' not in columns:
                print("[>] Выполняется миграция: добавление secondary_position...")
                cursor.execute("ALTER TABLE employees ADD COLUMN secondary_position TEXT")
                conn.commit()
                print("[OK] Поле secondary_position добавлено")
            else:
                print("[OK] Поле secondary_position уже существует")

            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка добавления secondary_position: {e}")

    def add_status_changed_date_column(self):
        """Добавление столбца status_changed_date в таблицу contracts"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(contracts)")
            columns = [column[1] for column in cursor.fetchall()]

            if 'status_changed_date' not in columns:
                print("[>] Выполняется миграция: добавление status_changed_date...")
                cursor.execute("ALTER TABLE contracts ADD COLUMN status_changed_date DATE")
                conn.commit()
                print("[OK] Поле status_changed_date добавлено")
            else:
                print("[OK] Поле status_changed_date уже существует")

            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка добавления status_changed_date: {e}")

    def add_tech_task_fields(self):
        """Добавление полей tech_task_file и tech_task_date в таблицу crm_cards"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(crm_cards)")
            columns = [column[1] for column in cursor.fetchall()]

            if 'tech_task_file' not in columns:
                print("[>] Выполняется миграция: добавление tech_task_file...")
                cursor.execute("ALTER TABLE crm_cards ADD COLUMN tech_task_file TEXT")
                conn.commit()
                print("[OK] Поле tech_task_file добавлено")
            else:
                print("[OK] Поле tech_task_file уже существует")

            if 'tech_task_date' not in columns:
                print("[>] Выполняется миграция: добавление tech_task_date...")
                cursor.execute("ALTER TABLE crm_cards ADD COLUMN tech_task_date DATE")
                conn.commit()
                print("[OK] Поле tech_task_date добавлено")
            else:
                print("[OK] Поле tech_task_date уже существует")

            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка добавления tech_task полей: {e}")

    def add_survey_date_column(self):
        """Добавление столбца survey_date в таблицу crm_cards"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(crm_cards)")
            columns = [column[1] for column in cursor.fetchall()]

            if 'survey_date' not in columns:
                print("[>] Выполняется миграция: добавление survey_date...")
                cursor.execute("ALTER TABLE crm_cards ADD COLUMN survey_date DATE")
                conn.commit()
                print("[OK] Поле survey_date добавлено")
            else:
                print("[OK] Поле survey_date уже существует")

            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка добавления survey_date: {e}")

    def create_project_files_table(self):
        """Создание таблицы project_files для управления файлами стадий проекта"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Проверяем, существует ли таблица
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='project_files'
            """)

            if not cursor.fetchone():
                print("[>] Создание таблицы project_files...")

                # Создаем таблицу
                cursor.execute('''
                    CREATE TABLE project_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        contract_id INTEGER NOT NULL,
                        stage TEXT NOT NULL,
                        file_type TEXT NOT NULL,
                        public_link TEXT,
                        yandex_path TEXT NOT NULL,
                        file_name TEXT NOT NULL,
                        upload_date TEXT DEFAULT CURRENT_TIMESTAMP,
                        preview_cache_path TEXT,
                        file_order INTEGER DEFAULT 0,
                        FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE CASCADE
                    )
                ''')

                # Создаем индексы
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_project_files_contract
                    ON project_files(contract_id)
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_project_files_stage
                    ON project_files(contract_id, stage)
                ''')

                conn.commit()
                print("[OK] Таблица project_files создана с индексами")
            else:
                print("[OK] Таблица project_files уже существует")

            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка создания таблицы project_files: {e}")

    def reset_approval_stages(self, crm_card_id):
        """Сброс всех этапов согласования при повторном входе в стадию"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('''
            DELETE FROM approval_stage_deadlines
            WHERE crm_card_id = ?
            ''', (crm_card_id,))
            
            conn.commit()
            rows_deleted = cursor.rowcount
            self.close()
            
            if rows_deleted > 0:
                print(f"[OK] Удалены этапы согласования для карточки {crm_card_id}: {rows_deleted} записей")
            else:
                print(f"[WARN] Не найдено этапов согласования для карточки {crm_card_id}")
            
        except Exception as e:
            print(f"[ERROR] Ошибка сброса этапов согласования: {e}")
            import traceback
            traceback.print_exc()
            
    def create_payments_system_tables(self):
        """Создание таблиц системы оплат"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # ========== ИСПРАВЛЕНИЕ: БЕЗ УДАЛЕНИЯ ТАБЛИЦЫ! ==========
            # Проверяем, существует ли таблица
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rates'")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                print("[>] Создание таблицы rates...")
                
                cursor.execute('''
                CREATE TABLE rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_type TEXT,
                    role TEXT NOT NULL,
                    stage_name TEXT,
                    rate_per_m2 REAL,
                    area_from REAL,
                    area_to REAL,
                    fixed_price REAL,
                    city TEXT,
                    surveyor_price REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                print("[OK] Таблица rates создана")
            else:
                print("[OK] Таблица rates уже существует (сохранение данных)")
            # =========================================================
            
            # Таблица выплат
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_id INTEGER NOT NULL,
                crm_card_id INTEGER,
                supervision_card_id INTEGER,
                employee_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                stage_name TEXT,
                calculated_amount REAL NOT NULL,
                manual_amount REAL,
                final_amount REAL NOT NULL,
                is_manual BOOLEAN DEFAULT 0,
                payment_type TEXT,
                report_month TEXT,
                is_paid BOOLEAN DEFAULT 0,
                paid_date TIMESTAMP,
                paid_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contract_id) REFERENCES contracts(id),
                FOREIGN KEY (employee_id) REFERENCES employees(id)
            )
            ''')
            
            # Таблица замеров
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS surveys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_id INTEGER NOT NULL,
                surveyor_id INTEGER NOT NULL,
                survey_date DATE NOT NULL,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contract_id) REFERENCES contracts(id),
                FOREIGN KEY (surveyor_id) REFERENCES employees(id)
            )
            ''')
            
            conn.commit()
            self.close()
            print("[OK] Таблицы системы оплат готовы к работе")
            
        except Exception as e:
            print(f"[ERROR] Ошибка создания таблиц оплат: {e}")
            import traceback
            traceback.print_exc()

    def add_reassigned_field_to_payments(self):
        """Миграция: добавление поля reassigned в payments"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Проверяем, есть ли уже это поле
            cursor.execute("PRAGMA table_info(payments)")
            columns = [column[1] for column in cursor.fetchall()]

            if 'reassigned' not in columns:
                print("[>] Выполняется миграция: добавление reassigned в payments...")
                cursor.execute("ALTER TABLE payments ADD COLUMN reassigned BOOLEAN DEFAULT 0")
                conn.commit()
                print("[OK] Поле reassigned добавлено")
            else:
                print("[OK] Поле reassigned уже существует")

            if 'old_employee_id' not in columns:
                print("[>] Выполняется миграция: добавление old_employee_id в payments...")
                cursor.execute("ALTER TABLE payments ADD COLUMN old_employee_id INTEGER")
                conn.commit()
                print("[OK] Поле old_employee_id добавлено")
            else:
                print("[OK] Поле old_employee_id уже существует")

            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка миграции reassigned: {e}")
            import traceback
            traceback.print_exc()

    def add_submitted_date_to_stage_executors(self):
        """Миграция: добавление поля submitted_date в stage_executors"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Проверяем, есть ли уже это поле
            cursor.execute("PRAGMA table_info(stage_executors)")
            columns = [column[1] for column in cursor.fetchall()]

            if 'submitted_date' not in columns:
                print("[>] Выполняется миграция: добавление submitted_date в stage_executors...")
                cursor.execute("ALTER TABLE stage_executors ADD COLUMN submitted_date TIMESTAMP")
                conn.commit()
                print("[OK] Поле submitted_date добавлено")
            else:
                print("[OK] Поле submitted_date уже существует")

            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка миграции submitted_date: {e}")
            import traceback
            traceback.print_exc()

    def calculate_payment_amount(self, contract_id, employee_id, role, stage_name=None, supervision_card_id=None):
        """Расчет суммы оплаты на основе тарифов"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Получаем данные договора
            cursor.execute('SELECT project_type, area, city FROM contracts WHERE id = ?', (contract_id,))
            contract = cursor.fetchone()

            if not contract:
                self.close()
                return 0

            project_type = contract['project_type']
            area = contract['area'] or 0
            city = contract['city']

            # ========== ИСПРАВЛЕНИЕ: Если это надзор, используем тарифы "Авторский надзор" ==========
            if supervision_card_id:
                print(f"[INFO] Расчет оплаты для надзора: роль={role}, стадия={stage_name}, площадь={area}")

                cursor.execute('''
                SELECT rate_per_m2 FROM rates
                WHERE project_type = 'Авторский надзор'
                  AND role = ?
                  AND (stage_name = ? OR stage_name IS NULL)
                ORDER BY CASE WHEN stage_name = ? THEN 0 ELSE 1 END
                LIMIT 1
                ''', (role, stage_name, stage_name))

                rate = cursor.fetchone()
                self.close()

                if rate and rate['rate_per_m2']:
                    amount = area * rate['rate_per_m2']
                    print(f"[INFO] Тариф надзора: {rate['rate_per_m2']} ₽/м², сумма: {amount} ₽")
                    return amount

                print(f"[WARN] Тариф для надзора не найден: роль={role}, стадия={stage_name}")
                return 0
            # ========================================================================================

            # ========== ЗАМЕРЩИК - ОСОБАЯ ЛОГИКА ==========
            if role == 'Замерщик':
                cursor.execute('''
                SELECT surveyor_price FROM rates
                WHERE role = 'Замерщик' AND city = ?
                LIMIT 1
                ''', (city,))

                rate = cursor.fetchone()
                self.close()
                return rate['surveyor_price'] if rate else 0
            # ==============================================

            # ========== ИНДИВИДУАЛЬНЫЕ: ЦЕНА ЗА М² СО СТАДИЯМИ ==========
            if project_type == 'Индивидуальный':
                # Если указана стадия (для чертёжника) - ищем по стадии
                if stage_name:
                    cursor.execute('''
                    SELECT rate_per_m2 FROM rates
                    WHERE project_type = 'Индивидуальный' 
                      AND role = ?
                      AND stage_name = ?
                    LIMIT 1
                    ''', (role, stage_name))
                    
                    rate = cursor.fetchone()
                    
                    # Если не найден тариф для конкретной стадии - пробуем без стадии
                    if not rate:
                        cursor.execute('''
                        SELECT rate_per_m2 FROM rates
                        WHERE project_type = 'Индивидуальный' 
                          AND role = ?
                          AND stage_name IS NULL
                        LIMIT 1
                        ''', (role,))
                        
                        rate = cursor.fetchone()
                else:
                    # Без стадии (для дизайнера, СДП, ГАП)
                    cursor.execute('''
                    SELECT rate_per_m2 FROM rates
                    WHERE project_type = 'Индивидуальный' 
                      AND role = ?
                      AND stage_name IS NULL
                    LIMIT 1
                    ''', (role,))
                    
                    rate = cursor.fetchone()
                
                self.close()
                
                if rate and rate['rate_per_m2']:
                    return area * rate['rate_per_m2']
                return 0
            # =============================================================
            
            # Шаблонные: диапазоны площади
            elif project_type == 'Шаблонный':
                cursor.execute('''
                SELECT fixed_price FROM rates
                WHERE project_type = 'Шаблонный' 
                  AND role = ?
                  AND area_from <= ?
                  AND (area_to >= ? OR area_to IS NULL)
                ORDER BY area_from ASC
                LIMIT 1
                ''', (role, area, area))
                
                rate = cursor.fetchone()
                self.close()
                
                if rate and rate['fixed_price']:
                    return rate['fixed_price']
                return 0
            
            # Авторский надзор: цена за м² × стадия
            elif project_type == 'Авторский надзор' or stage_name:
                cursor.execute('''
                SELECT rate_per_m2 FROM rates
                WHERE project_type = 'Авторский надзор' 
                  AND role = ?
                  AND (stage_name = ? OR stage_name IS NULL)
                LIMIT 1
                ''', (role, stage_name))
                
                rate = cursor.fetchone()
                self.close()
                
                if rate and rate['rate_per_m2']:
                    return area * rate['rate_per_m2']
                return 0
            
            self.close()
            return 0
            
        except Exception as e:
            print(f"[ERROR] Ошибка расчета оплаты: {e}")
            import traceback
            traceback.print_exc()
            return 0
        
    def create_payment_record(self, contract_id, employee_id, role, stage_name=None,
                             payment_type='Полная оплата', report_month=None,
                             crm_card_id=None, supervision_card_id=None):
        """Создание записи о выплате"""
        try:
            # ========== НОВОЕ: ДЛЯ ШАБЛОННЫХ ПРОЕКТОВ МЕНЕДЖЕРЫ ПОЛУЧАЮТ "ОКЛАД" ==========
            # Проверяем тип проекта
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT project_type FROM contracts WHERE id = ?', (contract_id,))
            contract = cursor.fetchone()
            self.close()

            # Для шаблонных проектов менеджеры получают "Оклад" вместо "Полная оплата"
            if contract and contract['project_type'] == 'Шаблонный':
                if role in ['Старший менеджер проектов', 'Менеджер']:
                    payment_type = 'Оклад'
                    print(f"[INFO] Для шаблонного проекта: {role} получает тип выплаты 'Оклад'")
            # ==============================================================================

            # Рассчитываем сумму
            # ИСПРАВЛЕНИЕ: Передаем supervision_card_id для правильного расчета тарифов надзора
            calculated_amount = self.calculate_payment_amount(
                contract_id, employee_id, role, stage_name, supervision_card_id
            )

            # ИСПРАВЛЕНИЕ: Создаем оплату даже если тариф = 0
            # (раньше возвращали None при calculated_amount == 0)
            if calculated_amount == 0:
                print(f"[WARN] Тариф для {role} (стадия: {stage_name}) = 0 или не установлен")
                print(f"   Создаем оплату с нулевой суммой")

            # ========== ИСПРАВЛЕНИЕ: УСТАНАВЛИВАЕМ ПУСТУЮ СТРОКУ ВМЕСТО NULL ==========
            if not report_month:
                report_month = ''  # ← ПУСТАЯ СТРОКА вместо None
            # ===========================================================================

            conn = self.connect()
            cursor = conn.cursor()

            # ИСПРАВЛЕНИЕ: Добавляем crm_card_id и supervision_card_id
            cursor.execute('''
            INSERT INTO payments
            (contract_id, crm_card_id, supervision_card_id, employee_id, role, stage_name,
             calculated_amount, final_amount, payment_type, report_month)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (contract_id, crm_card_id, supervision_card_id, employee_id, role, stage_name,
                  calculated_amount, calculated_amount, payment_type, report_month))

            conn.commit()
            payment_id = cursor.lastrowid
            self.close()

            month_display = report_month if report_month else "не указан"
            card_type = "CRM" if crm_card_id else ("Надзор" if supervision_card_id else "Общая")
            print(f"[OK] Создана выплата ID={payment_id} ({card_type}): {role} - {calculated_amount:.2f} ₽ (месяц: {month_display})")
            return payment_id
            
        except Exception as e:
            print(f"[ERROR] Ошибка создания выплаты: {e}")
            import traceback
            traceback.print_exc()
            return None
        
    def get_payments_for_contract(self, contract_id):
        """Получение всех выплат по договору (используется для активных проектов)"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # ИСПРАВЛЕНИЕ: Добавляем статус контракта для отображения отчетного месяца
            cursor.execute('''
            SELECT p.*, e.full_name as employee_name, c.status as contract_status
            FROM payments p
            JOIN employees e ON p.employee_id = e.id
            JOIN contracts c ON p.contract_id = c.id
            WHERE p.contract_id = ?
            ORDER BY p.role, p.stage_name
            ''', (contract_id,))

            payments = [dict(row) for row in cursor.fetchall()]
            self.close()

            return payments

        except Exception as e:
            print(f"[ERROR] Ошибка получения выплат: {e}")
            return []

    def get_payments_for_crm(self, contract_id):
        """Получение выплат для основной CRM (НЕ относящиеся к надзору)"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # ИСПРАВЛЕНИЕ: Показываем все оплаты, которые НЕ относятся к надзору
            # (т.е. supervision_card_id IS NULL или равен 0)
            cursor.execute('''
            SELECT p.*, e.full_name as employee_name, c.status as contract_status
            FROM payments p
            JOIN employees e ON p.employee_id = e.id
            JOIN contracts c ON p.contract_id = c.id
            WHERE p.contract_id = ?
              AND (p.supervision_card_id IS NULL OR p.supervision_card_id = 0)
            ORDER BY p.role, p.stage_name
            ''', (contract_id,))

            payments = [dict(row) for row in cursor.fetchall()]
            self.close()

            return payments

        except Exception as e:
            print(f"[ERROR] Ошибка получения выплат для CRM: {e}")
            return []

    def get_payments_for_supervision(self, contract_id):
        """Получение выплат для CRM надзора (только с supervision_card_id)"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT p.*, e.full_name as employee_name, c.status as contract_status
            FROM payments p
            JOIN employees e ON p.employee_id = e.id
            JOIN contracts c ON p.contract_id = c.id
            WHERE p.contract_id = ? AND p.supervision_card_id IS NOT NULL
            ORDER BY p.role, p.stage_name
            ''', (contract_id,))

            payments = [dict(row) for row in cursor.fetchall()]
            self.close()

            return payments

        except Exception as e:
            print(f"[ERROR] Ошибка получения выплат: {e}")
            return []

    def update_payment_manual(self, payment_id, manual_amount):
        """Обновление выплаты с ручным вводом"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE payments
            SET manual_amount = ?,
                final_amount = ?,
                is_manual = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''', (manual_amount, manual_amount, payment_id))
            
            conn.commit()
            self.close()
            
            print(f"[OK] Выплата ID={payment_id} обновлена вручную: {manual_amount:.2f} ₽")
            
        except Exception as e:
            print(f"[ERROR] Ошибка обновления выплаты: {e}")

    def mark_payment_as_paid(self, payment_id, paid_by_id):
        """Отметка выплаты как оплаченной"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE payments
            SET is_paid = 1,
                paid_date = CURRENT_TIMESTAMP,
                paid_by = ?
            WHERE id = ?
            ''', (paid_by_id, payment_id))
            
            conn.commit()
            self.close()
            
            print(f"[OK] Выплата ID={payment_id} отмечена как оплаченная")

        except Exception as e:
            print(f"[ERROR] Ошибка отметки оплаты: {e}")

    # ========== МЕТОДЫ ДЛЯ РАБОТЫ С АГЕНТАМИ ==========

    def get_all_agents(self):
        """Получение всех агентов с цветами"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, color FROM agents ORDER BY name')
            agents = cursor.fetchall()
            self.close()
            return agents
        except Exception as e:
            print(f"[ERROR] Ошибка получения агентов: {e}")
            return []

    def add_agent(self, name, color):
        """Добавление нового агента"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO agents (name, color) VALUES (?, ?)', (name, color))
            conn.commit()
            self.close()
            print(f"[OK] Агент '{name}' добавлен с цветом {color}")
            return True
        except Exception as e:
            print(f"[ERROR] Ошибка добавления агента: {e}")
            return False

    def update_agent_color(self, name, color):
        """Обновление цвета агента"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('UPDATE agents SET color = ? WHERE name = ?', (color, name))
            conn.commit()
            self.close()
            print(f"[OK] Цвет агента '{name}' обновлен на {color}")
            return True
        except Exception as e:
            print(f"[ERROR] Ошибка обновления цвета агента: {e}")
            return False

    def get_agent_color(self, name):
        """Получение цвета агента по имени"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT color FROM agents WHERE name = ?', (name,))
            result = cursor.fetchone()
            self.close()
            return result['color'] if result else None
        except Exception as e:
            print(f"[ERROR] Ошибка получения цвета агента: {e}")
            return None

    # ========== МЕТОДЫ ДЛЯ РАБОТЫ С ФАЙЛАМИ СТАДИЙ ПРОЕКТА ==========

    def add_project_file(self, contract_id, stage, file_type, public_link, yandex_path, file_name, preview_cache_path=None, variation=1):
        """Добавление файла стадии проекта

        Args:
            contract_id: ID договора
            stage: стадия ('measurement', 'stage1', 'stage2_concept', 'stage2_3d', 'stage3')
            file_type: тип файла ('image', 'pdf', 'excel')
            public_link: публичная ссылка на файл
            yandex_path: путь к файлу на Яндекс.Диске
            file_name: имя файла
            preview_cache_path: путь к кэшированному превью (опционально)
            variation: номер вариации (по умолчанию 1)

        Returns:
            ID созданной записи или None при ошибке
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Получаем максимальный порядковый номер для данной стадии и вариации
            cursor.execute('''
                SELECT COALESCE(MAX(file_order), -1) + 1
                FROM project_files
                WHERE contract_id = ? AND stage = ? AND variation = ?
            ''', (contract_id, stage, variation))
            next_order = cursor.fetchone()[0]

            # Добавляем файл
            cursor.execute('''
                INSERT INTO project_files
                (contract_id, stage, file_type, public_link, yandex_path, file_name, preview_cache_path, file_order, variation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (contract_id, stage, file_type, public_link, yandex_path, file_name, preview_cache_path, next_order, variation))

            conn.commit()
            file_id = cursor.lastrowid
            self.close()

            print(f"[OK] Файл '{file_name}' добавлен в БД (ID: {file_id}, variation: {variation})")
            return file_id

        except Exception as e:
            print(f"[ERROR] Ошибка добавления файла стадии: {e}")
            return None

    def get_project_files(self, contract_id, stage=None):
        """Получение файлов стадии проекта

        Args:
            contract_id: ID договора
            stage: стадия (опционально, если не указано - все файлы договора)

        Returns:
            Список словарей с данными файлов
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            if stage:
                cursor.execute('''
                    SELECT * FROM project_files
                    WHERE contract_id = ? AND stage = ?
                    ORDER BY file_order, upload_date
                ''', (contract_id, stage))
            else:
                cursor.execute('''
                    SELECT * FROM project_files
                    WHERE contract_id = ?
                    ORDER BY stage, file_order, upload_date
                ''', (contract_id,))

            files = [dict(row) for row in cursor.fetchall()]
            self.close()

            return files

        except Exception as e:
            print(f"[ERROR] Ошибка получения файлов стадии: {e}")
            return []

    def delete_project_file(self, file_id):
        """Удаление файла стадии проекта

        Args:
            file_id: ID файла

        Returns:
            Словарь с данными удаленного файла (yandex_path, preview_cache_path) или None
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Получаем информацию о файле перед удалением
            cursor.execute('SELECT yandex_path, preview_cache_path, file_name FROM project_files WHERE id = ?', (file_id,))
            result = cursor.fetchone()

            if result:
                # Удаляем файл из БД
                cursor.execute('DELETE FROM project_files WHERE id = ?', (file_id,))
                conn.commit()
                self.close()

                print(f"[OK] Файл '{result['file_name']}' удален из БД (ID: {file_id})")
                return dict(result)
            else:
                self.close()
                print(f"[WARN] Файл с ID {file_id} не найден в БД")
                return None

        except Exception as e:
            print(f"[ERROR] Ошибка удаления файла стадии: {e}")
            return None

    def update_project_file_order(self, file_id, new_order):
        """Обновление порядка файла в галерее

        Args:
            file_id: ID файла
            new_order: новый порядковый номер

        Returns:
            True при успехе, False при ошибке
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE project_files
                SET file_order = ?
                WHERE id = ?
            ''', (new_order, file_id))

            conn.commit()
            self.close()

            print(f"[OK] Порядок файла {file_id} обновлен: {new_order}")
            return True

        except Exception as e:
            print(f"[ERROR] Ошибка обновления порядка файла: {e}")
            return False

    # ========== МЕТОДЫ ДЛЯ РАБОТЫ С ШАБЛОНАМИ ПРОЕКТОВ ==========

    def add_project_template(self, contract_id, template_url):
        """Добавление ссылки на шаблон проекта

        Args:
            contract_id: ID договора
            template_url: URL ссылки на шаблон

        Returns:
            ID созданной записи или None при ошибке
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO project_templates (contract_id, template_url)
                VALUES (?, ?)
            ''', (contract_id, template_url))

            template_id = cursor.lastrowid
            conn.commit()
            self.close()

            print(f"[OK] Добавлена ссылка на шаблон проекта (ID: {template_id})")
            return template_id

        except Exception as e:
            print(f"[ERROR] Ошибка добавления шаблона проекта: {e}")
            return None

    def get_project_templates(self, contract_id):
        """Получение всех ссылок на шаблоны для договора

        Args:
            contract_id: ID договора

        Returns:
            Список словарей с данными о шаблонах
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, template_url, created_at
                FROM project_templates
                WHERE contract_id = ?
                ORDER BY created_at ASC
            ''', (contract_id,))

            templates = cursor.fetchall()
            self.close()

            return [dict(t) for t in templates] if templates else []

        except Exception as e:
            print(f"[ERROR] Ошибка получения шаблонов проекта: {e}")
            return []

    def delete_project_template(self, template_id):
        """Удаление ссылки на шаблон проекта

        Args:
            template_id: ID шаблона для удаления

        Returns:
            True при успехе, False при ошибке
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute('DELETE FROM project_templates WHERE id = ?', (template_id,))

            conn.commit()
            self.close()

            print(f"[OK] Шаблон проекта удален (ID: {template_id})")
            return True

        except Exception as e:
            print(f"[ERROR] Ошибка удаления шаблона проекта: {e}")
            return False


