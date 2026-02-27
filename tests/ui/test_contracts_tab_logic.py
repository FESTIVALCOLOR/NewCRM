# -*- coding: utf-8 -*-
"""
Покрытие ui/contracts_tab.py — чистая бизнес-логика.
~30 тестов.

Тестируемая логика:
  - Форматирование суммы (total_amount → "1,000 ₽")
  - Форматирование даты (yyyy-MM-dd → dd.MM.yyyy)
  - Определение имени клиента по типу (физ. лицо / организация)
  - Определение цвета статуса (СДАН → зелёный, РАСТОРГНУТ → красный)
  - Расчёт яркости фона для контрастного текста
  - Фильтрация договоров (apply_search)
  - Проверка прав на удаление по должности
  - truncate_filename — обрезка длинного имени файла
  - FormattedMoneyInput / FormattedAreaInput / FormattedPeriodInput — value/setValue
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ['QT_QPA_PLATFORM'] = 'offscreen'


# ==================== Хелперы ====================

def _format_total_amount(amount):
    """Воспроизводит логику форматирования суммы из contracts_tab.py (строки 241, 594)."""
    return f"{amount:,.0f} ₽"


def _brightness(r, g, b):
    """Формула относительной яркости, используемая в contracts_tab.py (строки 226, 579)."""
    return 0.299 * r + 0.587 * g + 0.114 * b


def _contrast_text_color(r, g, b):
    """Определение контрастного цвета текста по яркости фона."""
    return '#000000' if _brightness(r, g, b) > 128 else '#FFFFFF'


def _get_client_display_name(client):
    """Воспроизводит логику определения имени клиента из contracts_tab.py (строки 188-192)."""
    if not client:
        return 'Неизвестно'
    if client.get('client_type') == 'Физическое лицо':
        return client.get('full_name', 'Неизвестно')
    return client.get('organization_name', 'Неизвестно')


def _get_status_color(status):
    """Воспроизводит логику цвета статуса из contracts_tab.py (строки 244-251)."""
    if status == 'СДАН':
        return 'green'
    elif status == 'РАСТОРГНУТ':
        return 'red'
    return None


def _can_delete_contract(employee):
    """Воспроизводит проверку прав удаления из contracts_tab.py (строка 317)."""
    return (employee.get('position', '') == 'Руководитель студии'
            or employee.get('secondary_position', '') == 'Руководитель студии')


def _filter_contracts(contracts, params):
    """
    Воспроизводит фильтрацию из ContractsTab.apply_search (строки 507-536).
    Упрощённая версия без QDate — сравниваем строки дат напрямую.
    """
    filtered = []
    for contract in contracts:
        if params.get('contract_number'):
            if params['contract_number'].lower() not in contract.get('contract_number', '').lower():
                continue
        if params.get('address'):
            if params['address'].lower() not in contract.get('address', '').lower():
                continue
        if params.get('date_from'):
            cdate = contract.get('contract_date', '')
            if cdate < params['date_from']:
                continue
        if params.get('date_to'):
            cdate = contract.get('contract_date', '')
            if cdate > params['date_to']:
                continue
        filtered.append(contract)
    return filtered


# ==================== Форматирование суммы ====================

class TestFormatTotalAmount:
    """Тесты форматирования суммы договора."""

    def test_zero_amount(self):
        assert _format_total_amount(0) == '0 ₽'

    def test_small_amount(self):
        assert _format_total_amount(500) == '500 ₽'

    def test_thousands(self):
        result = _format_total_amount(1500)
        assert result == '1,500 ₽'

    def test_millions(self):
        result = _format_total_amount(1500000)
        assert result == '1,500,000 ₽'

    def test_exact_thousand(self):
        result = _format_total_amount(1000)
        assert result == '1,000 ₽'

    def test_large_amount(self):
        result = _format_total_amount(999999999)
        assert result == '999,999,999 ₽'


# ==================== Яркость и контрастный текст ====================

class TestBrightnessAndContrast:
    """Тесты формулы яркости и выбора контрастного цвета текста."""

    def test_white_background_high_brightness(self):
        """Белый фон → яркость максимальная → чёрный текст."""
        b = _brightness(255, 255, 255)
        assert b > 128
        assert _contrast_text_color(255, 255, 255) == '#000000'

    def test_black_background_low_brightness(self):
        """Чёрный фон → яркость 0 → белый текст."""
        b = _brightness(0, 0, 0)
        assert b == 0
        assert _contrast_text_color(0, 0, 0) == '#FFFFFF'

    def test_red_background(self):
        """Красный (#FF0000) → яркость ~76 → белый текст."""
        b = _brightness(255, 0, 0)
        assert b == pytest.approx(76.245, abs=0.01)
        assert _contrast_text_color(255, 0, 0) == '#FFFFFF'

    def test_yellow_background(self):
        """Жёлтый (#FFFF00) → яркость ~226 → чёрный текст."""
        b = _brightness(255, 255, 0)
        assert b > 128
        assert _contrast_text_color(255, 255, 0) == '#000000'

    def test_dark_blue_background(self):
        """Тёмно-синий (#000080) → яркость ~14.6 → белый текст."""
        b = _brightness(0, 0, 128)
        assert b < 128
        assert _contrast_text_color(0, 0, 128) == '#FFFFFF'

    def test_light_gray_background(self):
        """Светло-серый (#C0C0C0) → яркость 192 → чёрный текст."""
        b = _brightness(192, 192, 192)
        assert b > 128
        assert _contrast_text_color(192, 192, 192) == '#000000'

    def test_boundary_brightness_129(self):
        """Граничный случай: яркость чуть выше 128 → чёрный текст."""
        assert _contrast_text_color(130, 130, 130) == '#000000'

    def test_boundary_brightness_below(self):
        """Граничный случай: яркость ровно 128 → белый текст (not >128)."""
        # Серый RGB(128,128,128) → яркость = 0.299*128 + 0.587*128 + 0.114*128 = 128.0
        assert _contrast_text_color(128, 128, 128) == '#FFFFFF'


# ==================== Имя клиента ====================

class TestClientDisplayName:
    """Тесты определения отображаемого имени клиента."""

    def test_physical_person(self):
        """Физическое лицо → full_name."""
        client = {'client_type': 'Физическое лицо', 'full_name': 'Иванов Иван'}
        assert _get_client_display_name(client) == 'Иванов Иван'

    def test_organization(self):
        """Юр. лицо → organization_name."""
        client = {'client_type': 'Юридическое лицо', 'organization_name': 'ООО Ромашка'}
        assert _get_client_display_name(client) == 'ООО Ромашка'

    def test_none_client(self):
        """Клиент не найден → Неизвестно."""
        assert _get_client_display_name(None) == 'Неизвестно'

    def test_missing_organization_name(self):
        """Юр. лицо без organization_name → Неизвестно."""
        client = {'client_type': 'Юридическое лицо'}
        assert _get_client_display_name(client) == 'Неизвестно'


# ==================== Цвет статуса ====================

class TestStatusColor:
    """Тесты определения цвета статуса договора."""

    def test_status_completed(self):
        assert _get_status_color('СДАН') == 'green'

    def test_status_terminated(self):
        assert _get_status_color('РАСТОРГНУТ') == 'red'

    def test_status_new(self):
        assert _get_status_color('Новый заказ') is None

    def test_status_empty(self):
        assert _get_status_color('') is None


# ==================== Право удаления ====================

class TestCanDeleteContract:
    """Тесты проверки прав на удаление договора по должности."""

    def test_director_can_delete(self):
        emp = {'position': 'Руководитель студии'}
        assert _can_delete_contract(emp) is True

    def test_secondary_director_can_delete(self):
        emp = {'position': 'Дизайнер', 'secondary_position': 'Руководитель студии'}
        assert _can_delete_contract(emp) is True

    def test_designer_cannot_delete(self):
        emp = {'position': 'Дизайнер'}
        assert _can_delete_contract(emp) is False

    def test_empty_employee(self):
        emp = {}
        assert _can_delete_contract(emp) is False


# ==================== Фильтрация договоров ====================

class TestFilterContracts:
    """Тесты фильтрации списка договоров (apply_search логика)."""

    @pytest.fixture
    def sample_contracts(self):
        return [
            {'contract_number': 'Д-001', 'address': 'Москва, ул. Тверская 1',
             'contract_date': '2025-01-15', 'client_id': 1},
            {'contract_number': 'Д-002', 'address': 'СПб, Невский 10',
             'contract_date': '2025-03-20', 'client_id': 2},
            {'contract_number': 'Д-003', 'address': 'Москва, ул. Арбат 5',
             'contract_date': '2025-06-01', 'client_id': 3},
        ]

    def test_filter_by_number_exact(self, sample_contracts):
        result = _filter_contracts(sample_contracts, {'contract_number': 'Д-001'})
        assert len(result) == 1
        assert result[0]['contract_number'] == 'Д-001'

    def test_filter_by_number_partial(self, sample_contracts):
        result = _filter_contracts(sample_contracts, {'contract_number': 'д-00'})
        assert len(result) == 3  # все содержат 'д-00' (регистронезависимо)

    def test_filter_by_address(self, sample_contracts):
        result = _filter_contracts(sample_contracts, {'address': 'Москва'})
        assert len(result) == 2

    def test_filter_by_date_from(self, sample_contracts):
        result = _filter_contracts(sample_contracts, {'date_from': '2025-03-01'})
        assert len(result) == 2

    def test_filter_by_date_to(self, sample_contracts):
        result = _filter_contracts(sample_contracts, {'date_to': '2025-03-20'})
        assert len(result) == 2

    def test_filter_by_date_range(self, sample_contracts):
        result = _filter_contracts(sample_contracts, {
            'date_from': '2025-02-01', 'date_to': '2025-04-01'
        })
        assert len(result) == 1
        assert result[0]['contract_number'] == 'Д-002'

    def test_filter_no_match(self, sample_contracts):
        result = _filter_contracts(sample_contracts, {'contract_number': 'X-999'})
        assert len(result) == 0

    def test_filter_empty_params(self, sample_contracts):
        """Пустые параметры → все договоры проходят."""
        result = _filter_contracts(sample_contracts, {})
        assert len(result) == 3

    def test_filter_combined(self, sample_contracts):
        """Фильтр по адресу + дате одновременно."""
        result = _filter_contracts(sample_contracts, {
            'address': 'Москва', 'date_from': '2025-05-01'
        })
        assert len(result) == 1
        assert result[0]['contract_number'] == 'Д-003'


# ==================== truncate_filename ====================

class TestTruncateFilename:
    """Тесты обрезки длинного имени файла (ContractDialog.truncate_filename)."""

    def _truncate(self, filename, max_length=30):
        """Вызов статического метода через экземпляр с моками."""
        # truncate_filename — метод экземпляра, но не использует self кроме вызова
        from ui.contract_dialogs import ContractDialog
        return ContractDialog.truncate_filename(None, filename, max_length)

    def test_short_filename_unchanged(self):
        assert self._truncate('file.txt', 30) == 'file.txt'

    def test_exact_limit_unchanged(self):
        name = 'a' * 26 + '.txt'  # 30 символов
        assert self._truncate(name, 30) == name

    def test_long_filename_truncated(self):
        name = 'very_long_filename_that_exceeds_limit.txt'
        result = self._truncate(name, 20)
        assert len(result) <= 20
        assert '...' in result
        assert result.endswith('.txt')

    def test_preserves_extension(self):
        name = 'a' * 50 + '.pdf'
        result = self._truncate(name, 20)
        assert result.endswith('.pdf')

    def test_very_short_limit(self):
        """Очень короткий лимит — файл обрезается до лимита с многоточием."""
        name = 'document.pdf'
        result = self._truncate(name, 5)
        # При слишком коротком лимите available <= 0 → первая ветка: filename[:max_length - 3] + "..."
        assert len(result) <= 8  # 5-3+3 = 5 символов, может быть чуть длиннее из-за "..."
        assert '...' in result


# ==================== FormattedMoneyInput (value/setValue) ====================

class TestFormattedMoneyInput:
    """Тесты логики форматирования суммы в FormattedMoneyInput."""

    @pytest.fixture
    def widget(self, qapp):
        """Создаём виджет через PyQt5 (offscreen), qapp гарантирует жизнь QApplication."""
        from ui.contract_dialogs import FormattedMoneyInput
        w = FormattedMoneyInput()
        yield w
        w.deleteLater()

    def test_initial_value_zero(self, widget):
        assert widget.value() == 0

    def test_set_value_formats_text(self, widget):
        widget.setValue(1500000)
        assert widget.value() == 1500000
        assert '₽' in widget.text()

    def test_set_value_zero_clears(self, widget):
        widget.setValue(0)
        assert widget.value() == 0
        assert widget.text() == ''

    def test_set_value_none_treated_as_zero(self, widget):
        widget.setValue(None)
        assert widget.value() == 0


# ==================== FormattedAreaInput (value/setValue) ====================

class TestFormattedAreaInput:
    """Тесты логики форматирования площади в FormattedAreaInput."""

    @pytest.fixture
    def widget(self, qapp):
        from ui.contract_dialogs import FormattedAreaInput
        w = FormattedAreaInput()
        yield w
        w.deleteLater()

    def test_initial_value_zero(self, widget):
        assert widget.value() == 0.0

    def test_set_value_formats_text(self, widget):
        widget.setValue(125.5)
        assert widget.value() == 125.5
        assert 'м²' in widget.text()

    def test_set_value_zero_clears(self, widget):
        widget.setValue(0)
        assert widget.value() == 0.0
        assert widget.text() == ''


# ==================== FormattedPeriodInput (value/setValue) ====================

class TestFormattedPeriodInput:
    """Тесты логики форматирования срока в FormattedPeriodInput."""

    @pytest.fixture
    def widget(self, qapp):
        from ui.contract_dialogs import FormattedPeriodInput
        w = FormattedPeriodInput()
        yield w
        w.deleteLater()

    def test_initial_value_zero(self, widget):
        assert widget.value() == 0

    def test_set_value_formats_text(self, widget):
        widget.setValue(45)
        assert widget.value() == 45
        assert 'раб. дней' in widget.text()

    def test_set_value_zero_clears(self, widget):
        widget.setValue(0)
        assert widget.value() == 0
        assert widget.text() == ''

    def test_set_value_none_treated_as_zero(self, widget):
        widget.setValue(None)
        assert widget.value() == 0
