#!/usr/bin/env python3
"""
Автоматический сканер багов Interior Studio CRM.

Ищет известные паттерны багов в UI-файлах:
1. Прямой SQL вместо DataAccess (потеря данных в online-режиме)
2. NoneType crash (итерация по None без or [])
3. CustomMessageBox 'question' вместо CustomQuestionBox
4. Отсутствие offline-очереди в DataAccess
5. Утечка сигналов Qt в showEvent
6. prefer_local обход API
7. f-string SQL injection
8. DatabaseManager() в фоновых потоках

Использование:
    python scripts/bug_scanner.py                # Полный скан ui/
    python scripts/bug_scanner.py ui/crm_tab.py  # Скан конкретного файла
    python scripts/bug_scanner.py --category sql  # Только SQL паттерны
"""

import re
import sys
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class BugCandidate:
    file: str
    line: int
    category: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    pattern: str
    context: str
    description: str


class BugScanner:
    """Сканер паттернов багов в кодовой базе."""

    CATEGORIES = {
        'sql': 'Прямой SQL вместо DataAccess',
        'nonetype': 'NoneType crash (итерация по None)',
        'question': 'CustomMessageBox question вместо CustomQuestionBox',
        'offline': 'Отсутствие offline-очереди',
        'signals': 'Утечка сигналов Qt',
        'prefer_local': 'prefer_local обход API',
        'injection': 'f-string SQL injection',
        'thread_sql': 'DatabaseManager в фоновых потоках',
    }

    def __init__(self, root_dir: str = None):
        self.root_dir = Path(root_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.bugs: List[BugCandidate] = []

    def scan_file(self, filepath: Path, categories: Optional[List[str]] = None):
        """Сканировать один файл на паттерны багов."""
        try:
            content = filepath.read_text(encoding='utf-8')
        except Exception:
            return

        lines = content.split('\n')

        scanners = {
            'sql': self._scan_raw_sql,
            'nonetype': self._scan_nonetype,
            'question': self._scan_question_box,
            'signals': self._scan_signal_leak,
            'prefer_local': self._scan_prefer_local,
            'injection': self._scan_fstring_sql,
            'thread_sql': self._scan_thread_sql,
        }

        for cat, scanner in scanners.items():
            if categories and cat not in categories:
                continue
            scanner(filepath, lines)

    def scan_directory(self, directory: str = 'ui', categories: Optional[List[str]] = None):
        """Сканировать директорию."""
        dir_path = self.root_dir / directory
        if not dir_path.exists():
            print(f"Директория {dir_path} не найдена")
            return

        for py_file in sorted(dir_path.glob('*.py')):
            if py_file.name.startswith('__'):
                continue
            self.scan_file(py_file, categories)

    def scan_data_access(self):
        """Проверить DataAccess на отсутствие offline-очереди."""
        da_path = self.root_dir / 'utils' / 'data_access.py'
        if not da_path.exists():
            return

        content = da_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Ищем мутирующие методы без _queue_operation
        in_method = False
        method_name = ''
        method_start = 0
        method_has_queue = False
        method_has_cache_invalidate = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Начало нового метода
            match = re.match(r'\s+def (create_|update_|delete_)(\w+)\(', line)
            if match:
                # Проверяем предыдущий метод
                if in_method and not method_has_queue:
                    self.bugs.append(BugCandidate(
                        file=str(da_path.relative_to(self.root_dir)),
                        line=method_start + 1,
                        category='offline',
                        severity='HIGH',
                        pattern=f'def {method_name}() без _queue_operation',
                        context=lines[method_start],
                        description=f'Метод {method_name} не имеет offline-очереди. '
                                    f'При потере сети изменения будут потеряны.'
                    ))

                in_method = True
                method_name = match.group(1) + match.group(2)
                method_start = i
                method_has_queue = False
                method_has_cache_invalidate = False
                continue

            if in_method:
                if '_queue_operation' in stripped:
                    method_has_queue = True
                if '_global_cache.invalidate' in stripped:
                    method_has_cache_invalidate = True
                # Конец метода — следующий def на том же уровне
                if re.match(r'\s+def \w+\(', line) and not re.match(r'\s+def (create_|update_|delete_)', line):
                    if not method_has_queue:
                        self.bugs.append(BugCandidate(
                            file=str(da_path.relative_to(self.root_dir)),
                            line=method_start + 1,
                            category='offline',
                            severity='HIGH',
                            pattern=f'def {method_name}() без _queue_operation',
                            context=lines[method_start].strip(),
                            description=f'Метод {method_name} не имеет offline-очереди.'
                        ))
                    in_method = False

    def _scan_raw_sql(self, filepath: Path, lines: List[str]):
        """Ищем прямой SQL в UI файлах."""
        patterns = [
            (r'cursor\.execute\(', 'cursor.execute()'),
            (r'execute_raw_query\(', 'execute_raw_query()'),
            (r'execute_raw_update\(', 'execute_raw_update()'),
            (r'\.db\.connect\(\)', '.db.connect()'),
        ]
        rel_path = str(filepath.relative_to(self.root_dir))

        for i, line in enumerate(lines):
            for pattern, name in patterns:
                if re.search(pattern, line):
                    # Проверяем контекст — комментарий или строка?
                    stripped = line.strip()
                    if stripped.startswith('#') or stripped.startswith('"""'):
                        continue

                    self.bugs.append(BugCandidate(
                        file=rel_path,
                        line=i + 1,
                        category='sql',
                        severity='CRITICAL',
                        pattern=name,
                        context=stripped[:120],
                        description=f'Прямой SQL вместо DataAccess. В online-режиме '
                                    f'изменения не попадут на сервер.'
                    ))

    def _scan_nonetype(self, filepath: Path, lines: List[str]):
        """Ищем итерацию по результату DataAccess без or []."""
        rel_path = str(filepath.relative_to(self.root_dir))
        pattern = re.compile(r'for\s+\w+\s+in\s+self\.data\.\w+\(')

        for i, line in enumerate(lines):
            if pattern.search(line):
                stripped = line.strip()
                if stripped.startswith('#'):
                    continue
                # Проверяем наличие "or []" или "or {}"
                if 'or []' not in line and 'or {}' not in line:
                    # Проверяем предыдущую строку на присвоение с or []
                    prev = lines[i - 1].strip() if i > 0 else ''
                    if 'or []' not in prev:
                        self.bugs.append(BugCandidate(
                            file=rel_path,
                            line=i + 1,
                            category='nonetype',
                            severity='HIGH',
                            pattern='for x in self.data.method() без or []',
                            context=stripped[:120],
                            description='Если DataAccess вернёт None, произойдёт TypeError: '
                                        'cannot iterate over NoneType.'
                        ))

    def _scan_question_box(self, filepath: Path, lines: List[str]):
        """Ищем CustomMessageBox с типом 'question'."""
        rel_path = str(filepath.relative_to(self.root_dir))

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            if "CustomMessageBox" in line and "'question'" in line:
                self.bugs.append(BugCandidate(
                    file=rel_path,
                    line=i + 1,
                    category='question',
                    severity='MEDIUM',
                    pattern="CustomMessageBox(..., 'question')",
                    context=stripped[:120],
                    description='CustomMessageBox не поддерживает тип question. '
                                'Используйте CustomQuestionBox для подтверждений.'
                ))

            if 'QMessageBox.Yes' in line and 'import' not in line:
                self.bugs.append(BugCandidate(
                    file=rel_path,
                    line=i + 1,
                    category='question',
                    severity='MEDIUM',
                    pattern='QMessageBox.Yes (16384)',
                    context=stripped[:120],
                    description='Сравнение с QMessageBox.Yes (16384). '
                                'CustomQuestionBox возвращает QDialog.Accepted (1).'
                ))

    def _scan_signal_leak(self, filepath: Path, lines: List[str]):
        """Ищем .connect() внутри showEvent без guard."""
        rel_path = str(filepath.relative_to(self.root_dir))
        in_show_event = False
        show_event_indent = 0

        for i, line in enumerate(lines):
            stripped = line.strip()

            if 'def showEvent' in line:
                in_show_event = True
                show_event_indent = len(line) - len(line.lstrip())
                continue

            if in_show_event:
                current_indent = len(line) - len(line.lstrip()) if stripped else show_event_indent + 4
                if stripped and current_indent <= show_event_indent and 'def ' not in line:
                    pass  # Пустая строка или продолжение
                if stripped and current_indent <= show_event_indent and stripped.startswith('def '):
                    in_show_event = False
                    continue

                if '.connect(' in line and '_signals_connected' not in line and '_centered' not in line:
                    # Проверяем есть ли guard
                    has_guard = False
                    for j in range(max(0, i - 5), i):
                        if '_signals_connected' in lines[j] or '_connected' in lines[j]:
                            has_guard = True
                            break
                    if not has_guard:
                        self.bugs.append(BugCandidate(
                            file=rel_path,
                            line=i + 1,
                            category='signals',
                            severity='MEDIUM',
                            pattern='.connect() в showEvent без guard',
                            context=stripped[:120],
                            description='Сигнал подключается при каждом showEvent. '
                                        'При повторных открытиях обработчик вызовется N раз.'
                        ))

    def _scan_prefer_local(self, filepath: Path, lines: List[str]):
        """Ищем prefer_local = True."""
        rel_path = str(filepath.relative_to(self.root_dir))

        for i, line in enumerate(lines):
            if 'prefer_local' in line and '= True' in line:
                stripped = line.strip()
                if stripped.startswith('#'):
                    continue
                self.bugs.append(BugCandidate(
                    file=rel_path,
                    line=i + 1,
                    category='prefer_local',
                    severity='MEDIUM',
                    pattern='prefer_local = True',
                    context=stripped[:120],
                    description='Принудительное чтение из локальной SQLite. '
                                'Пользователь не видит актуальные данные с сервера.'
                ))

    def _scan_fstring_sql(self, filepath: Path, lines: List[str]):
        """Ищем f-string SQL injection."""
        rel_path = str(filepath.relative_to(self.root_dir))
        pattern = re.compile(r"""f['"](.*?(UPDATE|INSERT|DELETE|SELECT).*?\{)""")

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            if pattern.search(line):
                self.bugs.append(BugCandidate(
                    file=rel_path,
                    line=i + 1,
                    category='injection',
                    severity='CRITICAL',
                    pattern='f-string SQL',
                    context=stripped[:120],
                    description='SQL-запрос с f-string подстановкой. '
                                'Используйте параметризованные запросы (?, %s).'
                ))

    def _scan_thread_sql(self, filepath: Path, lines: List[str]):
        """Ищем DatabaseManager() в UI файлах."""
        rel_path = str(filepath.relative_to(self.root_dir))

        for i, line in enumerate(lines):
            if 'DatabaseManager()' in line:
                stripped = line.strip()
                if stripped.startswith('#') or stripped.startswith('from'):
                    continue
                self.bugs.append(BugCandidate(
                    file=rel_path,
                    line=i + 1,
                    category='thread_sql',
                    severity='CRITICAL',
                    pattern='DatabaseManager() в UI',
                    context=stripped[:120],
                    description='Создание нового DatabaseManager в UI. '
                                'Потоконебезопасно, дублирует DataAccess.'
                ))

    def report(self) -> str:
        """Генерация отчёта."""
        if not self.bugs:
            return "Потенциальных багов не найдено."

        # Сортируем по серьёзности
        severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        self.bugs.sort(key=lambda b: (severity_order.get(b.severity, 9), b.file, b.line))

        lines = []
        lines.append(f"{'='*70}")
        lines.append(f"ОТЧЁТ СКАНЕРА БАГОВ — Interior Studio CRM")
        lines.append(f"{'='*70}")
        lines.append(f"")
        lines.append(f"Найдено потенциальных багов: {len(self.bugs)}")
        lines.append(f"")

        # Статистика по категориям
        from collections import Counter
        by_cat = Counter(b.category for b in self.bugs)
        by_sev = Counter(b.severity for b in self.bugs)

        lines.append("По серьёзности:")
        for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            if sev in by_sev:
                lines.append(f"  {sev}: {by_sev[sev]}")

        lines.append("")
        lines.append("По категориям:")
        for cat, count in by_cat.most_common():
            lines.append(f"  {cat} ({self.CATEGORIES.get(cat, '?')}): {count}")

        lines.append(f"\n{'='*70}\n")

        # Детали
        for i, bug in enumerate(self.bugs, 1):
            lines.append(f"[{bug.severity}] #{i}: {bug.description}")
            lines.append(f"  Файл: {bug.file}:{bug.line}")
            lines.append(f"  Паттерн: {bug.pattern}")
            lines.append(f"  Код: {bug.context}")
            lines.append("")

        # Таблица
        lines.append(f"{'='*70}")
        lines.append(f"{'#':<4} {'Серьёзность':<12} {'Файл:строка':<45} {'Паттерн'}")
        lines.append(f"{'-'*4} {'-'*12} {'-'*45} {'-'*30}")
        for i, bug in enumerate(self.bugs, 1):
            loc = f"{bug.file}:{bug.line}"
            lines.append(f"{i:<4} {bug.severity:<12} {loc:<45} {bug.pattern}")

        return '\n'.join(lines)


def main():
    scanner = BugScanner()

    # Парсим аргументы
    categories = None
    targets = []

    for arg in sys.argv[1:]:
        if arg.startswith('--category='):
            categories = [arg.split('=')[1]]
        elif arg.startswith('--'):
            pass
        else:
            targets.append(arg)

    if not targets:
        # Полный скан
        print("Сканирование ui/ ...")
        scanner.scan_directory('ui', categories)
        print("Сканирование utils/data_access.py ...")
        scanner.scan_data_access()
    else:
        for target in targets:
            path = Path(target)
            if path.is_dir():
                scanner.scan_directory(str(path.relative_to(scanner.root_dir)), categories)
            elif path.is_file():
                scanner.scan_file(path, categories)
            else:
                # Попробуем как относительный путь
                full_path = scanner.root_dir / target
                if full_path.is_file():
                    scanner.scan_file(full_path, categories)
                elif full_path.is_dir():
                    scanner.scan_directory(target, categories)
                else:
                    print(f"Не найдено: {target}")

    print(scanner.report())
    return len([b for b in scanner.bugs if b.severity == 'CRITICAL'])


if __name__ == '__main__':
    sys.exit(main())
