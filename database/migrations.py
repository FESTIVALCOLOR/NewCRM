# -*- coding: utf-8 -*-
"""Миграции БД — выделены из db_manager.py для уменьшения размера файла."""

import json
import os
from utils.password_utils import hash_password


def add_contract_status_fields(db_path):
    """Совместимость: миграция статусов договоров (legacy).
    Вызывается из run_migrations() как свободная функция.
    """
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(contracts)")
        columns = [c[1] for c in cursor.fetchall()]
        if 'status' not in columns:
            cursor.execute("ALTER TABLE contracts ADD COLUMN status TEXT DEFAULT 'Новый заказ'")
        if 'termination_reason' not in columns:
            cursor.execute("ALTER TABLE contracts ADD COLUMN termination_reason TEXT")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] add_contract_status_fields: {e}")


class DatabaseMigrations:
    """Mixin-класс с миграциями. Наследуется DatabaseManager."""

    def run_migrations(self):
        """Запуск миграций базы данных"""
        try:
            # Проверяем, нужна ли миграция
            conn = self.connect()
            cursor = conn.cursor()

            # Миграция №1: status и termination_reason
            cursor.execute("PRAGMA table_info(contracts)")
            columns = [column[1] for column in cursor.fetchall()]
            self.close()

            if 'status' not in columns or 'termination_reason' not in columns:
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

            # ========== МИГРАЦИЯ: payment tracking fields ==========
            self.add_payment_tracking_fields()
            # ======================================================

            # ========== МИГРАЦИЯ: signed acts fields ==========
            self.add_signed_acts_fields()
            # =================================================

            # ========== МИГРАЦИЯ: user_permissions table ==========
            self.create_user_permissions_table()
            # =====================================================

            # ========== МИГРАЦИЯ: role_default_permissions table ==========
            self.create_role_default_permissions_table()
            # ==============================================================

            # ========== МИГРАЦИЯ: norm_days_templates table ==========
            self.create_norm_days_templates_table()
            # ========================================================

            # ========== МИГРАЦИЯ: agent_type в norm_days_templates ==========
            self.add_agent_type_to_norm_days_templates()
            # ==============================================================

            # ========== МИГРАЦИЯ: custom_norm_days в project_timeline_entries ==========
            self.add_custom_norm_days_column()
            # =====================================================================

            # ========== МИГРАЦИЯ: multiuser поля для employees ==========
            self.add_employee_multiuser_fields()
            # ===========================================================

            # ========== МИГРАЦИЯ: поле status для agents ==========
            self.add_agents_status_field()
            # ======================================================

            # ========== МИГРАЦИЯ: таблица городов ==========
            self.migrate_add_cities_table()
            # ===============================================

        except Exception as e:
            print(f"[WARN] Предупреждение при миграции: {e}")

    def add_payment_tracking_fields(self):
        """Миграция: добавление полей отслеживания платежей (даты оплат + чеки)"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(contracts)")
            columns = [column[1] for column in cursor.fetchall()]

            new_cols = {
                # Даты оплат
                'advance_payment_paid_date': 'TEXT',
                'additional_payment_paid_date': 'TEXT',
                'third_payment_paid_date': 'TEXT',
                # Чек аванса
                'advance_receipt_link': 'TEXT',
                'advance_receipt_yandex_path': 'TEXT',
                'advance_receipt_file_name': 'TEXT',
                # Чек 2-го платежа
                'additional_receipt_link': 'TEXT',
                'additional_receipt_yandex_path': 'TEXT',
                'additional_receipt_file_name': 'TEXT',
                # Чек 3-го платежа
                'third_receipt_link': 'TEXT',
                'third_receipt_yandex_path': 'TEXT',
                'third_receipt_file_name': 'TEXT',
            }

            added = []
            for col_name, col_type in new_cols.items():
                if col_name not in columns:
                    cursor.execute(f"ALTER TABLE contracts ADD COLUMN {col_name} {col_type}")
                    added.append(col_name)

            if added:
                conn.commit()
                print(f"[OK] Миграция payment_tracking: добавлено {len(added)} колонок: {', '.join(added)}")
            else:
                print("[OK] Поля payment_tracking уже существуют")

            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка миграции payment_tracking: {e}")

    def add_signed_acts_fields(self):
        """Миграция: добавление полей для подписанных актов"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(contracts)")
            columns = [column[1] for column in cursor.fetchall()]

            new_cols = {
                'act_planning_signed_link': 'TEXT',
                'act_planning_signed_yandex_path': 'TEXT',
                'act_planning_signed_file_name': 'TEXT',
                'act_concept_signed_link': 'TEXT',
                'act_concept_signed_yandex_path': 'TEXT',
                'act_concept_signed_file_name': 'TEXT',
                'info_letter_signed_link': 'TEXT',
                'info_letter_signed_yandex_path': 'TEXT',
                'info_letter_signed_file_name': 'TEXT',
                'act_final_signed_link': 'TEXT',
                'act_final_signed_yandex_path': 'TEXT',
                'act_final_signed_file_name': 'TEXT',
            }

            added = []
            for col_name, col_type in new_cols.items():
                if col_name not in columns:
                    cursor.execute(f"ALTER TABLE contracts ADD COLUMN {col_name} {col_type}")
                    added.append(col_name)

            if added:
                conn.commit()
                print(f"[OK] Миграция signed_acts: добавлено {len(added)} колонок: {', '.join(added)}")
            else:
                print("[OK] Поля signed_acts уже существуют")

            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка миграции signed_acts: {e}")

    def create_user_permissions_table(self):
        """Миграция: создание таблицы user_permissions для granular permissions"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                permission_name TEXT NOT NULL,
                granted_by INTEGER,
                granted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id),
                UNIQUE(employee_id, permission_name)
            )
            ''')

            conn.commit()
            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка миграции user_permissions: {e}")

    def create_role_default_permissions_table(self):
        """Миграция: создание таблицы role_default_permissions для матрицы прав по ролям"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS role_default_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                permission_name TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by INTEGER,
                UNIQUE(role, permission_name)
            )
            ''')

            conn.commit()
            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка миграции role_default_permissions: {e}")

    def create_norm_days_templates_table(self):
        """Миграция: создание таблицы norm_days_templates для шаблонов нормо-дней"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute('''CREATE TABLE IF NOT EXISTS norm_days_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_type TEXT NOT NULL,
                project_subtype TEXT NOT NULL,
                stage_code TEXT NOT NULL,
                stage_name TEXT NOT NULL,
                stage_group TEXT NOT NULL,
                substage_group TEXT,
                base_norm_days REAL NOT NULL,
                k_multiplier REAL DEFAULT 0,
                executor_role TEXT NOT NULL,
                is_in_contract_scope BOOLEAN DEFAULT 1,
                sort_order INTEGER NOT NULL,
                agent_type TEXT DEFAULT 'Все агенты',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by INTEGER,
                UNIQUE(project_type, project_subtype, stage_code, agent_type)
            )''')

            conn.commit()
            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка миграции norm_days_templates: {e}")

    def add_agent_type_to_norm_days_templates(self):
        """Миграция: добавление колонки agent_type + обновление UNIQUE-constraint"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(norm_days_templates)")
            columns = [col[1] for col in cursor.fetchall()]

            if 'agent_type' not in columns:
                # 1. Добавляем колонку
                cursor.execute(
                    "ALTER TABLE norm_days_templates ADD COLUMN agent_type TEXT DEFAULT 'Все агенты'"
                )
                # 2. Обновляем NULL → 'Все агенты'
                cursor.execute(
                    "UPDATE norm_days_templates SET agent_type = 'Все агенты' WHERE agent_type IS NULL"
                )
                # 3. Пересоздаём таблицу для обновления UNIQUE-constraint
                # SQLite не поддерживает ALTER CONSTRAINT, поэтому нужен полный цикл
                cursor.execute('''CREATE TABLE IF NOT EXISTS norm_days_templates_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_type TEXT NOT NULL,
                    project_subtype TEXT NOT NULL,
                    stage_code TEXT NOT NULL,
                    stage_name TEXT NOT NULL,
                    stage_group TEXT NOT NULL,
                    substage_group TEXT,
                    base_norm_days REAL NOT NULL,
                    k_multiplier REAL DEFAULT 0,
                    executor_role TEXT NOT NULL,
                    is_in_contract_scope BOOLEAN DEFAULT 1,
                    sort_order INTEGER NOT NULL,
                    agent_type TEXT DEFAULT 'Все агенты',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_by INTEGER,
                    UNIQUE(project_type, project_subtype, stage_code, agent_type)
                )''')
                cursor.execute('''INSERT INTO norm_days_templates_new
                    (id, project_type, project_subtype, stage_code, stage_name, stage_group,
                     substage_group, base_norm_days, k_multiplier, executor_role,
                     is_in_contract_scope, sort_order, agent_type, updated_at, updated_by)
                    SELECT id, project_type, project_subtype, stage_code, stage_name, stage_group,
                     substage_group, base_norm_days, k_multiplier, executor_role,
                     is_in_contract_scope, sort_order, agent_type, updated_at, updated_by
                    FROM norm_days_templates''')
                cursor.execute("DROP TABLE norm_days_templates")
                cursor.execute("ALTER TABLE norm_days_templates_new RENAME TO norm_days_templates")
                conn.commit()
                print("[OK] Миграция: добавлена колонка agent_type + обновлен UNIQUE в norm_days_templates")

            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка миграции agent_type в norm_days_templates: {e}")

    def add_custom_norm_days_column(self):
        """Миграция: добавление колонки custom_norm_days в project_timeline_entries"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(project_timeline_entries)")
            columns = [col[1] for col in cursor.fetchall()]

            if 'custom_norm_days' not in columns:
                cursor.execute(
                    "ALTER TABLE project_timeline_entries ADD COLUMN custom_norm_days INTEGER"
                )
                conn.commit()
                print("[OK] Миграция: добавлена колонка custom_norm_days в project_timeline_entries")

            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка миграции custom_norm_days: {e}")

    def add_employee_multiuser_fields(self):
        """Миграция: добавление multiuser полей в таблицу employees"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(employees)")
            columns = [col[1] for col in cursor.fetchall()]

            new_cols = {
                'is_online': 'INTEGER DEFAULT 0',
                'last_login': 'TIMESTAMP',
                'last_activity': 'TIMESTAMP',
                'current_session_token': 'TEXT',
                'agent_color': 'TEXT',
            }

            added = []
            for col_name, col_def in new_cols.items():
                if col_name not in columns:
                    cursor.execute(f"ALTER TABLE employees ADD COLUMN {col_name} {col_def}")
                    added.append(col_name)

            if added:
                conn.commit()
                print(f"[OK] Миграция employee_multiuser: добавлено {len(added)} колонок: {', '.join(added)}")
            else:
                print("[OK] Поля employee_multiuser уже существуют")

            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка миграции employee_multiuser: {e}")

    def add_agents_status_field(self):
        """Миграция: добавление поля status в таблицу agents"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(agents)")
            columns = [col[1] for col in cursor.fetchall()]

            if 'status' not in columns:
                cursor.execute(
                    "ALTER TABLE agents ADD COLUMN status TEXT DEFAULT 'активный'"
                )
                conn.commit()
                print("[OK] Миграция: добавлена колонка status в agents")
            else:
                print("[OK] Поле status в agents уже существует")

            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка миграции agents status: {e}")

    def migrate_add_cities_table(self):
        """Добавить таблицу городов"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    status TEXT DEFAULT 'активный',
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            # Seed дефолтные города
            for city_name in ['СПБ', 'МСК', 'ВН']:
                cursor.execute(
                    "INSERT OR IGNORE INTO cities (name) VALUES (?)",
                    (city_name,)
                )
            conn.commit()
            self.close()
            print("[OK] Таблица cities создана (с seed-данными)")
        except Exception as e:
            print(f"[ERROR] Ошибка миграции cities: {e}")

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
            birth_date TEXT,
            address TEXT,
            secondary_position TEXT,
            is_online INTEGER DEFAULT 0,
            last_login TIMESTAMP,
            last_activity TIMESTAMP,
            current_session_token TEXT,
            agent_color TEXT,
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
            project_subtype TEXT,
            floors INTEGER DEFAULT 1,
            agent_type TEXT,
            city TEXT,
            contract_number TEXT UNIQUE NOT NULL,
            contract_date DATE,
            address TEXT,
            area REAL,
            total_amount REAL,
            advance_payment REAL,
            additional_payment REAL,
            third_payment REAL,
            contract_period INTEGER,
            comments TEXT,
            contract_file_link TEXT,
            tech_task_link TEXT,
            status TEXT DEFAULT 'Новый заказ',
            termination_reason TEXT,
            status_changed_date DATE,
            yandex_folder_path TEXT,
            tech_task_file_name TEXT,
            tech_task_yandex_path TEXT,
            measurement_image_link TEXT,
            measurement_file_name TEXT,
            measurement_yandex_path TEXT,
            measurement_date DATE,
            contract_file_name TEXT,
            contract_file_yandex_path TEXT,
            template_contract_file_link TEXT,
            template_contract_file_name TEXT,
            template_contract_file_yandex_path TEXT,
            references_yandex_path TEXT,
            photo_documentation_yandex_path TEXT,
            act_planning_link TEXT,
            act_planning_yandex_path TEXT,
            act_planning_file_name TEXT,
            act_concept_link TEXT,
            act_concept_yandex_path TEXT,
            act_concept_file_name TEXT,
            info_letter_link TEXT,
            info_letter_yandex_path TEXT,
            info_letter_file_name TEXT,
            act_final_link TEXT,
            act_final_yandex_path TEXT,
            act_final_file_name TEXT,
            act_planning_signed_link TEXT,
            act_planning_signed_yandex_path TEXT,
            act_planning_signed_file_name TEXT,
            act_concept_signed_link TEXT,
            act_concept_signed_yandex_path TEXT,
            act_concept_signed_file_name TEXT,
            info_letter_signed_link TEXT,
            info_letter_signed_yandex_path TEXT,
            info_letter_signed_file_name TEXT,
            act_final_signed_link TEXT,
            act_final_signed_yandex_path TEXT,
            act_final_signed_file_name TEXT,
            advance_payment_paid_date TEXT,
            additional_payment_paid_date TEXT,
            third_payment_paid_date TEXT,
            advance_receipt_link TEXT,
            advance_receipt_yandex_path TEXT,
            advance_receipt_file_name TEXT,
            additional_receipt_link TEXT,
            additional_receipt_yandex_path TEXT,
            additional_receipt_file_name TEXT,
            third_receipt_link TEXT,
            third_receipt_yandex_path TEXT,
            third_receipt_file_name TEXT,
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
            approval_deadline DATE,
            approval_stages TEXT,
            project_data_link TEXT,
            tech_task_file TEXT,
            tech_task_date DATE,
            survey_date DATE,
            previous_column TEXT,
            paused_at TIMESTAMP,
            total_pause_days INTEGER DEFAULT 0,
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
            submitted_date TIMESTAMP,
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
            payment_type TEXT,
            stage_name TEXT,
            amount REAL,
            advance_payment REAL,
            salary_type TEXT,
            period TEXT,
            status TEXT,
            payment_date TIMESTAMP,
            report_month TEXT,
            comments TEXT,
            project_type TEXT,
            payment_status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
        # Пароль из переменной окружения или 'admin' как fallback
        default_admin_password = os.environ.get('ADMIN_DEFAULT_PASSWORD', 'admin')
        default_password_hash = hash_password(default_admin_password)
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
            print("Агенты по умолчанию добавлены с цветами")

        conn.commit()
        self.close()
        print("База данных успешно инициализирована!")

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
                    start_date TEXT,
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
                    'studio_director_id': 'INTEGER',
                    'dan_completed': 'BOOLEAN DEFAULT 0',
                    'is_paused': 'BOOLEAN DEFAULT 0',
                    'pause_reason': 'TEXT',
                    'paused_at': 'TIMESTAMP',
                    'start_date': 'TEXT',
                    'previous_column': 'TEXT',
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
                'Стадия 7: Лепной декор', 'Стадия 8: Освещение',
                'Стадия 9: Бытовая техника', 'Стадия 10: Закупка заказной мебели',
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

            if 'previous_column' not in columns:
                print("[>] Выполняется миграция: добавление previous_column в crm_cards...")
                cursor.execute("ALTER TABLE crm_cards ADD COLUMN previous_column TEXT")
                conn.commit()
                print("[OK] Поле previous_column добавлено в crm_cards")

            # K1: Поля для паузы дедлайна CRM
            if 'paused_at' not in columns:
                print("[>] Выполняется миграция: добавление paused_at в crm_cards...")
                cursor.execute("ALTER TABLE crm_cards ADD COLUMN paused_at TIMESTAMP")
                conn.commit()
                print("[OK] Поле paused_at добавлено в crm_cards")

            if 'total_pause_days' not in columns:
                print("[>] Выполняется миграция: добавление total_pause_days в crm_cards...")
                cursor.execute("ALTER TABLE crm_cards ADD COLUMN total_pause_days INTEGER DEFAULT 0")
                conn.commit()
                print("[OK] Поле total_pause_days добавлено в crm_cards")

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
                        variation INTEGER DEFAULT 1,
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

            # Миграция: добавление колонки variation
            cursor.execute("PRAGMA table_info(project_files)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'variation' not in columns:
                cursor.execute('ALTER TABLE project_files ADD COLUMN variation INTEGER DEFAULT 1')
                conn.commit()
                print("[OK] Добавлена колонка variation в project_files")

            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка создания таблицы project_files: {e}")

    def add_contract_file_columns(self):
        """Миграция: добавление колонок для файлов договоров (yandex_path, file_name и т.д.)"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(contracts)")
            columns = [column[1] for column in cursor.fetchall()]

            new_columns = {
                'yandex_folder_path': 'TEXT',
                'tech_task_file_name': 'TEXT',
                'tech_task_yandex_path': 'TEXT',
                'measurement_image_link': 'TEXT',
                'measurement_file_name': 'TEXT',
                'measurement_yandex_path': 'TEXT',
                'measurement_date': 'DATE',
                'contract_file_name': 'TEXT',
                'contract_file_yandex_path': 'TEXT',
                'template_contract_file_link': 'TEXT',
                'template_contract_file_name': 'TEXT',
                'template_contract_file_yandex_path': 'TEXT',
                'references_yandex_path': 'TEXT',
                'photo_documentation_yandex_path': 'TEXT',
                # Акты и информационное письмо
                'act_planning_link': 'TEXT',
                'act_planning_yandex_path': 'TEXT',
                'act_planning_file_name': 'TEXT',
                'act_concept_link': 'TEXT',
                'act_concept_yandex_path': 'TEXT',
                'act_concept_file_name': 'TEXT',
                'info_letter_link': 'TEXT',
                'info_letter_yandex_path': 'TEXT',
                'info_letter_file_name': 'TEXT',
                'act_final_link': 'TEXT',
                'act_final_yandex_path': 'TEXT',
                'act_final_file_name': 'TEXT',
                # Подписанные акты
                'act_planning_signed_link': 'TEXT',
                'act_planning_signed_yandex_path': 'TEXT',
                'act_planning_signed_file_name': 'TEXT',
                'act_concept_signed_link': 'TEXT',
                'act_concept_signed_yandex_path': 'TEXT',
                'act_concept_signed_file_name': 'TEXT',
                'info_letter_signed_link': 'TEXT',
                'info_letter_signed_yandex_path': 'TEXT',
                'info_letter_signed_file_name': 'TEXT',
                'act_final_signed_link': 'TEXT',
                'act_final_signed_yandex_path': 'TEXT',
                'act_final_signed_file_name': 'TEXT',
                # Отслеживание платежей
                'advance_payment_paid_date': 'TEXT',
                'additional_payment_paid_date': 'TEXT',
                'third_payment_paid_date': 'TEXT',
                'advance_receipt_link': 'TEXT',
                'advance_receipt_yandex_path': 'TEXT',
                'advance_receipt_file_name': 'TEXT',
                'additional_receipt_link': 'TEXT',
                'additional_receipt_yandex_path': 'TEXT',
                'additional_receipt_file_name': 'TEXT',
                'third_receipt_link': 'TEXT',
                'third_receipt_yandex_path': 'TEXT',
                'third_receipt_file_name': 'TEXT',
            }

            added = []
            for col_name, col_type in new_columns.items():
                if col_name not in columns:
                    cursor.execute(f"ALTER TABLE contracts ADD COLUMN {col_name} {col_type}")
                    added.append(col_name)

            if added:
                conn.commit()
                print(f"[OK] Добавлены колонки в contracts: {', '.join(added)}")
            else:
                print("[OK] Все колонки файлов в contracts уже существуют")

            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка миграции contract file columns: {e}")

    def create_project_templates_table(self):
        """Миграция: создание таблицы project_templates для ссылок на шаблоны проектов"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='project_templates'
            """)

            if not cursor.fetchone():
                print("[>] Создание таблицы project_templates...")
                cursor.execute('''
                    CREATE TABLE project_templates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        contract_id INTEGER NOT NULL,
                        template_url TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE CASCADE
                    )
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_project_templates_contract
                    ON project_templates(contract_id)
                ''')
                conn.commit()
                print("[OK] Таблица project_templates создана")
            else:
                print("[OK] Таблица project_templates уже существует")

            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка создания таблицы project_templates: {e}")

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
                contract_id INTEGER,
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

    def add_stage_field_to_payments(self):
        """Миграция: добавление полей для синхронизации в payments"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Проверяем, какие поля уже есть
            cursor.execute("PRAGMA table_info(payments)")
            columns = [column[1] for column in cursor.fetchall()]

            # Список полей для добавления
            fields_to_add = {
                'stage': 'TEXT',
                'base_amount': 'REAL',
                'bonus_amount': 'REAL',
                'penalty_amount': 'REAL',
                'status': 'TEXT',
                'payment_date': 'TIMESTAMP'
            }

            for field_name, field_type in fields_to_add.items():
                if field_name not in columns:
                    print(f"[>] Выполняется миграция: добавление {field_name} в payments...")
                    cursor.execute(f"ALTER TABLE payments ADD COLUMN {field_name} {field_type}")
                    conn.commit()
                    print(f"[OK] Поле {field_name} добавлено")
                else:
                    print(f"[OK] Поле {field_name} уже существует")

            self.close()
        except Exception as e:
            print(f"[ERROR] Ошибка миграции полей payments: {e}")
            import traceback
            traceback.print_exc()

    def create_performance_indexes(self):
        """Миграция: создание индексов для ускорения запросов"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_contracts_client_id ON contracts(client_id)",
                "CREATE INDEX IF NOT EXISTS idx_crm_cards_contract_id ON crm_cards(contract_id)",
                "CREATE INDEX IF NOT EXISTS idx_crm_cards_column_name ON crm_cards(column_name)",
                "CREATE INDEX IF NOT EXISTS idx_stage_executors_crm_card_id ON stage_executors(crm_card_id)",
                "CREATE INDEX IF NOT EXISTS idx_stage_executors_executor_id ON stage_executors(executor_id)",
                "CREATE INDEX IF NOT EXISTS idx_stage_executors_stage_name ON stage_executors(stage_name)",
                "CREATE INDEX IF NOT EXISTS idx_payments_contract_id ON payments(contract_id)",
                "CREATE INDEX IF NOT EXISTS idx_payments_employee_id ON payments(employee_id)",
                "CREATE INDEX IF NOT EXISTS idx_payments_crm_card_id ON payments(crm_card_id)",
                "CREATE INDEX IF NOT EXISTS idx_payments_supervision_card_id ON payments(supervision_card_id)",
                "CREATE INDEX IF NOT EXISTS idx_supervision_cards_contract_id ON supervision_cards(contract_id)",
                "CREATE INDEX IF NOT EXISTS idx_project_files_contract_id ON project_files(contract_id)",
                "CREATE INDEX IF NOT EXISTS idx_salaries_employee_id ON salaries(employee_id)",
            ]
            for idx_sql in indexes:
                try:
                    cursor.execute(idx_sql)
                except Exception:
                    pass  # Table may not exist yet
            conn.commit()
            self.close()
        except Exception as e:
            print(f"[WARN] Index creation: {e}")

    def add_missing_fields_rates_payments_salaries(self):
        """Миграция: добавление недостающих полей в rates, payments, salaries для совместимости с сервером"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # rates: price, executor_rate, manager_rate
            cursor.execute("PRAGMA table_info(rates)")
            rate_cols = [col[1] for col in cursor.fetchall()]
            for field, ftype in [('price', 'REAL'), ('executor_rate', 'REAL'), ('manager_rate', 'REAL')]:
                if field not in rate_cols:
                    cursor.execute(f"ALTER TABLE rates ADD COLUMN {field} {ftype}")

            # payments: payment_status
            cursor.execute("PRAGMA table_info(payments)")
            pay_cols = [col[1] for col in cursor.fetchall()]
            if 'payment_status' not in pay_cols:
                cursor.execute("ALTER TABLE payments ADD COLUMN payment_status TEXT")

            # salaries: salary_type, period, status, payment_date, updated_at, project_type, payment_status
            cursor.execute("PRAGMA table_info(salaries)")
            sal_cols = [col[1] for col in cursor.fetchall()]
            for field, ftype in [
                ('salary_type', 'TEXT'),
                ('period', 'TEXT'),
                ('status', 'TEXT'),
                ('payment_date', 'TIMESTAMP'),
                ('updated_at', 'TIMESTAMP'),
                ('project_type', 'TEXT'),
                ('payment_status', 'TEXT'),
            ]:
                if field not in sal_cols:
                    cursor.execute(f"ALTER TABLE salaries ADD COLUMN {field} {ftype}")

            conn.commit()
            self.close()
        except Exception as e:
            print(f"[WARN] Миграция rates/payments/salaries: {e}")

    def fix_payments_contract_id_nullable(self):
        """Миграция: снять NOT NULL с contract_id в payments.
        Оклады (salary_type) не привязаны к договорам — contract_id = NULL."""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            # Проверяем, есть ли NOT NULL на contract_id
            cursor.execute("PRAGMA table_info(payments)")
            cols = cursor.fetchall()
            contract_col = [c for c in cols if c[1] == 'contract_id']
            if not contract_col:
                self.close()
                return
            # c[3] = notnull flag: 1 = NOT NULL, 0 = nullable
            if contract_col[0][3] == 0:
                # Уже nullable — ничего делать не нужно
                self.close()
                return
            # Пересоздаём таблицу без NOT NULL на contract_id
            # Шаг 1: получаем все колонки
            col_names = [c[1] for c in cols]
            cols_str = ', '.join(col_names)
            # Шаг 2: rename → temp
            cursor.execute("ALTER TABLE payments RENAME TO payments_old")
            # Шаг 3: создаём новую таблицу (contract_id без NOT NULL)
            cursor.execute('''
            CREATE TABLE payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_id INTEGER,
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
                payment_status TEXT,
                reassigned BOOLEAN DEFAULT 0,
                old_employee_id INTEGER,
                stage TEXT,
                base_amount REAL,
                bonus_amount REAL,
                penalty_amount REAL,
                status TEXT,
                payment_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contract_id) REFERENCES contracts(id),
                FOREIGN KEY (employee_id) REFERENCES employees(id)
            )
            ''')
            # Шаг 4: копируем данные (только колонки которые есть в обоих таблицах)
            new_cols = [
                'id', 'contract_id', 'crm_card_id', 'supervision_card_id',
                'employee_id', 'role', 'stage_name',
                'calculated_amount', 'manual_amount', 'final_amount',
                'is_manual', 'payment_type', 'report_month',
                'is_paid', 'paid_date', 'paid_by',
                'payment_status', 'reassigned', 'old_employee_id',
                'stage', 'base_amount', 'bonus_amount', 'penalty_amount',
                'status', 'payment_date', 'created_at', 'updated_at'
            ]
            common_cols = [c for c in new_cols if c in col_names]
            common_str = ', '.join(common_cols)
            cursor.execute(f"INSERT INTO payments ({common_str}) SELECT {common_str} FROM payments_old")
            # Шаг 5: удаляем старую
            cursor.execute("DROP TABLE payments_old")
            conn.commit()
            print("[OK] payments.contract_id теперь nullable (для окладов)")
            self.close()
        except Exception as e:
            print(f"[WARN] fix_payments_contract_id_nullable: {e}")

    def add_project_subtype_to_contracts(self):
        """Миграция: поле project_subtype в contracts"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(contracts)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'project_subtype' not in columns:
                cursor.execute("ALTER TABLE contracts ADD COLUMN project_subtype TEXT")
                conn.commit()
                print("[OK] Поле project_subtype добавлено")
            self.close()
        except Exception as e:
            print(f"[MIGRATION] Ошибка добавления project_subtype: {e}")

    def add_floors_to_contracts(self):
        """Миграция: поле floors в contracts"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(contracts)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'floors' not in columns:
                cursor.execute("ALTER TABLE contracts ADD COLUMN floors INTEGER DEFAULT 1")
                conn.commit()
                print("[OK] Поле floors добавлено")
            self.close()
        except Exception as e:
            print(f"[MIGRATION] Ошибка добавления floors: {e}")

    def create_stage_workflow_state_table(self):
        """Миграция: таблица stage_workflow_state"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stage_workflow_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    crm_card_id INTEGER NOT NULL REFERENCES crm_cards(id),
                    stage_name TEXT NOT NULL,
                    current_substep_code TEXT,
                    status TEXT DEFAULT 'in_progress',
                    revision_count INTEGER DEFAULT 0,
                    revision_file_path TEXT,
                    client_approval_started_at TEXT,
                    client_approval_deadline_paused INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            ''')
            conn.commit()
            self.close()
        except Exception as e:
            print(f"[MIGRATION] Ошибка создания stage_workflow_state: {e}")

    def create_messenger_tables(self):
        """Миграция: таблицы системы мессенджер-чатов"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Таблица чатов проектов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messenger_chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_id INTEGER REFERENCES contracts(id),
                    crm_card_id INTEGER REFERENCES crm_cards(id),
                    supervision_card_id INTEGER,
                    messenger_type TEXT NOT NULL DEFAULT 'telegram',
                    telegram_chat_id INTEGER,
                    chat_title TEXT,
                    invite_link TEXT,
                    avatar_type TEXT,
                    creation_method TEXT NOT NULL DEFAULT 'manual',
                    created_by INTEGER REFERENCES employees(id),
                    created_at TEXT DEFAULT (datetime('now')),
                    is_active INTEGER DEFAULT 1
                )
            ''')

            # Таблица участников чата
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messenger_chat_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    messenger_chat_id INTEGER NOT NULL REFERENCES messenger_chats(id) ON DELETE CASCADE,
                    member_type TEXT NOT NULL,
                    member_id INTEGER NOT NULL,
                    role_in_project TEXT,
                    is_mandatory INTEGER DEFAULT 0,
                    phone TEXT,
                    email TEXT,
                    telegram_user_id INTEGER,
                    invite_status TEXT DEFAULT 'pending',
                    invited_at TEXT,
                    joined_at TEXT
                )
            ''')

            # Таблица скриптов сообщений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messenger_scripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    script_type TEXT NOT NULL,
                    project_type TEXT,
                    stage_name TEXT,
                    message_template TEXT NOT NULL,
                    use_auto_deadline INTEGER DEFAULT 1,
                    is_enabled INTEGER DEFAULT 1,
                    sort_order INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            ''')

            # Таблица настроек мессенджера
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messenger_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    updated_at TEXT DEFAULT (datetime('now')),
                    updated_by INTEGER REFERENCES employees(id)
                )
            ''')

            # Лог отправленных сообщений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messenger_message_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    messenger_chat_id INTEGER REFERENCES messenger_chats(id) ON DELETE CASCADE,
                    message_type TEXT,
                    message_text TEXT,
                    file_links TEXT,
                    sent_by INTEGER REFERENCES employees(id),
                    sent_at TEXT DEFAULT (datetime('now')),
                    telegram_message_id INTEGER,
                    delivery_status TEXT DEFAULT 'sent'
                )
            ''')

            # Индексы для быстрого поиска
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messenger_chats_crm_card ON messenger_chats(crm_card_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messenger_chats_contract ON messenger_chats(contract_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messenger_members_chat ON messenger_chat_members(messenger_chat_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messenger_log_chat ON messenger_message_log(messenger_chat_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messenger_scripts_type ON messenger_scripts(script_type, project_type)")

            conn.commit()
            print("[OK] Таблицы мессенджера созданы")
            self.close()
        except Exception as e:
            print(f"[MIGRATION] Ошибка создания таблиц мессенджера: {e}")

    def create_timeline_tables(self):
        """Миграция: таблицы сроков проектов и надзора"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project_timeline_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_id INTEGER NOT NULL,
                    stage_code TEXT NOT NULL,
                    stage_name TEXT NOT NULL,
                    stage_group TEXT NOT NULL,
                    substage_group TEXT,
                    actual_date TEXT,
                    actual_days INTEGER DEFAULT 0,
                    norm_days INTEGER DEFAULT 0,
                    status TEXT DEFAULT '',
                    executor_role TEXT NOT NULL,
                    is_in_contract_scope INTEGER DEFAULT 1,
                    sort_order INTEGER NOT NULL,
                    raw_norm_days REAL DEFAULT 0,
                    cumulative_days REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE CASCADE,
                    UNIQUE(contract_id, stage_code)
                )
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timeline_contract
                ON project_timeline_entries(contract_id)
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS supervision_timeline_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    supervision_card_id INTEGER NOT NULL,
                    stage_code TEXT NOT NULL,
                    stage_name TEXT NOT NULL,
                    sort_order INTEGER NOT NULL,
                    plan_date TEXT,
                    actual_date TEXT,
                    actual_days INTEGER DEFAULT 0,
                    budget_planned REAL DEFAULT 0,
                    budget_actual REAL DEFAULT 0,
                    budget_savings REAL DEFAULT 0,
                    supplier TEXT,
                    commission REAL DEFAULT 0,
                    status TEXT DEFAULT 'Не начато',
                    notes TEXT,
                    executor TEXT,
                    defects_found INTEGER DEFAULT 0,
                    defects_resolved INTEGER DEFAULT 0,
                    site_visits INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (supervision_card_id) REFERENCES supervision_cards(id) ON DELETE CASCADE,
                    UNIQUE(supervision_card_id, stage_code)
                )
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_supervision_timeline_card
                ON supervision_timeline_entries(supervision_card_id)
            ''')

            # Миграция: добавляем commission если отсутствует
            cursor.execute("PRAGMA table_info(supervision_timeline_entries)")
            sv_cols = [col[1] for col in cursor.fetchall()]
            if 'commission' not in sv_cols:
                cursor.execute('ALTER TABLE supervision_timeline_entries ADD COLUMN commission REAL DEFAULT 0')

            # Таблица выездов надзора
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS supervision_visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    supervision_card_id INTEGER NOT NULL,
                    stage_code TEXT NOT NULL,
                    stage_name TEXT NOT NULL,
                    visit_date TEXT NOT NULL,
                    executor_name TEXT,
                    notes TEXT,
                    sort_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (supervision_card_id) REFERENCES supervision_cards(id) ON DELETE CASCADE
                )
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_supervision_visits_card_id
                ON supervision_visits(supervision_card_id)
            ''')

            conn.commit()
            self.close()
        except Exception as e:
            print(f"[MIGRATION] Ошибка создания таблиц timeline: {e}")
