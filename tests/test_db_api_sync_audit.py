# -*- coding: utf-8 -*-
"""
Автоматический аудит: поиск вызовов self.db.<write_method>() в UI файлах,
которые не обёрнуты в паттерн API-first (self.api_client / self.data).

Запуск:
    python tests/test_db_api_sync_audit.py
    # или через pytest:
    pytest tests/test_db_api_sync_audit.py -v

Этот тест НЕ требует запущенного сервера — он делает статический анализ кода.
"""
import os
import re
import sys
from collections import defaultdict

# Путь к корню проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ======================================================================
# КОНФИГУРАЦИЯ
# ======================================================================

# UI файлы для проверки
UI_FILES = [
    'ui/crm_tab.py',
    'ui/crm_supervision_tab.py',
    'ui/contracts_tab.py',
    'ui/salaries_tab.py',
    'ui/main_window.py',
    'ui/login_window.py',
    'ui/dashboard_widget.py',
    'ui/employees_tab.py',
    'ui/clients_tab.py',
    'ui/rates_dialog.py',
]

# Паттерны WRITE-операций self.db.<method>()
WRITE_PREFIXES = [
    'update_', 'create_', 'add_', 'delete_', 'remove_',
    'save_', 'insert_', 'set_', 'reset_', 'complete_',
    'assign_', 'move_', 'mark_', 'close_', 'reopen_',
    'toggle_', 'approve_', 'reject_', 'reassign_',
    'increment_', 'decrement_', 'change_', 'modify_',
]

# Методы, которые не нужно проверять
IGNORE_METHODS = [
    'close', 'connect', 'commit', 'rollback', 'cursor',
    'execute', 'fetchone', 'fetchall',
]

# Известные исключения (методы, которые осознанно только локальные)
# Формат: (filename, method_name, reason)
KNOWN_EXCEPTIONS = [
    ('contracts_tab.py', 'add_agent', 'Агенты — локальная справочная таблица'),
    ('contracts_tab.py', 'update_agent_color', 'Цвета агентов — локальная настройка'),
    ('crm_tab.py', 'add_project_template', 'Шаблоны проектов — локальная справочная таблица'),
    ('crm_tab.py', 'delete_project_template', 'Шаблоны проектов — локальная справочная таблица'),
]

# Контекстное окно
CONTEXT_WINDOW_BEFORE = 25  # строк ВЫШЕ
CONTEXT_WINDOW_AFTER = 5    # строк НИЖЕ


# ======================================================================
# АНАЛИЗ
# ======================================================================

def is_write_method(method_name):
    """Является ли метод записывающей операцией?"""
    if method_name in IGNORE_METHODS:
        return False
    for prefix in WRITE_PREFIXES:
        if method_name.startswith(prefix):
            return True
    return False


def is_known_exception(filename, method_name):
    """Является ли этот вызов известным исключением?"""
    base = os.path.basename(filename)
    for exc_file, exc_method, _ in KNOWN_EXCEPTIONS:
        if base == exc_file and method_name == exc_method:
            return True
    return False


def get_indent_level(line):
    """Возвращает уровень отступа строки (в пробелах)."""
    return len(line) - len(line.lstrip())


def find_enclosing_function(lines, line_idx):
    """Находит имя функции/метода, в которой находится строка."""
    indent = get_indent_level(lines[line_idx])
    for i in range(line_idx - 1, max(0, line_idx - 200), -1):
        stripped = lines[i].strip()
        if stripped.startswith('def ') and get_indent_level(lines[i]) < indent:
            match = re.match(r'def\s+(\w+)', stripped)
            if match:
                return match.group(1)
    return None


def is_in_locally_helper(lines, line_idx):
    """Проверяет, находится ли вызов внутри метода *_locally() — осознанный offline-only хелпер."""
    func_name = find_enclosing_function(lines, line_idx)
    if func_name and ('_locally' in func_name or '_local' in func_name or '_set_report_month' in func_name):
        return True
    return False


def is_in_fallback_context(lines, line_idx):
    """
    Проверяет, находится ли вызов в контексте fallback после API вызова.
    Расширенная проверка:
    - except блок (try/except с API вызовом выше)
    - else: (после if self.api_client:)
    - if not api_ok / if not success / if not updated:
    - Внутри функции *_locally()
    - После print с "fallback" или "offline"
    """
    if is_in_locally_helper(lines, line_idx):
        return True

    target_indent = get_indent_level(lines[line_idx])

    # Ищем вверх по коду
    for i in range(line_idx - 1, max(0, line_idx - CONTEXT_WINDOW_BEFORE), -1):
        line = lines[i]
        stripped = line.strip()
        line_indent = get_indent_level(line)

        # except Exception — мы в блоке обработки ошибки
        if stripped.startswith('except') and ('Exception' in stripped or 'except:' == stripped):
            if line_indent <= target_indent:
                return True

        # if not api_ok / if not success / if not updated
        if re.match(r'if\s+not\s+(api_ok|api_reset_ok|success|updated|api_success)', stripped):
            if line_indent <= target_indent:
                return True

        # else: после if self.api_client
        if stripped == 'else:' and line_indent < target_indent:
            # Ищем if self.api_client выше
            for j in range(i - 1, max(0, i - 15), -1):
                if 'if self.api_client' in lines[j] or 'if self.api_client' in lines[j]:
                    return True

        # "fallback" или "Пытаемся сохранить локально" в комментарии/print выше
        if ('fallback' in stripped.lower() or 'локально' in stripped.lower()) and i > line_idx - 5:
            return True

        # Паттерн "API success + local sync": self.api_client.method() выше,
        # потом self.db.method() — это синхронизация локального кэша
        if 'self.api_client.' in stripped and line_indent <= target_indent:
            # Проверяем, что API вызов был успешным (не в try/except)
            return True

    return False


def has_api_in_context(lines, line_idx):
    """
    Проверяет, есть ли API вызов в контексте (ВЫШЕ текущей строки).
    """
    start = max(0, line_idx - CONTEXT_WINDOW_BEFORE)
    end = min(len(lines), line_idx + CONTEXT_WINDOW_AFTER)
    context_text = '\n'.join(lines[start:end])

    api_patterns = [
        r'self\.api_client\.\w+',
        r'self\.data\.\w+',
        r'if\s+self\.api_client',
        r'api_ok\s*=',
        r'api_reset_ok\s*=',
        r'api_success\s*=',
    ]

    for pattern in api_patterns:
        if re.search(pattern, context_text):
            return True

    return False


def analyze_file(filepath):
    """Анализирует один файл на предмет необёрнутых self.db вызовов."""
    issues = []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception as e:
        return [{'file': filepath, 'line': 0, 'method': 'N/A',
                 'issue': f'Ошибка чтения файла: {e}'}]

    pattern = re.compile(r'self\.db\.(\w+)\s*\(')

    for i, line in enumerate(lines):
        for match in pattern.finditer(line):
            method_name = match.group(1)

            if not is_write_method(method_name):
                continue

            if is_known_exception(filepath, method_name):
                continue

            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            # 0. Пропускаем если внутри offline-хелпера (*_locally, *_local)
            if is_in_locally_helper(lines, i):
                continue

            # 1. Проверяем local-first паттерн: API вызов НИЖЕ текущей строки
            below_start = min(len(lines), i + 1)
            below_end = min(len(lines), i + 15)
            below_text = '\n'.join(lines[below_start:below_end])
            if re.search(r'self\.api_client\.\w+|if\s+self\.api_client', below_text):
                continue  # Local-first паттерн: запись в БД, потом sync через API

            # 2. Проверяем offline_manager.queue_operation рядом (±5 строк)
            queue_start = max(0, i - 5)
            queue_end = min(len(lines), i + 5)
            queue_text = '\n'.join(lines[queue_start:queue_end])
            if 'offline_manager.queue_operation' in queue_text:
                continue  # Offline queue + immediate local update

            # 3. Есть ли API вызов в контексте?
            if not has_api_in_context(lines, i):
                # Нет API вообще — это баг
                issues.append({
                    'file': filepath,
                    'line': i + 1,
                    'method': method_name,
                    'code': stripped,
                    'func': find_enclosing_function(lines, i) or '?',
                    'issue': f'self.db.{method_name}() без API в контексте'
                })
                continue

            # 2. API есть — проверяем, что мы в fallback блоке
            if is_in_fallback_context(lines, i):
                continue  # Правильный fallback

            # Проверяем: возможно это дубликат (API уже вызван и мы дублируем локально)
            # Такие случаи — это баги (двойная запись)
            issues.append({
                'file': filepath,
                'line': i + 1,
                'method': method_name,
                'code': stripped,
                'func': find_enclosing_function(lines, i) or '?',
                'issue': f'self.db.{method_name}() — возможный дубликат (API уже рядом, не в fallback)'
            })

    return issues


def run_audit():
    """Запускает полный аудит всех UI файлов."""
    all_issues = []
    files_checked = 0
    total_write_calls = 0
    total_all_calls = 0

    print("=" * 70)
    print("АУДИТ СИНХРОНИЗАЦИИ: self.db write calls без API обёртки")
    print("=" * 70)

    for rel_path in UI_FILES:
        filepath = os.path.join(BASE_DIR, rel_path)
        if not os.path.exists(filepath):
            print(f"  [SKIP] {rel_path} — файл не найден")
            continue

        issues = analyze_file(filepath)
        all_issues.extend(issues)
        files_checked += 1

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            all_calls = re.findall(r'self\.db\.(\w+)\s*\(', content)
            total_all_calls += len(all_calls)
            total_write_calls += sum(1 for m in all_calls if is_write_method(m))
        except Exception:
            pass

    # Отчёт
    print(f"\nФайлов проверено: {files_checked}")
    print(f"Всего вызовов self.db.*: {total_all_calls}")
    print(f"Из них write-операций: {total_write_calls}")
    print(f"Проблем найдено: {len(all_issues)}")

    if all_issues:
        print("\n" + "=" * 70)
        print("НАЙДЕННЫЕ ПРОБЛЕМЫ:")
        print("=" * 70)

        by_file = defaultdict(list)
        for issue in all_issues:
            by_file[issue['file']].append(issue)

        for filepath, issues in by_file.items():
            rel = os.path.relpath(filepath, BASE_DIR)
            print(f"\n  {rel}:")
            for issue in issues:
                print(f"    Строка {issue['line']} [{issue['func']}]: {issue['issue']}")
                print(f"      {issue['code']}")
    else:
        print("\n  ВСЕ write-вызовы self.db.* правильно обёрнуты в API паттерн!")

    print("\n" + "=" * 70)
    print(f"Известные исключения (осознанно локальные):")
    for exc_file, exc_method, reason in KNOWN_EXCEPTIONS:
        print(f"  {exc_file}: {exc_method}() — {reason}")
    print("=" * 70)

    return all_issues


# ======================================================================
# PYTEST ИНТЕГРАЦИЯ
# ======================================================================

def test_no_unwrapped_db_writes():
    """
    Тест: все write-вызовы self.db в UI файлах должны быть обёрнуты в API паттерн.

    Паттерн:
        if self.api_client:
            try:
                self.api_client.method(...)
            except Exception:
                self.db.method(...)   # fallback
        else:
            self.db.method(...)       # offline

    Запуск: pytest tests/test_db_api_sync_audit.py -v
    """
    issues = run_audit()

    if issues:
        msg = f"\n\nНайдено {len(issues)} вызовов self.db без API обёртки:\n\n"
        for issue in issues:
            rel = os.path.relpath(issue['file'], BASE_DIR)
            msg += f"  {rel}:{issue['line']} [{issue['func']}] — {issue['issue']}\n"
            msg += f"    {issue['code']}\n\n"
        msg += (
            "Исправьте: добавьте API-first паттерн:\n"
            "  if self.api_client:\n"
            "      try: self.api_client.method(...)\n"
            "      except: self.db.method(...)  # fallback\n"
            "  else:\n"
            "      self.db.method(...)  # offline\n\n"
            "Или добавьте в KNOWN_EXCEPTIONS если метод осознанно локальный."
        )
        assert False, msg


# ======================================================================
# STANDALONE ЗАПУСК
# ======================================================================

if __name__ == '__main__':
    issues = run_audit()
    sys.exit(1 if issues else 0)
