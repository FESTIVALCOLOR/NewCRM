"""
Anti-pattern тесты: проверяют ОТСУТСТВИЕ запрещённых паттернов в production коде.

Эти тесты читают исходный код и ищут антипаттерны через regex.
Они ловят баги ДО запуска приложения — на уровне статического анализа.
"""

import os
from pathlib import Path
import re

import pytest

UI_DIR = Path(__file__).parent.parent.parent / "ui"
UTILS_DIR = Path(__file__).parent.parent.parent / "utils"

# Известные допустимые исключения (с обоснованием)
ALLOWED_RAW_SQL = {
    # Архивная карточка — read-only, нет API для surveys/stage_executors в архиве
    "crm_archive.py",
    # dashboard/reports — DatabaseManager для DataAccess init, не прямой SQL
    "dashboard_tab.py",
    "employee_reports_tab.py",
}

ALLOWED_DATABASE_MANAGER = {
    # Файлы где DatabaseManager создаётся для передачи в DataAccess (не прямой SQL)
    "dashboard_tab.py",
    "employee_reports_tab.py",
    "login_window.py",
    "main_window.py",
    "rates_dialog.py",  # создаёт для DataAccess
    "salaries_tab.py",  # создаёт для DataAccess
    # Tech debt: DatabaseManager в фоновых потоках для READ-fallback (файлы стадий)
    "crm_card_edit_dialog.py",  # validate_stage_files, project_history (READ-only)
    "supervision_card_edit_dialog.py",  # validate_stage_files (READ-only)
}

ALLOWED_RAW_UPDATE = {
    # Tech debt: execute_raw_update для кэш-поля public_link (низкий импакт)
    "supervision_card_edit_dialog.py",
}


def _get_ui_files():
    """Получить все .py файлы из ui/"""
    return sorted(f for f in UI_DIR.glob("*.py") if not f.name.startswith("__"))


def _get_ui_files_excluding(*allowlists):
    """Получить UI файлы, исключая файлы из указанных allowlist-ов."""
    excluded = set()
    for al in allowlists:
        excluded |= al
    return sorted(f for f in UI_DIR.glob("*.py") if not f.name.startswith("__") and f.name not in excluded)


def _read_file(path):
    return path.read_text(encoding="utf-8", errors="ignore")


class TestNoDirectSQLWrites:
    """UI файлы не должны содержать прямые SQL WRITE операции."""

    @pytest.mark.parametrize("ui_file", _get_ui_files_excluding(ALLOWED_RAW_SQL), ids=lambda f: f.name)
    def test_no_cursor_execute_write(self, ui_file):
        """cursor.execute() с UPDATE/INSERT/DELETE запрещён в UI."""

        content = _read_file(ui_file)
        lines = content.split("\n")

        violations = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            if "cursor.execute" not in line:
                continue
            # Смотрим SQL-запрос в ±3 строках
            context = "\n".join(lines[max(0, i - 2) : min(len(lines), i + 3)])
            if re.search(r"(?i)(UPDATE|INSERT|DELETE)\s", context):
                violations.append(f"  строка {i}: {stripped[:100]}")

        assert not violations, f"{ui_file.name} содержит прямые SQL WRITE операции:\n" + "\n".join(violations) + "\n\nИспользуйте self.data.update_*/create_*/delete_* (DataAccess)"

    @pytest.mark.parametrize("ui_file", _get_ui_files_excluding(ALLOWED_RAW_SQL, ALLOWED_RAW_UPDATE), ids=lambda f: f.name)
    def test_no_execute_raw_update(self, ui_file):
        """execute_raw_update() запрещён в UI — используйте DataAccess."""

        content = _read_file(ui_file)
        lines = content.split("\n")

        violations = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "execute_raw_update(" in line:
                violations.append(f"  строка {i}: {stripped[:100]}")

        assert not violations, f"{ui_file.name} содержит execute_raw_update():\n" + "\n".join(violations) + "\n\nИспользуйте self.data.update_*/create_*/delete_* (DataAccess)"


class TestNoForbiddenPatterns:
    """Запрещённые паттерны в UI коде."""

    @pytest.mark.parametrize("ui_file", _get_ui_files(), ids=lambda f: f.name)
    def test_no_custom_message_box_question(self, ui_file):
        """CustomMessageBox не должен использоваться с типом 'question'.
        Для подтверждений используйте CustomQuestionBox."""
        content = _read_file(ui_file)
        lines = content.split("\n")

        violations = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "CustomMessageBox" in line and "'question'" in line:
                violations.append(f"  строка {i}: {stripped[:100]}")

        assert not violations, f"{ui_file.name} использует CustomMessageBox с типом question:\n" + "\n".join(violations) + "\n\nИспользуйте CustomQuestionBox для подтверждений (Yes/No)"

    @pytest.mark.parametrize("ui_file", _get_ui_files(), ids=lambda f: f.name)
    def test_no_qmessagebox_yes_comparison(self, ui_file):
        """Сравнение с QMessageBox.Yes (16384) запрещено.
        CustomQuestionBox возвращает QDialog.Accepted (1)."""
        content = _read_file(ui_file)
        lines = content.split("\n")

        violations = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#") or "import" in stripped:
                continue
            if "QMessageBox.Yes" in line or "QMessageBox.No" in line:
                violations.append(f"  строка {i}: {stripped[:100]}")

        assert not violations, f"{ui_file.name} сравнивает с QMessageBox.Yes/No:\n" + "\n".join(violations) + "\n\nИспользуйте reply.exec_() == QDialog.Accepted"

    @pytest.mark.parametrize("ui_file", _get_ui_files(), ids=lambda f: f.name)
    def test_no_fstring_sql(self, ui_file):
        """f-string SQL запросы запрещены — SQL injection."""
        content = _read_file(ui_file)
        lines = content.split("\n")
        pattern = re.compile(r"""f['"].*?(UPDATE|INSERT|DELETE)\s.*?\{""")

        violations = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if pattern.search(line):
                violations.append(f"  строка {i}: {stripped[:100]}")

        assert not violations, f"{ui_file.name} содержит f-string SQL:\n" + "\n".join(violations) + "\n\nИспользуйте параметризованные запросы (?, %s)"


class TestSignalSafety:
    """Проверки безопасности Qt сигналов."""

    @pytest.mark.parametrize("ui_file", _get_ui_files(), ids=lambda f: f.name)
    def test_no_unguarded_connect_in_show_event(self, ui_file):
        """.connect() внутри showEvent должен иметь guard (_signals_connected)."""
        content = _read_file(ui_file)
        lines = content.split("\n")

        in_show_event = False
        show_indent = 0
        violations = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            if "def showEvent" in line:
                in_show_event = True
                show_indent = len(line) - len(line.lstrip())
                continue

            if in_show_event:
                if stripped and not stripped.startswith("#"):
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent <= show_indent and stripped.startswith("def "):
                        in_show_event = False
                        continue

                if ".connect(" in line and "_signals_connected" not in line and "_centered" not in line:
                    # Проверяем guard в ±5 строках выше
                    has_guard = False
                    for j in range(max(0, i - 6), i - 1):
                        if "_signals_connected" in lines[j] or "_connected" in lines[j]:
                            has_guard = True
                            break
                    if not has_guard:
                        violations.append(f"  строка {i}: {stripped[:100]}")

        assert not violations, f"{ui_file.name} имеет .connect() в showEvent без guard:\n" + "\n".join(violations) + '\n\nДобавьте: if not hasattr(self, "_signals_connected"): ...'


class TestDatabaseManagerInUI:
    """DatabaseManager() не должен создаваться в UI для прямого SQL."""

    @pytest.mark.parametrize("ui_file", _get_ui_files_excluding(ALLOWED_DATABASE_MANAGER), ids=lambda f: f.name)
    def test_no_new_database_manager_for_sql(self, ui_file):
        """DatabaseManager() в UI допустим только для передачи в DataAccess."""

        content = _read_file(ui_file)
        lines = content.split("\n")

        violations = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("from") or stripped.startswith("import"):
                continue
            if "DatabaseManager()" in line:
                violations.append(f"  строка {i}: {stripped[:100]}")

        assert not violations, f"{ui_file.name} создаёт DatabaseManager() напрямую:\n" + "\n".join(violations) + "\n\nИспользуйте self.data (DataAccess) для всех операций с БД"
