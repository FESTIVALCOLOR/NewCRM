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

    def __init__(self, parent, api_client=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.api_client = api_client
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        print("\n" + "ОТКРЫТИЕ ДИАЛОГА ТАРИФОВ " + "="*40)
        
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
        title_bar = CustomTitleBar(self, 'Управление тарифами', simple_mode=True)
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

        # Стили для таблиц и полей ввода
        tabs.setStyleSheet("""
            /* Таблицы */
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #d9d9d9;
                border-radius: 8px;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #d9d9d9;
                font-weight: bold;
            }

            /* Поля ввода цен (QDoubleSpinBox) */
            QDoubleSpinBox {
                padding: 6px 8px;
                max-height: 28px;
                min-height: 28px;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            QDoubleSpinBox:hover {
                border-color: #c0c0c0;
            }
            QDoubleSpinBox:focus {
                border-color: #ffd93c;
            }

            /* Кнопки стрелок в QDoubleSpinBox */
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 16px;
                border: none;
                background-color: transparent;
            }
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #f0f0f0;
            }
        """)
        
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
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
                max-height: 36px;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #D0D0D0; }
            QPushButton:pressed { background-color: #C0C0C0; }
        """)
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
        table.verticalHeader().setDefaultSectionSize(36)  # Стандартная высота строк
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
            save_btn.setFixedHeight(28)
            save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffd93c;
                    color: #333333;
                    padding: 0px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                    font-weight: bold;
                    max-height: 28px;
                    min-height: 28px;
                }
                QPushButton:hover { background-color: #f0c929; }
                QPushButton:pressed { background-color: #e0b919; }
            """)
            save_btn.clicked.connect(
                lambda checked, r=role, s=stage, p=price_spin: 
                    self.save_individual_rate(r, p.value(), s)
            )
            table.setCellWidget(row, 3, save_btn)
            # ====================================================
        
        layout.addWidget(table)
        
        hint = QLabel('Для чертёжника указаны РАЗНЫЕ тарифы на 2 стадии')
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
        table.verticalHeader().setDefaultSectionSize(36)
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
        table.verticalHeader().setDefaultSectionSize(36)
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
        table.verticalHeader().setDefaultSectionSize(36)
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

    def _load_rates_from_data(self, rates_data: list):
        """Загрузка тарифов из данных API"""
        try:
            # === 1. ИНДИВИДУАЛЬНЫЕ ===
            print("\n1⃣ Загрузка ИНДИВИДУАЛЬНЫХ тарифов из API:")
            table_individual = self.findChild(QTableWidget, 'individual_rates_table')
            individual_count = 0

            if table_individual:
                for row in range(table_individual.rowCount()):
                    role_item = table_individual.item(row, 0)
                    stage_item = table_individual.item(row, 1)

                    if not role_item:
                        continue

                    role = role_item.text()
                    stage = stage_item.text() if stage_item and stage_item.text() != '-' else None

                    # Ищем тариф в данных API
                    for rate in rates_data:
                        if (rate.get('project_type') == 'Индивидуальный' and
                            rate.get('role') == role):
                            rate_stage = rate.get('stage_name')
                            if (stage is None and rate_stage is None) or (stage == rate_stage):
                                rate_value = rate.get('rate_per_m2', 0)
                                if rate_value:
                                    spin = table_individual.cellWidget(row, 2)
                                    if spin:
                                        spin.blockSignals(True)
                                        spin.setValue(float(rate_value))
                                        spin.blockSignals(False)
                                        individual_count += 1
                                break

            print(f"   Итого загружено: {individual_count} тарифов")

            # === 2. ЗАМЕРЩИКИ ===
            print("\n2⃣ Загрузка тарифов ЗАМЕРЩИКОВ из API:")
            table_surveyor = self.findChild(QTableWidget, 'surveyor_rates_table')
            surveyor_count = 0

            if table_surveyor:
                for rate in rates_data:
                    if rate.get('role') == 'Замерщик' and rate.get('city'):
                        city = rate.get('city')
                        price = rate.get('surveyor_price', 0)

                        for row in range(table_surveyor.rowCount()):
                            city_item = table_surveyor.item(row, 0)
                            if city_item and city_item.text() == city:
                                spin = table_surveyor.cellWidget(row, 1)
                                if spin and price:
                                    spin.blockSignals(True)
                                    spin.setValue(float(price))
                                    spin.blockSignals(False)
                                    surveyor_count += 1
                                break

            print(f"   Итого загружено: {surveyor_count} тарифов")

            # === 3. АВТОРСКИЙ НАДЗОР ===
            print("\n3⃣ Загрузка тарифов АВТОРСКОГО НАДЗОРА из API:")
            supervision_count = 0

            for rate in rates_data:
                if rate.get('project_type') == 'Авторский надзор':
                    executor_rate = rate.get('executor_rate')
                    manager_rate = rate.get('manager_rate')

                    if executor_rate:
                        spin = self.findChild(QDoubleSpinBox, 'supervision_executor_rate')
                        if spin:
                            spin.blockSignals(True)
                            spin.setValue(float(executor_rate))
                            spin.blockSignals(False)
                            supervision_count += 1

                    if manager_rate:
                        spin = self.findChild(QDoubleSpinBox, 'supervision_manager_rate')
                        if spin:
                            spin.blockSignals(True)
                            spin.setValue(float(manager_rate))
                            spin.blockSignals(False)
                            supervision_count += 1
                    break

            print(f"   Итого загружено: {supervision_count} значений")

            # === 4. ШАБЛОННЫЕ ===
            print("\n4⃣ Загрузка ШАБЛОННЫХ диапазонов:")
            print("   → Вызов load_template_ranges() для первой роли...")
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, self.load_template_ranges)

            print("="*60 + "\n")

        except Exception as e:
            print(f"Ошибка загрузки тарифов из API: {e}")
            import traceback
            traceback.print_exc()

    def load_all_rates(self):
        """Загрузка всех тарифов из БД"""
        try:
            print("\n" + "="*60)
            print("[RATES] ЗАГРУЗКА ТАРИФОВ...")
            print("="*60)

            if self.api_client:
                try:
                    rates_data = self.api_client.get_rates()
                    self._load_rates_from_data(rates_data)
                    return
                except Exception as e:
                    print(f"[WARN] Ошибка API загрузки тарифов: {e}, fallback на локальную БД")

            conn = self.db.connect()
            cursor = conn.cursor()
            
            # === 1. ИНДИВИДУАЛЬНЫЕ ===
            print("\n1⃣ Загрузка ИНДИВИДУАЛЬНЫХ тарифов:")
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
                            print(f"   {role}{stage_text}: {rate['rate_per_m2']:.2f} ₽/м²")
                            loaded_count += 1
                
                print(f"   Итого загружено: {loaded_count} тарифов")
            
            # === 2. ЗАМЕРЩИКИ ===
            print("\n2⃣ Загрузка тарифов ЗАМЕРЩИКОВ:")
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
                            
                            print(f"   {city}: {rate['surveyor_price']:.2f} ₽")
                            loaded_count += 1
                
                print(f"   Итого загружено: {loaded_count} тарифов")
            
            # === 3. АВТОРСКИЙ НАДЗОР ===
            print("\n3⃣ Загрузка тарифов АВТОРСКОГО НАДЗОРА:")
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
                        print(f"   {stage}: ДАН={dan_price:.2f}, Менеджер={mgr_price:.2f} ₽/м²")
                
                print(f"   Итого загружено: {loaded_count} значений")
            
            self.db.close()
            
            # === 4. ШАБЛОННЫЕ (ВЫЗЫВАЕМ ОТДЕЛЬНО) ===
            print("\n4⃣ Загрузка ШАБЛОННЫХ диапазонов:")
            print("   → Вызов load_template_ranges() для первой роли...")
            
            # ========== КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ ==========
            # Загружаем шаблонные для первой роли
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, self.load_template_ranges)
            # =============================================
            
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"Ошибка загрузки тарифов: {e}")
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
                print("[WARN] Таблица template_rates_table не найдена")
                return

            # УСТАНАВЛИВАЕМ ВЫСОТУ СТРОК
            table.verticalHeader().setDefaultSectionSize(36)

            # Получаем тарифы из БД или API
            if self.api_client:
                try:
                    ranges = self.api_client.get_template_rates(role)
                except Exception as e:
                    print(f"[WARN] Ошибка API загрузки диапазонов: {e}")
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
            else:
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
                    
                    save_btn = QPushButton('Сохр.')
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
            
            print(f"Загружено диапазонов для {role}: {len(ranges)}")
            
        except Exception as e:
            print(f"Ошибка загрузки диапазонов: {e}")
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
            
            print(f"Добавлена новая строка диапазона")
            
        except Exception as e:
            print(f"Ошибка добавления диапазона: {e}")

    def save_template_range(self, role, area_from, area_to, price):
        """Сохранение диапазона для шаблонного проекта"""
        try:
            if self.api_client:
                try:
                    self.api_client.save_template_rate(role, area_from, area_to, price)
                    print(f"[API] Сохранен диапазон: {role} {area_from}-{area_to} м² = {price:.2f} рублей")
                    CustomMessageBox(
                        self,
                        'Успех',
                        f'Тариф сохранен:\n\n'
                        f'{role}\n'
                        f'{area_from:.0f} - {area_to:.0f} м² = {price:,.2f} рублей',
                        'success'
                    ).exec_()
                    return
                except Exception as e:
                    print(f"[WARN] Ошибка API сохранения: {e}, fallback на локальную БД")

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
                
                print(f"Обновлен диапазон: {role} {area_from}-{area_to} м² = {price:.2f} ₽")
            else:
                # Создаем новый
                cursor.execute('''
                INSERT INTO rates 
                (project_type, role, area_from, area_to, fixed_price)
                VALUES ('Шаблонный', ?, ?, ?, ?)
                ''', (role, area_from, area_to, price))
                
                print(f"Создан диапазон: {role} {area_from}-{area_to} м² = {price:.2f} ₽")
            
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
            print(f"Ошибка сохранения диапазона: {e}")
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
                if self.api_client:
                    try:
                        self.api_client.delete_individual_rate(role)
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
                        return
                    except Exception as e:
                        print(f"[WARN] Ошибка API удаления: {e}, fallback на локальную БД")

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
                print(f"Ошибка сброса тарифа: {e}")
                CustomMessageBox(self, 'Ошибка', f'Не удалось удалить: {e}', 'error').exec_()

    def save_supervision_rate(self, stage_name, executor_rate, manager_rate):
        """Сохранение тарифов для авторского надзора"""
        try:
            if self.api_client:
                try:
                    self.api_client.save_supervision_rate(stage_name, executor_rate, manager_rate)
                    CustomMessageBox(
                        self,
                        'Успех',
                        f'Тарифы для стадии "{stage_name}" сохранены:\n\n'
                        f'ДАН: {executor_rate:.2f} руб/м²\n'
                        f'Старший менеджер: {manager_rate:.2f} руб/м²',
                        'success'
                    ).exec_()
                    return
                except Exception as e:
                    print(f"[WARN] Ошибка API сохранения тарифа надзора: {e}, fallback на локальную БД")

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
            print(f"Ошибка сохранения тарифов надзора: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось сохранить: {e}', 'error').exec_()
    
    def save_individual_rate(self, role, rate_per_m2, stage_name=None):
        """Сохранение тарифа для индивидуального проекта"""
        try:
            print(f"\n[SAVE] Сохранение тарифа:")
            print(f"   Роль: {role}")
            print(f"   Стадия: {stage_name}")
            print(f"   Цена: {rate_per_m2:.2f} руб/м²")

            if self.api_client:
                try:
                    self.api_client.save_individual_rate(role, rate_per_m2, stage_name)
                    stage_display = f'\n\nСтадия: {stage_name}' if stage_name else ''
                    CustomMessageBox(
                        self,
                        'Успех',
                        f'Тариф для {role} сохранен: {rate_per_m2:.2f} руб/м²{stage_display}',
                        'success'
                    ).exec_()
                    return
                except Exception as e:
                    print(f"[WARN] Ошибка API сохранения: {e}, fallback на локальную БД")

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
                print(f"   Обновлен тариф ID={existing['id']}: {role}{stage_text} = {rate_per_m2:.2f} ₽/м²")
            else:
                # Создаем новый
                cursor.execute('''
                INSERT INTO rates 
                (project_type, role, stage_name, rate_per_m2)
                VALUES ('Индивидуальный', ?, ?, ?)
                ''', (role, stage_name, rate_per_m2))
                
                new_id = cursor.lastrowid
                stage_text = f" ({stage_name})" if stage_name else ""
                print(f"   Создан тариф ID={new_id}: {role}{stage_text} = {rate_per_m2:.2f} ₽/м²")
            
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
                print(f"   ПРОВЕРКА: Тариф сохранен в БД (ID={saved['id']}, значение={saved['rate_per_m2']:.2f})")
            else:
                print(f"   [WARN] ПРОВЕРКА ПРОВАЛЕНА: Тариф НЕ найден в БД после сохранения!")
            # =========================================
            
            self.db.close()

            stage_display = f'\n\nСтадия: {stage_name}' if stage_name else ''
            CustomMessageBox(
                self,
                'Успех',
                f'Тариф для {role} сохранен: {rate_per_m2:.2f} ₽/м²{stage_display}',
                'success'
            ).exec_()

            # НОВОЕ: Предложение пересчитать выплаты
            self._offer_recalculate_payments(role)

        except Exception as e:
            print(f"Ошибка сохранения тарифа: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось сохранить: {e}', 'error').exec_()
            
    def reset_individual_rate(self, role, stage_name=None):
        """Сброс тарифа с учетом стадии"""
        try:
            if self.api_client:
                try:
                    self.api_client.delete_individual_rate(role, stage_name)
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
                    return
                except Exception as e:
                    print(f"[WARN] Ошибка API удаления: {e}, fallback на локальную БД")

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
            print(f"Ошибка сброса тарифа: {e}")
            CustomMessageBox(self, 'Ошибка', f'Не удалось удалить: {e}', 'error').exec_()

    def _offer_recalculate_payments(self, role: str = None):
        """Предложение пересчитать выплаты после изменения тарифа"""
        try:
            if not self.api_client:
                return

            reply = CustomQuestionBox(
                self,
                'Пересчет выплат',
                f'Тариф изменен.\n\n'
                f'Пересчитать существующие выплаты по новому тарифу?\n\n'
                f'Это обновит суммы всех незакрытых выплат.'
            ).exec_()

            if reply == QDialog.Accepted:
                try:
                    result = self.api_client.recalculate_payments(role=role)
                    if result.get('status') == 'success':
                        updated = result.get('updated', 0)
                        total = result.get('total', 0)
                        CustomMessageBox(
                            self,
                            'Пересчет завершен',
                            f'Обновлено выплат: {updated} из {total}',
                            'success'
                        ).exec_()
                    else:
                        CustomMessageBox(
                            self,
                            'Ошибка',
                            f'Ошибка пересчета: {result.get("error", "Неизвестная ошибка")}',
                            'error'
                        ).exec_()
                except Exception as e:
                    print(f"[ERROR] Ошибка пересчета выплат: {e}")
                    CustomMessageBox(
                        self,
                        'Ошибка',
                        f'Не удалось пересчитать выплаты:\n{str(e)}',
                        'error'
                    ).exec_()
        except Exception as e:
            print(f"[ERROR] Ошибка в _offer_recalculate_payments: {e}")

    def save_surveyor_rate(self, city, price):
        """Сохранение тарифа замерщика"""
        try:
            if self.api_client:
                try:
                    self.api_client.save_surveyor_rate(city, price)
                    CustomMessageBox(
                        self,
                        'Успех',
                        f'Тариф замера в городе {city}: {price:.2f} рублей',
                        'success'
                    ).exec_()
                    return
                except Exception as e:
                    print(f"[WARN] Ошибка API сохранения тарифа замера: {e}, fallback на локальную БД")

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
                
                print(f"Обновлен тариф замера: {city} = {price:.2f} ₽")
            else:
                # ========== ИСПРАВЛЕНИЕ: УКАЗЫВАЕМ project_type = NULL ==========
                cursor.execute('''
                INSERT INTO rates 
                (project_type, role, city, surveyor_price)
                VALUES (NULL, 'Замерщик', ?, ?)
                ''', (city, price))
                # ================================================================
                
                print(f"Создан тариф замера: {city} = {price:.2f} ₽")
            
            conn.commit()
            self.db.close()
            
            CustomMessageBox(
                self, 
                'Успех', 
                f'Тариф замера в городе {city}: {price:.2f} ₽',
                'success'
            ).exec_()
            
        except Exception as e:
            print(f"Ошибка сохранения тарифа замера: {e}")
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

        
