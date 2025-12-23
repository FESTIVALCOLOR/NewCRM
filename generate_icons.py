"""
Генератор минималистичных SVG иконок для Festival Color
Запустите: python generate_icons_svg.py
"""

import os

# Создаем папку для иконок
ICONS_DIR = 'resources/icons'
os.makedirs(ICONS_DIR, exist_ok=True)

# Цвета
COLOR_DARK = '#333333'
COLOR_RED = '#E74C3C'
COLOR_GREEN = '#27AE60'
COLOR_BLUE = '#3498DB'
COLOR_ORANGE = '#FF9800'
COLOR_GRAY = '#95A5A6'

def save_svg(filename, content):
    """Сохранение SVG файла"""
    with open(f'{ICONS_DIR}/{filename}', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'✓ {filename}')

# ========== ИКОНКИ TITLE BAR ==========

def create_minimize_svg():
    """− (свернуть)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <line x1="6" y1="12" x2="18" y2="12" stroke="{COLOR_DARK}" stroke-width="2" stroke-linecap="round"/>
</svg>'''
    save_svg('minimize.svg', svg)

def create_maximize_svg():
    """□ (развернуть)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <rect x="6" y="6" width="12" height="12" stroke="{COLOR_DARK}" stroke-width="2" fill="none" rx="1"/>
</svg>'''
    save_svg('maximize.svg', svg)

def create_close_svg():
    """× (закрыть)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <line x1="6" y1="6" x2="18" y2="18" stroke="{COLOR_RED}" stroke-width="2" stroke-linecap="round"/>
    <line x1="18" y1="6" x2="6" y2="18" stroke="{COLOR_RED}" stroke-width="2" stroke-linecap="round"/>
</svg>'''
    save_svg('close.svg', svg)

# ========== ИКОНКИ КНОПОК ДЕЙСТВИЙ ==========

def create_search_svg():
    """🔍 (поиск)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <circle cx="10" cy="10" r="6" stroke="{COLOR_BLUE}" stroke-width="2" fill="none"/>
    <line x1="14.5" y1="14.5" x2="19" y2="19" stroke="{COLOR_BLUE}" stroke-width="2" stroke-linecap="round"/>
</svg>'''
    save_svg('search.svg', svg)

def create_add_svg():
    """+ (добавить)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <line x1="12" y1="6" x2="12" y2="18" stroke="{COLOR_GREEN}" stroke-width="2" stroke-linecap="round"/>
    <line x1="6" y1="12" x2="18" y2="12" stroke="{COLOR_GREEN}" stroke-width="2" stroke-linecap="round"/>
</svg>'''
    save_svg('add.svg', svg)

def create_edit_svg():
    """✏ (редактировать)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M 17 3 L 21 7 L 9 19 L 3 21 L 5 15 Z" stroke="{COLOR_ORANGE}" stroke-width="2" fill="none" stroke-linejoin="round"/>
    <line x1="15" y1="5" x2="19" y2="9" stroke="{COLOR_ORANGE}" stroke-width="2"/>
</svg>'''
    save_svg('edit.svg', svg)

def create_delete_svg():
    """🗑 (удалить)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M 5 9 L 19 9 L 18 21 L 6 21 Z" stroke="{COLOR_RED}" stroke-width="2" fill="none"/>
    <line x1="3" y1="6" x2="21" y2="6" stroke="{COLOR_RED}" stroke-width="2" stroke-linecap="round"/>
    <path d="M 9 3 L 15 3 L 15 6 L 9 6 Z" stroke="{COLOR_RED}" stroke-width="2" fill="none"/>
</svg>'''
    save_svg('delete.svg', svg)

def create_view_svg():
    """👁 (просмотр)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M 2 12 Q 2 6, 12 6 Q 22 6, 22 12 Q 22 18, 12 18 Q 2 18, 2 12" stroke="{COLOR_DARK}" stroke-width="2" fill="none"/>
    <circle cx="12" cy="12" r="3" fill="{COLOR_DARK}"/>
</svg>'''
    save_svg('view.svg', svg)

def create_stats_svg():
    """📊 (статистика)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <rect x="4" y="14" width="4" height="6" fill="{COLOR_BLUE}" rx="1"/>
    <rect x="10" y="10" width="4" height="10" fill="{COLOR_BLUE}" rx="1"/>
    <rect x="16" y="6" width="4" height="14" fill="{COLOR_BLUE}" rx="1"/>
</svg>'''
    save_svg('stats.svg', svg)

def create_folder_svg():
    """📁 (папка/данные проекта)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M 4 7 L 4 19 L 20 19 L 20 7 Z" stroke="{COLOR_ORANGE}" stroke-width="2" fill="none"/>
    <path d="M 4 7 L 10 7 L 12 5 L 20 5 L 20 7" stroke="{COLOR_ORANGE}" stroke-width="2" fill="none"/>
</svg>'''
    save_svg('folder.svg', svg)

def create_calendar_svg():
    """📅 (календарь)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <rect x="4" y="6" width="16" height="14" stroke="{COLOR_DARK}" stroke-width="2" fill="none" rx="2"/>
    <line x1="4" y1="10" x2="20" y2="10" stroke="{COLOR_DARK}" stroke-width="2"/>
    <line x1="8" y1="3" x2="8" y2="8" stroke="{COLOR_DARK}" stroke-width="2" stroke-linecap="round"/>
    <line x1="16" y1="3" x2="16" y2="8" stroke="{COLOR_DARK}" stroke-width="2" stroke-linecap="round"/>
</svg>'''
    save_svg('calendar.svg', svg)

def create_accept_svg():
    """✓ (принять/галочка)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <polyline points="5,12 10,17 20,7" stroke="{COLOR_GREEN}" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
</svg>'''
    save_svg('accept.svg', svg)

def create_pause_svg():
    """⏸ (пауза)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <rect x="7" y="5" width="3" height="14" fill="{COLOR_ORANGE}" rx="1"/>
    <rect x="14" y="5" width="3" height="14" fill="{COLOR_ORANGE}" rx="1"/>
</svg>'''
    save_svg('pause.svg', svg)

def create_play_svg():
    """▶ (возобновить)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <polygon points="8,5 8,19 18,12" fill="{COLOR_GREEN}"/>
</svg>'''
    save_svg('play.svg', svg)

def create_history_svg():
    """📖 (история)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <rect x="6" y="4" width="12" height="16" stroke="{COLOR_BLUE}" stroke-width="2" fill="none" rx="1"/>
    <line x1="9" y1="8" x2="15" y2="8" stroke="{COLOR_BLUE}" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="9" y1="12" x2="15" y2="12" stroke="{COLOR_BLUE}" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="9" y1="16" x2="13" y2="16" stroke="{COLOR_BLUE}" stroke-width="1.5" stroke-linecap="round"/>
</svg>'''
    save_svg('history.svg', svg)

def create_note_svg():
    """📝 (заметка/добавить запись)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <rect x="5" y="3" width="14" height="18" stroke="{COLOR_GRAY}" stroke-width="2" fill="none" rx="1"/>
    <line x1="8" y1="8" x2="16" y2="8" stroke="{COLOR_GRAY}" stroke-width="1.5"/>
    <line x1="8" y1="12" x2="16" y2="12" stroke="{COLOR_GRAY}" stroke-width="1.5"/>
    <line x1="8" y1="16" x2="13" y2="16" stroke="{COLOR_GRAY}" stroke-width="1.5"/>
</svg>'''
    save_svg('note.svg', svg)

def create_refresh_svg():
    """🔄 (обновить/сбросить)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M 4 12 A 8 8 0 1 1 12 20" stroke="{COLOR_BLUE}" stroke-width="2" fill="none" stroke-linecap="round"/>
    <polyline points="4,8 4,12 8,12" fill="{COLOR_BLUE}"/>
</svg>'''
    save_svg('refresh.svg', svg)

def create_export_svg():
    """📄 (экспорт)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M 6 4 L 6 20 L 18 20 L 18 8 L 14 4 Z" stroke="{COLOR_RED}" stroke-width="2" fill="none"/>
    <polyline points="14,4 14,8 18,8" stroke="{COLOR_RED}" stroke-width="2" fill="none"/>
    <line x1="9" y1="12" x2="15" y2="12" stroke="{COLOR_RED}" stroke-width="1.5"/>
    <line x1="9" y1="15" x2="15" y2="15" stroke="{COLOR_RED}" stroke-width="1.5"/>
</svg>'''
    save_svg('export.svg', svg)

def create_team_svg():
    """👥 (команда)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <circle cx="9" cy="8" r="3" stroke="{COLOR_DARK}" stroke-width="2" fill="none"/>
    <path d="M 3 20 Q 3 14, 9 14 Q 15 14, 15 20" stroke="{COLOR_DARK}" stroke-width="2" fill="none"/>
    <circle cx="17" cy="9" r="2.5" stroke="{COLOR_DARK}" stroke-width="1.5" fill="none"/>
    <path d="M 20 19 Q 20 15, 17 15 Q 14 15, 14 19" stroke="{COLOR_DARK}" stroke-width="1.5" fill="none"/>
</svg>'''
    save_svg('team.svg', svg)

def create_submit_svg():
    """✓ Сдать работу"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="10" stroke="{COLOR_GREEN}" stroke-width="2" fill="none"/>
    <polyline points="7,12 11,16 17,8" stroke="{COLOR_GREEN}" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
</svg>'''
    save_svg('submit.svg', svg)

def create_waiting_svg():
    """⏳ (ожидание)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="9" stroke="{COLOR_BLUE}" stroke-width="2" fill="none"/>
    <polyline points="12,12 12,6 16,8" stroke="{COLOR_BLUE}" stroke-width="2" fill="none" stroke-linecap="round"/>
</svg>'''
    save_svg('waiting.svg', svg)

def create_deadline_svg():
    """⏰ (дедлайн)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="13" r="8" stroke="{COLOR_RED}" stroke-width="2" fill="none"/>
    <line x1="12" y1="13" x2="12" y2="8" stroke="{COLOR_RED}" stroke-width="2" stroke-linecap="round"/>
    <line x1="12" y1="13" x2="15" y2="15" stroke="{COLOR_RED}" stroke-width="2" stroke-linecap="round"/>
    <line x1="10" y1="3" x2="14" y2="3" stroke="{COLOR_RED}" stroke-width="2" stroke-linecap="round"/>
</svg>'''
    save_svg('deadline.svg', svg)

def create_tag_svg():
    """🏷️ (теги)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M 3 3 L 13 3 L 21 12 L 12 21 L 3 12 Z" stroke="{COLOR_RED}" stroke-width="2" fill="none" stroke-linejoin="round"/>
    <circle cx="8" cy="8" r="1.5" fill="{COLOR_RED}"/>
</svg>'''
    save_svg('tag.svg', svg)

def create_archive_svg():
    """📦 (архив)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <rect x="4" y="7" width="16" height="13" stroke="{COLOR_GRAY}" stroke-width="2" fill="none" rx="1"/>
    <rect x="4" y="4" width="16" height="3" fill="{COLOR_GRAY}"/>
    <rect x="9" y="11" width="6" height="2" fill="{COLOR_GRAY}" rx="1"/>
</svg>'''
    save_svg('archive.svg', svg)

def create_active_svg():
    """📋 (активные)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <rect x="5" y="3" width="14" height="18" stroke="{COLOR_GREEN}" stroke-width="2" fill="none" rx="2"/>
    <line x1="9" y1="8" x2="15" y2="8" stroke="{COLOR_GREEN}" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="9" y1="12" x2="15" y2="12" stroke="{COLOR_GREEN}" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="9" y1="16" x2="13" y2="16" stroke="{COLOR_GREEN}" stroke-width="1.5" stroke-linecap="round"/>
</svg>'''
    save_svg('active.svg', svg)

def create_employee_svg():
    """👤 (сотрудник)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="8" r="4" stroke="{COLOR_DARK}" stroke-width="2" fill="none"/>
    <path d="M 4 20 Q 4 14, 12 14 Q 20 14, 20 20" stroke="{COLOR_DARK}" stroke-width="2" fill="none"/>
</svg>'''
    save_svg('employee.svg', svg)

def create_money_svg():
    """💰 (деньги/зарплата)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="9" stroke="{COLOR_ORANGE}" stroke-width="2" fill="none"/>
    <path d="M 12 6 L 12 8 M 12 8 Q 9 8, 9 11 Q 9 14, 12 14 M 12 14 Q 15 14, 15 17 Q 15 20, 12 20 M 12 18 L 12 20" stroke="{COLOR_ORANGE}" stroke-width="2" fill="none" stroke-linecap="round"/>
</svg>'''
    save_svg('money.svg', svg)

def create_client_svg():
    """👤 (клиент)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="9" r="4" stroke="{COLOR_BLUE}" stroke-width="2" fill="none"/>
    <path d="M 5 20 Q 5 14, 12 14 Q 19 14, 19 20" stroke="{COLOR_BLUE}" stroke-width="2" fill="none"/>
</svg>'''
    save_svg('client.svg', svg)

def create_contract_svg():
    """📄 (договор)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <rect x="6" y="3" width="12" height="18" stroke="{COLOR_DARK}" stroke-width="2" fill="none" rx="1"/>
    <line x1="9" y1="8" x2="15" y2="8" stroke="{COLOR_DARK}" stroke-width="1.5"/>
    <line x1="9" y1="12" x2="15" y2="12" stroke="{COLOR_DARK}" stroke-width="1.5"/>
    <line x1="9" y1="16" x2="13" y2="16" stroke="{COLOR_DARK}" stroke-width="1.5"/>
</svg>'''
    save_svg('contract.svg', svg)

def create_warning_svg():
    """⚠️ (предупреждение)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M 12 3 L 22 20 L 2 20 Z" stroke="{COLOR_ORANGE}" stroke-width="2" fill="none" stroke-linejoin="round"/>
    <line x1="12" y1="10" x2="12" y2="14" stroke="{COLOR_ORANGE}" stroke-width="2" stroke-linecap="round"/>
    <circle cx="12" cy="17" r="1" fill="{COLOR_ORANGE}"/>
</svg>'''
    save_svg('warning.svg', svg)

def create_info_svg():
    """ℹ️ (информация)"""
    svg = f'''<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="9" stroke="{COLOR_BLUE}" stroke-width="2" fill="none"/>
    <line x1="12" y1="11" x2="12" y2="17" stroke="{COLOR_BLUE}" stroke-width="2" stroke-linecap="round"/>
    <circle cx="12" cy="8" r="1" fill="{COLOR_BLUE}"/>
</svg>'''
    save_svg('info.svg', svg)

# ========== ЗАПУСК ГЕНЕРАЦИИ ==========
if __name__ == '__main__':
    print("\n🎨 Генерация минималистичных SVG иконок...")
    print(f"📁 Папка: {ICONS_DIR}\n")
    
    # Title bar
    create_minimize_svg()
    create_maximize_svg()
    create_close_svg()
    
    # Действия
    create_search_svg()
    create_add_svg()
    create_edit_svg()
    create_delete_svg()
    create_view_svg()
    
    # Функции
    create_stats_svg()
    create_folder_svg()
    create_calendar_svg()
    create_accept_svg()
    create_pause_svg()
    create_play_svg()
    create_history_svg()
    create_note_svg()
    create_refresh_svg()
    create_export_svg()
    create_team_svg()
    create_submit_svg()
    create_waiting_svg()
    create_deadline_svg()
    create_tag_svg()
    create_archive_svg()
    create_active_svg()
    create_employee_svg()
    create_money_svg()
    create_client_svg()
    create_contract_svg()
    create_warning_svg()
    create_info_svg()
    
    # Подсчет
    svg_files = [f for f in os.listdir(ICONS_DIR) if f.endswith('.svg')]
    print(f"\n✅ Создано {len(svg_files)} SVG иконок!")
    print(f"📂 Путь: {os.path.abspath(ICONS_DIR)}")
    print("\nСписок иконок:")
    for icon in sorted(svg_files):
        print(f"  • {icon}")
    print()
