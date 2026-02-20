# Дорожная карта оптимизации Interior Studio CRM

> Последнее обновление: 2026-02-17
> Документ создан по результатам архитектурного анализа (Sequential Thinking, 12 итераций)

## Общая оценка проекта: 7/10

| Метрика | Значение |
|---------|----------|
| Основной код | 80.1K строк |
| С тестами | 116.5K строк |
| API endpoints | 183 |
| Таблицы PostgreSQL | 23 |
| Миграции SQLite | 44 |
| E2E тесты | 30+ файлов |
| Документация | 21+ документ |

---

## Обзор фаз

| Фаза | Название | Задач | Приоритет |
|------|----------|-------|-----------|
| **1** | [Защита данных и безопасность](#фаза-1--защита-данных-и-безопасность) | 6 | Критический |
| **2** | [UX и пользовательский опыт](#фаза-2--ux-и-пользовательский-опыт) | 7 | Высокий |
| **3** | [Архитектура и рефакторинг](#фаза-3--архитектура-и-рефакторинг) | 8 | Средний |
| **4** | [Инфраструктура и улучшения](#фаза-4--инфраструктура-и-улучшения) | 6 | Низкий |

---

## Фаза 1 — Защита данных и безопасность

> Цель: Исключить риск потери данных и закрыть критические уязвимости безопасности

### 1.1 Верификация бэкапов PostgreSQL

**Статус:** Бэкапы УЖЕ настроены (cron 4:00, pg_dump → Яндекс.Диск CRM_Backups/)

| Параметр | Текущее значение |
|----------|-----------------|
| Локальное хранение | `/opt/interior_studio/backups/` |
| Локальный retention | 14 дней |
| Удалённое хранение | Яндекс.Диск `CRM_Backups/` |
| Удалённый retention | 30 дней |
| Размер бэкапа | ~276 КБ (gzip) |
| Расписание | Ежедневно 4:00 (cron) |

**Что нужно проверить/доработать:**

- [ ] **1.1.1** Проверить что cron-задача реально выполняется на сервере
  ```bash
  ssh timeweb
  crontab -l  # проверить наличие записей
  ls -la /opt/interior_studio/backups/  # проверить наличие файлов
  ```
- [ ] **1.1.2** Добавить тест восстановления бэкапа (раз в месяц)
  ```bash
  # Скрипт восстановления тестовой БД из бэкапа
  docker exec -i crm_postgres psql -U crm_user -d test_restore < backup.sql
  ```
- [ ] **1.1.3** Добавить алерт при неудачном бэкапе (email/Telegram бот)
- [ ] **1.1.4** Добавить почасовые бэкапы (сейчас только ежедневные)

**Файлы:** скрипты на сервере `/opt/interior_studio/scripts/backup-db.sh`

---

### 1.2 Консолидация папок Яндекс.Диска

**Проблема:** 4 разрозненные корневые папки на Яндекс.Диске

**Текущая структура:**
```
Яндекс.Диск/
├── crm                    ← неизвестная роль
├── crm backups            ← бэкапы PostgreSQL
├── crm updates            ← обновления .exe
└── АРХИВ ПРОЕКТОВ         ← файлы проектов (основная)
```

**Целевая структура:**
```
Яндекс.Диск/
└── CRM/
    ├── Проекты/           ← бывший "АРХИВ ПРОЕКТОВ"
    │   ├── ФЕСТИВАЛЬ/
    │   │   ├── Авторские надзоры/
    │   │   ├── Индивидуальные/
    │   │   └── Шаблонные/
    │   └── ПЕТРОВИЧ/
    │       └── ...
    ├── Бэкапы/            ← бывший "crm backups"
    │   ├── daily/
    │   └── archive/
    ├── Обновления/        ← бывший "crm updates"
    │   └── v1.x.x/
    └── Системное/         ← бывший "crm" (если есть данные)
```

**План миграции (чистая миграция — данные тестовые):**

- [x] **1.2.1** Добавить константы путей в [config.py](../config.py):
  ```python
  YANDEX_DISK_ROOT = 'disk:/CRM'
  YANDEX_DISK_PROJECTS = f'{YANDEX_DISK_ROOT}/Проекты'
  YANDEX_DISK_BACKUPS = f'{YANDEX_DISK_ROOT}/Бэкапы'
  YANDEX_DISK_UPDATES = f'{YANDEX_DISK_ROOT}/Обновления'
  ```
- [x] **1.2.2** Обновить [utils/yandex_disk.py](../utils/yandex_disk.py) — `archive_root` из config
- [x] **1.2.3** Обновить [utils/update_manager.py](../utils/update_manager.py) — путь из config
- [x] **1.2.4** Создать структуру `disk:/CRM/` на Яндекс.Диске (через API)
- [x] **1.2.5** Удалить старые папки (CRM_Backups, CRM_UPDATES, АРХИВ ПРОЕКТОВ)
- [x] **1.2.6** Обновить скрипт бэкапа на сервере (новый путь `CRM/Бэкапы/`)
- [ ] **1.2.7** Задеплоить сервер и клиент

**Изменённые файлы:**
- [config.py](../config.py) — константы `YANDEX_DISK_*`
- [utils/yandex_disk.py](../utils/yandex_disk.py) — `archive_root` из config
- [utils/update_manager.py](../utils/update_manager.py) — `updates_folder` из config

---

### 1.3 Conflict resolution при offline-синхронизации

**Проблема:** 2 пользователя offline одновременно меняют одну запись → потеря данных

**Текущее поведение:** Last write wins (без уведомления пользователя)

**Решение:**

- [ ] **1.3.1** Добавить поле `version` (INTEGER) во все основные таблицы (clients, contracts, crm_cards, supervision_cards)
  - SQLite миграция: `ALTER TABLE ... ADD COLUMN version INTEGER DEFAULT 1`
  - PostgreSQL: `version INTEGER DEFAULT 1 NOT NULL` в SQLAlchemy models
- [ ] **1.3.2** При каждом UPDATE инкрементировать version на сервере:
  ```python
  # server/main.py — пример для contracts
  if contract.version != request.version:
      raise HTTPException(409, detail={
          "error": "conflict",
          "server_version": contract.version,
          "server_data": serialize(contract)
      })
  contract.version += 1
  ```
- [ ] **1.3.3** Создать `ui/conflict_dialog.py` — диалог разрешения конфликтов:
  - Показать обе версии (локальная vs серверная)
  - Кнопки: "Сохранить мою версию" / "Принять серверную" / "Объединить"
- [ ] **1.3.4** Интегрировать в OfflineManager — при синхронизации очереди проверять version

**Затрагиваемые файлы:**
- [database/db_manager.py](../database/db_manager.py) — миграция `version`
- [server/database.py](../server/database.py) — SQLAlchemy модели
- [server/main.py](../server/main.py) — проверка version в PUT/PATCH handlers
- [utils/offline_manager.py](../utils/offline_manager.py) — обработка 409 Conflict
- Новый файл: `ui/conflict_dialog.py`

---

### 1.4 Request deduplication (защита от двойных кликов)

**Проблема:** Двойной клик = 2 одинаковых POST запроса = дубль данных

**Решение:**

- [ ] **1.4.1** Добавить debounce в UI:
  ```python
  # utils/ui_helpers.py
  def disable_button_during_request(button, callback):
      button.setEnabled(False)
      try:
          result = callback()
      finally:
          button.setEnabled(True)
      return result
  ```
- [ ] **1.4.2** Idempotency key в api_client:
  ```python
  # POST запросы получают уникальный ключ
  headers['X-Idempotency-Key'] = str(uuid4())
  ```
- [ ] **1.4.3** Серверная проверка идемпотентности (кэш ключей на 5 мин)

**Затрагиваемые файлы:**
- [utils/api_client.py](../utils/api_client.py) — idempotency header
- [server/main.py](../server/main.py) — проверка ключа
- UI файлы — debounce кнопок сохранения

---

### 1.5 Аудит JWT и секретов

**Статус:** Секреты уже вынесены в env (отмечено в roadmap). Дополнительно:

- [ ] **1.5.1** Убрать fallback-значение SECRET_KEY в config.py (падать при отсутствии)
- [ ] **1.5.2** Добавить ротацию JWT secret key (раз в квартал)
- [ ] **1.5.3** Добавить rate limit для /api/auth/login (nginx level)

---

### 1.6 Brute-force защита — персистентное хранение

**Проблема:** `_login_attempts` в памяти — сбрасывается при рестарте

- [ ] **1.6.1** Перенести хранение attempts в PostgreSQL таблицу `login_attempts`
- [ ] **1.6.2** Очистка старых записей по cron

---

## Фаза 2 — UX и пользовательский опыт

> Цель: Улучшить ежедневную работу менеджеров, дизайнеров и руководителя студии

### 2.1 Расширение Dashboard для руководителя

**Проблема:** Текущий dashboard (289 строк) слишком примитивен для руководителя

**Что добавить:**

- [ ] **2.1.1** Виджет "Просроченные дедлайны" — красные флаги
  - Список карточек с просроченными стадиями
  - Группировка по исполнителю
  - Клик → переход в CRM карточку
- [ ] **2.1.2** Виджет "Финансовая сводка за месяц"
  - Суммы оплат: план vs факт
  - Задолженности клиентов
  - Выплаты сотрудникам
- [ ] **2.1.3** Виджет "Загрузка команды"
  - Барчарт: сотрудник → количество активных стадий
  - Цветовая индикация: зелёный (норма), жёлтый (много), красный (перегрузка)
- [ ] **2.1.4** Виджет "Динамика проектов" (месяц к месяцу)
  - Линейный график: новых / завершённых / в работе
- [ ] **2.1.5** Виджет "Конверсия воронки"
  - Funnel-диаграмма с процентами перехода между этапами

**Затрагиваемые файлы:**
- [ui/dashboard_tab.py](../ui/dashboard_tab.py) — расширение
- [ui/dashboard_widget.py](../ui/dashboard_widget.py) — новые виджеты
- [ui/chart_widget.py](../ui/chart_widget.py) — новые типы графиков
- [utils/data_access.py](../utils/data_access.py) — методы получения данных

**API endpoints (уже существуют):**
- `GET /api/statistics/dashboard`
- `GET /api/statistics/funnel`
- `GET /api/statistics/executor-load`
- `GET /api/dashboard/salaries*`

---

### 2.2 Desktop-уведомления (QSystemTrayIcon)

**Проблема:** Коллега изменил карточку — пользователь не знает до ручного обновления

- [ ] **2.2.1** Создать `utils/notification_manager.py`:
  ```python
  class DesktopNotificationManager:
      def notify(self, title, message, icon=None):
          self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 5000)
  ```
- [ ] **2.2.2** Интегрировать с SyncManager:
  - При `crm_cards_updated` — проверить "мои" карточки → уведомить
  - При `record_locked` — "Запись редактируется: {имя}"
  - При назначении нового исполнителя → "Вам назначена стадия X"
- [ ] **2.2.3** Настройки уведомлений (вкл/выкл по типам)
- [ ] **2.2.4** Иконка в трей с бейджем непрочитанных

**Затрагиваемые файлы:**
- Новый файл: `utils/notification_manager.py`
- [ui/main_window.py](../ui/main_window.py) — инициализация tray icon
- [utils/sync_manager.py](../utils/sync_manager.py) — привязка сигналов

---

### 2.3 Undo для drag & drop в Kanban

**Проблема:** Случайное перетаскивание карточки — нет отмены

- [ ] **2.3.1** Создать `utils/undo_manager.py`:
  ```python
  class UndoManager:
      def __init__(self, max_history=20):
          self._history = deque(maxlen=max_history)

      def push(self, action: UndoAction):
          self._history.append(action)

      def undo(self) -> Optional[UndoAction]:
          if self._history:
              action = self._history.pop()
              action.revert()
              return action
  ```
- [ ] **2.3.2** При drag & drop → сохранять `UndoAction(card_id, prev_column, new_column)`
- [ ] **2.3.3** Ctrl+Z → вызов `undo_manager.undo()` → возврат карточки
- [ ] **2.3.4** Показывать toast "Карточка перемещена. Ctrl+Z для отмены"

**Затрагиваемые файлы:**
- Новый файл: `utils/undo_manager.py`
- [ui/crm_tab.py](../ui/crm_tab.py) — интеграция в drag & drop
- [ui/crm_supervision_tab.py](../ui/crm_supervision_tab.py) — аналогично

---

### 2.4 Горячие клавиши

**Проблема:** Менеджер работает 8ч/день — нет keyboard shortcuts

- [ ] **2.4.1** Глобальные:
  | Клавиша | Действие |
  |---------|----------|
  | `Ctrl+F` | Глобальный поиск |
  | `Ctrl+N` | Новый (клиент/договор/карточка в зависимости от таба) |
  | `Ctrl+S` | Сохранить текущую форму |
  | `Ctrl+Z` | Отменить последнее действие |
  | `Ctrl+1..8` | Переключение табов |
  | `F5` | Обновить данные |
  | `Escape` | Закрыть диалог |

- [ ] **2.4.2** Kanban-специфичные:
  | Клавиша | Действие |
  |---------|----------|
  | `Enter` | Открыть выбранную карточку |
  | `←/→` | Переместить карточку между колонками |
  | `↑/↓` | Навигация по карточкам |

**Затрагиваемые файлы:**
- [ui/main_window.py](../ui/main_window.py) — QShortcut привязки
- [ui/crm_tab.py](../ui/crm_tab.py) — Kanban shortcuts

---

### 2.5 Пагинация и виртуализация Kanban

**Проблема:** Все карточки загружаются в память. При 500+ карточек — тормоза

- [ ] **2.5.1** Серверная пагинация: `GET /api/crm/cards?column=X&page=1&per_page=20`
- [ ] **2.5.2** Lazy loading при скролле (подгрузка следующей страницы)
- [ ] **2.5.3** Виртуализация: рендерить только видимые карточки в QScrollArea
- [ ] **2.5.4** Кеширование отрендеренных карточек для мгновенного скролла назад

**Затрагиваемые файлы:**
- [server/main.py](../server/main.py) — пагинация endpoint
- [utils/api_client.py](../utils/api_client.py) — параметры пагинации
- [ui/crm_tab.py](../ui/crm_tab.py) — виртуализация отображения

---

### 2.6 Drag & drop файлов

- [ ] **2.6.1** Добавить QDropArea в [ui/file_gallery_widget.py](../ui/file_gallery_widget.py)
- [ ] **2.6.2** При бросании файла → загрузка на Яндекс.Диск + создание записи
- [ ] **2.6.3** Индикатор прогресса загрузки

---

### 2.7 Улучшение формы редактирования карточек CRM

- [ ] **2.7.1** Tab-навигация между полями формы
- [ ] **2.7.2** Автосохранение черновика (каждые 30 сек при изменениях)
- [ ] **2.7.3** Индикация несохранённых изменений (точка в заголовке)

---

## Фаза 3 — Архитектура и рефакторинг

> Цель: Снизить сложность кодовой базы, улучшить maintainability и testability

### 3.1 Разделение server/main.py на роутеры

**Проблема:** 9159 строк, 183 endpoints в одном файле

**Целевая структура:**
```
server/
├── main.py                 (~300 строк — инициализация, middleware)
├── routers/
│   ├── __init__.py
│   ├── auth.py             (~300 строк — login, refresh, logout, permissions)
│   ├── clients.py          (~200 строк — CRUD клиенты)
│   ├── contracts.py        (~400 строк — CRUD договоры)
│   ├── employees.py        (~200 строк — CRUD сотрудники)
│   ├── crm.py              (~600 строк — CRM карточки, стадии, исполнители)
│   ├── supervision.py      (~400 строк — авторский надзор)
│   ├── payments.py         (~500 строк — платежи, тарифы, зарплаты)
│   ├── files.py            (~300 строк — файлы, Яндекс.Диск)
│   ├── statistics.py       (~400 строк — dashboard, analytics, funnel)
│   ├── timeline.py         (~300 строк — таблицы сроков)
│   └── system.py           (~200 строк — health, sync, locks, search)
├── services/               (бизнес-логика)
│   ├── __init__.py
│   ├── crm_service.py
│   ├── payment_service.py
│   └── notification_service.py
├── models/                 (бывший database.py)
│   ├── __init__.py
│   └── tables.py
├── schemas/                (бывший schemas.py)
│   ├── __init__.py
│   ├── auth.py
│   ├── clients.py
│   └── ...
├── database.py             (engine, session, Base)
├── auth.py                 (JWT логика)
├── config.py               (настройки)
└── permissions.py          (права доступа)
```

**План:**

- [ ] **3.1.1** Создать `server/routers/` с `__init__.py`
- [ ] **3.1.2** Выделить `auth.py` router (наименее связанный)
- [ ] **3.1.3** Выделить `clients.py`, `employees.py` (простые CRUD)
- [ ] **3.1.4** Выделить `contracts.py`
- [ ] **3.1.5** Выделить `crm.py` (самый сложный — 16+ endpoints)
- [ ] **3.1.6** Выделить `supervision.py`
- [ ] **3.1.7** Выделить `payments.py`, `statistics.py`, `timeline.py`, `files.py`, `system.py`
- [ ] **3.1.8** Оставить в main.py: app init, middleware, include_router
- [ ] **3.1.9** Прогнать все e2e тесты → убедиться что ничего не сломалось

**Правило:** Каждый роутер — один коммит. Тесты после каждого шага.

---

### 3.2 Декомпозиция crm_tab.py (17834 строк)

**Целевая структура:**
```
ui/crm/
├── __init__.py
├── crm_tab.py              (~2000 строк — основной контейнер)
├── kanban_board.py          (~3000 строк — доска с колонками)
├── kanban_card.py           (~1500 строк — виджет карточки)
├── card_detail_dialog.py    (~4000 строк — диалог редактирования)
├── stage_panel.py           (~2000 строк — панель стадий)
├── filter_bar.py            (~1000 строк — фильтры)
├── executor_assignment.py   (~1500 строк — назначение исполнителей)
└── approval_workflow.py     (~1500 строк — workflow согласования)
```

- [ ] **3.2.1** Выделить KanbanCard (виджет одной карточки)
- [ ] **3.2.2** Выделить CardDetailDialog (форма редактирования)
- [ ] **3.2.3** Выделить StagePanel (панель стадий и исполнителей)
- [ ] **3.2.4** Выделить FilterBar (фильтры и поиск)
- [ ] **3.2.5** Выделить ApprovalWorkflow (согласование)
- [ ] **3.2.6** Оставить в crm_tab.py: layout, подключение компонентов

---

### 3.3 Service layer на сервере

**Проблема:** Бизнес-логика внутри endpoint handlers

- [ ] **3.3.1** Создать `server/services/crm_service.py`:
  - `create_card()` — создание + расчёт дедлайнов + уведомления
  - `move_card()` — перемещение + workflow transitions
  - `assign_executor()` — назначение + расчёт платежей
- [ ] **3.3.2** Создать `server/services/payment_service.py`:
  - `calculate_payment()` — расчёт по тарифам
  - `reassign_payments()` — переназначение при смене исполнителя
- [ ] **3.3.3** Создать `server/services/notification_service.py`

---

### 3.4 Единая схема SQLite / PostgreSQL

**Проблема:** 2 источника истины для схемы БД

- [ ] **3.4.1** Внедрить Alembic для PostgreSQL миграций
- [ ] **3.4.2** Создать CI-тест: сравнение колонок SQLite vs PostgreSQL
- [ ] **3.4.3** Документировать процесс добавления новых полей (оба места)

---

### 3.5 Типизация API ответов на клиенте

- [ ] **3.5.1** Создать `models/` папку в корне:
  ```python
  @dataclass
  class Contract:
      id: int
      client_id: int
      contract_number: str
      project_type: str
      # ...
  ```
- [ ] **3.5.2** Возвращать typed objects из api_client вместо Dict
- [ ] **3.5.3** Типизировать DataAccess методы

---

### 3.6 Покрытие unit-тестами UI виджетов

- [ ] **3.6.1** pytest-qt для изолированного тестирования PyQt5 виджетов
- [ ] **3.6.2** Mock DataAccess для UI тестов
- [ ] **3.6.3** Целевое покрытие: 60%+ для ui/

---

### 3.7 Retry стратегия api_client

- [ ] **3.7.1** Добавить обработку HTTP 429 (Rate Limit) с `Retry-After`
- [ ] **3.7.2** Exponential backoff: 0.5 → 1.0 → 2.0 сек
- [ ] **3.7.3** Jitter для предотвращения thundering herd

---

### 3.8 SQL Injection аудит

- [ ] **3.8.1** Проверить все вызовы `execute_raw_query()` — убедиться что params используются
- [ ] **3.8.2** Убрать `execute_raw_*` если не используется, или ограничить доступ

---

## Фаза 4 — Инфраструктура и улучшения

> Цель: Повысить надёжность, масштабируемость и наблюдаемость системы

### 4.1 Health monitoring и alerting

- [ ] **4.1.1** Настроить UptimeRobot (бесплатно) для `https://crm.festivalcolor.ru/health`
- [ ] **4.1.2** Алерт в Telegram при downtime
- [ ] **4.1.3** Добавить `/health` расширенный: проверка PostgreSQL, диск, память
- [ ] **4.1.4** Логирование запросов в файл (не только stdout)

---

### 4.2 WebSocket вместо polling

**Текущее:** SyncManager polling каждые 30 сек

- [ ] **4.2.1** Добавить FastAPI WebSocket endpoint: `/ws/sync`
- [ ] **4.2.2** Клиентский WebSocket handler в SyncManager
- [ ] **4.2.3** Fallback на polling если WebSocket недоступен
- [ ] **4.2.4** Push-события: card_moved, card_updated, executor_assigned

**Затрагиваемые файлы:**
- [server/main.py](../server/main.py) — WebSocket endpoint
- [utils/sync_manager.py](../utils/sync_manager.py) — WebSocket клиент

---

### 4.3 Brute-force защита в PostgreSQL

- [ ] **4.3.1** Создать таблицу `login_attempts` в PostgreSQL
- [ ] **4.3.2** При login → записывать attempt в БД
- [ ] **4.3.3** Очистка старых записей: cron каждый час

---

### 4.4 Gunicorn с несколькими workers

**Текущее:** uvicorn с 1 worker

- [ ] **4.4.1** Заменить на gunicorn: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker`
- [ ] **4.4.2** Обновить Dockerfile
- [ ] **4.4.3** Настроить connection pool per worker

---

### 4.5 Индексы PostgreSQL

- [ ] **4.5.1** Проанализировать slow queries: `pg_stat_statements`
- [ ] **4.5.2** Добавить индексы:
  ```sql
  CREATE INDEX idx_crm_cards_column ON crm_cards(column_name);
  CREATE INDEX idx_contracts_client ON contracts(client_id);
  CREATE INDEX idx_payments_contract_paid ON payments(contract_id, is_paid);
  CREATE INDEX idx_stage_executors_executor ON stage_executors(executor_id);
  CREATE INDEX idx_contracts_created ON contracts(created_at DESC);
  ```

---

### 4.6 Staging окружение

- [ ] **4.6.1** Docker-compose.staging.yml с отдельной БД
- [ ] **4.6.2** CI/CD: автодеплой в staging при push в develop
- [ ] **4.6.3** Smoke-тесты на staging перед production

---

## Метрики успеха

| Фаза | Метрика | Цель |
|------|---------|------|
| 1 | Потеря данных | 0 инцидентов |
| 1 | Успешность бэкапов | 99.9% |
| 2 | Время на типовую операцию | -30% |
| 2 | Количество кликов (создание карточки) | -20% |
| 3 | Максимальный размер файла | < 3000 строк |
| 3 | Покрытие тестами | > 60% |
| 4 | Время отклика API (p95) | < 200ms |
| 4 | Доступность сервера | 99.5%+ |

---

## Связанные документы

- [01-roadmap.md](01-roadmap.md) — основная дорожная карта
- [02-project-rules.md](02-project-rules.md) — правила проекта
- [07-server.md](07-server.md) — серверная документация
- [21-security.md](21-security.md) — безопасность
