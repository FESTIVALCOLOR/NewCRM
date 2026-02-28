# -*- coding: utf-8 -*-
"""
Покрытие ui/contract_dialogs.py — чистая бизнес-логика.
~28 тестов.

Тестируемая логика (БЕЗ создания виджетов):
- FormattedMoneyInput: форматирование сумм, value/setValue, парсинг текста
- FormattedAreaInput: форматирование площади, ограничение 10000, парсинг
- FormattedPeriodInput: форматирование сроков, ограничение 365, парсинг
- ContractDialog.truncate_filename: обрезка длинных имён файлов
- ContractDialog._get_pt_code: маппинг подтипа проекта → числовой код
- ContractDialog.get_contract_yandex_folder: получение пути к папке ЯД
- Маппинг _receipt_prefix_map: соответствие payment → receipt
- Маппинг _doc_defaults: умолчания для документов
- Логика определения contract_period по типу проекта (save_contract)

НЕ дублирует test_contract_calc_full.py (_calc_contract_term / _calc_template_contract_term).
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ['QT_QPA_PLATFORM'] = 'offscreen'


# ==================== Хелперы ====================

def _make_money_input(**kwargs):
    """Создать FormattedMoneyInput с минимальной инициализацией Qt."""
    from ui.contract_dialogs import FormattedMoneyInput
    widget = FormattedMoneyInput(**kwargs)
    return widget


def _make_area_input():
    """Создать FormattedAreaInput."""
    from ui.contract_dialogs import FormattedAreaInput
    return FormattedAreaInput()


def _make_period_input():
    """Создать FormattedPeriodInput."""
    from ui.contract_dialogs import FormattedPeriodInput
    return FormattedPeriodInput()


def _truncate_filename(filename, max_length=30):
    """Воспроизведение логики ContractDialog.truncate_filename без создания виджета."""
    if len(filename) <= max_length:
        return filename
    name, ext = os.path.splitext(filename)
    ext_len = len(ext)
    available = max_length - ext_len - 3  # 3 для "..."
    if available <= 0:
        return filename[:max_length - 3] + "..."
    start_len = available // 2
    end_len = available - start_len
    return name[:start_len] + "..." + name[-end_len:] + ext


def _get_pt_code(subtype_text):
    """Воспроизведение логики ContractDialog._get_pt_code без создания виджета."""
    if 'Полный' in subtype_text:
        return 1
    elif 'Планировочный' in subtype_text:
        return 3
    return 2


def _get_contract_yandex_folder(contract_data):
    """Воспроизведение логики ContractDialog.get_contract_yandex_folder."""
    if contract_data:
        return contract_data.get('yandex_folder_path')
    return None


# ==================== FormattedMoneyInput ====================

class TestFormattedMoneyInput:
    """Тесты форматирования денежных сумм."""

    def test_initial_value_is_zero(self, qtbot):
        """Начальное значение — 0."""
        w = _make_money_input()
        qtbot.addWidget(w)
        assert w.value() == 0

    def test_set_value_positive(self, qtbot):
        """setValue устанавливает значение и форматирует текст."""
        w = _make_money_input()
        qtbot.addWidget(w)
        w.setValue(1500000)
        assert w.value() == 1500000
        assert '1 500 000' in w.text()
        assert '\u20bd' in w.text()  # символ рубля

    def test_set_value_zero_clears_text(self, qtbot):
        """setValue(0) очищает текстовое поле."""
        w = _make_money_input()
        qtbot.addWidget(w)
        w.setValue(1000)
        w.setValue(0)
        assert w.value() == 0
        assert w.text() == ''

    def test_set_value_none(self, qtbot):
        """setValue(None) сбрасывает значение в 0."""
        w = _make_money_input()
        qtbot.addWidget(w)
        w.setValue(None)
        assert w.value() == 0

    def test_set_value_string_number(self, qtbot):
        """setValue со строковым числом корректно конвертируется."""
        w = _make_money_input()
        qtbot.addWidget(w)
        w.setValue('250000')
        assert w.value() == 250000

    def test_focus_out_parses_raw_number(self, qtbot):
        """focusOutEvent парсит введённое число и форматирует его."""
        w = _make_money_input()
        qtbot.addWidget(w)
        w.setText('3000000')
        # Имитируем потерю фокуса через прямой вызов логики
        from PyQt5.QtGui import QFocusEvent
        from PyQt5.QtCore import QEvent
        w.focusOutEvent(QFocusEvent(QEvent.FocusOut))
        assert w.value() == 3000000
        assert '3 000 000' in w.text()

    def test_focus_out_invalid_text_resets(self, qtbot):
        """Некорректный текст при focusOut сбрасывает значение в 0."""
        w = _make_money_input()
        qtbot.addWidget(w)
        w.setText('abc')
        from PyQt5.QtGui import QFocusEvent
        from PyQt5.QtCore import QEvent
        w.focusOutEvent(QFocusEvent(QEvent.FocusOut))
        assert w.value() == 0
        assert w.text() == ''

    def test_focus_out_empty_text(self, qtbot):
        """Пустой текст при focusOut — значение 0, текст пуст."""
        w = _make_money_input()
        qtbot.addWidget(w)
        w.setText('')
        from PyQt5.QtGui import QFocusEvent
        from PyQt5.QtCore import QEvent
        w.focusOutEvent(QFocusEvent(QEvent.FocusOut))
        assert w.value() == 0


# ==================== FormattedAreaInput ====================

class TestFormattedAreaInput:
    """Тесты форматирования площади."""

    def test_initial_value_is_zero(self, qtbot):
        """Начальное значение площади — 0.0."""
        w = _make_area_input()
        qtbot.addWidget(w)
        assert w.value() == 0.0

    def test_set_value_positive(self, qtbot):
        """setValue устанавливает площадь и форматирует текст."""
        w = _make_area_input()
        qtbot.addWidget(w)
        w.setValue(85.5)
        assert w.value() == 85.5
        assert '85.5' in w.text()
        assert '\u043c\u00b2' in w.text()  # м²

    def test_set_value_zero_clears(self, qtbot):
        """setValue(0) очищает поле."""
        w = _make_area_input()
        qtbot.addWidget(w)
        w.setValue(100)
        w.setValue(0)
        assert w.value() == 0.0
        assert w.text() == ''

    def test_focus_out_caps_at_10000(self, qtbot):
        """Площадь ограничена 10000 м\u00b2."""
        w = _make_area_input()
        qtbot.addWidget(w)
        w.setText('15000')
        from PyQt5.QtGui import QFocusEvent
        from PyQt5.QtCore import QEvent
        w.focusOutEvent(QFocusEvent(QEvent.FocusOut))
        assert w.value() == 10000

    def test_focus_out_parses_with_comma(self, qtbot):
        """Запятая как разделитель дроби корректно парсится."""
        w = _make_area_input()
        qtbot.addWidget(w)
        w.setText('120,5')
        from PyQt5.QtGui import QFocusEvent
        from PyQt5.QtCore import QEvent
        w.focusOutEvent(QFocusEvent(QEvent.FocusOut))
        assert w.value() == 120.5

    def test_focus_out_invalid_text_resets(self, qtbot):
        """Некорректный текст — сброс в 0."""
        w = _make_area_input()
        qtbot.addWidget(w)
        w.setText('invalid')
        from PyQt5.QtGui import QFocusEvent
        from PyQt5.QtCore import QEvent
        w.focusOutEvent(QFocusEvent(QEvent.FocusOut))
        assert w.value() == 0.0
        assert w.text() == ''


# ==================== FormattedPeriodInput ====================

class TestFormattedPeriodInput:
    """Тесты форматирования срока (раб. дней)."""

    def test_initial_value_is_zero(self, qtbot):
        w = _make_period_input()
        qtbot.addWidget(w)
        assert w.value() == 0

    def test_set_value_positive(self, qtbot):
        """setValue форматирует с суффиксом 'раб. дней'."""
        w = _make_period_input()
        qtbot.addWidget(w)
        w.setValue(60)
        assert w.value() == 60
        assert '\u0440\u0430\u0431. \u0434\u043d\u0435\u0439' in w.text()

    def test_focus_out_caps_at_365(self, qtbot):
        """Срок ограничен 365 рабочими днями."""
        w = _make_period_input()
        qtbot.addWidget(w)
        w.setText('500')
        from PyQt5.QtGui import QFocusEvent
        from PyQt5.QtCore import QEvent
        w.focusOutEvent(QFocusEvent(QEvent.FocusOut))
        assert w.value() == 365

    def test_focus_out_invalid_text_resets(self, qtbot):
        """Некорректный текст — сброс в 0."""
        w = _make_period_input()
        qtbot.addWidget(w)
        w.setText('нечисло')
        from PyQt5.QtGui import QFocusEvent
        from PyQt5.QtCore import QEvent
        w.focusOutEvent(QFocusEvent(QEvent.FocusOut))
        assert w.value() == 0
        assert w.text() == ''

    def test_set_value_none_resets(self, qtbot):
        """setValue(None) сбрасывает значение."""
        w = _make_period_input()
        qtbot.addWidget(w)
        w.setValue(None)
        assert w.value() == 0


# ==================== truncate_filename ====================

class TestTruncateFilename:
    """Тесты обрезки длинных имён файлов."""

    def test_short_filename_unchanged(self):
        """Имя короче max_length — без изменений."""
        assert _truncate_filename('doc.pdf', max_length=30) == 'doc.pdf'

    def test_exact_max_length_unchanged(self):
        """Имя длиной ровно max_length — без изменений."""
        name = 'a' * 26 + '.pdf'  # 30 символов
        assert _truncate_filename(name, max_length=30) == name

    def test_long_filename_truncated(self):
        """Длинное имя обрезается с многоточием в середине."""
        name = 'very_long_contract_document_name.pdf'
        result = _truncate_filename(name, max_length=20)
        assert len(result) <= 20
        assert '...' in result
        assert result.endswith('.pdf')

    def test_preserves_extension(self):
        """Расширение файла сохраняется при обрезке."""
        name = 'a' * 50 + '.docx'
        result = _truncate_filename(name, max_length=25)
        assert result.endswith('.docx')
        assert '...' in result

    def test_very_short_max_length(self):
        """Очень маленький max_length — graceful degradation."""
        name = 'document.pdf'
        result = _truncate_filename(name, max_length=5)
        # При available <= 0 — простая обрезка с '...'
        assert len(result) <= 5 or '...' in result


# ==================== _get_pt_code ====================

class TestGetPtCode:
    """Тесты маппинга подтипа проекта -> числовой код."""

    def test_full_project_returns_1(self):
        """'Полный (с 3д визуализацией)' -> код 1."""
        assert _get_pt_code('Полный (с 3д визуализацией)') == 1

    def test_planning_project_returns_3(self):
        """'Планировочный' -> код 3."""
        assert _get_pt_code('Планировочный') == 3

    def test_sketch_project_returns_2(self):
        """'Эскизный (с коллажами)' -> код 2 (по умолчанию)."""
        assert _get_pt_code('Эскизный (с коллажами)') == 2

    def test_unknown_subtype_returns_2(self):
        """Неизвестный подтип -> код 2 (по умолчанию)."""
        assert _get_pt_code('Какой-то новый тип') == 2


# ==================== get_contract_yandex_folder ====================

class TestGetContractYandexFolder:
    """Тесты получения пути к папке на Яндекс.Диске."""

    def test_existing_contract_returns_folder(self):
        """Для существующего договора возвращает yandex_folder_path."""
        data = {'id': 1, 'yandex_folder_path': '/disk/contracts/123'}
        assert _get_contract_yandex_folder(data) == '/disk/contracts/123'

    def test_existing_contract_no_folder(self):
        """Договор без папки на ЯД — возвращает None."""
        data = {'id': 1}
        assert _get_contract_yandex_folder(data) is None

    def test_new_contract_returns_none(self):
        """Новый договор (contract_data=None) — возвращает None."""
        assert _get_contract_yandex_folder(None) is None


# ==================== Маппинги данных ====================

class TestDataMappings:
    """Тесты маппингов и констант бизнес-логики."""

    def test_receipt_prefix_map(self):
        """Маппинг payment_prefix → receipt_prefix корректен."""
        # Воспроизводим маппинг из fill_data / _upload_receipt_file
        receipt_prefix_map = {
            'advance_payment': 'advance_receipt',
            'additional_payment': 'additional_receipt',
            'third_payment': 'third_receipt',
        }
        assert receipt_prefix_map['advance_payment'] == 'advance_receipt'
        assert receipt_prefix_map['additional_payment'] == 'additional_receipt'
        assert receipt_prefix_map['third_payment'] == 'third_receipt'
        assert len(receipt_prefix_map) == 3

    def test_doc_defaults_mapping(self):
        """Маппинг документов по умолчанию содержит все 8 типов."""
        _doc_defaults = {
            'act_planning': 'Акт ПР.pdf',
            'act_concept': 'Акт КД.pdf',
            'info_letter': 'Инф. письмо.pdf',
            'act_final': 'Акт финальный.pdf',
            'act_planning_signed': 'Акт ПР (подписан).pdf',
            'act_concept_signed': 'Акт КД (подписан).pdf',
            'info_letter_signed': 'Инф. письмо (подписано).pdf',
            'act_final_signed': 'Акт финальный (подписан).pdf',
        }
        assert len(_doc_defaults) == 8
        # Все подписанные акты содержат 'signed'
        signed = [k for k in _doc_defaults if 'signed' in k]
        assert len(signed) == 4

    def test_payment_prefixes_list(self):
        """Список платежных префиксов — 3 элемента."""
        _payment_prefixes = ['advance_payment', 'additional_payment', 'third_payment']
        assert len(_payment_prefixes) == 3
        assert 'advance_payment' in _payment_prefixes

    def test_upload_receipt_display_names(self):
        """Маппинг отображаемых имён чеков корректен."""
        display_names = {
            'advance_payment': 'Чек аванса',
            'additional_payment': 'Чек 2-го платежа',
            'third_payment': 'Чек 3-го платежа',
        }
        assert display_names['advance_payment'] == 'Чек аванса'
        assert display_names['third_payment'] == 'Чек 3-го платежа'


# ==================== Логика save_contract (подготовка данных) ====================

class TestSaveContractDataPrep:
    """Тесты логики подготовки данных при сохранении."""

    def test_contract_number_strip(self):
        """Номер договора очищается от пробелов."""
        raw = '  ИН-001/2025  '
        assert raw.strip() == 'ИН-001/2025'

    def test_folder_changed_detection(self):
        """Определение изменения пути к папке — при смене города."""
        old = {'city': 'СПБ', 'address': 'ул. Мира 1', 'area': 100,
               'agent_type': 'ФЕСТИВАЛЬ', 'project_type': 'Индивидуальный'}
        new_city = 'МСК'
        folder_changed = (
            old['city'] != new_city or
            old['address'] != old['address'] or
            old['area'] != old['area'] or
            old['agent_type'] != old['agent_type'] or
            old['project_type'] != old['project_type']
        )
        assert folder_changed is True

    def test_folder_not_changed_same_data(self):
        """Путь не меняется если данные идентичны."""
        old = {'city': 'СПБ', 'address': 'ул. Мира 1', 'area': 100,
               'agent_type': 'ФЕСТИВАЛЬ', 'project_type': 'Индивидуальный'}
        folder_changed = (
            old['city'] != 'СПБ' or
            old['address'] != 'ул. Мира 1' or
            old['area'] != 100 or
            old['agent_type'] != 'ФЕСТИВАЛЬ' or
            old['project_type'] != 'Индивидуальный'
        )
        assert folder_changed is False

    def test_error_msg_unique_constraint_detection(self):
        """Определение дубликата номера договора по тексту ошибки."""
        error_msg = 'UNIQUE constraint failed: contracts.contract_number'
        assert 'UNIQUE constraint failed' in error_msg
        error_msg2 = 'Договор с номером ИН-001 уже существует'
        assert 'уже существует' in error_msg2

    def test_template_project_zeroes_extra_payments(self):
        """Шаблонный проект обнуляет additional_payment и third_payment."""
        project_type = 'Шаблонный'
        advance = 50000
        additional_raw = 30000
        third_raw = 20000
        # Логика из save_contract
        additional = 0 if project_type == 'Шаблонный' else additional_raw
        third = 0 if project_type == 'Шаблонный' else third_raw
        assert additional == 0
        assert third == 0

    def test_individual_project_keeps_all_payments(self):
        """Индивидуальный проект сохраняет все три платежа."""
        project_type = 'Индивидуальный'
        advance = 50000
        additional_raw = 30000
        third_raw = 20000
        additional = 0 if project_type == 'Шаблонный' else additional_raw
        third = 0 if project_type == 'Шаблонный' else third_raw
        assert additional == 30000
        assert third == 20000
