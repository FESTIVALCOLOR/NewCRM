# -*- coding: utf-8 -*-
"""
Anti-pattern тесты: защита от повторяющихся UI регрессий.

Ловят паттерны кода, которые многократно приводили к багам:
- Хардкод значений в фильтрах (вместо динамической загрузки)
- Потеря searchable combo (editable, completer, eventFilter)
- Exact match вместо substring в фильтрах адреса
- Отсутствие PNG в фильтрах файлов
- Потеря CRM карточки при создании договора

Каждый тест привязан к конкретному багу с комментарием.
"""

import os
from pathlib import Path
import re

import pytest

UI_DIR = Path(__file__).parent.parent.parent / "ui"
SERVER_DIR = Path(__file__).parent.parent.parent / "server"


def _read(filepath):
    return filepath.read_text(encoding="utf-8")


# ======================================================================
# 1. ХАРДКОД ЗНАЧЕНИЙ В ФИЛЬТРАХ
# Баг: agent_type_filter содержал ['Фестиваль', 'Петрович'] вместо
#      динамической загрузки из данных. Повторялся 3 раза.
# ======================================================================


class TestNoHardcodedFilterValues:
    """Фильтры НЕ должны содержать хардкод бизнес-значений."""

    # Значения, которые НЕ должны быть в addItem/addItems фильтров
    FORBIDDEN_HARDCODED = [
        "Фестиваль",
        "Петрович",  # agent_type — загружаются из БД
    ]

    def test_salaries_no_hardcoded_agent_types(self):
        """salaries_tab.py НЕ должен хардкодить типы агентов в addItem."""
        content = _read(UI_DIR / "salaries_tab.py")
        for value in self.FORBIDDEN_HARDCODED:
            # Ищем addItem('Фестиваль') или addItems([...'Фестиваль'...])
            pattern = rf"addItem[s]?\s*\([^)]*['\"]{re.escape(value)}['\"]"
            matches = re.findall(pattern, content)
            assert not matches, f"РЕГРЕССИЯ: salaries_tab.py содержит хардкод '{value}' в addItem! Типы агентов должны загружаться динамически из данных платежей."


# ======================================================================
# 2. SEARCHABLE COMBO — обязательные компоненты
# Баг: при рефакторинге теряли editable, completer, eventFilter.
#      Повторялся 4+ раза в salaries_tab и contract_dialogs.
# ======================================================================


class TestSearchableComboRequired:
    """Файлы с searchable combo ДОЛЖНЫ содержать все компоненты."""

    @pytest.mark.parametrize(
        "filename,required_patterns",
        [
            (
                "salaries_tab.py",
                [
                    ("_setup_searchable_combo", "метод настройки searchable combo"),
                    ("def eventFilter", "метод eventFilter для clear-on-click"),
                    ("setEditable", "включение editable режима (внутри _setup_searchable_combo)"),
                    ("MatchContains", "поиск по подстроке в QCompleter"),
                    ("NoInsert", "запрет добавления пользовательского текста"),
                    ("_searchable", "свойство _searchable для eventFilter"),
                ],
            ),
            (
                "contract_dialogs.py",
                [
                    ("def eventFilter", "метод eventFilter для clear-on-click"),
                    ("client_combo.*setProperty|setProperty.*_searchable", "свойство _searchable на client_combo"),
                ],
            ),
        ],
    )
    def test_searchable_combo_components(self, filename, required_patterns):
        """Проверяем наличие всех компонентов searchable combo."""
        content = _read(UI_DIR / filename)
        for pattern, description in required_patterns:
            found = re.search(pattern, content)
            assert found, f"РЕГРЕССИЯ в {filename}: отсутствует {description}! Паттерн '{pattern}' не найден. Searchable combo не будет работать правильно."


# ======================================================================
# 3. EXACT MATCH ВМЕСТО SUBSTRING В ФИЛЬТРАХ АДРЕСА
# Баг: payment.get('address') != f_address вместо
#      f_address.lower() not in address.lower()
#      Повторялся 2 раза.
# ======================================================================


class TestNoExactMatchInAddressFilter:
    """Фильтр адреса ДОЛЖЕН использовать substring match."""

    EXACT_MATCH_PATTERNS = [
        r"\.get\(['\"]address['\"]\)\s*!=\s*f_address",
        r"\.get\(['\"]address['\"]\)\s*==\s*f_address",
        r"address\s*!=\s*f_address",
        r"address\s*==\s*f_address",
    ]

    def test_salaries_no_exact_address_match(self):
        """salaries_tab.py НЕ должен использовать exact match для адреса."""
        content = _read(UI_DIR / "salaries_tab.py")
        for pattern in self.EXACT_MATCH_PATTERNS:
            matches = re.findall(pattern, content)
            assert not matches, f"РЕГРЕССИЯ: salaries_tab.py использует exact match по адресу: '{matches[0]}'. Должен быть substring match: f_address.lower() not in address.lower()"


# ======================================================================
# 4. PNG В ФИЛЬТРАХ ФАЙЛОВ
# Баг: при рефакторинге теряли *.png в QFileDialog фильтрах.
#      Повторялся 2 раза.
# ======================================================================


class TestPngInFileFilters:
    """Все загрузки файлов ДОЛЖНЫ поддерживать PNG."""

    @pytest.mark.parametrize(
        "filename",
        [
            "contract_dialogs.py",
            "crm_card_edit_dialog.py",
            "crm_dialogs.py",
        ],
    )
    def test_file_filters_include_png(self, filename):
        """QFileDialog фильтры ДОЛЖНЫ содержать *.png."""
        filepath = UI_DIR / filename
        if not filepath.exists():
            pytest.skip(f"{filename} не найден")
        content = _read(filepath)
        # Ищем все QFileDialog фильтры с *.pdf или *.jpg
        dialog_calls = re.findall(r'getOpenFileName\([^)]*["\']([^"\']*\*\.[^"\']*)["\']', content)
        for filter_str in dialog_calls:
            if "*.pdf" in filter_str or "*.jpg" in filter_str:
                assert "*.png" in filter_str, f"РЕГРЕССИЯ в {filename}: фильтр '{filter_str}' НЕ содержит *.png! Пользователь не сможет загрузить PNG файл."


# ======================================================================
# 5. CRM КАРТОЧКА ПРИ СОЗДАНИИ ДОГОВОРА
# Баг: CRM карточка не создавалась автоматически.
#      Причины: серверный код удалён или клиент не делает fallback.
# ======================================================================


class TestCRMCardCreationGuard:
    """Автоматическое создание CRM карточки при создании договора."""

    def test_server_creates_crm_card_in_create_contract(self):
        """Серверный create_contract ДОЛЖЕН создавать CRMCard."""
        content = _read(SERVER_DIR / "routers" / "contracts_router.py")
        # Ищем CRMCard( в контексте create_contract
        assert "CRMCard(" in content, "РЕГРЕССИЯ: contracts_router.py не создаёт CRMCard! При создании договора CRM карточка не будет создана."

    def test_client_has_crm_card_fallback(self):
        """Клиент ДОЛЖЕН иметь fallback _ensure_crm_card_exists."""
        content = _read(UI_DIR / "contract_dialogs.py")
        assert "_ensure_crm_card_exists" in content, "РЕГРЕССИЯ: contract_dialogs.py потерял _ensure_crm_card_exists! Нет fallback если сервер не создаст CRM карточку."


# ======================================================================
# 6. TRUNCATE_FILENAME — MAX_LENGTH
# Баг: max_length был 30-50, длинные имена ломали layout.
#      Повторялся 2 раза.
# ======================================================================


class TestTruncateFilenameGuard:
    """truncate_filename ДОЛЖЕН обрезать достаточно агрессивно."""

    @pytest.mark.parametrize(
        "filename",
        [
            "contract_dialogs.py",
            "crm_card_edit_dialog.py",
            "crm_dialogs.py",
        ],
    )
    def test_truncate_max_length_not_too_large(self, filename):
        """max_length по умолчанию ДОЛЖЕН быть <= 25."""
        filepath = UI_DIR / filename
        if not filepath.exists():
            pytest.skip(f"{filename} не найден")
        content = _read(filepath)
        matches = re.findall(r"def truncate_filename\([^)]*max_length\s*=\s*(\d+)", content)
        for match in matches:
            max_length = int(match)
            assert max_length <= 25, f"РЕГРЕССИЯ в {filename}: truncate_filename default max_length={max_length}, должен быть <= 25. Длинные имена файлов будут ломать layout."
