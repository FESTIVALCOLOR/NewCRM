# -*- coding: utf-8 -*-
"""
Виджет настройки нормо-дней для администрирования.
Позволяет настроить распределение нормо-дней по этапам/подэтапам для каждого типа проекта.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from ui.custom_combobox import CustomComboBox
from ui.custom_message_box import CustomMessageBox
from utils.resource_path import resource_path
from utils.data_access import DataAccess

# Путь к иконкам для стилей
ICONS_PATH = resource_path('resources/icons').replace('\\', '/')

# Подтипы проектов по типу
_SUBTYPES = {
    'Индивидуальный': [
        'Полный (с 3д визуализацией)',
        'Эскизный (с коллажами)',
        'Планировочный',
    ],
    'Шаблонный': [
        'Стандарт',
        'Стандарт с визуализацией',
        'Проект ванной комнаты',
        'Проект ванной комнаты с визуализацией',
    ],
}

# Площади для превью (зависят от типа/подтипа проекта — синхронизированы с таблицей сроков в договоре)
_AREAS_INDIVIDUAL = [70, 100, 130, 160, 190, 220, 250, 300, 350, 400, 450, 500]
_AREAS_TEMPLATE = [90, 140, 190, 240, 290, 340]
_AREAS_BATHROOM = []  # фиксированный срок, площадь не влияет


def _get_areas_for_subtype(project_type: str, project_subtype: str) -> list:
    """Возвращает шкалу площадей для данного типа/подтипа проекта
    (синхронизирована с таблицей сроков в диалоге договора)."""
    if project_type == 'Индивидуальный':
        return _AREAS_INDIVIDUAL
    # Шаблонный
    sub = project_subtype.lower()
    if 'ванной' in sub:
        return _AREAS_BATHROOM
    return _AREAS_TEMPLATE


# ================================================================
# Локальный расчет срока договора (для отображения в UI)
# ================================================================

def _calc_contract_term(project_type: str, project_subtype: str, area: int) -> int:
    """Расчет срока договора в рабочих днях."""
    if project_type == 'Индивидуальный':
        if 'Полный' in project_subtype:
            pt_code = 1
        elif 'Планировочный' in project_subtype:
            pt_code = 3
        else:
            pt_code = 2
        thresholds_1 = [
            (70, 50), (100, 60), (130, 70), (160, 80), (190, 90), (220, 100),
            (250, 110), (300, 120), (350, 130), (400, 140), (450, 150), (500, 160),
        ]
        thresholds_2 = [
            (70, 30), (100, 35), (130, 40), (160, 45), (190, 50), (220, 55),
            (250, 60), (300, 65), (350, 70), (400, 75), (450, 80), (500, 85),
        ]
        thresholds_3 = [
            (70, 10), (100, 15), (130, 20), (160, 25), (190, 30), (220, 35),
            (250, 40), (300, 45), (350, 50), (400, 55), (450, 60), (500, 65),
        ]
        t = [thresholds_1, thresholds_2, thresholds_3][pt_code - 1]
        for max_a, days in t:
            if area <= max_a:
                return days
        # Площадь > 500 м² — возвращаем максимальный срок из таблицы
        return t[-1][1]
    else:  # Шаблонный
        sub = project_subtype.lower()
        if 'ванн' in sub:
            return 20 if 'визуализац' in sub else 10
        if area <= 90:
            base = 20
        else:
            base = 20 + (int((area - 90 - 1) // 50) + 1) * 10
        if 'визуализац' in sub:
            if area <= 90:
                base += 25
            else:
                base += 25 + (int((area - 90 - 1) // 50) + 1) * 15
        return base


# ================================================================
# Локальная генерация шаблона нормо-дней (fallback, когда API недоступен)
# ================================================================

def _build_individual_template(project_subtype: str, area: int):
    """Локальная генерация шаблона для индивидуального проекта."""
    K = max(0, int((area - 1) // 100))

    if 'Полный' in project_subtype:
        pt_code = 1
    elif 'Планировочный' in project_subtype:
        pt_code = 3
    else:
        pt_code = 2

    # Расчет срока
    contract_term = _calc_contract_term('Индивидуальный', project_subtype, area)

    entries = []
    order = 0

    def add(code, name, group, subgroup, g, executor, in_scope=True):
        nonlocal order
        order += 1
        entries.append({
            'stage_code': code, 'stage_name': name, 'stage_group': group,
            'substage_group': subgroup, 'raw_norm_days': g, 'executor_role': executor,
            'is_in_contract_scope': in_scope, 'sort_order': order,
        })

    def add_header(code, name, group, subgroup=''):
        nonlocal order
        order += 1
        entries.append({
            'stage_code': code, 'stage_name': name, 'stage_group': group,
            'substage_group': subgroup, 'raw_norm_days': 0, 'executor_role': 'header',
            'is_in_contract_scope': False, 'sort_order': order,
        })

    # --- ДАТА НАЧАЛА ---
    add('START', 'ДАТА НАЧАЛА РАЗРАБОТКИ', 'START', '', 0, 'Менеджер', True)

    # --- ЭТАП 1: ПЛАНИРОВОЧНОЕ РЕШЕНИЕ ---
    add_header('S1_HDR', 'ЭТАП 1: ПЛАНИРОВОЧНОЕ РЕШЕНИЕ', 'STAGE1')

    add_header('S1_1_HDR', 'Подэтап 1.1', 'STAGE1', 'Подэтап 1.1')
    add('S1_1_01', 'Разработка 3 вар. планировок', 'STAGE1', 'Подэтап 1.1', 4 + K * 2, 'Чертежник', True)
    add('S1_1_02', 'Проверка СДП', 'STAGE1', 'Подэтап 1.1', 1 + K * 0.5, 'СДП', True)
    add('S1_1_03', 'Правка чертежником', 'STAGE1', 'Подэтап 1.1', 1.5 + K * 1, 'Чертежник', True)
    add('S1_1_04', 'Проверка повторная СДП', 'STAGE1', 'Подэтап 1.1', 0.5 + K * 0.5, 'СДП', True)
    add('S1_1_05', 'Отправка клиенту', 'STAGE1', 'Подэтап 1.1', 3, 'Клиент', False)
    add('S1_1_06', 'Сбор правок от клиента СДП', 'STAGE1', 'Подэтап 1.1', 1 + K * 0.5, 'СДП', False)

    add_header('S1_2_HDR', 'Подэтап 1.2 -- Фин. план 1 круг', 'STAGE1', 'Подэтап 1.2')
    add('S1_2_01', 'Фин. план. решение (1 круг)', 'STAGE1', 'Подэтап 1.2', 1 + K * 1, 'Чертежник', True)
    add('S1_2_02', 'Проверка СДП', 'STAGE1', 'Подэтап 1.2', 1 + K * 0.5, 'СДП', False)
    add('S1_2_03', 'Правка чертежником', 'STAGE1', 'Подэтап 1.2', 1 + K * 0.5, 'Чертежник', False)
    add('S1_2_04', 'Проверка повторная СДП', 'STAGE1', 'Подэтап 1.2', 1 + K * 0.5, 'СДП', False)
    add('S1_2_05', 'Отправка клиенту', 'STAGE1', 'Подэтап 1.2', 3, 'Клиент', False)
    add('S1_2_06', 'Сбор правок от клиента СДП', 'STAGE1', 'Подэтап 1.2', 1 + K * 0.5, 'СДП', False)

    add_header('S1_3_HDR', 'Подэтап 1.3 -- Фин. план 2 круг', 'STAGE1', 'Подэтап 1.3')
    add('S1_3_01', 'Фин. план. решение (2 круг)', 'STAGE1', 'Подэтап 1.3', 1 + K * 1, 'Чертежник', False)
    add('S1_3_02', 'Проверка СДП', 'STAGE1', 'Подэтап 1.3', 1 + K * 0.5, 'СДП', False)
    add('S1_3_03', 'Правка чертежником', 'STAGE1', 'Подэтап 1.3', 1 + K * 0.5, 'Чертежник', False)
    add('S1_3_04', 'Проверка СДП', 'STAGE1', 'Подэтап 1.3', 1 + K * 0.5, 'СДП', False)
    add('S1_3_05', 'Согласование планировки. Акт', 'STAGE1', 'Подэтап 1.3', 0, 'Клиент', False)

    # --- ЭТАП 2: КОНЦЕПЦИЯ ДИЗАЙНА ---
    add_header('S2_HDR', 'ЭТАП 2: КОНЦЕПЦИЯ ДИЗАЙНА', 'STAGE2')

    add_header('S2_1_HDR', 'Подэтап 2.1 -- Мудборды', 'STAGE2', 'Подэтап 2.1')
    add('S2_1_01', 'Разработка мудбордов', 'STAGE2', 'Подэтап 2.1', 3 + K * 2, 'Дизайнер', True)
    add('S2_1_02', 'Проверка СДП', 'STAGE2', 'Подэтап 2.1', 1 + K * 1, 'СДП', True)
    add('S2_1_03', 'Правка дизайнером', 'STAGE2', 'Подэтап 2.1', 2 + K * 1, 'Дизайнер', True)
    add('S2_1_04', 'Проверка повторная СДП', 'STAGE2', 'Подэтап 2.1', 1 + K * 0.5, 'СДП', True)
    add('S2_1_05', 'Отправка клиенту', 'STAGE2', 'Подэтап 2.1', 3, 'Клиент', False)
    add('S2_1_06', 'Сбор правок СДП', 'STAGE2', 'Подэтап 2.1', 1 + K * 0.5, 'СДП', False)
    add('S2_1_07', 'Правка дизайнером', 'STAGE2', 'Подэтап 2.1', 1 + K * 1, 'Дизайнер', False)
    add('S2_1_08', 'Проверка СДП', 'STAGE2', 'Подэтап 2.1', 1, 'СДП', False)
    add('S2_1_09', 'Согласование мудборда', 'STAGE2', 'Подэтап 2.1', 0, 'Клиент', False)

    add_header('S2_2_HDR', 'Подэтап 2.2 -- Виз 1 пом.', 'STAGE2', 'Подэтап 2.2')
    add('S2_2_01', 'Разработка визуализации 1 пом.', 'STAGE2', 'Подэтап 2.2', 3 + K * 0.5, 'Дизайнер', True)
    add('S2_2_02', 'Проверка СДП', 'STAGE2', 'Подэтап 2.2', 1, 'СДП', True)
    add('S2_2_03', 'Правка дизайнером', 'STAGE2', 'Подэтап 2.2', 2, 'Дизайнер', True)
    add('S2_2_04', 'Проверка повторная СДП', 'STAGE2', 'Подэтап 2.2', 1, 'СДП', True)
    add('S2_2_05', 'Отправка клиенту', 'STAGE2', 'Подэтап 2.2', 3, 'Клиент', False)
    add('S2_2_06', 'Сбор правок СДП', 'STAGE2', 'Подэтап 2.2', 1, 'СДП', False)

    add_header('S2_3_HDR', 'Подэтап 2.3 -- Виз 1 пом. 1 круг', 'STAGE2', 'Подэтап 2.3')
    add('S2_3_01', 'Правка визуализации (1 круг)', 'STAGE2', 'Подэтап 2.3', 2 + K * 0.5, 'Дизайнер', False)
    add('S2_3_02', 'Проверка СДП', 'STAGE2', 'Подэтап 2.3', 1, 'СДП', False)
    add('S2_3_03', 'Правка дизайнером', 'STAGE2', 'Подэтап 2.3', 1, 'Дизайнер', False)
    add('S2_3_04', 'Проверка повторная СДП', 'STAGE2', 'Подэтап 2.3', 1, 'СДП', False)
    add('S2_3_05', 'Отправка клиенту', 'STAGE2', 'Подэтап 2.3', 3, 'Клиент', False)
    add('S2_3_06', 'Сбор правок СДП', 'STAGE2', 'Подэтап 2.3', 1, 'СДП', False)

    add_header('S2_4_HDR', 'Подэтап 2.4 -- Виз 1 пом. 2 круг', 'STAGE2', 'Подэтап 2.4')
    add('S2_4_01', 'Правка визуализации (2 круг)', 'STAGE2', 'Подэтап 2.4', 1 + K * 1, 'Дизайнер', False)
    add('S2_4_02', 'Проверка СДП', 'STAGE2', 'Подэтап 2.4', 1, 'СДП', False)
    add('S2_4_03', 'Правка дизайнером', 'STAGE2', 'Подэтап 2.4', 1, 'Дизайнер', False)
    add('S2_4_04', 'Проверка СДП', 'STAGE2', 'Подэтап 2.4', 1, 'СДП', False)
    add('S2_4_05', 'Согласование 1 пом.', 'STAGE2', 'Подэтап 2.4', 0, 'Клиент', False)

    add_header('S2_5_HDR', 'Подэтап 2.5 -- Виз остальных', 'STAGE2', 'Подэтап 2.5')
    add('S2_5_01', 'Разработка визуализаций всех', 'STAGE2', 'Подэтап 2.5', 10 + K * 10, 'Дизайнер', True)
    add('S2_5_02', 'Проверка СДП', 'STAGE2', 'Подэтап 2.5', 3 + K * 2.5, 'СДП', True)
    add('S2_5_03', 'Правка дизайнером', 'STAGE2', 'Подэтап 2.5', 5 + K * 5, 'Дизайнер', True)
    add('S2_5_04', 'Проверка повторная СДП', 'STAGE2', 'Подэтап 2.5', 2 + K * 1.5, 'СДП', True)
    add('S2_5_05', 'Отправка клиенту', 'STAGE2', 'Подэтап 2.5', 3, 'Клиент', False)
    add('S2_5_06', 'Сбор правок СДП', 'STAGE2', 'Подэтап 2.5', 2 + K * 1.5, 'СДП', False)

    add_header('S2_6_HDR', 'Подэтап 2.6 -- Виз все 1 круг', 'STAGE2', 'Подэтап 2.6')
    add('S2_6_01', 'Правка визуализаций (1 круг)', 'STAGE2', 'Подэтап 2.6', 5 + K * 5, 'Дизайнер', False)
    add('S2_6_02', 'Проверка СДП', 'STAGE2', 'Подэтап 2.6', 2 + K * 1.5, 'СДП', False)
    add('S2_6_03', 'Правка дизайнером', 'STAGE2', 'Подэтап 2.6', 2 + K * 1.5, 'Дизайнер', False)
    add('S2_6_04', 'Проверка повторная СДП', 'STAGE2', 'Подэтап 2.6', 2 + K * 1.5, 'СДП', False)
    add('S2_6_05', 'Согласование визуализаций', 'STAGE2', 'Подэтап 2.6', 0, 'Клиент', False)

    add_header('S2_7_HDR', 'Подэтап 2.7 -- Виз все 2 круг', 'STAGE2', 'Подэтап 2.7')
    add('S2_7_01', 'Правка визуализаций (2 круг)', 'STAGE2', 'Подэтап 2.7', 3 + K * 3, 'Дизайнер', False)
    add('S2_7_02', 'Проверка СДП', 'STAGE2', 'Подэтап 2.7', 1 + K * 1, 'СДП', False)
    add('S2_7_03', 'Правка дизайнером', 'STAGE2', 'Подэтап 2.7', 1 + K * 1, 'Дизайнер', False)
    add('S2_7_04', 'Проверка СДП', 'STAGE2', 'Подэтап 2.7', 1 + K * 1, 'СДП', False)
    add('S2_7_05', 'Согласование дизайна. Акт', 'STAGE2', 'Подэтап 2.7', 0, 'Клиент', False)

    # --- ЭТАП 3: РАБОЧАЯ ДОКУМЕНТАЦИЯ ---
    add_header('S3_HDR', 'ЭТАП 3: РАБОЧАЯ ДОКУМЕНТАЦИЯ', 'STAGE3')

    add('S3_01', 'Подготовка файлов, выдача', 'STAGE3', '', 1, 'СДП', True)
    add('S3_02', 'Разработка комплекта РД', 'STAGE3', '', 10 + K * 2, 'Чертежник', True)
    add('S3_03', 'Проверка ГАП (1 круг)', 'STAGE3', '', 3 + K * 0.5, 'ГАП', True)
    add('S3_04', 'Правка чертежником', 'STAGE3', '', 2 + K * 1, 'Чертежник', True)
    add('S3_05', 'Проверка ГАП (2 круг)', 'STAGE3', '', 1 + K * 0.5, 'ГАП', True)
    add('S3_06', 'Правка чертежником (при необх.)', 'STAGE3', '', 1, 'Чертежник', True)
    add('S3_07', 'Проверка ГАП (3 круг)', 'STAGE3', '', 1, 'ГАП', True)
    add('S3_08', 'Отправка клиенту', 'STAGE3', '', 3, 'Клиент', False)
    add('S3_09', 'Сбор правок от клиента', 'STAGE3', '', 1 + K * 0.5, 'Менеджер', False)
    add('S3_10', 'Внесение правок чертежником', 'STAGE3', '', 1 + K * 1, 'Чертежник', False)
    add('S3_11', 'Проверка ГАП (4 круг)', 'STAGE3', '', 1 + K * 0.5, 'ГАП', False)
    add('S3_12', 'Принятие проекта. Акт финальный', 'STAGE3', '', 0, 'Клиент', False)

    # Фильтрация по подтипу
    if 'Планировочный' in project_subtype:
        entries = [e for e in entries if e['stage_group'] in ('START', 'STAGE1')]
    elif 'Эскизный' in project_subtype:
        entries = [e for e in entries if e['stage_group'] in ('START', 'STAGE1', 'STAGE3')
                   or (e['stage_group'] == 'STAGE2' and e['substage_group'] == 'Подэтап 2.1')
                   or e['stage_code'] == 'S2_HDR']

    # Перенумерация sort_order
    for i, e in enumerate(entries, 1):
        e['sort_order'] = i

    # Пропорциональный расчет
    _distribute_norm_days(entries, contract_term)
    return entries, contract_term


def _build_template_template(project_subtype: str, area: int):
    """Локальная генерация шаблона для шаблонного проекта."""
    contract_term = _calc_contract_term('Шаблонный', project_subtype, area)

    entries = []
    order = 0

    def add(code, name, group, subgroup, g, executor, in_scope=True):
        nonlocal order
        order += 1
        entries.append({
            'stage_code': code, 'stage_name': name, 'stage_group': group,
            'substage_group': subgroup, 'raw_norm_days': g, 'executor_role': executor,
            'is_in_contract_scope': in_scope, 'sort_order': order,
        })

    def add_header(code, name, group, subgroup=''):
        nonlocal order
        order += 1
        entries.append({
            'stage_code': code, 'stage_name': name, 'stage_group': group,
            'substage_group': subgroup, 'raw_norm_days': 0, 'executor_role': 'header',
            'is_in_contract_scope': False, 'sort_order': order,
        })

    add('START', 'ДАТА НАЧАЛА РАЗРАБОТКИ', 'START', '', 0, 'Менеджер', True)

    # --- СТАДИЯ 1: ПЛАНИРОВОЧНЫЕ РЕШЕНИЯ ---
    add_header('T1_HDR', 'СТАДИЯ 1: ПЛАНИРОВОЧНЫЕ РЕШЕНИЯ', 'STAGE1')

    add_header('T1_1_HDR', 'Подэтап 1.1', 'STAGE1', 'Подэтап 1.1')
    add('T1_1_01', 'Разработка 3 вар. план. решений', 'STAGE1', 'Подэтап 1.1', 3, 'Чертежник', True)
    add('T1_1_02', 'Проверка менеджером', 'STAGE1', 'Подэтап 1.1', 1, 'Менеджер', True)
    add('T1_1_03', 'Правка чертежником', 'STAGE1', 'Подэтап 1.1', 1, 'Чертежник', True)
    add('T1_1_04', 'Проверка повторная менеджером', 'STAGE1', 'Подэтап 1.1', 0.5, 'Менеджер', True)
    add('T1_1_05', 'Отправка клиенту / Согласование', 'STAGE1', 'Подэтап 1.1', 3, 'Клиент', False)
    add('T1_1_06', 'Сбор правок от клиента', 'STAGE1', 'Подэтап 1.1', 1, 'Менеджер', False)

    add_header('T1_2_HDR', 'Подэтап 1.2 -- Финальное план. решение', 'STAGE1', 'Подэтап 1.2')
    add('T1_2_01', 'Финальное план. решение (1 круг)', 'STAGE1', 'Подэтап 1.2', 1, 'Чертежник', True)
    add('T1_2_02', 'Проверка менеджером', 'STAGE1', 'Подэтап 1.2', 1, 'Менеджер', False)
    add('T1_2_03', 'Правка чертежником', 'STAGE1', 'Подэтап 1.2', 1, 'Чертежник', False)
    add('T1_2_04', 'Проверка повторная менеджером', 'STAGE1', 'Подэтап 1.2', 0.5, 'Менеджер', False)
    add('T1_2_05', 'Отправка клиенту / Согласование', 'STAGE1', 'Подэтап 1.2', 3, 'Клиент', False)

    # --- СТАДИЯ 2: РАБОЧИЕ ЧЕРТЕЖИ ---
    add_header('T2_HDR', 'СТАДИЯ 2: РАБОЧИЕ ЧЕРТЕЖИ', 'STAGE2')

    add('T2_01', 'Подготовка файлов, выдача чертежнику', 'STAGE2', '', 1, 'Менеджер', True)
    add('T2_02', 'Разработка комплекта РД', 'STAGE2', '', 5, 'Чертежник', True)
    add('T2_03', 'Проверка ГАП (1 круг)', 'STAGE2', '', 2, 'ГАП', True)
    add('T2_04', 'Правка чертежником', 'STAGE2', '', 1, 'Чертежник', True)
    add('T2_05', 'Проверка ГАП (2 круг)', 'STAGE2', '', 1, 'ГАП', True)
    add('T2_06', 'Правка чертежником (при необх.)', 'STAGE2', '', 1, 'Чертежник', False)
    add('T2_07', 'Проверка ГАП (3 круг)', 'STAGE2', '', 1, 'ГАП', False)
    add('T2_08', 'Отправка клиенту / Согласование', 'STAGE2', '', 3, 'Клиент', False)
    add('T2_09', 'Сбор правок от клиента', 'STAGE2', '', 1, 'Менеджер', False)
    add('T2_10', 'Внесение правок чертежником', 'STAGE2', '', 1, 'Чертежник', False)
    add('T2_11', 'Проверка ГАП (4 круг)', 'STAGE2', '', 1, 'ГАП', False)
    add('T2_12', 'Принятие проекта. Закрытие.', 'STAGE2', '', 0, 'Клиент', False)

    # --- СТАДИЯ 3: 3Д ВИЗУАЛИЗАЦИЯ ---
    has_viz = 'визуализац' in project_subtype.lower()
    if has_viz:
        add_header('T3_HDR', 'СТАДИЯ 3: 3Д ВИЗУАЛИЗАЦИЯ', 'STAGE3')

        add('T3_01', 'Разработка визуализаций всех пом.', 'STAGE3', '', 10, 'Дизайнер', True)
        add('T3_02', 'Проверка менеджером', 'STAGE3', '', 2, 'Менеджер', True)
        add('T3_03', 'Правка дизайнером', 'STAGE3', '', 3, 'Дизайнер', True)
        add('T3_04', 'Проверка повторная менеджером', 'STAGE3', '', 1, 'Менеджер', True)
        add('T3_05', 'Отправка клиенту / Согласование', 'STAGE3', '', 3, 'Клиент', False)
        add('T3_06', 'Принятие проекта. Закрытие.', 'STAGE3', '', 0, 'Клиент', False)

    # Перенумерация sort_order
    for i, e in enumerate(entries, 1):
        e['sort_order'] = i

    _distribute_norm_days(entries, contract_term)
    return entries, contract_term


def _distribute_norm_days(entries: list, contract_term: int):
    """Пропорциональное распределение нормо-дней по записям."""
    in_scope = [
        e for e in entries
        if e['is_in_contract_scope'] and e['executor_role'] != 'header' and e['raw_norm_days'] > 0
    ]
    total_raw = sum(e['raw_norm_days'] for e in in_scope)

    if total_raw > 0 and contract_term > 0:
        cumulative = 0
        prev_rounded = 0
        for e in in_scope:
            cumulative += e['raw_norm_days']
            e['cumulative_days'] = cumulative
            current_rounded = round(cumulative / total_raw * contract_term)
            e['norm_days'] = max(1, current_rounded - prev_rounded) if prev_rounded > 0 else max(1, current_rounded)
            prev_rounded = current_rounded

        total_assigned = sum(e['norm_days'] for e in in_scope)
        if total_assigned != contract_term and in_scope:
            in_scope[-1]['norm_days'] += (contract_term - total_assigned)
            if in_scope[-1]['norm_days'] < 1:
                in_scope[-1]['norm_days'] = 1

    for e in entries:
        if e['executor_role'] == 'header':
            e['norm_days'] = 0
            continue
        if not e['is_in_contract_scope'] and e['raw_norm_days'] > 0:
            e['norm_days'] = max(1, round(e['raw_norm_days']))
        elif 'norm_days' not in e:
            e['norm_days'] = 0


# ================================================================
# Основной виджет
# ================================================================

class NormDaysSettingsWidget(QWidget):
    """Виджет настройки нормо-дней для администрирования."""

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent)
        self.api_client = api_client
        self.data_access = DataAccess(api_client=self.api_client)
        self._entries = []          # текущие данные таблицы
        self._contract_term = 0     # рассчитанный срок договора
        self._is_custom = False     # загружен ли кастомный шаблон
        self._loading = False       # флаг блокировки пересчета при загрузке
        self._init_ui()
        # Первоначальная загрузка данных
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(200, self._on_filters_changed)

    # ================================================================
    # UI
    # ================================================================

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- Верхняя панель фильтров ---
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)

        # Тип проекта
        lbl_type = QLabel('Тип:')
        lbl_type.setStyleSheet('font-size: 12px;')
        filter_layout.addWidget(lbl_type)
        self._combo_type = CustomComboBox()
        self._combo_type.addItems(list(_SUBTYPES.keys()))
        self._combo_type.setMinimumWidth(140)
        self._combo_type.currentTextChanged.connect(self._on_type_changed)
        filter_layout.addWidget(self._combo_type)

        # Подтип проекта
        lbl_sub = QLabel('Подтип:')
        lbl_sub.setStyleSheet('font-size: 12px;')
        filter_layout.addWidget(lbl_sub)
        self._combo_subtype = CustomComboBox()
        self._combo_subtype.setMinimumWidth(220)
        self._combo_subtype.currentTextChanged.connect(self._on_filters_changed)
        filter_layout.addWidget(self._combo_subtype)

        # Площадь (превью) — шкала обновляется динамически при смене типа/подтипа
        lbl_area = QLabel('Площадь:')
        lbl_area.setStyleSheet('font-size: 12px;')
        filter_layout.addWidget(lbl_area)
        self._combo_area = CustomComboBox()
        self._combo_area.setMinimumWidth(70)
        self._combo_area.setMaximumWidth(90)
        self._combo_area.currentTextChanged.connect(self._on_filters_changed)
        filter_layout.addWidget(self._combo_area)

        # Агент (Все агенты / конкретный)
        lbl_agent = QLabel('Агент:')
        lbl_agent.setStyleSheet('font-size: 12px;')
        filter_layout.addWidget(lbl_agent)
        self._combo_agent_type = CustomComboBox()
        self._combo_agent_type.setMinimumWidth(140)
        self._combo_agent_type.currentTextChanged.connect(self._on_filters_changed)
        filter_layout.addWidget(self._combo_agent_type)

        # Срок по договору
        self._label_term = QLabel('Срок: -- дн.')
        self._label_term.setStyleSheet('font-weight: bold; font-size: 12px; color: #333;')
        filter_layout.addWidget(self._label_term)

        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Заполняем подтипы, площади и агентов для первого типа
        self._fill_subtypes()
        self._fill_areas()
        self._fill_agents()

        # --- Таблица ---
        self._table = QTableWidget()
        self._table.setObjectName('norm_days_table')
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels([
            'Этап / Подэтап / Действие', 'Исполнитель', 'Норма дней',
        ])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.verticalHeader().setDefaultSectionSize(28)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionMode(QTableWidget.NoSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: #FFFFFF;
                border: 1px solid #d9d9d9;
                border-radius: 8px;
                gridline-color: #e0e0e0;
            }}
            QTableWidget::item {{
                padding: 2px;
            }}
            QHeaderView::section {{
                background-color: #f5f5f5;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #d9d9d9;
                font-weight: bold;
            }}
            QSpinBox {{
                padding: 1px 2px;
                padding-right: 18px;
                max-height: 22px;
                min-height: 22px;
                border: 1px solid #d9d9d9;
                border-radius: 3px;
                background-color: #FFFFFF;
                font-size: 11px;
            }}
            QSpinBox:hover {{
                border-color: #c0c0c0;
            }}
            QSpinBox:focus {{
                border-color: #ffd93c;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 15px;
                border: none;
                background-color: #F8F9FA;
                border-radius: 2px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: #f5f5f5;
            }}
            QSpinBox::up-arrow {{
                image: url({ICONS_PATH}/arrow-up-circle.svg);
                width: 10px;
                height: 10px;
            }}
            QSpinBox::down-arrow {{
                image: url({ICONS_PATH}/arrow-down-circle.svg);
                width: 10px;
                height: 10px;
            }}
        """)

        layout.addWidget(self._table, 1)

        # --- Нижняя панель ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(12)

        # Сумма
        self._label_sum = QLabel('Сумма (в сроке): -- / -- дней')
        self._label_sum.setStyleSheet('font-size: 12px; font-weight: bold;')
        bottom_layout.addWidget(self._label_sum)

        # Расхождение
        self._label_diff = QLabel('')
        self._label_diff.setStyleSheet('font-size: 11px;')
        bottom_layout.addWidget(self._label_diff)

        bottom_layout.addStretch()

        # Кнопка "Сбросить к формулам"
        self._btn_reset = QPushButton('Сбросить к формулам')
        self._btn_reset.setFixedHeight(36)
        self._btn_reset.setCursor(Qt.PointingHandCursor)
        self._btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                padding: 0px 20px;
                font-weight: bold;
                max-height: 36px;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #f5f5f5; }
            QPushButton:pressed { background-color: #e8e8e8; }
        """)
        self._btn_reset.clicked.connect(self._on_reset)
        bottom_layout.addWidget(self._btn_reset)

        # Кнопка "Сохранить"
        self._btn_save = QPushButton('Сохранить')
        self._btn_save.setFixedHeight(36)
        self._btn_save.setCursor(Qt.PointingHandCursor)
        self._btn_save.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
                max-height: 36px;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #f0c929; }
            QPushButton:pressed { background-color: #e0b919; }
        """)
        self._btn_save.clicked.connect(self._on_save)
        bottom_layout.addWidget(self._btn_save)

        layout.addLayout(bottom_layout)

    # ================================================================
    # Обработчики фильтров
    # ================================================================

    def _fill_subtypes(self):
        """Заполнить подтипы для текущего типа проекта."""
        self._combo_subtype.blockSignals(True)
        self._combo_subtype.clear()
        project_type = self._combo_type.currentText()
        subtypes = _SUBTYPES.get(project_type, [])
        self._combo_subtype.addItems(subtypes)
        self._combo_subtype.blockSignals(False)

    def _fill_areas(self):
        """Обновить шкалу площадей в соответствии с типом/подтипом проекта."""
        self._combo_area.blockSignals(True)
        old_val = self._combo_area.currentText()
        self._combo_area.clear()
        project_type = self._combo_type.currentText()
        project_subtype = self._combo_subtype.currentText()
        areas = _get_areas_for_subtype(project_type, project_subtype)
        if not areas:
            # Фиксированный срок (ванная) — показываем одну запись
            self._combo_area.addItem('--', 0)
        else:
            for i, a in enumerate(areas):
                if i == 0:
                    label = f'до {a}'
                else:
                    label = f'от {areas[i-1]} до {a}'
                self._combo_area.addItem(label, a)
            # Попытка восстановить предыдущий выбор
            idx = self._combo_area.findText(old_val)
            if idx >= 0:
                self._combo_area.setCurrentIndex(idx)
        self._combo_area.blockSignals(False)

    def _fill_agents(self):
        """Заполнить ComboBox агентов: 'Все агенты' + список из БД."""
        self._combo_agent_type.blockSignals(True)
        old_val = self._combo_agent_type.currentText()
        self._combo_agent_type.clear()
        self._combo_agent_type.addItem('Все агенты')
        try:
            agents = self.data_access.get_all_agents()
            for agent in agents:
                name = agent.get('name', '')
                if name:
                    self._combo_agent_type.addItem(name)
        except Exception:
            pass
        # Восстановить предыдущий выбор
        idx = self._combo_agent_type.findText(old_val)
        if idx >= 0:
            self._combo_agent_type.setCurrentIndex(idx)
        self._combo_agent_type.blockSignals(False)

    def _on_type_changed(self):
        """При смене типа проекта — обновить подтипы, площади и перезагрузить."""
        self._fill_subtypes()
        self._fill_areas()
        self._on_filters_changed()

    def _on_filters_changed(self):
        """При смене любого фильтра — обновить площади, срок и загрузить данные."""
        project_type = self._combo_type.currentText()
        project_subtype = self._combo_subtype.currentText()
        area_text = self._combo_area.currentText()
        agent_type = self._combo_agent_type.currentText() or 'Все агенты'

        if not project_subtype:
            return

        # Обновляем шкалу площадей при смене подтипа
        current_areas = _get_areas_for_subtype(project_type, project_subtype)
        combo_count = self._combo_area.count()
        # Перезаполняем площади только если шкала изменилась
        needs_refill = False
        if not current_areas and area_text != '--':
            needs_refill = True
        elif current_areas and (combo_count != len(current_areas)):
            needs_refill = True
        if needs_refill:
            self._fill_areas()
            area_text = self._combo_area.currentText()

        area_data = self._combo_area.currentData()
        if area_data is not None and area_data > 0:
            area = int(area_data)
        elif not area_text or area_text == '--':
            # Фиксированный срок (ванная) — площадь не влияет на срок
            area = 1  # минимальная площадь для корректной работы формул
        else:
            # Fallback для старого формата (чистое число)
            try:
                area = int(area_text)
            except ValueError:
                area = 1

        # Обновляем срок по договору
        self._contract_term = _calc_contract_term(project_type, project_subtype, area)
        self._label_term.setText(f'Срок: {self._contract_term} дней')

        # Загружаем данные
        self._load_data(project_type, project_subtype, area, agent_type)

    # ================================================================
    # Загрузка данных
    # ================================================================

    def _load_data(self, project_type: str, project_subtype: str, area: int, agent_type: str = 'Все агенты'):
        """Загрузить шаблон нормо-дней: сначала пробуем API, затем fallback на локальный расчет."""
        self._is_custom = False

        # 1. Попробовать загрузить кастомный шаблон через DataAccess
        if self.data_access.is_multi_user:
            try:
                data = self.data_access.get_norm_days_template(project_type, project_subtype, agent_type)
                if data and isinstance(data, dict) and data.get('is_custom'):
                    entries = data.get('entries', [])
                    if entries:
                        # Сервер возвращает base_norm_days, конвертируем в norm_days
                        for e in entries:
                            if 'norm_days' not in e and 'base_norm_days' in e:
                                e['norm_days'] = int(round(e['base_norm_days']))
                        self._entries = entries
                        self._is_custom = True
                        self._fill_table()
                        self._update_sum()
                        print(f"[NORM_DAYS] Загружен кастомный шаблон из API: "
                              f"{project_type} / {project_subtype} / {agent_type} ({len(entries)} записей)")
                        return
            except Exception as e:
                print(f"[NORM_DAYS] Ошибка загрузки кастомного шаблона: {e}")

        # 2. Попробовать preview через DataAccess
        if self.data_access.is_multi_user:
            try:
                data = self.data_access.preview_norm_days_template(
                    project_type, project_subtype, area, agent_type
                )
                if data and isinstance(data, dict):
                    self._entries = data.get('entries', [])
                    self._contract_term = data.get('contract_term', self._contract_term)
                    self._label_term.setText(f'Срок: {self._contract_term} дней')
                    self._fill_table()
                    self._update_sum()
                    print(f"[NORM_DAYS] Загружен preview из API: "
                          f"{project_type} / {project_subtype} / {agent_type}, площадь={area}")
                    return
            except Exception as e:
                print(f"[NORM_DAYS] Ошибка preview API: {e}")

        # 3. Fallback — локальный расчет по формулам
        try:
            if project_type == 'Индивидуальный':
                entries, contract_term = _build_individual_template(project_subtype, area)
            else:
                entries, contract_term = _build_template_template(project_subtype, area)

            self._entries = entries
            self._contract_term = contract_term
            self._label_term.setText(f'Срок: {self._contract_term} дней')
            self._fill_table()
            self._update_sum()
            print(f"[NORM_DAYS] Локальный расчет: {project_type} / {project_subtype}, "
                  f"площадь={area}, срок={contract_term}")
        except Exception as e:
            print(f"[NORM_DAYS] Ошибка локального расчета: {e}")
            import traceback
            traceback.print_exc()
            self._table.setRowCount(0)
            self._label_sum.setText('Сумма (в сроке): -- / -- дней')
            self._label_sum.setStyleSheet('font-size: 12px; font-weight: bold; color: #999;')
            self._label_diff.setText('Нет данных')

    # ================================================================
    # Заполнение таблицы
    # ================================================================

    def _fill_table(self):
        """Заполнить таблицу данными из self._entries."""
        self._loading = True
        self._table.setRowCount(0)

        if not self._entries:
            self._loading = False
            return

        self._table.setRowCount(len(self._entries))

        for row, entry in enumerate(self._entries):
            stage_name = entry.get('stage_name', '')
            executor = entry.get('executor_role', '')
            is_header = (executor == 'header')
            is_substage_header = (is_header and entry.get('substage_group', ''))
            is_stage_header = (is_header and not is_substage_header)
            is_in_scope = entry.get('is_in_contract_scope', False)
            norm_days = entry.get('norm_days', 0) or 0

            # --- Колонка 0: Этап / Подэтап / Действие ---
            name_item = QTableWidgetItem(stage_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)

            if is_stage_header:
                # Заголовок этапа — серый фон, bold
                font = QFont()
                font.setBold(True)
                name_item.setFont(font)
                name_item.setBackground(QColor('#f0f0f0'))
            elif is_substage_header:
                # Заголовок подэтапа — светло-голубой фон, bold
                font = QFont()
                font.setBold(True)
                name_item.setFont(font)
                name_item.setBackground(QColor('#f0f7ff'))
            elif not is_in_scope:
                # Не в сроке — серый текст
                name_item.setForeground(QColor('#999999'))

            self._table.setItem(row, 0, name_item)

            # --- Колонка 1: Исполнитель ---
            executor_item = QTableWidgetItem(executor if not is_header else '')
            executor_item.setFlags(executor_item.flags() & ~Qt.ItemIsEditable)

            if is_stage_header:
                executor_item.setBackground(QColor('#f0f0f0'))
            elif is_substage_header:
                executor_item.setBackground(QColor('#f0f7ff'))
            elif not is_in_scope:
                executor_item.setForeground(QColor('#999999'))

            self._table.setItem(row, 1, executor_item)

            # --- Колонка 2: Норма дней ---
            stage_code = entry.get('stage_code', '')
            is_start = (stage_code == 'START')
            if is_header or is_start:
                # Заголовки и START — пустая ячейка (START определяется автоматически)
                empty_item = QTableWidgetItem('')
                empty_item.setFlags(empty_item.flags() & ~Qt.ItemIsEditable)
                if is_stage_header:
                    empty_item.setBackground(QColor('#f0f0f0'))
                elif is_substage_header:
                    empty_item.setBackground(QColor('#f0f7ff'))
                self._table.setItem(row, 2, empty_item)
            else:
                # Обычные строки — QSpinBox
                spin = QSpinBox()
                spin.setRange(0, 999)
                spin.setValue(int(norm_days))
                spin.setFixedHeight(22)
                spin.setProperty('row_index', row)
                spin.valueChanged.connect(self._on_spin_changed)
                self._table.setCellWidget(row, 2, spin)

        self._loading = False

    # ================================================================
    # Обновление суммы
    # ================================================================

    def _on_spin_changed(self, value):
        """При изменении SpinBox — обновить данные и сумму."""
        if self._loading:
            return
        spin = self.sender()
        if spin:
            row_index = spin.property('row_index')
            if row_index is not None and 0 <= row_index < len(self._entries):
                self._entries[row_index]['norm_days'] = value
        self._update_sum()

    def _update_sum(self):
        """Пересчет и отображение суммы нормо-дней в сроке."""
        in_scope_sum = 0
        for entry in self._entries:
            if (entry.get('is_in_contract_scope', False)
                    and entry.get('executor_role') != 'header'
                    and entry.get('raw_norm_days', 0) > 0):
                in_scope_sum += (entry.get('norm_days', 0) or 0)

        diff = in_scope_sum - self._contract_term
        self._label_sum.setText(
            f'Сумма (в сроке): {in_scope_sum} / {self._contract_term} дней'
        )

        if diff == 0:
            self._label_sum.setStyleSheet('font-size: 12px; font-weight: bold; color: #27ae60;')
            self._label_diff.setText('')
            self._label_diff.setStyleSheet('font-size: 11px;')
        else:
            self._label_sum.setStyleSheet('font-size: 12px; font-weight: bold; color: #e74c3c;')
            sign = '+' if diff > 0 else ''
            self._label_diff.setText(f'Расхождение: {sign}{diff} дней')
            self._label_diff.setStyleSheet('font-size: 11px; color: #e74c3c; font-weight: bold;')

    # ================================================================
    # Сохранение
    # ================================================================

    def _on_save(self):
        """Сохранить кастомный шаблон нормо-дней."""
        # Собираем актуальные значения из SpinBox
        self._sync_spinbox_values()

        # Проверяем сумму
        in_scope_sum = 0
        for entry in self._entries:
            if (entry.get('is_in_contract_scope', False)
                    and entry.get('executor_role') != 'header'
                    and entry.get('raw_norm_days', 0) > 0):
                in_scope_sum += (entry.get('norm_days', 0) or 0)

        if in_scope_sum != self._contract_term:
            diff = in_scope_sum - self._contract_term
            sign = '+' if diff > 0 else ''
            CustomMessageBox(
                self,
                'Несовпадение суммы',
                f'Сумма нормо-дней ({in_scope_sum}) не совпадает со сроком по договору '
                f'({self._contract_term}).\n\n'
                f'Расхождение: {sign}{diff} дней.\n\n'
                f'Подкорректируйте нормо-дни.',
                'warning'
            ).exec_()
            return

        # Сохраняем
        if not self.data_access.is_multi_user:
            CustomMessageBox(
                self,
                'Ошибка',
                'API клиент недоступен. Сохранение невозможно.',
                'error'
            ).exec_()
            return

        project_type = self._combo_type.currentText()
        project_subtype = self._combo_subtype.currentText()
        agent_type = self._combo_agent_type.currentText() or 'Все агенты'

        # Конвертируем entries для API: norm_days -> base_norm_days
        api_entries = []
        for e in self._entries:
            api_entry = {
                'stage_code': e.get('stage_code', ''),
                'stage_name': e.get('stage_name', ''),
                'stage_group': e.get('stage_group', ''),
                'substage_group': e.get('substage_group', ''),
                'base_norm_days': float(e.get('norm_days', 0)),
                'k_multiplier': e.get('k_multiplier', 0.0),
                'executor_role': e.get('executor_role', ''),
                'is_in_contract_scope': e.get('is_in_contract_scope', True),
                'sort_order': e.get('sort_order', 0),
            }
            api_entries.append(api_entry)

        data = {
            'project_type': project_type,
            'project_subtype': project_subtype,
            'agent_type': agent_type,
            'entries': api_entries,
        }

        try:
            self.data_access.save_norm_days_template(data)
            self._is_custom = True
            CustomMessageBox(
                self,
                'Успех',
                f'Шаблон нормо-дней сохранен:\n\n'
                f'{project_type} / {project_subtype} / {agent_type}\n'
                f'Сумма в сроке: {in_scope_sum} дней',
                'success'
            ).exec_()
            print(f"[NORM_DAYS] Шаблон сохранен: {project_type} / {project_subtype} / {agent_type}")
        except Exception as e:
            print(f"[NORM_DAYS] Ошибка сохранения: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(
                self,
                'Ошибка',
                f'Не удалось сохранить шаблон:\n{str(e)}',
                'error'
            ).exec_()

    def _sync_spinbox_values(self):
        """Синхронизировать значения из SpinBox обратно в self._entries."""
        for row in range(self._table.rowCount()):
            spin = self._table.cellWidget(row, 2)
            if spin and isinstance(spin, QSpinBox) and row < len(self._entries):
                self._entries[row]['norm_days'] = spin.value()

    # ================================================================
    # Сброс к формулам
    # ================================================================

    def _on_reset(self):
        """Сбросить кастомный шаблон и пересчитать по формулам."""
        project_type = self._combo_type.currentText()
        project_subtype = self._combo_subtype.currentText()
        area_text = self._combo_area.currentText()
        agent_type = self._combo_agent_type.currentText() or 'Все агенты'

        if not project_subtype or not area_text:
            return

        area_data = self._combo_area.currentData()
        if area_data is not None and area_data > 0:
            area = int(area_data)
        elif area_text == '--':
            area = 1
        else:
            try:
                area = int(area_text)
            except ValueError:
                area = 1

        # Сбрасываем кастомный шаблон через DataAccess
        if self.data_access.is_multi_user and self._is_custom:
            try:
                self.data_access.reset_norm_days_template(project_type, project_subtype, agent_type)
                print(f"[NORM_DAYS] Кастомный шаблон сброшен: {project_type} / {project_subtype} / {agent_type}")
            except Exception as e:
                print(f"[NORM_DAYS] Ошибка сброса кастомного шаблона: {e}")

        # Пересчитываем по формулам
        self._is_custom = False
        try:
            if project_type == 'Индивидуальный':
                entries, contract_term = _build_individual_template(project_subtype, area)
            else:
                entries, contract_term = _build_template_template(project_subtype, area)

            self._entries = entries
            self._contract_term = contract_term
            self._label_term.setText(f'Срок: {self._contract_term} дней')
            self._fill_table()
            self._update_sum()
            print(f"[NORM_DAYS] Сброс к формулам: {project_type} / {project_subtype}, "
                  f"площадь={area}, срок={contract_term}")
        except Exception as e:
            print(f"[NORM_DAYS] Ошибка сброса: {e}")
            import traceback
            traceback.print_exc()
