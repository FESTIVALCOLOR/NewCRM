# -*- coding: utf-8 -*-
import os
import sys

# ========== ОПРЕДЕЛЯЕМ КОРЕНЬ ПРОЕКТА ==========
if getattr(sys, 'frozen', False):
    APP_ROOT = os.path.dirname(sys.executable)
else:
    APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ICONS_PATH = os.path.join(APP_ROOT, 'resources', 'icons').replace('\\', '/')

print(f"[GLOBAL_STYLES] Путь к иконкам: {ICONS_PATH}")
# ================================================

COMBOBOX_STYLE = f"""
/* ========== QComboBox (ЗАКРЫТ) ========== */
QComboBox {{
    background-color: #FFFFFF;
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 6px 8px;
    padding-right: 30px;
    font-size: 12px;
    color: #333333;
    min-height: 28px;
}}

QComboBox:hover {{
    border-color: #3498DB;
    background-color: #F8FBFF;
}}

QComboBox:focus {{
    border-color: #3498DB;
    background-color: #FFFFFF;
}}

QComboBox:disabled {{
    background-color: #F5F5F5;
    color: #999999;
}}

/* ========== QComboBox (ОТКРЫТ) ========== */
QComboBox:on {{
    border-color: #3498DB;  
    border-top-left-radius: 4px;  
    border-top-right-radius: 4px; 
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;
    margin: 10px;    
}}

/* Кнопка drop-down */
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: right center;
    width: 25px;
    border: none;
    background-color: transparent;
    border-top-left-radius: 4px;  
    border-top-right-radius: 4px; 
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;    
}}

QComboBox::drop-down:hover {{
    background-color: #E8F4F8;
}}

QComboBox::drop-down:pressed {{
    background-color: #D4E9F7;
    border-bottom-right-radius: 0px;
}}

QComboBox:on::drop-down {{
    border-bottom-right-radius: 0px;
}}

QComboBox:on::drop-down:hover {{
    border-bottom-right-radius: 0px;
    margin: 1px;
}}

QComboBox::down-arrow {{
    image: url({ICONS_PATH}/arrow-down-circle.svg);
    width: 16px;
    height: 16px;
    border: none;
}}

/* ========== ВЫПАДАЮЩИЙ СПИСОК - ФИНАЛЬНАЯ ВЕРСИЯ ========== */
QComboBox QAbstractItemView {{
    background-color: #f3f3f3;
    border: 0px solid #3498DB;
    border-top-left-radius: 4px;  
    border-top-right-radius: 4px; 
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;    
    selection-background-color: #E8F4F8;
    selection-color: #333333;
    outline: none;
    padding: 2px;
}}

QComboBox QAbstractItemView::item {{
    padding: 6px 10px;
    min-height: 25px;
    border-radius: 3px;
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: #E8F4F8;
    color: #3498DB;
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: #3498DB;
    color: #FFFFFF;
}}
/* =========================================================== */
"""

SCROLLBAR_STYLE = f"""
/* (БЕЗ ИЗМЕНЕНИЙ) */
QScrollBar:vertical {{
    background-color: #F8F9FA;
    width: 14px;
    margin: 16px 0px 16px 0px;
    border: none;
    border-radius: 7px;
}}

QScrollBar::handle:vertical {{
    background-color: #CCCCCC;
    min-height: 30px;
    border-radius: 5px;
    margin: 2px 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: #3498DB;
}}

QScrollBar::add-line:vertical {{
    height: 16px;
    background-color: transparent;
    subcontrol-position: bottom;
    subcontrol-origin: margin;
    border: none;
}}

QScrollBar::sub-line:vertical {{
    height: 16px;
    background-color: transparent;
    subcontrol-position: top;
    subcontrol-origin: margin;
    border: none;
}}

QScrollBar::up-arrow:vertical {{
    image: url({ICONS_PATH}/arrow-up-circle.svg);
    width: 12px;
    height: 12px;
}}

QScrollBar::down-arrow:vertical {{
    image: url({ICONS_PATH}/arrow-down-circle.svg);
    width: 12px;
    height: 12px;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background-color: #F8F9FA;
    height: 14px;
    margin: 0px 16px 0px 16px;
    border: none;
    border-radius: 7px;
}}

QScrollBar::handle:horizontal {{
    background-color: #CCCCCC;
    min-width: 30px;
    border-radius: 5px;
    margin: 2px 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: #3498DB;
}}

QScrollBar::add-line:horizontal {{
    width: 16px;
    background-color: transparent;
    subcontrol-position: right;
    subcontrol-origin: margin;
    border: none;
}}

QScrollBar::sub-line:horizontal {{
    width: 16px;
    background-color: transparent;
    subcontrol-position: left;
    subcontrol-origin: margin;
    border: none;
}}

QScrollBar::left-arrow:horizontal {{
    image: url({ICONS_PATH}/arrow-left-circle.svg);
    width: 12px;
    height: 12px;
}}

QScrollBar::right-arrow:horizontal {{
    image: url({ICONS_PATH}/arrow-right-circle.svg);
    width: 12px;
    height: 12px;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}
"""

TOOLTIP_STYLE = """
/* ========== ВСПЛЫВАЮЩИЕ ПОДСКАЗКИ ========== */
QToolTip {
    background-color: #F5F5F5;
    color: #333333;
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 5px;
    font-size: 12px;
}
"""

GLOBAL_STYLE = COMBOBOX_STYLE + "\n" + SCROLLBAR_STYLE + "\n" + TOOLTIP_STYLE
