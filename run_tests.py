#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interior Studio CRM — Test Runner (интерактивный, с деревом тестов).

Функционал как VSCode Testing, но в терминале:
  - Дерево тестов: группа > файл > тест
  - Живые галочки/крестики по мере прохождения
  - Нумерация тестов и прогрессбары (группа + общий)
  - Интерактивное меню выбора групп
  - Логи в tests/logs/

Использование:
  python run_tests.py                        -- интерактивное меню
  python run_tests.py property               -- одна группа
  python run_tests.py client ui db           -- несколько групп
  python run_tests.py --server               -- серверные тесты
  python run_tests.py --all                  -- все тесты
  python run_tests.py --coverage             -- с coverage
"""

import subprocess
import sys
import os
import time
import re
import json
from datetime import datetime
from pathlib import Path

# UTF-8 для Windows
if sys.platform == 'win32':
    os.system('chcp 65001 > nul 2>&1')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ===== ЦВЕТА =====
class C:
    G = '\033[92m'     # green
    R = '\033[91m'     # red
    Y = '\033[93m'     # yellow
    CY = '\033[96m'    # cyan
    B = '\033[1m'      # bold
    D = '\033[2m'      # dim
    _ = '\033[0m'      # reset
    BG_G = '\033[42m'  # bg green
    BG_R = '\033[41m'  # bg red
    W = '\033[97m'     # white


def _fmt_time(seconds):
    """Форматировать секунды как Ч:ММ:СС или М:СС."""
    seconds = max(0, int(seconds))
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _get_key():
    """Считать одну клавишу без Enter."""
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


def _clear():
    os.system('cls' if sys.platform == 'win32' else 'clear')


# ===== СБОР ТЕСТОВ =====
def collect_test_count(venv_python, test_dir):
    """Собрать количество тестов через pytest --collect-only."""
    cmd = [venv_python, '-m', 'pytest', test_dir, '--collect-only', '-q', '--color=no']
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    env['COLUMNS'] = '300'
    if any(qt_dir in test_dir for qt_dir in ('ui', 'visual')):
        env['QT_QPA_PLATFORM'] = 'offscreen'

    result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=os.getcwd())
    for line in result.stdout.split('\n'):
        m = re.search(r'(\d+)\s+tests?\s+collected', line)
        if m:
            return int(m.group(1))
        m = re.search(r'collected\s+(\d+)\s+item', line)
        if m:
            return int(m.group(1))
    return 0


# ===== ПРОГРЕССБАР =====
def _make_bar(current, total, width=25):
    """Создать строку прогрессбара [████░░░░]."""
    filled = int(width * current / max(total, 1))
    return '\u2588' * filled + '\u2591' * (width - filled)


def _format_bar_line(label, current, total, passed, failed, skipped, elapsed, eta):
    """Форматировать одну строку прогрессбара."""
    pct = current / max(total, 1) * 100
    bar = _make_bar(current, total)
    return (
        f"  {label:12s} [{bar}] {pct:5.1f}% ({current}/{total})  "
        f"{C.G}{passed}v{C._} {C.R}{failed}x{C._} {C.Y}{skipped}S{C._}  "
        f"{_fmt_time(elapsed)} ETA {_fmt_time(eta)}\033[K"
    )


def _draw_bars(suite_label, s_cur, s_tot, s_pass, s_fail, s_skip, s_elapsed,
               global_state=None):
    """Нарисовать 2 строки прогресса: suite + global."""
    s_eta = (s_elapsed / s_cur) * (s_tot - s_cur) if s_cur > 0 else 0
    sys.stdout.write(_format_bar_line(
        f"{C.CY}{suite_label}{C._}", s_cur, s_tot, s_pass, s_fail, s_skip, s_elapsed, s_eta
    ) + '\n')

    if global_state and global_state['total'] > 0:
        g = global_state
        g_elapsed = time.time() - g['start_time']
        g_eta = (g_elapsed / g['current']) * (g['total'] - g['current']) if g['current'] > 0 else 0
        sys.stdout.write(_format_bar_line(
            f"{C.B}TOTAL{C._}       ", g['current'], g['total'],
            g['passed'], g['failed'], g['skipped'], g_elapsed, g_eta
        ))
    sys.stdout.flush()


def _erase_bars(has_global=True):
    """Стереть строки прогрессбаров (cursor up + erase)."""
    lines = 2 if has_global else 1
    for _ in range(lines):
        sys.stdout.write('\033[A\r\033[K')


# ===== ИНТЕРАКТИВНОЕ МЕНЮ =====
def interactive_menu(local_suites, server_suites):
    """Интерактивное меню с подсчётом тестов."""
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

    key_map = {}
    for i in range(min(9, len(items))):
        key_map[str(i + 1)] = i
    if len(items) > 9:
        key_map['0'] = 9
    for i in range(10, len(items)):
        key_map[chr(ord('a') + i - 10)] = i
    display_keys = {v: k for k, v in key_map.items()}

    def draw():
        _clear()
        print()
        print(f"  {C.CY}{'═' * 60}{C._}")
        print(f"  {C.B}  Interior Studio CRM — Test Runner{C._}")
        print(f"  {C.CY}{'═' * 60}{C._}")
        print(f"  {C.D}  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{C._}")
        print()

        # Локальные
        print(f"  {C.B}ЛОКАЛЬНЫЕ{C._} {C.D}(без сервера){C._}")
        for i, item in enumerate(items):
            if item['server']:
                break
            dk = display_keys.get(i, '?')
            check = f"{C.G}x{C._}" if item['selected'] else ' '
            suffix = f" {C.R}(нет){C._}" if not item['exists'] else ''
            print(f"    [{check}] {C.CY}{dk}{C._}  {item['label']:12s}  {C.D}{item['path']}{C._}{suffix}")
е        print()
        print(f"  {C.B}СЕРВЕРНЫЕ{C._} {C.D}(нужен запущенный сервер){C._}")
        for i, item in enumerate(items):
            if not item['server']:
                continue
            dk = display_keys.get(i, '?')
            check = f"{C.G}x{C._}" if item['selected'] else ' '
            suffix = f" {C.R}(нет){C._}" if not item['exists'] else ''
            print(f"    [{check}] {C.CY}{dk}{C._}  {item['label']:12s}  {C.D}{item['path']}{C._}{suffix}")

        selected_count = sum(1 for item in items if item['selected'])
        print()
        print(f"  {C.D}{'─' * 60}{C._}")
        print(f"  {C.CY}L{C._} Локальные  "
              f"{C.CY}S{C._} Серверные  "
              f"{C.CY}A{C._} Все  "
              f"{C.CY}N{C._} Снять  "
              f"{C.CY}Enter{C._} Запуск  "
              f"{C.CY}Q{C._} Выход")
        print(f"  Выбрано: {C.B}{selected_count}{C._} групп")
        print()

    while True:
        draw()
        ch = _get_key()

        if ch in ('\r', '\n'):
            break
        elif ch.lower() == 'q' or ch == '\x1b':
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


# ===== LIVE TREE RUNNER =====
def run_suite_live(venv_python, test_dir, label, log_file, global_state=None, extra_args=None):
    """Запуск группы тестов с живым деревом результатов.

    Показывает каждый тест с нумерацией и результатом (v/x/S),
    двойной прогрессбар (группа + общий) и итоги.
    """
    has_global = global_state is not None and global_state['total'] > 0

    # Сбор списка тестов
    sys.stdout.write(f"\n  {C.B}{label}{C._} {C.D}сбор тестов...{C._}")
    sys.stdout.flush()
    total = collect_test_count(venv_python, test_dir)
    sys.stdout.write(f"\r  {C.B}{label}{C._} ({total} тестов)                    \n")
    sys.stdout.flush()

    if total == 0:
        print(f"  {C.Y}  Тесты не найдены{C._}")
        return {
            'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0,
            'total': 0, 'duration': 0, 'test_results': []
        }

    # Запуск pytest
    cmd = [venv_python, '-m', 'pytest', test_dir, '-v', '--tb=short', '--no-header', '--color=no']
    if extra_args:
        cmd.extend(extra_args)

    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    env['COLUMNS'] = '300'
    if any(qt_dir in test_dir for qt_dir in ('ui', 'visual')):
        env['QT_QPA_PLATFORM'] = 'offscreen'

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, env=env, cwd=os.getcwd(), bufsize=1
    )

    start_time = time.time()
    passed = 0
    failed = 0
    errors = 0
    skipped = 0
    current = 0
    log_lines = []
    test_results = []  # [(name, status)]
    bars_drawn = False

    # Текущий файл для группировки вывода
    current_file = None
    file_stats = {}  # file -> {'passed': N, 'failed': N, ...}

    for line in process.stdout:
        log_lines.append(line)
        stripped = line.strip()

        # Определяем результат теста: ищем строки вида "path::test PASSED"
        status = None
        test_id = None

        if '::' in stripped:
            for st, keyword in [('PASSED', ' PASSED'), ('FAILED', ' FAILED'),
                                ('SKIPPED', ' SKIPPED'), ('ERROR', ' ERROR'),
                                ('XFAIL', ' XFAIL'), ('XPASS', ' XPASS')]:
                if keyword in stripped:
                    if st == 'ERROR' and '[ERROR]' in stripped:
                        continue
                    status = st
                    test_id = stripped.split(keyword)[0].strip()
                    break

        # Standalone SKIPPED: pytest выводит "SKIPPED (reason)  [XX%]" без пути
        if not status and stripped.startswith('SKIPPED (') and re.search(r'\[\s*\d+%\]', stripped):
            status = 'SKIPPED'
            test_id = current_file or 'unknown'

        if not status or not test_id:
            continue

        current += 1

        # Обновить глобальный счётчик
        if global_state:
            global_state['current'] += 1

        # Определяем файл
        file_part = test_id.split('::')[0] if '::' in test_id else test_id
        test_part = '::'.join(test_id.split('::')[1:]) if '::' in test_id else test_id

        # Новый файл — вывести заголовок
        new_file = file_part != current_file
        if new_file:
            current_file = file_part
            if file_part not in file_stats:
                file_stats[file_part] = {'passed': 0, 'failed': 0, 'skipped': 0, 'errors': 0}

        # Иконка результата
        if status == 'PASSED':
            icon = f"{C.G}v{C._}"
            passed += 1
            file_stats[file_part]['passed'] += 1
            if global_state:
                global_state['passed'] += 1
        elif status == 'FAILED':
            icon = f"{C.R}x{C._}"
            failed += 1
            file_stats[file_part]['failed'] += 1
            if global_state:
                global_state['failed'] += 1
        elif status in ('SKIPPED', 'XFAIL'):
            icon = f"{C.Y}S{C._}"
            skipped += 1
            file_stats[file_part]['skipped'] += 1
            if global_state:
                global_state['skipped'] += 1
        elif status == 'ERROR':
            icon = f"{C.R}E{C._}"
            errors += 1
            file_stats[file_part]['errors'] += 1
            if global_state:
                global_state['errors'] += 1
        elif status == 'XPASS':
            icon = f"{C.G}v{C._}"
            passed += 1
            file_stats[file_part]['passed'] += 1
            if global_state:
                global_state['passed'] += 1

        test_results.append((test_id, status))

        # Короткое имя теста
        short_test = test_part.split('::')[-1] if '::' in test_part else test_part
        short_test = re.sub(r'\[.*?\]$', '', short_test)

        # --- РЕНДЕРИНГ ---
        # 1. Стереть старые прогрессбары
        if bars_drawn:
            _erase_bars(has_global)

        # 2. Заголовок файла (если новый)
        if new_file:
            short_file = file_part.replace('tests/', '')
            print(f"  {C.D}  {short_file}{C._}")

        # 3. Результат теста с нумерацией
        num_str = f"{C.D}{current}/{total}{C._}"
        print(f"    {icon} {num_str} {short_test}")

        # 4. Нарисовать прогрессбары (suite + global)
        elapsed = time.time() - start_time
        _draw_bars(label, current, total, passed, failed, skipped, elapsed, global_state)
        bars_drawn = True

    process.wait()
    elapsed = time.time() - start_time

    # Стереть промежуточные бары, нарисовать финальные (100%)
    if bars_drawn:
        _erase_bars(has_global)

    # Финальный бар группы (100%)
    bar = _make_bar(total, total)
    sys.stdout.write(
        f"  {C.CY}{label:12s}{C._} [{bar}] 100.0% ({total}/{total})  "
        f"{C.G}{passed}v{C._} {C.R}{failed}x{C._} {C.Y}{skipped}S{C._}  "
        f"{_fmt_time(elapsed)}\033[K\n"
    )
    # Финальный глобальный бар
    if has_global:
        g = global_state
        g_elapsed = time.time() - g['start_time']
        g_bar = _make_bar(g['current'], g['total'])
        g_pct = g['current'] / max(g['total'], 1) * 100
        sys.stdout.write(
            f"  {C.B}{'TOTAL':12s}{C._} [{g_bar}] {g_pct:5.1f}% ({g['current']}/{g['total']})  "
            f"{C.G}{g['passed']}v{C._} {C.R}{g['failed']}x{C._} {C.Y}{g['skipped']}S{C._}  "
            f"{_fmt_time(g_elapsed)}\033[K\n"
        )
    sys.stdout.flush()

    # Файлы — итоги
    if file_stats:
        print(f"  {C.D}  {'─' * 45}{C._}")
        for fp, st in file_stats.items():
            short = fp.replace('tests/', '')
            if st['failed'] > 0 or st['errors'] > 0:
                ficon = f"{C.R}x{C._}"
            elif st['skipped'] > 0 and st['passed'] == 0:
                ficon = f"{C.Y}S{C._}"
            else:
                ficon = f"{C.G}v{C._}"
            parts = []
            if st['passed']:
                parts.append(f"{C.G}{st['passed']}v{C._}")
            if st['failed']:
                parts.append(f"{C.R}{st['failed']}x{C._}")
            if st['errors']:
                parts.append(f"{C.R}{st['errors']}E{C._}")
            if st['skipped']:
                parts.append(f"{C.Y}{st['skipped']}S{C._}")
            print(f"  {ficon} {short:40s} {' '.join(parts)}")

    # Итог группы
    if failed == 0 and errors == 0:
        badge = f"{C.BG_G}{C.W} PASS {C._}"
    else:
        badge = f"{C.BG_R}{C.W} FAIL {C._}"
    print(f"\n  {badge} {label}: "
          f"{C.G}{passed} passed{C._}, "
          f"{C.R}{failed} failed{C._}, "
          f"{C.Y}{skipped} skipped{C._} "
          f"in {_fmt_time(elapsed)}")

    # Записать лог
    with open(log_file, 'w', encoding='utf-8') as f:
        f.writelines(log_lines)

    return {
        'passed': passed, 'failed': failed, 'errors': errors, 'skipped': skipped,
        'total': total, 'duration': elapsed, 'test_results': test_results
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

    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    run_all = len(args) == 0

    # Локальные тесты (без сервера)
    LOCAL_SUITES = {
        'client':       ('Client',       'tests/client/'),
        'ui':           ('UI',           'tests/ui/'),
        'db':           ('DB',           'tests/db/'),
        'api_client':   ('API Client',   'tests/api_client/'),
        'anti_pattern': ('AntiPattern',  'tests/anti_pattern/'),
        'property':     ('Property',     'tests/property/'),
        'regression':   ('Regression',   'tests/regression/'),
        'ui_real':      ('UI Real',      'tests/ui_real/'),
        'visual':       ('Visual',       'tests/visual/'),
        'edge_cases':   ('Edge Cases',   'tests/edge_cases/'),
        'frontend':     ('Frontend',     'tests/frontend/'),
        'integration':  ('Integration',  'tests/integration/'),
    }
    # Серверные тесты (нужен сервер)
    SERVER_SUITES = {
        'backend':     ('Backend',     'tests/backend/'),
        'e2e':         ('E2E',         'tests/e2e/'),
        'smoke':       ('Smoke',       'tests/smoke/'),
        'contract':    ('Contract',    'tests/contract/'),
        'fuzz':        ('Fuzz',        'tests/fuzz/'),
        'pywinauto':   ('PyWinAuto',   'tests/pywinauto/'),
    }

    run_server = '--server' in sys.argv
    run_everything = '--all' in sys.argv
    has_flags = run_server or run_everything or use_coverage

    suites = []
    if run_everything:
        for key, (label, path) in {**LOCAL_SUITES, **SERVER_SUITES}.items():
            if Path(path).exists():
                suites.append((key, label, path))
    elif run_server:
        for key, (label, path) in SERVER_SUITES.items():
            if Path(path).exists():
                suites.append((key, label, path))
    elif run_all and not has_flags and sys.stdin.isatty():
        selected = interactive_menu(LOCAL_SUITES, SERVER_SUITES)
        if selected is None:
            print(f"\n  {C.D}Отменено.{C._}\n")
            return 0
        for key, label, path in selected:
            suites.append((key, label, path))
    elif run_all:
        for key, (label, path) in LOCAL_SUITES.items():
            if Path(path).exists():
                suites.append((key, label, path))
    else:
        all_suites = {**LOCAL_SUITES, **SERVER_SUITES}
        for arg in args:
            if arg in all_suites:
                label, path = all_suites[arg]
                suites.append((arg, label, path))

    # Заголовок
    _clear()
    print()
    print(f"  {C.CY}{'═' * 60}{C._}")
    print(f"  {C.B}  Interior Studio CRM — Test Runner{C._}")
    print(f"  {C.CY}{'═' * 60}{C._}")
    print(f"  {C.D}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{C._}")
    print(f"  {C.D}Групп: {len(suites)}{C._}")

    # Предварительный сбор количества тестов для глобального прогресса
    if len(suites) > 1:
        print(f"\n  {C.D}Подсчёт тестов...{C._}", end='', flush=True)
        suite_counts = {}
        for key, label, test_dir in suites:
            cnt = collect_test_count(venv_python, test_dir)
            suite_counts[key] = cnt
        grand_total = sum(suite_counts.values())
        sys.stdout.write(f"\r  {C.D}Всего тестов: {C.B}{grand_total}{C._}                    \n")
        sys.stdout.flush()
    else:
        suite_counts = {}
        grand_total = 0

    # Глобальное состояние прогресса
    global_state = {
        'total': grand_total,
        'current': 0,
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'errors': 0,
        'start_time': time.time(),
    } if grand_total > 0 else None

    results = {}
    total_time = time.time()

    for key, label, test_dir in suites:
        log_file = str(log_dir / f'{key}_{ts}.log')
        results[label] = run_suite_live(
            venv_python, test_dir, label, log_file,
            global_state=global_state
        )

    total_elapsed = time.time() - total_time

    # ===== ИТОГОВАЯ ТАБЛИЦА =====
    print()
    print(f"  {C.CY}{'═' * 60}{C._}")
    print(f"  {C.B}  ИТОГО{C._}")
    print(f"  {C.CY}{'═' * 60}{C._}")

    total_passed = sum(r['passed'] for r in results.values())
    total_failed = sum(r['failed'] for r in results.values())
    total_errors = sum(r['errors'] for r in results.values())
    total_skipped = sum(r.get('skipped', 0) for r in results.values())
    total_tests = sum(r['total'] for r in results.values())

    for label, r in results.items():
        suite_ok = r['failed'] == 0 and r['errors'] == 0
        icon = f"{C.G}v{C._}" if suite_ok else f"{C.R}x{C._}"
        parts = [f"{C.G}{r['passed']}v{C._}"]
        if r['failed']:
            parts.append(f"{C.R}{r['failed']}x{C._}")
        if r['errors']:
            parts.append(f"{C.R}{r['errors']}E{C._}")
        if r.get('skipped', 0):
            parts.append(f"{C.Y}{r.get('skipped', 0)}S{C._}")
        stats_str = ' '.join(parts)
        print(f"  {icon} {label:12s}  {r['total']:4d} tests  {stats_str}  {C.D}{_fmt_time(r['duration'])}{C._}")

    print(f"  {C.D}{'─' * 60}{C._}")

    all_ok = total_failed == 0 and total_errors == 0
    if all_ok:
        final = f"{C.BG_G}{C.W} ALL PASS {C._}"
    else:
        final = f"{C.BG_R}{C.W} HAS FAILURES {C._}"
    print(f"  {final}  {total_tests} tests: "
          f"{C.G}{total_passed}v{C._} "
          f"{C.R}{total_failed}x{C._} "
          f"{C.Y}{total_skipped}S{C._}  "
          f"in {_fmt_time(total_elapsed)}")

    # Показать упавшие тесты
    all_failed = []
    for label, r in results.items():
        for test_id, status in r.get('test_results', []):
            if status in ('FAILED', 'ERROR'):
                all_failed.append((label, test_id))

    if all_failed:
        print()
        print(f"  {C.R}{C.B}FAILURES:{C._}")
        for label, test_id in all_failed:
            print(f"  {C.R}x{C._} [{label}] {test_id}")

    # JSON summary
    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_tests': total_tests,
        'passed': total_passed,
        'failed': total_failed,
        'errors': total_errors,
        'skipped': total_skipped,
        'duration_seconds': round(total_elapsed, 1),
        'all_pass': all_ok,
        'suites': {k: {kk: vv for kk, vv in v.items() if kk != 'test_results'}
                   for k, v in results.items()},
    }
    summary_file = str(log_dir / f'summary_{ts}.json')
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n  {C.D}Логи: {log_dir}/{C._}")
    print(f"  {C.D}Summary: {summary_file}{C._}")
    print()

    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
