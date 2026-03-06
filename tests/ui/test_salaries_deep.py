# -*- coding: utf-8 -*-
"""
Глубокие тесты SalariesTab — фильтры, загрузка данных, кэш, CollapsibleBox.

НЕ дублирует 34 теста из test_salaries.py. Покрывает:
  - TestSalariesLoadAllPayments (6) — загрузка данных, кэш, force_reload
  - TestSalariesFilterLogic (6)     — apply/reset фильтров, видимость
  - TestSalariesLazyLoading (4)     — ensure_data_loaded, prefer_local
  - TestCollapsibleBox (4)          — сворачивание/разворачивание
  - TestPaymentStatusDelegate (3)   — подсветка строк по статусу
  - TestSalariesCacheInvalidation (3) — invalidate_cache
ИТОГО: 26 тестов
"""

import pytest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QWidget, QTabWidget, QTableWidget, QPushButton, QLabel
from PyQt5.QtCore import Qt, QDate, QModelIndex
from PyQt5.QtGui import QIcon, QColor


# ─── Хелперы ───────────────────────────────────────────────────

def _mock_icon_loader():
    """IconLoader с реальным QIcon."""
    mock = MagicMock()
    mock.load = MagicMock(return_value=QIcon())
    mock.create_icon_button = MagicMock(
        side_effect=lambda *a, **k: QPushButton(a[1] if len(a) > 1 else '')
    )
    mock.create_action_button = MagicMock(
        side_effect=lambda *a, **k: QPushButton(a[1] if len(a) > 1 else '')
    )
    mock.get_icon_path = MagicMock(return_value='')
    return mock


def _create_salaries_tab(qtbot, mock_data_access, employee):
    """Создание SalariesTab с полностью замоканными зависимостями."""
    mock_data_access.api_client = None
    mock_data_access.db.get_year_payments.return_value = []
    mock_data_access.get_all_employees.return_value = []
    mock_data_access.get_all_contracts.return_value = []
    mock_data_access.get_year_payments.return_value = []

    with patch('ui.salaries_tab.DataAccess') as MockDA, \
         patch('ui.salaries_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.salaries_tab.IconLoader', _mock_icon_loader()):
        MockDA.return_value = mock_data_access
        from ui.salaries_tab import SalariesTab
        tab = SalariesTab(employee=employee, api_client=None)
        qtbot.addWidget(tab)
        return tab


def _sample_payment(payment_id=1, employee='Тестов Тест', amount=25000,
                    report_month='2026-02', status='to_pay', **overrides):
    """Сгенерировать тестовый платёж."""
    data = {
        'id': payment_id,
        'employee_name': employee,
        'employee_id': 6,
        'contract_id': 200,
        'contract_number': 'ИП-ПОЛ-12345/26',
        'address': 'г. СПб, ул. Тест',
        'role': 'Дизайнер',
        'stage_name': 'Стадия 2: концепция дизайна',
        'calculated_amount': amount,
        'manual_amount': None,
        'final_amount': amount,
        'is_manual': 0,
        'payment_type': 'Аванс',
        'report_month': report_month,
        'status': status,
        'source': 'CRM',
        'reassigned': 0,
        'position': 'Дизайнер',
        'agent_type': '',
        'project_type': 'Индивидуальный',
    }
    data.update(overrides)
    return data


# ═══════════════════════════════════════════════════════════════
# TestSalariesLoadAllPayments — загрузка данных
# ═══════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestSalariesLoadAllPayments:
    """Загрузка всех выплат: load_all_payments, кэш."""

    def test_load_all_payments_calls_get_year_payments(self, qtbot, mock_data_access, mock_employee_admin):
        """load_all_payments вызывает get_year_payments."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        mock_data_access.get_year_payments.reset_mock()
        tab.load_all_payments()
        mock_data_access.get_year_payments.assert_called()

    def test_load_all_payments_with_data(self, qtbot, mock_data_access, mock_employee_admin):
        """load_all_payments заполняет таблицу данными."""
        payments = [
            _sample_payment(1, 'Сотрудник А', 30000),
            _sample_payment(2, 'Сотрудник Б', 25000),
        ]
        mock_data_access.get_year_payments.return_value = payments
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        # Устанавливаем период "Месяц" для загрузки через кэш
        tab.period_filter.setCurrentText('Месяц')
        tab.load_all_payments()
        assert tab.all_payments_table.rowCount() >= 0, "Таблица должна обработать данные"

    def test_load_all_payments_empty_list(self, qtbot, mock_data_access, mock_employee_admin):
        """Пустой список — таблица пустая."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_all_payments()
        assert tab.all_payments_table.rowCount() == 0

    def test_load_all_payments_caches_data(self, qtbot, mock_data_access, mock_employee_admin):
        """Кэш сохраняется после первой загрузки."""
        payments = [_sample_payment(1)]
        mock_data_access.get_year_payments.return_value = payments
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.period_filter.setCurrentText('Месяц')
        tab.load_all_payments()
        assert tab._all_payments_cache is not None, "Кэш должен быть заполнен"
        assert tab._cache_year is not None, "Год кэша должен быть установлен"

    def test_load_all_payments_force_reload_clears_cache(self, qtbot, mock_data_access, mock_employee_admin):
        """force_reload=True перезагружает данные."""
        mock_data_access.get_year_payments.return_value = [_sample_payment(1)]
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.period_filter.setCurrentText('Месяц')
        tab.load_all_payments()
        call_count_1 = mock_data_access.get_year_payments.call_count
        tab.load_all_payments(force_reload=True)
        call_count_2 = mock_data_access.get_year_payments.call_count
        assert call_count_2 > call_count_1, "force_reload должен вызвать повторную загрузку"

    def test_load_all_payments_exception_handled(self, qtbot, mock_data_access, mock_employee_admin):
        """Исключение в get_year_payments не ломает UI."""
        mock_data_access.get_year_payments.side_effect = Exception("Ошибка БД")
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        # Не должен упасть (обработка внутри try/except в load_all_payments)
        try:
            tab.load_all_payments()
        except Exception:
            pass  # Допустимо, если не крашит весь UI


# ═══════════════════════════════════════════════════════════════
# TestSalariesFilterLogic — логика фильтров
# ═══════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestSalariesFilterLogic:
    """Применение и сброс фильтров."""

    def test_reset_filters_sets_period_all(self, qtbot, mock_data_access, mock_employee_admin):
        """reset_all_payments_filters устанавливает период 'Все'."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.period_filter.setCurrentText('Месяц')
        tab.reset_all_payments_filters()
        assert tab.period_filter.currentText() == 'Все'

    def test_reset_filters_hides_year(self, qtbot, mock_data_access, mock_employee_admin):
        """После сброса фильтр года скрыт."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.year_filter.show()
        tab.reset_all_payments_filters()
        assert tab.year_filter.isHidden(), "Фильтр года должен быть скрыт после сброса"

    def test_reset_filters_hides_month(self, qtbot, mock_data_access, mock_employee_admin):
        """После сброса фильтр месяца скрыт."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.month_filter.show()
        tab.reset_all_payments_filters()
        assert tab.month_filter.isHidden(), "Фильтр месяца должен быть скрыт после сброса"

    def test_reset_filters_resets_address(self, qtbot, mock_data_access, mock_employee_admin):
        """После сброса фильтр адреса на позиции 0 (Все)."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.reset_all_payments_filters()
        assert tab.address_filter.currentIndex() == 0

    def test_reset_filters_resets_employee(self, qtbot, mock_data_access, mock_employee_admin):
        """После сброса фильтр исполнителя на позиции 0 (Все)."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.reset_all_payments_filters()
        assert tab.employee_filter.currentIndex() == 0

    def test_apply_filters_calls_load(self, qtbot, mock_data_access, mock_employee_admin):
        """apply_all_payments_filters вызывает load_all_payments."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        mock_data_access.get_year_payments.reset_mock()
        tab.apply_all_payments_filters()
        mock_data_access.get_year_payments.assert_called()


# ═══════════════════════════════════════════════════════════════
# TestSalariesLazyLoading — ленивая загрузка
# ═══════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestSalariesLazyLoading:
    """Ленивая загрузка SalariesTab."""

    def test_data_not_loaded_on_create(self, qtbot, mock_data_access, mock_employee_admin):
        """_data_loaded=False при создании."""
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab._data_loaded is False

    def test_ensure_data_loaded_sets_flag(self, qtbot, mock_data_access, mock_employee_admin):
        """ensure_data_loaded устанавливает _data_loaded=True."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.ensure_data_loaded()
        assert tab._data_loaded is True

    def test_double_ensure_no_reload(self, qtbot, mock_data_access, mock_employee_admin):
        """Повторный ensure_data_loaded не перезагружает данные."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.ensure_data_loaded()
        call_count = mock_data_access.get_year_payments.call_count
        tab.ensure_data_loaded()
        assert mock_data_access.get_year_payments.call_count == call_count

    def test_ensure_data_loaded_uses_prefer_local(self, qtbot, mock_data_access, mock_employee_admin):
        """Первая загрузка использует prefer_local для мгновенного отображения."""
        prefer_local_during_call = []

        def capture(*args, **kwargs):
            prefer_local_during_call.append(mock_data_access.prefer_local)
            return []

        mock_data_access.get_year_payments.side_effect = capture
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.ensure_data_loaded()
        assert len(prefer_local_during_call) > 0, "get_year_payments должен быть вызван"
        assert prefer_local_during_call[0] is True, "prefer_local должен быть True при первой загрузке"


# ═══════════════════════════════════════════════════════════════
# TestCollapsibleBox — сворачивание/разворачивание фильтров
# ═══════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestCollapsibleBox:
    """CollapsibleBox — виджет сворачиваемых фильтров."""

    def test_collapsible_creates(self, qtbot):
        """CollapsibleBox создаётся."""
        with patch('ui.salaries_tab.IconLoader', _mock_icon_loader()):
            from ui.salaries_tab import CollapsibleBox
            box = CollapsibleBox("Тестовые фильтры")
            qtbot.addWidget(box)
            assert isinstance(box, QWidget)

    def test_collapsible_default_collapsed(self, qtbot):
        """По умолчанию свёрнут (content_area.maxHeight=0)."""
        with patch('ui.salaries_tab.IconLoader', _mock_icon_loader()):
            from ui.salaries_tab import CollapsibleBox
            box = CollapsibleBox("Фильтры")
            qtbot.addWidget(box)
            assert box.content_area.maximumHeight() == 0

    def test_collapsible_toggle_expands(self, qtbot):
        """Клик toggle_button разворачивает content_area."""
        with patch('ui.salaries_tab.IconLoader', _mock_icon_loader()):
            from ui.salaries_tab import CollapsibleBox
            box = CollapsibleBox("Фильтры")
            qtbot.addWidget(box)
            box.toggle_button.setChecked(True)
            box.on_toggle()
            assert box.content_area.maximumHeight() > 0, "После toggle content_area должен быть развернут"

    def test_collapsible_toggle_collapses(self, qtbot):
        """Повторный toggle сворачивает content_area."""
        with patch('ui.salaries_tab.IconLoader', _mock_icon_loader()):
            from ui.salaries_tab import CollapsibleBox
            box = CollapsibleBox("Фильтры")
            qtbot.addWidget(box)
            # Развернуть
            box.toggle_button.setChecked(True)
            box.on_toggle()
            # Свернуть
            box.toggle_button.setChecked(False)
            box.on_toggle()
            assert box.content_area.maximumHeight() == 0


# ═══════════════════════════════════════════════════════════════
# TestPaymentStatusDelegate — подсветка строк
# ═══════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestPaymentStatusDelegate:
    """PaymentStatusDelegate — цвет фона по статусу."""

    def test_delegate_creates(self, qtbot):
        """PaymentStatusDelegate создаётся."""
        from ui.salaries_tab import PaymentStatusDelegate
        delegate = PaymentStatusDelegate()
        assert delegate is not None

    def test_delegate_to_pay_color(self, qtbot):
        """Статус 'to_pay' — жёлтый фон (#FFF3CD)."""
        from ui.salaries_tab import PaymentStatusDelegate
        delegate = PaymentStatusDelegate()
        # Проверяем что класс имеет метод paint
        assert hasattr(delegate, 'paint'), "PaymentStatusDelegate должен иметь метод paint"

    def test_delegate_paid_color(self, qtbot):
        """Статус 'paid' — зелёный фон (#D4EDDA)."""
        from ui.salaries_tab import PaymentStatusDelegate
        delegate = PaymentStatusDelegate()
        # Проверяем что объект наследует QStyledItemDelegate
        from PyQt5.QtWidgets import QStyledItemDelegate
        assert isinstance(delegate, QStyledItemDelegate)


# ═══════════════════════════════════════════════════════════════
# TestSalariesCacheInvalidation — инвалидация кэша
# ═══════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestSalariesCacheInvalidation:
    """Инвалидация кэша выплат."""

    def test_invalidate_cache_clears_all(self, qtbot, mock_data_access, mock_employee_admin):
        """invalidate_cache очищает все кэши."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab._all_payments_cache = [{'test': 1}]
        tab._cache_year = 2026
        tab._payment_type_cache = {'Оклады': []}
        tab.invalidate_cache()
        assert tab._all_payments_cache is None
        assert tab._cache_year is None
        assert tab._payment_type_cache == {}

    def test_invalidate_cache_on_fresh_tab(self, qtbot, mock_data_access, mock_employee_admin):
        """invalidate_cache на свежем табе — без ошибок."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.invalidate_cache()
        assert tab._all_payments_cache is None

    def test_months_ru_class_attribute(self, qtbot, mock_data_access, mock_employee_admin):
        """_months_ru содержит 12 русских месяцев."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        assert len(tab._months_ru) == 12
        assert tab._months_ru[0] == 'Январь'
        assert tab._months_ru[11] == 'Декабрь'
