# -*- coding: utf-8 -*-
"""
Тесты для utils/pdf_utils.py — генерация PDF, стили таблиц, footer, секции.

Покрытие:
- register_fonts (идемпотентность, fallback на Helvetica)
- get_default_table_style (формат, цвета)
- make_page_footer (callback, рисование)
- pdf_section_header (структура)
- pdf_hr (размеры)
- fit_image (масштабирование, пропорции)
- chart_to_png (None-safety, matplotlib)
- build_table_pdf (генерация файла, landscape/portrait, status_colors)
- open_file (платформы)
"""
import pytest
import sys
import os
import io
import tempfile
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ==================== register_fonts ====================

class TestRegisterFonts:
    """register_fonts — регистрация шрифтов."""

    def test_returns_tuple(self):
        """Возвращает кортеж (font_name, font_bold)."""
        from utils.pdf_utils import register_fonts
        result = register_fonts()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_idempotent(self):
        """Повторный вызов возвращает те же шрифты."""
        from utils.pdf_utils import register_fonts
        r1 = register_fonts()
        r2 = register_fonts()
        assert r1 == r2

    def test_fallback_to_helvetica_when_no_arial(self):
        """Без Arial возвращает Helvetica."""
        import utils.pdf_utils as mod
        old_flag = mod._fonts_registered
        mod._fonts_registered = False
        try:
            with patch('os.path.exists', return_value=False):
                name, bold = mod.register_fonts()
            assert name == 'Helvetica'
            assert bold == 'Helvetica-Bold'
        finally:
            mod._fonts_registered = old_flag

    def test_registers_arial_when_available(self):
        """При наличии arial.ttf регистрирует Arial."""
        from utils.pdf_utils import register_fonts
        name, bold = register_fonts()
        # На Windows обычно есть Arial, на CI — нет
        assert name in ('Arial', 'Helvetica')
        assert bold in ('ArialBold', 'Helvetica-Bold')


# ==================== get_default_table_style ====================

class TestGetDefaultTableStyle:
    """get_default_table_style — стиль таблицы."""

    def test_returns_table_style(self):
        from utils.pdf_utils import get_default_table_style
        from reportlab.platypus import TableStyle
        style = get_default_table_style()
        assert isinstance(style, TableStyle)

    def test_accepts_custom_fonts(self):
        from utils.pdf_utils import get_default_table_style
        style = get_default_table_style('Helvetica', 'Helvetica-Bold')
        assert style is not None

    def test_has_grid_commands(self):
        """Стиль содержит команды GRID и BOX."""
        from utils.pdf_utils import get_default_table_style
        style = get_default_table_style()
        cmds = [c[0] for c in style.getCommands()]
        assert 'GRID' in cmds
        assert 'BOX' in cmds

    def test_has_header_background(self):
        """Стиль содержит фон заголовка."""
        from utils.pdf_utils import get_default_table_style
        style = get_default_table_style()
        cmds = [c[0] for c in style.getCommands()]
        assert 'BACKGROUND' in cmds


# ==================== make_page_footer ====================

class TestMakePageFooter:
    """make_page_footer — footer callback."""

    def test_returns_callable(self):
        from utils.pdf_utils import make_page_footer
        from reportlab.lib.pagesizes import A4
        cb = make_page_footer(A4)
        assert callable(cb)

    def test_callback_executes_without_error(self):
        """Footer callback не падает при вызове."""
        from utils.pdf_utils import make_page_footer
        from reportlab.lib.pagesizes import A4
        cb = make_page_footer(A4, 'Helvetica')
        canvas = MagicMock()
        doc = MagicMock()
        doc.page = 1
        cb(canvas, doc)
        canvas.saveState.assert_called_once()
        canvas.restoreState.assert_called_once()


# ==================== pdf_section_header ====================

class TestPdfSectionHeader:
    """pdf_section_header — заголовок секции."""

    def test_returns_paragraph(self):
        from utils.pdf_utils import pdf_section_header
        from reportlab.platypus import Paragraph
        result = pdf_section_header('Тест')
        assert isinstance(result, Paragraph)

    def test_with_custom_font(self):
        from utils.pdf_utils import pdf_section_header
        result = pdf_section_header('Секция', font_bold='Helvetica-Bold')
        assert result is not None


# ==================== pdf_hr ====================

class TestPdfHr:
    """pdf_hr — горизонтальная линия."""

    def test_returns_table(self):
        from utils.pdf_utils import pdf_hr
        from reportlab.platypus import Table
        result = pdf_hr(180)
        assert isinstance(result, Table)

    def test_different_widths(self):
        from utils.pdf_utils import pdf_hr
        r1 = pdf_hr(100)
        r2 = pdf_hr(200)
        assert r1 is not None
        assert r2 is not None


# ==================== fit_image ====================

def _make_minimal_png(width=4, height=4):
    """Создаёт минимальный валидный PNG через PIL."""
    from PIL import Image
    img = Image.new('RGB', (width, height), color='red')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


class TestFitImage:
    """fit_image — масштабирование изображения."""

    def test_proportional_fit_landscape(self):
        """Горизонтальное изображение вписывается по ширине."""
        from utils.pdf_utils import fit_image
        buf = _make_minimal_png(100, 50)
        img = fit_image(buf, 1000, 500, 180, 120)
        assert img is not None

    def test_proportional_fit_portrait(self):
        """Вертикальное изображение вписывается по высоте."""
        from utils.pdf_utils import fit_image
        buf = _make_minimal_png(50, 100)
        img = fit_image(buf, 500, 1000, 180, 120)
        assert img is not None

    def test_zero_width_handled(self):
        """w_px=0 не вызывает деление на ноль."""
        from utils.pdf_utils import fit_image
        buf = _make_minimal_png()
        img = fit_image(buf, 0, 100, 180, 120)
        assert img is not None

    def test_square_image(self):
        from utils.pdf_utils import fit_image
        buf = _make_minimal_png(80, 80)
        img = fit_image(buf, 800, 800, 100, 100)
        assert img is not None


# ==================== chart_to_png ====================

class TestChartToPng:
    """chart_to_png — захват matplotlib графика."""

    def test_none_widget_returns_none(self):
        from utils.pdf_utils import chart_to_png
        assert chart_to_png(None) is None

    def test_no_figure_attr_returns_none(self):
        from utils.pdf_utils import chart_to_png
        widget = MagicMock(spec=[])  # Нет атрибута figure
        assert chart_to_png(widget) is None

    def test_empty_axes_returns_none(self):
        from utils.pdf_utils import chart_to_png
        widget = MagicMock()
        widget.figure.axes = []
        assert chart_to_png(widget) is None

    def test_savefig_error_returns_none(self):
        from utils.pdf_utils import chart_to_png
        widget = MagicMock()
        widget.figure.axes = [MagicMock()]
        widget.figure.savefig.side_effect = Exception('test error')
        assert chart_to_png(widget) is None


# ==================== build_table_pdf ====================

class TestBuildTablePdf:
    """build_table_pdf — генерация табличного PDF."""

    def test_creates_pdf_file(self, tmp_path):
        """Генерирует валидный PDF файл."""
        from utils.pdf_utils import build_table_pdf
        output = str(tmp_path / 'test.pdf')
        build_table_pdf(
            output_path=output,
            title='Тестовый отчёт',
            headers=['Имя', 'Значение'],
            rows=[['Тест', '100']],
            auto_open=False,
        )
        assert os.path.exists(output)
        assert os.path.getsize(output) > 0

    def test_landscape_orientation(self, tmp_path):
        from utils.pdf_utils import build_table_pdf
        output = str(tmp_path / 'landscape.pdf')
        build_table_pdf(
            output_path=output,
            title='Landscape',
            headers=['A', 'B'],
            rows=[['1', '2']],
            orientation='landscape',
            auto_open=False,
        )
        assert os.path.exists(output)

    def test_portrait_orientation(self, tmp_path):
        from utils.pdf_utils import build_table_pdf
        output = str(tmp_path / 'portrait.pdf')
        build_table_pdf(
            output_path=output,
            title='Portrait',
            headers=['X'],
            rows=[['test']],
            orientation='portrait',
            auto_open=False,
        )
        assert os.path.exists(output)

    def test_empty_rows(self, tmp_path):
        """Пустые данные — PDF с сообщением 'Нет данных'."""
        from utils.pdf_utils import build_table_pdf
        output = str(tmp_path / 'empty.pdf')
        build_table_pdf(
            output_path=output,
            title='Пустой отчёт',
            headers=['Колонка'],
            rows=[],
            auto_open=False,
        )
        assert os.path.exists(output)

    def test_with_subtitle(self, tmp_path):
        from utils.pdf_utils import build_table_pdf
        output = str(tmp_path / 'subtitle.pdf')
        build_table_pdf(
            output_path=output,
            title='С подзаголовком',
            headers=['A'],
            rows=[['1']],
            subtitle='Период: Январь 2026',
            auto_open=False,
        )
        assert os.path.exists(output)

    def test_with_summary_items(self, tmp_path):
        from utils.pdf_utils import build_table_pdf
        output = str(tmp_path / 'summary.pdf')
        build_table_pdf(
            output_path=output,
            title='Со сводкой',
            headers=['Имя', 'Сумма'],
            rows=[['Иванов', '50000']],
            summary_items=[('Всего', '1'), ('Сумма', '50000')],
            auto_open=False,
        )
        assert os.path.exists(output)

    def test_with_status_colors(self, tmp_path):
        from utils.pdf_utils import build_table_pdf
        output = str(tmp_path / 'status.pdf')
        build_table_pdf(
            output_path=output,
            title='Статусы',
            headers=['Статус', 'Описание'],
            rows=[['Оплачено', 'тест'], ['К оплате', 'тест2']],
            status_column=0,
            status_colors={'Оплачено': '#27AE60', 'К оплате': '#E74C3C'},
            auto_open=False,
        )
        assert os.path.exists(output)

    def test_with_col_widths(self, tmp_path):
        from utils.pdf_utils import build_table_pdf
        output = str(tmp_path / 'widths.pdf')
        build_table_pdf(
            output_path=output,
            title='Ширины',
            headers=['A', 'B', 'C'],
            rows=[['1', '2', '3']],
            col_widths=[50, 80, 50],
            auto_open=False,
        )
        assert os.path.exists(output)


# ==================== open_file ====================

class TestOpenFile:
    """open_file — автооткрытие файла."""

    def test_win32_calls_startfile(self):
        from utils.pdf_utils import open_file
        with patch('sys.platform', 'win32'), \
             patch('os.startfile') as mock_start:
            open_file('/tmp/test.pdf')
            mock_start.assert_called_once()

    def test_darwin_calls_open(self):
        from utils.pdf_utils import open_file
        with patch('sys.platform', 'darwin'), \
             patch('subprocess.Popen') as mock_popen:
            open_file('/tmp/test.pdf')
            mock_popen.assert_called_once()
            assert mock_popen.call_args[0][0][0] == 'open'

    def test_linux_calls_xdg_open(self):
        from utils.pdf_utils import open_file
        with patch('sys.platform', 'linux'), \
             patch('subprocess.Popen') as mock_popen:
            open_file('/tmp/test.pdf')
            mock_popen.assert_called_once()
            assert mock_popen.call_args[0][0][0] == 'xdg-open'

    def test_error_does_not_raise(self):
        """Ошибка при открытии файла не пробрасывается."""
        from utils.pdf_utils import open_file
        with patch('sys.platform', 'win32'), \
             patch('os.startfile', side_effect=OSError('test')):
            open_file('/nonexistent/path.pdf')  # Не должно упасть


# ==================== Константы цветов ====================

class TestColorConstants:
    """Проверка констант цветов."""

    def test_header_bg_is_hex(self):
        from utils.pdf_utils import HEADER_BG
        assert HEADER_BG is not None

    def test_row_colors_different(self):
        from utils.pdf_utils import ROW_ODD, ROW_EVEN
        assert ROW_ODD != ROW_EVEN
