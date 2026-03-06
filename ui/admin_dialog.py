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

