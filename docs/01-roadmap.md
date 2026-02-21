# Roadmap — Дорожная карта Interior Studio CRM

> Последнее обновление: 2026-02-21

## Текущая версия

- **Клиент:** PyQt5 Desktop (Python 3.14.0)
- **Сервер:** FastAPI (Python 3.11) + PostgreSQL
- **Инфраструктура:** Docker на VPS (Timeweb)

## Выполненные фичи

### Ядро (Core)
- [x] Двухрежимная архитектура (Автономный SQLite + Сетевой REST API)
- [x] JWT авторизация с ролями и правами доступа
- [x] Offline-first с очередью синхронизации
- [x] Real-time синхронизация между клиентами (QTimer 30 сек)
- [x] Heartbeat и онлайн-статус пользователей
- [x] Блокировка записей (concurrent editing prevention)
- [x] Синхронизация БД при входе (14 этапов)

### CRM Kanban ([ui/crm_tab.py](../ui/crm_tab.py))
- [x] Kanban доска с Drag & Drop
- [x] Индивидуальные проекты (6 колонок) и Шаблонные (5 колонок)
- [x] Стадии согласования (approval stages)
- [x] Назначение исполнителей на стадии
- [x] Workflow: Сдать работу → Проверка → Принять/На исправление
- [x] Workflow: Клиенту на согласование → Клиент согласовал
- [x] Рассчёт дедлайнов исполнителей (рабочие дни)

### Авторский надзор ([ui/crm_supervision_tab.py](../ui/crm_supervision_tab.py))
- [x] Отдельная Kanban доска для надзора
- [x] Таблица закупок (12 стадий)
- [x] Бюджет план/факт, экономия, комиссия поставщика
- [x] Пауза/возобновление карточки надзора

### Платежи ([ui/salaries_tab.py](../ui/salaries_tab.py))
- [x] Расчёт платежей по тарифам
- [x] Переназначение платежей при смене исполнителя
- [x] Зарплатные отчёты по месяцам
- [x] Статус "В работе" (report_month = NULL)

### Таблица сроков ([ui/timeline_widget.py](../ui/timeline_widget.py))
- [x] 7-колоночная таблица для проектов (Дата, Дни, Норма, Статус, Исполнитель, ФИО)
- [x] 11-колоночная таблица для надзора (Бюджет, Поставщик, Комиссия)
- [x] Авто-расчёт START = max(contract_date, survey_date, tech_task_date)
- [x] Пропорциональное распределение norm_days по contract_term
- [x] Экспорт в Excel и PDF

### Файлы и интеграции
- [x] Интеграция с Яндекс.Диском (загрузка/скачивание/публикация)
- [x] Автоматическое создание папок при создании договора
- [x] Галерея файлов с превью
- [x] Галерея вариаций

### Поиск и аналитика
- [x] Глобальный полнотекстовый поиск (клиенты, договора, проекты)
- [x] Дашборд: круговая диаграмма типов проектов
- [x] Дашборд: воронка проектов по колонкам Kanban
- [x] Дашборд: нагрузка исполнителей (активные стадии)
- [x] Менеджер обновлений клиента (auto-update)
- [x] Экспорт PDF (таймлайн, надзор)

### Инфраструктура
- [x] Docker-compose (PostgreSQL + FastAPI + Nginx) с health checks
- [x] PyInstaller сборка в exe
- [x] Кастомный CustomTitleBar (Frameless окна)
- [x] Единая система стилей (unified_styles.py)
- [x] SVG иконки через IconLoader
- [x] 17 субагентов Claude Code (оркестратор + 16 специализированных)
- [x] Hooks для валидации кода
- [x] GitHub Actions CI/CD (lint, test-db, docker-build, e2e)
- [x] `.env.example` шаблон переменных окружения
- [x] Секреты вынесены в переменные окружения
- [x] faulthandler для crash-диагностики (Python traceback при segfault)
- [x] Thread-safe PyQt signals (QTimer.singleShot для фоновых потоков)
- [x] Фильтрация offline-очереди (только сетевые ошибки)

## Планируемые улучшения

### Приоритет 1 (Высокий)
- [x] Расширение покрытия тестами (E2E + Mock + UI) — 23/23 групп (100%), 600+ тестов
- [x] Автоматический деплой через CI/CD (GitHub Actions) — `.github/workflows/ci.yml`
- [ ] Push-уведомления между клиентами (WebSocket вместо polling)
- [x] Менеджер обновлений клиента (auto-update exe) — `utils/update_manager.py`

### Приоритет 2 (Средний)
- [x] Экспорт отчётов в PDF (все табы) — `utils/pdf_export.py`
- [x] Расширенная аналитика дашборда — графики: воронка, нагрузка, типы проектов
- [x] Полнотекстовый поиск по проектам — `GET /api/search` + `ui/global_search_widget.py`
- [ ] Мобильный веб-клиент (React/Vue)

### Приоритет 3 (Низкий)
- [ ] Мультиязычность (i18n)
- [ ] Тёмная тема
- [ ] Интеграция с 1С
- [ ] API для внешних интеграций

## Технический долг

| Область | Проблема | Приоритет | Статус |
|---------|----------|-----------|--------|
| ~~[ui/crm_tab.py](../ui/crm_tab.py)~~ | ~~17K+ строк — нужна декомпозиция~~ | ~~Высокий~~ | **DONE Phase 4** (3 368 строк, −81%) |
| ~~[server/main.py](../server/main.py)~~ | ~~8700+ строк — выделить routers~~ | ~~Высокий~~ | **DONE Phase 2+3** (424 строки, 22 роутера) |
| ~~[ui/contracts_tab.py](../ui/contracts_tab.py)~~ | ~~5K строк — нужна декомпозиция~~ | ~~Низкий~~ | **DONE Phase 5** (693 строки, contract_dialogs.py) |
| [ui/base_kanban_tab.py](../ui/base_kanban_tab.py) | Базовый класс KanbanTab — заготовка, требует полной интеграции | Средний | Заготовка в Phase 5 |
| Тесты | Нет unit-тестов для UI виджетов | Средний | — |
| Тесты | Нет нагрузочного тестирования | Низкий | — |
| Sync | QTimer polling → WebSocket | Средний | — |
| ~~Docker~~ | ~~Нет health checks~~ — **Реализовано** в `docker-compose.yml` | ~~Средний~~ | **DONE** |
| ~~Безопасность~~ | ~~Хардкод admin/admin123~~ — **Секреты вынесены в env** | ~~Высокий~~ | **DONE** |
| ~~Offline~~ | ~~Write-операции без offline-fallback~~ — **Все 34 write-метода: local-first + offline queue, 18 entity types** | ~~Высокий~~ | **DONE Phase 6.3** |
| ~~Offline~~ | ~~Бизнес-ошибки (409/400) попадают в offline-очередь~~ — **Фильтрация по sys.exc_info(): только сетевые ошибки** | ~~Высокий~~ | **DONE Phase 7.5** |
| ~~Стабильность~~ | ~~Segfault при drag-and-drop карточек CRM~~ — **CopyAction + deferred dialog + thread-safe signals** | ~~Критический~~ | **DONE Phase 7.5** |
| ~~Стабильность~~ | ~~Stale signal connections DataAccess→OfflineManager~~ — **Удалены мёртвые подключения** | ~~Высокий~~ | **DONE Phase 7.5** |
| ~~Авторизация~~ | ~~401 loop при длительной работе~~ — **Token 24h + auto-relogin + redirect header fix** | ~~Высокий~~ | **DONE Phase 7.5** |
| ~~Производительность~~ | ~~N+1 в statistics, нет пагинации, нет кэша~~ | ~~Высокий~~ | **DONE Phase 5** |
| Стиль | border-color без токена (#E0E0E0 вместо переменной) | Низкий | WARN Phase 5 |
| ~~Стиль~~ | ~~Неиспользуемый импорт в messenger_router.py~~ | ~~Низкий~~ | **DONE Phase 5.1** |
| ~~БД~~ | ~~f-string WHERE в db_manager.py (не whitelist)~~ — **_validate_columns + _build_set_clause** | ~~Средний~~ | **DONE Phase 5.1** |
| ~~Тесты~~ | ~~Дублирование в conftest.py~~ — **_factory_teardown helper** | ~~Низкий~~ | **DONE Phase 5.1** |
| ~~DataAccess~~ | ~~19 расхождений параметров DataAccess↔API↔DB~~ | ~~Высокий~~ | **DONE Phase 6.1** |
| ~~DataAccess~~ | ~~34 write-метода без local-first / offline queue~~ | ~~Высокий~~ | **DONE Phase 6.3** |
