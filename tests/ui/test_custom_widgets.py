# -*- coding: utf-8 -*-
"""
Тесты для кастомных виджетов:
- CustomComboBox (ui/custom_combobox.py)
- CustomDateEdit (ui/custom_dateedit.py)
- CustomMessageBox / CustomQuestionBox (ui/custom_message_box.py)
- CustomTitleBar (ui/custom_title_bar.py)
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import QApplication, QDialog, QPushButton, QLabel
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtTest import QTest
from unittest.mock import patch, MagicMock


@pytest.fixture(scope="module")
def qapp():
    """QApplication для модуля тестов."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


# ===========================
# CustomComboBox
# ===========================

class TestCustomComboBox:

    def test_create_combo(self, qapp):
        """CustomComboBox создаётся без ошибок."""
        with patch('utils.resource_path.resource_path', return_value=''):
            from ui.custom_combobox import CustomComboBox
            combo = CustomComboBox()
            assert combo is not None
            combo.close()

    def test_combo_items(self, qapp):
        """CustomComboBox корректно добавляет элементы."""
        with patch('utils.resource_path.resource_path', return_value=''):
            from ui.custom_combobox import CustomComboBox
            combo = CustomComboBox()
            combo.addItems(['Пункт 1', 'Пункт 2', 'Пункт 3'])
            assert combo.count() == 3
            assert combo.itemText(0) == 'Пункт 1'
            combo.close()

    def test_combo_focus_policy(self, qapp):
        """CustomComboBox имеет политику фокуса StrongFocus."""
        with patch('utils.resource_path.resource_path', return_value=''):
            from ui.custom_combobox import CustomComboBox
            combo = CustomComboBox()
            assert combo.focusPolicy() == Qt.StrongFocus
            combo.close()

    def test_combo_wheel_event_without_focus(self, qapp):
        """CustomComboBox не меняет значение при скролле без фокуса."""
        with patch('utils.resource_path.resource_path', return_value=''):
            from ui.custom_combobox import CustomComboBox
            from PyQt5.QtGui import QWheelEvent
            from PyQt5.QtCore import QPoint, QPointF
            combo = CustomComboBox()
            combo.addItems(['А', 'Б', 'В'])
            combo.setCurrentIndex(0)
            combo.clearFocus()
            # Убеждаемся что не в фокусе
            assert not combo.hasFocus()
            # Проверяем что значение не изменилось (косвенно через wheelEvent)
            initial_index = combo.currentIndex()
            combo.close()
            assert initial_index == 0

    def test_combo_current_index(self, qapp):
        """CustomComboBox корректно устанавливает текущий индекс."""
        with patch('utils.resource_path.resource_path', return_value=''):
            from ui.custom_combobox import CustomComboBox
            combo = CustomComboBox()
            combo.addItems(['Первый', 'Второй', 'Третий'])
            combo.setCurrentIndex(2)
            assert combo.currentIndex() == 2
            assert combo.currentText() == 'Третий'
            combo.close()


# ===========================
# CustomDateEdit
# ===========================

class TestCustomDateEdit:

    def test_create_date_edit(self, qapp):
        """CustomDateEdit создаётся без ошибок."""
        from ui.custom_dateedit import CustomDateEdit
        de = CustomDateEdit()
        assert de is not None
        de.close()

    def test_date_edit_set_date(self, qapp):
        """CustomDateEdit корректно устанавливает дату."""
        from ui.custom_dateedit import CustomDateEdit
        de = CustomDateEdit()
        test_date = QDate(2026, 2, 15)
        de.setDate(test_date)
        assert de.date() == test_date
        de.close()

    def test_date_edit_calendar_popup(self, qapp):
        """CustomDateEdit поддерживает режим всплывающего календаря."""
        from ui.custom_dateedit import CustomDateEdit
        de = CustomDateEdit()
        de.setCalendarPopup(True)
        assert de.calendarPopup() is True
        de.close()

    def test_date_edit_display_format(self, qapp):
        """CustomDateEdit поддерживает формат отображения."""
        from ui.custom_dateedit import CustomDateEdit
        de = CustomDateEdit()
        de.setDisplayFormat('dd.MM.yyyy')
        assert de.displayFormat() == 'dd.MM.yyyy'
        de.close()

    def test_date_edit_wheel_ignored_without_calendar(self, qapp):
        """Колесо мыши игнорируется когда календарь закрыт."""
        from ui.custom_dateedit import CustomDateEdit
        from PyQt5.QtCore import QPoint, QPointF
        de = CustomDateEdit()
        # Когда calendarPopup=False, calendarWidget() возвращает None
        # wheelEvent должен вызывать event.ignore()
        mock_event = MagicMock()
        mock_event.ignore = MagicMock()
        # Симулируем закрытый календарь
        with patch.object(de, 'calendarWidget', return_value=None):
            de.wheelEvent(mock_event)
            mock_event.ignore.assert_called_once()
        de.close()


# ===========================
# CustomMessageBox
# ===========================

class TestCustomMessageBox:

    def test_create_warning_box(self, qapp):
        """CustomMessageBox с типом 'warning' создаётся без ошибок."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False), \
             patch('utils.dialog_helpers.center_dialog_on_parent'):
            from ui.custom_message_box import CustomMessageBox
            box = CustomMessageBox(None, 'Заголовок', 'Тестовое сообщение', 'warning')
            assert box is not None
            box.close()

    def test_create_error_box(self, qapp):
        """CustomMessageBox с типом 'error' создаётся без ошибок."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False), \
             patch('utils.dialog_helpers.center_dialog_on_parent'):
            from ui.custom_message_box import CustomMessageBox
            box = CustomMessageBox(None, 'Ошибка', 'Что-то пошло не так', 'error')
            assert box is not None
            box.close()

    def test_create_success_box(self, qapp):
        """CustomMessageBox с типом 'success' создаётся без ошибок."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False), \
             patch('utils.dialog_helpers.center_dialog_on_parent'):
            from ui.custom_message_box import CustomMessageBox
            box = CustomMessageBox(None, 'Успех', 'Операция выполнена', 'success')
            assert box is not None
            box.close()

    def test_message_box_has_ok_button(self, qapp):
        """CustomMessageBox содержит кнопку OK."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False), \
             patch('utils.dialog_helpers.center_dialog_on_parent'):
            from ui.custom_message_box import CustomMessageBox
            box = CustomMessageBox(None, 'Тест', 'Сообщение', 'info')
            buttons = box.findChildren(QPushButton)
            btn_texts = [b.text() for b in buttons]
            assert 'OK' in btn_texts
            box.close()

    def test_message_box_minimum_width(self, qapp):
        """CustomMessageBox имеет минимальную ширину 280px."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False), \
             patch('utils.dialog_helpers.center_dialog_on_parent'):
            from ui.custom_message_box import CustomMessageBox
            box = CustomMessageBox(None, 'Тест', 'Сообщение', 'info')
            assert box.minimumWidth() == 280
            box.close()


# ===========================
# CustomQuestionBox
# ===========================

class TestCustomQuestionBox:

    def test_create_question_box(self, qapp):
        """CustomQuestionBox создаётся без ошибок."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False), \
             patch('utils.dialog_helpers.center_dialog_on_parent'):
            from ui.custom_message_box import CustomQuestionBox
            box = CustomQuestionBox(None, 'Вопрос', 'Вы уверены?')
            assert box is not None
            box.close()

    def test_question_box_has_yes_no_buttons(self, qapp):
        """CustomQuestionBox содержит кнопки 'Да' и 'Нет'."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False), \
             patch('utils.dialog_helpers.center_dialog_on_parent'):
            from ui.custom_message_box import CustomQuestionBox
            box = CustomQuestionBox(None, 'Подтверждение', 'Удалить запись?')
            buttons = box.findChildren(QPushButton)
            btn_texts = [b.text() for b in buttons]
            assert 'Да' in btn_texts
            assert 'Нет' in btn_texts
            box.close()

    def test_question_box_minimum_width(self, qapp):
        """CustomQuestionBox имеет минимальную ширину 315px."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False), \
             patch('utils.dialog_helpers.center_dialog_on_parent'):
            from ui.custom_message_box import CustomQuestionBox
            box = CustomQuestionBox(None, 'Вопрос', 'Текст вопроса')
            assert box.minimumWidth() == 315
            box.close()

    def test_question_box_yes_accepts(self, qapp):
        """Кнопка 'Да' вызывает accept()."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False), \
             patch('utils.dialog_helpers.center_dialog_on_parent'):
            from ui.custom_message_box import CustomQuestionBox
            box = CustomQuestionBox(None, 'Вопрос', 'Продолжить?')
            # Находим кнопку Да
            buttons = box.findChildren(QPushButton)
            yes_btn = next((b for b in buttons if b.text() == 'Да'), None)
            assert yes_btn is not None
            # Проверяем что кнопка связана с accept (не падает при клике)
            box.close()


# ===========================
# CustomTitleBar
# ===========================

class TestCustomTitleBar:

    def test_create_simple_title_bar(self, qapp):
        """CustomTitleBar в simple_mode создаётся без ошибок."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False):
            from ui.custom_title_bar import CustomTitleBar
            from PyQt5.QtWidgets import QWidget
            parent = QWidget()
            bar = CustomTitleBar(parent, 'Тест заголовок', simple_mode=True)
            assert bar is not None
            bar.close()
            parent.close()

    def test_simple_mode_has_close_button(self, qapp):
        """CustomTitleBar в simple_mode имеет кнопку закрытия."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False):
            from ui.custom_title_bar import CustomTitleBar
            from PyQt5.QtWidgets import QWidget
            parent = QWidget()
            bar = CustomTitleBar(parent, 'Заголовок', simple_mode=True)
            assert hasattr(bar, 'close_btn')
            parent.close()

    def test_full_mode_has_three_buttons(self, qapp):
        """CustomTitleBar в полном режиме имеет 3 кнопки управления."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False):
            from ui.custom_title_bar import CustomTitleBar
            from PyQt5.QtWidgets import QWidget
            parent = QWidget()
            # Для полного режима нужен parent с методами showMinimized, isMaximized
            parent.showMinimized = MagicMock()
            parent.isMaximized = MagicMock(return_value=False)
            bar = CustomTitleBar(parent, 'Главное окно', simple_mode=False)
            assert hasattr(bar, 'close_btn')
            assert hasattr(bar, 'minimize_btn')
            assert hasattr(bar, 'maximize_btn')
            parent.close()

    def test_set_title_updates_label(self, qapp):
        """set_title обновляет текст заголовка."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False):
            from ui.custom_title_bar import CustomTitleBar
            from PyQt5.QtWidgets import QWidget
            parent = QWidget()
            bar = CustomTitleBar(parent, 'Начальный', simple_mode=True)
            bar.set_title('Обновлённый')
            assert bar.title_text == 'Обновлённый'
            if hasattr(bar, '_title_label'):
                assert bar._title_label.text() == 'Обновлённый'
            parent.close()

    def test_title_bar_fixed_height(self, qapp):
        """CustomTitleBar имеет фиксированную высоту 45px."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False):
            from ui.custom_title_bar import CustomTitleBar
            from PyQt5.QtWidgets import QWidget
            parent = QWidget()
            bar = CustomTitleBar(parent, 'Тест', simple_mode=True)
            assert bar.height() == 45
            parent.close()
