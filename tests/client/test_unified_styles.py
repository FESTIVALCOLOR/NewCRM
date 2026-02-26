# -*- coding: utf-8 -*-
"""
Тесты unified_styles.py — генерация QSS стилей.

Покрытие:
  - TestUnifiedStylesheet (9) — структура, селекторы, цвета
  - TestStyleConstants (3) — экспортируемые константы
  - TestQSSContentDetails (4) — детальная проверка содержимого QSS
ИТОГО: 16 тестов
"""

import pytest
import re
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestUnifiedStylesheet:
    """Тесты генерации QSS стилей."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Получаем stylesheet с замоканным resource_path."""
        with patch('utils.unified_styles.resource_path', return_value=''):
            from utils.unified_styles import get_unified_stylesheet
            self.stylesheet = get_unified_stylesheet()

    def test_returns_non_empty_string(self):
        """Возвращает непустую строку > 1000 символов."""
        assert isinstance(self.stylesheet, str)
        assert len(self.stylesheet) > 1000

    def test_contains_qpushbutton(self):
        """Содержит стили для QPushButton."""
        assert 'QPushButton' in self.stylesheet

    def test_contains_qtablewidget(self):
        """Содержит стили для QTableWidget."""
        assert 'QTableWidget' in self.stylesheet

    def test_contains_qlineedit(self):
        """Содержит стили для QLineEdit."""
        assert 'QLineEdit' in self.stylesheet

    def test_contains_qcombobox(self):
        """Содержит стили для QComboBox."""
        assert 'QComboBox' in self.stylesheet

    def test_contains_qcalendarwidget(self):
        """Содержит стили для QCalendarWidget."""
        assert 'QCalendarWidget' in self.stylesheet

    def test_contains_hex_colors(self):
        """Содержит цветовые hex-коды (#ffffff, #000000 и т.д.)."""
        hex_pattern = re.compile(r'#[0-9a-fA-F]{6}')
        matches = hex_pattern.findall(self.stylesheet)
        assert len(matches) > 10, f"Найдено только {len(matches)} hex-кодов"

    def test_balanced_braces(self):
        """Сбалансированные фигурные скобки."""
        open_count = self.stylesheet.count('{')
        close_count = self.stylesheet.count('}')
        assert open_count == close_count, (
            f"Несбалансированные скобки: {{ = {open_count}, }} = {close_count}"
        )

    def test_contains_accent_color(self):
        """Содержит акцентный жёлтый цвет #ffd93c."""
        assert '#ffd93c' in self.stylesheet.lower() or '#FFD93C' in self.stylesheet


class TestStyleConstants:
    """Тесты экспортируемых констант стилей."""

    def test_border_color_defined(self):
        """Константа BORDER_COLOR определена и не пуста."""
        with patch('utils.unified_styles.resource_path', return_value=''):
            from utils.unified_styles import BORDER_COLOR
            assert isinstance(BORDER_COLOR, str)
            assert len(BORDER_COLOR) > 0
            assert BORDER_COLOR.startswith('#')

    def test_border_style_defined(self):
        """Константа BORDER_STYLE определена и содержит '1px solid'."""
        with patch('utils.unified_styles.resource_path', return_value=''):
            from utils.unified_styles import BORDER_STYLE
            assert isinstance(BORDER_STYLE, str)
            assert '1px solid' in BORDER_STYLE

    def test_border_style_uses_border_color(self):
        """BORDER_STYLE содержит BORDER_COLOR."""
        with patch('utils.unified_styles.resource_path', return_value=''):
            from utils.unified_styles import BORDER_COLOR, BORDER_STYLE
            assert BORDER_COLOR in BORDER_STYLE


class TestQSSContentDetails:
    """Детальная проверка содержимого QSS."""

    @pytest.fixture(autouse=True)
    def setup(self):
        with patch('utils.unified_styles.resource_path', return_value=''):
            from utils.unified_styles import get_unified_stylesheet
            self.stylesheet = get_unified_stylesheet()

    def test_contains_scrollbar_styles(self):
        """QSS содержит стили скроллбаров."""
        assert 'QScrollBar' in self.stylesheet

    def test_contains_checkbox_styles(self):
        """QSS содержит стили чекбоксов."""
        assert 'QCheckBox' in self.stylesheet

    def test_contains_hover_states(self):
        """QSS содержит состояния :hover."""
        assert ':hover' in self.stylesheet

    def test_contains_border_radius(self):
        """QSS содержит border-radius для скруглённых углов."""
        assert 'border-radius' in self.stylesheet
