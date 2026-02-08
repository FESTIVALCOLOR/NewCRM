# Interior Studio CRM -- Copilot Instructions

Полная документация проекта: `.claude/CLAUDE.md`

## Ключевые правила

1. **Никогда не используй emoji в UI** -- только SVG иконки через IconLoader
2. **resource_path()** для всех ресурсов (иначе не работает в exe)
3. **__init__.py обязательны** в database/, ui/, utils/
4. **Двухрежимная архитектура**: поддерживай MULTI_USER_MODE True и False
5. **Frameless окна** + CustomTitleBar везде
6. **Рамки диалогов**: строго `border: 1px solid #E0E0E0`
7. **Endpoints**: статические пути ПЕРЕД динамическими в FastAPI
8. **Кодировка**: `# -*- coding: utf-8 -*-`, все строки UI на русском

## Стек

- PyQt5 Desktop клиент + FastAPI сервер + PostgreSQL
- Python 3.14.0 (клиент), 3.11 (сервер)
- PyInstaller для сборки exe
- SQLite как fallback/offline БД
