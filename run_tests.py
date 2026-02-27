#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interior Studio CRM — Test Runner с прогрессбаром.

Возможности:
  - Прогрессбар с % прохождения и ETA
  - Логирование результатов в tests/logs/
  - Цветной вывод (PASS/FAIL)
  - Итоговый summary для Claude Code

Использование:
  python run_tests.py                        — все локальные тесты
  python run_tests.py client                 — только client
  python run_tests.py ui                     — только UI
  python run_tests.py db                     — только DB
  python run_tests.py api_client             — API client тесты
  python run_tests.py edge_cases             — Edge cases
  python run_tests.py frontend               — Frontend тесты
  python run_tests.py integration            — Интеграционные тесты
  python run_tests.py regression             — Регрессионные тесты
  python run_tests.py backend                — Backend (нужен сервер)
  python run_tests.py e2e                    — E2E (нужен сервер)
  python run_tests.py smoke                  — Smoke (нужен сервер)
  python run_tests.py contract               — Contract (нужен сервер)
  python run_tests.py client ui db           — несколько групп
  python run_tests.py --server               — только серверные тесты
  python run_tests.py --all                  — локальные + серверные
  python run_tests.py --coverage             — с замером coverage

Интерактивный режим:
  python run_tests.py                        — открывает меню выбора
  Клавиши 1-9, 0, a-b переключают группы
  L/S/A/N — быстрый выбор, Enter — запуск, Q — выход
"""

import subprocess
import sys
import os
import time
import re
import json
from datetime import datetime
from pathlib import Path

# Принудительная UTF-8 для Windows консоли
if sys.platform == 'win32':
    os.system('chcp 65001 > nul 2>&1')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ===== ЦВЕТА =====
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    DIM = '\033[2m'


def colorize(text, color):
    return f"{color}{text}{Colors.RESET}"


# ===== ПРОГРЕССБАР =====
def progress_bar(current, total, width=40, elapsed=0, prefix=''):
    """Рисует ASCII прогрессбар."""
    if total == 0:
        pct = 0
    else:
        pct = current / total * 100

    filled = int(width * current / max(total, 1))
    bar = '█' * filled + '░' * (width - filled)

    # ETA
    if current > 0 and elapsed > 0:
        eta_seconds = (elapsed / current) * (total - current)
        eta_str = f"ETA {int(eta_seconds)}s"
    else:
        eta_str = "ETA --"

    line = f"\r  {prefix} [{bar}] {pct:5.1f}% ({current}/{total}) {elapsed:.0f}s {eta_str}  "
    sys.stdout.write(line)
    sys.stdout.flush()


# ===== ИНТЕРАКТИВНОЕ МЕНЮ =====
def _get_key():
    """Считать одну клавишу без ожидания Enter."""
    if sys.platform == 'win32':
        import msvcrt
        return msvcrt.getwch()
    else:
        import tty, termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def interactive_menu(local_suites, server_suites):
    """Интерактивное меню выбора тестовых групп."""
    items = []
    for key, (label, path) in local_suites.items():
        exists = Path(path).exists()
        items.append({
            'key': key, 'label': label, 'path': path,
            'selected': exists, 'exists': exists, 'server': False
        })
    for key, (label, path) in server_suites.items():
        exists = Path(path).exists()
        items.append({
            'key': key, 'label': label, 'path': path,
            'selected': False, 'exists': exists, 'server': True
        })

    # Маппинг клавиш: '1'-'9' → 0-8, '0' → 9, 'a'-'z' → 10+
    key_map = {}
    for i in range(min(9, len(items))):
        key_map[str(i + 1)] = i
    if len(items) > 9:
        key_map['0'] = 9
    for i in range(10, len(items)):
        key_map[chr(ord('a') + i - 10)] = i
    display_keys = {v: k for k, v in key_map.items()}

    def draw():
        os.system('cls' if sys.platform == 'win32' else 'clear')
        print()
        print(f"  {colorize('═' * 56, Colors.CYAN)}")
        print(f"  {colorize('  Interior Studio CRM — Test Runner', Colors.BOLD)}")
        print(f"  {colorize('═' * 56, Colors.CYAN)}")
        print(f"  {Colors.DIM}  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
        print()
        print(f"  {Colors.DIM}Нажмите цифру/букву для переключения группы{Colors.RESET}")
        print()

        # Локальные
        print(f"  {colorize('ЛОКАЛЬНЫЕ', Colors.BOLD)} {Colors.DIM}(без сервера){Colors.RESET}")
        for i, item in enumerate(items):
            if item['server']:
                break
            dk = display_keys[i]
            check = colorize('x', Colors.GREEN) if item['selected'] else ' '
            suffix = colorize(' (нет)', Colors.RED) if not item['exists'] else ''
            print(f"    [{check}] {colorize(dk, Colors.CYAN)}  {item['label']:12s}  {Colors.DIM}{item['path']}{Colors.RESET}{suffix}")

        print()

        # Серверные
        print(f"  {colorize('СЕРВЕРНЫЕ', Colors.BOLD)} {Colors.DIM}(нужен запущенный сервер){Colors.RESET}")
        for i, item in enumerate(items):
            if not item['server']:
                continue
            dk = display_keys[i]
            check = colorize('x', Colors.GREEN) if item['selected'] else ' '
            suffix = colorize(' (нет)', Colors.RED) if not item['exists'] else ''
            print(f"    [{check}] {colorize(dk, Colors.CYAN)}  {item['label']:12s}  {Colors.DIM}{item['path']}{Colors.RESET}{suffix}")

        selected_count = sum(1 for item in items if item['selected'])
        print()
        print(f"  {colorize('─' * 56, Colors.DIM)}")
        print(f"  {colorize('L', Colors.CYAN)} Локальные  "
              f"{colorize('S', Colors.CYAN)} Серверные  "
              f"{colorize('A', Colors.CYAN)} Все  "
              f"{colorize('N', Colors.CYAN)} Снять  "
              f"{colorize('Enter', Colors.CYAN)} Запуск  "
              f"{colorize('Q', Colors.CYAN)} Выход")
        print(f"  Выбрано: {colorize(str(selected_count), Colors.BOLD)} групп")
        print()

    while True:
        draw()
        ch = _get_key()

        if ch in ('\r', '\n'):  # Enter → запуск
            break
        elif ch.lower() == 'q' or ch == '\x1b':  # Q или Esc → выход
            return None
        elif ch.lower() == 'l':
            for item in items:
                item['selected'] = not item['server'] and item['exists']
        elif ch.lower() == 's':
            for item in items:
                item['selected'] = item['server'] and item['exists']
        elif ch.lower() == 'a':
            for item in items:
                item['selected'] = item['exists']
        elif ch.lower() == 'n':
            for item in items:
                item['selected'] = False
        elif ch.lower() in key_map:
            idx = key_map[ch.lower()]
            if items[idx]['exists']:
                items[idx]['selected'] = not items[idx]['selected']

    return [(item['key'], item['label'], item['path']) for item in items if item['selected']]


# ===== СБОР ТЕСТОВ =====
def collect_tests(venv_python, test_dir, extra_args=None):
    """Собрать количество тестов через pytest --collect-only."""
    cmd = [venv_python, '-m', 'pytest', test_dir, '--collect-only', '-q']
    if extra_args:
        cmd.extend(extra_args)

    env = os.environ.copy()
    if 'ui' in test_dir:
        env['QT_QPA_PLATFORM'] = 'offscreen'

    result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=os.getcwd())
    # Парсим "collected N items" или "N tests collected" из вывода
    for line in result.stdout.split('\n'):
        m = re.search(r'collected\s+(\d+)\s+item', line)
        if m:
            return int(m.group(1))
        m = re.search(r'(\d+)\s+test', line)
        if m:
            return int(m.group(1))
    return 0


# ===== ЗАПУСК С ПРОГРЕССБАРОМ =====
def run_with_progress(venv_python, test_dir, label, log_file, extra_args=None):
    """Запустить тесты с прогрессбаром."""
    print(f"\n  {colorize(label, Colors.BOLD)}")
    print(f"  {Colors.DIM}Сбор тестов...{Colors.RESET}", end='', flush=True)

    total = collect_tests(venv_python, test_dir, extra_args)
    print(f"\r  Найдено: {total} тестов{' ' * 20}")

    if total == 0:
        print(f"  {colorize('Тесты не найдены', Colors.YELLOW)}")
        return {'passed': 0, 'failed': 0, 'errors': 0, 'total': 0, 'duration': 0}

    # Запуск pytest с verbose output
    cmd = [venv_python, '-m', 'pytest', test_dir, '-v', '--tb=short', '--no-header']
    if extra_args:
        cmd.extend(extra_args)

    env = os.environ.copy()
    if 'ui' in test_dir:
        env['QT_QPA_PLATFORM'] = 'offscreen'

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, env=env, cwd=os.getcwd(), bufsize=1
    )

    start_time = time.time()
    passed = 0
    failed = 0
    errors = 0
    current = 0
    log_lines = []

    prev_current = -1
    for line in process.stdout:
        log_lines.append(line)

        # Парсим результат теста
        # Реальные pytest-строки имеют вид: "tests/foo.py::test_bar PASSED/FAILED"
        # Условие '::' in line отсекает WARNING-строки вида "WARNING: Test FAILED: ..."
        if ' PASSED' in line and '::' in line:
            passed += 1
            current += 1
        elif ' FAILED' in line and '::' in line:
            failed += 1
            current += 1
        elif 'ERROR' in line and '::' in line:
            errors += 1
            current += 1
        elif ' SKIPPED' in line and '::' in line:
            current += 1

        if current != prev_current:
            elapsed = time.time() - start_time
            progress_bar(current, total, elapsed=elapsed, prefix=label)
            prev_current = current

    process.wait()
    elapsed = time.time() - start_time

    # Финальный прогрессбар
    progress_bar(total, total, elapsed=elapsed, prefix=label)
    print()  # новая строка

    # Записать лог
    with open(log_file, 'w', encoding='utf-8') as f:
        f.writelines(log_lines)

    # Результат
    status = colorize('PASS', Colors.GREEN) if failed == 0 and errors == 0 else colorize('FAIL', Colors.RED)
    print(f"  {status}: {passed} passed, {failed} failed, {errors} errors in {elapsed:.1f}s")

    return {
        'passed': passed, 'failed': failed, 'errors': errors,
        'total': total, 'duration': elapsed
    }


# ===== MAIN =====
def main():
    venv_python = os.path.join('.venv', 'Scripts', 'python.exe')
    if not os.path.exists(venv_python):
        venv_python = sys.executable

    log_dir = Path('tests/logs')
    log_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    use_coverage = '--coverage' in sys.argv

    # Определяем какие группы запускать
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    run_all = len(args) == 0

    # Локальные тесты (без сервера)
    LOCAL_SUITES = {
        'client':      ('Client',      'tests/client/'),
        'ui':          ('UI',          'tests/ui/'),
        'db':          ('DB',          'tests/db/'),
        'api_client':  ('API Client',  'tests/api_client/'),
        'edge_cases':  ('Edge Cases',  'tests/edge_cases/'),
        'frontend':    ('Frontend',    'tests/frontend/'),
        'integration': ('Integration', 'tests/integration/'),
        'regression':  ('Regression',  'tests/regression/'),
    }
    # Серверные тесты (нужен запущенный сервер)
    SERVER_SUITES = {
        'backend':     ('Backend',     'tests/backend/'),
        'e2e':         ('E2E',         'tests/e2e/'),
        'smoke':       ('Smoke',       'tests/smoke/'),
        'contract':    ('Contract',    'tests/contract/'),
    }

    run_server = '--server' in sys.argv
    run_everything = '--all' in sys.argv
    has_flags = run_server or run_everything or use_coverage

    suites = []
    if run_everything:
        # --all: локальные + серверные
        for key, (label, path) in {**LOCAL_SUITES, **SERVER_SUITES}.items():
            if Path(path).exists():
                suites.append((label, path, str(log_dir / f'{key}_{ts}.log'), []))
    elif run_server:
        # --server: только серверные
        for key, (label, path) in SERVER_SUITES.items():
            if Path(path).exists():
                suites.append((label, path, str(log_dir / f'{key}_{ts}.log'), []))
    elif run_all and not has_flags and sys.stdin.isatty():
        # Интерактивное меню (терминал, без аргументов)
        selected = interactive_menu(LOCAL_SUITES, SERVER_SUITES)
        if selected is None:
            print(f"\n  {Colors.DIM}Отменено.{Colors.RESET}\n")
            return 0
        for key, label, path in selected:
            suites.append((label, path, str(log_dir / f'{key}_{ts}.log'), []))
    elif run_all:
        # Не-интерактивный режим (pipe/CI) — только локальные тесты
        for key, (label, path) in LOCAL_SUITES.items():
            if Path(path).exists():
                suites.append((label, path, str(log_dir / f'{key}_{ts}.log'), []))
    else:
        all_suites = {**LOCAL_SUITES, **SERVER_SUITES}
        for arg in args:
            if arg in all_suites:
                label, path = all_suites[arg]
                suites.append((label, path, str(log_dir / f'{arg}_{ts}.log'), []))

    print()
    print(f"  {colorize('═' * 50, Colors.CYAN)}")
    print(f"  {colorize('  Interior Studio CRM — Test Runner', Colors.BOLD)}")
    print(f"  {colorize('═' * 50, Colors.CYAN)}")
    print(f"  {Colors.DIM}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")

    results = {}
    total_time = time.time()

    for label, test_dir, log_file, extra in suites:
        results[label] = run_with_progress(venv_python, test_dir, label, log_file, extra)

    total_elapsed = time.time() - total_time

    # ===== SUMMARY =====
    print()
    print(f"  {colorize('═' * 50, Colors.CYAN)}")
    print(f"  {colorize('  ИТОГО', Colors.BOLD)}")
    print(f"  {colorize('═' * 50, Colors.CYAN)}")

    total_passed = sum(r['passed'] for r in results.values())
    total_failed = sum(r['failed'] for r in results.values())
    total_errors = sum(r['errors'] for r in results.values())
    total_tests = sum(r['total'] for r in results.values())

    for label, r in results.items():
        status = colorize('✓', Colors.GREEN) if r['failed'] == 0 else colorize('✗', Colors.RED)
        print(f"  {status} {label:12s}: {r['passed']:4d} passed, {r['failed']:2d} failed ({r['duration']:.1f}s)")

    print(f"  {'─' * 50}")
    all_ok = total_failed == 0 and total_errors == 0
    final = colorize('ALL PASS', Colors.GREEN) if all_ok else colorize('HAS FAILURES', Colors.RED)
    print(f"  {final}: {total_passed}/{total_tests} tests in {total_elapsed:.1f}s")

    # Сохранить summary JSON для Claude Code
    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_tests': total_tests,
        'passed': total_passed,
        'failed': total_failed,
        'errors': total_errors,
        'duration_seconds': round(total_elapsed, 1),
        'all_pass': all_ok,
        'suites': {k: v for k, v in results.items()},
    }
    summary_file = str(log_dir / f'summary_{ts}.json')
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n  {Colors.DIM}Логи: {log_dir}/{Colors.RESET}")
    print(f"  {Colors.DIM}Summary: {summary_file}{Colors.RESET}")
    print()

    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
