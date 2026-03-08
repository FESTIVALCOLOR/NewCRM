# -*- coding: utf-8 -*-
"""
Фаза 2: Тесты расчёта сроков (Timeline).

Проверяет РЕЗУЛЬТАТЫ:
- calc_area_coefficient: коэффициент K по площади
- calc_contract_term: срок договора по площади и типу
- networkdays: рабочие дни между датами (с праздниками РФ)
- add_working_days: добавление рабочих дней к дате
- calculate_deadline: START дата проекта (max из трёх дат)
- calc_planned_dates: цепочка планируемых дат
- Пропорциональное распределение norm_days
- Согласованность двух реализаций add_working_days

ЛОВИТ БАГИ:
1. Неправильный коэффициент K → все нормо-дни неверны
2. Неправильный contract_term → дедлайн проекта сдвинут
3. Не учтены праздники → рабочие дни завышены
4. Площадь на границе (100, 200, 500 м²) → K ±1
5. Сумма norm_days ≠ contract_term → дедлайн сдвигается
6. working_days_between vs networkdays → расхождение из-за праздников
"""
import pytest
import sys
import os
from datetime import datetime, date, timedelta
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Мокируем серверную базу данных ПЕРЕД импортом timeline_service
# (SessionLocal и NormDaysTemplate недоступны на клиенте)
_mock_db = MagicMock()
_mock_db.SessionLocal.return_value.__enter__ = MagicMock(return_value=MagicMock())
_mock_db.SessionLocal.return_value.__exit__ = MagicMock(return_value=False)
_saved_database = sys.modules.get('database')
sys.modules['database'] = _mock_db

# Теперь импортируем серверные функции
from server.services.timeline_service import (
    calc_area_coefficient,
    calc_contract_term,
    build_project_timeline_template,
)

# Восстанавливаем database модуль
if _saved_database is not None:
    sys.modules['database'] = _saved_database
else:
    del sys.modules['database']
# Чистим кешированный модуль timeline_service чтобы не отравлять другие тесты
if 'server.services.timeline_service' in sys.modules:
    del sys.modules['server.services.timeline_service']


# ======================================================================
# КОЭФФИЦИЕНТ K (ПЛОЩАДЬ)
# ======================================================================

class TestAreaCoefficient:
    """calc_area_coefficient: K = max(0, int((area-1) // 100))"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.calc_K = calc_area_coefficient

    def test_area_1(self):
        """Минимальная площадь 1 м² → K=0."""
        assert self.calc_K(1) == 0

    def test_area_50(self):
        """Маленькая площадь 50 м² → K=0."""
        assert self.calc_K(50) == 0

    def test_area_100(self):
        """Граница 100 м² → K=0 (т.к. (100-1)//100=0)."""
        assert self.calc_K(100) == 0

    def test_area_101(self):
        """101 м² → K=1 (первый переход)."""
        assert self.calc_K(101) == 1

    def test_area_200(self):
        """200 м² → K=1 (т.к. (200-1)//100=1)."""
        assert self.calc_K(200) == 1

    def test_area_201(self):
        """201 м² → K=2."""
        assert self.calc_K(201) == 2

    def test_area_300(self):
        """300 м² → K=2."""
        assert self.calc_K(300) == 2

    def test_area_500(self):
        """500 м² → K=4."""
        assert self.calc_K(500) == 4

    def test_area_501(self):
        """501 м² → K=5."""
        assert self.calc_K(501) == 5

    def test_area_1000(self):
        """Очень большая площадь 1000 м² → K=9."""
        assert self.calc_K(1000) == 9

    def test_area_zero(self):
        """Нулевая площадь → K=0 (не отрицательный)."""
        assert self.calc_K(0) == 0

    def test_area_negative(self):
        """Отрицательная площадь → K=0 (не отрицательный)."""
        assert self.calc_K(-50) == 0

    def test_monotonicity(self):
        """K монотонно растёт с площадью."""
        areas = [1, 50, 100, 101, 200, 201, 300, 400, 500, 600, 1000]
        K_values = [self.calc_K(a) for a in areas]
        for i in range(len(K_values) - 1):
            assert K_values[i] <= K_values[i + 1], (
                f"K({areas[i]})={K_values[i]} > K({areas[i+1]})={K_values[i+1]} — "
                f"коэффициент НЕ монотонный!"
            )


# ======================================================================
# СРОК ДОГОВОРА (CONTRACT TERM)
# ======================================================================

class TestContractTerm:
    """calc_contract_term: срок в рабочих днях по площади и типу проекта."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.calc_term = calc_contract_term

    # --- Полный проект (pt_code=1) ---

    def test_full_area_70(self):
        """Полный, 70 м² → 50 дней."""
        assert self.calc_term(1, 70) == 50

    def test_full_area_100(self):
        """Полный, 100 м² → 60 дней."""
        assert self.calc_term(1, 100) == 60

    def test_full_area_150(self):
        """Полный, 150 м² → 80 дней (попадает в (130,160] диапазон)."""
        assert self.calc_term(1, 150) == 80

    def test_full_area_500(self):
        """Полный, 500 м² → 160 дней (максимум таблицы)."""
        assert self.calc_term(1, 500) == 160

    def test_full_area_501(self):
        """Полный, >500 м² → 0 (индивидуальный расчёт)."""
        assert self.calc_term(1, 501) == 0

    def test_full_area_1(self):
        """Полный, 1 м² → 50 дней (попадает в первый диапазон ≤70)."""
        assert self.calc_term(1, 1) == 50

    # --- Эскизный проект (pt_code=2) ---

    def test_sketch_area_70(self):
        """Эскизный, 70 м² → 30 дней."""
        assert self.calc_term(2, 70) == 30

    def test_sketch_area_100(self):
        """Эскизный, 100 м² → 35 дней."""
        assert self.calc_term(2, 100) == 35

    def test_sketch_area_500(self):
        """Эскизный, 500 м² → 85 дней."""
        assert self.calc_term(2, 500) == 85

    def test_sketch_area_501(self):
        """Эскизный, >500 м² → 0."""
        assert self.calc_term(2, 501) == 0

    # --- Планировочный проект (pt_code=3) ---

    def test_planning_area_70(self):
        """Планировочный, 70 м² → 10 дней."""
        assert self.calc_term(3, 70) == 10

    def test_planning_area_100(self):
        """Планировочный, 100 м² → 15 дней."""
        assert self.calc_term(3, 100) == 15

    def test_planning_area_500(self):
        """Планировочный, 500 м² → 65 дней."""
        assert self.calc_term(3, 500) == 65

    # --- Граничные значения ---

    def test_boundary_exact_70(self):
        """Граница 70 м² — попадает в первый диапазон."""
        assert self.calc_term(1, 70) == 50

    def test_boundary_71(self):
        """71 м² — попадает во второй диапазон (≤100)."""
        assert self.calc_term(1, 71) == 60

    def test_boundary_exact_100(self):
        """Граница 100 м² — ≤100 → 60."""
        assert self.calc_term(1, 100) == 60

    def test_boundary_101(self):
        """101 м² — следующий диапазон (≤130)."""
        assert self.calc_term(1, 101) == 70

    def test_all_thresholds_full(self):
        """Все пороги Полного проекта."""
        expected = [
            (70, 50), (100, 60), (130, 70), (160, 80), (190, 90), (220, 100),
            (250, 110), (300, 120), (350, 130), (400, 140), (450, 150), (500, 160)
        ]
        for area, days in expected:
            assert self.calc_term(1, area) == days, (
                f"Полный проект, area={area} → ожидали {days} дней"
            )

    def test_term_monotonicity(self):
        """Срок монотонно растёт с площадью (в пределах таблицы)."""
        areas = [50, 70, 100, 130, 160, 190, 220, 250, 300, 350, 400, 450, 500]
        for pt_code in [1, 2, 3]:
            terms = [self.calc_term(pt_code, a) for a in areas]
            for i in range(len(terms) - 1):
                assert terms[i] <= terms[i + 1], (
                    f"pt={pt_code}, area={areas[i]}→{terms[i]} > area={areas[i+1]}→{terms[i+1]}"
                )


# ======================================================================
# РАБОЧИЕ ДНИ (NETWORKDAYS)
# ======================================================================

class TestNetworkdays:
    """networkdays: рабочие дни между двумя датами с учётом праздников РФ."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from utils.date_utils import networkdays, is_working_day
        self.networkdays = networkdays
        self.is_working_day = is_working_day

    def test_same_day(self):
        """Одна и та же дата → 0 дней."""
        assert self.networkdays('2026-03-02', '2026-03-02') == 0

    def test_weekday_to_next_weekday(self):
        """Пн→Вт = 1 рабочий день."""
        assert self.networkdays('2026-03-02', '2026-03-03') == 1  # Пн→Вт

    def test_full_work_week(self):
        """Пн→Пт = 4 рабочих дня (не считая конец)."""
        assert self.networkdays('2026-03-02', '2026-03-06') == 4  # Пн→Пт

    def test_over_weekend(self):
        """Пт→Пн = 1 рабочий день (Пт считается, Сб-Вс нет)."""
        assert self.networkdays('2026-03-06', '2026-03-09') == 1  # Пт→Пн

    def test_two_weeks(self):
        """2 недели = 10 рабочих дней."""
        assert self.networkdays('2026-03-02', '2026-03-16') == 10  # Пн→Пн+14дн

    def test_through_march_8(self):
        """Через 8 Марта (праздник) — не считается."""
        # 8 марта 2027 = понедельник (праздник)
        # networkdays('2027-03-05', '2027-03-09'):
        # 5(Пт-раб), 6(Сб-нет), 7(Вс-нет), 8(Пн-праздник) = 1 рабочий день
        assert self.networkdays('2027-03-05', '2027-03-09') == 1  # 8 марта — праздник

    def test_new_year_holidays(self):
        """Новогодние праздники 1-8 января — все нерабочие."""
        # 2026-12-31 (Ср) → 2026-01-12 (Пн):
        # Проверим январь 2026: 1-8 праздники, 9(Пт)=рабочий
        # 2025-12-31 (Ср) → 2026-01-12 (Пн)
        # 31 дек (Ср-раб), 1-8 янв (праздники), 9(Пт-раб), 10(Сб), 11(Вс)
        # = 2 рабочих дня (31 дек + 9 янв)
        assert self.networkdays('2025-12-31', '2026-01-12') == 2

    def test_end_before_start(self):
        """end < start → 0 дней."""
        assert self.networkdays('2026-03-10', '2026-03-05') == 0

    def test_none_dates(self):
        """None даты → 0."""
        assert self.networkdays(None, '2026-03-10') == 0
        assert self.networkdays('2026-03-10', None) == 0

    def test_empty_string(self):
        """Пустые строки → 0."""
        assert self.networkdays('', '2026-03-10') == 0

    def test_string_dates(self):
        """Принимает строки 'YYYY-MM-DD'."""
        result = self.networkdays('2026-03-02', '2026-03-06')
        assert isinstance(result, int)
        assert result == 4

    def test_datetime_dates(self):
        """Принимает datetime объекты."""
        start = datetime(2026, 3, 2)
        end = datetime(2026, 3, 6)
        assert self.networkdays(start, end) == 4

    def test_february_23_holiday(self):
        """23 февраля — праздник."""
        # 2026-02-23 = понедельник
        assert self.is_working_day(date(2026, 2, 23)) is False

    def test_may_1_holiday(self):
        """1 мая — праздник."""
        # Проверим что 1 мая всегда нерабочий
        assert self.is_working_day(date(2026, 5, 1)) is False

    def test_may_9_holiday(self):
        """9 мая — праздник."""
        assert self.is_working_day(date(2026, 5, 9)) is False

    def test_june_12_holiday(self):
        """12 июня — праздник."""
        assert self.is_working_day(date(2026, 6, 12)) is False

    def test_november_4_holiday(self):
        """4 ноября — праздник."""
        assert self.is_working_day(date(2026, 11, 4)) is False

    def test_regular_weekday(self):
        """Обычный вторник — рабочий день."""
        assert self.is_working_day(date(2026, 3, 3)) is True

    def test_saturday_not_working(self):
        """Суббота — нерабочий день."""
        assert self.is_working_day(date(2026, 3, 7)) is False

    def test_sunday_not_working(self):
        """Воскресенье — нерабочий день."""
        assert self.is_working_day(date(2026, 3, 8)) is False


# ======================================================================
# ДОБАВЛЕНИЕ РАБОЧИХ ДНЕЙ
# ======================================================================

class TestAddWorkingDays:
    """add_working_days из date_utils: добавляет рабочие дни к дате."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from utils.date_utils import add_working_days
        self.add_days = add_working_days

    def test_add_1_weekday(self):
        """Пн + 1 рабочий день = Вт."""
        result = self.add_days('2026-03-02', 1)  # Пн
        assert result.day == 3  # Вт

    def test_add_5_from_monday(self):
        """Пн + 5 рабочих дней = Пн следующей недели."""
        result = self.add_days('2026-03-02', 5)  # Пн
        assert result.day == 9  # Следующий Пн

    def test_add_1_from_friday(self):
        """Пт + 1 рабочий день = Пн (пропуск Сб-Вс)."""
        result = self.add_days('2026-03-06', 1)  # Пт
        assert result.day == 9  # Пн

    def test_add_through_new_year(self):
        """Добавление через новогодние праздники (1-8 января)."""
        # 31 дек 2025 (Ср) + 1 рабочий день = 9 января 2026 (Пт)
        result = self.add_days('2025-12-31', 1)
        assert result.month == 1
        assert result.day == 9

    def test_add_zero_days(self):
        """0 рабочих дней → та же дата."""
        result = self.add_days('2026-03-02', 0)
        assert result == datetime(2026, 3, 2)

    def test_string_input(self):
        """Принимает строку 'YYYY-MM-DD'."""
        result = self.add_days('2026-03-02', 3)
        assert isinstance(result, datetime)

    def test_datetime_input(self):
        """Принимает datetime объект."""
        result = self.add_days(datetime(2026, 3, 2), 3)
        assert isinstance(result, datetime)

    def test_add_50_days(self):
        """50 рабочих дней от 2 марта 2026."""
        result = self.add_days('2026-03-02', 50)
        # 50 рабочих дней ≈ 10 недель = ~70 календарных
        # + праздники (1 мая, 9 мая) = ещё +2
        # Проверяем что результат > start + 65 календарных дней
        start = datetime(2026, 3, 2)
        assert result > start + timedelta(days=65)
        assert result < start + timedelta(days=80)


# ======================================================================
# ДОБАВЛЕНИЕ РАБОЧИХ ДНЕЙ (calendar_helpers)
# ======================================================================

class TestAddWorkingDaysCalendarHelpers:
    """add_working_days из calendar_helpers: строковый вариант."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from utils.calendar_helpers import add_working_days
        self.add_days = add_working_days

    def test_returns_string(self):
        """Возвращает строку 'YYYY-MM-DD'."""
        result = self.add_days('2026-03-02', 1)
        assert isinstance(result, str)
        assert result == '2026-03-03'

    def test_add_1_from_friday(self):
        """Пт + 1 = Пн (пропуск выходных)."""
        result = self.add_days('2026-03-06', 1)
        assert result == '2026-03-09'

    def test_add_through_holiday(self):
        """Через новогодние → пропускает 1-8 января."""
        result = self.add_days('2025-12-31', 1)
        assert result == '2026-01-09'

    def test_zero_days(self):
        """0 дней → та же дата (строка)."""
        result = self.add_days('2026-03-02', 0)
        assert result == '2026-03-02'

    def test_empty_date(self):
        """Пустая строка → пустая строка."""
        result = self.add_days('', 5)
        assert result == ''

    def test_none_date(self):
        """None → пустая строка."""
        result = self.add_days(None, 5)
        assert result == ''


# ======================================================================
# СОГЛАСОВАННОСТЬ ДВУХ РЕАЛИЗАЦИЙ
# ======================================================================

class TestAddWorkingDaysConsistency:
    """Две реализации add_working_days ДОЛЖНЫ давать одинаковый результат."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from utils.date_utils import add_working_days as date_utils_add
        from utils.calendar_helpers import add_working_days as calendar_add
        self.date_utils_add = date_utils_add
        self.calendar_add = calendar_add

    @pytest.mark.parametrize("start,days", [
        ('2026-03-02', 1),
        ('2026-03-02', 5),
        ('2026-03-06', 1),   # Пт → через выходные
        ('2025-12-31', 1),   # через Новый год
        ('2026-02-22', 3),   # через 23 февраля
        ('2026-03-02', 50),  # через 1 мая, 9 мая
        ('2026-03-02', 10),
    ])
    def test_both_implementations_agree(self, start, days):
        """date_utils и calendar_helpers дают одинаковую дату."""
        result_dt = self.date_utils_add(start, days)
        result_str = self.calendar_add(start, days)
        # date_utils возвращает datetime, calendar_helpers — строку
        assert result_dt.strftime('%Y-%m-%d') == result_str, (
            f"РАСХОЖДЕНИЕ! start={start}, days={days}: "
            f"date_utils={result_dt.strftime('%Y-%m-%d')}, "
            f"calendar_helpers={result_str}"
        )


# ======================================================================
# РЕГРЕССИЯ: working_days_between ДОЛЖНА учитывать праздники
# (Исправлено: теперь использует is_working_day вместо weekday() < 5)
# ======================================================================

class TestWorkingDaysBetweenVsNetworkdays:
    """working_days_between (calendar_helpers) vs networkdays (date_utils).

    РЕГРЕССИОННЫЕ ТЕСТЫ: working_days_between теперь учитывает RUSSIAN_HOLIDAYS.
    Обе функции ДОЛЖНЫ давать одинаковый результат.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        from utils.date_utils import networkdays
        from utils.calendar_helpers import working_days_between
        self.networkdays = networkdays
        self.working_days_between = working_days_between

    def test_no_holidays_same_result(self):
        """Без праздников — обе функции совпадают."""
        nd = self.networkdays('2026-03-02', '2026-03-06')
        wdb = self.working_days_between('2026-03-02', '2026-03-06')
        assert nd == wdb, (
            f"Без праздников: networkdays={nd}, working_days_between={wdb}"
        )

    def test_regression_feb_23_holiday(self):
        """РЕГРЕССИЯ: 23 февраля — working_days_between ДОЛЖНА пропустить праздник.

        Был баг: working_days_between использовал weekday() < 5, не учитывая
        RUSSIAN_HOLIDAYS. 23 февраля (Пн) считался рабочим.
        Исправлено: теперь использует is_working_day().

        СЕМАНТИКА РАЗЛИЧАЕТСЯ:
        - networkdays(start, end): считает рабочие дни [start, end) (start вкл, end нет)
        - working_days_between(start, end): считает рабочие дни (start, end] (start нет, end вкл)
        Поэтому прямое сравнение корректно только когда start и end — оба рабочие дни.

        Тест проверяет что is_working_day используется через прямую проверку:
        """
        from utils.date_utils import is_working_day
        # 23 февраля 2026 = понедельник (будний день-праздник)
        assert is_working_day(date(2026, 2, 23)) is False, "23 февраля должен быть нерабочим"

        # working_days_between('2026-02-20', '2026-02-24'):
        # (start=20 Пт), считаем: 21(Сб-нет), 22(Вс-нет), 23(Пн-праздник-нет), 24(Вт-да) = 1
        wdb = self.working_days_between('2026-02-20', '2026-02-24')
        assert wdb == 1, (
            f"РЕГРЕССИЯ! working_days_between через 23 февраля = {wdb}, ожидали 1. "
            f"working_days_between снова не учитывает RUSSIAN_HOLIDAYS!"
        )

    def test_regression_may_1_holiday(self):
        """РЕГРЕССИЯ: 1 мая — working_days_between ДОЛЖНА пропустить праздник."""
        # working_days_between('2026-04-30', '2026-05-04'):
        # (start=30 Чт), считаем: 1(Пт-праздник-нет), 2(Сб-нет), 3(Вс-нет), 4(Пн-да) = 1
        wdb = self.working_days_between('2026-04-30', '2026-05-04')
        assert wdb == 1, (
            f"РЕГРЕССИЯ! working_days_between через 1 мая = {wdb}, ожидали 1."
        )

    def test_regression_may_9_holiday(self):
        """РЕГРЕССИЯ: 9 мая — working_days_between ДОЛЖНА пропустить праздник."""
        # working_days_between('2026-05-08', '2026-05-11'):
        # (start=8 Пт), считаем: 9(Сб-нет), 10(Вс-нет), 11(Пн-да) = 1
        # Но 9 мая 2026 = суббота, так что тут праздник и так не рабочий.
        # Лучше: working_days_between('2027-05-07', '2027-05-11'):
        # 2027-05-09 = воскресенье. Тоже выходной.
        # Проверим через общий assert: 1 мая достаточно, а 9 мая проверим напрямую
        from utils.date_utils import is_working_day
        assert is_working_day(date(2026, 5, 9)) is False

    def test_regression_new_year_holidays(self):
        """РЕГРЕССИЯ: новогодние каникулы (1-8 января)."""
        # working_days_between('2025-12-31', '2026-01-12'):
        # (start=31 Ср), считаем: 1-8 янв (праздники, нет), 9(Пт-да), 10(Сб-нет), 11(Вс-нет), 12(Пн-да) = 2
        wdb = self.working_days_between('2025-12-31', '2026-01-12')
        assert wdb == 2, (
            f"РЕГРЕССИЯ! working_days_between через новогодние каникулы = {wdb}, ожидали 2."
        )

    def test_regression_june_12_holiday(self):
        """РЕГРЕССИЯ: 12 июня — День России."""
        from utils.date_utils import is_working_day
        # 12 июня 2026 = пятница
        assert is_working_day(date(2026, 6, 12)) is False, "12 июня должен быть нерабочим"
        # working_days_between('2026-06-11', '2026-06-15'):
        # (start=11 Чт), считаем: 12(Пт-праздник-нет), 13(Сб-нет), 14(Вс-нет), 15(Пн-да) = 1
        wdb = self.working_days_between('2026-06-11', '2026-06-15')
        assert wdb == 1, (
            f"РЕГРЕССИЯ! working_days_between через 12 июня = {wdb}, ожидали 1."
        )

    def test_regression_november_4_holiday(self):
        """РЕГРЕССИЯ: 4 ноября — День народного единства."""
        from utils.date_utils import is_working_day
        # 4 ноября 2026 = среда
        assert is_working_day(date(2026, 11, 4)) is False, "4 ноября должен быть нерабочим"
        # working_days_between('2026-11-03', '2026-11-05'):
        # (start=3 Вт), считаем: 4(Ср-праздник-нет), 5(Чт-да) = 1
        wdb = self.working_days_between('2026-11-03', '2026-11-05')
        assert wdb == 1, (
            f"РЕГРЕССИЯ! working_days_between через 4 ноября = {wdb}, ожидали 1."
        )


# ======================================================================
# CALCULATE DEADLINE (START ДАТА)
# ======================================================================

class TestCalculateDeadline:
    """calculate_deadline: max(contract_date, survey_date, tech_task_date) + рабочие дни."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from utils.date_utils import calculate_deadline
        self.calc_deadline = calculate_deadline

    def test_all_three_dates(self):
        """Все 3 даты → берётся максимальная."""
        result = self.calc_deadline(
            '2026-01-15',  # contract_date
            '2026-01-20',  # survey_date (максимум)
            '2026-01-18',  # tech_task_date
            10             # рабочих дней
        )
        assert result is not None
        # START = 20 января (Вт), + 10 раб дней:
        # 21(Ср), 22(Чт), 23(Пт), 26(Пн), 27(Вт), 28(Ср), 29(Чт), 30(Пт), 2(Пн), 3(Вт)
        assert result.month == 2
        assert result.day == 3

    def test_contract_date_is_max(self):
        """contract_date — максимальная."""
        result = self.calc_deadline('2026-03-01', '2026-02-01', '2026-02-15', 1)
        # START = 1 марта (Вс) → +1 раб день = 2 марта (Пн)
        assert result.month == 3
        assert result.day == 2

    def test_survey_date_none(self):
        """survey_date=None → игнорируется."""
        result = self.calc_deadline('2026-01-15', None, '2026-01-20', 5)
        assert result is not None
        # max(15, 20) = 20 января

    def test_tech_task_date_none(self):
        """tech_task_date=None → игнорируется."""
        result = self.calc_deadline('2026-01-15', '2026-01-20', None, 5)
        assert result is not None

    def test_all_dates_same(self):
        """Все даты одинаковые."""
        result = self.calc_deadline('2026-03-02', '2026-03-02', '2026-03-02', 5)
        assert result is not None
        assert result.day == 9  # Пн + 5 = Пн

    def test_only_contract_date(self):
        """Только contract_date, остальные None."""
        result = self.calc_deadline('2026-03-02', None, None, 5)
        assert result is not None
        assert result.day == 9

    def test_all_dates_none(self):
        """Все даты None → None."""
        result = self.calc_deadline(None, None, None, 10)
        assert result is None

    def test_contract_period_zero(self):
        """contract_period=0 → None."""
        result = self.calc_deadline('2026-03-02', None, None, 0)
        assert result is None

    def test_contract_period_negative(self):
        """contract_period < 0 → None."""
        result = self.calc_deadline('2026-03-02', None, None, -5)
        assert result is None

    def test_datetime_input(self):
        """Принимает datetime объекты."""
        result = self.calc_deadline(
            datetime(2026, 3, 2), datetime(2026, 3, 5), None, 1
        )
        assert result is not None
        assert result.day == 6  # 5(Чт) + 1 = 6(Пт)


# ======================================================================
# ПРОПОРЦИОНАЛЬНОЕ РАСПРЕДЕЛЕНИЕ NORM_DAYS
# ======================================================================

class TestNormDaysDistribution:
    """Пропорциональное распределение norm_days: сумма in-scope = contract_term."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.build_template = build_project_timeline_template

    def _in_scope_entries(self, entries):
        """Отфильтровать записи в сроке (in_scope, не header, norm_days>0)."""
        return [
            e for e in entries
            if e.get('is_in_contract_scope')
            and e.get('executor_role') != 'header'
            and e.get('norm_days', 0) > 0
        ]

    def test_sum_equals_contract_term_area_100(self):
        """Сумма norm_days in-scope = contract_term для 100 м²."""
        entries, contract_term, K = self.build_template('Индивидуальный', 100)
        in_scope = self._in_scope_entries(entries)
        total = sum(e['norm_days'] for e in in_scope)
        assert total == contract_term, (
            f"СУММА norm_days={total} ≠ contract_term={contract_term} для area=100 м²!"
        )

    def test_sum_equals_contract_term_area_200(self):
        """Сумма norm_days in-scope = contract_term для 200 м²."""
        entries, contract_term, K = self.build_template('Индивидуальный', 200)
        in_scope = self._in_scope_entries(entries)
        total = sum(e['norm_days'] for e in in_scope)
        assert total == contract_term, (
            f"СУММА norm_days={total} ≠ contract_term={contract_term} для area=200 м²!"
        )

    def test_sum_equals_contract_term_area_400(self):
        """Сумма norm_days in-scope = contract_term для 400 м²."""
        entries, contract_term, K = self.build_template('Индивидуальный', 400)
        in_scope = self._in_scope_entries(entries)
        total = sum(e['norm_days'] for e in in_scope)
        assert total == contract_term

    def test_min_norm_days_is_1(self):
        """Каждый in-scope подэтап получает ≥ 1 дня."""
        entries, contract_term, K = self.build_template('Индивидуальный', 70)
        in_scope = self._in_scope_entries(entries)
        for e in in_scope:
            assert e['norm_days'] >= 1, (
                f"{e['stage_code']} получил norm_days={e['norm_days']} < 1!"
            )

    def test_headers_have_zero_norm_days(self):
        """Заголовки всегда имеют norm_days=0."""
        entries, _, _ = self.build_template('Индивидуальный', 100)
        for e in entries:
            if e['executor_role'] == 'header':
                assert e.get('norm_days', 0) == 0, (
                    f"Header {e['stage_code']} имеет norm_days={e['norm_days']}!"
                )

    def test_K_affects_raw_norm_days(self):
        """Больший K → большие raw_norm_days."""
        entries_100, _, K_100 = self.build_template('Индивидуальный', 100)
        entries_300, _, K_300 = self.build_template('Индивидуальный', 300)

        # Найдём подэтап S2_5_01 (10 + K*10) — зависит от K
        raw_100 = None
        raw_300 = None
        for e in entries_100:
            if e['stage_code'] == 'S2_5_01':
                raw_100 = e['raw_norm_days']
        for e in entries_300:
            if e['stage_code'] == 'S2_5_01':
                raw_300 = e['raw_norm_days']

        assert raw_100 is not None and raw_300 is not None
        assert raw_300 > raw_100, (
            f"S2_5_01: raw_norm_days(K={K_100})={raw_100} >= "
            f"raw_norm_days(K={K_300})={raw_300}!"
        )

    def test_sketch_project_no_viz(self):
        """Эскизный проект — нет визуализаций (Подэтап 2.2+)."""
        entries, _, _ = self.build_template(
            'Индивидуальный', 100, 'Эскизный (с коллажами)'
        )
        stage_codes = {e['stage_code'] for e in entries}
        # Эскизный содержит STAGE1 + мудборды (2.1) + STAGE3
        assert 'S1_1_01' in stage_codes, "Эскизный должен содержать STAGE1"
        assert 'S3_02' in stage_codes, "Эскизный должен содержать STAGE3"
        # Не должно быть визуализаций 2.2+
        assert 'S2_2_01' not in stage_codes, (
            "Эскизный НЕ должен содержать визуализации (Подэтап 2.2)!"
        )

    def test_planning_project_only_stage1(self):
        """Планировочный проект — только START + STAGE1."""
        entries, _, _ = self.build_template(
            'Индивидуальный', 100, 'Планировочный'
        )
        groups = {e['stage_group'] for e in entries}
        assert 'START' in groups
        assert 'STAGE1' in groups
        assert 'STAGE2' not in groups, "Планировочный НЕ должен содержать STAGE2!"
        assert 'STAGE3' not in groups, "Планировочный НЕ должен содержать STAGE3!"


# ======================================================================
# РАСЧЁТ ПЛАНИРУЕМЫХ ДАТ
# ======================================================================

class TestCalcPlannedDates:
    """calc_planned_dates: цепочка планируемых дат по подэтапам."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from utils.timeline_calc import calc_planned_dates
        self.calc_planned = calc_planned_dates

    def test_start_gets_actual_date(self):
        """START получает _planned_date = actual_date."""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-03-02',
             'executor_role': 'Менеджер', 'norm_days': 0},
        ]
        result = self.calc_planned(entries)
        assert result[0]['_planned_date'] == '2026-03-02'

    def test_chain_calculation(self):
        """Цепочка: START + norm_days каждого шага."""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-03-02',
             'executor_role': 'Менеджер', 'norm_days': 0},
            {'stage_code': 'S1_1_01', 'actual_date': '',
             'executor_role': 'Чертежник', 'norm_days': 4},
            {'stage_code': 'S1_1_02', 'actual_date': '',
             'executor_role': 'СДП', 'norm_days': 1},
        ]
        result = self.calc_planned(entries)
        # START: planned = 2026-03-02
        # S1_1_01: 2026-03-02 + 4 рабочих = 2026-03-06 (Пт)
        # S1_1_02: 2026-03-06 + 1 рабочий = 2026-03-09 (Пн)
        assert result[1]['_planned_date'] == '2026-03-06'
        assert result[2]['_planned_date'] == '2026-03-09'

    def test_actual_date_overrides_chain(self):
        """actual_date обновляет prev_date для следующих подэтапов."""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-03-02',
             'executor_role': 'Менеджер', 'norm_days': 0},
            {'stage_code': 'S1_1_01', 'actual_date': '2026-03-10',  # Фактическая!
             'executor_role': 'Чертежник', 'norm_days': 4},
            {'stage_code': 'S1_1_02', 'actual_date': '',
             'executor_role': 'СДП', 'norm_days': 2},
        ]
        result = self.calc_planned(entries)
        # S1_1_01: planned = 2026-03-06, но actual = 2026-03-10
        # S1_1_02: prev = 2026-03-10 (actual), + 2 = 2026-03-12 (Чт)
        assert result[2]['_planned_date'] == '2026-03-12'

    def test_header_skipped(self):
        """Header строки пропускаются."""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-03-02',
             'executor_role': 'Менеджер', 'norm_days': 0},
            {'stage_code': 'S1_HDR', 'actual_date': '',
             'executor_role': 'header', 'norm_days': 0},
            {'stage_code': 'S1_1_01', 'actual_date': '',
             'executor_role': 'Чертежник', 'norm_days': 3},
        ]
        result = self.calc_planned(entries)
        # Header не должен сломать цепочку
        assert result[2]['_planned_date'] == '2026-03-05'

    def test_zero_norm_inherits_date(self):
        """norm_days=0 → наследует prev_date без смещения."""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-03-02',
             'executor_role': 'Менеджер', 'norm_days': 0},
            {'stage_code': 'S1_1_01', 'actual_date': '',
             'executor_role': 'Чертежник', 'norm_days': 0},
        ]
        result = self.calc_planned(entries)
        # norm_days=0 → planned = prev_date = 2026-03-02
        assert result[1]['_planned_date'] == '2026-03-02'

    def test_custom_norm_days_priority(self):
        """custom_norm_days переопределяет norm_days."""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-03-02',
             'executor_role': 'Менеджер', 'norm_days': 0},
            {'stage_code': 'S1_1_01', 'actual_date': '',
             'executor_role': 'Чертежник', 'norm_days': 4, 'custom_norm_days': 10},
        ]
        result = self.calc_planned(entries)
        # custom_norm_days=10 вместо norm_days=4
        # 2026-03-02 + 10 раб дней = 2026-03-16 (Пн)
        assert result[1]['_planned_date'] == '2026-03-16'

    def test_no_start_date(self):
        """Без START.actual_date → все пустые."""
        entries = [
            {'stage_code': 'START', 'actual_date': '',
             'executor_role': 'Менеджер', 'norm_days': 0},
            {'stage_code': 'S1_1_01', 'actual_date': '',
             'executor_role': 'Чертежник', 'norm_days': 4},
        ]
        result = self.calc_planned(entries)
        assert result[1]['_planned_date'] == ''


# ======================================================================
# ИНТЕГРАЦИЯ: ПОЛНЫЙ ЦИКЛ РАСЧЁТА
# ======================================================================

class TestFullTimelineCalculation:
    """Полный цикл: area → K → raw_norm → norm_days → planned_dates."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.build_template = build_project_timeline_template
        from utils.timeline_calc import calc_planned_dates
        self.calc_planned = calc_planned_dates

    def test_full_cycle_area_100(self):
        """Полный цикл для 100 м²: K=0, contract_term=60."""
        entries, contract_term, K = self.build_template('Индивидуальный', 100)

        assert K == 0
        assert contract_term == 60

        # Устанавливаем START дату
        for e in entries:
            if e['stage_code'] == 'START':
                e['actual_date'] = '2026-03-02'
                break

        # Рассчитываем planned_dates
        result = self.calc_planned(entries)

        # Проверяем что START получил дату
        start_entry = next(e for e in result if e['stage_code'] == 'START')
        assert start_entry['_planned_date'] == '2026-03-02'

        # Проверяем что все non-header записи с norm_days>0 получили planned_date
        for e in result:
            if e['executor_role'] != 'header' and e['stage_code'] != 'START':
                if e.get('norm_days', 0) > 0:
                    assert e.get('_planned_date'), (
                        f"{e['stage_code']} не получил planned_date! "
                        f"norm_days={e['norm_days']}"
                    )

    def test_full_cycle_area_300(self):
        """Полный цикл для 300 м²: K=2, contract_term=120."""
        entries, contract_term, K = self.build_template('Индивидуальный', 300)

        assert K == 2
        assert contract_term == 120

        # Устанавливаем START дату
        for e in entries:
            if e['stage_code'] == 'START':
                e['actual_date'] = '2026-03-02'
                break

        result = self.calc_planned(entries)

        # Последний подэтап in-scope должен быть в будущем
        in_scope = [
            e for e in result
            if e.get('is_in_contract_scope') and e['executor_role'] != 'header'
            and e.get('_planned_date')
        ]
        if in_scope:
            last_date_str = in_scope[-1]['_planned_date']
            assert last_date_str > '2026-03-02', (
                f"Последний подэтап {in_scope[-1]['stage_code']} "
                f"запланирован на {last_date_str} — раньше START!"
            )

    def test_planned_dates_monotonic(self):
        """Planned dates монотонно растут (каждый следующий ≥ предыдущий)."""
        entries, _, _ = self.build_template('Индивидуальный', 150)

        for e in entries:
            if e['stage_code'] == 'START':
                e['actual_date'] = '2026-03-02'
                break

        result = self.calc_planned(entries)

        prev_date = ''
        for e in result:
            if e['executor_role'] == 'header':
                continue
            planned = e.get('_planned_date', '')
            if planned and prev_date:
                assert planned >= prev_date, (
                    f"Немонотонность! {e['stage_code']}: {planned} < предыдущий {prev_date}"
                )
            if planned:
                prev_date = planned


# ======================================================================
# RAW NORM DAYS — ФОРМУЛЫ ДЛЯ КОНКРЕТНЫХ ПОДЭТАПОВ
# ======================================================================

class TestRawNormDaysFormulas:
    """Проверка формул raw_norm_days для конкретных подэтапов."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.build_template = build_project_timeline_template

    def _get_entry(self, entries, code):
        for e in entries:
            if e['stage_code'] == code:
                return e
        return None

    def test_s1_1_01_formula(self):
        """S1_1_01: raw = 4 + K*2."""
        for area, K_expected in [(100, 0), (200, 1), (300, 2)]:
            entries, _, K = self.build_template('Индивидуальный', area)
            assert K == K_expected
            e = self._get_entry(entries, 'S1_1_01')
            assert e is not None
            expected_raw = 4 + K * 2
            assert e['raw_norm_days'] == expected_raw, (
                f"S1_1_01 при K={K}: raw={e['raw_norm_days']} ≠ {expected_raw}"
            )

    def test_s2_5_01_formula(self):
        """S2_5_01 (Визуализации все): raw = 10 + K*10."""
        for area, K_expected in [(100, 0), (200, 1), (500, 4)]:
            entries, _, K = self.build_template('Индивидуальный', area)
            e = self._get_entry(entries, 'S2_5_01')
            assert e is not None
            expected_raw = 10 + K * 10
            assert e['raw_norm_days'] == expected_raw

    def test_s3_02_formula(self):
        """S3_02 (Комплект РД): raw = 10 + K*2."""
        for area, K_expected in [(100, 0), (300, 2)]:
            entries, _, K = self.build_template('Индивидуальный', area)
            e = self._get_entry(entries, 'S3_02')
            assert e is not None
            expected_raw = 10 + K * 2
            assert e['raw_norm_days'] == expected_raw

    def test_client_steps_fixed(self):
        """Шаги клиента ('Отправка клиенту') = фиксированные 3 дня, не зависят от K."""
        entries, _, K = self.build_template('Индивидуальный', 300)
        for code in ['S1_1_05', 'S2_1_05', 'S2_2_05']:
            e = self._get_entry(entries, code)
            if e:
                assert e['raw_norm_days'] == 3, (
                    f"{code} (Отправка клиенту) = {e['raw_norm_days']} ≠ 3 при K={K}"
                )
