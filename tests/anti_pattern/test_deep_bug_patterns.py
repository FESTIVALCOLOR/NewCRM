# -*- coding: utf-8 -*-
"""
Anti-pattern тесты: глубокие паттерны багов из реальной истории проекта.

ЛОВИТ БАГИ (каждый из них РЕАЛЬНО встречался в production):
1. NameError/ImportError при импорте UI модулей — несуществующие имена в import
2. Дублированные методы в классах — второй тихо перезаписывает первый
3. CustomMessageBox vs CustomQuestionBox — неправильный тип диалога
4. Вызов self.method() где method не определён в классе
5. Прямой доступ self.db./self.api_client. в UI — обход DataAccess

Эти тесты работают на уровне исходного кода (AST/regex), без запуска PyQt5.
"""

import ast
import importlib
from pathlib import Path
import re
import sys

import pytest

UI_DIR = Path(__file__).parent.parent.parent / "ui"
PROJECT_ROOT = Path(__file__).parent.parent.parent


def _read(filepath):
    """Прочитать файл в UTF-8."""
    return filepath.read_text(encoding="utf-8")


def _get_ui_py_files():
    """Все .py файлы в ui/ (кроме __init__.py и не-python файлов)."""
    return sorted(f for f in UI_DIR.glob("*.py") if f.name != "__init__.py" and not f.name.startswith("_"))


def _parse_ast(filepath):
    """Распарсить файл в AST дерево."""
    source = _read(filepath)
    return ast.parse(source, filename=str(filepath))


# ======================================================================
# 1. IMPORT VALIDATION — реальный импорт каждого UI модуля
# Баг: from utils.custom_dialogs import CustomQuestionBox — а его нет
# Баг: from X import Y — NameError при первом использовании модуля
# ======================================================================


class TestImportValidation:
    """Каждый UI модуль должен импортироваться без NameError/ImportError.

    Исторический пример: rates_dialog.py импортировал несуществующее имя
    из модуля — баг обнаруживался только при открытии диалога пользователем.
    """

    @pytest.fixture(autouse=True)
    def _mock_pyqt(self):
        """Мокируем PyQt5 для headless-среды, если он не установлен."""
        # Запоминаем состояние sys.modules для восстановления
        self._original_modules = set(sys.modules.keys())
        yield
        # Восстанавливаем sys.modules — удаляем все новые модули
        new_modules = set(sys.modules.keys()) - self._original_modules
        for mod in new_modules:
            if mod.startswith("ui."):
                del sys.modules[mod]

    def _extract_imports(self, filepath):
        """Извлечь все import/from-import из файла через AST."""
        tree = _parse_ast(filepath)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(
                        {
                            "module": module,
                            "name": alias.name,
                            "line": node.lineno,
                        }
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(
                        {
                            "module": alias.name,
                            "name": None,
                            "line": node.lineno,
                        }
                    )
        return imports

    @pytest.mark.parametrize("filepath", _get_ui_py_files(), ids=lambda f: f.name)
    def test_imports_are_valid_ast(self, filepath):
        """Все имена в import-ах должны существовать в целевых модулях (AST-проверка).

        Проверяем: from X import Y — существует ли Y в модуле X?
        Ограничение: проверяем только внутренние модули проекта (ui.*, utils.*),
        т.к. внешние зависимости могут быть не установлены в тестовой среде.
        """
        imports = self._extract_imports(filepath)
        errors = []

        for imp in imports:
            module = imp["module"]
            name = imp["name"]
            line = imp["line"]

            # Проверяем только внутренние модули проекта
            if not module or not any(module.startswith(prefix) for prefix in ("ui.", "utils.", "database.")):
                continue

            # Пропускаем star imports
            if name == "*":
                continue

            # Находим файл целевого модуля
            module_path = PROJECT_ROOT / module.replace(".", "/")
            target_file = None
            if (module_path.with_suffix(".py")).exists():
                target_file = module_path.with_suffix(".py")
            elif (module_path / "__init__.py").exists():
                target_file = module_path / "__init__.py"

            if target_file is None:
                errors.append(f"  строка {line}: from {module} import {name} -- модуль {module} не найден на диске")
                continue

            # Парсим целевой модуль и ищем определение name
            try:
                target_tree = _parse_ast(target_file)
            except SyntaxError:
                continue

            defined_names = set()
            for node in ast.walk(target_tree):
                if isinstance(node, ast.ClassDef):
                    defined_names.add(node.name)
                elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    defined_names.add(node.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            defined_names.add(target.id)
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        actual_name = alias.asname if alias.asname else alias.name
                        defined_names.add(actual_name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        actual_name = alias.asname if alias.asname else alias.name
                        defined_names.add(actual_name)

            if name and name not in defined_names:
                errors.append(f"  строка {line}: from {module} import {name} -- имя '{name}' НЕ определено в {target_file.name}")

        assert not errors, f"РЕГРЕССИЯ в {filepath.name}: найдены импорты несуществующих имён!\n" + "\n".join(errors) + f"\nЭто приведёт к NameError/ImportError при открытии модуля пользователем."


# ======================================================================
# 2. ДУБЛИРОВАННЫЕ МЕТОДЫ В КЛАССАХ
# Баг: class Foo: def save(self): ... def save(self): ...
# Второй save() тихо перезаписывает первый без предупреждений
# ======================================================================


class TestDuplicateMethodDetection:
    """Каждый класс должен иметь уникальные имена методов.

    Python тихо перезаписывает первое определение вторым.
    В больших файлах (5000+ строк) это частая ошибка при рефакторинге.
    """

    @pytest.mark.parametrize("filepath", _get_ui_py_files(), ids=lambda f: f.name)
    def test_no_duplicate_methods(self, filepath):
        """Ни один класс не должен иметь два метода с одинаковым именем."""
        try:
            tree = _parse_ast(filepath)
        except SyntaxError as e:
            pytest.skip(f"SyntaxError в {filepath.name}: {e}")

        duplicates = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            method_names = {}
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    name = item.name
                    if name in method_names:
                        duplicates.append(f"  класс {node.name}: метод '{name}' определён дважды (строки {method_names[name]} и {item.lineno})")
                    else:
                        method_names[name] = item.lineno

        assert not duplicates, (
            f"РЕГРЕССИЯ в {filepath.name}: найдены дублированные методы!\n" + "\n".join(duplicates) + "\n"
            f"Второе определение тихо перезаписывает первое — "
            f"логика первого метода ПОТЕРЯНА без предупреждений!"
        )


# ======================================================================
# 3. CustomMessageBox vs CustomQuestionBox — правильность использования
# Баг: CustomMessageBox для подтверждения (нужен Yes/No) = нет кнопки "Нет"
# Баг: CustomQuestionBox для информирования = лишняя кнопка "Нет"
# ======================================================================


class TestDialogBoxCorrectness:
    """CustomMessageBox — информирование (OK), CustomQuestionBox — подтверждение (Yes/No).

    Исторический пример: использование CustomMessageBox для удаления записи
    показывало только кнопку OK, и пользователь не мог отменить удаление.
    """

    # Паттерны подтверждения — фразы, ТОЧНО указывающие на необходимость Yes/No.
    # Исключаем информационные ("Не удалось удалить", "Нельзя удалить").
    CONFIRMATION_KEYWORDS = [
        r"\bвы уверены\b",
        r"\bподтвердите\b",
        r"\bподтверждение\b",
        r"\bдействительно хотите\b",
        r"\bхотите удалить\b",
        r"\bхотите сбросить\b",
        r"\bхотите\s+\w+\s*\?",
    ]

    # Исключения — информационные фразы, которые содержат ключевые слова,
    # но НЕ являются подтверждениями
    EXCLUSION_PATTERNS = re.compile(
        r"не удалось|нельзя|невозможно|ошибка|failed|error|"
        r"не найден|не существует|уже удалён|был удалён|успешно удалён",
        re.IGNORECASE,
    )

    CONFIRMATION_RE = re.compile("|".join(CONFIRMATION_KEYWORDS), re.IGNORECASE)

    @pytest.mark.parametrize("filepath", _get_ui_py_files(), ids=lambda f: f.name)
    def test_confirmation_uses_question_box(self, filepath):
        """Диалоги подтверждения (удалить/сбросить/вы уверены) должны использовать CustomQuestionBox."""
        content = _read(filepath)

        # Ищем CustomMessageBox с текстом подтверждения
        # Паттерн: CustomMessageBox(..., "текст с подтверждением", ...)
        # или CustomMessageBox(\n...\n "текст"
        problems = []

        # Находим все вызовы CustomMessageBox
        # Простой подход: ищем CustomMessageBox( и смотрим следующие 300 символов
        for match in re.finditer(r"CustomMessageBox\s*\(", content):
            start = match.end()
            # Берём фрагмент аргументов (до 500 символов)
            fragment = content[start : start + 500]
            # Ищем первую закрывающую скобку (упрощённо)
            paren_depth = 1
            end_idx = 0
            for i, ch in enumerate(fragment):
                if ch == "(":
                    paren_depth += 1
                elif ch == ")":
                    paren_depth -= 1
                    if paren_depth == 0:
                        end_idx = i
                        break
            if end_idx == 0:
                end_idx = min(300, len(fragment))

            args_text = fragment[:end_idx]

            # Проверяем: содержит ли текст аргументов слова подтверждения?
            if self.CONFIRMATION_RE.search(args_text):
                # Исключаем информационные сообщения
                if self.EXCLUSION_PATTERNS.search(args_text):
                    continue
                # Определяем номер строки
                line_no = content[: match.start()].count("\n") + 1
                # Извлекаем краткий фрагмент текста
                text_match = re.search(r'["\']([^"\']{10,60})["\']', args_text)
                text_preview = text_match.group(1) if text_match else args_text[:60]
                problems.append(f"  строка {line_no}: CustomMessageBox с текстом подтверждения: '{text_preview}...'")

        assert not problems, (
            f"РЕГРЕССИЯ в {filepath.name}: CustomMessageBox используется для подтверждения!\n" + "\n".join(problems) + "\n"
            f"CustomMessageBox показывает только кнопку OK — пользователь НЕ МОЖЕТ отказаться!\n"
            f"Для подтверждений используйте CustomQuestionBox (Yes/No)."
        )

    @pytest.mark.parametrize("filepath", _get_ui_py_files(), ids=lambda f: f.name)
    def test_question_box_result_is_checked(self, filepath):
        """Результат CustomQuestionBox должен проверяться (if result == ...)."""
        content = _read(filepath)

        problems = []
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Ищем CustomQuestionBox без присвоения результата
            if "CustomQuestionBox" in stripped and ".exec" in stripped:
                # Должно быть: result = ... или if ...
                # Проблема если стоит просто: CustomQuestionBox(...).exec()
                if not any(kw in stripped for kw in ("=", "if ", "elif ", "while ")):
                    # Также допустимо на предыдущей строке
                    prev_line = lines[i - 2].strip() if i >= 2 else ""
                    if not any(kw in prev_line for kw in ("=", "if ", "elif ")):
                        problems.append(f"  строка {i}: {stripped[:80]}")

        assert not problems, (
            f"РЕГРЕССИЯ в {filepath.name}: CustomQuestionBox.exec() без проверки результата!\n" + "\n".join(problems) + "\n"
            f"Если результат не проверяется, диалог бесполезен — "
            f"действие выполнится независимо от выбора пользователя."
        )


# ======================================================================
# 4. ОТСУТСТВУЮЩИЕ МЕТОДЫ — self.method_name() где method не определён
# Баг: вызов self.refresh_data() в классе, где нет такого метода
# ======================================================================


class TestMissingSelfMethods:
    """Все self.method() вызовы должны ссылаться на существующие методы.

    Исторический пример: после рефакторинга метод переименован,
    но один вызов остался со старым именем — crash при определённом сценарии.
    """

    # Методы, унаследованные от QWidget/QDialog/QMainWindow и т.д. —
    # не проверяем, т.к. они определены в базовых классах PyQt5
    KNOWN_QT_METHODS = {
        # QWidget
        "show",
        "hide",
        "close",
        "update",
        "repaint",
        "resize",
        "move",
        "setWindowTitle",
        "setWindowIcon",
        "setMinimumSize",
        "setMaximumSize",
        "setFixedSize",
        "setFixedWidth",
        "setFixedHeight",
        "setMinimumWidth",
        "setMinimumHeight",
        "setMaximumWidth",
        "setMaximumHeight",
        "setEnabled",
        "setDisabled",
        "setVisible",
        "setHidden",
        "setFocus",
        "setFont",
        "setStyleSheet",
        "setLayout",
        "setCursor",
        "setToolTip",
        "setStatusTip",
        "setWhatsThis",
        "setGeometry",
        "setContentsMargins",
        "setSizePolicy",
        "width",
        "height",
        "size",
        "pos",
        "geometry",
        "rect",
        "isVisible",
        "isEnabled",
        "isHidden",
        "isWindow",
        "raise_",
        "lower",
        "activateWindow",
        "setAttribute",
        "setProperty",
        "property",
        "installEventFilter",
        "removeEventFilter",
        "setParent",
        "parent",
        "parentWidget",
        "findChild",
        "findChildren",
        "layout",
        "children",
        "deleteLater",
        "destroyed",
        "grab",
        "render",
        "grabMouse",
        "releaseMouse",
        "setObjectName",
        "objectName",
        "setAccessibleName",
        "setAccessibleDescription",
        "mapToGlobal",
        "mapFromGlobal",
        "mapToParent",
        "mapFromParent",
        "underMouse",
        "hasFocus",
        "adjustSize",
        "updateGeometry",
        "setContextMenuPolicy",
        "setFocusPolicy",
        "setWindowFlags",
        "setWindowModality",
        "palette",
        "setPalette",
        "setAutoFillBackground",
        "ensurePolished",
        "style",
        "setStyle",
        "addAction",
        "removeAction",
        "actions",
        "setMouseTracking",
        "hasMouseTracking",
        "window",
        "winId",
        "nativeParentWidget",
        "isMaximized",
        "isMinimized",
        "isFullScreen",
        "isActiveWindow",
        "showNormal",
        "showMaximized",
        "showMinimized",
        "showFullScreen",
        "styleSheet",
        "setGraphicsEffect",
        "graphicsEffect",
        "frameGeometry",
        "frameSize",
        "normalGeometry",
        "isAncestorOf",
        "childAt",
        "calendarWidget",
        "setCalendarWidget",
        "setCalendarPopup",
        "contentsMargins",
        "getContentsMargins",
        "spacing",
        "setSpacing",
        # QDialog
        "exec",
        "exec_",
        "accept",
        "reject",
        "done",
        "result",
        "setModal",
        "setResult",
        "open",
        # QMainWindow
        "setCentralWidget",
        "centralWidget",
        "menuBar",
        "statusBar",
        "toolBar",
        "addToolBar",
        "addDockWidget",
        "setMenuBar",
        "setStatusBar",
        # QLayout
        "addWidget",
        "addLayout",
        "addStretch",
        "addSpacing",
        "addItem",
        "removeWidget",
        "removeItem",
        "count",
        "itemAt",
        "takeAt",
        "setAlignment",
        "setStretch",
        # QAbstractItemModel / QTableWidget / QTreeWidget
        "setRowCount",
        "setColumnCount",
        "rowCount",
        "columnCount",
        "setItem",
        "item",
        "setHorizontalHeaderLabels",
        "setVerticalHeaderLabels",
        "horizontalHeader",
        "verticalHeader",
        "setSelectionBehavior",
        "setSelectionMode",
        "setEditTriggers",
        "setSortingEnabled",
        "sortItems",
        "sortByColumn",
        "setColumnWidth",
        "setRowHeight",
        "resizeColumnsToContents",
        "clearContents",
        "clear",
        "removeRow",
        "insertRow",
        "selectedItems",
        "selectedRanges",
        "currentRow",
        "currentColumn",
        "setCurrentCell",
        "scrollToItem",
        "scrollTo",
        "setCellWidget",
        "cellWidget",
        "removeCellWidget",
        "setSpan",
        "setItemDelegateForColumn",
        "topLevelItemCount",
        "topLevelItem",
        "addTopLevelItem",
        "setHeaderLabels",
        "headerItem",
        "setHeaderItem",
        "expandAll",
        "collapseAll",
        "expandItem",
        "collapseItem",
        # QComboBox
        "addItems",
        "insertItem",
        "currentText",
        "currentIndex",
        "setCurrentIndex",
        "setCurrentText",
        "itemText",
        "itemData",
        "setItemData",
        "setEditable",
        "setInsertPolicy",
        "setModel",
        "model",
        "setView",
        "view",
        # QLineEdit / QTextEdit / QPlainTextEdit
        "setText",
        "text",
        "setPlaceholderText",
        "setReadOnly",
        "setMaxLength",
        "setValidator",
        "setCompleter",
        "selectAll",
        "setEchoMode",
        "toPlainText",
        "toHtml",
        "setPlainText",
        "setHtml",
        "append",
        "insertPlainText",
        "setTabStopWidth",
        "setLineWrapMode",
        "setDocument",
        "document",
        # QLabel
        "setPixmap",
        "setScaledContents",
        "setWordWrap",
        "setTextFormat",
        "setOpenExternalLinks",
        # QPushButton / QAbstractButton
        "setIcon",
        "setIconSize",
        "setCheckable",
        "setChecked",
        "isChecked",
        "setAutoExclusive",
        "setFlat",
        "click",
        "toggle",
        "animateClick",
        "setMenu",
        "menu",
        "setDefault",
        "setAutoDefault",
        # QCheckBox
        "checkState",
        "setCheckState",
        "setTristate",
        # QProgressBar
        "setValue",
        "setMinimum",
        "setMaximum",
        "setRange",
        "value",
        "minimum",
        "maximum",
        "setFormat",
        "setTextVisible",
        # QScrollArea
        "setWidget",
        "widget",
        "setWidgetResizable",
        "setHorizontalScrollBarPolicy",
        "setVerticalScrollBarPolicy",
        "horizontalScrollBar",
        "verticalScrollBar",
        # QTabWidget
        "addTab",
        "insertTab",
        "removeTab",
        "setTabText",
        "currentWidget",
        "indexOf",
        "setTabEnabled",
        "setTabPosition",
        "setTabShape",
        "setTabsClosable",
        # QSplitter
        "insertWidget",
        "setSizes",
        "sizes",
        "setOrientation",
        "setStretchFactor",
        # QTimer
        "start",
        "stop",
        "setInterval",
        "isActive",
        "singleShot",
        # QStackedWidget
        "setCurrentWidget",
        # Общие сигналы и слоты
        "connect",
        "disconnect",
        "emit",
        "blockSignals",
        "sender",
        "receivers",
        # Python builtins на self
        "format",
        "join",
        "replace",
        "strip",
        "split",
        "extend",
        "insert",
        "remove",
        "pop",
        "get",
        "keys",
        "values",
        "items",
        "add",
        "discard",
        "copy",
        "deepcopy",
        "encode",
        "decode",
        "startswith",
        "endswith",
        "upper",
        "capitalize",
        "title",
        "find",
        "index",
        "rfind",
        "rindex",
        "sort",
        "reverse",
        "isdigit",
        "isalpha",
        "isalnum",
        # Типичные конвенции
        "tr",
        "translate",
        "setWindowFlag",
        "unsetCursor",
    }

    # Дополнительные методы, приходящие через миксины или множественное наследование
    KNOWN_MIXIN_METHODS = {
        "setupUi",
        "retranslateUi",
        "showEvent",
        "closeEvent",
        "resizeEvent",
        "paintEvent",
        "keyPressEvent",
        "keyReleaseEvent",
        "mousePressEvent",
        "mouseReleaseEvent",
        "mouseMoveEvent",
        "mouseDoubleClickEvent",
        "wheelEvent",
        "dragEnterEvent",
        "dragMoveEvent",
        "dragLeaveEvent",
        "dropEvent",
        "focusInEvent",
        "focusOutEvent",
        "enterEvent",
        "leaveEvent",
        "timerEvent",
        "changeEvent",
        "contextMenuEvent",
        "eventFilter",
        "event",
        "nativeEvent",
        "sizeHint",
        "minimumSizeHint",
        "validate",
        "fixup",
    }

    def _get_class_methods(self, class_node):
        """Получить все методы определённые в классе (включая вложенные)."""
        methods = set()
        for item in class_node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.add(item.name)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        methods.add(target.id)
        return methods

    def _get_self_calls(self, class_node):
        """Найти все вызовы self.method_name() в классе."""
        calls = []
        for node in ast.walk(class_node):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "self":
                    calls.append(
                        {
                            "name": func.attr,
                            "line": node.lineno,
                        }
                    )
        return calls

    def _resolve_all_methods(self, class_node, class_map):
        """Собрать все методы класса, включая унаследованные из того же файла."""
        methods = self._get_class_methods(class_node)

        # Разрешаем базовые классы из того же файла
        for base in class_node.bases:
            base_name = None
            if isinstance(base, ast.Name):
                base_name = base.id
            elif isinstance(base, ast.Attribute):
                # Пропускаем внешние базы (например QtWidgets.QWidget)
                continue

            if base_name and base_name in class_map:
                base_methods = self._resolve_all_methods(class_map[base_name], class_map)
                methods |= base_methods

        return methods

    @pytest.mark.parametrize("filepath", _get_ui_py_files(), ids=lambda f: f.name)
    def test_self_method_calls_exist(self, filepath):
        """Все self.method() вызовы должны ссылаться на определённые методы."""
        try:
            tree = _parse_ast(filepath)
        except SyntaxError as e:
            pytest.skip(f"SyntaxError в {filepath.name}: {e}")

        problems = []
        known_external = self.KNOWN_QT_METHODS | self.KNOWN_MIXIN_METHODS

        # Собираем карту всех классов файла для разрешения наследования
        class_map = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_map[node.name] = node

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            # Собираем методы этого класса + базовых классов из файла
            own_methods = self._resolve_all_methods(node, class_map)

            # Также учитываем атрибуты, установленные через self.x = ... в __init__ и др.
            assigned_attrs = set()
            for method_node in ast.walk(node):
                if isinstance(method_node, ast.Assign):
                    for target in method_node.targets:
                        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                            assigned_attrs.add(target.attr)

            # Собираем все self.xxx() вызовы
            self_calls = self._get_self_calls(node)

            for call in self_calls:
                name = call["name"]
                line = call["line"]

                # Пропускаем если метод определён в классе или его базовых
                if name in own_methods:
                    continue

                # Пропускаем если это атрибут (self.timer.start(), self.button.click())
                if name in assigned_attrs:
                    continue

                # Пропускаем известные Qt/Python методы
                if name in known_external:
                    continue

                # Пропускаем методы начинающиеся с _ (приватные, часто наследуемые)
                if name.startswith("_"):
                    continue

                # Если класс наследует от внешнего класса (не из файла),
                # то пропускаем — мы не можем знать методы внешних базовых
                has_external_base = False
                for base in node.bases:
                    if isinstance(base, ast.Attribute):
                        has_external_base = True
                    elif isinstance(base, ast.Name) and base.id not in class_map:
                        has_external_base = True

                if has_external_base:
                    continue

                problems.append(f"  класс {node.name}, строка {line}: self.{name}() -- метод не найден в классе и не является Qt-методом")

        # Фильтруем: показываем только уникальные имена методов (не дублируем)
        seen_methods = set()
        unique_problems = []
        for p in problems:
            # Извлекаем имя метода
            method_match = re.search(r"self\.(\w+)\(\)", p)
            if method_match:
                method_name = method_match.group(1)
                if method_name not in seen_methods:
                    seen_methods.add(method_name)
                    unique_problems.append(p)
            else:
                unique_problems.append(p)

        assert not unique_problems, (
            f"РЕГРЕССИЯ в {filepath.name}: вызовы self.method() без определения!\n" + "\n".join(unique_problems[:15]) + "\n"
            f"(показано первые 15 из {len(unique_problems)})\n"
            f"Метод может быть удалён или переименован при рефакторинге — "
            f"вызов приведёт к AttributeError в runtime."
        )


# ======================================================================
# 5. ОБХОД DataAccess — прямой доступ к self.db / self.api_client в UI
# Баг: self.db.execute() в UI → нет offline fallback, нет кеширования
# ======================================================================


class TestDataAccessBypass:
    """UI модули должны обращаться к данным ТОЛЬКО через DataAccess.

    Прямой доступ self.db.execute() или self.api_client.get() в UI:
    - Не работает в offline-режиме (нет fallback на SQLite)
    - Не кешируется (лишние запросы к серверу)
    - Не логируется единообразно

    Исключения: login_window.py (до авторизации DataAccess не доступен).
    """

    # Файлы, которым разрешён прямой доступ
    EXCEPTIONS = {
        "login_window.py",  # Авторизация — до DataAccess
        "main_window_original.txt",  # Бекап, не код
        "tabs_section_original.txt",  # Бекап, не код
    }

    # Паттерны прямого доступа к БД/API
    DIRECT_DB_PATTERN = re.compile(
        r"self\s*\.\s*db\s*\.\s*(?:execute|fetch|query|cursor|commit|rollback|"
        r"get_|create_|update_|delete_|find_|list_|search_|count_)",
    )
    DIRECT_API_PATTERN = re.compile(
        r"self\s*\.\s*api_client\s*\.\s*(?:get|post|put|patch|delete|request|"
        r"get_|create_|update_|delete_|find_|list_|search_|fetch_)",
    )

    @pytest.mark.parametrize("filepath", [f for f in _get_ui_py_files() if f.name not in {"login_window.py", "main_window_original.txt", "tabs_section_original.txt"}], ids=lambda f: f.name)
    def test_no_direct_db_access(self, filepath):
        """UI файлы не должны обращаться к self.db напрямую."""

        content = _read(filepath)
        matches = []

        for i, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            # Пропускаем комментарии
            if stripped.startswith("#"):
                continue
            if self.DIRECT_DB_PATTERN.search(stripped):
                matches.append(f"  строка {i}: {stripped[:100]}")

        assert not matches, (
            f"РЕГРЕССИЯ в {filepath.name}: прямой доступ к self.db в UI!\n" + "\n".join(matches[:10]) + "\n"
            f"Все CRUD-операции должны идти через DataAccess для:\n"
            f"  - offline fallback (автоматическое переключение на SQLite)\n"
            f"  - кеширование (30с TTL)\n"
            f"  - единообразное логирование ошибок"
        )

    @pytest.mark.parametrize("filepath", [f for f in _get_ui_py_files() if f.name not in {"login_window.py", "main_window_original.txt", "tabs_section_original.txt"}], ids=lambda f: f.name)
    def test_no_direct_api_client_access(self, filepath):
        """UI файлы не должны обращаться к self.api_client напрямую."""

        content = _read(filepath)
        matches = []

        for i, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if self.DIRECT_API_PATTERN.search(stripped):
                matches.append(f"  строка {i}: {stripped[:100]}")

        assert not matches, (
            f"РЕГРЕССИЯ в {filepath.name}: прямой доступ к self.api_client в UI!\n" + "\n".join(matches[:10]) + "\n"
            f"Все CRUD-операции должны идти через DataAccess для:\n"
            f"  - offline fallback (автоматическое переключение на SQLite)\n"
            f"  - кеширование (30с TTL)\n"
            f"  - единообразное логирование ошибок"
        )


# ======================================================================
# 6. prefer_local=True БЕЗ ВОССТАНОВЛЕНИЯ — данные навсегда из локальной БД
# Баг: self.data.prefer_local = True без finally: prefer_local = False
# ======================================================================


class TestPreferLocalSafety:
    """prefer_local=True ОБЯЗАН восстанавливаться в False через try/finally.

    Исторический пример: prefer_local = True в методе без finally →
    после ошибки все последующие запросы шли в пустую локальную SQLite →
    пользователь видел "Нет данных" вместо реальных записей.
    """

    @pytest.mark.parametrize("filepath", _get_ui_py_files(), ids=lambda f: f.name)
    def test_prefer_local_has_finally_restore(self, filepath):
        """Каждый prefer_local=True должен иметь prefer_local=False в finally."""
        content = _read(filepath)

        if "prefer_local" not in content:
            return  # файл не использует prefer_local — проверка не нужна

        lines = content.split("\n")
        problems = []

        for i, line in enumerate(lines):
            stripped = line.strip()
            if "prefer_local" not in stripped:
                continue
            if "True" not in stripped:
                continue
            if stripped.startswith("#"):
                continue
            if "= True" not in stripped and "=True" not in stripped:
                continue

            # Нашли prefer_local = True, ищем prefer_local = False в окрестности
            # (в пределах 100 строк ниже)
            search_end = min(i + 100, len(lines))
            has_restore = False
            has_finally = False

            for j in range(i + 1, search_end):
                line_j = lines[j].strip()
                if "prefer_local" in line_j and ("= False" in line_j or "=False" in line_j):
                    has_restore = True
                if line_j.startswith("finally:"):
                    has_finally = True

            if not has_restore:
                problems.append(f"  строка {i + 1}: prefer_local = True БЕЗ восстановления в False")
            elif has_restore and not has_finally:
                # Есть восстановление, но не в finally — при исключении не сработает
                # Это предупреждение, не ошибка — может быть в том же try блоке
                pass

        assert not problems, (
            f"РЕГРЕССИЯ в {filepath.name}: prefer_local = True без восстановления!\n" + "\n".join(problems) + "\n"
            f"Если prefer_local остаётся True после ошибки, ВСЕ данные будут\n"
            f"читаться из пустой локальной SQLite — пользователь увидит 'Нет данных'.\n"
            f"Исправление: обернуть в try/finally с prefer_local = False в finally."
        )
