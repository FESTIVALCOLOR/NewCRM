# -*- coding: utf-8 -*-
import sys
import os
from PyQt5.QtWidgets import QApplication, QComboBox
from PyQt5.QtCore import Qt, QObject, QEvent
from PyQt5.QtGui import QIcon
from ui.login_window import LoginWindow
from database.db_manager import DatabaseManager

# ========== ЛОГИРОВАНИЕ ==========
from utils.logger import app_logger, log_error
# =================================

# ========== ФУНКЦИЯ ДЛЯ ОПРЕДЕЛЕНИЯ ПУТИ К РЕСУРСАМ ==========
from utils.resource_path import resource_path
# ==============================================================


class ComboBoxEventFilter(QObject):
    """
    Глобальный фильтр событий для всех QComboBox.
    Отключает изменение значения при прокрутке колесиком мыши,
    если ComboBox не в фокусе.
    """

    def eventFilter(self, obj, event):
        if isinstance(obj, QComboBox) and event.type() == QEvent.Wheel:
            # Если ComboBox не в фокусе, игнорируем событие колесика
            if not obj.hasFocus():
                event.ignore()
                return True
        return super().eventFilter(obj, event)

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
        # Включаем поддержку композитинга для tooltip поверх полупрозрачных окон
        if hasattr(Qt, 'AA_UseDesktopOpenGL'):
            QApplication.setAttribute(Qt.AA_UseDesktopOpenGL, True)
        # ==============================================

        # Инициализация приложения
        app = QApplication(sys.argv)

        # Устанавливаем иконку приложения
        app_icon = QIcon(resource_path('resources/icon.ico'))
        app.setWindowIcon(app_icon)

        # Устанавливаем глобальный фильтр событий для всех QComboBox
        combo_filter = ComboBoxEventFilter(app)
        app.installEventFilter(combo_filter)
        app_logger.info("Установлен глобальный фильтр для QComboBox (отключение прокрутки без фокуса)")

        # Применяем стандартный стиль Fusion
        app.setStyle('Fusion')

        # Устанавливаем палитру для tooltip
        from PyQt5.QtGui import QPalette, QColor
        palette = app.palette()
        palette.setColor(QPalette.ToolTipBase, QColor(245, 245, 245))
        palette.setColor(QPalette.ToolTipText, QColor(51, 51, 51))
        app.setPalette(palette)

        app_logger.info("Qt Application инициализировано")

        # ========== ОТЛАДКА ПУТЕЙ ==========
        print("\n" + "="*60)
        print("ОТЛАДКА ПУТЕЙ К РЕСУРСАМ")
        print("="*60)

        if getattr(sys, 'frozen', False):
            app_root = os.path.dirname(sys.executable)
        else:
            app_root = os.path.dirname(os.path.abspath(__file__))

        print(f"Корень приложения: {app_root}")
        app_logger.debug(f"Корень приложения: {app_root}")

        icons_path = resource_path('resources/icons')
        print(f"Путь к иконкам: {icons_path}")
        print(f"Папка существует: {os.path.exists(icons_path)}")

        required_icons = [
            'arrow-down-circle.svg',
            'arrow-up-circle.svg',
            'arrow-left-circle.svg',
            'arrow-right-circle.svg'
        ]

        print("\nПроверка SVG файлов:")
        missing_icons = []
        for icon in required_icons:
            full_path = os.path.join(icons_path, icon)
            exists = os.path.exists(full_path)
            status = "[OK]" if exists else "[MISS]"
            print(f"  {status} {icon}")
            if not exists:
                print(f"      Ожидаемый путь: {full_path}")
                missing_icons.append(icon)

        if missing_icons:
            app_logger.warning(f"Отсутствуют иконки: {', '.join(missing_icons)}")

        print("="*60 + "\n")
        # ===================================
    
        # ========== ПРИМЕНЕНИЕ ГЛОБАЛЬНЫХ СТИЛЕЙ ==========
        base_styles = ""
        try:
            styles_path = resource_path('resources/styles.qss')
            with open(styles_path, 'r', encoding='utf-8') as f:
                base_styles = f.read()
            app_logger.info(f"Стили загружены из {styles_path}")
        except FileNotFoundError:
            print(f"[WARN] Файл resources/styles.qss не найден")
            app_logger.warning(f"Файл resources/styles.qss не найден")

        from utils.calendar_styles import CALENDAR_STYLE
        from utils.global_styles import GLOBAL_STYLE

        # Добавляем принудительный стиль для QToolTip в самом конце
        tooltip_override = """
        QToolTip {
            background-color: rgb(245, 245, 245);
            color: rgb(51, 51, 51);
            border: 1px solid rgb(204, 204, 204);
            border-radius: 4px;
            padding: 5px;
            font-size: 12px;
        }
        """
        combined_styles = base_styles + "\n" + CALENDAR_STYLE + "\n" + GLOBAL_STYLE + "\n" + tooltip_override
        app.setStyleSheet(combined_styles)
        app_logger.info("Глобальные стили применены")
        # ==================================================

        # Инициализация базы данных
        app_logger.info("Инициализация базы данных...")
        db = DatabaseManager()
        db.initialize_database()
        app_logger.info("База данных успешно инициализирована")

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
