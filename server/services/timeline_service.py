"""
Сервис расчёта таблиц сроков (Timeline).
Чистые функции для генерации шаблонов и расчёта нормо-дней.
"""
import logging
from database import SessionLocal, NormDaysTemplate

logger = logging.getLogger(__name__)


def calc_contract_term(project_type_code: int, area: float):
    """Расчёт срока договора. 1=Полный, 2=Эскизный, 3=Планировочный"""
    if project_type_code == 1:
        thresholds = [(70,50),(100,60),(130,70),(160,80),(190,90),(220,100),
                      (250,110),(300,120),(350,130),(400,140),(450,150),(500,160)]
    elif project_type_code == 3:
        thresholds = [(70,10),(100,15),(130,20),(160,25),(190,30),(220,35),
                      (250,40),(300,45),(350,50),(400,55),(450,60),(500,65)]
    else:
        thresholds = [(70,30),(100,35),(130,40),(160,45),(190,50),(220,55),
                      (250,60),(300,65),(350,70),(400,75),(450,80),(500,85)]
    for max_area, days in thresholds:
        if area <= max_area:
            return days
    return 0  # индивидуальный расчёт


def calc_area_coefficient(area: float) -> int:
    return max(0, int((area - 1) // 100))


def build_project_timeline_template(project_type: str, area: float, project_subtype: str = None):
    """Генерация полного шаблона подэтапов с формулами.
    project_subtype: 'Полный (с 3д визуализацией)', 'Эскизный (с коллажами)', 'Планировочный'
    """
    K = calc_area_coefficient(area)
    # Определяем pt_code из project_subtype (если задан)
    if project_subtype:
        if 'Полный' in project_subtype:
            pt_code = 1
        elif 'Планировочный' in project_subtype:
            pt_code = 3
        else:
            pt_code = 2
    else:
        pt_code = 1 if project_type == 'Индивидуальный' else 2
    contract_term = calc_contract_term(pt_code, area)

    # Все подэтапы: (stage_code, stage_name, stage_group, substage_group, raw_G, executor, in_scope)
    entries = []
    order = 0

    def add(code, name, group, subgroup, g, executor, in_scope=True):
        nonlocal order
        order += 1
        entries.append({
            'stage_code': code, 'stage_name': name, 'stage_group': group,
            'substage_group': subgroup, 'raw_norm_days': g, 'executor_role': executor,
            'is_in_contract_scope': in_scope, 'sort_order': order
        })

    def add_header(code, name, group, subgroup=''):
        nonlocal order
        order += 1
        entries.append({
            'stage_code': code, 'stage_name': name, 'stage_group': group,
            'substage_group': subgroup, 'raw_norm_days': 0, 'executor_role': 'header',
            'is_in_contract_scope': False, 'sort_order': order
        })

    # --- ДАТА НАЧАЛА ---
    add('START', 'ДАТА НАЧАЛА РАЗРАБОТКИ', 'START', '', 0, 'Менеджер', True)

    # --- ЭТАП 1: ПЛАНИРОВОЧНОЕ РЕШЕНИЕ ---
    add_header('S1_HDR', 'ЭТАП 1: ПЛАНИРОВОЧНОЕ РЕШЕНИЕ', 'STAGE1')

    # Подэтап 1.1 — входит
    add_header('S1_1_HDR', 'Подэтап 1.1', 'STAGE1', 'Подэтап 1.1')
    add('S1_1_01', 'Разработка 3 вар. планировок', 'STAGE1', 'Подэтап 1.1', 4 + K*2, 'Чертежник', True)
    add('S1_1_02', 'Проверка СДП', 'STAGE1', 'Подэтап 1.1', 1 + K*0.5, 'СДП', True)
    add('S1_1_03', 'Правка чертежником', 'STAGE1', 'Подэтап 1.1', 1.5 + K*1, 'Чертежник', True)
    add('S1_1_04', 'Проверка повторная СДП', 'STAGE1', 'Подэтап 1.1', 0.5 + K*0.5, 'СДП', True)
    add('S1_1_05', 'Отправка клиенту', 'STAGE1', 'Подэтап 1.1', 3, 'Клиент', False)
    add('S1_1_06', 'Сбор правок от клиента СДП', 'STAGE1', 'Подэтап 1.1', 1 + K*0.5, 'СДП', False)

    # Подэтап 1.2 — не входит
    add_header('S1_2_HDR', 'Подэтап 1.2 — Фин. план 1 круг', 'STAGE1', 'Подэтап 1.2')
    add('S1_2_01', 'Фин. план. решение (1 круг)', 'STAGE1', 'Подэтап 1.2', 1 + K*1, 'Чертежник', True)
    add('S1_2_02', 'Проверка СДП', 'STAGE1', 'Подэтап 1.2', 1 + K*0.5, 'СДП', False)
    add('S1_2_03', 'Правка чертежником', 'STAGE1', 'Подэтап 1.2', 1 + K*0.5, 'Чертежник', False)
    add('S1_2_04', 'Проверка повторная СДП', 'STAGE1', 'Подэтап 1.2', 1 + K*0.5, 'СДП', False)
    add('S1_2_05', 'Отправка клиенту', 'STAGE1', 'Подэтап 1.2', 3, 'Клиент', False)
    add('S1_2_06', 'Сбор правок от клиента СДП', 'STAGE1', 'Подэтап 1.2', 1 + K*0.5, 'СДП', False)

    # Подэтап 1.3 — не входит
    add_header('S1_3_HDR', 'Подэтап 1.3 — Фин. план 2 круг', 'STAGE1', 'Подэтап 1.3')
    add('S1_3_01', 'Фин. план. решение (2 круг)', 'STAGE1', 'Подэтап 1.3', 1 + K*1, 'Чертежник', False)
    add('S1_3_02', 'Проверка СДП', 'STAGE1', 'Подэтап 1.3', 1 + K*0.5, 'СДП', False)
    add('S1_3_03', 'Правка чертежником', 'STAGE1', 'Подэтап 1.3', 1 + K*0.5, 'Чертежник', False)
    add('S1_3_04', 'Проверка СДП', 'STAGE1', 'Подэтап 1.3', 1 + K*0.5, 'СДП', False)
    add('S1_3_05', 'Согласование планировки. Акт', 'STAGE1', 'Подэтап 1.3', 0, 'Клиент', False)

    # --- ЭТАП 2: КОНЦЕПЦИЯ ДИЗАЙНА ---
    add_header('S2_HDR', 'ЭТАП 2: КОНЦЕПЦИЯ ДИЗАЙНА', 'STAGE2')

    # 2.1 Мудборды
    add_header('S2_1_HDR', 'Подэтап 2.1 — Мудборды', 'STAGE2', 'Подэтап 2.1')
    add('S2_1_01', 'Разработка мудбордов', 'STAGE2', 'Подэтап 2.1', 3 + K*2, 'Дизайнер', True)
    add('S2_1_02', 'Проверка СДП', 'STAGE2', 'Подэтап 2.1', 1 + K*1, 'СДП', True)
    add('S2_1_03', 'Правка дизайнером', 'STAGE2', 'Подэтап 2.1', 2 + K*1, 'Дизайнер', True)
    add('S2_1_04', 'Проверка повторная СДП', 'STAGE2', 'Подэтап 2.1', 1 + K*0.5, 'СДП', True)
    add('S2_1_05', 'Отправка клиенту', 'STAGE2', 'Подэтап 2.1', 3, 'Клиент', False)
    add('S2_1_06', 'Сбор правок СДП', 'STAGE2', 'Подэтап 2.1', 1 + K*0.5, 'СДП', False)
    add('S2_1_07', 'Правка дизайнером', 'STAGE2', 'Подэтап 2.1', 1 + K*1, 'Дизайнер', False)
    add('S2_1_08', 'Проверка СДП', 'STAGE2', 'Подэтап 2.1', 1, 'СДП', False)
    add('S2_1_09', 'Согласование мудборда', 'STAGE2', 'Подэтап 2.1', 0, 'Клиент', False)

    # 2.2 Виз 1 пом.
    add_header('S2_2_HDR', 'Подэтап 2.2 — Виз 1 пом.', 'STAGE2', 'Подэтап 2.2')
    add('S2_2_01', 'Разработка визуализации 1 пом.', 'STAGE2', 'Подэтап 2.2', 3 + K*0.5, 'Дизайнер', True)
    add('S2_2_02', 'Проверка СДП', 'STAGE2', 'Подэтап 2.2', 1, 'СДП', True)
    add('S2_2_03', 'Правка дизайнером', 'STAGE2', 'Подэтап 2.2', 2, 'Дизайнер', True)
    add('S2_2_04', 'Проверка повторная СДП', 'STAGE2', 'Подэтап 2.2', 1, 'СДП', True)
    add('S2_2_05', 'Отправка клиенту', 'STAGE2', 'Подэтап 2.2', 3, 'Клиент', False)
    add('S2_2_06', 'Сбор правок СДП', 'STAGE2', 'Подэтап 2.2', 1, 'СДП', False)

    # 2.3 Виз 1 пом. 1 круг — не входит
    add_header('S2_3_HDR', 'Подэтап 2.3 — Виз 1 пом. 1 круг', 'STAGE2', 'Подэтап 2.3')
    add('S2_3_01', 'Правка визуализации (1 круг)', 'STAGE2', 'Подэтап 2.3', 2 + K*0.5, 'Дизайнер', False)
    add('S2_3_02', 'Проверка СДП', 'STAGE2', 'Подэтап 2.3', 1, 'СДП', False)
    add('S2_3_03', 'Правка дизайнером', 'STAGE2', 'Подэтап 2.3', 1, 'Дизайнер', False)
    add('S2_3_04', 'Проверка повторная СДП', 'STAGE2', 'Подэтап 2.3', 1, 'СДП', False)
    add('S2_3_05', 'Отправка клиенту', 'STAGE2', 'Подэтап 2.3', 3, 'Клиент', False)
    add('S2_3_06', 'Сбор правок СДП', 'STAGE2', 'Подэтап 2.3', 1, 'СДП', False)

    # 2.4 Виз 1 пом. 2 круг — не входит
    add_header('S2_4_HDR', 'Подэтап 2.4 — Виз 1 пом. 2 круг', 'STAGE2', 'Подэтап 2.4')
    add('S2_4_01', 'Правка визуализации (2 круг)', 'STAGE2', 'Подэтап 2.4', 1 + K*1, 'Дизайнер', False)
    add('S2_4_02', 'Проверка СДП', 'STAGE2', 'Подэтап 2.4', 1, 'СДП', False)
    add('S2_4_03', 'Правка дизайнером', 'STAGE2', 'Подэтап 2.4', 1, 'Дизайнер', False)
    add('S2_4_04', 'Проверка СДП', 'STAGE2', 'Подэтап 2.4', 1, 'СДП', False)
    add('S2_4_05', 'Согласование 1 пом.', 'STAGE2', 'Подэтап 2.4', 0, 'Клиент', False)

    # 2.5 Виз остальных — входит
    add_header('S2_5_HDR', 'Подэтап 2.5 — Виз остальных', 'STAGE2', 'Подэтап 2.5')
    add('S2_5_01', 'Разработка визуализаций всех', 'STAGE2', 'Подэтап 2.5', 10 + K*10, 'Дизайнер', True)
    add('S2_5_02', 'Проверка СДП', 'STAGE2', 'Подэтап 2.5', 3 + K*2.5, 'СДП', True)
    add('S2_5_03', 'Правка дизайнером', 'STAGE2', 'Подэтап 2.5', 5 + K*5, 'Дизайнер', True)
    add('S2_5_04', 'Проверка повторная СДП', 'STAGE2', 'Подэтап 2.5', 2 + K*1.5, 'СДП', True)
    add('S2_5_05', 'Отправка клиенту', 'STAGE2', 'Подэтап 2.5', 3, 'Клиент', False)
    add('S2_5_06', 'Сбор правок СДП', 'STAGE2', 'Подэтап 2.5', 2 + K*1.5, 'СДП', False)

    # 2.6 Виз все 1 круг — не входит
    add_header('S2_6_HDR', 'Подэтап 2.6 — Виз все 1 круг', 'STAGE2', 'Подэтап 2.6')
    add('S2_6_01', 'Правка визуализаций (1 круг)', 'STAGE2', 'Подэтап 2.6', 5 + K*5, 'Дизайнер', False)
    add('S2_6_02', 'Проверка СДП', 'STAGE2', 'Подэтап 2.6', 2 + K*1.5, 'СДП', False)
    add('S2_6_03', 'Правка дизайнером', 'STAGE2', 'Подэтап 2.6', 2 + K*1.5, 'Дизайнер', False)
    add('S2_6_04', 'Проверка повторная СДП', 'STAGE2', 'Подэтап 2.6', 2 + K*1.5, 'СДП', False)
    add('S2_6_05', 'Согласование визуализаций', 'STAGE2', 'Подэтап 2.6', 0, 'Клиент', False)

    # 2.7 Виз все 2 круг — не входит
    add_header('S2_7_HDR', 'Подэтап 2.7 — Виз все 2 круг', 'STAGE2', 'Подэтап 2.7')
    add('S2_7_01', 'Правка визуализаций (2 круг)', 'STAGE2', 'Подэтап 2.7', 3 + K*3, 'Дизайнер', False)
    add('S2_7_02', 'Проверка СДП', 'STAGE2', 'Подэтап 2.7', 1 + K*1, 'СДП', False)
    add('S2_7_03', 'Правка дизайнером', 'STAGE2', 'Подэтап 2.7', 1 + K*1, 'Дизайнер', False)
    add('S2_7_04', 'Проверка СДП', 'STAGE2', 'Подэтап 2.7', 1 + K*1, 'СДП', False)
    add('S2_7_05', 'Согласование дизайна. Акт', 'STAGE2', 'Подэтап 2.7', 0, 'Клиент', False)

    # --- ЭТАП 3: РАБОЧАЯ ДОКУМЕНТАЦИЯ ---
    add_header('S3_HDR', 'ЭТАП 3: РАБОЧАЯ ДОКУМЕНТАЦИЯ', 'STAGE3')

    add('S3_01', 'Подготовка файлов, выдача', 'STAGE3', '', 1, 'СДП', True)
    add('S3_02', 'Разработка комплекта РД', 'STAGE3', '', 10 + K*2, 'Чертежник', True)
    add('S3_03', 'Проверка ГАП (1 круг)', 'STAGE3', '', 3 + K*0.5, 'ГАП', True)
    add('S3_04', 'Правка чертежником', 'STAGE3', '', 2 + K*1, 'Чертежник', True)
    add('S3_05', 'Проверка ГАП (2 круг)', 'STAGE3', '', 1 + K*0.5, 'ГАП', True)
    add('S3_06', 'Правка чертежником (при необх.)', 'STAGE3', '', 1, 'Чертежник', True)
    add('S3_07', 'Проверка ГАП (3 круг)', 'STAGE3', '', 1, 'ГАП', True)
    add('S3_08', 'Отправка клиенту', 'STAGE3', '', 3, 'Клиент', False)
    add('S3_09', 'Сбор правок от клиента', 'STAGE3', '', 1 + K*0.5, 'Менеджер', False)
    add('S3_10', 'Внесение правок чертежником', 'STAGE3', '', 1 + K*1, 'Чертежник', False)
    add('S3_11', 'Проверка ГАП (4 круг)', 'STAGE3', '', 1 + K*0.5, 'ГАП', False)
    add('S3_12', 'Принятие проекта. Акт финальный', 'STAGE3', '', 0, 'Клиент', False)

    # --- Фильтрация по подтипу проекта ---
    if project_subtype and 'Планировочный' in project_subtype:
        # Только START + STAGE1
        entries = [e for e in entries if e['stage_group'] in ('START', 'STAGE1')]
    elif project_subtype and 'Эскизный' in project_subtype:
        # START + STAGE1 + мудборды (Подэтап 2.1) + STAGE3
        entries = [e for e in entries if e['stage_group'] in ('START', 'STAGE1', 'STAGE3')
                   or (e['stage_group'] == 'STAGE2' and e['substage_group'] == 'Подэтап 2.1')
                   or e['stage_code'] == 'S2_HDR']
    # Полный / None — все этапы

    # Перенумерация sort_order после фильтрации
    for i, e in enumerate(entries, 1):
        e['sort_order'] = i

    # Проверяем кастомный шаблон нормо-дней в БД
    try:
        db_session = SessionLocal()
        custom = db_session.query(NormDaysTemplate).filter(
            NormDaysTemplate.project_type == 'Индивидуальный',
            NormDaysTemplate.project_subtype == (project_subtype or 'Полный (с 3д визуализацией)'),
        ).all()
        db_session.close()
        if custom:
            custom_map = {c.stage_code: c for c in custom}
            for e in entries:
                if e['stage_code'] in custom_map:
                    c = custom_map[e['stage_code']]
                    e['raw_norm_days'] = c.base_norm_days + K * c.k_multiplier
    except Exception:
        pass  # Fallback на хардкод-формулы

    # Пропорциональный расчёт норм
    in_scope = [e for e in entries if e['is_in_contract_scope'] and e['executor_role'] != 'header' and e['raw_norm_days'] > 0]
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

        # Корректировка: сумма in-scope = contract_term
        total_assigned = sum(e['norm_days'] for e in in_scope)
        if total_assigned != contract_term and in_scope:
            in_scope[-1]['norm_days'] += (contract_term - total_assigned)
            if in_scope[-1]['norm_days'] < 1:
                in_scope[-1]['norm_days'] = 1

    # Не в сроке: norm = max(1, round(raw))
    for e in entries:
        if e['executor_role'] == 'header':
            e['norm_days'] = 0
            continue
        if not e['is_in_contract_scope'] and e['raw_norm_days'] > 0:
            e['norm_days'] = max(1, round(e['raw_norm_days']))

    return entries, contract_term, K


def calc_template_contract_term(template_subtype: str, area: float, floors: int = 1) -> int:
    """Расчёт срока для шаблонных проектов (рабочие дни)"""
    sub = template_subtype.lower()
    if 'ванной' in sub:
        if 'визуализац' in sub:
            return 20
        return 10

    # Стандарт / Стандарт с визуализацией
    if area <= 90:
        base_days = 20
    else:
        extra = int((area - 90 - 1) // 50) + 1
        base_days = 20 + extra * 10

    # Доп. этажи
    if floors > 1:
        for _ in range(1, floors):
            if area <= 90:
                base_days += 10
            else:
                extra = int((area - 90 - 1) // 50) + 1
                base_days += 10 + extra * 10

    # Визуализация
    if 'визуализац' in sub:
        if area <= 90:
            base_days += 25
        else:
            extra = int((area - 90 - 1) // 50) + 1
            base_days += 25 + extra * 15

    return int(base_days)


def build_template_project_timeline(template_subtype: str, area: float, floors: int = 1):
    """Генерация шаблона таблицы сроков для шаблонных проектов.
    template_subtype: 'Стандарт', 'Стандарт с визуализацией',
                      'Проект ванной комнаты', 'Проект ванной комнаты с визуализацией'
    """
    contract_term = calc_template_contract_term(template_subtype, area, floors)
    entries = []
    order = 0

    def add(code, name, group, subgroup, g, executor, in_scope=True):
        nonlocal order
        order += 1
        entries.append({
            'stage_code': code, 'stage_name': name, 'stage_group': group,
            'substage_group': subgroup, 'raw_norm_days': g, 'executor_role': executor,
            'is_in_contract_scope': in_scope, 'sort_order': order
        })

    def add_header(code, name, group, subgroup=''):
        nonlocal order
        order += 1
        entries.append({
            'stage_code': code, 'stage_name': name, 'stage_group': group,
            'substage_group': subgroup, 'raw_norm_days': 0, 'executor_role': 'header',
            'is_in_contract_scope': False, 'sort_order': order
        })

    # --- ДАТА НАЧАЛА ---
    add('START', 'ДАТА НАЧАЛА РАЗРАБОТКИ', 'START', '', 0, 'Менеджер', True)

    # --- СТАДИЯ 1: ПЛАНИРОВОЧНЫЕ РЕШЕНИЯ ---
    add_header('T1_HDR', 'СТАДИЯ 1: ПЛАНИРОВОЧНЫЕ РЕШЕНИЯ', 'STAGE1')

    # Подэтап 1.1
    add_header('T1_1_HDR', 'Подэтап 1.1', 'STAGE1', 'Подэтап 1.1')
    add('T1_1_01', 'Разработка 3 вар. план. решений', 'STAGE1', 'Подэтап 1.1', 3, 'Чертежник', True)
    add('T1_1_02', 'Проверка менеджером', 'STAGE1', 'Подэтап 1.1', 1, 'Менеджер', True)
    add('T1_1_03', 'Правка чертежником', 'STAGE1', 'Подэтап 1.1', 1, 'Чертежник', True)
    add('T1_1_04', 'Проверка повторная менеджером', 'STAGE1', 'Подэтап 1.1', 0.5, 'Менеджер', True)
    add('T1_1_05', 'Отправка клиенту / Согласование', 'STAGE1', 'Подэтап 1.1', 3, 'Клиент', False)
    add('T1_1_06', 'Сбор правок от клиента', 'STAGE1', 'Подэтап 1.1', 1, 'Менеджер', False)

    # Подэтап 1.2
    add_header('T1_2_HDR', 'Подэтап 1.2 — Финальное план. решение', 'STAGE1', 'Подэтап 1.2')
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

    # --- СТАДИЯ 3: 3Д ВИЗУАЛИЗАЦИЯ (только для подтипов с визуализацией) ---
    has_viz = 'визуализац' in template_subtype.lower()
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

    # Проверяем кастомный шаблон нормо-дней в БД
    try:
        db_session = SessionLocal()
        custom = db_session.query(NormDaysTemplate).filter(
            NormDaysTemplate.project_type == 'Шаблонный',
            NormDaysTemplate.project_subtype == template_subtype,
        ).all()
        db_session.close()
        if custom:
            custom_map = {c.stage_code: c for c in custom}
            for e in entries:
                if e['stage_code'] in custom_map:
                    c = custom_map[e['stage_code']]
                    # Для шаблонных проектов K=0 (нет коэффициента площади)
                    e['raw_norm_days'] = c.base_norm_days + 0 * c.k_multiplier
    except Exception:
        pass  # Fallback на хардкод-формулы

    # Пропорциональный расчёт норм
    in_scope = [e for e in entries if e['is_in_contract_scope'] and e['executor_role'] != 'header' and e['raw_norm_days'] > 0]
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

        # Корректировка: сумма in-scope = contract_term
        total_assigned = sum(e['norm_days'] for e in in_scope)
        if total_assigned != contract_term and in_scope:
            in_scope[-1]['norm_days'] += (contract_term - total_assigned)
            if in_scope[-1]['norm_days'] < 1:
                in_scope[-1]['norm_days'] = 1

    # Не в сроке: norm = max(1, round(raw))
    for e in entries:
        if e['executor_role'] == 'header':
            e['norm_days'] = 0
            continue
        if not e['is_in_contract_scope'] and e['raw_norm_days'] > 0:
            e['norm_days'] = max(1, round(e['raw_norm_days']))

    return entries, contract_term, 0
