# -*- coding: utf-8 -*-
"""
Диалог администрирования — единая точка управления системой.
Вкладки: Права доступа, Настройка чата, Настройка норма дней, Тарифы.
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QFrame, QPushButton, QLabel,
)
from PyQt5.QtCore import Qt

_TAB_STYLE = """
    QTabWidget::pane {
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        background-color: #ffffff;
        top: -1px;
    }
    QTabBar::tab {
        background-color: #f5f5f5;
        border: 1px solid #e0e0e0;
        border-bottom: none;
        padding: 8px 16px;
        font-size: 13px;
        margin-right: 2px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
    }
    QTabBar::tab:selected {
        background-color: #ffffff;
        font-weight: 600;
        border-bottom: 2px solid #ffd93c;
    }
    QTabBar::tab:hover:!selected { background-color: #fafafa; }
"""


class AdminDialog(QDialog):
    """Диалог администрирования (только для Руководителя студии)"""

    def __init__(self, parent, api_client=None, data_access=None, employee=None):
        super().__init__(parent)
        self.api_client = api_client
        self.data_access = data_access
        self.employee = employee or {}

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(1250, 750)
        self.setMaximumSize(1500, 900)

        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 10px;
            }
        """)
        frame_layout = QVBoxLayout(border_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        from ui.custom_title_bar import CustomTitleBar
        title_bar = CustomTitleBar(self, "Администрирование", simple_mode=True)
        frame_layout.addWidget(title_bar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 8, 16, 16)
        content_layout.setSpacing(10)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(_TAB_STYLE)

        # --- Вкладка 1: Права доступа ---
        self._tab_permissions = self._create_permissions_tab()
        self._tabs.addTab(self._tab_permissions, "Права доступа")

        # --- Вкладка 2: Настройка чата ---
        self._tab_chat = self._create_chat_tab()
        self._tabs.addTab(self._tab_chat, "Настройка чата")

        # --- Вкладка 3: Настройка норма дней ---
        self._tab_norm_days = self._create_norm_days_tab()
        self._tabs.addTab(self._tab_norm_days, "Настройка норма дней")

        # --- Вкладка 4: Тарифы ---
        self._tab_rates = self._create_rates_tab()
        self._tabs.addTab(self._tab_rates, "Тарифы")

        # --- Вкладка 5: Агенты и города ---
        self._tab_agents_cities = self._create_agents_cities_tab()
        self._tabs.addTab(self._tab_agents_cities, "Агенты и города")

        # --- Вкладка 6: Уведомления ---
        self._tab_notifications = self._create_notifications_tab()
        self._tabs.addTab(self._tab_notifications, "Уведомления")

        content_layout.addWidget(self._tabs)

        # Нижняя панель
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)
        bottom_row.addStretch()

        close_btn = QPushButton("Закрыть")
        close_btn.setFixedHeight(38)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                padding: 0 24px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #f5f5f5; }
        """)
        close_btn.clicked.connect(self.close)
        bottom_row.addWidget(close_btn)

        content_layout.addLayout(bottom_row)
        frame_layout.addWidget(content)
        root.addWidget(border_frame)

    # ================================================================
    # Вкладка: Права доступа
    # ================================================================

    def _create_permissions_tab(self):
        """Заглушка — будет заполнена в Фазе 1"""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Загрузка..."))
        # Ленивая загрузка при первом переключении на вкладку
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self._init_permissions_widget)
        return w

    def _init_permissions_widget(self):
        """Инициализация виджета матрицы прав доступа"""
        try:
            from ui.permissions_matrix_widget import PermissionsMatrixWidget
            widget = PermissionsMatrixWidget(
                parent=self._tab_permissions,
                api_client=self.api_client,
            )
            layout = self._tab_permissions.layout()
            # Убрать заглушку
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            layout.addWidget(widget)
        except Exception as e:
            print(f"[WARN] Не удалось загрузить PermissionsMatrixWidget: {e}")
            lbl = self._tab_permissions.findChild(QLabel)
            if lbl:
                lbl.setText(f"Ошибка загрузки: {e}")

    # ================================================================
    # Вкладка: Настройка чата
    # ================================================================

    def _create_chat_tab(self):
        """Встраиваем MessengerSettingsWidget"""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Загрузка..."))
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(150, self._init_chat_widget)
        return w

    def _init_chat_widget(self):
        """Инициализация виджета настроек чата"""
        try:
            from ui.messenger_admin_dialog import MessengerSettingsWidget
            widget = MessengerSettingsWidget(
                parent=self._tab_chat,
                api_client=self.api_client,
                data_access=self.data_access,
                employee=self.employee,
            )
            layout = self._tab_chat.layout()
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            layout.addWidget(widget)
        except Exception as e:
            print(f"[WARN] Не удалось загрузить MessengerSettingsWidget: {e}")
            lbl = self._tab_chat.findChild(QLabel)
            if lbl:
                lbl.setText(f"Ошибка загрузки: {e}")

    # ================================================================
    # Вкладка: Настройка норма дней
    # ================================================================

    def _create_norm_days_tab(self):
        """Заглушка — будет заполнена в Фазе 3"""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Загрузка..."))
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(200, self._init_norm_days_widget)
        return w

    def _init_norm_days_widget(self):
        """Инициализация виджета настроек нормо-дней"""
        try:
            from ui.norm_days_settings_widget import NormDaysSettingsWidget
            widget = NormDaysSettingsWidget(
                parent=self._tab_norm_days,
                api_client=self.api_client,
            )
            layout = self._tab_norm_days.layout()
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            layout.addWidget(widget)
        except Exception as e:
            print(f"[WARN] Не удалось загрузить NormDaysSettingsWidget: {e}")
            lbl = self._tab_norm_days.findChild(QLabel)
            if lbl:
                lbl.setText(f"Ошибка загрузки: {e}")

    # ================================================================
    # Вкладка: Тарифы
    # ================================================================

    def _create_rates_tab(self):
        """Встраиваем RatesSettingsWidget"""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Загрузка..."))
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(250, self._init_rates_widget)
        return w

    def _init_rates_widget(self):
        """Инициализация виджета тарифов"""
        try:
            from ui.rates_dialog import RatesSettingsWidget
            widget = RatesSettingsWidget(
                parent=self._tab_rates,
                api_client=self.api_client,
            )
            layout = self._tab_rates.layout()
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            layout.addWidget(widget)
        except Exception as e:
            print(f"[WARN] Не удалось загрузить RatesSettingsWidget: {e}")
            lbl = self._tab_rates.findChild(QLabel)
            if lbl:
                lbl.setText(f"Ошибка загрузки: {e}")

    # ================================================================
    # Вкладка: Агенты и города
    # ================================================================

    def _create_agents_cities_tab(self):
        """Вкладка управления агентами и городами"""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Загрузка..."))
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(300, self._init_agents_cities_widget)
        return w

    def _init_agents_cities_widget(self):
        """Инициализация виджета агентов и городов"""
        try:
            from ui.agents_cities_widget import AgentsCitiesWidget
            widget = AgentsCitiesWidget(
                parent=self._tab_agents_cities,
                api_client=self.api_client,
                data_access=self.data_access,
            )
            layout = self._tab_agents_cities.layout()
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            layout.addWidget(widget)
        except Exception as e:
            print(f"[WARN] Не удалось загрузить AgentsCitiesWidget: {e}")
            lbl = self._tab_agents_cities.findChild(QLabel)
            if lbl:
                lbl.setText(f"Ошибка загрузки: {e}")

    # ================================================================
    # Вкладка: Уведомления
    # ================================================================

    def _create_notifications_tab(self):
        """Вкладка настроек уведомлений для сотрудников"""
        from PyQt5.QtCore import QTimer
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Загрузка..."))
        QTimer.singleShot(200, self._init_notifications_widget)
        return w

    def _init_notifications_widget(self):
        """Инициализация виджета настроек уведомлений"""
        try:
            from ui.notification_settings_widget import NotificationSettingsWidget
            widget = NotificationSettingsWidget(
                parent=self._tab_notifications,
                api_client=self.api_client,
                data_access=self.data_access,
                employee=self.employee,
            )
            layout = self._tab_notifications.layout()
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            layout.addWidget(widget)
        except Exception as e:
            print(f"[WARN] Не удалось загрузить NotificationSettingsWidget: {e}")
            lbl = self._tab_notifications.findChild(QLabel)
            if lbl:
                lbl.setText(f"Ошибка загрузки: {e}")
