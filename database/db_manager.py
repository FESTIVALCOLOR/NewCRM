import sqlite3
from datetime import datetime
import json
import threading
try:
    from PyQt5.QtCore import QDate
except ImportError:
    QDate = None
from utils.password_utils import hash_password, verify_password
from utils.yandex_disk import YandexDiskManager
from config import YANDEX_DISK_TOKEN
from database.migrations import DatabaseMigrations


# Флаг для предотвращения повторных миграций
_migrations_completed = False
_migrations_lock = threading.Lock()


class DatabaseManager(DatabaseMigrations):
    def __init__(self, db_path='interior_studio.db'):
        global _migrations_completed

        self.db_path = db_path
        self.connection = None

        # ========== КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ ==========
        # Создаем alias для совместимости со старым кодом
        self.conn = None  # Добавляем атрибут
        # =============================================

        # Выполняем миграции только один раз за сессию
        with _migrations_lock:
            if not _migrations_completed:
                self.run_migrations()
                self.create_supervision_table_migration()
                self.fix_supervision_cards_column_name()
                self.create_supervision_history_table()
                self.create_manager_acceptance_table()
                self.create_payments_system_tables()
                self.add_reassigned_field_to_payments()
                self.add_submitted_date_to_stage_executors()
                self.add_stage_field_to_payments()
                self.add_contract_file_columns()
                self.create_project_files_table()
                self.create_project_templates_table()
                self.create_timeline_tables()
                self.add_project_subtype_to_contracts()
                self.add_floors_to_contracts()
                self.create_stage_workflow_state_table()
                self.create_messenger_tables()
                self.create_performance_indexes()
                self.add_missing_fields_rates_payments_salaries()
                _migrations_completed = True

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

    # Whitelist допустимых имён таблиц для динамического SQL
    ALLOWED_TABLES = {
        'clients', 'contracts', 'employees', 'crm_cards', 'supervision_cards',
        'payments', 'rates', 'salaries', 'project_files', 'action_history',
        'supervision_history', 'stage_executors', 'supervision_orders',
        'employee_permissions', 'template_rates', 'contract_templates',
        'messenger_settings', 'messenger_scripts', 'norm_days'
    }

    def _validate_table(self, table: str):
        """Проверяет имя таблицы по whitelist перед подстановкой в SQL"""
        if table not in self.ALLOWED_TABLES:
            raise ValueError(f"Недопустимое имя таблицы: {table}")

    @staticmethod
    def _validate_columns(columns):
        """Проверяет имена колонок перед подстановкой в SQL SET clause.
        Допускаются только snake_case идентификаторы (a-z, 0-9, _)."""
        import re
        pattern = re.compile(r'^[a-z_][a-z0-9_]*$')
        for col in columns:
            if not pattern.match(col):
                raise ValueError(f"Недопустимое имя колонки: {col}")

    def _build_set_clause(self, data: dict):
        """Строит безопасный SET clause из словаря данных.
        Валидирует имена колонок и возвращает (set_clause, values)."""
        self._validate_columns(data.keys())
        set_parts = [f'{key} = ?' for key in data.keys()]
        return ', '.join(set_parts), list(data.values())

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
        print(f"Поиск сотрудников с должностью '{position}':")
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
    
    def get_all_clients(self, skip: int = 0, limit: int = 10000):
        """Получение всех клиентов с поддержкой пагинации.

        Args:
            skip: Количество записей для пропуска (OFFSET)
            limit: Максимальное количество записей (LIMIT)
        """
        conn = self.connect()
        cursor = conn.cursor()
        # Параметризованный SQL запрос с поддержкой пагинации
        cursor.execute(
            'SELECT * FROM clients ORDER BY id DESC LIMIT ? OFFSET ?',
            (limit, skip)
        )
        clients = [dict(row) for row in cursor.fetchall()]
        self.close()
        return clients

    def get_clients_count(self) -> int:
        """Получить общее количество клиентов (для пагинации)"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM clients')
        count = cursor.fetchone()[0]
        self.close()
        return count
    
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

        set_clause, values = self._build_set_clause(validated_data)
        values = values + [client_id]

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
    
    def get_all_contracts(self, skip: int = 0, limit: int = 10000):
        """Получение всех договоров с поддержкой пагинации.

        Args:
            skip: Количество записей для пропуска (OFFSET)
            limit: Максимальное количество записей (LIMIT)
        """
        conn = self.connect()
        cursor = conn.cursor()
        # Параметризованный SQL запрос с поддержкой пагинации
        cursor.execute(
            '''
            SELECT c.*, cl.full_name, cl.organization_name, cl.client_type
            FROM contracts c
            LEFT JOIN clients cl ON c.client_id = cl.id
            ORDER BY c.id DESC
            LIMIT ? OFFSET ?
            ''',
            (limit, skip)
        )
        contracts = [dict(row) for row in cursor.fetchall()]
        self.close()
        return contracts

    def check_contract_number_exists(self, contract_number, exclude_id=None):
        """Проверка существования номера договора

        Args:
            contract_number: Номер договора для проверки
            exclude_id: ID договора, который нужно исключить из проверки (для редактирования)
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            if exclude_id is not None:
                cursor.execute('SELECT COUNT(*) as count FROM contracts WHERE contract_number = ? AND id != ?', (contract_number, exclude_id))
            else:
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
        need_supervision_card = False  # Флаг для создания карточки надзора
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

                # ИСПРАВЛЕНИЕ BUG #2: Автоматическое создание карточки надзора
                if new_status == 'АВТОРСКИЙ НАДЗОР':
                    need_supervision_card = True

        # Формируем SQL запрос динамически
        set_clause, values = self._build_set_clause(updates)
        values = values + [contract_id]

        query = f"UPDATE contracts SET {set_clause} WHERE id = ?"

        cursor.execute(query, values)
        conn.commit()

        # ========== ИСПРАВЛЕНИЕ BUG #2: Автосоздание карточки надзора ==========
        if need_supervision_card:
            try:
                # Проверяем, существует ли уже карточка надзора для этого договора
                cursor.execute('SELECT id FROM supervision_cards WHERE contract_id = ?', (contract_id,))
                existing_supervision = cursor.fetchone()

                if not existing_supervision:
                    # Создаём карточку надзора
                    cursor.execute('''
                    INSERT INTO supervision_cards (contract_id, column_name, created_at)
                    VALUES (?, 'Новый заказ', datetime('now'))
                    ''', (contract_id,))
                    conn.commit()
                    supervision_card_id = cursor.lastrowid
                    print(f"[OK] BUG #2 FIX: Автоматически создана карточка надзора ID={supervision_card_id} для договора {contract_id}")
                else:
                    print(f"[INFO] Карточка надзора для договора {contract_id} уже существует (ID={existing_supervision['id']})")
            except Exception as e:
                print(f"[WARN] Ошибка автосоздания карточки надзора: {e}")
        # ===================================================================

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
        
        set_clause, values = self._build_set_clause(updates)
        values = values + [card_id]

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
                                    current_month = datetime.now().strftime('%Y-%m')

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
        
        set_clause, values = self._build_set_clause(updates)
        values = values + [card_id]

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
        conn = self.connect()
        cursor = conn.cursor()

        # ОСНОВНОЙ ЗАПРОС (CTE вместо коррелированных подзапросов)
        query = '''
        WITH designer_latest AS (
            SELECT se.crm_card_id, MAX(se.id) as max_id
            FROM stage_executors se
            WHERE se.stage_name LIKE '%концепция%'
            GROUP BY se.crm_card_id
        ),
        draftsman_latest AS (
            SELECT se.crm_card_id, MAX(se.id) as max_id
            FROM stage_executors se
            WHERE se.stage_name LIKE '%чертежи%' OR se.stage_name LIKE '%планировочные%'
            GROUP BY se.crm_card_id
        )
        SELECT cc.id as id, cc.contract_id, cc.column_name, cc.deadline, cc.tags,
               cc.is_approved, cc.approval_deadline, cc.approval_stages,
               cc.project_data_link,
               cc.senior_manager_id, cc.sdp_id, cc.gap_id,
               cc.manager_id, cc.surveyor_id,
               c.contract_number, c.address, c.area, c.city, c.agent_type,
               c.project_type, c.status as contract_status,
               e1.full_name as senior_manager_name,
               e2.full_name as sdp_name,
               e3.full_name as gap_name,
               e4.full_name as manager_name,
               e5.full_name as surveyor_name,

               -- ДИЗАЙНЕР (через CTE)
               ed.full_name as designer_name,
               sed.completed as designer_completed,
               sed.deadline as designer_deadline,

               -- ЧЕРТЁЖНИК (через CTE)
               edr.full_name as draftsman_name,
               sedr.completed as draftsman_completed,
               sedr.deadline as draftsman_deadline,

               -- ПОЛЯ ДЛЯ ТЗ И ЗАМЕРА (из crm_cards для совместимости)
               cc.tech_task_file,
               cc.tech_task_date,
               cc.survey_date,

               -- ПОЛЯ ДЛЯ ТЗ И ЗАМЕРА (из contracts)
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
        LEFT JOIN designer_latest dl ON dl.crm_card_id = cc.id
        LEFT JOIN stage_executors sed ON sed.id = dl.max_id
        LEFT JOIN employees ed ON sed.executor_id = ed.id
        LEFT JOIN draftsman_latest drl ON drl.crm_card_id = cc.id
        LEFT JOIN stage_executors sedr ON sedr.id = drl.max_id
        LEFT JOIN employees edr ON sedr.executor_id = edr.id
        WHERE c.project_type = ?
          AND (c.status IS NULL OR c.status = '' OR c.status NOT IN ('СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР'))
        ORDER BY cc.order_position, cc.id
        '''
        
        cursor.execute(query, (project_type,))
        rows = cursor.fetchall()

        cards = [dict(row) for row in rows]

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

        set_clause, values = self._build_set_clause(employee_data)
        values = values + [employee_id]

        cursor.execute(f'UPDATE employees SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?', values)
        conn.commit()
        self.close()

    def get_employee_by_id(self, employee_id):
        """Получение сотрудника по ID"""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM employees WHERE id = ?', (employee_id,))
        row = cursor.fetchone()
        self.close()

        if row:
            return dict(row)
        return None

    def delete_employee(self, employee_id):
        """Удаление сотрудника"""
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute('DELETE FROM employees WHERE id = ?', (employee_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка удаления сотрудника: {e}")
            return False
        finally:
            self.close()

    def cache_employee_password(self, employee_id: int, password: str) -> bool:
        """
        Кеширование пароля сотрудника для offline-аутентификации.
        Вызывается после успешного API входа.

        Args:
            employee_id: ID сотрудника
            password: Пароль в открытом виде (будет захеширован)

        Returns:
            True если успешно, False при ошибке
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Хешируем пароль
            password_hash = hash_password(password)

            # Обновляем пароль в локальной БД
            cursor.execute(
                'UPDATE employees SET password = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (password_hash, employee_id)
            )
            conn.commit()
            self.close()

            print(f"[DB] Пароль сотрудника ID={employee_id} закеширован для offline-входа")
            return True

        except Exception as e:
            print(f"[DB ERROR] Ошибка кеширования пароля: {e}")
            return False

    def get_employee_for_offline_login(self, login: str) -> dict:
        """
        Получение данных сотрудника для offline-аутентификации.
        Возвращает сотрудника только если у него есть закешированный пароль.

        Args:
            login: Логин сотрудника

        Returns:
            Словарь с данными сотрудника или None
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM employees
                WHERE login = ? AND status = 'активный' AND password IS NOT NULL AND password != ''
            ''', (login,))

            employee = cursor.fetchone()
            self.close()

            if employee:
                return dict(employee)
            return None

        except Exception as e:
            print(f"[DB ERROR] Ошибка получения сотрудника для offline-входа: {e}")
            return None

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
    
    def get_year_payments(self, year, include_null_month=False):
        """Получение выплат за год из всех источников с полными данными

        Args:
            year: Год
            include_null_month: Включить платежи с NULL report_month (В работе)
        """
        conn = self.connect()
        cursor = conn.cursor()

        # Условие фильтрации по месяцу
        if include_null_month:
            month_cond_p = "(p.report_month LIKE ? OR p.report_month IS NULL)"
            month_cond_s = "(s.report_month LIKE ? OR s.report_month IS NULL)"
        else:
            month_cond_p = "p.report_month LIKE ?"
            month_cond_s = "s.report_month LIKE ?"

        query = f'''
        SELECT
            p.id, p.contract_id, p.crm_card_id, p.supervision_card_id,
            p.employee_id, e.full_name as employee_name, e.position,
            p.role, p.stage_name, p.final_amount as amount,
            p.payment_type as payment_subtype, 'CRM' as source,
            p.report_month, p.payment_status, p.reassigned,
            c.project_type, c.agent_type, c.address, c.contract_number, c.area, c.city
        FROM payments p
        LEFT JOIN employees e ON p.employee_id = e.id
        LEFT JOIN crm_cards cc ON p.crm_card_id = cc.id
        LEFT JOIN contracts c ON cc.contract_id = c.id
        WHERE {month_cond_p} AND p.crm_card_id IS NOT NULL

        UNION ALL

        SELECT
            p.id, p.contract_id, p.crm_card_id, p.supervision_card_id,
            p.employee_id, e.full_name as employee_name, e.position,
            p.role, p.stage_name, p.final_amount as amount,
            p.payment_type as payment_subtype, 'CRM Надзор' as source,
            p.report_month, p.payment_status, p.reassigned,
            c.project_type, c.agent_type, c.address, c.contract_number, c.area, c.city
        FROM payments p
        LEFT JOIN employees e ON p.employee_id = e.id
        LEFT JOIN supervision_cards sc ON p.supervision_card_id = sc.id
        LEFT JOIN contracts c ON sc.contract_id = c.id
        WHERE {month_cond_p} AND p.supervision_card_id IS NOT NULL

        UNION ALL

        SELECT
            s.id, s.contract_id, NULL as crm_card_id, NULL as supervision_card_id,
            s.employee_id, e.full_name as employee_name, e.position,
            s.payment_type as role, s.stage_name, s.amount,
            'Оклад' as payment_subtype, 'Оклад' as source,
            s.report_month, s.payment_status, 0 as reassigned,
            s.project_type, c.agent_type, c.address, c.contract_number, c.area, c.city
        FROM salaries s
        LEFT JOIN employees e ON s.employee_id = e.id
        LEFT JOIN contracts c ON s.contract_id = c.id
        WHERE {month_cond_s}
        '''

        cursor.execute(query, (f'{year}%', f'{year}%', f'{year}%'))

        payments = [dict(row) for row in cursor.fetchall()]
        self.close()
        return payments
    
    def get_payments_by_type(self, payment_type, project_type_filter=None):
        """Получение выплат по типу (UNION payments + salaries)

        Args:
            payment_type: Тип выплаты ('Индивидуальные проекты', 'Шаблонные проекты', 'Оклады', 'Авторский надзор')
            project_type_filter: Фильтр типа проекта ('Индивидуальный', 'Шаблонный', 'Авторский надзор', None)
        """
        conn = self.connect()
        cursor = conn.cursor()

        if payment_type == 'Оклады':
            # Для Окладов — только из salaries
            cursor.execute('''
            SELECT s.id, s.contract_id, s.employee_id, s.payment_type, s.stage_name,
                   s.amount, s.report_month, s.created_at, s.project_type, s.payment_status,
                   e.full_name as employee_name, e.position,
                   c.contract_number, c.address, c.area, c.city, c.agent_type,
                   'Оклад' as source
            FROM salaries s
            JOIN employees e ON s.employee_id = e.id
            LEFT JOIN contracts c ON s.contract_id = c.id
            ORDER BY s.id DESC
            ''')
        elif project_type_filter == 'Авторский надзор':
            # Для Авторского надзора — payments (supervision) + salaries
            cursor.execute('''
            SELECT p.id, p.contract_id, p.employee_id, p.role, p.stage_name,
                   p.final_amount, p.payment_type, p.report_month, p.payment_status,
                   e.full_name as employee_name, e.position,
                   c.contract_number, c.address, c.area, c.city, c.agent_type,
                   sc.column_name as card_stage,
                   'CRM Надзор' as source,
                   p.reassigned, p.old_employee_id
            FROM payments p
            JOIN employees e ON p.employee_id = e.id
            LEFT JOIN supervision_cards sc ON p.supervision_card_id = sc.id
            LEFT JOIN contracts c ON sc.contract_id = c.id
            WHERE p.supervision_card_id IS NOT NULL

            UNION ALL

            SELECT s.id, s.contract_id, s.employee_id, s.payment_type as role, s.stage_name,
                   s.amount as final_amount, 'Оклад' as payment_type, s.report_month, s.payment_status,
                   e.full_name as employee_name, e.position,
                   c.contract_number, c.address, c.area, c.city, c.agent_type,
                   NULL as card_stage,
                   'Оклад' as source,
                   0 as reassigned, NULL as old_employee_id
            FROM salaries s
            JOIN employees e ON s.employee_id = e.id
            LEFT JOIN contracts c ON s.contract_id = c.id
            WHERE s.project_type = ?

            ORDER BY 1 DESC
            ''', (project_type_filter,))
        elif project_type_filter:
            # Для Индивидуальных / Шаблонных — payments (crm) + salaries
            cursor.execute('''
            SELECT p.id, p.contract_id, p.employee_id, p.role, p.stage_name,
                   p.final_amount, p.payment_type, p.report_month, p.payment_status,
                   e.full_name as employee_name, e.position,
                   c.contract_number, c.address, c.area, c.city, c.agent_type,
                   cc.column_name as card_stage,
                   'CRM' as source,
                   p.reassigned, p.old_employee_id
            FROM payments p
            JOIN employees e ON p.employee_id = e.id
            LEFT JOIN crm_cards cc ON p.crm_card_id = cc.id
            LEFT JOIN contracts c ON cc.contract_id = c.id
            WHERE c.project_type = ?

            UNION ALL

            SELECT s.id, s.contract_id, s.employee_id, s.payment_type as role, s.stage_name,
                   s.amount as final_amount, 'Оклад' as payment_type, s.report_month, s.payment_status,
                   e.full_name as employee_name, e.position,
                   c.contract_number, c.address, c.area, c.city, c.agent_type,
                   NULL as card_stage,
                   'Оклад' as source,
                   0 as reassigned, NULL as old_employee_id
            FROM salaries s
            JOIN employees e ON s.employee_id = e.id
            LEFT JOIN contracts c ON s.contract_id = c.id
            WHERE s.project_type = ?

            ORDER BY 1 DESC
            ''', (project_type_filter, project_type_filter))
        else:
            # Без фильтра — все платежи
            cursor.execute('''
            SELECT s.*, e.full_name as employee_name, e.position,
                   c.contract_number, c.address, c.area, c.city, c.agent_type,
                   'Оклад' as source
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
        
        set_clause, values = self._build_set_clause(salary_data)
        values = values + [salary_id]

        cursor.execute(f'UPDATE salaries SET {set_clause} WHERE id = ?', values)
        conn.commit()
        self.close()
    
    def delete_payment(self, payment_id):
        """Удаление выплаты из таблицы payments"""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM payments WHERE id = ?', (payment_id,))
        conn.commit()
        self.close()

    def delete_salary(self, salary_id):
        """Удаление оклада из таблицы salaries (#5)"""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM salaries WHERE id = ?', (salary_id,))
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
        
    def update_stage_executor_deadline(self, crm_card_id, stage_keyword, deadline, executor_id=None):
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

            # Обновляем executor_id если передан
            if executor_id is not None:
                cursor.execute('''
                UPDATE stage_executors SET executor_id = ?
                WHERE crm_card_id = ? AND stage_name LIKE ? AND completed = 0
                ''', (executor_id, crm_card_id, search_pattern))

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

            print(f"\n[DELETE] УДАЛЕНИЕ ЗАКАЗА:")
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

            print(f"\n[DELETE] УДАЛЕНИЕ ЗАКАЗА НАДЗОРА:")
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
            self.close()
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
        
        set_clause, values = self._build_set_clause(updates)
        values = values + [card_id]

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
    
    def complete_supervision_stage(self, card_id, stage_name=None):
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
        print(f"[OK] Стадия надзора ID={card_id} отмечена как сданная (stage: {stage_name or 'all'})")

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

    def get_action_history(self, entity_type, entity_id):
        """Получить историю действий по сущности"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM action_history
                WHERE entity_type = ? AND entity_id = ?
                ORDER BY action_date DESC
            ''', (entity_type, entity_id))
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            self.close()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"[WARN] get_action_history: {e}")
            return []

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
                   -- ИСПРАВЛЕНИЕ 26.01.2026: Добавлены имена исполнителей для диалога переназначения
                   (SELECT e.full_name
                    FROM stage_executors se
                    JOIN employees e ON se.executor_id = e.id
                    WHERE se.crm_card_id = cc.id
                      AND se.stage_name LIKE '%концепция%'
                    ORDER BY se.id DESC LIMIT 1) as designer_name,

                   (SELECT e.full_name
                    FROM stage_executors se
                    JOIN employees e ON se.executor_id = e.id
                    WHERE se.crm_card_id = cc.id
                      AND (se.stage_name LIKE '%чертежи%' OR se.stage_name LIKE '%планировочные%')
                    ORDER BY se.id DESC LIMIT 1) as draftsman_name,

                   (SELECT se.completed
                    FROM stage_executors se
                    WHERE se.crm_card_id = cc.id
                      AND se.stage_name LIKE '%концепция%'
                    ORDER BY se.id DESC LIMIT 1) as designer_completed,

                   (SELECT se.completed
                    FROM stage_executors se
                    WHERE se.crm_card_id = cc.id
                      AND (se.stage_name LIKE '%чертежи%' OR se.stage_name LIKE '%планировочные%')
                    ORDER BY se.id DESC LIMIT 1) as draftsman_completed,

                   -- Дедлайны исполнителей
                   (SELECT se.deadline
                    FROM stage_executors se
                    WHERE se.crm_card_id = cc.id
                      AND se.stage_name LIKE '%концепция%'
                    ORDER BY se.id DESC LIMIT 1) as designer_deadline,

                   (SELECT se.deadline
                    FROM stage_executors se
                    WHERE se.crm_card_id = cc.id
                      AND (se.stage_name LIKE '%чертежи%' OR se.stage_name LIKE '%планировочные%')
                    ORDER BY se.id DESC LIMIT 1) as draftsman_deadline
            FROM crm_cards cc
            WHERE cc.id = ?
            ''', (card_id,))

            row = cursor.fetchone()
            self.close()

            return dict(row) if row else None

        except Exception as e:
            print(f"[ERROR] Ошибка получения данных карточки: {e}")
            return None

    def get_dashboard_statistics(self, year=None, month=None, quarter=None, project_type=None):
        """Получение общей статистики для Dashboard за все время"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Построение дополнительных WHERE-условий по дате и типу проекта
            date_clauses = []
            date_params = []

            if year:
                date_clauses.append("strftime('%Y', c.contract_date) = ?")
                date_params.append(str(year))

            if month:
                date_clauses.append("CAST(strftime('%m', c.contract_date) AS INTEGER) = ?")
                date_params.append(int(month))

            if quarter:
                q_months = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
                q_key = int(quarter) if isinstance(quarter, str) and quarter.isdigit() else (
                    int(quarter[1]) if isinstance(quarter, str) and quarter.startswith('Q') else int(quarter)
                )
                start, end = q_months.get(q_key, (1, 3))
                date_clauses.append("CAST(strftime('%m', c.contract_date) AS INTEGER) BETWEEN ? AND ?")
                date_params.extend([start, end])

            if project_type and project_type != 'Все':
                date_clauses.append("c.agent_type = ?")
                date_params.append(project_type)

            date_filter = (' AND ' + ' AND '.join(date_clauses)) if date_clauses else ''

            # Индивидуальные проекты
            cursor.execute(
                "SELECT COUNT(*) as count, SUM(c.area) as total_area FROM contracts c "
                "WHERE c.project_type = 'Индивидуальный'" + date_filter,
                date_params
            )
            individual = cursor.fetchone()

            # Шаблонные проекты
            cursor.execute(
                "SELECT COUNT(*) as count, SUM(c.area) as total_area FROM contracts c "
                "WHERE c.project_type = 'Шаблонный'" + date_filter,
                date_params
            )
            template = cursor.fetchone()

            # Авторский надзор
            cursor.execute(
                "SELECT COUNT(DISTINCT c.id) as count, SUM(c.area) as total_area FROM contracts c "
                "WHERE c.status = 'АВТОРСКИЙ НАДЗОР'" + date_filter,
                date_params
            )
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
            print(f"[STATS] GET_PROJECT_STATISTICS вызван:")
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
            print(f"[STATS] GET_SUPERVISION_STATISTICS вызван:")
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

    def update_payment_manual(self, payment_id, manual_amount, report_month=None):
        """Обновление выплаты с ручным вводом"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            if report_month is not None:
                cursor.execute('''
                UPDATE payments
                SET manual_amount = ?,
                    final_amount = ?,
                    is_manual = 1,
                    report_month = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                ''', (manual_amount, manual_amount, report_month, payment_id))
            else:
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
        """Получение всех агентов с цветами (возвращает list[dict])"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, color FROM agents ORDER BY name')
            rows = cursor.fetchall()
            self.close()
            return [{'id': r[0], 'name': r[1], 'color': r[2]} for r in rows]
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
            DatabaseManager._agent_colors_cache = None
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
            DatabaseManager._agent_colors_cache = None
            print(f"[OK] Цвет агента '{name}' обновлен на {color}")
            return True
        except Exception as e:
            print(f"[ERROR] Ошибка обновления цвета агента: {e}")
            return False

    # Кэш цветов агентов на уровне класса (загружается один раз)
    _agent_colors_cache = None

    def get_agent_color(self, name):
        """Получение цвета агента по имени (с кэшированием)"""
        try:
            if DatabaseManager._agent_colors_cache is None:
                self._load_agent_colors_cache()
            return DatabaseManager._agent_colors_cache.get(name)
        except Exception as e:
            print(f"[ERROR] Ошибка получения цвета агента: {e}")
            return None

    def _load_agent_colors_cache(self):
        """Загрузка всех цветов агентов одним запросом"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT name, color FROM agents')
            rows = cursor.fetchall()
            self.close()
            DatabaseManager._agent_colors_cache = {row['name']: row['color'] for row in rows}
        except Exception:
            DatabaseManager._agent_colors_cache = {}

    def invalidate_agent_colors_cache(self):
        """Сброс кэша цветов агентов"""
        DatabaseManager._agent_colors_cache = None

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

    # ========== МЕТОДЫ-ОБЁРТКИ ДЛЯ OFFLINE FALLBACK (DataAccess) ==========

    def get_payment(self, payment_id):
        """Получить платёж по ID"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM payments WHERE id = ?', (payment_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                self.close()
                return result
            self.close()
            return None
        except Exception as e:
            print(f"[WARN] get_payment: {e}")
            return None

    def add_payment(self, payment_data):
        """Добавить платёж (обёртка для DataAccess)"""
        try:
            return self.create_payment_record(
                payment_data.get('contract_id'),
                payment_data.get('employee_id'),
                payment_data.get('role', ''),
                payment_data.get('stage_name'),
                payment_data.get('payment_type'),
                payment_data.get('report_month'),
                payment_data.get('crm_card_id'),
                payment_data.get('supervision_card_id')
            )
        except Exception as e:
            print(f"[WARN] add_payment: {e}")
            return None

    def update_payment(self, payment_id, payment_data):
        """Обновить платёж"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            set_clause, values = self._build_set_clause(payment_data)
            values = values + [payment_id]
            cursor.execute(f'UPDATE payments SET {set_clause} WHERE id = ?', values)
            conn.commit()
            self.close()
            return True
        except Exception as e:
            print(f"[WARN] update_payment: {e}")
            return False

    def get_payments_by_supervision_card(self, card_id):
        """Получить платежи по карточке надзора"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM payments WHERE supervision_card_id = ?', (card_id,))
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]
            self.close()
            return result
        except Exception as e:
            print(f"[WARN] get_payments_by_supervision_card: {e}")
            return []

    def get_salaries(self, report_month=None, employee_id=None):
        """Получить зарплаты"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            query = 'SELECT * FROM salaries WHERE 1=1'
            params = []
            if report_month:
                query += ' AND report_month = ?'
                params.append(report_month)
            if employee_id:
                query += ' AND employee_id = ?'
                params.append(employee_id)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]
            self.close()
            return result
        except Exception as e:
            print(f"[WARN] get_salaries: {e}")
            return []

    def get_salary_by_id(self, salary_id):
        """Получить зарплату по ID"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM salaries WHERE id = ?', (salary_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                self.close()
                return result
            self.close()
            return None
        except Exception as e:
            print(f"[WARN] get_salary_by_id: {e}")
            return None

    def get_rates(self, project_type=None, role=None):
        """Получить ставки"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            query = 'SELECT * FROM rates WHERE 1=1'
            params = []
            if project_type:
                query += ' AND project_type = ?'
                params.append(project_type)
            if role:
                query += ' AND role = ?'
                params.append(role)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]
            self.close()
            return result
        except Exception as e:
            print(f"[WARN] get_rates: {e}")
            return []

    def get_rate_by_id(self, rate_id):
        """Получить ставку по ID"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM rates WHERE id = ?', (rate_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                self.close()
                return result
            self.close()
            return None
        except Exception as e:
            print(f"[WARN] get_rate_by_id: {e}")
            return None

    def add_rate(self, rate_data):
        """Добавить ставку"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            columns = ', '.join(rate_data.keys())
            placeholders = ', '.join(['?'] * len(rate_data))
            cursor.execute(
                f'INSERT INTO rates ({columns}) VALUES ({placeholders})',
                list(rate_data.values())
            )
            conn.commit()
            rate_id = cursor.lastrowid
            self.close()
            return {'id': rate_id, **rate_data}
        except Exception as e:
            print(f"[WARN] add_rate: {e}")
            return None

    def update_rate(self, rate_id, rate_data):
        """Обновить ставку"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            set_clause, values = self._build_set_clause(rate_data)
            values = values + [rate_id]
            cursor.execute(f'UPDATE rates SET {set_clause} WHERE id = ?', values)
            conn.commit()
            self.close()
            return True
        except Exception as e:
            print(f"[WARN] update_rate: {e}")
            return False

    def delete_rate(self, rate_id):
        """Удалить ставку"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM rates WHERE id = ?', (rate_id,))
            conn.commit()
            self.close()
            return True
        except Exception as e:
            print(f"[WARN] delete_rate: {e}")
            return False

    def get_template_rates(self, role=None):
        """Получить шаблонные ставки (fallback на rates)"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            # Таблица template_rates может отсутствовать — пробуем rates
            query = 'SELECT * FROM rates WHERE 1=1'
            params = []
            if role:
                query += ' AND role = ?'
                params.append(role)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]
            self.close()
            return result
        except Exception as e:
            print(f"[WARN] get_template_rates: {e}")
            return []

    def get_contract_files(self, contract_id, stage=None):
        """Получить файлы договора (алиас для get_project_files)"""
        return self.get_project_files(contract_id, stage)

    def add_contract_file(self, file_data):
        """Добавить файл договора (обёртка над add_project_file)"""
        try:
            return self.add_project_file(
                file_data.get('contract_id'),
                file_data.get('stage', ''),
                file_data.get('file_type', ''),
                file_data.get('public_link', ''),
                file_data.get('yandex_path', ''),
                file_data.get('file_name', ''),
                file_data.get('preview_cache_path'),
                file_data.get('variation', 1)
            )
        except Exception as e:
            print(f"[WARN] add_contract_file: {e}")
            return None

    def get_supervision_card_data(self, card_id):
        """Получить данные карточки надзора по ID"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM supervision_cards WHERE id = ?', (card_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                self.close()
                return result
            self.close()
            return None
        except Exception as e:
            print(f"[WARN] get_supervision_card_data: {e}")
            return None

    def add_supervision_card(self, card_data):
        """Добавить карточку надзора (обёртка над create_supervision_card)"""
        try:
            contract_id = card_data.get('contract_id') if isinstance(card_data, dict) else card_data
            return self.create_supervision_card(contract_id)
        except Exception as e:
            print(f"[WARN] add_supervision_card: {e}")
            return None

    def get_employee_permissions(self, employee_id):
        """Получить права сотрудника (заглушка для offline)"""
        try:
            return {'permissions': []}
        except Exception as e:
            print(f"[WARN] get_employee_permissions: {e}")
            return {'permissions': []}

    def set_employee_permissions(self, employee_id, data):
        """Установить права сотрудника (заглушка для offline)"""
        try:
            return False
        except Exception as e:
            print(f"[WARN] set_employee_permissions: {e}")
            return False

    def add_crm_card(self, card_data):
        """Добавить CRM-карточку (обёртка над _create_crm_card)"""
        try:
            contract_id = card_data.get('contract_id') if isinstance(card_data, dict) else card_data
            project_type = card_data.get('project_type', 'Индивидуальный') if isinstance(card_data, dict) else 'Индивидуальный'
            # _create_crm_card использует self.connection напрямую
            conn = self.connect()
            self._create_crm_card(contract_id, project_type)
            # Получаем ID созданной карточки
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM crm_cards WHERE contract_id = ? ORDER BY id DESC LIMIT 1', (contract_id,))
            row = cursor.fetchone()
            self.close()
            if row:
                return {'id': row['id'], 'contract_id': contract_id}
            return None
        except Exception as e:
            print(f"[WARN] add_crm_card: {e}")
            return None

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

    # ========== МЕТОДЫ ДЛЯ ДАШБОРДОВ ==========

    def get_clients_dashboard_stats(self, year=None, agent_type=None):
        """Статистика для дашборда страницы Клиенты

        Returns:
            dict: {
                'total_clients': int,
                'total_individual': int,
                'total_legal': int,
                'clients_by_year': int,
                'agent_clients_total': int,
                'agent_clients_by_year': int
            }
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # 1. Всего клиентов
            cursor.execute('SELECT COUNT(*) FROM clients')
            total_clients = cursor.fetchone()[0]

            # 2. Всего физлиц
            cursor.execute("SELECT COUNT(*) FROM clients WHERE client_type = 'Физическое лицо'")
            total_individual = cursor.fetchone()[0]

            # 3. Всего юрлиц
            cursor.execute("SELECT COUNT(*) FROM clients WHERE client_type = 'Юридическое лицо'")
            total_legal = cursor.fetchone()[0]

            # 4. Клиенты за год (через договоры)
            if year:
                cursor.execute('''
                    SELECT COUNT(DISTINCT c.client_id)
                    FROM contracts c
                    WHERE strftime('%Y', c.contract_date) = ?
                ''', (str(year),))
                clients_by_year = cursor.fetchone()[0]
            else:
                clients_by_year = 0

            # 5. Клиенты агента (всего)
            if agent_type:
                cursor.execute('''
                    SELECT COUNT(DISTINCT c.client_id)
                    FROM contracts c
                    WHERE c.agent_type = ?
                ''', (agent_type,))
                agent_clients_total = cursor.fetchone()[0]
            else:
                agent_clients_total = 0

            # 6. Клиенты агента за год
            if agent_type and year:
                cursor.execute('''
                    SELECT COUNT(DISTINCT c.client_id)
                    FROM contracts c
                    WHERE c.agent_type = ? AND strftime('%Y', c.contract_date) = ?
                ''', (agent_type, str(year)))
                agent_clients_by_year = cursor.fetchone()[0]
            else:
                agent_clients_by_year = 0

            self.close()

            return {
                'total_clients': total_clients,
                'total_individual': total_individual,
                'total_legal': total_legal,
                'clients_by_year': clients_by_year,
                'agent_clients_total': agent_clients_total,
                'agent_clients_by_year': agent_clients_by_year
            }

        except Exception as e:
            print(f"[ERROR] Ошибка получения статистики клиентов: {e}")
            import traceback
            traceback.print_exc()
            return {
                'total_clients': 0,
                'total_individual': 0,
                'total_legal': 0,
                'clients_by_year': 0,
                'agent_clients_total': 0,
                'agent_clients_by_year': 0
            }

    def get_contracts_dashboard_stats(self, year=None, agent_type=None):
        """Статистика для дашборда страницы Договора

        Returns:
            dict: {
                'individual_orders': int,
                'individual_area': float,
                'template_orders': int,
                'template_area': float,
                'agent_orders_by_year': int,
                'agent_area_by_year': float
            }
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # 1-2. Индивидуальные проекты
            cursor.execute('''
                SELECT COUNT(*), COALESCE(SUM(area), 0)
                FROM contracts
                WHERE project_type = 'Индивидуальный'
            ''')
            row = cursor.fetchone()
            individual_orders = row[0]
            individual_area = row[1]

            # 3-4. Шаблонные проекты
            cursor.execute('''
                SELECT COUNT(*), COALESCE(SUM(area), 0)
                FROM contracts
                WHERE project_type = 'Шаблонный'
            ''')
            row = cursor.fetchone()
            template_orders = row[0]
            template_area = row[1]

            # 5-6. Заказы агента за год
            if agent_type and year:
                cursor.execute('''
                    SELECT COUNT(*), COALESCE(SUM(area), 0)
                    FROM contracts
                    WHERE agent_type = ? AND strftime('%Y', contract_date) = ?
                ''', (agent_type, str(year)))
                row = cursor.fetchone()
                agent_orders_by_year = row[0]
                agent_area_by_year = row[1]
            else:
                agent_orders_by_year = 0
                agent_area_by_year = 0

            self.close()

            return {
                'individual_orders': individual_orders,
                'individual_area': individual_area,
                'template_orders': template_orders,
                'template_area': template_area,
                'agent_orders_by_year': agent_orders_by_year,
                'agent_area_by_year': agent_area_by_year
            }

        except Exception as e:
            print(f"[ERROR] Ошибка получения статистики договоров: {e}")
            import traceback
            traceback.print_exc()
            return {
                'individual_orders': 0,
                'individual_area': 0,
                'template_orders': 0,
                'template_area': 0,
                'agent_orders_by_year': 0,
                'agent_area_by_year': 0
            }

    def get_contracts_count(
        self,
        status=None,
        project_type=None,
        year=None
    ):
        """Получить количество договоров с фильтрацией (без загрузки всех записей)

        Args:
            status: Фильтр по статусу договора (опционально)
            project_type: Фильтр по типу проекта (опционально)
            year: Фильтр по году даты договора (опционально)

        Returns:
            int: Количество договоров, удовлетворяющих фильтрам
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Строим запрос с параметризованными условиями
            conditions = []
            params = []

            if status is not None:
                conditions.append('status = ?')
                params.append(status)

            if project_type is not None:
                conditions.append('project_type = ?')
                params.append(project_type)

            if year is not None:
                conditions.append("strftime('%Y', contract_date) = ?")
                params.append(str(year))

            query = 'SELECT COUNT(*) as cnt FROM contracts'
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)

            cursor.execute(query, params)
            row = cursor.fetchone()
            self.close()
            return row[0] if row else 0

        except Exception as e:
            print(f"[ERROR] Ошибка get_contracts_count: {e}")
            return 0

    def get_crm_dashboard_stats(self, project_type, agent_type=None):
        """Статистика для дашборда СРМ (Индивидуальные/Шаблонные/Надзор)

        Args:
            project_type: 'Индивидуальный', 'Шаблонный', или 'Авторский надзор'
            agent_type: Тип агента для фильтрации

        Returns:
            dict: {
                'total_orders': int,
                'total_area': float,
                'active_orders': int,
                'archive_orders': int,
                'agent_active_orders': int,
                'agent_archive_orders': int
            }
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Определяем условия для фильтрации
            # Используем единую таблицу crm_cards для Индивидуальных и Шаблонных
            # и crm_supervision для Авторского надзора
            if project_type == 'Авторский надзор':
                crm_table = 'supervision_cards'
                contract_condition = "c.status = 'АВТОРСКИЙ НАДЗОР'"
                # Для надзора используем supervision_cards
                crm_join_condition = "crm.contract_id = c.id"
            elif project_type == 'Индивидуальный':
                crm_table = 'crm_cards'
                contract_condition = "c.project_type = 'Индивидуальный'"
                crm_join_condition = "crm.contract_id = c.id AND c.project_type = 'Индивидуальный'"
            else:  # Шаблонный
                crm_table = 'crm_cards'
                contract_condition = "c.project_type = 'Шаблонный'"
                crm_join_condition = "crm.contract_id = c.id AND c.project_type = 'Шаблонный'"
            self._validate_table(crm_table)

            # 1-2. Всего заказов и площадь (из договоров)
            cursor.execute(f'''
                SELECT COUNT(*), COALESCE(SUM(c.area), 0)
                FROM contracts c
                WHERE {contract_condition}
            ''')
            row = cursor.fetchone()
            total_orders = row[0]
            total_area = row[1]

            # 3. Активные заказы в СРМ (карточки в crm_cards/supervision_cards)
            if project_type == 'Авторский надзор':
                cursor.execute(f'SELECT COUNT(*) FROM {crm_table}')
            else:
                # Для Индивидуальных/Шаблонных фильтруем по project_type через JOIN
                cursor.execute(f'''
                    SELECT COUNT(*)
                    FROM {crm_table} crm
                    JOIN contracts c ON {crm_join_condition}
                ''')
            active_orders = cursor.fetchone()[0]

            # 4. Архивные заказы - считаем договора без активных карточек в CRM
            # (договора которые были завершены)
            if project_type == 'Авторский надзор':
                cursor.execute(f'''
                    SELECT COUNT(*)
                    FROM contracts c
                    WHERE {contract_condition}
                    AND c.id NOT IN (SELECT contract_id FROM {crm_table})
                ''')
            else:
                cursor.execute(f'''
                    SELECT COUNT(*)
                    FROM contracts c
                    WHERE {contract_condition}
                    AND c.id NOT IN (SELECT contract_id FROM {crm_table})
                ''')
            archive_orders = cursor.fetchone()[0]

            # 5. Активные заказы агента
            agent_active_orders = 0
            if agent_type:
                if project_type == 'Авторский надзор':
                    cursor.execute(f'''
                        SELECT COUNT(*)
                        FROM {crm_table} crm
                        JOIN contracts c ON crm.contract_id = c.id
                        WHERE c.agent_type = ?
                    ''', (agent_type,))
                else:
                    cursor.execute(f'''
                        SELECT COUNT(*)
                        FROM {crm_table} crm
                        JOIN contracts c ON crm.contract_id = c.id
                        WHERE c.project_type = ? AND c.agent_type = ?
                    ''', (project_type, agent_type))
                agent_active_orders = cursor.fetchone()[0]

            # 6. Архивные заказы агента
            agent_archive_orders = 0
            if agent_type:
                if project_type == 'Авторский надзор':
                    cursor.execute(f'''
                        SELECT COUNT(*)
                        FROM contracts c
                        WHERE {contract_condition}
                        AND c.agent_type = ?
                        AND c.id NOT IN (SELECT contract_id FROM {crm_table})
                    ''', (agent_type,))
                else:
                    cursor.execute(f'''
                        SELECT COUNT(*)
                        FROM contracts c
                        WHERE c.project_type = ?
                        AND c.agent_type = ?
                        AND c.id NOT IN (SELECT contract_id FROM {crm_table})
                    ''', (project_type, agent_type))
                agent_archive_orders = cursor.fetchone()[0]

            self.close()

            return {
                'total_orders': total_orders,
                'total_area': total_area,
                'active_orders': active_orders,
                'archive_orders': archive_orders,
                'agent_active_orders': agent_active_orders,
                'agent_archive_orders': agent_archive_orders
            }

        except Exception as e:
            print(f"[ERROR] Ошибка получения статистики СРМ: {e}")
            import traceback
            traceback.print_exc()
            return {
                'total_orders': 0,
                'total_area': 0,
                'active_orders': 0,
                'archive_orders': 0,
                'agent_active_orders': 0,
                'agent_archive_orders': 0
            }

    def get_employees_dashboard_stats(self):
        """Статистика для дашборда страницы Сотрудники

        Returns:
            dict: {
                'active_employees': int,
                'reserve_employees': int,
                'active_admin': int,
                'active_project': int,
                'active_execution': int,
                'nearest_birthday': str
            }
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # 1. Активные сотрудники (используем LIKE для надёжности)
            cursor.execute("SELECT COUNT(*) FROM employees WHERE status LIKE '%ктивн%'")
            active_employees = cursor.fetchone()[0]

            # 2. Сотрудники в резерве
            cursor.execute("SELECT COUNT(*) FROM employees WHERE status LIKE '%езерв%'")
            reserve_employees = cursor.fetchone()[0]

            # 3. Активный руководящий состав (административный отдел)
            cursor.execute("""
                SELECT COUNT(*) FROM employees
                WHERE status LIKE '%ктивн%' AND department LIKE '%дминистр%'
            """)
            active_admin = cursor.fetchone()[0]

            # 4. Активный проектный отдел
            cursor.execute("""
                SELECT COUNT(*) FROM employees
                WHERE status LIKE '%ктивн%' AND department LIKE '%роектн%'
            """)
            active_project = cursor.fetchone()[0]

            # 5. Активный исполнительный отдел
            cursor.execute("""
                SELECT COUNT(*) FROM employees
                WHERE status LIKE '%ктивн%' AND department LIKE '%сполнит%'
            """)
            active_execution = cursor.fetchone()[0]

            # 6. Ближайший день рождения
            from datetime import datetime, date
            today = date.today()

            cursor.execute("""
                SELECT full_name, birth_date FROM employees
                WHERE birth_date IS NOT NULL AND birth_date != ''
            """)
            employees = cursor.fetchall()

            nearest_birthday = "Нет данных"
            min_days = 366
            birthday_names = []

            for emp in employees:
                try:
                    birth_date = datetime.strptime(emp['birth_date'], '%Y-%m-%d').date()
                    # Переносим день рождения на текущий год
                    this_year_birthday = birth_date.replace(year=today.year)

                    # Если день рождения уже прошел, берем следующий год
                    if this_year_birthday < today:
                        this_year_birthday = birth_date.replace(year=today.year + 1)

                    days_until = (this_year_birthday - today).days

                    if days_until < min_days:
                        min_days = days_until
                        birthday_names = [emp['full_name']]
                    elif days_until == min_days:
                        birthday_names.append(emp['full_name'])
                except Exception:
                    continue

            if birthday_names:
                nearest_birthday = ", ".join(birthday_names)

            self.close()

            # Подсчитываем дни рождения в ближайшие 30 дней
            upcoming_birthdays_count = 0
            for emp in employees:
                try:
                    birth_date = datetime.strptime(emp['birth_date'], '%Y-%m-%d').date()
                    this_year_birthday = birth_date.replace(year=today.year)
                    if this_year_birthday < today:
                        this_year_birthday = birth_date.replace(year=today.year + 1)
                    days_until = (this_year_birthday - today).days
                    if 0 <= days_until <= 30:
                        upcoming_birthdays_count += 1
                except Exception:
                    continue

            return {
                'active_employees': active_employees,
                'reserve_employees': reserve_employees,
                'active_admin': active_admin,
                'active_project': active_project,
                'active_execution': active_execution,
                'nearest_birthday': nearest_birthday,
                # Дополнительные ключи для EmployeeReportsDashboard
                'active_management': active_admin,
                'active_projects_dept': active_project,
                'active_execution_dept': active_execution,
                'upcoming_birthdays': upcoming_birthdays_count
            }

        except Exception as e:
            print(f"[ERROR] Ошибка получения статистики сотрудников: {e}")
            import traceback
            traceback.print_exc()
            return {
                'active_employees': 0,
                'reserve_employees': 0,
                'active_admin': 0,
                'active_project': 0,
                'active_execution': 0,
                'nearest_birthday': 'Нет данных',
                # Дополнительные ключи для EmployeeReportsDashboard
                'active_management': 0,
                'active_projects_dept': 0,
                'active_execution_dept': 0,
                'upcoming_birthdays': 0
            }

    def get_salaries_dashboard_stats(self, year=None, month=None):
        """Статистика для дашборда страницы Зарплаты

        Args:
            year: Год для фильтрации
            month: Месяц для фильтрации (1-12)

        Returns:
            dict: {
                'total_paid': float,
                'paid_by_year': float,
                'paid_by_month': float,
                'individual_by_year': float,
                'template_by_year': float,
                'supervision_by_year': float
            }
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # 1. Всего выплачено (за все время)
            cursor.execute("""
                SELECT COALESCE(SUM(final_amount), 0)
                FROM payments
                WHERE payment_status = 'paid'
            """)
            total_paid = cursor.fetchone()[0]

            # 2. Выплачено за год
            if year:
                cursor.execute("""
                    SELECT COALESCE(SUM(final_amount), 0)
                    FROM payments
                    WHERE payment_status = 'paid'
                    AND report_month LIKE ?
                """, (f'{year}-%',))
                paid_by_year = cursor.fetchone()[0]
            else:
                paid_by_year = 0

            # 3. Выплачено за месяц
            if year and month:
                cursor.execute("""
                    SELECT COALESCE(SUM(final_amount), 0)
                    FROM payments
                    WHERE payment_status = 'paid'
                    AND report_month = ?
                """, (f'{year}-{month:02d}',))
                paid_by_month = cursor.fetchone()[0]
            else:
                paid_by_month = 0

            # 4. Выплачено по индивидуальным за год
            if year:
                cursor.execute("""
                    SELECT COALESCE(SUM(p.final_amount), 0)
                    FROM payments p
                    JOIN contracts c ON p.contract_id = c.id
                    WHERE p.payment_status = 'paid'
                    AND p.report_month LIKE ?
                    AND c.project_type = 'Индивидуальный'
                """, (f'{year}-%',))
                individual_by_year = cursor.fetchone()[0]
            else:
                individual_by_year = 0

            # 5. Выплачено по шаблонным за год
            if year:
                cursor.execute("""
                    SELECT COALESCE(SUM(p.final_amount), 0)
                    FROM payments p
                    JOIN contracts c ON p.contract_id = c.id
                    WHERE p.payment_status = 'paid'
                    AND p.report_month LIKE ?
                    AND c.project_type = 'Шаблонный'
                """, (f'{year}-%',))
                template_by_year = cursor.fetchone()[0]
            else:
                template_by_year = 0

            # 6. Выплачено по авторским надзорам за год
            if year:
                cursor.execute("""
                    SELECT COALESCE(SUM(p.final_amount), 0)
                    FROM payments p
                    JOIN contracts c ON p.contract_id = c.id
                    WHERE p.payment_status = 'paid'
                    AND p.report_month LIKE ?
                    AND c.status = 'АВТОРСКИЙ НАДЗОР'
                """, (f'{year}-%',))
                supervision_by_year = cursor.fetchone()[0]
            else:
                supervision_by_year = 0

            self.close()

            return {
                'total_paid': total_paid,
                'paid_by_year': paid_by_year,
                'paid_by_month': paid_by_month,
                'individual_by_year': individual_by_year,
                'template_by_year': template_by_year,
                'supervision_by_year': supervision_by_year
            }

        except Exception as e:
            print(f"[ERROR] Ошибка получения статистики зарплат: {e}")
            import traceback
            traceback.print_exc()
            return {
                'total_paid': 0,
                'paid_by_year': 0,
                'paid_by_month': 0,
                'individual_by_year': 0,
                'template_by_year': 0,
                'supervision_by_year': 0
            }

    def get_salaries_payment_type_stats(self, payment_type, year=None, month=None, agent_type=None):
        """Статистика для дашборда вкладок зарплат по типу выплат

        Args:
            payment_type: Тип вкладки ('all', 'individual', 'template', 'salary', 'supervision')
            year: Год для фильтрации
            month: Месяц для фильтрации (1-12)
            agent_type: Тип агента для фильтрации

        Returns:
            dict: {
                'total_paid': float,
                'paid_by_year': float,
                'paid_by_month': float,
                'payments_count': int,
                'to_pay_amount': float,
                'by_agent': float
            }
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Условие фильтрации по типу
            type_condition = ""
            join_clause = ""

            if payment_type == 'individual':
                join_clause = "JOIN contracts c ON p.contract_id = c.id"
                type_condition = "AND c.project_type = 'Индивидуальный'"
            elif payment_type == 'template':
                join_clause = "JOIN contracts c ON p.contract_id = c.id"
                type_condition = "AND c.project_type = 'Шаблонный'"
            elif payment_type == 'supervision':
                join_clause = ""
                type_condition = "AND p.supervision_card_id IS NOT NULL"
            elif payment_type == 'salary':
                # Оклады - отдельная таблица salaries
                pass

            # Для окладов используем таблицу salaries
            if payment_type == 'salary':
                # Всего выплачено (только оплаченные оклады)
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0)
                    FROM salaries
                    WHERE payment_status = 'paid'
                """)
                total_paid = cursor.fetchone()[0]

                # За год
                if year:
                    cursor.execute("""
                        SELECT COALESCE(SUM(amount), 0)
                        FROM salaries
                        WHERE payment_status = 'paid'
                        AND report_month LIKE ?
                    """, (f'{year}-%',))
                    paid_by_year = cursor.fetchone()[0]
                else:
                    paid_by_year = 0

                # За месяц
                if year and month:
                    cursor.execute("""
                        SELECT COALESCE(SUM(amount), 0)
                        FROM salaries
                        WHERE payment_status = 'paid'
                        AND report_month = ?
                    """, (f'{year}-{month:02d}',))
                    paid_by_month = cursor.fetchone()[0]
                else:
                    paid_by_month = 0

                # Количество выплат (только оплаченные)
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM salaries
                    WHERE payment_status = 'paid'
                """)
                payments_count = cursor.fetchone()[0]

                # К оплате
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0)
                    FROM salaries
                    WHERE payment_status = 'to_pay'
                """)
                to_pay_amount = cursor.fetchone()[0]

                # По агенту - для окладов не применимо
                by_agent = 0

            else:
                # Для payments таблицы
                # Всего выплачено
                cursor.execute(f"""
                    SELECT COALESCE(SUM(p.final_amount), 0)
                    FROM payments p
                    {join_clause}
                    WHERE p.payment_status = 'paid'
                    {type_condition}
                """)
                total_paid = cursor.fetchone()[0]

                # За год
                if year:
                    cursor.execute(f"""
                        SELECT COALESCE(SUM(p.final_amount), 0)
                        FROM payments p
                        {join_clause}
                        WHERE p.payment_status = 'paid'
                        AND p.report_month LIKE ?
                        {type_condition}
                    """, (f'{year}-%',))
                    paid_by_year = cursor.fetchone()[0]
                else:
                    paid_by_year = 0

                # За месяц
                if year and month:
                    cursor.execute(f"""
                        SELECT COALESCE(SUM(p.final_amount), 0)
                        FROM payments p
                        {join_clause}
                        WHERE p.payment_status = 'paid'
                        AND p.report_month = ?
                        {type_condition}
                    """, (f'{year}-{month:02d}',))
                    paid_by_month = cursor.fetchone()[0]
                else:
                    paid_by_month = 0

                # Количество выплат (только paid)
                cursor.execute(f"""
                    SELECT COUNT(*)
                    FROM payments p
                    {join_clause}
                    WHERE p.payment_status = 'paid'
                    {type_condition}
                """)
                payments_count = cursor.fetchone()[0]

                # К оплате
                cursor.execute(f"""
                    SELECT COALESCE(SUM(p.final_amount), 0)
                    FROM payments p
                    {join_clause}
                    WHERE p.payment_status = 'to_pay'
                    {type_condition}
                """)
                to_pay_amount = cursor.fetchone()[0]

                # По агенту
                if agent_type:
                    if payment_type == 'supervision':
                        # Надзор: через supervision_cards -> contracts
                        cursor.execute("""
                            SELECT COALESCE(SUM(p.final_amount), 0)
                            FROM payments p
                            JOIN supervision_cards sc ON p.supervision_card_id = sc.id
                            JOIN contracts c ON sc.contract_id = c.id
                            WHERE p.payment_status = 'paid'
                            AND p.supervision_card_id IS NOT NULL
                            AND c.agent_type = ?
                        """, (agent_type,))
                    elif payment_type in ('individual', 'template'):
                        cursor.execute(f"""
                            SELECT COALESCE(SUM(p.final_amount), 0)
                            FROM payments p
                            {join_clause}
                            WHERE p.payment_status = 'paid'
                            AND c.agent_type = ?
                            {type_condition}
                        """, (agent_type,))
                    else:
                        # all - нужен join
                        cursor.execute("""
                            SELECT COALESCE(SUM(p.final_amount), 0)
                            FROM payments p
                            JOIN contracts c ON p.contract_id = c.id
                            WHERE p.payment_status = 'paid'
                            AND c.agent_type = ?
                        """, (agent_type,))
                    by_agent = cursor.fetchone()[0]
                else:
                    by_agent = 0

            self.close()

            return {
                'total_paid': total_paid or 0,
                'paid_by_year': paid_by_year or 0,
                'paid_by_month': paid_by_month or 0,
                'payments_count': payments_count or 0,
                'to_pay_amount': to_pay_amount or 0,
                'by_agent': by_agent or 0
            }

        except Exception as e:
            print(f"[ERROR] Ошибка получения статистики по типу {payment_type}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'total_paid': 0,
                'paid_by_year': 0,
                'paid_by_month': 0,
                'payments_count': 0,
                'to_pay_amount': 0,
                'by_agent': 0
            }

    def get_salaries_all_payments_stats(self, year=None, month=None):
        """Статистика для дашборда 'Все выплаты'
        Возвращает: total_paid, paid_by_year, paid_by_month, individual_by_year, template_by_year, supervision_by_year
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Всего выплачено
            cursor.execute("""
                SELECT COALESCE(SUM(final_amount), 0)
                FROM payments
                WHERE payment_status = 'paid'
            """)
            total_paid = cursor.fetchone()[0]

            # За год
            paid_by_year = 0
            individual_by_year = 0
            template_by_year = 0
            supervision_by_year = 0

            if year:
                cursor.execute("""
                    SELECT COALESCE(SUM(final_amount), 0)
                    FROM payments
                    WHERE payment_status = 'paid'
                    AND report_month LIKE ?
                """, (f'{year}-%',))
                paid_by_year = cursor.fetchone()[0]

                # Индивидуальные за год
                cursor.execute("""
                    SELECT COALESCE(SUM(p.final_amount), 0)
                    FROM payments p
                    JOIN contracts c ON p.contract_id = c.id
                    WHERE p.payment_status = 'paid'
                    AND p.report_month LIKE ?
                    AND c.project_type = 'Индивидуальный'
                """, (f'{year}-%',))
                individual_by_year = cursor.fetchone()[0]

                # Шаблонные за год
                cursor.execute("""
                    SELECT COALESCE(SUM(p.final_amount), 0)
                    FROM payments p
                    JOIN contracts c ON p.contract_id = c.id
                    WHERE p.payment_status = 'paid'
                    AND p.report_month LIKE ?
                    AND c.project_type = 'Шаблонный'
                """, (f'{year}-%',))
                template_by_year = cursor.fetchone()[0]

                # Авторский надзор за год
                cursor.execute("""
                    SELECT COALESCE(SUM(p.final_amount), 0)
                    FROM payments p
                    JOIN contracts c ON p.contract_id = c.id
                    WHERE p.payment_status = 'paid'
                    AND p.report_month LIKE ?
                    AND c.status = 'АВТОРСКИЙ НАДЗОР'
                """, (f'{year}-%',))
                supervision_by_year = cursor.fetchone()[0]

            # За месяц
            paid_by_month = 0
            if year and month:
                cursor.execute("""
                    SELECT COALESCE(SUM(final_amount), 0)
                    FROM payments
                    WHERE payment_status = 'paid'
                    AND report_month = ?
                """, (f'{year}-{month:02d}',))
                paid_by_month = cursor.fetchone()[0]

            self.close()

            return {
                'total_paid': total_paid or 0,
                'paid_by_year': paid_by_year or 0,
                'paid_by_month': paid_by_month or 0,
                'individual_by_year': individual_by_year or 0,
                'template_by_year': template_by_year or 0,
                'supervision_by_year': supervision_by_year or 0
            }

        except Exception as e:
            print(f"[ERROR] Ошибка получения статистики 'Все выплаты': {e}")
            return {'total_paid': 0, 'paid_by_year': 0, 'paid_by_month': 0,
                    'individual_by_year': 0, 'template_by_year': 0, 'supervision_by_year': 0}

    def get_salaries_individual_stats(self, year=None, month=None, agent_type=None):
        """Статистика для дашборда 'Индивидуальные'
        Возвращает: total_paid, paid_by_year, paid_by_month, by_agent, avg_payment, payments_count
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Всего выплачено
            cursor.execute("""
                SELECT COALESCE(SUM(p.final_amount), 0), COUNT(*), COALESCE(AVG(p.final_amount), 0)
                FROM payments p
                JOIN contracts c ON p.contract_id = c.id
                WHERE p.payment_status = 'paid'
                AND c.project_type = 'Индивидуальный'
            """)
            row = cursor.fetchone()
            total_paid = row[0]
            total_count = row[1]
            avg_payment = row[2]

            # За год
            paid_by_year = 0
            payments_count = 0
            if year:
                cursor.execute("""
                    SELECT COALESCE(SUM(p.final_amount), 0), COUNT(*)
                    FROM payments p
                    JOIN contracts c ON p.contract_id = c.id
                    WHERE p.payment_status = 'paid'
                    AND c.project_type = 'Индивидуальный'
                    AND p.report_month LIKE ?
                """, (f'{year}-%',))
                row = cursor.fetchone()
                paid_by_year = row[0]
                payments_count = row[1]

            # За месяц
            paid_by_month = 0
            if year and month:
                cursor.execute("""
                    SELECT COALESCE(SUM(p.final_amount), 0)
                    FROM payments p
                    JOIN contracts c ON p.contract_id = c.id
                    WHERE p.payment_status = 'paid'
                    AND c.project_type = 'Индивидуальный'
                    AND p.report_month = ?
                """, (f'{year}-{month:02d}',))
                paid_by_month = cursor.fetchone()[0]

            # По агенту
            by_agent = 0
            if agent_type:
                cursor.execute("""
                    SELECT COALESCE(SUM(p.final_amount), 0)
                    FROM payments p
                    JOIN contracts c ON p.contract_id = c.id
                    WHERE p.payment_status = 'paid'
                    AND c.project_type = 'Индивидуальный'
                    AND c.agent_type = ?
                """, (agent_type,))
                by_agent = cursor.fetchone()[0]

            self.close()

            return {
                'total_paid': total_paid or 0,
                'paid_by_year': paid_by_year or 0,
                'paid_by_month': paid_by_month or 0,
                'by_agent': by_agent or 0,
                'avg_payment': avg_payment or 0,
                'payments_count': payments_count or 0
            }

        except Exception as e:
            print(f"[ERROR] Ошибка получения статистики 'Индивидуальные': {e}")
            return {'total_paid': 0, 'paid_by_year': 0, 'paid_by_month': 0,
                    'by_agent': 0, 'avg_payment': 0, 'payments_count': 0}

    def get_salaries_template_stats(self, year=None, month=None, agent_type=None):
        """Статистика для дашборда 'Шаблонные'
        Возвращает: total_paid, paid_by_year, paid_by_month, by_agent, avg_payment, payments_count
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Всего выплачено
            cursor.execute("""
                SELECT COALESCE(SUM(p.final_amount), 0), COUNT(*), COALESCE(AVG(p.final_amount), 0)
                FROM payments p
                JOIN contracts c ON p.contract_id = c.id
                WHERE p.payment_status = 'paid'
                AND c.project_type = 'Шаблонный'
            """)
            row = cursor.fetchone()
            total_paid = row[0]
            total_count = row[1]
            avg_payment = row[2]

            # За год
            paid_by_year = 0
            payments_count = 0
            if year:
                cursor.execute("""
                    SELECT COALESCE(SUM(p.final_amount), 0), COUNT(*)
                    FROM payments p
                    JOIN contracts c ON p.contract_id = c.id
                    WHERE p.payment_status = 'paid'
                    AND c.project_type = 'Шаблонный'
                    AND p.report_month LIKE ?
                """, (f'{year}-%',))
                row = cursor.fetchone()
                paid_by_year = row[0]
                payments_count = row[1]

            # За месяц
            paid_by_month = 0
            if year and month:
                cursor.execute("""
                    SELECT COALESCE(SUM(p.final_amount), 0)
                    FROM payments p
                    JOIN contracts c ON p.contract_id = c.id
                    WHERE p.payment_status = 'paid'
                    AND c.project_type = 'Шаблонный'
                    AND p.report_month = ?
                """, (f'{year}-{month:02d}',))
                paid_by_month = cursor.fetchone()[0]

            # По агенту
            by_agent = 0
            if agent_type:
                cursor.execute("""
                    SELECT COALESCE(SUM(p.final_amount), 0)
                    FROM payments p
                    JOIN contracts c ON p.contract_id = c.id
                    WHERE p.payment_status = 'paid'
                    AND c.project_type = 'Шаблонный'
                    AND c.agent_type = ?
                """, (agent_type,))
                by_agent = cursor.fetchone()[0]

            self.close()

            return {
                'total_paid': total_paid or 0,
                'paid_by_year': paid_by_year or 0,
                'paid_by_month': paid_by_month or 0,
                'by_agent': by_agent or 0,
                'avg_payment': avg_payment or 0,
                'payments_count': payments_count or 0
            }

        except Exception as e:
            print(f"[ERROR] Ошибка получения статистики 'Шаблонные': {e}")
            return {'total_paid': 0, 'paid_by_year': 0, 'paid_by_month': 0,
                    'by_agent': 0, 'avg_payment': 0, 'payments_count': 0}

    def get_salaries_salary_stats(self, year=None, month=None, project_type=None):
        """Статистика для дашборда 'Оклады'
        Возвращает: total_paid, paid_by_year, paid_by_month, by_project_type, avg_salary, employees_count
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Всего выплачено и средний оклад (только оплаченные)
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0), COALESCE(AVG(amount), 0)
                FROM salaries
                WHERE payment_status = 'paid'
            """)
            row = cursor.fetchone()
            total_paid = row[0]
            avg_salary = row[1]

            # За год и кол-во уникальных сотрудников
            paid_by_year = 0
            employees_count = 0
            if year:
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0), COUNT(DISTINCT employee_id)
                    FROM salaries
                    WHERE payment_status = 'paid'
                    AND report_month LIKE ?
                """, (f'{year}-%',))
                row = cursor.fetchone()
                paid_by_year = row[0]
                employees_count = row[1]

            # За месяц
            paid_by_month = 0
            if year and month:
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0)
                    FROM salaries
                    WHERE payment_status = 'paid'
                    AND report_month = ?
                """, (f'{year}-{month:02d}',))
                paid_by_month = cursor.fetchone()[0]

            # По типу проекта
            by_project_type = 0
            if project_type:
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0)
                    FROM salaries
                    WHERE payment_status = 'paid'
                    AND project_type = ?
                """, (project_type,))
                by_project_type = cursor.fetchone()[0]

            self.close()

            return {
                'total_paid': total_paid or 0,
                'paid_by_year': paid_by_year or 0,
                'paid_by_month': paid_by_month or 0,
                'by_project_type': by_project_type or 0,
                'avg_salary': avg_salary or 0,
                'employees_count': employees_count or 0
            }

        except Exception as e:
            print(f"[ERROR] Ошибка получения статистики 'Оклады': {e}")
            return {'total_paid': 0, 'paid_by_year': 0, 'paid_by_month': 0,
                    'by_project_type': 0, 'avg_salary': 0, 'employees_count': 0}

    def get_salaries_supervision_stats(self, year=None, month=None, agent_type=None):
        """Статистика для дашборда 'Авторский надзор'
        Возвращает: total_paid, paid_by_year, paid_by_month, by_agent, avg_payment, payments_count
        Платежи надзора определяются по supervision_card_id IS NOT NULL.
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Всего выплачено (только платежи привязанные к supervision_card)
            cursor.execute("""
                SELECT COALESCE(SUM(p.final_amount), 0), COUNT(*), COALESCE(AVG(p.final_amount), 0)
                FROM payments p
                WHERE p.payment_status = 'paid'
                AND p.supervision_card_id IS NOT NULL
            """)
            row = cursor.fetchone()
            total_paid = row[0]
            total_count = row[1]
            avg_payment = row[2]

            # За год
            paid_by_year = 0
            payments_count = 0
            if year:
                cursor.execute("""
                    SELECT COALESCE(SUM(p.final_amount), 0), COUNT(*)
                    FROM payments p
                    WHERE p.payment_status = 'paid'
                    AND p.supervision_card_id IS NOT NULL
                    AND p.report_month LIKE ?
                """, (f'{year}-%',))
                row = cursor.fetchone()
                paid_by_year = row[0]
                payments_count = row[1]

            # За месяц
            paid_by_month = 0
            if year and month:
                cursor.execute("""
                    SELECT COALESCE(SUM(p.final_amount), 0)
                    FROM payments p
                    WHERE p.payment_status = 'paid'
                    AND p.supervision_card_id IS NOT NULL
                    AND p.report_month = ?
                """, (f'{year}-{month:02d}',))
                paid_by_month = cursor.fetchone()[0]

            # По агенту (через supervision_cards -> contracts)
            by_agent = 0
            if agent_type:
                cursor.execute("""
                    SELECT COALESCE(SUM(p.final_amount), 0)
                    FROM payments p
                    JOIN supervision_cards sc ON p.supervision_card_id = sc.id
                    JOIN contracts c ON sc.contract_id = c.id
                    WHERE p.payment_status = 'paid'
                    AND p.supervision_card_id IS NOT NULL
                    AND c.agent_type = ?
                """, (agent_type,))
                by_agent = cursor.fetchone()[0]

            self.close()

            return {
                'total_paid': total_paid or 0,
                'paid_by_year': paid_by_year or 0,
                'paid_by_month': paid_by_month or 0,
                'by_agent': by_agent or 0,
                'avg_payment': avg_payment or 0,
                'payments_count': payments_count or 0
            }

        except Exception as e:
            print(f"[ERROR] Ошибка получения статистики 'Авторский надзор': {e}")
            return {'total_paid': 0, 'paid_by_year': 0, 'paid_by_month': 0,
                    'by_agent': 0, 'avg_payment': 0, 'payments_count': 0}

    def get_contract_years(self):
        """Получить список всех годов из договоров (для фильтров дашборда)

        Returns:
            list: Список годов в обратном порядке (от нового к старому),
                  включая текущий год и следующий год
        """
        try:
            from datetime import datetime
            conn = self.connect()
            cursor = conn.cursor()

            # Получаем все уникальные годы из дат договоров
            cursor.execute("""
                SELECT DISTINCT strftime('%Y', contract_date) as year
                FROM contracts
                WHERE contract_date IS NOT NULL AND contract_date != ''
                ORDER BY year DESC
            """)

            db_years = [int(row[0]) for row in cursor.fetchall() if row[0]]
            self.close()

            # Добавляем текущий год и следующий год (если их нет)
            current_year = datetime.now().year
            next_year = current_year + 1

            all_years = set(db_years)
            all_years.add(current_year)
            all_years.add(next_year)

            # Сортируем в обратном порядке (от нового к старому)
            years_list = sorted(all_years, reverse=True)

            return years_list

        except Exception as e:
            print(f"[ERROR] Ошибка получения годов договоров: {e}")
            # Возвращаем fallback - 10 лет назад до следующего года
            from datetime import datetime
            current_year = datetime.now().year
            return list(range(current_year + 1, current_year - 10, -1))

    def get_agent_types(self):
        """Получить список всех типов агентов из договоров

        Returns:
            list: Список уникальных типов агентов
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DISTINCT agent_type
                FROM contracts
                WHERE agent_type IS NOT NULL AND agent_type != ''
                ORDER BY agent_type
            """)

            agents = [row[0] for row in cursor.fetchall()]
            self.close()

            return agents

        except Exception as e:
            print(f"[ERROR] Ошибка получения типов агентов: {e}")
            return []

    # =====================================================
    # ТАБЛИЦЫ СРОКОВ (TIMELINE)
    # =====================================================

    def init_project_timeline(self, contract_id, entries):
        """Инициализация таблицы сроков проекта (INSERT OR IGNORE)"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            for entry in entries:
                cursor.execute('''
                    INSERT OR IGNORE INTO project_timeline_entries
                    (contract_id, stage_code, stage_name, stage_group, substage_group,
                     executor_role, is_in_contract_scope, sort_order, raw_norm_days,
                     cumulative_days, norm_days)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    contract_id,
                    entry['stage_code'],
                    entry['stage_name'],
                    entry['stage_group'],
                    entry.get('substage_group', ''),
                    entry['executor_role'],
                    1 if entry.get('is_in_contract_scope', True) else 0,
                    entry['sort_order'],
                    entry.get('raw_norm_days', 0),
                    entry.get('cumulative_days', 0),
                    entry.get('norm_days', 0)
                ))
            conn.commit()
            self.close()
            return True
        except Exception as e:
            print(f"[DB] Ошибка init_project_timeline: {e}")
            return False

    def get_project_timeline(self, contract_id):
        """Получить таблицу сроков проекта"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM project_timeline_entries
                WHERE contract_id = ?
                ORDER BY sort_order
            ''', (contract_id,))
            rows = [dict(row) for row in cursor.fetchall()]
            self.close()
            return rows
        except Exception as e:
            print(f"[DB] Ошибка get_project_timeline: {e}")
            return []

    def update_timeline_entry(self, contract_id, stage_code, updates):
        """Обновить запись таблицы сроков проекта"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            set_clause, values = self._build_set_clause(updates)
            values = values + [contract_id, stage_code]
            cursor.execute(
                f"UPDATE project_timeline_entries SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE contract_id = ? AND stage_code = ?",
                tuple(values)
            )
            conn.commit()
            self.close()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"[DB] Ошибка update_timeline_entry: {e}")
            return False

    def init_supervision_timeline(self, supervision_card_id, entries):
        """Инициализация таблицы сроков надзора (INSERT OR IGNORE)"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            for entry in entries:
                cursor.execute('''
                    INSERT OR IGNORE INTO supervision_timeline_entries
                    (supervision_card_id, stage_code, stage_name, sort_order,
                     status, executor)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    supervision_card_id,
                    entry['stage_code'],
                    entry['stage_name'],
                    entry['sort_order'],
                    entry.get('status', 'Не начато'),
                    entry.get('executor', '')
                ))
            conn.commit()
            self.close()
            return True
        except Exception as e:
            print(f"[DB] Ошибка init_supervision_timeline: {e}")
            return False

    def get_supervision_timeline(self, supervision_card_id):
        """Получить таблицу сроков надзора"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM supervision_timeline_entries
                WHERE supervision_card_id = ?
                ORDER BY sort_order
            ''', (supervision_card_id,))
            rows = [dict(row) for row in cursor.fetchall()]
            self.close()
            return rows
        except Exception as e:
            print(f"[DB] Ошибка get_supervision_timeline: {e}")
            return []

    def update_supervision_timeline_entry(self, supervision_card_id, stage_code, updates):
        """Обновить запись таблицы сроков надзора"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            set_clause, values = self._build_set_clause(updates)
            values = values + [supervision_card_id, stage_code]
            cursor.execute(
                f"UPDATE supervision_timeline_entries SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE supervision_card_id = ? AND stage_code = ?",
                tuple(values)
            )
            conn.commit()
            self.close()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"[DB] Ошибка update_supervision_timeline_entry: {e}")
            return False

    # =========================
    # ГЛОБАЛЬНЫЙ ПОИСК
    # =========================

    def global_search(self, query, limit=50):
        """Полнотекстовый поиск по клиентам, договорам, CRM карточкам"""
        results = []
        if not query or len(query.strip()) < 2:
            return {"results": [], "total": 0, "query": query}
        pattern = f"%{query.strip()}%"
        try:
            conn = self.connect()
            cursor = conn.cursor()
            # Клиенты
            cursor.execute(
                "SELECT id, full_name, phone, email FROM clients WHERE full_name LIKE ? OR phone LIKE ? OR email LIKE ? LIMIT ?",
                (pattern, pattern, pattern, limit)
            )
            for row in cursor.fetchall():
                results.append({
                    "type": "client",
                    "id": row[0],
                    "title": row[1] or "",
                    "subtitle": row[2] or row[3] or "",
                })
            # Договоры
            cursor.execute(
                "SELECT id, contract_number, address FROM contracts WHERE contract_number LIKE ? OR address LIKE ? LIMIT ?",
                (pattern, pattern, limit)
            )
            for row in cursor.fetchall():
                results.append({
                    "type": "contract",
                    "id": row[0],
                    "title": row[1] or "",
                    "subtitle": row[2] or "",
                })
            # CRM карточки (через join с договорами)
            cursor.execute(
                """SELECT cc.id, c.contract_number, c.address, cc.column_name
                   FROM crm_cards cc JOIN contracts c ON cc.contract_id = c.id
                   WHERE c.address LIKE ? OR c.contract_number LIKE ? LIMIT ?""",
                (pattern, pattern, limit)
            )
            for row in cursor.fetchall():
                results.append({
                    "type": "crm_card",
                    "id": row[0],
                    "title": f"Проект #{row[0]}",
                    "subtitle": f"{row[2] or ''} ({row[3]})",
                })
            self.close()
        except Exception as e:
            print(f"[DB] Ошибка global_search: {e}")
        return {"results": results[:limit], "total": len(results), "query": query}

    # =========================
    # СТАТИСТИКА (расширенная)
    # =========================

    def get_funnel_statistics(self, year=None, project_type=None):
        """Статистика воронки: количество карточек по колонкам Kanban"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            query = "SELECT column_name, COUNT(*) as cnt FROM crm_cards"
            conditions = []
            params = []
            if project_type:
                conditions.append(
                    "contract_id IN (SELECT id FROM contracts WHERE project_type = ?)"
                )
                params.append(project_type)
            if year:
                conditions.append(
                    "contract_id IN (SELECT id FROM contracts WHERE strftime('%Y', contract_date) = ?)"
                )
                params.append(str(year))
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " GROUP BY column_name ORDER BY cnt DESC"
            cursor.execute(query, tuple(params))
            funnel = {row[0]: row[1] for row in cursor.fetchall()}
            self.close()
            return {"funnel": funnel, "total": sum(funnel.values())}
        except Exception as e:
            print(f"[DB] Ошибка get_funnel_statistics: {e}")
            return {"funnel": {}, "total": 0}

    def get_executor_load(self, year=None, month=None):
        """Нагрузка на исполнителей: количество активных стадий"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            query = """
                SELECT e.full_name,
                       COUNT(CASE WHEN se.completed = 0 THEN 1 END) as active_stages
                FROM stage_executors se
                JOIN employees e ON se.executor_id = e.id
            """
            conditions = []
            params = []
            if year:
                conditions.append("strftime('%Y', se.assigned_date) = ?")
                params.append(str(year))
            if month:
                conditions.append("strftime('%m', se.assigned_date) = ?")
                params.append(f"{month:02d}")
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " GROUP BY e.id, e.full_name HAVING active_stages > 0 ORDER BY active_stages DESC LIMIT 15"
            cursor.execute(query, tuple(params))
            result = [
                {"name": row[0], "active_stages": row[1]}
                for row in cursor.fetchall()
            ]
            self.close()
            return result
        except Exception as e:
            print(f"[DB] Ошибка get_executor_load: {e}")
            return []
