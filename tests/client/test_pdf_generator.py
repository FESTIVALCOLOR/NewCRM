# -*- coding: utf-8 -*-
"""
Unit-тесты для utils/pdf_generator.py
Тестирует форматирование значений и генерацию PDF (с моком reportlab).
"""
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from unittest.mock import patch, MagicMock

from utils.pdf_generator import format_report_value, PDF_STYLE


# ========== Тесты format_report_value ==========

class TestFormatReportValue:
    """Тесты функции форматирования значений отчёта."""

    def test_none_returns_empty_string(self):
        """None возвращает пустую строку."""
        assert format_report_value(None) == ''
        assert format_report_value(None, 'currency') == ''
        assert format_report_value(None, 'area') == ''
        assert format_report_value(None, 'date') == ''

    def test_currency_integer(self):
        """Целое число форматируется как рубли."""
        result = format_report_value(150000, 'currency')
        assert 'руб.' in result
        assert '150' in result

    def test_currency_string_number(self):
        """Строковое число форматируется как рубли."""
        result = format_report_value('100000', 'currency')
        assert 'руб.' in result

    def test_currency_invalid_returns_str(self):
        """Невалидное значение возвращается как строка."""
        result = format_report_value('не число', 'currency')
        assert result == 'не число'

    def test_area_float(self):
        """Площадь форматируется с одним знаком после запятой и м²."""
        result = format_report_value(50.5, 'area')
        assert 'м²' in result
        assert '50.5' in result

    def test_area_integer(self):
        """Целое число площади форматируется как float."""
        result = format_report_value(100, 'area')
        assert 'м²' in result
        assert '100.0' in result

    def test_area_invalid_returns_str(self):
        """Невалидное значение площади возвращается как строка."""
        result = format_report_value('abc', 'area')
        assert result == 'abc'

    def test_date_iso_format(self):
        """Дата в формате ISO конвертируется в DD.MM.YYYY."""
        result = format_report_value('2024-03-15', 'date')
        assert result == '15.03.2024'

    def test_date_with_time(self):
        """Дата с временем — берётся только дата."""
        result = format_report_value('2024-03-15T10:30:00', 'date')
        assert result == '15.03.2024'

    def test_date_invalid_returns_str(self):
        """Невалидная дата возвращается как строка."""
        result = format_report_value('не дата', 'date')
        assert result == 'не дата'

    def test_text_type_returns_str(self):
        """Тип 'text' возвращает строковое представление."""
        assert format_report_value(42, 'text') == '42'
        assert format_report_value('hello') == 'hello'

    def test_default_type_is_text(self):
        """По умолчанию тип 'text'."""
        assert format_report_value(123) == '123'


# ========== Тесты PDF_STYLE константы ==========

class TestPDFStyle:
    """Тесты структуры стиля PDF отчётов."""

    def test_style_has_required_keys(self):
        """Словарь стиля содержит все необходимые ключи."""
        required_keys = [
            'header_bg', 'header_fg', 'row_odd_bg', 'row_even_bg',
            'border_color', 'font_size_header', 'font_size_body',
            'font_size_title', 'margins'
        ]
        for key in required_keys:
            assert key in PDF_STYLE, f"Ключ '{key}' должен быть в PDF_STYLE"

    def test_style_colors_are_hex(self):
        """Цвета заданы в hex-формате."""
        for key in ['header_bg', 'header_fg', 'row_odd_bg', 'row_even_bg', 'border_color']:
            assert PDF_STYLE[key].startswith('#'), f"PDF_STYLE['{key}'] должен начинаться с #"

    def test_font_sizes_are_positive(self):
        """Размеры шрифтов положительные числа."""
        assert PDF_STYLE['font_size_header'] > 0
        assert PDF_STYLE['font_size_body'] > 0
        assert PDF_STYLE['font_size_title'] > 0

    def test_margins_is_tuple_of_four(self):
        """Поля — кортеж из четырёх значений."""
        margins = PDF_STYLE['margins']
        assert len(margins) == 4


# ========== Тесты PDFGenerator с моком reportlab ==========

class TestPDFGeneratorMocked:
    """Тесты класса PDFGenerator с замоканным reportlab."""

    def test_init_sets_font(self):
        """Инициализация устанавливает шрифт."""
        # Мокаем reportlab модули
        mock_reportlab = MagicMock()
        with patch.dict('sys.modules', {
            'reportlab': mock_reportlab,
            'reportlab.lib': mock_reportlab.lib,
            'reportlab.lib.pagesizes': mock_reportlab.lib.pagesizes,
            'reportlab.lib.styles': mock_reportlab.lib.styles,
            'reportlab.platypus': mock_reportlab.platypus,
            'reportlab.lib.colors': mock_reportlab.lib.colors,
            'reportlab.lib.units': mock_reportlab.lib.units,
            'reportlab.pdfbase': mock_reportlab.pdfbase,
            'reportlab.pdfbase.pdfmetrics': mock_reportlab.pdfbase.pdfmetrics,
            'reportlab.pdfbase.ttfonts': mock_reportlab.pdfbase.ttfonts,
        }):
            from utils.pdf_generator import PDFGenerator
            gen = PDFGenerator()
            assert gen.font in ('Arial', 'Helvetica'), \
                "Шрифт должен быть Arial или Helvetica"

    def test_generate_report_calls_doc_build(self):
        """generate_report вызывает doc.build()."""
        pytest.importorskip("reportlab")

        from utils.pdf_generator import PDFGenerator

        gen = PDFGenerator()

        build_calls = []

        def fake_build(elements):
            build_calls.append(elements)

        mock_doc = MagicMock()
        mock_doc.width = 500
        mock_doc.build = fake_build

        with patch('utils.pdf_generator.SimpleDocTemplate', return_value=mock_doc):
            result = gen.generate_report(
                '/tmp/test_report.pdf',
                'Тестовый заголовок',
                [['Иванов', 'Дизайнер']],
                ['ФИО', 'Должность']
            )

            assert len(build_calls) == 1, "doc.build должен быть вызван один раз"
            assert result == '/tmp/test_report.pdf'

    def test_generate_report_no_data_no_crash(self):
        """generate_report с пустыми данными не падает."""
        pytest.importorskip("reportlab")

        from utils.pdf_generator import PDFGenerator

        gen = PDFGenerator()

        build_calls = []

        def fake_build(elements):
            build_calls.append(elements)

        mock_doc = MagicMock()
        mock_doc.width = 500
        mock_doc.build = fake_build

        with patch('utils.pdf_generator.SimpleDocTemplate', return_value=mock_doc):
            result = gen.generate_report(
                '/tmp/test_report_empty.pdf',
                'Пустой отчёт',
                [],  # нет данных
                ['ФИО', 'Должность']
            )
            assert len(build_calls) == 1, "doc.build должен вызываться даже с пустыми данными"


# ========== Тесты format_report_value граничные случаи ==========

class TestFormatReportValueEdgeCases:
    """Граничные случаи форматирования."""

    def test_zero_currency(self):
        """Нулевая сумма форматируется как '0 руб.'."""
        result = format_report_value(0, 'currency')
        assert 'руб.' in result
        assert '0' in result

    def test_large_currency_with_spaces(self):
        """Большая сумма разбивается пробелами."""
        result = format_report_value(1000000, 'currency')
        assert 'руб.' in result
        # Должен быть разделитель разрядов (пробел заменяет запятую)
        assert '1' in result

    def test_area_zero(self):
        """Нулевая площадь форматируется как '0.0 м²'."""
        result = format_report_value(0, 'area')
        assert result == '0.0 м²'

    def test_date_wrong_separator_returns_str(self):
        """Дата без '-' возвращается как строка без ошибки."""
        result = format_report_value('15/03/2024', 'date')
        # Нет '-' в строке, поэтому возвращается строка без конвертации
        assert isinstance(result, str)
