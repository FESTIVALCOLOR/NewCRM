# -*- coding: utf-8 -*-
"""
Виджет управления агентами и городами для администрирования.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QLineEdit, QFrame, QColorDialog,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from ui.custom_message_box import CustomMessageBox
from utils.data_access import DataAccess
from utils.icon_loader import IconLoader


class AgentsCitiesWidget(QWidget):
    """Виджет управления агентами и городами"""

    def __init__(self, parent=None, api_client=None, data_access=None):
        super().__init__(parent)
        self.data = data_access or DataAccess(api_client=api_client)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(16)

        # === Левая секция: Агенты ===
        agents_frame = QFrame()
        agents_frame.setStyleSheet("""
            QFrame { border: 1px solid #E0E0E0; border-radius: 8px; background: white; }
        """)
        agents_layout = QVBoxLayout(agents_frame)
        agents_layout.setContentsMargins(12, 12, 12, 12)

        agents_header = QHBoxLayout()
        agents_title = QLabel("Типы агентов")
        agents_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #333; border: none;")
        agents_header.addWidget(agents_title)
        agents_header.addStretch()

        add_agent_btn = QPushButton("Добавить")
        add_agent_btn.setFixedHeight(30)
        add_agent_btn.setCursor(Qt.PointingHandCursor)
        add_agent_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c; color: #333; border: 1px solid #e6c235;
                border-radius: 4px; padding: 0 16px; font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background-color: #ffe066; }
        """)
        add_agent_btn.clicked.connect(self._add_agent)
        agents_header.addWidget(add_agent_btn)
        agents_layout.addLayout(agents_header)

        self._agents_table = QTableWidget()
        self._agents_table.setColumnCount(4)
        self._agents_table.setHorizontalHeaderLabels(["Название", "Цвет", "Статус", ""])
        self._agents_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._agents_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self._agents_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self._agents_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self._agents_table.setColumnWidth(1, 80)
        self._agents_table.setColumnWidth(2, 90)
        self._agents_table.setColumnWidth(3, 80)
        self._agents_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._agents_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._agents_table.verticalHeader().setVisible(False)
        self._agents_table.setStyleSheet("border: none;")
        agents_layout.addWidget(self._agents_table)

        main_layout.addWidget(agents_frame)

        # === Правая секция: Города ===
        cities_frame = QFrame()
        cities_frame.setStyleSheet("""
            QFrame { border: 1px solid #E0E0E0; border-radius: 8px; background: white; }
        """)
        cities_layout = QVBoxLayout(cities_frame)
        cities_layout.setContentsMargins(12, 12, 12, 12)

        cities_header = QHBoxLayout()
        cities_title = QLabel("Города")
        cities_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #333; border: none;")
        cities_header.addWidget(cities_title)
        cities_header.addStretch()

        add_city_btn = QPushButton("Добавить")
        add_city_btn.setFixedHeight(30)
        add_city_btn.setCursor(Qt.PointingHandCursor)
        add_city_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c; color: #333; border: 1px solid #e6c235;
                border-radius: 4px; padding: 0 16px; font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background-color: #ffe066; }
        """)
        add_city_btn.clicked.connect(self._add_city)
        cities_header.addWidget(add_city_btn)
        cities_layout.addLayout(cities_header)

        self._cities_table = QTableWidget()
        self._cities_table.setColumnCount(3)
        self._cities_table.setHorizontalHeaderLabels(["Название", "Статус", ""])
        self._cities_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._cities_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self._cities_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self._cities_table.setColumnWidth(1, 90)
        self._cities_table.setColumnWidth(2, 80)
        self._cities_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._cities_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._cities_table.verticalHeader().setVisible(False)
        self._cities_table.setStyleSheet("border: none;")
        cities_layout.addWidget(self._cities_table)

        main_layout.addWidget(cities_frame)

    def _load_data(self):
        """Загрузить данные агентов и городов"""
        self._load_agents()
        self._load_cities()

    def _load_agents(self):
        """Загрузить список агентов"""
        agents = self.data.get_all_agents()
        self._agents_table.setRowCount(len(agents))
        for row, agent in enumerate(agents):
            # Название
            name_item = QTableWidgetItem(agent.get('name', ''))
            self._agents_table.setItem(row, 0, name_item)

            # Цвет
            color = agent.get('color', '#FFFFFF')
            color_btn = QPushButton()
            color_btn.setFixedSize(60, 24)
            color_btn.setStyleSheet(f"background-color: {color}; border: 1px solid #ccc; border-radius: 3px;")
            color_btn.setCursor(Qt.PointingHandCursor)
            color_btn.setProperty('agent_name', agent.get('name'))
            color_btn.setProperty('agent_color', color)
            color_btn.clicked.connect(lambda checked, n=agent.get('name'), c=color: self._change_agent_color(n, c))
            self._agents_table.setCellWidget(row, 1, color_btn)

            # Статус
            status_item = QTableWidgetItem(agent.get('status', 'активный'))
            self._agents_table.setItem(row, 2, status_item)

            # Кнопка удаления
            del_btn = QPushButton("Удалить")
            del_btn.setFixedHeight(24)
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setStyleSheet("""
                QPushButton {
                    background-color: #fff; color: #e74c3c; border: 1px solid #e74c3c;
                    border-radius: 3px; padding: 0 8px; font-size: 11px;
                }
                QPushButton:hover { background-color: #e74c3c; color: white; }
            """)
            del_btn.clicked.connect(lambda checked, aid=agent.get('id'), aname=agent.get('name'): self._delete_agent(aid, aname))
            self._agents_table.setCellWidget(row, 3, del_btn)

    def _load_cities(self):
        """Загрузить список городов"""
        cities = self.data.get_all_cities()
        self._cities_table.setRowCount(len(cities))
        for row, city in enumerate(cities):
            # Название
            name_item = QTableWidgetItem(city.get('name', ''))
            self._cities_table.setItem(row, 0, name_item)

            # Статус
            status_item = QTableWidgetItem(city.get('status', 'активный'))
            self._cities_table.setItem(row, 1, status_item)

            # Кнопка удаления
            del_btn = QPushButton("Удалить")
            del_btn.setFixedHeight(24)
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setStyleSheet("""
                QPushButton {
                    background-color: #fff; color: #e74c3c; border: 1px solid #e74c3c;
                    border-radius: 3px; padding: 0 8px; font-size: 11px;
                }
                QPushButton:hover { background-color: #e74c3c; color: white; }
            """)
            del_btn.clicked.connect(lambda checked, cid=city.get('id'), cname=city.get('name'): self._delete_city(cid, cname))
            self._cities_table.setCellWidget(row, 2, del_btn)

    def _add_agent(self):
        """Диалог добавления агента"""
        from PyQt5.QtWidgets import QDialog, QFormLayout
        from ui.custom_title_bar import CustomTitleBar

        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setAttribute(Qt.WA_TranslucentBackground, True)
        dialog.setFixedWidth(400)

        border_frame = QFrame(dialog)
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 10px;
            }
        """)
        frame_layout = QVBoxLayout(border_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)

        title_bar = CustomTitleBar(dialog, 'Добавить агента', simple_mode=True)
        frame_layout.addWidget(title_bar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 8, 16, 16)

        name_input = QLineEdit()
        name_input.setPlaceholderText("Название агента (например: ПЕТРОВИЧ)")
        name_input.setStyleSheet("padding: 8px; border: 1px solid #d9d9d9; border-radius: 4px; font-size: 13px;")
        content_layout.addWidget(QLabel("Название:"))
        content_layout.addWidget(name_input)

        # Выбор цвета
        self._new_agent_color = '#FFFFFF'
        color_layout = QHBoxLayout()
        color_preview = QPushButton()
        color_preview.setFixedSize(40, 30)
        color_preview.setStyleSheet(f"background-color: {self._new_agent_color}; border: 1px solid #ccc; border-radius: 3px;")

        def pick_color():
            c = QColorDialog.getColor(QColor(self._new_agent_color), dialog, "Выберите цвет агента")
            if c.isValid():
                self._new_agent_color = c.name()
                color_preview.setStyleSheet(f"background-color: {self._new_agent_color}; border: 1px solid #ccc; border-radius: 3px;")

        color_btn = QPushButton("Выбрать цвет")
        color_btn.setStyleSheet("padding: 6px 12px; font-size: 12px;")
        color_btn.clicked.connect(pick_color)
        color_layout.addWidget(color_preview)
        color_layout.addWidget(color_btn)
        color_layout.addStretch()
        content_layout.addWidget(QLabel("Цвет:"))
        content_layout.addLayout(color_layout)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("padding: 6px 16px; font-size: 12px;")
        cancel_btn.clicked.connect(dialog.reject)
        ok_btn = QPushButton("Добавить")
        ok_btn.setStyleSheet("""
            QPushButton { background-color: #ffd93c; padding: 6px 16px; font-size: 12px; font-weight: 600; border-radius: 4px; }
            QPushButton:hover { background-color: #ffe066; }
        """)

        def on_ok():
            name = name_input.text().strip()
            if not name:
                CustomMessageBox(dialog, 'Ошибка', 'Введите название агента', 'warning').exec_()
                return
            if self.data.add_agent(name, self._new_agent_color):
                dialog.accept()
                self._load_agents()
            else:
                CustomMessageBox(dialog, 'Ошибка', 'Не удалось добавить агента', 'error').exec_()

        ok_btn.clicked.connect(on_ok)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        content_layout.addLayout(btn_layout)

        frame_layout.addWidget(content)
        root_layout = QVBoxLayout(dialog)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(border_frame)
        dialog.exec_()

    def _add_city(self):
        """Диалог добавления города"""
        from PyQt5.QtWidgets import QDialog
        from ui.custom_title_bar import CustomTitleBar

        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setAttribute(Qt.WA_TranslucentBackground, True)
        dialog.setFixedWidth(400)

        border_frame = QFrame(dialog)
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 10px;
            }
        """)
        frame_layout = QVBoxLayout(border_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)

        title_bar = CustomTitleBar(dialog, 'Добавить город', simple_mode=True)
        frame_layout.addWidget(title_bar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 8, 16, 16)

        name_input = QLineEdit()
        name_input.setPlaceholderText("Название города (например: НСК)")
        name_input.setStyleSheet("padding: 8px; border: 1px solid #d9d9d9; border-radius: 4px; font-size: 13px;")
        content_layout.addWidget(QLabel("Название:"))
        content_layout.addWidget(name_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("padding: 6px 16px; font-size: 12px;")
        cancel_btn.clicked.connect(dialog.reject)
        ok_btn = QPushButton("Добавить")
        ok_btn.setStyleSheet("""
            QPushButton { background-color: #ffd93c; padding: 6px 16px; font-size: 12px; font-weight: 600; border-radius: 4px; }
            QPushButton:hover { background-color: #ffe066; }
        """)

        def on_ok():
            name = name_input.text().strip()
            if not name:
                CustomMessageBox(dialog, 'Ошибка', 'Введите название города', 'warning').exec_()
                return
            if self.data.add_city(name):
                dialog.accept()
                self._load_cities()
            else:
                CustomMessageBox(dialog, 'Ошибка', 'Не удалось добавить город', 'error').exec_()

        ok_btn.clicked.connect(on_ok)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        content_layout.addLayout(btn_layout)

        frame_layout.addWidget(content)
        root_layout = QVBoxLayout(dialog)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(border_frame)
        dialog.exec_()

    def _change_agent_color(self, agent_name, current_color):
        """Изменить цвет агента"""
        color = QColorDialog.getColor(QColor(current_color), self, "Выберите цвет агента")
        if color.isValid():
            if self.data.update_agent_color(agent_name, color.name()):
                self._load_agents()

    def _delete_agent(self, agent_id, agent_name):
        """Удалить агента"""
        msg = CustomMessageBox(
            self, 'Подтверждение',
            f'Удалить агента "{agent_name}"?\n\nАгент будет деактивирован. Существующие договоры сохранятся.',
            'question'
        )
        if msg.exec_() == msg.AcceptRole or msg.clickedButton() == msg.yes_button if hasattr(msg, 'yes_button') else False:
            if self.data.delete_agent(agent_id):
                self._load_agents()
            else:
                CustomMessageBox(self, 'Ошибка', 'Не удалось удалить агента.\nВозможно есть активные договоры.', 'error').exec_()

    def _delete_city(self, city_id, city_name):
        """Удалить город"""
        msg = CustomMessageBox(
            self, 'Подтверждение',
            f'Удалить город "{city_name}"?\n\nГород будет деактивирован. Существующие договоры сохранятся.',
            'question'
        )
        if msg.exec_() == msg.AcceptRole or msg.clickedButton() == msg.yes_button if hasattr(msg, 'yes_button') else False:
            if self.data.delete_city(city_id):
                self._load_cities()
            else:
                CustomMessageBox(self, 'Ошибка', 'Не удалось удалить город.\nВозможно есть активные договоры.', 'error').exec_()
