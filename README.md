# Interior Studio CRM

Многопользовательская CRM-система для управления студией интерьеров.

## Возможности

- Управление клиентами и договорами
- CRM с Kanban-досками (drag & drop)
- Авторский надзор
- Расчет и учет зарплат
- Генерация отчетов и PDF
- Интеграция с Яндекс.Диском
- Разграничение прав доступа по ролям
- Offline режим с синхронизацией

## Технологии

- **Python 3.14** + **PyQt5** -- десктоп клиент
- **FastAPI** + **PostgreSQL** -- сервер
- **PyInstaller** -- сборка exe
- **SQLite** -- локальная БД (fallback)
- **Docker** -- деплой сервера

## Запуск

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск клиента
.venv\Scripts\python.exe main.py
```

## Сборка exe

```bash
.venv\Scripts\pyinstaller.exe InteriorStudio.spec --clean --noconfirm
```

## Документация

Полная техническая документация: [.claude/CLAUDE.md](.claude/CLAUDE.md)
