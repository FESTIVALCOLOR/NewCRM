# Interior Studio CRM — Документация

> Полная документация по проекту Interior Studio CRM.
> Версия: 1.0 | Дата: 2026-02-14

## Содержание

| # | Документ | Описание | Путь |
|---|----------|----------|------|
| 1 | [Roadmap](01-roadmap.md) | Дорожная карта развития проекта | `docs/01-roadmap.md` |
| 2 | [Правила проекта](02-project-rules.md) | Критические правила, соглашения, стандарты кода | `docs/02-project-rules.md` |
| 3 | [Авторизация](03-auth.md) | Система авторизации, JWT, роли и права доступа | `docs/03-auth.md` |
| 4 | [Бекенд проекта](04-backend.md) | FastAPI сервер, SQLAlchemy модели, Pydantic схемы | `docs/04-backend.md` |
| 5 | [Фронтенд проекта](05-frontend.md) | PyQt5 UI, табы, виджеты, диалоги | `docs/05-frontend.md` |
| 6 | [API и Endpoints](06-api-endpoints.md) | Полный каталог всех 144+ API endpoints | `docs/06-api-endpoints.md` |
| 7 | [Сервер проекта](07-server.md) | Docker, деплой, инфраструктура, мониторинг | `docs/07-server.md` |
| 8 | [Фичи и спеки](08-features-specs.md) | Бизнес-логика, Kanban, платежи, таймлайны | `docs/08-features-specs.md` |
| 9 | [Дизайн и стили](09-design-styles.md) | Unified Styles, QSS, иконки, палитра цветов | `docs/09-design-styles.md` |
| 10 | [UI и Utils](10-ui-utils.md) | Утилиты, хелперы, валидаторы, кэш | `docs/10-ui-utils.md` |
| 11 | [Система оплат](11-payments.md) | Платежи, тарифы, расчёт сумм, переназначение | `docs/11-payments.md` |
| 12 | [Система дедлайнов](12-deadlines.md) | Дедлайны, таймлайны, рабочие дни, workflow | `docs/12-deadlines.md` |
| 13 | [CRM интеграция](13-crm-integration.md) | Kanban, карточки, стадии, исполнители | `docs/13-crm-integration.md` |
| 14 | [CRM надзора](14-crm-supervision.md) | Авторский надзор, закупки, бюджет | `docs/14-crm-supervision.md` |
| 15 | [Тестирование](15-testing.md) | Стратегия тестирования, покрытие, запуск | `docs/15-testing.md` |
| 16 | [AI промпты и правила](16-ai-prompts.md) | Базовые промпты, context compression, правила AI | `docs/16-ai-prompts.md` |
| 17 | [Субагенты](17-subagents.md) | Агенты, модели, инструменты, инструкции | `docs/17-subagents.md` |
| 18 | [Agent Skills](18-agent-skills.md) | Переиспользуемые навыки, шаблоны, автоматизация | `docs/18-agent-skills.md` |
| 19 | [Логи и покрытие](19-logs-coverage.md) | Логирование, мониторинг, отладка | `docs/19-logs-coverage.md` |
| 20 | [UI тесты (pytest-qt)](20-ui-testing.md) | 460 тестов pytest-qt offscreen, 13 модулей, ролевое тестирование | `docs/20-ui-testing.md` |
| 21 | [Безопасность](21-security.md) | SSL, JWT, fail2ban, бэкапы, сетевая защита (~82%) | `docs/21-security.md` |
| 22 | [Оптимизация (Roadmap)](22-optimization-roadmap.md) | 4 фазы: защита данных, UX, архитектура, инфраструктура | `docs/22-optimization-roadmap.md` |

## Быстрые ссылки

- **Запуск клиента:** `.venv\Scripts\python.exe main.py`
- **Запуск тестов:** `pytest tests/ui/ -v --timeout=30` (UI) | `pytest tests/e2e/ tests/db/ -v --timeout=60` (E2E+DB)
- **Деплой сервера:** `ssh timeweb` → `cd /opt/interior_studio` → `docker-compose down && docker-compose build --no-cache api && docker-compose up -d`
- **Сборка exe:** `.venv\Scripts\pyinstaller.exe InteriorStudio.spec --clean --noconfirm`

---

## Полная структура проекта

> **104 537 строк** Python-кода | **307 файлов** | **10 AI агентов** | **82 файла тестов**

```
interior_studio/                       # Корень проекта
│
├── main.py                            # 188 строк — Точка входа клиента (PyQt5)
├── config.py                          # 163 строк — Конфигурация (API URL, роли, константы)
├── migrate_to_server.py               # 471 строк — Утилита миграции SQLite → PostgreSQL
├── docker-compose.yml                 # Docker orchestration (PostgreSQL + API + Nginx)
├── pytest.ini                         # Конфигурация pytest (маркеры, таймауты)
├── InteriorStudio.spec                # PyInstaller спецификация для сборки exe
├── requirements.txt                   # Зависимости клиента
├── requirements-dev.txt               # Dev/test зависимости (pytest, pytest-qt)
├── deploy.sh                          # Скрипт развёртывания на VPS
├── full_deploy.sh                     # Полное развёртывание с бэкапом
├── initial_setup.sh                   # Начальная настройка VPS
├── finalize_setup.sh                  # Финализация установки
├── README.md                          # Краткое описание проекта
├── token.txt                          # JWT токен для разработки
│
├── .claude/                           # === Конфигурация Claude Code ===
│   ├── CLAUDE.md                      # Описание проекта (ссылка на docs/)
│   ├── config.json                    # API ключи
│   ├── settings.local.json            # Локальные настройки (permissions, hooks, model)
│   │
│   └── agents/                        # 10 AI агентов
│       ├── api-client-agent.md        # REST клиент, offline, sync
│       ├── backend-agent.md           # FastAPI endpoints, SQLAlchemy
│       ├── bug-fixer-agent.md         # Отладка через Playwright + Context7
│       ├── compatibility-checker.md   # Проверка совместимости server↔client
│       ├── database-agent.md          # SQLite, миграции, индексы
│       ├── deploy-agent.md            # Docker деплой, откат, мониторинг
│       ├── design-stylist-agent.md    # QSS стили, цвета, дизайн
│       ├── frontend-agent.md          # PyQt5 UI, виджеты, диалоги
│       ├── fullstack-agent.md         # Координация server + API + UI
│       └── test-agent.md             # pytest, валидация, покрытие
│
├── docs/                              # === Документация (20 файлов) ===
│   ├── Index.md                       # Этот файл — оглавление
│   ├── 01-roadmap.md                  # Дорожная карта
│   ├── 02-project-rules.md            # Правила проекта
│   ├── 03-auth.md                     # JWT авторизация, роли
│   ├── 04-backend.md                  # FastAPI, SQLAlchemy модели
│   ├── 05-frontend.md                 # PyQt5 UI компоненты
│   ├── 06-api-endpoints.md            # Каталог 144+ endpoints
│   ├── 07-server.md                   # Docker, деплой, VPS
│   ├── 08-features-specs.md           # Бизнес-логика, Kanban, workflow
│   ├── 09-design-styles.md            # Стили, QSS, палитра, иконки
│   ├── 10-ui-utils.md                 # Утилиты и хелперы
│   ├── 11-payments.md                 # Платежи, тарифы
│   ├── 12-deadlines.md                # Дедлайны, таймлайны
│   ├── 13-crm-integration.md          # CRM Kanban интеграция
│   ├── 14-crm-supervision.md          # Авторский надзор
│   ├── 15-testing.md                  # Тестирование, покрытие
│   ├── 16-ai-prompts.md               # AI промпты, правила
│   ├── 17-subagents.md                # 10 агентов
│   ├── 18-agent-skills.md             # Skills и шаблоны
│   └── 19-logs-coverage.md            # Логи, мониторинг
│
├── server/                            # === FastAPI сервер (10 657 строк) ===
│   ├── __init__.py                    # 1 строка
│   ├── main.py                        # 8675 строк — 144+ REST endpoints
│   ├── database.py                    # 686 строк — 25 SQLAlchemy моделей
│   ├── schemas.py                     # 819 строк — 45+ Pydantic схем
│   ├── auth.py                        # 134 строк — JWT (HS256) + bcrypt
│   ├── config.py                      # 51 строк — серверная конфигурация
│   ├── yandex_disk_service.py         # 291 строк — интеграция Яндекс.Диска
│   ├── Dockerfile                     # Docker образ Python 3.11
│   └── requirements.txt              # Серверные зависимости (FastAPI, SQLAlchemy, psycopg2)
│
├── database/                          # === Локальная SQLite БД (6 286 строк) ===
│   ├── __init__.py                    # 1 строка
│   └── db_manager.py                  # 6285 строк — 50+ миграций, все CRUD операции
│
├── ui/                                # === PyQt5 интерфейс (47 372 строк, 28 файлов) ===
│   ├── __init__.py                    # 0 строк
│   │
│   │  # --- Главные окна ---
│   ├── main_window.py                 # 1574 строк — Главное окно с табами
│   ├── login_window.py                # 611 строк — Окно авторизации
│   │
│   │  # --- Основные табы ---
│   ├── crm_tab.py                     # 17842 строк — CRM Kanban доска (Drag&Drop)
│   ├── crm_supervision_tab.py         # 8223 строк — Авторский надзор (Kanban)
│   ├── contracts_tab.py               # 4501 строк — Управление договорами
│   ├── clients_tab.py                 # 1340 строк — Управление клиентами
│   ├── employees_tab.py               # 1329 строк — Управление сотрудниками
│   ├── salaries_tab.py                # 3188 строк — Зарплаты и отчёты
│   │
│   │  # --- Дашборд и отчёты ---
│   ├── dashboard_tab.py               # 292 строк — Вкладка дашборда
│   ├── dashboard_widget.py            # 504 строк — Виджеты дашборда
│   ├── dashboards.py                  # 1967 строк — Логика дашбордов
│   ├── employee_reports_tab.py        # 443 строк — Отчёты по сотрудникам
│   ├── reports_tab.py                 # 824 строк — Общие отчёты и статистика
│   │
│   │  # --- Файлы и галереи ---
│   ├── file_list_widget.py            # 271 строк — Список файлов
│   ├── file_gallery_widget.py         # 191 строк — Галерея файлов (превью)
│   ├── file_preview_widget.py         # 172 строк — Предпросмотр файлов
│   ├── variation_gallery_widget.py    # 291 строк — Галерея вариаций
│   │
│   │  # --- Таймлайны и сроки ---
│   ├── timeline_widget.py             # 798 строк — Таблица сроков проекта (7 колонок)
│   ├── supervision_timeline_widget.py # 530 строк — Таблица сроков надзора (11 колонок)
│   │
│   │  # --- Диалоги и виджеты ---
│   ├── rates_dialog.py                # 1470 строк — Диалог управления тарифами
│   ├── update_dialogs.py              # 297 строк — Диалоги обновлений
│   ├── custom_title_bar.py            # 256 строк — Кастомный заголовок (Frameless)
│   ├── custom_message_box.py          # 294 строк — Кастомное MessageBox
│   ├── custom_combobox.py             # 40 строк — Кастомный ComboBox
│   ├── custom_dateedit.py             # 28 строк — Кастомный DateEdit
│   └── flow_layout.py                # 96 строк — Flow Layout для виджетов
│
├── utils/                             # === Утилиты (12 151 строк, 27 файлов) ===
│   ├── __init__.py                    # 0 строк
│   │
│   │  # --- Ядро: API и данные ---
│   ├── api_client.py                  # 3068 строк — REST клиент (HTTP, JWT, таймауты)
│   ├── data_access.py                 # 914 строк — Унифицированный CRUD (API-first + SQLite fallback)
│   ├── db_sync.py                     # 1730 строк — Синхронизация БД при входе (14 этапов)
│   ├── offline_manager.py             # 796 строк — Offline-очередь, операции при потере сети
│   ├── sync_manager.py                # 483 строк — Real-time синхронизация (QTimer 30 сек)
│   │
│   │  # --- UI: стили и отображение ---
│   ├── unified_styles.py              # 959 строк — Единая QSS система стилей
│   ├── icon_loader.py                 # 75 строк — Загрузчик SVG иконок
│   ├── resource_path.py               # 32 строк — Пути к ресурсам (exe-совместимость)
│   │
│   │  # --- Файлы и интеграции ---
│   ├── yandex_disk.py                 # 882 строк — Интеграция с Яндекс.Диском
│   ├── pdf_generator.py               # 281 строк — Генерация PDF отчётов
│   ├── preview_generator.py           # 223 строк — Генерация превью файлов
│   ├── cache_manager.py               # 136 строк — Менеджер кэширования данных
│   │
│   │  # --- Безопасность ---
│   ├── password_utils.py              # 130 строк — bcrypt хэширование паролей
│   ├── db_security.py                 # 201 строк — Безопасность локальной БД
│   ├── validators.py                  # 274 строк — Валидаторы данных (телефон, email, ИНН)
│   │
│   │  # --- Даты и время ---
│   ├── calendar_helpers.py            # 152 строк — Рабочие дни, праздники, расчёт дат
│   ├── date_utils.py                  # 331 строк — Утилиты дат (форматирование, парсинг)
│   │
│   │  # --- Обновления и настройки ---
│   ├── update_manager.py              # 259 строк — Менеджер обновлений клиента
│   ├── table_settings.py              # 470 строк — Настройки таблиц (ширины, видимость)
│   │
│   │  # --- Логирование ---
│   ├── logger.py                      # 198 строк — Централизованное логирование (5 логгеров)
│   │
│   │  # --- Хелперы ---
│   ├── dialog_helpers.py              # 53 строк — Помощники создания диалогов
│   ├── message_helper.py              # 55 строк — Помощники сообщений
│   ├── tab_helpers.py                 # 57 строк — Помощники вкладок
│   ├── tooltip_fix.py                 # 18 строк — Исправление tooltip (Windows)
│   │
│   │  # --- Миграции и индексы ---
│   ├── add_indexes.py                 # 201 строк — Добавление индексов в SQLite
│   └── migrate_passwords.py          # 173 строк — Миграция паролей (plain → bcrypt)
│
├── resources/                         # === Ресурсы (112 файлов) ===
│   ├── logo.png                       # Логотип приложения
│   ├── icon.ico                       # Основная иконка
│   ├── icon32.ico                     # 32x32
│   ├── icon48.ico                     # 48x48
│   ├── icon64.ico                     # 64x64
│   ├── icon128.ico                    # 128x128
│   ├── icon256.ico                    # 256x256
│   │
│   └── icons/                         # 105 SVG иконок
│       ├── accept.svg                 # Принять
│       ├── active.svg                 # Активный статус
│       ├── activity.svg               # Активность
│       ├── add.svg / add2.svg         # Добавить
│       ├── archive.svg                # Архив
│       ├── arrow-*.svg                # Стрелки (4 направления)
│       ├── award.svg                  # Награда
│       ├── birthday.svg               # День рождения
│       ├── box.svg                    # Коробка
│       ├── briefcase.svg              # Портфель
│       ├── calendar.svg               # Календарь
│       ├── calendar-plus.svg/2.svg    # Добавить в календарь
│       ├── check-*.svg                # Чекбоксы (5 вариантов)
│       ├── clipboard*.svg             # Буфер обмена (4 варианта)
│       ├── clock.svg                  # Часы
│       ├── close.svg                  # Закрыть
│       ├── codepen*.svg               # Проект (3 варианта)
│       ├── deadline.svg               # Дедлайн
│       ├── delete.svg / delete2.svg   # Удалить
│       ├── delete-red.svg             # Удалить (красная)
│       ├── dollar.svg / dollar-sign.svg # Валюта
│       ├── download.svg               # Скачать
│       ├── edit.svg / edit2.svg       # Редактировать
│       ├── export.svg / export2.svg   # Экспорт
│       ├── eye.svg                    # Просмотр
│       ├── file-text.svg              # Файл
│       ├── folder.svg                 # Папка
│       ├── gift.svg                   # Подарок
│       ├── grid.svg                   # Сетка
│       ├── history.svg                # История
│       ├── info.svg                   # Информация
│       ├── layers.svg                 # Слои
│       ├── map-pin.svg                # Карта / адрес
│       ├── maximize.svg               # Развернуть
│       ├── minimize.svg               # Свернуть
│       ├── money.svg                  # Деньги
│       ├── note.svg                   # Заметка
│       ├── package.svg                # Пакет
│       ├── pause.svg / pause2.svg     # Пауза
│       ├── play.svg                   # Воспроизвести
│       ├── refresh.svg / 2 / 3        # Обновить (3 варианта)
│       ├── refresh-black.svg          # Обновить (чёрная)
│       ├── refresh-white.svg          # Обновить (белая)
│       ├── save.svg                   # Сохранить
│       ├── search.svg / search2.svg   # Поиск
│       ├── settings.svg / settings2.svg # Настройки
│       ├── shield.svg / shield-off.svg # Безопасность
│       ├── stats.svg / stats2.svg     # Статистика
│       ├── submit.svg                 # Отправить
│       ├── tag.svg / tag-black.svg    # Метка
│       ├── team.svg                   # Команда
│       ├── tool.svg                   # Инструмент
│       ├── trending-down.svg          # Тренд вниз
│       ├── trending-up.svg            # Тренд вверх
│       ├── upload.svg                 # Загрузить
│       ├── user.svg                   # Пользователь
│       ├── user-check.svg             # Пользователь OK
│       ├── user-minus.svg             # Удалить пользователя
│       ├── user-plus.svg              # Добавить пользователя
│       ├── users.svg                  # Группа
│       ├── user-x.svg                 # Заблокировать
│       ├── view.svg                   # Просмотр
│       ├── warning.svg                # Предупреждение
│       └── x-circle.svg              # Отмена
│
├── tests/                             # === Тесты (32 000+ строк, 90+ файлов) ===
│   ├── __init__.py
│   ├── conftest.py                    # Глобальные фикстуры pytest
│   ├── test_db_api_sync_audit.py      # 376 строк — Аудит синхронизации DB↔API
│   ├── test_performance.py            # 378 строк — Нагрузочное тестирование
│   │
│   ├── api_client/                    # --- Unit-тесты API клиента (1 600+ строк) ---
│   │   ├── __init__.py
│   │   ├── test_api_methods.py        # 387 строк — Тесты HTTP методов
│   │   ├── test_api_crud.py           # 560+ строк — Mock CRUD тесты (77 тестов, 13 классов)
│   │   ├── test_offline.py            # 341 строк — Offline режим
│   │   └── test_sync.py              # 308 строк — Синхронизация
│   │
│   ├── backend/                       # --- Unit-тесты FastAPI (1 276 строк) ---
│   │   ├── __init__.py
│   │   ├── test_auth.py               # 224 строк — JWT авторизация
│   │   ├── test_endpoints.py          # 407 строк — REST endpoints
│   │   ├── test_models.py             # 337 строк — SQLAlchemy модели
│   │   └── test_schemas.py           # 308 строк — Pydantic схемы
│   │
│   ├── client/                        # --- Unit-тесты клиента (2 800+ строк) ---
│   │   ├── __init__.py
│   │   ├── conftest.py                # Фикстуры клиента
│   │   ├── test_api_client.py         # 303 строк — APIClient методы
│   │   ├── test_cache_manager.py      # 100 строк — Кэширование (15 тестов)
│   │   ├── test_data_access.py        # 422 строк — DataAccess CRUD
│   │   ├── test_date_utils.py         # 224 строк — Утилиты дат
│   │   ├── test_login_widget.py       # 146 строк — Окно входа
│   │   ├── test_password_utils.py     # 116 строк — Утилиты паролей
│   │   ├── test_supervision_upload.py # 434 строк — Загрузка надзора
│   │   ├── test_unified_styles.py     # 80 строк — QSS стили (9 тестов)
│   │   ├── test_validation_bugs.py    # 528 строк — Баги валидации
│   │   └── test_validators.py        # 261 строк — Валидаторы (75+ тестов)
│   │
│   ├── db/                            # --- Тесты БД без сервера (569 строк) ---
│   │   ├── __init__.py
│   │   ├── conftest.py                # Фикстуры с temp SQLite
│   │   ├── test_db_crud.py            # 202 строк — CRUD операции
│   │   ├── test_db_file_queries.py    # 169 строк — Файловые запросы
│   │   └── test_db_migrations.py     # 198 строк — Миграции
│   │
│   ├── e2e/                           # --- E2E тесты (7 000+ строк, нужен сервер) ---
│   │   ├── __init__.py
│   │   ├── conftest.py                # Фикстуры E2E (API URL, JWT)
│   │   ├── test_e2e_action_history.py # 129 строк — История действий
│   │   ├── test_e2e_auth_roles.py     # 178 строк — Авторизация и роли
│   │   ├── test_e2e_clients.py        # 76 строк — Клиенты CRUD
│   │   ├── test_e2e_contracts.py      # 116 строк — Договоры CRUD
│   │   ├── test_e2e_crm_approval.py   # 184 строк — Согласования CRM
│   │   ├── test_e2e_crm_deadlines.py  # 188 строк — Дедлайны CRM
│   │   ├── test_e2e_crm_executors.py  # 279 строк — Исполнители CRM
│   │   ├── test_e2e_crm_lifecycle.py  # 267 строк — Жизненный цикл CRM
│   │   ├── test_e2e_dashboard.py      # 76 строк — Дашборд
│   │   ├── test_e2e_employees.py      # 503 строк — Сотрудники CRUD
│   │   ├── test_e2e_files_db.py       # 209 строк — Файлы в БД
│   │   ├── test_e2e_files_yandex.py   # 430+ строк — Файлы Яндекс.Диск (21 тест)
│   │   ├── test_e2e_full_workflow.py  # 366 строк — Полный рабочий цикл
│   │   ├── test_e2e_heartbeat.py      # Heartbeat + синхронизация (3 теста)
│   │   ├── test_e2e_locks.py          # 432 строк — Блокировки записей (11 тестов)
│   │   ├── test_e2e_notifications.py  # Уведомления
│   │   ├── test_e2e_payments.py       # 465 строк — Платежи
│   │   ├── test_e2e_pdf_export.py     # 54 строк — Экспорт PDF
│   │   ├── test_e2e_project_templates.py # Шаблоны проектов
│   │   ├── test_e2e_rates.py          # 630 строк — Тарифы
│   │   ├── test_e2e_reports.py        # Отчёты
│   │   ├── test_e2e_salaries.py       # 479 строк — Зарплаты
│   │   ├── test_e2e_statistics.py     # Расширенная статистика
│   │   ├── test_e2e_supervision.py    # 228 строк — Авторский надзор
│   │   ├── test_e2e_supervision_timeline.py # Таймлайн надзора (7 тестов)
│   │   ├── test_e2e_sync_data.py      # Синхронизация данных
│   │   └── test_e2e_timeline.py      # Таблица сроков (15 тестов)
│   │
│   ├── ui/                            # --- UI тесты pytest-qt offscreen (3 700+ строк, 460 тестов) ---
│   │   ├── __init__.py
│   │   ├── conftest.py                # Инфраструктура: offscreen, 11 ролей, автоочистка БД
│   │   ├── test_login.py              # 14 тестов — Авторизация, поля, валидация
│   │   ├── test_main_window.py        # 18 тестов — Вкладки, навигация, lazy-loading
│   │   ├── test_clients.py            # 36 тестов — CRUD, диалоги, валидация
│   │   ├── test_contracts.py          # 44 теста — CRUD, динамические поля, подтипы
│   │   ├── test_employees.py          # 30 тестов — CRUD, роли, фильтры
│   │   ├── test_crm.py               # 92 теста — Kanban, workflow, перемещение, дедлайны
│   │   ├── test_crm_supervision.py    # 40 тестов — 12 стадий, timeline, архив
│   │   ├── test_salaries.py           # 34 теста — Вкладки, фильтры, диалоги
│   │   ├── test_reports.py            # 8 тестов — 4 вкладки, фильтры
│   │   ├── test_dashboard.py          # 14 тестов — Карточки метрик, виджеты
│   │   ├── test_roles.py             # 95 тестов — 9 должностей + 2 двойные роли
│   │   ├── test_data_access.py       # 17 тестов — DataAccess CRUD
│   │   └── test_edge_cases.py        # 18 тестов — Edge cases: пустые данные, offline, extreme values
│   │
│   ├── edge_cases/                    # --- Граничные случаи (5 788 строк) ---
│   │   ├── __init__.py
│   │   ├── test_concurrent_updates.py              # 549 строк — Конкурентные обновления
│   │   ├── test_crm_relationship_breakage.py       # 631 строк — Разрыв CRM связей
│   │   ├── test_data_integrity.py                  # 325 строк — Целостность данных
│   │   ├── test_duplicate_payments.py              # 336 строк — Дубликаты платежей
│   │   ├── test_offline_online.py                  # 336 строк — Переключение offline↔online
│   │   ├── test_offline_queue_integrity.py         # 723 строк — Целостность offline-очереди
│   │   ├── test_payment_reassignment_breakage.py   # 542 строк — Разрыв переназначения
│   │   ├── test_relationship_changes.py            # 573 строк — Изменение связей
│   │   ├── test_salaries_relationship_breakage.py  # 558 строк — Разрыв связей зарплат
│   │   └── test_supervision_relationship_breakage.py # 718 строк — Разрыв связей надзора
│   │
│   ├── frontend/                      # --- Frontend тесты (673 строк) ---
│   │   ├── __init__.py
│   │   ├── test_dialogs.py            # 348 строк — Тесты диалогов
│   │   └── test_widgets.py           # 325 строк — Тесты виджетов
│   │
│   ├── integration/                   # --- Интеграционные тесты (4 946 строк) ---
│   │   ├── __init__.py
│   │   ├── test_card_completion_flow.py              # 361 строк — Завершение карточки
│   │   ├── test_contracts_clients_api_integration.py # 898 строк — Контракты + клиенты API
│   │   ├── test_contract_flow.py                     # 280 строк — Поток договора
│   │   ├── test_crm_flow.py                          # 230 строк — Поток CRM
│   │   ├── test_crm_supervision_integration.py       # 643 строк — Интеграция надзора
│   │   ├── test_crm_tab_integration.py               # 1041 строк — Интеграция CRM таба
│   │   ├── test_offline_edge_cases.py                # 559 строк — Edge cases offline
│   │   ├── test_payment_flow.py                      # 314 строк — Поток платежей
│   │   └── test_salaries_tab_integration.py         # 620 строк — Интеграция зарплат
│   │
│   ├── regression/                    # --- Регрессионные тесты (620 строк) ---
│   │   ├── __init__.py
│   │   └── test_critical_bugs.py     # 620 строк — Регрессия критических багов
│   │
│   ├── smoke/                         # --- Smoke тесты (295 строк) ---
│   │   ├── __init__.py
│   │   └── test_api_health.py        # 295 строк — Здоровье API
│   │
│   ├── load/                          # --- Нагрузочные тесты (locust) ---
│   │   ├── __init__.py
│   │   └── locustfile.py             # CRMUser: 9 task-методов, JWT, wait 0.5-2s
│   │
│   └── visual/                        # --- Визуальные тесты ---
│       ├── __init__.py
│       ├── auto_test.py               # Автоматический UI тест
│       ├── full_ui_test.py            # Полный UI тест
│       ├── qt_auto_login.py           # Авто-логин для тестов
│       ├── run_and_capture.py         # Запуск + снимок экрана
│       ├── run_with_autologin.py      # Запуск с автологином
│       └── visual_tester.py          # Визуальный тестер (Playwright)
│
└── logs/                              # === Логи (автогенерируемые) ===
    ├── crm_all.log                    # Все логи (RotatingFile, 10MB x 5)
    └── crm_errors.log               # Только ошибки (ERROR+)
```

---

## Статистика по модулям

| Модуль | Файлов | Строк Python | Крупнейший файл |
|--------|--------|-------------|-----------------|
| **server/** | 8 | 10 657 | `main.py` — 8 675 строк |
| **database/** | 2 | 6 286 | `db_manager.py` — 6 285 строк |
| **ui/** | 28 | 47 372 | `crm_tab.py` — 17 842 строк |
| **utils/** | 27 | 12 151 | `api_client.py` — 3 068 строк |
| **tests/** | 90+ | 32 000+ | `test_crm_tab_integration.py` — 1 041 строк |
| **корень** | 3 | 822 | `migrate_to_server.py` — 471 строк |
| **ИТОГО** | **160+ .py** | **109 500+** | |

## Архитектура

```
┌──────────────────────────────────────────────────────────────────────┐
│                     Interior Studio CRM                              │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  КЛИЕНТ (PyQt5, Python 3.14)         СЕРВЕР (FastAPI, Python 3.11)  │
│  ═══════════════════════════         ═══════════════════════════════ │
│                                                                      │
│  ┌─────────────┐                     ┌────────────────────┐         │
│  │ UI Layer    │                     │ server/main.py     │         │
│  │ 47 372 строк│  ───HTTP/JWT───►   │ 144+ endpoints     │         │
│  │ 28 файлов   │                     │ 8 675 строк        │         │
│  └──────┬──────┘                     └─────────┬──────────┘         │
│         │                                       │                    │
│  ┌──────▼──────┐                     ┌─────────▼──────────┐         │
│  │ DataAccess  │                     │ SQLAlchemy Models   │         │
│  │ API-first   │                     │ 25 моделей          │         │
│  │ + fallback  │                     │ 686 строк           │         │
│  └──────┬──────┘                     └─────────┬──────────┘         │
│         │                                       │                    │
│  ┌──────▼──────┐                     ┌─────────▼──────────┐         │
│  │ APIClient   │                     │ PostgreSQL          │         │
│  │ 3 068 строк │                     │ (Docker)            │         │
│  └──────┬──────┘                     └────────────────────┘         │
│         │                                                            │
│  ┌──────▼──────┐  ┌──────────────┐                                  │
│  │ Offline Mgr │  │ Sync Manager │                                  │
│  │ 796 строк   │  │ QTimer 30сек │                                  │
│  └──────┬──────┘  └──────────────┘                                  │
│         │                                                            │
│  ┌──────▼──────┐                                                     │
│  │ SQLite      │  ◄── Offline fallback                              │
│  │ 6 285 строк │                                                     │
│  │ 50+ миграций│                                                     │
│  └─────────────┘                                                     │
│                                                                      │
│  ИНТЕГРАЦИИ             ИНФРАСТРУКТУРА                              │
│  ════════════           ════════════════                             │
│  Яндекс.Диск           Docker (PostgreSQL + API + Nginx)            │
│  PDF генератор          PyInstaller (exe сборка)                    │
│  Preview генератор      10 AI агентов Claude Code                   │
│                         4 Hooks валидации                           │
└──────────────────────────────────────────────────────────────────────┘
```
