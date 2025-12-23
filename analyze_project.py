#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Комплексный анализ всех файлов проекта Interior Studio CRM
"""
import os
import re
from pathlib import Path
from collections import defaultdict

# Директория проекта
PROJECT_ROOT = r'd:\New CRM\interior_studio'

# Файлы для проверки (исключаем backup и database/database)
EXCLUDE_DIRS = {
    'database_backup_20251125_102227',
    'database/database',
    '__pycache__',
    'build',
    'logs'
}

class ProjectAnalyzer:
    def __init__(self, root_path):
        self.root = Path(root_path)
        self.results = defaultdict(list)
        self.stats = {
            'total_files': 0,
            'total_lines': 0,
            'bare_except': 0,
            'print_statements': 0,
            'debug_functions': 0,
            'syntax_errors': 0,
            'unused_imports': 0
        }
    
    def should_exclude(self, path_str):
        """Проверить, нужно ли исключить файл"""
        for exclude in EXCLUDE_DIRS:
            if exclude in path_str:
                return True
        return False
    
    def analyze_all_files(self):
        """Анализировать все Python файлы"""
        print("🔍 Анализирую все файлы проекта...")
        print("=" * 70)
        
        py_files = list(self.root.rglob('*.py'))
        
        for py_file in py_files:
            if self.should_exclude(str(py_file)):
                continue
            
            self.analyze_file(py_file)
        
        return self.results, self.stats
    
    def analyze_file(self, file_path):
        """Анализировать один файл"""
        rel_path = file_path.relative_to(self.root)
        try:
            # Пробуем разные кодировки
            encodings = ['utf-8', 'utf-8-sig', 'cp1251', 'latin-1']
            content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            
            if content is None:
                self.results['errors'].append({
                    'file': str(rel_path),
                    'error': 'Не удалось декодировать файл'
                })
                return
            
            lines = content.split('\n')
            
            rel_path = file_path.relative_to(self.root)
            self.stats['total_files'] += 1
            self.stats['total_lines'] += len(lines)
            
            # Проверить bare except
            bare_except_matches = re.findall(r'^\s*except\s*:\s*$', content, re.MULTILINE)
            if bare_except_matches:
                self.stats['bare_except'] += len(bare_except_matches)
                self.results['bare_except'].append({
                    'file': str(rel_path),
                    'count': len(bare_except_matches)
                })
            
            # Проверить print в UI файлах (где их быть не должно)
            if 'ui/' in str(rel_path) and 'test_' not in str(rel_path):
                print_matches = re.findall(r'\bprint\s*\(', content)
                if print_matches:
                    self.stats['print_statements'] += len(print_matches)
                    self.results['print_ui'].append({
                        'file': str(rel_path),
                        'count': len(print_matches)
                    })
            
            # Проверить debug функции
            debug_matches = re.findall(r'\.debug_\w+\(|def debug_\w+', content)
            if debug_matches:
                self.stats['debug_functions'] += len(debug_matches)
                self.results['debug_functions'].append({
                    'file': str(rel_path),
                    'count': len(debug_matches)
                })
            
        except Exception as e:
            self.results['errors'].append({
                'file': str(rel_path),
                'error': str(e)
            })
    
    def print_report(self):
        """Вывести отчет"""
        print("\n")
        print("╔" + "=" * 68 + "╗")
        print("║" + " ПОЛНЫЙ ОТЧЕТ ПРОВЕРКИ ПРОЕКТА ".center(68) + "║")
        print("╚" + "=" * 68 + "╝")
        
        print("\n📊 СТАТИСТИКА:")
        print(f"  • Проверено файлов: {self.stats['total_files']}")
        print(f"  • Всего строк кода: {self.stats['total_lines']:,}")
        
        print("\n🔴 НАЙДЕННЫЕ ПРОБЛЕМЫ:")
        print(f"  • Bare except блоки: {self.stats['bare_except']}")
        if self.results['bare_except']:
            for item in self.results['bare_except']:
                print(f"    - {item['file']}: {item['count']}")
        
        print(f"  • Print в UI файлах: {self.stats['print_statements']}")
        if self.results.get('print_ui'):
            for item in self.results['print_ui'][:5]:
                print(f"    - {item['file']}: {item['count']}")
        
        print(f"  • Debug функции: {self.stats['debug_functions']}")
        if self.results['debug_functions']:
            for item in self.results['debug_functions'][:5]:
                print(f"    - {item['file']}: {item['count']}")
        
        print("\n✅ ФАЙЛЫ БЕЗ ПРОБЛЕМ:")
        total_py_files = self.stats['total_files']
        problem_files = len(self.results['bare_except']) + len(self.results.get('print_ui', [])) + len(self.results['debug_functions'])
        print(f"  • {total_py_files - problem_files} файлов без проблем")
        
        print("\n" + "=" * 70)

# Запустить анализ
analyzer = ProjectAnalyzer(PROJECT_ROOT)
results, stats = analyzer.analyze_all_files()
analyzer.print_report()
