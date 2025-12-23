# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,

                             QTableWidget, QTableWidgetItem, QPushButton,
                             QLabel, QHeaderView, QDoubleSpinBox, QComboBox,
                             QMessageBox, QWidget, QFormLayout, QFrame)
from PyQt5.QtCore import Qt
from database.db_manager import DatabaseManager
from config import CITIES
from ui.custom_title_bar import CustomTitleBar
from ui.custom_message_box import CustomMessageBox
from ui.custom_combobox import CustomComboBox

class RatesDialog(QDialog):
    """Диалог управления тарифами (только для Руководителя студии)"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.db = DatabaseManager()
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        print("\n" + "🔓 ОТКРЫТИЕ ДИАЛОГА ТАРИФОВ " + "="*40)
        
        self.init_ui()
        
        # ========== ЗАДЕРЖКА ПЕРЕД ЗАГРУЗКОЙ ==========
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(200, self.load_all_rates)
        # ==============================================
        
        print("="*60 + "\n")
    
    def init_ui(self):
        # Главный layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Контейнер с рамкой
        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
        """)
        
        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)
        
        # Title Bar
        title_bar = CustomTitleBar(self, '⚙️ Управление тарифами', simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)
        
        # Контент
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #FFFFFF;")
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Вкладки
        tabs = QTabWidget()
        
        # 1. Индивидуальные проекты
        individual_widget = self.create_individual_rates_tab()
        tabs.addTab(individual_widget, '  Индивидуальные (за м²)  ')
        
        # 2. Шаблонные проекты
        template_widget = self.create_template_rates_tab()
        tabs.addTab(template_widget, '  Шаблонные (диапазоны)  ')
        
        # 3. Авторский надзор
        supervision_widget = self.create_supervision_rates_tab()
        tabs.addTab(supervision_widget, '  Авторский надзор (за м²)  ')
        
        # 4. Замерщик
        surveyor_widget = self.create_surveyor_rates_tab()
        tabs.addTab(surveyor_widget, '  Замерщик (по городам)  ')
        
        layout.addWidget(tabs, 1)
        
        # Кнопка закрытия
        close_btn = QPushButton('Закрыть')
        close_btn.setStyleSheet('padding: 10px 30px; font-weight: bold;')
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)
        
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)
        
        self.setMinimumSize(1000, 700)
    
    def create_individual_rates_tab(self):
        """Тарифы для индивидуальных проектов (цена за м² по стадиям)"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        info = QLabel('Стоимость за 1 м² для каждой роли ПО СТАДИЯМ:')
        info.setStyleSheet('font-size: 12px; font-weight: bold; margin-bottom: 10px;')
        layout.addWidget(info)
        
        table = QTableWidget()
        table.setObjectName('individual_rates_table')
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(['Должность', 'Стадия', 'Цена за м² (₽)', 'Действия'])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # ========== УВЕЛИЧЕННАЯ ВЫСОТА СТРОК ==========
        table.verticalHeader().setDefaultSectionSize(30)  # 50px вместо 30px
        # ==============================================
        
        roles_stages = [
            ('Дизайнер', 'Стадия 2: концепция дизайна', 'Концепция дизайна'),
            ('Чертёжник', 'Стадия 1: планировочные решения', 'Планировочные решения'),
            ('Чертёжник', 'Стадия 3: рабочие чертежи', 'Рабочие чертежи (РЧ)'),
            ('СДП', None, 'Все стадии'),
            ('ГАП', None, 'Все стадии'),
            ('Старший менеджер проектов', None, 'Все проекты'),
            ('Менеджер', None, 'Все проекты'),
        ]
        
        table.setRowCount(len(roles_stages))
        
        for row, (role, stage, description) in enumerate(roles_stages):
            # Должность
            role_item = QTableWidgetItem(role)
            role_item.setFlags(role_item.flags() & ~Qt.ItemIsEditable)
            table.setItem(row, 0, role_item)
            
            # Стадия
            stage_display = stage if stage else '-'
            stage_item = QTableWidgetItem(stage_display)
            stage_item.setFlags(stage_item.flags() & ~Qt.ItemIsEditable)
            stage_item.setToolTip(description)
            table.setItem(row, 1, stage_item)
            
            # ========== ЦЕНА БЕЗ АВТОСОХРАНЕНИЯ ==========
            price_spin = QDoubleSpinBox()
            price_spin.setRange(0, 100000)
            price_spin.setDecimals(2)
            price_spin.setSuffix(' ₽')
            # ← УБРАЛИ valueChanged.connect()
            table.setCellWidget(row, 2, price_spin)
            # =============================================
            
            # ========== КНОПКА "СОХРАНИТЬ" (КОМПАКТНАЯ) ==========
            save_btn = QPushButton(' Сохранить ')
            save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27AE60;
                    color: white;
                    padding: 5px 8px;
                    border-radius: 3px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #229954; }
                QPushButton:pressed { background-color: #1E8449; }
            """)
            save_btn.clicked.connect(
                lambda checked, r=role, s=stage, p=price_spin: 
                    self.save_individual_rate(r, p.value(), s)
            )
            table.setCellWidget(row, 3, save_btn)
            # ====================================================
        
        layout.addWidget(table)
        
        hint = QLabel('💡 Для чертёжника указаны РАЗНЫЕ тарифы на 2 стадии')
        hint.setStyleSheet('color: #FF9800; font-size: 10px; font-style: italic; margin-top: 10px;')
        layout.addWidget(hint)
        
        widget.setLayout(layout)
        return widget
    
    def create_template_rates_tab(self):
        """Тарифы для шаблонных (таблица диапазонов)"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        info = QLabel('Стоимость в зависимости от площади (для каждой роли):')
        info.setStyleSheet('font-size: 12px; font-weight: bold;')
        layout.addWidget(info)
        
        # Выбор роли
        role_layout = QHBoxLayout()
        role_layout.addWidget(QLabel('Выберите должность:'))
        
        self.template_role_combo = CustomComboBox()
        self.template_role_combo.addItems(['Дизайнер', 'Чертёжник', 'ГАП'])
        self.template_role_combo.currentTextChanged.connect(self.load_template_ranges)
        role_layout.addWidget(self.template_role_combo)
        
        role_layout.addStretch()
        layout.addLayout(role_layout)
        
        # Таблица диапазонов
        table = QTableWidget()
        table.setObjectName('template_rates_table')
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels([
            'Площадь от (м²)', 'Площадь до (м²)', 'Стоимость (₽)', 'Действия'
        ])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setDefaultSectionSize(30)
        table.setRowCount(6)
        
        layout.addWidget(table)
        
        add_range_btn = QPushButton('+ Добавить диапазон')
        add_range_btn.setStyleSheet('padding: 8px; font-weight: bold;')
        add_range_btn.clicked.connect(self.add_template_range)
        layout.addWidget(add_range_btn)
        
        widget.setLayout(layout)
        
        # ========== КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ ==========
        # Сохраняем ссылку на widget для доступа из load_all_rates()
        self.template_widget = widget
        # =============================================
        
        return widget
    
    def create_supervision_rates_tab(self):
        """Тарифы для авторского надзора (за м² по стадиям)"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        info = QLabel('Стоимость за 1 м² для каждой стадии:')
        info.setStyleSheet('font-size: 12px; font-weight: bold;')
        layout.addWidget(info)
        
        table = QTableWidget()
        table.setObjectName('supervision_rates_table')
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(['Стадия', 'Исполнитель (₽/м²)', 'Старший менеджер (₽/м²)', 'Действия'])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # ========== УВЕЛИЧЕННАЯ ВЫСОТА ==========
        table.verticalHeader().setDefaultSectionSize(30)
        # ========================================
        
        stages = [
            'Стадия 1: Закупка керамогранита',
            'Стадия 2: Закупка сантехники',
            'Стадия 3: Закупка оборудования',
            'Стадия 4: Закупка дверей и окон',
            'Стадия 5: Закупка настенных материалов',
            'Стадия 6: Закупка напольных материалов',
            'Стадия 7: Лепного декора',
            'Стадия 8: Освещения',
            'Стадия 9: бытовой техники',
            'Стадия 10: Закупка заказной мебели',
            'Стадия 11: Закупка фабричной мебели',
            'Стадия 12: Закупка декора'
        ]
        
        table.setRowCount(len(stages))
        
        for row, stage in enumerate(stages):
            table.setItem(row, 0, QTableWidgetItem(stage))
            
            # Цена для исполнителя
            executor_spin = QDoubleSpinBox()
            executor_spin.setRange(0, 10000)
            executor_spin.setSuffix(' ₽/м²')
            table.setCellWidget(row, 1, executor_spin)
            
            # Цена для старшего менеджера
            manager_spin = QDoubleSpinBox()
            manager_spin.setRange(0, 10000)
            manager_spin.setSuffix(' ₽/м²')
            table.setCellWidget(row, 2, manager_spin)
            
            # ========== КОМПАКТНАЯ КНОПКА ==========
            save_btn = QPushButton(' Сохранить ')
            save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27AE60;
                    color: white;
                    padding: 5px 8px;
                    border-radius: 3px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #229954; }
            """)
            save_btn.clicked.connect(
                lambda checked, s=stage, e=executor_spin, m=manager_spin: 
                    self.save_supervision_rate(s, e.value(), m.value())
            )
            table.setCellWidget(row, 3, save_btn)
            # ========================================
        
        layout.addWidget(table)
        
        widget.setLayout(layout)
        return widget
    
    def create_surveyor_rates_tab(self):
        """Тарифы замерщика по городам"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        info = QLabel('Фиксированная стоимость замера по городам:')
        info.setStyleSheet('font-size: 12px; font-weight: bold;')
        layout.addWidget(info)
        
        table = QTableWidget()
        table.setObjectName('surveyor_rates_table')
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(['Город', 'Стоимость замера (₽)', 'Действия'])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # ========== УВЕЛИЧЕННАЯ ВЫСОТА ==========
        table.verticalHeader().setDefaultSectionSize(30)
        # ========================================
        
        table.setRowCount(len(CITIES))
        
        for row, city in enumerate(CITIES):
            table.setItem(row, 0, QTableWidgetItem(city))
            
            price_spin = QDoubleSpinBox()
            price_spin.setRange(0, 50000)
            price_spin.setSuffix(' ₽')
            table.setCellWidget(row, 1, price_spin)
            
            # ========== КОМПАКТНАЯ КНОПКА ==========
            save_btn = QPushButton(' Сохранить ')
            save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27AE60;
                    color: white;
                    padding: 5px 8px;
                    border-radius: 3px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #229954; }
            """)
            save_btn.clicked.connect(
                lambda checked, c=city, p=price_spin: 
                    self.save_surveyor_rate(c, p.value())
            )
            table.setCellWidget(row, 2, save_btn)
            # ========================================
        
        layout.addWidget(table)
        
        widget.setLayout(layout)
        return widget
    
    def load_all_rates(self):
        """Загрузка всех тарифов из БД"""
        try:
            print("\n" + "="*60)
            print("📥 ЗАГРУЗКА ТАРИФОВ ИЗ БД...")
            print("="*60)
            
            conn = self.db.connect()
            cursor = conn.cursor()
            
            # === 1. ИНДИВИДУАЛЬНЫЕ ===
            print("\n1️⃣ Загрузка ИНДИВИДУАЛЬНЫХ тарифов:")
            table_individual = self.findChild(QTableWidget, 'individual_rates_table')
            
            if table_individual:
                loaded_count = 0
                for row in range(table_individual.rowCount()):
                    role_item = table_individual.item(row, 0)
                    stage_item = table_individual.item(row, 1)
                    
                    if not role_item:
                        continue
                    
                    role = role_item.text()
                    stage = stage_item.text() if stage_item.text() != '-' else None
                    
                    # Ищем тариф в БД
                    if stage:
                        cursor.execute('''
                        SELECT rate_per_m2 FROM rates
                        WHERE project_type = 'Индивидуальный' AND role = ? AND stage_name = ?
                        ''', (role, stage))
                    else:
                        cursor.execute('''
                        SELECT rate_per_m2 FROM rates
                        WHERE project_type = 'Индивидуальный' AND role = ? AND stage_name IS NULL
                        ''', (role,))
                    
                    rate = cursor.fetchone()
                    
                    if rate and rate['rate_per_m2']:
                        spin = table_individual.cellWidget(row, 2)
                        if spin:
                            spin.blockSignals(True)  # Блокируем сигналы
                            spin.setValue(rate['rate_per_m2'])
                            spin.blockSignals(False)
                            
                            stage_text = f" ({stage})" if stage else ""
                            print(f"   ✓ {role}{stage_text}: {rate['rate_per_m2']:.2f} ₽/м²")
                            loaded_count += 1
                
                print(f"   Итого загружено: {loaded_count} тарифов")
            
            # === 2. ЗАМЕРЩИКИ ===
            print("\n2️⃣ Загрузка тарифов ЗАМЕРЩИКОВ:")
            table_surveyor = self.findChild(QTableWidget, 'surveyor_rates_table')
            
            if table_surveyor:
                loaded_count = 0
                for row in range(table_surveyor.rowCount()):
                    city_item = table_surveyor.item(row, 0)
                    
                    if not city_item:
                        continue
                    
                    city = city_item.text()
                    
                    cursor.execute('''
                    SELECT surveyor_price FROM rates
                    WHERE role = 'Замерщик' AND city = ?
                    ''', (city,))
                    
                    rate = cursor.fetchone()
                    
                    if rate and rate['surveyor_price']:
                        spin = table_surveyor.cellWidget(row, 1)
                        if spin:
                            spin.blockSignals(True)
                            spin.setValue(rate['surveyor_price'])
                            spin.blockSignals(False)
                            
                            print(f"   ✓ {city}: {rate['surveyor_price']:.2f} ₽")
                            loaded_count += 1
                
                print(f"   Итого загружено: {loaded_count} тарифов")
            
            # === 3. АВТОРСКИЙ НАДЗОР ===
            print("\n3️⃣ Загрузка тарифов АВТОРСКОГО НАДЗОРА:")
            table_supervision = self.findChild(QTableWidget, 'supervision_rates_table')
            
            if table_supervision:
                loaded_count = 0
                for row in range(table_supervision.rowCount()):
                    stage_item = table_supervision.item(row, 0)
                    
                    if not stage_item:
                        continue
                    
                    stage = stage_item.text()
                    
                    # ДАН
                    cursor.execute('''
                    SELECT rate_per_m2 FROM rates
                    WHERE project_type = 'Авторский надзор' AND role = 'ДАН' AND stage_name = ?
                    ''', (stage,))
                    
                    rate_dan = cursor.fetchone()
                    
                    if rate_dan and rate_dan['rate_per_m2']:
                        spin = table_supervision.cellWidget(row, 1)
                        if spin:
                            spin.blockSignals(True)
                            spin.setValue(rate_dan['rate_per_m2'])
                            spin.blockSignals(False)
                            loaded_count += 1
                    
                    # Старший менеджер
                    cursor.execute('''
                    SELECT rate_per_m2 FROM rates
                    WHERE project_type = 'Авторский надзор' 
                      AND role = 'Старший менеджер проектов' 
                      AND stage_name = ?
                    ''', (stage,))
                    
                    rate_manager = cursor.fetchone()
                    
                    if rate_manager and rate_manager['rate_per_m2']:
                        spin = table_supervision.cellWidget(row, 2)
                        if spin:
                            spin.blockSignals(True)
                            spin.setValue(rate_manager['rate_per_m2'])
                            spin.blockSignals(False)
                            
                    if rate_dan or rate_manager:
                        dan_price = rate_dan['rate_per_m2'] if rate_dan else 0
                        mgr_price = rate_manager['rate_per_m2'] if rate_manager else 0
                        print(f"   ✓ {stage}: ДАН={dan_price:.2f}, Менеджер={mgr_price:.2f} ₽/м²")
                
                print(f"   Итого загружено: {loaded_count} значений")
            
            self.db.close()
            
            # === 4. ШАБЛОННЫЕ (ВЫЗЫВАЕМ ОТДЕЛЬНО) ===
            print("\n4️⃣ Загрузка ШАБЛОННЫХ диапазонов:")
            print("   → Вызов load_template_ranges() для первой роли...")
            
            # ========== КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ ==========
            # Загружаем шаблонные для первой роли
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, self.load_template_ranges)
            # =============================================
            
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки тарифов: {e}")
            import traceback
            traceback.print_exc()
            
    def load_template_ranges(self):
        """Загрузка диапазонов для выбранной роли (Шаблонные)"""
        try:
            role = self.template_role_combo.currentText()
            
            print(f"[RATES] Загрузка диапазонов для роли: {role}")
            
            # Получаем таблицу
            table = self.findChild(QTableWidget, 'template_rates_table')
            
            if not table:
                print("⚠️ Таблица template_rates_table не найдена")
                return
            
            # ========== УСТАНАВЛИВАЕМ ВЫСОТУ СТРОК ==========
            table.verticalHeader().setDefaultSectionSize(30)
            # ================================================
            
            # Получаем тарифы из БД
            conn = self.db.connect()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT area_from, area_to, fixed_price
            FROM rates
            WHERE project_type = 'Шаблонный' AND role = ?
            ORDER BY area_from ASC
            ''', (role,))
            
            ranges = cursor.fetchall()
            self.db.close()
            
            # Очищаем таблицу
            table.setRowCount(0)
            
            # Заполняем существующими диапазонами
            if ranges:
                table.setRowCount(len(ranges))
                
                for row, rate in enumerate(ranges):
                    # Площадь от
                    from_spin = QDoubleSpinBox()
                    from_spin.setRange(0, 10000)
                    from_spin.setValue(rate['area_from'] or 0)
                    from_spin.setSuffix(' м²')
                    table.setCellWidget(row, 0, from_spin)
                    
                    # Площадь до
                    to_spin = QDoubleSpinBox()
                    to_spin.setRange(0, 10000)
                    to_spin.setValue(rate['area_to'] or 0)
                    to_spin.setSuffix(' м²')
                    table.setCellWidget(row, 1, to_spin)
                    
                    # Стоимость
                    price_spin = QDoubleSpinBox()
                    price_spin.setRange(0, 10000000)
                    price_spin.setValue(rate['fixed_price'] or 0)
                    price_spin.setSuffix(' ₽')
                    table.setCellWidget(row, 2, price_spin)
                    
                    # ========== КОМПАКТНАЯ КНОПКА ==========
                    save_btn = QPushButton(' Сохранить ')
                    save_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #27AE60;
                            color: white;
                            padding: 5px 8px;
                            border-radius: 3px;
                            font-size: 12px;
                            font-weight: bold;
                        }
                        QPushButton:hover { background-color: #229954; }
                    """)
                    save_btn.clicked.connect(
                        lambda checked, r=role, f=from_spin, t=to_spin, p=price_spin: 
                            self.save_template_range(r, f.value(), t.value(), p.value())
                    )
                    table.setCellWidget(row, 3, save_btn)
                    # ========================================
            else:
                # Пустая таблица - добавляем стартовые строки
                table.setRowCount(5)
                
                default_ranges = [
                    (0, 49, 0),
                    (50, 99, 0),
                    (100, 149, 0),
                    (150, 199, 0),
                    (200, 999999, 0)
                ]
                
                for row, (from_val, to_val, price) in enumerate(default_ranges):
                    from_spin = QDoubleSpinBox()
                    from_spin.setRange(0, 10000)
                    from_spin.setValue(from_val)
                    from_spin.setSuffix(' м²')
                    table.setCellWidget(row, 0, from_spin)
                    
                    to_spin = QDoubleSpinBox()
                    to_spin.setRange(0, 10000)
                    to_spin.setValue(to_val)
                    to_spin.setSuffix(' м²')
                    table.setCellWidget(row, 1, to_spin)
                    
                    price_spin = QDoubleSpinBox()
                    price_spin.setRange(0, 10000000)
                    price_spin.setValue(price)
                    price_spin.setSuffix(' ₽')
                    table.setCellWidget(row, 2, price_spin)
                    
                    save_btn = QPushButton('💾 Сохр.')
                    save_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #27AE60;
                            color: white;
                            padding: 5px 8px;
                            border-radius: 3px;
                            font-size: 10px;
                            font-weight: bold;
                        }
                        QPushButton:hover { background-color: #229954; }
                    """)
                    save_btn.clicked.connect(
                        lambda checked, r=role, f=from_spin, t=to_spin, p=price_spin: 
                            self.save_template_range(r, f.value(), t.value(), p.value())
                    )
                    table.setCellWidget(row, 3, save_btn)
            
            print(f"✓ Загружено диапазонов для {role}: {len(ranges)}")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки диапазонов: {e}")
            import traceback
            traceback.print_exc()

    def add_template_range(self):
        """Добавление нового диапазона"""
        try:
            table = self.findChild(QTableWidget, 'template_rates_table')
            
            if not table:
                return
            
            # Добавляем пустую строку
            row = table.rowCount()
            table.insertRow(row)
            
            # Площадь от
            from_spin = QDoubleSpinBox()
            from_spin.setRange(0, 10000)
            from_spin.setSuffix(' м²')
            table.setCellWidget(row, 0, from_spin)
            
            # Площадь до
            to_spin = QDoubleSpinBox()
            to_spin.setRange(0, 10000)
            to_spin.setSuffix(' м²')
            table.setCellWidget(row, 1, to_spin)
            
            # Стоимость
            price_spin = QDoubleSpinBox()
            price_spin.setRange(0, 10000000)
            price_spin.setSuffix(' ₽')
            table.setCellWidget(row, 2, price_spin)
            
            # Кнопка сохранения
            role = self.template_role_combo.currentText()
            save_btn = QPushButton(' Сохранить ')
            save_btn.clicked.connect(
                lambda checked, r=role, f=from_spin, t=to_spin, p=price_spin: 
                    self.save_template_range(r, f.value(), t.value(), p.value())
            )
            table.setCellWidget(row, 3, save_btn)
            
            print(f"✓ Добавлена новая строка диапазона")
            
        except Exception as e:
            print(f"❌ Ошибка добавления диапазона: {e}")

    def save_template_range(self, role, area_from, area_to, price):
        """Сохранение диапазона для шаблонного проекта"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            # Проверяем, существует ли уже такой диапазон
            cursor.execute('''
            SELECT id FROM rates
            WHERE project_type = 'Шаблонный' 
              AND role = ?
              AND area_from = ?
              AND area_to = ?
            ''', (role, area_from, area_to))
            
            existing = cursor.fetchone()
            
            if existing:
                # Обновляем
                cursor.execute('''
                UPDATE rates
                SET fixed_price = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                ''', (price, existing['id']))
                
                print(f"✓ Обновлен диапазон: {role} {area_from}-{area_to} м² = {price:.2f} ₽")
            else:
                # Создаем новый
                cursor.execute('''
                INSERT INTO rates 
                (project_type, role, area_from, area_to, fixed_price)
                VALUES ('Шаблонный', ?, ?, ?, ?)
                ''', (role, area_from, area_to, price))
                
                print(f"✓ Создан диапазон: {role} {area_from}-{area_to} м² = {price:.2f} ₽")
            
            conn.commit()
            self.db.close()
            
            CustomMessageBox(
                self, 
                'Успех', 
                f'Тариф сохранен:\n\n'
                f'{role}\n'
                f'{area_from:.0f} - {area_to:.0f} м² = {price:,.2f} ₽',
                'success'
            ).exec_()
            
        except Exception as e:
            print(f"❌ Ошибка сохранения диапазона: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось сохранить: {e}', 'error').exec_()

    def reset_rate(self, role):
        """Сброс тарифа (удаление из БД)"""
        reply = CustomMessageBox(
            self, 
            'Подтверждение', 
            f'Удалить тариф для роли "{role}"?',
            'question'
        ).exec_()
        
        if reply == QDialog.Accepted:
            try:
                conn = self.db.connect()
                cursor = conn.cursor()
                
                cursor.execute('''
                DELETE FROM rates
                WHERE project_type = 'Индивидуальный' AND role = ?
                ''', (role,))
                
                conn.commit()
                self.db.close()
                
                # Обнуляем поле в таблице
                table = self.findChild(QTableWidget, 'individual_rates_table')
                
                for row in range(table.rowCount()):
                    role_item = table.item(row, 0)
                    if role_item and role_item.text() == role:
                        spin = table.cellWidget(row, 1)
                        if spin:
                            spin.setValue(0)
                        break
                
                CustomMessageBox(self, 'Успех', f'Тариф для {role} удален', 'success').exec_()
                
            except Exception as e:
                print(f"❌ Ошибка сброса тарифа: {e}")
                CustomMessageBox(self, 'Ошибка', f'Не удалось удалить: {e}', 'error').exec_()

    def save_supervision_rate(self, stage_name, executor_rate, manager_rate):
        """Сохранение тарифов для авторского надзора"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            # Сохраняем тариф для исполнителя (ДАН)
            cursor.execute('''
            SELECT id FROM rates
            WHERE project_type = 'Авторский надзор' AND role = 'ДАН' AND stage_name = ?
            ''', (stage_name,))
            
            existing_executor = cursor.fetchone()
            
            if existing_executor:
                cursor.execute('''
                UPDATE rates
                SET rate_per_m2 = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                ''', (executor_rate, existing_executor['id']))
            else:
                cursor.execute('''
                INSERT INTO rates 
                (project_type, role, stage_name, rate_per_m2)
                VALUES ('Авторский надзор', 'ДАН', ?, ?)
                ''', (stage_name, executor_rate))
            
            # Сохраняем тариф для старшего менеджера
            cursor.execute('''
            SELECT id FROM rates
            WHERE project_type = 'Авторский надзор' 
              AND role = 'Старший менеджер проектов' 
              AND stage_name = ?
            ''', (stage_name,))
            
            existing_manager = cursor.fetchone()
            
            if existing_manager:
                cursor.execute('''
                UPDATE rates
                SET rate_per_m2 = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                ''', (manager_rate, existing_manager['id']))
            else:
                cursor.execute('''
                INSERT INTO rates 
                (project_type, role, stage_name, rate_per_m2)
                VALUES ('Авторский надзор', 'Старший менеджер проектов', ?, ?)
                ''', (stage_name, manager_rate))
            
            conn.commit()
            self.db.close()
            
            CustomMessageBox(
                self, 
                'Успех', 
                f'Тарифы для стадии "{stage_name}" сохранены:\n\n'
                f'ДАН: {executor_rate:.2f} ₽/м²\n'
                f'Старший менеджер: {manager_rate:.2f} ₽/м²',
                'success'
            ).exec_()
            
        except Exception as e:
            print(f"❌ Ошибка сохранения тарифов надзора: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось сохранить: {e}', 'error').exec_()
    
    def save_individual_rate(self, role, rate_per_m2, stage_name=None):
        """Сохранение тарифа для индивидуального проекта"""
        try:
            print(f"\n[SAVE] Сохранение тарифа:")
            print(f"   Роль: {role}")
            print(f"   Стадия: {stage_name}")
            print(f"   Цена: {rate_per_m2:.2f} ₽/м²")
            
            conn = self.db.connect()
            cursor = conn.cursor()
            
            # Для чертёжника учитываем стадию!
            if stage_name:
                cursor.execute('''
                SELECT id FROM rates
                WHERE project_type = 'Индивидуальный' 
                  AND role = ? 
                  AND stage_name = ?
                ''', (role, stage_name))
            else:
                cursor.execute('''
                SELECT id FROM rates
                WHERE project_type = 'Индивидуальный' 
                  AND role = ?
                  AND stage_name IS NULL
                ''', (role,))
            
            existing = cursor.fetchone()
            
            if existing:
                # Обновляем
                cursor.execute('''
                UPDATE rates
                SET rate_per_m2 = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                ''', (rate_per_m2, existing['id']))
                
                stage_text = f" ({stage_name})" if stage_name else ""
                print(f"   ✓ Обновлен тариф ID={existing['id']}: {role}{stage_text} = {rate_per_m2:.2f} ₽/м²")
            else:
                # Создаем новый
                cursor.execute('''
                INSERT INTO rates 
                (project_type, role, stage_name, rate_per_m2)
                VALUES ('Индивидуальный', ?, ?, ?)
                ''', (role, stage_name, rate_per_m2))
                
                new_id = cursor.lastrowid
                stage_text = f" ({stage_name})" if stage_name else ""
                print(f"   ✓ Создан тариф ID={new_id}: {role}{stage_text} = {rate_per_m2:.2f} ₽/м²")
            
            conn.commit()
            
            # ========== ПРОВЕРКА СОХРАНЕНИЯ ==========
            if stage_name:
                cursor.execute('''
                SELECT id, rate_per_m2 FROM rates
                WHERE project_type = 'Индивидуальный' AND role = ? AND stage_name = ?
                ''', (role, stage_name))
            else:
                cursor.execute('''
                SELECT id, rate_per_m2 FROM rates
                WHERE project_type = 'Индивидуальный' AND role = ? AND stage_name IS NULL
                ''', (role,))
            
            saved = cursor.fetchone()
            
            if saved:
                print(f"   ✅ ПРОВЕРКА: Тариф сохранен в БД (ID={saved['id']}, значение={saved['rate_per_m2']:.2f})")
            else:
                print(f"   ⚠️ ПРОВЕРКА ПРОВАЛЕНА: Тариф НЕ найден в БД после сохранения!")
            # =========================================
            
            self.db.close()
            
            stage_display = f'\n\nСтадия: {stage_name}' if stage_name else ''
            CustomMessageBox(
                self, 
                'Успех', 
                f'Тариф для {role} сохранен: {rate_per_m2:.2f} ₽/м²{stage_display}',
                'success'
            ).exec_()
            
        except Exception as e:
            print(f"❌ Ошибка сохранения тарифа: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось сохранить: {e}', 'error').exec_()
            
    def reset_individual_rate(self, role, stage_name=None):
        """Сброс тарифа с учетом стадии"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            if stage_name:
                cursor.execute('''
                DELETE FROM rates
                WHERE project_type = 'Индивидуальный' AND role = ? AND stage_name = ?
                ''', (role, stage_name))
            else:
                cursor.execute('''
                DELETE FROM rates
                WHERE project_type = 'Индивидуальный' AND role = ? AND stage_name IS NULL
                ''', (role,))
            
            conn.commit()
            self.db.close()
            
            # Обнуляем поле в таблице
            table = self.findChild(QTableWidget, 'individual_rates_table')
            
            for row in range(table.rowCount()):
                role_item = table.item(row, 0)
                stage_item = table.item(row, 1)
                
                if role_item and role_item.text() == role:
                    current_stage = stage_item.text() if stage_item.text() != '-' else None
                    
                    if (stage_name and current_stage == stage_name) or (not stage_name and not current_stage):
                        spin = table.cellWidget(row, 2)
                        if spin:
                            spin.setValue(0)
                        break
            
            CustomMessageBox(self, 'Успех', f'Тариф для {role} удален', 'success').exec_()
            
        except Exception as e:
            print(f"❌ Ошибка сброса тарифа: {e}")
            CustomMessageBox(self, 'Ошибка', f'Не удалось удалить: {e}', 'error').exec_()
         
    def save_surveyor_rate(self, city, price):
        """Сохранение тарифа замерщика"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            # Проверяем, существует ли уже тариф
            cursor.execute('''
            SELECT id FROM rates
            WHERE role = 'Замерщик' AND city = ?
            ''', (city,))
            
            existing = cursor.fetchone()
            
            if existing:
                # Обновляем
                cursor.execute('''
                UPDATE rates
                SET surveyor_price = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                ''', (price, existing['id']))
                
                print(f"✓ Обновлен тариф замера: {city} = {price:.2f} ₽")
            else:
                # ========== ИСПРАВЛЕНИЕ: УКАЗЫВАЕМ project_type = NULL ==========
                cursor.execute('''
                INSERT INTO rates 
                (project_type, role, city, surveyor_price)
                VALUES (NULL, 'Замерщик', ?, ?)
                ''', (city, price))
                # ================================================================
                
                print(f"✓ Создан тариф замера: {city} = {price:.2f} ₽")
            
            conn.commit()
            self.db.close()
            
            CustomMessageBox(
                self, 
                'Успех', 
                f'Тариф замера в городе {city}: {price:.2f} ₽',
                'success'
            ).exec_()
            
        except Exception as e:
            print(f"❌ Ошибка сохранения тарифа замера: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось сохранить: {e}', 'error').exec_()
            
    def showEvent(self, event):
        """Центрирование при первом показе"""
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()

    def center_on_screen(self):
        """Центрирование относительно родительского окна"""
        from utils.dialog_helpers import center_dialog_on_parent
        center_dialog_on_parent(self)

        
