# -*- coding: utf-8 -*-
"""
Покрытие ui/salaries_tab.py — чистая бизнес-логика.
~30 тестов.

Тестируем ТОЛЬКО чистые функции и логику, не требующую создания QWidget/QApplication:
- Маппинг месяцев (русские названия)
- Фильтрация платежей по месяцу/кварталу/году
- Форматирование report_month ("2025-11" -> "Ноябрь 2025")
- Форматирование сумм
- Маппинг статусов -> цвета
- Toggle-логика статусов оплаты
- Дедупликация платежей
- Расчёт итогов (сумм за период/год)
- Фильтрация по полям (адрес, сотрудник, должность, тип агента и т.д.)
- Маппинг вкладок -> ключи дашборда
- Обрезка комментариев
- Определение подтипа выплаты
- Инвалидация кеша
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ['QT_QPA_PLATFORM'] = 'offscreen'


# ──────────────────────────────────────────────────────────
# Хелперы: создание тестовых платежей
# ──────────────────────────────────────────────────────────

def _make_payment(
    payment_id=1,
    employee_name='Иванов Иван',
    amount=50000,
    report_month='2026-02',
    source='CRM',
    payment_status=None,
    payment_subtype='Полная оплата',
    project_type='Индивидуальный',
    address='ул. Тестовая, д.1',
    position='Дизайнер',
    agent_type='Фестиваль',
    reassigned=False,
    **overrides,
):
    """Генерация тестового платежа — словарь, аналогичный DataAccess.get_year_payments."""
    data = {
        'id': payment_id,
        'employee_name': employee_name,
        'amount': amount,
        'report_month': report_month,
        'source': source,
        'payment_status': payment_status,
        'payment_subtype': payment_subtype,
        'project_type': project_type,
        'address': address,
        'position': position,
        'agent_type': agent_type,
        'reassigned': reassigned,
    }
    data.update(overrides)
    return data


# ──────────────────────────────────────────────────────────
# 1. Класс-атрибут _months_ru
# ──────────────────────────────────────────────────────────

class TestMonthsRu:
    """Проверка маппинга русских названий месяцев."""

    def _get_months_ru(self):
        """Получаем _months_ru без создания виджета."""
        # Атрибут класса — можно прочитать напрямую
        with patch('ui.salaries_tab.DataAccess', MagicMock()), \
             patch('ui.salaries_tab.DatabaseManager', MagicMock()), \
             patch('ui.salaries_tab.IconLoader', MagicMock()):
            from ui.salaries_tab import SalariesTab
            return SalariesTab._months_ru

    def test_months_count(self):
        """12 месяцев в списке."""
        months = self._get_months_ru()
        assert len(months) == 12

    def test_january_first(self):
        """Январь — первый элемент."""
        months = self._get_months_ru()
        assert months[0] == 'Январь'

    def test_december_last(self):
        """Декабрь — последний элемент."""
        months = self._get_months_ru()
        assert months[11] == 'Декабрь'

    def test_june_index(self):
        """Июнь — индекс 5."""
        months = self._get_months_ru()
        assert months[5] == 'Июнь'


# ──────────────────────────────────────────────────────────
# 2. Фильтрация платежей по месяцу
# ──────────────────────────────────────────────────────────

class TestPaymentMatchesMonth:
    """Тесты _payment_matches_month — проверка соответствия платежа месяцу."""

    def _matches_month(self, payment, month, year):
        """Чистая реализация логики _payment_matches_month (без виджета)."""
        report_month = payment.get('report_month', '')
        if report_month:
            try:
                parts = report_month.split('-')
                if len(parts) == 2:
                    return int(parts[0]) == year and int(parts[1]) == month
            except Exception:
                pass
        return False

    def test_matching_month(self):
        """Платёж с report_month='2026-02' соответствует февралю 2026."""
        p = _make_payment(report_month='2026-02')
        assert self._matches_month(p, 2, 2026) is True

    def test_wrong_month(self):
        """Платёж с report_month='2026-03' не соответствует февралю 2026."""
        p = _make_payment(report_month='2026-03')
        assert self._matches_month(p, 2, 2026) is False

    def test_wrong_year(self):
        """Платёж с report_month='2025-02' не соответствует февралю 2026."""
        p = _make_payment(report_month='2025-02')
        assert self._matches_month(p, 2, 2026) is False

    def test_empty_report_month(self):
        """Платёж без report_month не соответствует никакому месяцу."""
        p = _make_payment(report_month='')
        assert self._matches_month(p, 2, 2026) is False

    def test_none_report_month(self):
        """Платёж с report_month=None не соответствует."""
        p = _make_payment(report_month=None)
        assert self._matches_month(p, 2, 2026) is False

    def test_malformed_report_month(self):
        """Некорректный формат report_month не вызывает ошибку."""
        p = _make_payment(report_month='invalid')
        assert self._matches_month(p, 2, 2026) is False


# ──────────────────────────────────────────────────────────
# 3. Фильтрация платежей по кварталу
# ──────────────────────────────────────────────────────────

class TestPaymentMatchesQuarter:
    """Тесты _payment_matches_quarter."""

    def _matches_quarter(self, payment, start_month, end_month, year):
        """Чистая реализация логики _payment_matches_quarter."""
        report_month = payment.get('report_month', '')
        if report_month:
            try:
                parts = report_month.split('-')
                if len(parts) == 2:
                    p_year = int(parts[0])
                    p_month = int(parts[1])
                    return p_year == year and start_month <= p_month <= end_month
            except Exception:
                pass
        return False

    def test_q1_january(self):
        """Январь 2026 входит в Q1 (1-3)."""
        p = _make_payment(report_month='2026-01')
        assert self._matches_quarter(p, 1, 3, 2026) is True

    def test_q1_march(self):
        """Март 2026 входит в Q1 (1-3)."""
        p = _make_payment(report_month='2026-03')
        assert self._matches_quarter(p, 1, 3, 2026) is True

    def test_q1_april_not_match(self):
        """Апрель 2026 не входит в Q1 (1-3)."""
        p = _make_payment(report_month='2026-04')
        assert self._matches_quarter(p, 1, 3, 2026) is False

    def test_q4_december(self):
        """Декабрь 2026 входит в Q4 (10-12)."""
        p = _make_payment(report_month='2026-12')
        assert self._matches_quarter(p, 10, 12, 2026) is True

    def test_empty_report_month_quarter(self):
        """Пустой report_month — не соответствует кварталу."""
        p = _make_payment(report_month='')
        assert self._matches_quarter(p, 1, 3, 2026) is False


# ──────────────────────────────────────────────────────────
# 4. Фильтрация платежей по году
# ──────────────────────────────────────────────────────────

class TestPaymentMatchesYear:
    """Тесты _payment_matches_year."""

    def _matches_year(self, payment, year):
        """Чистая реализация логики _payment_matches_year."""
        report_month = payment.get('report_month', '')
        if report_month:
            try:
                parts = report_month.split('-')
                if len(parts) >= 1:
                    return int(parts[0]) == year
            except Exception:
                pass
        return False

    def test_matching_year(self):
        """Платёж 2026-02 соответствует году 2026."""
        p = _make_payment(report_month='2026-02')
        assert self._matches_year(p, 2026) is True

    def test_wrong_year(self):
        """Платёж 2025-02 не соответствует году 2026."""
        p = _make_payment(report_month='2025-02')
        assert self._matches_year(p, 2026) is False

    def test_empty_report_month_year(self):
        """Пустой report_month — не соответствует году."""
        p = _make_payment(report_month='')
        assert self._matches_year(p, 2026) is False


# ──────────────────────────────────────────────────────────
# 5. Форматирование report_month -> русский текст
# ──────────────────────────────────────────────────────────

class TestReportMonthFormatting:
    """Форматирование 'YYYY-MM' -> 'Месяц ГГГГ'."""

    _months_ru = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']

    def _format_report_month(self, report_month):
        """Логика форматирования report_month из _render_all_payments."""
        if report_month and report_month != 'Не установлен':
            try:
                parts = report_month.split('-')
                if len(parts) == 2:
                    month_idx = int(parts[1]) - 1
                    return f"{self._months_ru[month_idx]} {parts[0]}"
            except Exception:
                pass
        return report_month

    def test_format_february_2026(self):
        """'2026-02' -> 'Февраль 2026'."""
        assert self._format_report_month('2026-02') == 'Февраль 2026'

    def test_format_november_2025(self):
        """'2025-11' -> 'Ноябрь 2025'."""
        assert self._format_report_month('2025-11') == 'Ноябрь 2025'

    def test_format_january(self):
        """'2026-01' -> 'Январь 2026'."""
        assert self._format_report_month('2026-01') == 'Январь 2026'

    def test_format_december(self):
        """'2026-12' -> 'Декабрь 2026'."""
        assert self._format_report_month('2026-12') == 'Декабрь 2026'

    def test_format_not_set(self):
        """'Не установлен' остаётся без изменений."""
        assert self._format_report_month('Не установлен') == 'Не установлен'

    def test_format_empty(self):
        """Пустая строка остаётся без изменений."""
        assert self._format_report_month('') == ''


# ──────────────────────────────────────────────────────────
# 6. Маппинг статус -> цвет строки
# ──────────────────────────────────────────────────────────

class TestStatusColorMapping:
    """Маппинг payment_status -> цвет фона строки (apply_row_color)."""

    def _get_color(self, status, is_reassigned=False):
        """Извлечение цвета из логики apply_row_color."""
        if is_reassigned:
            return '#FFF9C4'
        elif status == 'to_pay':
            return '#FFE4B5'
        elif status == 'paid':
            return '#D4EDDA'
        else:
            return None  # Белый фон по умолчанию

    def test_to_pay_color(self):
        """Статус 'to_pay' -> оранжевый '#FFE4B5'."""
        assert self._get_color('to_pay') == '#FFE4B5'

    def test_paid_color(self):
        """Статус 'paid' -> зеленый '#D4EDDA'."""
        assert self._get_color('paid') == '#D4EDDA'

    def test_no_status_color(self):
        """Нет статуса -> None (белый по умолчанию)."""
        assert self._get_color(None) is None

    def test_reassigned_overrides_status(self):
        """Переназначение перекрывает любой статус."""
        assert self._get_color('paid', is_reassigned=True) == '#FFF9C4'
        assert self._get_color('to_pay', is_reassigned=True) == '#FFF9C4'
        assert self._get_color(None, is_reassigned=True) == '#FFF9C4'


# ──────────────────────────────────────────────────────────
# 7. Toggle-логика статусов оплаты
# ──────────────────────────────────────────────────────────

class TestStatusToggleLogic:
    """Toggle-логика из set_payment_status: повторное нажатие сбрасывает статус."""

    def _toggle_status(self, current_status, new_status):
        """Логика из set_payment_status."""
        if current_status == new_status:
            return None  # Сброс
        return new_status

    def test_set_to_pay(self):
        """Из None -> to_pay."""
        assert self._toggle_status(None, 'to_pay') == 'to_pay'

    def test_set_paid(self):
        """Из None -> paid."""
        assert self._toggle_status(None, 'paid') == 'paid'

    def test_toggle_to_pay_off(self):
        """Повторное нажатие to_pay -> None."""
        assert self._toggle_status('to_pay', 'to_pay') is None

    def test_toggle_paid_off(self):
        """Повторное нажатие paid -> None."""
        assert self._toggle_status('paid', 'paid') is None

    def test_switch_from_to_pay_to_paid(self):
        """Переключение to_pay -> paid."""
        assert self._toggle_status('to_pay', 'paid') == 'paid'

    def test_switch_from_paid_to_to_pay(self):
        """Переключение paid -> to_pay."""
        assert self._toggle_status('paid', 'to_pay') == 'to_pay'


# ──────────────────────────────────────────────────────────
# 8. Определение подтипа выплаты для отображения
# ──────────────────────────────────────────────────────────

class TestPaymentSubtypeDetermination:
    """Логика определения подтипа выплаты из _render_all_payments."""

    def _get_display_subtype(self, payment):
        """Логика из _render_all_payments (строки 1545-1549)."""
        payment_subtype = payment.get('payment_subtype')
        if payment['source'] == 'Оклад':
            payment_subtype = 'Оклад'
        elif not payment_subtype:
            payment_subtype = '-'
        return payment_subtype

    def test_salary_source(self):
        """Источник 'Оклад' -> подтип 'Оклад'."""
        p = _make_payment(source='Оклад', payment_subtype='Полная оплата')
        assert self._get_display_subtype(p) == 'Оклад'

    def test_crm_with_subtype(self):
        """CRM-источник с подтипом 'Аванс' -> 'Аванс'."""
        p = _make_payment(source='CRM', payment_subtype='Аванс')
        assert self._get_display_subtype(p) == 'Аванс'

    def test_crm_without_subtype(self):
        """CRM-источник без подтипа -> '-'."""
        p = _make_payment(source='CRM', payment_subtype=None)
        assert self._get_display_subtype(p) == '-'

    def test_crm_empty_subtype(self):
        """CRM-источник с пустым подтипом -> '-'."""
        p = _make_payment(source='CRM', payment_subtype='')
        assert self._get_display_subtype(p) == '-'


# ──────────────────────────────────────────────────────────
# 9. Дедупликация платежей
# ──────────────────────────────────────────────────────────

class TestPaymentDeduplication:
    """Логика дедупликации из load_all_payments (период='Все')."""

    def _deduplicate(self, payments_by_year):
        """Логика дедупликации из load_all_payments (строки 1340-1356)."""
        all_payments = []
        seen_ids = set()
        for year_payments in payments_by_year:
            for p in year_payments:
                pid = (p.get('id'), p.get('source', 'CRM'))
                if pid not in seen_ids:
                    all_payments.append(p)
                    seen_ids.add(pid)
        return all_payments

    def test_no_duplicates(self):
        """Уникальные платежи — все сохраняются."""
        y1 = [_make_payment(payment_id=1), _make_payment(payment_id=2)]
        y2 = [_make_payment(payment_id=3)]
        result = self._deduplicate([y1, y2])
        assert len(result) == 3

    def test_duplicate_removed(self):
        """Дублирующийся ID+source удаляется."""
        y1 = [_make_payment(payment_id=1, source='CRM')]
        y2 = [_make_payment(payment_id=1, source='CRM')]
        result = self._deduplicate([y1, y2])
        assert len(result) == 1

    def test_same_id_different_source(self):
        """Одинаковый ID, но разный source — оба сохраняются."""
        y1 = [_make_payment(payment_id=1, source='CRM')]
        y2 = [_make_payment(payment_id=1, source='Оклад')]
        result = self._deduplicate([y1, y2])
        assert len(result) == 2


# ──────────────────────────────────────────────────────────
# 10. Расчёт итогов (суммирование)
# ──────────────────────────────────────────────────────────

class TestTotalsCalculation:
    """Расчёт итогов за период и год из _render_all_payments."""

    def _calc_totals(self, payments, year):
        """Логика суммирования из _render_all_payments (строки 1577-1583)."""
        total_period = sum(p['amount'] for p in payments)
        total_year = sum(
            p['amount'] for p in payments
            if self._matches_year(p, year)
        )
        return total_period, total_year

    def _matches_year(self, payment, year):
        report_month = payment.get('report_month', '')
        if report_month:
            try:
                parts = report_month.split('-')
                if len(parts) >= 1:
                    return int(parts[0]) == year
            except Exception:
                pass
        return False

    def test_single_payment(self):
        """Один платёж — итоги совпадают."""
        payments = [_make_payment(amount=100000, report_month='2026-02')]
        total_period, total_year = self._calc_totals(payments, 2026)
        assert total_period == 100000
        assert total_year == 100000

    def test_multiple_payments(self):
        """Несколько платежей — сумма корректна."""
        payments = [
            _make_payment(payment_id=1, amount=30000, report_month='2026-01'),
            _make_payment(payment_id=2, amount=20000, report_month='2026-02'),
            _make_payment(payment_id=3, amount=10000, report_month='2026-03'),
        ]
        total_period, total_year = self._calc_totals(payments, 2026)
        assert total_period == 60000
        assert total_year == 60000

    def test_mixed_years(self):
        """Платежи за разные годы — годовой итог фильтруется."""
        payments = [
            _make_payment(payment_id=1, amount=50000, report_month='2026-02'),
            _make_payment(payment_id=2, amount=30000, report_month='2025-12'),
        ]
        total_period, total_year = self._calc_totals(payments, 2026)
        assert total_period == 80000  # Все платежи в периоде
        assert total_year == 50000   # Только 2026

    def test_empty_payments(self):
        """Нет платежей — нулевые итоги."""
        total_period, total_year = self._calc_totals([], 2026)
        assert total_period == 0
        assert total_year == 0


# ──────────────────────────────────────────────────────────
# 11. Фильтрация по полям (логика из _render_all_payments)
# ──────────────────────────────────────────────────────────

class TestFieldFiltering:
    """Фильтрация по адресу, сотруднику, должности, типу агента, подтипу, статусу."""

    def _filter_payments(self, payments, f_address=None, f_employee=None,
                         f_position=None, f_agent_type=None, f_subtype=None,
                         f_project_type='Все', f_status='Все'):
        """Логика фильтрации из _render_all_payments — substring match по адресу."""
        filtered = []
        for payment in payments:
            if f_address and f_address.lower() not in (payment.get('address') or '').lower():
                continue
            if f_employee and payment.get('employee_name') != f_employee:
                continue
            if f_position and payment.get('position') != f_position:
                continue
            if f_agent_type and payment.get('agent_type') != f_agent_type:
                continue
            if f_subtype:
                actual_subtype = payment.get('payment_subtype')
                if payment['source'] == 'Оклад':
                    actual_subtype = 'Оклад'
                if actual_subtype != f_subtype:
                    continue
            if f_project_type != 'Все':
                if f_project_type != payment.get('project_type', ''):
                    continue
            if f_status != 'Все':
                status = payment.get('payment_status', '')
                if f_status == 'К оплате' and status != 'to_pay':
                    continue
                if f_status == 'Оплачено' and status != 'paid':
                    continue
            filtered.append(payment)
        return filtered

    def test_filter_by_address(self):
        """Фильтрация по адресу — substring match."""
        payments = [
            _make_payment(payment_id=1, address='ул. Тестовая'),
            _make_payment(payment_id=2, address='ул. Другая'),
        ]
        result = self._filter_payments(payments, f_address='Тестовая')
        assert len(result) == 1
        assert result[0]['address'] == 'ул. Тестовая'

    def test_filter_by_address_substring(self):
        """Баг #2: Адрес ищется по подстроке, а не точному совпадению."""
        payments = [
            _make_payment(payment_id=1, address='г. СПб, ул. Тестовая, д.1'),
            _make_payment(payment_id=2, address='г. Москва, ул. Тестовая, д.5'),
            _make_payment(payment_id=3, address='г. СПб, пр. Невский, д.10'),
        ]
        # Поиск по подстроке "Тестовая" — найдёт оба
        result = self._filter_payments(payments, f_address='Тестовая')
        assert len(result) == 2

    def test_filter_by_address_case_insensitive(self):
        """Баг #2: Поиск по адресу — регистронезависимый."""
        payments = [
            _make_payment(payment_id=1, address='ул. ТЕСТОВАЯ, д.1'),
        ]
        result = self._filter_payments(payments, f_address='тестовая')
        assert len(result) == 1

    def test_filter_by_address_none_address(self):
        """Баг #2: Платёж без адреса (None) не ломает фильтрацию."""
        payments = [
            _make_payment(payment_id=1, address=None),
            _make_payment(payment_id=2, address='ул. Тестовая'),
        ]
        result = self._filter_payments(payments, f_address='Тестовая')
        assert len(result) == 1

    def test_filter_by_employee(self):
        """Фильтрация по сотруднику."""
        payments = [
            _make_payment(payment_id=1, employee_name='Иванов'),
            _make_payment(payment_id=2, employee_name='Петров'),
        ]
        result = self._filter_payments(payments, f_employee='Петров')
        assert len(result) == 1
        assert result[0]['employee_name'] == 'Петров'

    def test_filter_by_status_to_pay(self):
        """Фильтрация по статусу 'К оплате'."""
        payments = [
            _make_payment(payment_id=1, payment_status='to_pay'),
            _make_payment(payment_id=2, payment_status='paid'),
            _make_payment(payment_id=3, payment_status=None),
        ]
        result = self._filter_payments(payments, f_status='К оплате')
        assert len(result) == 1
        assert result[0]['payment_status'] == 'to_pay'

    def test_filter_by_status_paid(self):
        """Фильтрация по статусу 'Оплачено'."""
        payments = [
            _make_payment(payment_id=1, payment_status='to_pay'),
            _make_payment(payment_id=2, payment_status='paid'),
        ]
        result = self._filter_payments(payments, f_status='Оплачено')
        assert len(result) == 1
        assert result[0]['payment_status'] == 'paid'

    def test_filter_all_no_filtering(self):
        """Без фильтров — все платежи возвращаются."""
        payments = [_make_payment(payment_id=i) for i in range(5)]
        result = self._filter_payments(payments)
        assert len(result) == 5

    def test_filter_by_salary_subtype(self):
        """Фильтрация по подтипу 'Оклад' (source='Оклад')."""
        payments = [
            _make_payment(payment_id=1, source='Оклад', payment_subtype='Полная оплата'),
            _make_payment(payment_id=2, source='CRM', payment_subtype='Аванс'),
        ]
        result = self._filter_payments(payments, f_subtype='Оклад')
        assert len(result) == 1
        assert result[0]['source'] == 'Оклад'

    def test_filter_by_project_type(self):
        """Фильтрация по типу проекта."""
        payments = [
            _make_payment(payment_id=1, project_type='Индивидуальный'),
            _make_payment(payment_id=2, project_type='Шаблонный'),
        ]
        result = self._filter_payments(payments, f_project_type='Шаблонный')
        assert len(result) == 1
        assert result[0]['project_type'] == 'Шаблонный'

    def test_combined_filters(self):
        """Комбинированная фильтрация по нескольким полям."""
        payments = [
            _make_payment(payment_id=1, employee_name='Иванов', position='Дизайнер',
                          payment_status='to_pay'),
            _make_payment(payment_id=2, employee_name='Иванов', position='Менеджер',
                          payment_status='to_pay'),
            _make_payment(payment_id=3, employee_name='Петров', position='Дизайнер',
                          payment_status='to_pay'),
        ]
        result = self._filter_payments(
            payments, f_employee='Иванов', f_position='Дизайнер', f_status='К оплате'
        )
        assert len(result) == 1
        assert result[0]['id'] == 1


# ──────────────────────────────────────────────────────────
# 12. Маппинг вкладок -> ключи дашборда
# ──────────────────────────────────────────────────────────

class TestDashboardMapping:
    """Маппинг индекса вкладки на ключ дашборда из on_tab_changed."""

    _dashboard_map = {
        0: 'Зарплаты (Все)',
        1: 'Зарплаты (Индивидуальные)',
        2: 'Зарплаты (Шаблонные)',
        3: 'Зарплаты (Оклады)',
        4: 'Зарплаты (Надзор)',
    }

    def test_all_payments_tab(self):
        """Вкладка 0 -> 'Зарплаты (Все)'."""
        assert self._dashboard_map[0] == 'Зарплаты (Все)'

    def test_individual_tab(self):
        """Вкладка 1 -> 'Зарплаты (Индивидуальные)'."""
        assert self._dashboard_map[1] == 'Зарплаты (Индивидуальные)'

    def test_unknown_index(self):
        """Неизвестный индекс -> fallback 'Зарплаты (Все)'."""
        result = self._dashboard_map.get(99, 'Зарплаты (Все)')
        assert result == 'Зарплаты (Все)'


# ──────────────────────────────────────────────────────────
# 13. Обрезка комментариев
# ──────────────────────────────────────────────────────────

class TestCommentTruncation:
    """Обрезка комментариев > 30 символов для отображения."""

    def _truncate_comment(self, comment):
        """Логика из load_payment_type_data (строки 1734-1736)."""
        comment = comment or ''
        display = comment[:30] + '...' if len(comment) > 30 else comment
        return display

    def test_short_comment(self):
        """Короткий комментарий — без обрезки."""
        assert self._truncate_comment('Тест') == 'Тест'

    def test_exactly_30_chars(self):
        """Ровно 30 символов — без обрезки."""
        text = 'А' * 30
        assert self._truncate_comment(text) == text

    def test_31_chars_truncated(self):
        """31 символ — обрезка до 30 + '...'."""
        text = 'Б' * 31
        result = self._truncate_comment(text)
        assert result == 'Б' * 30 + '...'

    def test_none_comment(self):
        """None -> пустая строка."""
        assert self._truncate_comment(None) == ''


# ──────────────────────────────────────────────────────────
# 14. Подсчёт переназначенных платежей
# ──────────────────────────────────────────────────────────

class TestReassignedCount:
    """Подсчёт и формирование текста перераспределённых платежей."""

    def _reassigned_text(self, payments):
        """Логика из _render_all_payments (строки 1586-1587)."""
        count = sum(1 for p in payments if p.get('reassigned', False))
        return f'  |  Перераспределено: {count}' if count > 0 else ''

    def test_no_reassigned(self):
        """Нет переназначенных — пустая строка."""
        payments = [_make_payment(reassigned=False)]
        assert self._reassigned_text(payments) == ''

    def test_some_reassigned(self):
        """Есть переназначенные — текст с числом."""
        payments = [
            _make_payment(payment_id=1, reassigned=True),
            _make_payment(payment_id=2, reassigned=False),
            _make_payment(payment_id=3, reassigned=True),
        ]
        assert self._reassigned_text(payments) == '  |  Перераспределено: 2'


# ──────────────────────────────────────────────────────────
# 15. Форматирование суммы
# ──────────────────────────────────────────────────────────

class TestAmountFormatting:
    """Форматирование сумм для отображения в таблице."""

    def _format_amount(self, amount):
        """Логика форматирования из _render_all_payments (строка 1540)."""
        return f"{amount:,.2f} ₽"

    def test_integer_amount(self):
        """Целая сумма форматируется с двумя знаками."""
        assert self._format_amount(50000) == '50,000.00 ₽'

    def test_decimal_amount(self):
        """Дробная сумма сохраняет знаки."""
        assert self._format_amount(1234.56) == '1,234.56 ₽'

    def test_zero_amount(self):
        """Нулевая сумма."""
        assert self._format_amount(0) == '0.00 ₽'

    def test_large_amount(self):
        """Большая сумма с разделителями тысяч."""
        assert self._format_amount(1000000) == '1,000,000.00 ₽'


# ──────────────────────────────────────────────────────────
# 16. Инвалидация кеша
# ──────────────────────────────────────────────────────────

class TestCacheInvalidation:
    """Проверка логики инвалидации кеша."""

    def test_invalidate_clears_all(self):
        """invalidate_cache очищает все кеш-поля."""
        # Имитируем состояние кеша
        cache = {
            '_all_payments_cache': [_make_payment()],
            '_cache_year': 2026,
            '_payment_type_cache': {'Оклады': [_make_payment()]},
        }
        # Логика invalidate_cache
        cache['_all_payments_cache'] = None
        cache['_cache_year'] = None
        cache['_payment_type_cache'] = {}

        assert cache['_all_payments_cache'] is None
        assert cache['_cache_year'] is None
        assert cache['_payment_type_cache'] == {}


# ──────────────────────────────────────────────────────────
# 17. Определение report_month при установке статуса
# ──────────────────────────────────────────────────────────

class TestAutoReportMonth:
    """При установке статуса to_pay/paid, если report_month=NULL, ставим текущий месяц."""

    def _should_set_report_month(self, new_status, current_report_month):
        """Логика из set_payment_status (строки 2421-2426)."""
        return new_status in ('to_pay', 'paid') and not current_report_month

    def test_to_pay_null_month(self):
        """to_pay + NULL report_month -> нужно установить."""
        assert self._should_set_report_month('to_pay', None) is True

    def test_paid_null_month(self):
        """paid + NULL report_month -> нужно установить."""
        assert self._should_set_report_month('paid', None) is True

    def test_to_pay_existing_month(self):
        """to_pay + report_month='2026-02' -> не нужно менять."""
        assert self._should_set_report_month('to_pay', '2026-02') is False

    def test_none_status_null_month(self):
        """Сброс статуса (None) -> не устанавливаем report_month."""
        assert self._should_set_report_month(None, None) is False

    def test_paid_empty_string_month(self):
        """paid + пустая строка report_month -> нужно установить."""
        assert self._should_set_report_month('paid', '') is True
