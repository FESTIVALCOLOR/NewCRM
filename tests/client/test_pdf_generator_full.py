# -*- coding: utf-8 -*-
"""
Полные тесты для utils/pdf_generator.py

Покрытие:
- format_report_value() — все value_type: text, currency, area, date
- Edge cases: None, пустая строка, 0, отрицательные числа, большие числа
- PDF_STYLE — структура и обязательные ключи
- REPORTLAB_AVAILABLE — флаг доступности
- PDFGenerator — создание экземпляра (если reportlab доступен)
"""
import sys
from pathlib import Path

import pytest

# Корень проекта
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.pdf_generator import format_report_value, PDF_STYLE, REPORTLAB_AVAILABLE


# ============================================================================
# format_report_value — тип 'text' (по умолчанию)
# ============================================================================


class TestFormatReportValueText:
    """Тесты форматирования значений с типом 'text' (по умолчанию)."""

    def test_none_returns_empty_string(self):
        """None должен возвращать пустую строку для text."""
        assert format_report_value(None) == ''

    def test_none_explicit_text_type(self):
        """None с явным value_type='text' — пустая строка."""
        assert format_report_value(None, value_type='text') == ''

    def test_string_value(self):
        """Обычная строка возвращается как есть."""
        assert format_report_value('Привет') == 'Привет'

    def test_empty_string(self):
        """Пустая строка возвращается как есть (не None)."""
        assert format_report_value('') == ''

    def test_integer_as_text(self):
        """Целое число приводится к строке."""
        assert format_report_value(42) == '42'

    def test_float_as_text(self):
        """Дробное число приводится к строке."""
        result = format_report_value(3.14)
        assert result == '3.14'

    def test_zero_as_text(self):
        """Ноль приводится к строке '0'."""
        assert format_report_value(0) == '0'


# ============================================================================
# format_report_value — тип 'currency'
# ============================================================================


class TestFormatReportValueCurrency:
    """Тесты форматирования валюты."""

    def test_none_currency(self):
        """None с currency — пустая строка (общий ранний return)."""
        assert format_report_value(None, value_type='currency') == ''

    def test_integer_currency(self):
        """Целое число форматируется с разделителями тысяч и 'руб.'."""
        result = format_report_value(1234567, value_type='currency')
        assert result == '1 234 567 руб.'

    def test_float_currency_truncated(self):
        """Дробное число округляется до целого в currency."""
        result = format_report_value(999.99, value_type='currency')
        # int(float(999.99)) = 999
        assert result == '999 руб.'

    def test_string_numeric_currency(self):
        """Строка с числом корректно парсится."""
        result = format_report_value('50000', value_type='currency')
        assert result == '50 000 руб.'

    def test_zero_currency(self):
        """Ноль форматируется как '0 руб.'."""
        result = format_report_value(0, value_type='currency')
        assert result == '0 руб.'

    def test_negative_currency(self):
        """Отрицательное число форматируется с минусом."""
        result = format_report_value(-5000, value_type='currency')
        assert '-5 000 руб.' == result

    def test_large_currency(self):
        """Большое число (миллионы) — корректные разделители."""
        result = format_report_value(12345678, value_type='currency')
        assert result == '12 345 678 руб.'

    def test_non_numeric_string_currency(self):
        """Нечисловая строка возвращается как есть (fallback)."""
        result = format_report_value('не число', value_type='currency')
        assert result == 'не число'


# ============================================================================
# format_report_value — тип 'area'
# ============================================================================


class TestFormatReportValueArea:
    """Тесты форматирования площади."""

    def test_none_area(self):
        """None с area — пустая строка."""
        assert format_report_value(None, value_type='area') == ''

    def test_integer_area(self):
        """Целое число отображается с одним десятичным знаком и 'м²'."""
        result = format_report_value(100, value_type='area')
        assert result == '100.0 м²'

    def test_float_area(self):
        """Дробное число — один десятичный знак."""
        result = format_report_value(123.456, value_type='area')
        assert result == '123.5 м²'

    def test_string_numeric_area(self):
        """Строка с числом парсится корректно."""
        result = format_report_value('55.7', value_type='area')
        assert result == '55.7 м²'

    def test_zero_area(self):
        """Ноль — '0.0 м²'."""
        result = format_report_value(0, value_type='area')
        assert result == '0.0 м²'

    def test_non_numeric_area(self):
        """Нечисловая строка возвращается как есть (fallback)."""
        result = format_report_value('большая', value_type='area')
        assert result == 'большая'


# ============================================================================
# format_report_value — тип 'date'
# ============================================================================


class TestFormatReportValueDate:
    """Тесты форматирования дат."""

    def test_none_date(self):
        """None с date — пустая строка."""
        assert format_report_value(None, value_type='date') == ''

    def test_iso_date_string(self):
        """ISO строка 'YYYY-MM-DD' конвертируется в 'DD.MM.YYYY'."""
        result = format_report_value('2024-03-15', value_type='date')
        assert result == '15.03.2024'

    def test_iso_datetime_string(self):
        """ISO datetime 'YYYY-MM-DDThh:mm:ss' — берётся только дата."""
        result = format_report_value('2024-12-31T23:59:59', value_type='date')
        assert result == '31.12.2024'

    def test_non_date_string(self):
        """Строка без '-' не парсится — возвращается как есть."""
        result = format_report_value('вчера', value_type='date')
        assert result == 'вчера'

    def test_invalid_date_format(self):
        """Некорректная дата с '-' — fallback на str(value)."""
        result = format_report_value('99-99-9999', value_type='date')
        assert result == '99-99-9999'

    def test_integer_date(self):
        """Целое число с date — приводится к строке."""
        result = format_report_value(20240315, value_type='date')
        assert result == '20240315'


# ============================================================================
# PDF_STYLE — структура стилей
# ============================================================================


class TestPDFStyle:
    """Тесты структуры константы PDF_STYLE."""

    def test_pdf_style_is_dict(self):
        """PDF_STYLE — словарь."""
        assert isinstance(PDF_STYLE, dict)

    def test_required_color_keys(self):
        """Обязательные ключи цветов присутствуют."""
        required = ['header_bg', 'header_fg', 'row_odd_bg', 'row_even_bg', 'border_color']
        for key in required:
            assert key in PDF_STYLE, f"Отсутствует ключ '{key}' в PDF_STYLE"

    def test_required_font_size_keys(self):
        """Обязательные ключи размеров шрифтов присутствуют."""
        required = ['font_size_header', 'font_size_body', 'font_size_title']
        for key in required:
            assert key in PDF_STYLE, f"Отсутствует ключ '{key}' в PDF_STYLE"

    def test_margins_key(self):
        """Ключ margins присутствует и является кортежем из 4 элементов."""
        assert 'margins' in PDF_STYLE
        assert isinstance(PDF_STYLE['margins'], tuple)
        assert len(PDF_STYLE['margins']) == 4

    def test_header_bg_is_hex_color(self):
        """Цвет фона заголовка — HEX строка."""
        assert PDF_STYLE['header_bg'].startswith('#')
        assert len(PDF_STYLE['header_bg']) == 7  # #RRGGBB

    def test_font_sizes_are_positive(self):
        """Размеры шрифтов — положительные числа."""
        for key in ['font_size_header', 'font_size_body', 'font_size_title']:
            assert PDF_STYLE[key] > 0, f"Размер шрифта '{key}' должен быть > 0"


# ============================================================================
# REPORTLAB_AVAILABLE — флаг доступности
# ============================================================================


class TestReportlabAvailable:
    """Тесты флага REPORTLAB_AVAILABLE."""

    def test_reportlab_flag_is_bool(self):
        """REPORTLAB_AVAILABLE — булево значение."""
        assert isinstance(REPORTLAB_AVAILABLE, bool)


# ============================================================================
# PDFGenerator — создание экземпляра (если reportlab доступен)
# ============================================================================


@pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab не установлен")
class TestPDFGeneratorInit:
    """Тесты создания PDFGenerator (требуется reportlab)."""

    def test_create_instance(self):
        """Экземпляр PDFGenerator создаётся без ошибок."""
        from utils.pdf_generator import PDFGenerator
        gen = PDFGenerator()
        assert gen is not None

    def test_font_attribute(self):
        """У экземпляра есть атрибут font (Arial или Helvetica)."""
        from utils.pdf_generator import PDFGenerator
        gen = PDFGenerator()
        assert hasattr(gen, 'font')
        assert gen.font in ('Arial', 'Helvetica')

    def test_generate_report_method_exists(self):
        """Метод generate_report доступен."""
        from utils.pdf_generator import PDFGenerator
        gen = PDFGenerator()
        assert callable(getattr(gen, 'generate_report', None))

    def test_generate_general_report_method_exists(self):
        """Метод generate_general_report доступен."""
        from utils.pdf_generator import PDFGenerator
        gen = PDFGenerator()
        assert callable(getattr(gen, 'generate_general_report', None))
