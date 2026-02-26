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
  python run_tests.py              — все тесты
  python run_tests.py client       — только client
  python run_tests.py ui           — только UI
  python run_tests.py db           — только DB
  python run_tests.py --coverage   — с замером coverage
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

    for line in process.stdout:
        log_lines.append(line)

        # Парсим результат теста
        if 'PASSED' in line:
            passed += 1
            current += 1
        elif 'FAILED' in line:
            failed += 1
            current += 1
        elif 'ERROR' in line and '::' in line:
            errors += 1
            current += 1
        elif 'SKIPPED' in line:
            current += 1

        elapsed = time.time() - start_time
        progress_bar(current, total, elapsed=elapsed, prefix=label)

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

    suites = []
    if run_all or 'client' in args:
        suites.append(('Client', 'tests/client/', str(log_dir / f'client_{ts}.log'), []))
    if run_all or 'ui' in args:
        suites.append(('UI', 'tests/ui/', str(log_dir / f'ui_{ts}.log'), []))
    if run_all or 'db' in args:
        suites.append(('DB', 'tests/db/', str(log_dir / f'db_{ts}.log'), []))

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
        print(f"  {status} {label:8s}: {r['passed']:4d} passed, {r['failed']:2d} failed ({r['duration']:.1f}s)")

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
