# -*- coding: utf-8 -*-
import sys
import os
import ctypes

# Принудительная UTF-8 кодировка для вывода (Windows charmap fix)
# PyInstaller windowed (console=False) может иметь stdout=None
for _stream_name in ('stdout', 'stderr'):
    _stream = getattr(sys, _stream_name, None)
    if _stream is None:
        # PyInstaller windowed: перенаправляем в devnull чтобы print() не падал
        setattr(sys, _stream_name, open(os.devnull, 'w', encoding='utf-8'))
    elif hasattr(_stream, 'reconfigure'):
        try:
            _stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

# Включаем вывод Python traceback при segfault (SIGSEGV)
# Вызываем ПОСЛЕ починки stderr (в windowed PyInstaller stderr=None)
import faulthandler
try:
    faulthandler.enable()
except Exception:
    pass
from PyQt5.QtWidgets import QApplication, QComboBox, QMenu, QWidget
from PyQt5.QtCore import Qt, QObject, QEvent, QSize
from PyQt5.QtGui import QIcon, QFont, QFontDatabase
from ui.login_window import LoginWindow
from database.db_manager import DatabaseManager

# ========== ЛОГИРОВАНИЕ ==========
from utils.logger import app_logger, log_error
# =================================

# ========== ФУНКЦИЯ ДЛЯ ОПРЕДЕЛЕНИЯ ПУТИ К РЕСУРСАМ ==========
from utils.resource_path import resource_path
# ==============================================================


class PopupStyleFilter(QObject):
    """
    Глобальный фильтр событий:
    1. Отключает прокрутку QComboBox без фокуса
    2. Скруглённые углы через DWM API (Windows 11+)
    3. Лёгкая нативная тень DWM вместо тёмной CS_DROPSHADOW
    """

    def eventFilter(self, obj, event):
        if not isinstance(obj, QWidget):
            return False

        etype = event.type()

        # Отключение прокрутки QComboBox без фокуса
        if isinstance(obj, QComboBox) and etype == QEvent.Wheel:
            if not obj.hasFocus():
                event.ignore()
                return True

        # Подготовка popup QComboBox: убрать тень ДО показа
        if isinstance(obj, QComboBox) and etype == QEvent.MouseButtonPress:
            self._remove_combo_shadow(obj)

        # Все popup окна: DWM скругление + удаление тёмной тени
        # ВАЖНО: используем WindowType_Mask для точного сравнения типа окна,
        # т.к. Qt.Popup (0x09) включает бит Qt.Window (0x01) и простая
        # проверка flags & Qt.Popup сработает на ЛЮБОЕ окно (Dialog, ToolTip и т.д.)
        if etype == QEvent.Show and isinstance(obj, QWidget) and obj.isWindow():
            wtype = int(obj.windowFlags()) & int(Qt.WindowType_Mask)
            if wtype == int(Qt.Popup):
                self._style_popup(obj)

        return False

    def _remove_combo_shadow(self, combo):
        """Убрать CS_DROPSHADOW у popup QComboBox до его показа"""
        try:
            view = combo.view()
            if not view:
                return
            popup = view.window()
            if not popup or popup is combo.window():
                return
            if not popup.property('_shadow_removed'):
                popup.setProperty('_shadow_removed', True)
                popup.setWindowFlag(Qt.NoDropShadowWindowHint, True)
        except Exception:
            pass

    def _style_popup(self, widget):
        """Скруглённые углы (DWM) + лёгкая тень для popup"""
        # Удалить тёмную тень CS_DROPSHADOW (один раз на виджет)
        if not widget.property('_shadow_removed'):
            widget.setProperty('_shadow_removed', True)
            try:
                geo = widget.geometry()
                widget.setWindowFlag(Qt.NoDropShadowWindowHint, True)
                widget.setGeometry(geo)
                widget.show()
            except Exception:
                pass
        # DWM скруглённые углы (каждый Show — HWND мог смениться)
        self._apply_dwm_corners(widget)

    @staticmethod
    def _apply_dwm_corners(widget):
        """Скруглённые углы через DWM API (Windows 11+)"""
        if sys.platform != 'win32':
            return
        try:
            hwnd = int(widget.winId())
            # DWMWA_WINDOW_CORNER_PREFERENCE = 33, DWMWCP_ROUND = 2
            value = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 33, ctypes.byref(value), ctypes.sizeof(value))
        except Exception:
            pass

def main():
    try:
        app_logger.info("="*60)
        app_logger.info("ЗАПУСК ПРИЛОЖЕНИЯ INTERIOR STUDIO CRM")
        app_logger.info("="*60)

        # ========== FIX для High DPI экранов ==========
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        # Рендеринг: Qt автоматически выбирает лучший бэкенд (Software/ANGLE/Desktop)
        # НЕ форсируем AA_UseDesktopOpenGL — может вызвать createDIB failed на встроенных GPU
        # ==============================================

        # ========== ИСПРАВЛЕНИЕ ИКОНКИ В ПАНЕЛИ ЗАДАЧ WINDOWS ==========
        # Устанавливаем App User Model ID для корректного отображения иконки в панели задач
        if sys.platform == 'win32':
            try:
                myappid = 'interiorstudio.crm.app.1.0'  # Уникальный ID приложения
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                app_logger.info("Установлен App User Model ID для Windows")
            except Exception as e:
                app_logger.warning(f"Не удалось установить App User Model ID: {e}")
        # ================================================================

        # Инициализация приложения
        app = QApplication(sys.argv)

        # Устанавливаем иконку приложения
        # ИСПРАВЛЕНИЕ 07.02.2026: Добавляем несколько размеров для корректного отображения в панели задач
        app_icon = QIcon()
        # Добавляем разные размеры иконки (от малого к большому)
        for size in [32, 48, 64, 128, 256]:
            icon_path = resource_path(f'resources/icon{size}.ico')
            if os.path.exists(icon_path):
                app_icon.addFile(icon_path, QSize(size, size))
        # Fallback на основную иконку если отдельных нет
        if app_icon.isNull():
            app_icon = QIcon(resource_path('resources/icon.ico'))
        app.setWindowIcon(app_icon)

        # Глобальный фильтр: QComboBox прокрутка + popup скругления + тень
        popup_filter = PopupStyleFilter(app)
        app.installEventFilter(popup_filter)
        app_logger.info("Установлен глобальный фильтр PopupStyleFilter")

        # Monkeypatch QMenu: убрать тёмную системную тень
        _orig_menu_popup = QMenu.popup
        _orig_menu_exec = QMenu.exec_

        def _menu_popup_no_shadow(self, *args, **kwargs):
            if not self.property('_shadow_removed'):
                self.setProperty('_shadow_removed', True)
                self.setWindowFlag(Qt.NoDropShadowWindowHint, True)
            return _orig_menu_popup(self, *args, **kwargs)

        def _menu_exec_no_shadow(self, *args, **kwargs):
            if not self.property('_shadow_removed'):
                self.setProperty('_shadow_removed', True)
                self.setWindowFlag(Qt.NoDropShadowWindowHint, True)
            return _orig_menu_exec(self, *args, **kwargs)

        QMenu.popup = _menu_popup_no_shadow
        QMenu.exec_ = _menu_exec_no_shadow
        app_logger.info("QMenu monkeypatch: NoDropShadowWindowHint")

        # Применяем стандартный стиль Fusion
        app.setStyle('Fusion')

        # Устанавливаем палитру для tooltip
        from PyQt5.QtGui import QPalette, QColor
        palette = app.palette()
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
        app.setPalette(palette)

        app_logger.info("Qt Application инициализировано")

        # ========== ЗАГРУЗКА ШРИФТА MANROPE ==========
        fonts_dir = resource_path('resources/fonts')
        manrope_loaded = False
        if os.path.exists(fonts_dir):
            for font_file in ['Manrope-Regular.ttf', 'Manrope-Medium.ttf',
                               'Manrope-SemiBold.ttf', 'Manrope-Bold.ttf',
                               'Manrope-ExtraBold.ttf']:
                font_path = os.path.join(fonts_dir, font_file)
                if os.path.exists(font_path):
                    font_id = QFontDatabase.addApplicationFont(font_path)
                    if font_id >= 0:
                        manrope_loaded = True
                        app_logger.debug(f"Шрифт загружен: {font_file}")
                    else:
                        app_logger.warning(f"Не удалось загрузить шрифт: {font_file}")

        if manrope_loaded:
            app_logger.info("Шрифт Manrope успешно загружен")
        else:
            app_logger.warning("Шрифт Manrope не найден, используется системный шрифт")
        # ==================================================

        # ========== ПРИМЕНЕНИЕ ЕДИНЫХ СТИЛЕЙ ==========
        from utils.unified_styles import get_unified_stylesheet

        # Скрываем стандартный QToolTip (заменён на BubbleToolTip)
        tooltip_override = """
        QToolTip {
            background-color: transparent;
            color: transparent;
            border: none;
            padding: 0px;
            font-size: 1px;
        }
        """
        combined_styles = get_unified_stylesheet() + "\n" + tooltip_override
        app.setStyleSheet(combined_styles)

        # Глобальная палитра для QToolTip (fallback)
        from PyQt5.QtGui import QPalette, QColor
        palette = app.palette()
        palette.setColor(QPalette.ToolTipBase, QColor('#FFFFFF'))
        palette.setColor(QPalette.ToolTipText, QColor('#000000'))
        app.setPalette(palette)

        # Устанавливаем кастомный tooltip-облачко с хвостиком
        from ui.bubble_tooltip import ToolTipFilter
        tooltip_filter = ToolTipFilter(app)
        app.installEventFilter(tooltip_filter)
        app_logger.info("BubbleToolTip (облачко с хвостиком) установлен")

        app_logger.info("Единые стили (unified_styles.py) применены")
        # ==================================================

        # Инициализация базы данных + окно логина
        # DatabaseManager.__init__ выполняет initialize_database() + run_migrations()
        # Оптимизация: все миграции на одном соединении (вместо 40+ open/close)
        app_logger.info("Инициализация базы данных...")
        import time as _perf_time
        _t0 = _perf_time.perf_counter()
        _db_init = DatabaseManager()  # Только миграции, не сохраняем — LoginWindow создаст свой
        _dt = (_perf_time.perf_counter() - _t0) * 1000
        app_logger.info(f"База данных инициализирована за {_dt:.0f}ms")

        # Запуск окна входа
        app_logger.info("Запуск окна входа в систему")
        login_window = LoginWindow()
        login_window.show()

        app_logger.info("Приложение запущено успешно")
        app_logger.info("="*60)

        sys.exit(app.exec_())

    except Exception as e:
        log_error(e, context="Запуск приложения")
        print(f"\n[CRITICAL ERROR] Критическая ошибка при запуске: {e}")
        print("Подробности в файле logs/crm_errors.log")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
