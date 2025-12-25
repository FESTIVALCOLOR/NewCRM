# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,

                             QGroupBox, QGridLayout, QScrollArea, QSizePolicy)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont
from PyQt5.QtSvg import QSvgWidget
from database.db_manager import DatabaseManager
from utils.resource_path import resource_path
import os

class DashboardTab(QWidget):
    """Главная страница со сводной статистикой"""

    def __init__(self, employee, api_client=None):
        super().__init__()
        self.employee = employee
        self.api_client = api_client  # Клиент для работы с API (многопользовательский режим)
        self.db = DatabaseManager()
        self.init_ui()
        self.load_statistics()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        header_layout = QHBoxLayout()
        
        header = QLabel('Сводная статистика')
        header.setStyleSheet('font-size: 20px; font-weight: bold; color: #2C3E50;')
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # Информация о пользователе
        user_info = QLabel(f'Пользователь: {self.employee["full_name"]} | Должность: {self.employee["position"]}')
        user_info.setStyleSheet('font-size: 12px; color: #7F8C8D; padding: 5px;')
        header_layout.addWidget(user_info)
        
        main_layout.addLayout(header_layout)
        
        # Скролл для карточек
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #F8F9FA; }")
        
        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(10, 10, 10, 10)
        
        # ========== СЕТКА КАРТОЧЕК (2 ряда × 3 колонки) ==========
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        
        # Ряд 1: Количество заказов
        self.individual_orders_card = self.create_stat_card(
            'individual_orders',
            'Индивидуальные проекты',
            '0',
            'resources/icons/clipboard1.svg',
            '#E8F4F8',
            '#3498DB'
        )
        grid_layout.addWidget(self.individual_orders_card, 0, 0)

        self.template_orders_card = self.create_stat_card(
            'template_orders',
            'Шаблонные проекты',
            '0',
            'resources/icons/clipboard2.svg',
            '#FFF3E0',
            '#F39C12'
        )
        grid_layout.addWidget(self.template_orders_card, 0, 1)

        self.supervision_orders_card = self.create_stat_card(
            'supervision_orders',
            'Авторский надзор',
            '0',
            'resources/icons/clipboard3.svg',
            '#E8F5E9',
            '#27AE60'
        )
        grid_layout.addWidget(self.supervision_orders_card, 0, 2)

        # Ряд 2: Общая площадь
        self.individual_area_card = self.create_stat_card(
            'individual_area',
            'Площадь индивидуальных',
            '0 м²',
            'resources/icons/codepen1.svg',
            '#F3E5F5',
            '#9B59B6'
        )
        grid_layout.addWidget(self.individual_area_card, 1, 0)

        self.template_area_card = self.create_stat_card(
            'template_area',
            'Площадь шаблонных',
            '0 м²',
            'resources/icons/codepen2.svg',
            '#FFEBEE',
            '#E74C3C'
        )
        grid_layout.addWidget(self.template_area_card, 1, 1)

        self.supervision_area_card = self.create_stat_card(
            'supervision_area',
            'Площадь надзора',
            '0 м²',
            'resources/icons/codepen3.svg',
            '#E0F2F1',
            '#1ABC9C'
        )
        grid_layout.addWidget(self.supervision_area_card, 1, 2)
        
        # Настраиваем растягивание колонок
        for col in range(3):
            grid_layout.setColumnStretch(col, 1)
        
        content_layout.addLayout(grid_layout)
        # =========================================================
        
        content_layout.addStretch()
        
        content.setLayout(content_layout)
        scroll.setWidget(content)
        
        main_layout.addWidget(scroll, 1)
        
        self.setLayout(main_layout)
    
    def create_stat_card(self, object_name, title, value, icon_path, bg_color, border_color):
        """Создание карточки статистики"""
        card = QGroupBox()
        card.setObjectName(object_name)

        # ========== АДАПТИВНАЯ КВАДРАТНОСТЬ ==========
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card.setMinimumSize(200, 200)  # Минимальный размер

        # Переопределяем метод для поддержания квадратности
        def resizeEvent(event):
            width = event.size().width()
            card.setMinimumHeight(width)  # Высота = Ширине
            QGroupBox.resizeEvent(card, event)

        card.resizeEvent = resizeEvent
        # =============================================

        card.setStyleSheet(f"""
            QGroupBox {{
                background-color: {bg_color};
                border: 3px solid {border_color};
                border-radius: 12px;
                padding: 20px;
            }}
            QGroupBox:hover {{
                border: 3px solid {border_color};
                background-color: {self.lighter_color(bg_color)};
                transform: scale(1.02);
            }}
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignCenter)

        # Иконка SVG
        full_icon_path = resource_path(icon_path)
        if os.path.exists(full_icon_path):
            icon_widget = QSvgWidget(full_icon_path)
            icon_widget.setFixedSize(64, 64)
            layout.addWidget(icon_widget, 0, Qt.AlignCenter)
        else:
            # Fallback на текстовую иконку
            icon_label = QLabel('📊')
            icon_label.setStyleSheet('font-size: 48px; background-color: transparent;')
            icon_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon_label)
        
        # Заголовок
        title_label = QLabel(title)
        title_label.setStyleSheet(f'font-size: 13px; color: {border_color}; font-weight: bold; background-color: transparent;')
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Значение
        value_label = QLabel(value)
        value_label.setObjectName('value_label')
        value_label.setStyleSheet('font-size: 36px; font-weight: bold; color: #2C3E50; background-color: transparent;')
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)
        
        card.setLayout(layout)
        return card
    
    def lighter_color(self, hex_color):
        """Получение более светлого оттенка"""
        # Простой способ - можно оставить тот же цвет или сделать чуть светлее
        return hex_color
    
    def load_statistics(self):
        """Загрузка статистики за все время"""
        try:
            if self.api_client:
                # Многопользовательский режим - загружаем из API
                stats = self.calculate_api_statistics()
            else:
                # Локальный режим - загружаем из локальной БД
                stats = self.db.get_dashboard_statistics()

            # Обновляем карточки заказов
            self.update_card_value('individual_orders', str(stats['individual_orders']))
            self.update_card_value('template_orders', str(stats['template_orders']))
            self.update_card_value('supervision_orders', str(stats['supervision_orders']))

            # Обновляем карточки площади
            self.update_card_value('individual_area', f"{stats['individual_area']:,.0f} м²")
            self.update_card_value('template_area', f"{stats['template_area']:,.0f} м²")
            self.update_card_value('supervision_area', f"{stats['supervision_area']:,.0f} м²")

            print("✓ Статистика dashboard загружена")

        except Exception as e:
            print(f"❌ Ошибка загрузки статистики dashboard: {e}")
            import traceback
            traceback.print_exc()

    def calculate_api_statistics(self):
        """Рассчитать статистику из данных API"""
        try:
            # Получаем все договоры с сервера
            contracts = self.api_client.get_contracts(limit=1000)

            # Инициализируем счетчики
            stats = {
                'individual_orders': 0,
                'template_orders': 0,
                'supervision_orders': 0,
                'individual_area': 0.0,
                'template_area': 0.0,
                'supervision_area': 0.0
            }

            # Подсчитываем статистику
            for contract in contracts:
                project_type = contract.get('project_type', '')
                area = float(contract.get('area', 0) or 0)
                supervision = contract.get('supervision', False)

                if project_type == 'Индивидуальный':
                    stats['individual_orders'] += 1
                    stats['individual_area'] += area
                elif project_type == 'Шаблонный':
                    stats['template_orders'] += 1
                    stats['template_area'] += area

                # Авторский надзор подсчитывается отдельно
                if supervision:
                    stats['supervision_orders'] += 1
                    stats['supervision_area'] += area

            return stats

        except Exception as e:
            print(f"❌ Ошибка расчета статистики из API: {e}")
            import traceback
            traceback.print_exc()
            # Возвращаем нулевую статистику в случае ошибки
            return {
                'individual_orders': 0,
                'template_orders': 0,
                'supervision_orders': 0,
                'individual_area': 0.0,
                'template_area': 0.0,
                'supervision_area': 0.0
            }
    
    def update_card_value(self, card_name, value):
        """Обновление значения карточки"""
        card = self.findChild(QGroupBox, card_name)
        if card:
            value_label = card.findChild(QLabel, 'value_label')
            if value_label:
                value_label.setText(value)
