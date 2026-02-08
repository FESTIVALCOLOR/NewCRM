"""
Единый файл стилей для Interior Studio CRM
Объединяет стили из styles.qss, global_styles.py, calendar_styles.py
"""

from .resource_path import resource_path


def get_unified_stylesheet():
    """
    Возвращает единый stylesheet для всего приложения

    ВАЖНО: Все высоты установлены в 28px для полей ввода и выпадающих списков
    """

    # Формируем пути к иконкам
    icons_path = resource_path('resources/icons').replace('\\', '/')

    return f"""
/* ===== YANDEX DISK STYLE - Interior Studio CRM ===== */

* {{
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
}}

/* ===== ОСНОВНОЙ ФОН ===== */
QMainWindow {{
    background-color: #f0f0f0;
}}

QWidget {{
    color: #000000;
    background-color: transparent;
}}

/* ===== КНОПКИ (Стиль Яндекс.Диска) ===== */
QPushButton {{
    background-color: #ffffff;
    border: 1px solid #d9d9d9;
    padding: 7px 16px;
    border-radius: 6px;
    color: #000000;
    font-size: 13px;
    font-weight: 500;
    min-height: 32px;
}}

QPushButton[icon-only="true"] {{
    padding: 0px;
    min-height: 20px;
    min-width: 20px;
}}

QPushButton:hover {{
    background-color: #fafafa;
    border-color: #c0c0c0;
}}

QPushButton:pressed {{
    background-color: #f0f0f0;
    border-color: #b0b0b0;
}}

QPushButton:disabled {{
    background-color: #fafafa;
    color: #b0b0b0;
    border-color: #e6e6e6;
}}

QPushButton[primary="true"] {{
    background-color: #ffd93c;
    border: 1px solid #e6c236;
    color: #000000;
    font-weight: 600;
}}

QPushButton[primary="true"]:hover {{
    background-color: #ffdb4d;
    border-color: #d9b530;
}}

QPushButton[primary="true"]:pressed {{
    background-color: #e6c236;
}}

/* ===== TOOLTIP ===== */
QToolTip {{
    background-color: #ffffff;
    font-size: 12px;
    color: #000000;
    border: 1px solid #d9d9d9;
    border-radius: 4px;
    padding: 6px 8px;
}}

/* ===== ПОЛЯ ВВОДА (28px height) ===== */
QLineEdit {{
    border: 1px solid #d9d9d9;
    padding: 2px 8px;
    border-radius: 6px;
    background-color: #ffffff;
    selection-background-color: #fff4d9;
    selection-color: #000000;
    min-height: 22px;
    max-height: 22px;
}}

/* QTextEdit - многострочное поле, без ограничения высоты */
QTextEdit {{
    border: 1px solid #d9d9d9;
    padding: 2px 8px;
    border-radius: 6px;
    background-color: #ffffff;
    selection-background-color: #fff4d9;
    selection-color: #000000;
}}

QLineEdit:hover, QTextEdit:hover {{
    border-color: #c0c0c0;
}}

QLineEdit:focus, QTextEdit:focus {{
    border: 1px solid #ffd93c;
    outline: none;
}}

QLineEdit:disabled, QTextEdit:disabled {{
    background-color: #fafafa;
    color: #b0b0b0;
    border-color: #e6e6e6;
}}

/* ===== SPINBOX (28px height) ===== */
QSpinBox, QDoubleSpinBox {{
    border: 1px solid #d9d9d9;
    padding: 2px 8px;
    border-radius: 6px;
    background-color: #ffffff;
    selection-background-color: #fff4d9;
    selection-color: #000000;
    min-height: 22px;
    max-height: 22px;
}}

QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: #c0c0c0;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid #ffd93c;
    outline: none;
}}

QSpinBox::up-button, QDoubleSpinBox::up-button {{
    border: none;
    background: transparent;
    width: 16px;
    border-radius: 4px;
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
    background-color: #fafafa;
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    border: none;
    background: transparent;
    width: 16px;
    border-radius: 4px;
}}

QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: #fafafa;
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    width: 24;
    height: 24;
    border-left: 0px solid transparent;
    border-right: 0px solid transparent;
    border-bottom: 0px solid #808080;
}}

QSpinBox::up-arrow, QSpinBox::up-arrow {{
    image: url({icons_path}/arrow-up-circle.svg);
    width: 14px;
    height: 14px;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    width: 24;
    height: 24;
    border-left: 0px solid transparent;
    border-right: 0px solid transparent;
    border-top: 0px solid #808080;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url({icons_path}/arrow-down-circle.svg);
    width: 14px;
    height: 14px;
}}

/* ===== ВЫПАДАЮЩИЕ СПИСКИ (28px height) ===== */
QComboBox {{
    border: 1px solid #d9d9d9;
    padding: 2px 12px;
    padding-right: 28px;
    border-radius: 6px;
    background-color: #ffffff;
    selection-background-color: #fff4d9;
    min-height: 22px;
    max-height: 22px;
}}

QComboBox:hover {{
    border-color: #c0c0c0;
}}

QComboBox:focus {{
    border-color: #ffd93c;
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
    background: transparent;
    border-radius: 6px;
}}

QComboBox::down-arrow {{
    image: url({icons_path}/arrow-down-circle.svg);
    width: 14px;
    height: 14px;
}}

QComboBox QAbstractItemView {{
    border: none;
    background-color: #ffffff;
    selection-background-color: #fff4d9;
    selection-color: #000000;
    outline: none;
    border-radius: 6px;
    padding: 6px;
    margin: 6px;
}}

QComboBox QAbstractItemView::item {{
    padding: 6px 12px;
    min-height: 28px;
    border-radius: 4px;
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: #fafafa;
    border-radius: 4px;
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: #fff4d9;
    border-radius: 4px;
}}

/* ===== DATE/TIME EDIT (28px height) ===== */
QDateEdit, QTimeEdit, QDateTimeEdit {{
    border: 1px solid #d9d9d9;
    padding: 2px 8px;
    border-radius: 6px;
    background-color: #ffffff;
    padding-right: 28px;
    min-height: 22px;
    max-height: 22px;
}}

QDateEdit:hover, QTimeEdit:hover, QDateTimeEdit:hover {{
    border-color: #c0c0c0;
}}

QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus {{
    border-color: #ffd93c;
}}

QDateEdit::drop-up, QTimeEdit::drop-up, QDateTimeEdit::drop-up {{
    border: none;
    width: 24px;
    background: transparent;
    border-radius: 6px;
}}

QDateEdit::drop-up:hover, QTimeEdit::drop-up:hover, QDateTimeEdit::drop-up:hover {{
    background-color: #fafafa;
}}

QDateEdit::up-arrow, QTimeEdit::up-arrow, QDateTimeEdit::up-arrow {{
    image: url({icons_path}/arrow-up-circle.svg);
    width: 14px;
    height: 14px;
}}
QDateEdit::drop-down, QTimeEdit::drop-down, QDateTimeEdit::drop-down {{
    border: none;
    width: 24px;
    background: transparent;
    border-radius: 6px;
}}

QDateEdit::drop-down:hover, QTimeEdit::drop-down:hover, QDateTimeEdit::drop-down:hover {{
    background-color: #fafafa;
}}

QDateEdit::down-arrow, QTimeEdit::down-arrow, QDateTimeEdit::down-arrow {{
    image: url({icons_path}/arrow-down-circle.svg);
    width: 14px;
    height: 14px;
}}

/* ===== КАЛЕНДАРЬ ===== */
QCalendarWidget {{
    background-color: #ffffff;
    border: 1px solid #d9d9d9;
    border-top-left-radius: 4px;  
    border-top-right-radius: 4px; 
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;
    min-width: 300px;
    max-width: 300px;
    min-height: 340px;
    max-height: 340px;
}}

QCalendarWidget QWidget {{
    alternate-background-color: #fafafa;
}}

/* Заголовок с месяцем и годом */
QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background-color: #ffffff;
    border-bottom: 1px solid #e6e6e6;
    min-height: 30px;
    padding: 4px;
    border: 1px solid #d9d9d9;
    border-top-left-radius: 4px;  
    border-top-right-radius: 4px;     
}}

/* Кнопки навигации (влево/вправо) */
QCalendarWidget QToolButton {{
    background-color: transparent;
    color: #000000;
    border: none;
    border-radius: 4px;
    padding: 4px;
    margin: 1px;
    min-width: 28px;
    min-height: 28px;
}}

QCalendarWidget QToolButton:hover {{
    background-color: #fafafa;
}}

QCalendarWidget QToolButton:pressed {{
    background-color: #e0e0e0;
}}

/* Иконки навигации */
QCalendarWidget QToolButton#qt_calendar_prevmonth {{
    qproperty-icon: url({icons_path}/arrow-left-circle.svg);
    qproperty-iconSize: 20px;
}}

QCalendarWidget QToolButton#qt_calendar_nextmonth {{
    qproperty-icon: url({icons_path}/arrow-right-circle.svg);
    qproperty-iconSize: 20px;
}}

/* Меню выбора месяца/года */
QCalendarWidget QMenu {{
    background-color: #FFFFFF;
    border: 1px solid #CCCCCC;
    border-radius: 2px;
    padding: 2px;
    min-width: 90px;
    min-height: 26px; 
}}

QCalendarWidget QMenu::item {{
    padding: 5px 20px;
    color: #333333;
}}

QCalendarWidget QMenu::item:selected {{
    background-color: #fff4d9;
    color: #000000;
}}

QCalendarWidget QToolButton#qt_calendar_monthbutton {{
    text-align: left;
    min-width: 90px;
}}

/* Поле выбора года (QSpinBox) */
QCalendarWidget QSpinBox {{
    background-color: #ffffff;
    border: 1px solid #d9d9d9;
    border-radius: 4px;
    padding: 6px;
    min-height: 26px;
    max-height: 26px;
    min-width: 50px;
    max-width: 50px;
}}

QCalendarWidget QSpinBox:hover {{
    border-color: #ffd93c;
}}

QCalendarWidget QSpinBox::up-button,
QCalendarWidget QSpinBox::down-button {{
    background-color: #ffffff;
    border: none;
    width: 20px;
    height: 20px;
}}

QCalendarWidget QSpinBox::up-button:hover,
QCalendarWidget QSpinBox::down-button:hover {{
    background-color: #ffffff;
}}

QCalendarWidget QSpinBox::up-arrow {{
    image: url({icons_path}/arrow-up-circle.svg);
    width: 13px;
    height: 13px;
    border-left: 0px solid transparent;
    border-right: 0px solid transparent;
    border-top: 0px solid #808080; 
}}

QCalendarWidget QSpinBox::down-arrow {{
    image: url({icons_path}/arrow-down-circle.svg);
    width: 13px;
    height: 13px;
    border-left: 0px solid transparent;
    border-right: 0px solid transparent;
    border-top: 0px solid #808080;
}}

/* Заголовки дней недели */
QCalendarWidget QWidget QAbstractItemView:enabled {{
    font-size: 12px;
    color: #000000;
    background-color: #e0e0e0;
    selection-background-color: #FF0000;
    selection-color: #FFFFFF;
    font-weight: bold;
}}

QCalendarWidget QTableView {{
    background-color: #ffffff;
    gridline-color: transparent;
    selection-background-color: #FF0000;
    border-radius: 10px;
    outline: none;
}}

/* Заголовки дней недели (Пн, Вт, Ср...) */
QCalendarWidget QTableView QHeaderView {{
    background-color: #e0e0e0;
    font-weight: bold;
}}

QCalendarWidget QTableView QHeaderView::section {{
    background-color: transparent;
    color: #FF0000;;
    border: none;
    padding: 2px;
    font-size: 11px;
    border-radius: 10px;
    font-weight: bold;
}}

/* Ячейки с датами */
QCalendarWidget QTableView::item {{
    padding: 2px;
    border-radius: 4px;
}}

QCalendarWidget QTableView::item:hover {{
    background-color: #fafafa;
    border-radius: 4px;
}}

/* Выбранная дата - КРАСНЫЙ КРУГ с белым текстом */
QCalendarWidget QTableView::item:selected {{
    background-color: #ffffff;
    color: #000000;
    font-weight: bold;
    border-radius: 10px;
}}

QCalendarWidget QTableView::item:focus {{
    background-color: #FF0000;
    color: #FFFFFF;
    border: 2px solid #CC0000;
    border-radius: 10px;
}}

/* Сегодняшняя дата */
QCalendarWidget QTableView::item:selected:focus {{
    background-color: #FF0000;
    color: #FFFFFF;
    border-radius: 10px;
}}

/* Кнопка "Сегодня" */
QCalendarWidget QWidget QPushButton {{
    background-color: #ffd93c;
    border: none;
    border-radius: 6px;
    padding: 4px 16px;
    color: #000000;
    font-weight: 600;
    min-height: 24px;
}}

QCalendarWidget QWidget QPushButton:hover {{
    background-color: #ffdb4d;
}}

QCalendarWidget QWidget QPushButton:pressed {{
    background-color: #e6c236;
}}

/* ===== ТАБЛИЦЫ (Стиль Яндекс.Диска) ===== */
QTableWidget, QTableView {{
    border: none;
    background-color: #ffffff;
    gridline-color: #f0f0f0;
    selection-background-color: #fff4d9;
    selection-color: #000000;
    alternate-background-color: #fafafa;
    border-radius: 8px;
    show-decoration-selected: 1;
}}

QTableWidget::item, QTableView::item {{
    padding: 4px;
    border: none;
    border-bottom: 1px solid #f0f0f0;
}}

QTableWidget::item:hover, QTableView::item:hover {{
    background-color: #fafafa;
}}

QTableWidget::item:selected, QTableView::item:selected {{
    background-color: #fff4d9;
    color: #000000;
}}

QTableWidget::item:selected:active, QTableView::item:selected:active {{
    background-color: #fff4d9;
}}

QTableWidget::item:selected:!active, QTableView::item:selected:!active {{
    background-color: #fff4d9;
}}

QTableWidget::item:selected:!focus, QTableView::item:selected:!focus {{
    background-color: #fff4d9;
    outline: none;
}}

/* Убираем рамку фокуса с ячеек - должна выделяться только строка */
QTableWidget::item:focus, QTableView::item:focus {{
    border: none;
    outline: none;
}}

QTableWidget::item:selected:focus, QTableView::item:selected:focus {{
    border: none;
    outline: none;
    background-color: #fff4d9;
    color: #000000;
}}

QHeaderView::section {{
    background-color: #fafafa;
    border: none;
    border-bottom: 1px solid #e6e6e6;
    border-right: 1px solid #f0f0f0;
    padding: 4px 8px;
    font-weight: 600;
    color: #000000;
}}

QHeaderView::section:hover {{
    background-color: #f5f5f5;
}}

/* ===== ВКЛАДКИ ===== */
QTabWidget::pane {{
    border: 1px solid #d9d9d9;
    background-color: #ffffff;
    border-radius: 8px;
}}

QTabBar::tab {{
    background-color: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 10px 20px;
    margin-right: 2px;
    color: #808080;
    font-weight: 500;
}}

QTabBar::tab:hover {{
    color: #000000;
    border-bottom: 2px solid #d9d9d9;
}}

QTabBar::tab:selected {{
    color: #000000;
    border-bottom: 2px solid #ffd93c;
    font-weight: 600;
}}

/* ===== SCROLLBAR (Яндекс стиль) ===== */
QScrollBar:vertical {{
    background: #fafafa;
    width: 12px;
    margin: 0px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background-color: #d9d9d9;
    min-height: 30px;
    border-radius: 6px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: #ffd93c;
    border-radius: 6px;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    border: none;
    background: none;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background: #fafafa;
    height: 12px;
    margin: 0px;
    border: none;
}}

QScrollBar::handle:horizontal {{
    background-color: #d9d9d9;
    min-width: 30px;
    border-radius: 6px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: #ffd93c;
    border-radius: 6px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
    border: none;
    background: none;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* ===== CHECKBOX ===== */
QCheckBox {{
    spacing: 8px;
    color: #000000;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid #d9d9d9;
    border-radius: 4px;
    background-color: #ffffff;
}}

QCheckBox::indicator:hover {{
    border-color: #c0c0c0;
}}

QCheckBox::indicator:checked {{
    background-color: #ffd93c;
    border-color: #e6c236;
    image: none;
}}

QCheckBox::indicator:checked:hover {{
    background-color: #ffdb4d;
}}

QCheckBox::indicator:disabled {{
    background-color: #fafafa;
    border-color: #e6e6e6;
}}

/* ===== RADIO BUTTON ===== */
QRadioButton {{
    spacing: 8px;
    color: #000000;
}}

QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid #d9d9d9;
    border-radius: 9px;
    background-color: #ffffff;
}}

QRadioButton::indicator:hover {{
    border-color: #c0c0c0;
}}

QRadioButton::indicator:checked {{
    background-color: #ffffff;
    border: 5px solid #ffd93c;
}}

QRadioButton::indicator:disabled {{
    background-color: #fafafa;
    border-color: #e6e6e6;
}}

/* ===== PROGRESS BAR ===== */
QProgressBar {{
    border: 1px solid #d9d9d9;
    border-radius: 6px;
    background-color: #fafafa;
    text-align: center;
    color: #000000;
    height: 24px;
}}

QProgressBar::chunk {{
    background-color: #ffd93c;
    border-radius: 5px;
}}

/* ===== MENU ===== */
QMenuBar {{
    background-color: #ffffff;
    border-bottom: 1px solid #d9d9d9;
    padding: 4px;
}}

QMenuBar::item {{
    background: transparent;
    padding: 8px 16px;
    border-radius: 6px;
}}

QMenuBar::item:selected {{
    background-color: #fafafa;
}}

QMenuBar::item:pressed {{
    background-color: #fff4d9;
}}

QMenu {{
    background-color: #ffffff;
    border: 1px solid #d9d9d9;
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 24px 8px 12px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: #fff4d9;
}}

QMenu::separator {{
    height: 1px;
    background: #d9d9d9;
    margin: 4px 8px;
}}

/* ===== GROUPBOX ===== */
QGroupBox {{
    border: 1px solid #d9d9d9;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    background-color: #ffffff;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 3 10px;
    color: #000000;
    font-weight: 600;
}}

/* ===== LABEL ===== */
QLabel {{
    color: #000000;
    background: transparent;
}}

/* ===== STATUSBAR ===== */
QStatusBar {{
    background-color: #ffffff;
    border-top: 1px solid #d9d9d9;
    color: #808080;
}}

/* ===== DIALOG ===== */
QDialog {{
    background-color: #f0f0f0;
}}

/* ===== SPLITTER ===== */
QSplitter::handle {{
    background-color: #d9d9d9;
}}

QSplitter::handle:hover {{
    background-color: #c0c0c0;
}}

QSplitter::handle:horizontal {{
    width: 1px;
}}

QSplitter::handle:vertical {{
    height: 1px;
}}

/* ===== LIST WIDGET ===== */
QListWidget {{
    border: 1px solid #d9d9d9;
    background-color: #ffffff;
    outline: none;
    border-radius: 8px;
}}

QListWidget::item {{
    padding: 8px;
    border-bottom: 1px solid #f0f0f0;
    border-radius: 4px;
}}

QListWidget::item:hover {{
    background-color: #fafafa;
}}

QListWidget::item:selected {{
    background-color: #fff4d9;
    color: #000000;
}}

/* ===== TREE WIDGET ===== */
QTreeWidget {{
    border: 1px solid #d9d9d9;
    background-color: #ffffff;
    outline: none;
    border-radius: 8px;
}}

QTreeWidget::item {{
    padding: 6px;
}}

QTreeWidget::item:hover {{
    background-color: #fafafa;
}}

QTreeWidget::item:selected {{
    background-color: #fff4d9;
    color: #000000;
}}

QTreeWidget::branch {{
    background: transparent;
}}

/* ===== SLIDER ===== */
QSlider::groove:horizontal {{
    border: 1px solid #d9d9d9;
    height: 4px;
    background: #fafafa;
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: #ffd93c;
    border: 1px solid #e6c236;
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background: #ffdb4d;
}}

/* ===== TOOLBAR ===== */
QToolBar {{
    background-color: #ffffff;
    border-bottom: 1px solid #d9d9d9;
    spacing: 4px;
    padding: 4px;
}}

QToolBar::separator {{
    background-color: #d9d9d9;
    width: 1px;
    margin: 4px;
}}

QToolButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px;
    min-height: 32px;
}}

QToolButton:hover {{
    background-color: #fafafa;
    border-color: #d9d9d9;
}}

QToolButton:pressed {{
    background-color: #fff4d9;
}}
"""
