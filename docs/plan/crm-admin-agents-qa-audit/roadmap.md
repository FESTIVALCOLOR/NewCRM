# Roadmap: Перенос агентов/городов в админ + QA-аудит CRM

**Дата:** 2026-02-25
**Статус:** Approved
**Источники:** [research.md](./research.md), [design.md](./design.md)

---

```
ПЛАН: Перенос агентов/городов в админ + QA-аудит CRM
РЕЖИМ: full + qa
СЛОИ: server, ui, utils, database
ФАЙЛЫ: server/database.py, server/routers/agents_router.py, server/routers/cities_router.py (NEW),
        server/permissions.py, server/main.py, server/schemas.py,
        ui/admin_dialog.py, ui/agents_cities_widget.py (NEW), ui/contract_dialogs.py,
        ui/permissions_matrix_widget.py, ui/rates_dialog.py,
        utils/api_client/misc_mixin.py, utils/data_access.py,
        database/db_manager.py, database/migrations.py, config.py

ПОДЗАДАЧИ (Задача 1 — РЕАЛИЗАЦИЯ):
1.1. [Server] Модель City + миграция + API endpoints (cities CRUD + agents DELETE)
1.2. [Server] Новые permissions: agents.delete, cities.create, cities.delete
1.3. [Client API] Методы для городов + delete_agent
1.4. [Client DataAccess] CRUD городов + delete агентов
1.5. [Client DB] Таблица cities в SQLite + миграция
1.6. [UI] AgentsCitiesWidget для AdminDialog
1.7. [UI] Убрать кнопки из ContractDialog
1.8. [UI] Обновить загрузку городов в ComboBox (из DataAccess вместо config)

ПОДЗАДАЧИ (Задача 2 — QA ПРАВА ДОСТУПА):
2.1. Анализ кода прав: проверить все 34 permission и их использование
2.2. E2E тест: каждое право проверить через API
2.3. Проверить UI: PermissionsMatrixWidget
2.4. Баг: 'crm.update' vs 'crm_cards.update' в crm_tab.py:113

ПОДЗАДАЧИ (Задача 3 — QA ОСНОВНАЯ CRM, 14 вариаций):
3.1–3.10. Создание карточек, стадии, исполнители, дашборды, оплаты, история, чат, архив

ПОДЗАДАЧИ (Задача 4 — QA CRM НАДЗОРА):
4.1–4.8. Переход, стадии, сотрудники, история, файлы, оплаты, архив, чат

ТЕСТЫ: e2e, db, client, critical
ПАРАЛЛЕЛИЗМ:
  - 1.1+1.2 параллельно
  - 1.3+1.4+1.5 параллельно (после 1.1+1.2)
  - 1.6+1.7+1.8 параллельно (после 1.3+1.4+1.5)
  - 2.x можно параллельно с 1.x
  - 3.x и 4.x — после завершения задачи 1
```

---

## Задача 1: Перенос агентов/городов в администрирование (РЕАЛИЗАЦИЯ)

### Фаза 1: Сервер (БД + API)

- [ ] **1.1. [Server] Модель City + миграция + seed**
  - **Агент:** Backend Agent
  - **Файлы:** `server/database.py:174`, `server/main.py`
  - **Что делать:**
    - Добавить модель `City(Base)` в `server/database.py` после класса `Agent` (строка 174):
      - `id` (Integer, PK, index)
      - `name` (String, unique, not null)
      - `status` (String, default='активный') — значения: 'активный' / 'удалён'
      - `created_at` (DateTime, default=datetime.utcnow)
    - В `server/main.py` в блоке `@app.on_event("startup")`:
      - `Base.metadata.create_all(bind=engine)` создаст таблицу автоматически
      - Добавить функцию `seed_cities(db)` — `INSERT OR IGNORE` для `['СПБ', 'МСК', 'ВН']`
  - **Критерий готовности:** Таблица `cities` создаётся при старте сервера, содержит 3 записи

- [ ] **1.2. [Server] Новый роутер cities_router.py (CRUD)**
  - **Агент:** Backend Agent
  - **Файлы:** `server/routers/cities_router.py` (NEW), `server/main.py:351`
  - **Что делать:**
    - Создать `server/routers/cities_router.py` с prefix `/api/v1/cities`:
      - `GET /` — список городов (параметр `include_deleted: bool = False`)
      - `POST /` — добавить город (право `cities.create`), повторное добавление удалённого восстанавливает статус
      - `DELETE /{city_id}` — мягкое удаление (право `cities.delete`), проверка 409 если есть активные договоры
    - Зарегистрировать в `server/main.py`: `app.include_router(cities_router, ...)`
  - **API контракты:**
    - `GET /api/v1/cities` → `[{"id": 1, "name": "СПБ", "status": "активный"}, ...]`
    - `POST /api/v1/cities` + `{"name": "КЗН"}` → `{"status": "success", "id": 4, "name": "КЗН"}`
    - `DELETE /api/v1/cities/2` → `{"status": "success", "message": "Город 'МСК' удалён"}` / 409 / 404
  - **Критерий готовности:** Все 3 endpoint работают, включая edge cases (дубликат 400, активные договоры 409, восстановление)

- [ ] **1.3. [Server] DELETE endpoint для агентов + фильтрация удалённых**
  - **Агент:** Backend Agent
  - **Файлы:** `server/routers/agents_router.py`
  - **Что делать:**
    - Добавить `DELETE /{agent_id}` endpoint:
      - Право `agents.delete`
      - Мягкое удаление (`agent.status = "удалён"`)
      - Проверка 409 если есть активные договоры (`Contract.agent_type == agent.name, status != 'РАСТОРГНУТ'`)
    - Изменить `GET /` (строка 29): добавить параметр `include_deleted: bool = False`, фильтровать `Agent.status != "удалён"` по умолчанию
  - **API контракты:**
    - `DELETE /api/v1/agents/3` → `{"status": "success", "message": "Агент 'ПЕТРОВИЧ' удалён"}` / 404 / 409
    - `GET /api/v1/agents?include_deleted=true` → включая удалённых
  - **Критерий готовности:** DELETE работает с soft delete, GET фильтрует удалённых

- [ ] **1.4. [Server] Новые permissions**
  - **Агент:** Backend Agent
  - **Файлы:** `server/permissions.py:57-58, 95-96`
  - **Что делать:**
    - Добавить в `ALL_PERMISSIONS` (строки 57-58):
      - `"agents.delete": "Удаление агентов"`
      - `"cities.create": "Создание городов"`
      - `"cities.delete": "Удаление городов"`
    - Добавить в `_BASE_MANAGER` (строки 95-96): `"agents.delete"`, `"cities.create"`, `"cities.delete"`
  - **Критерий готовности:** `seed_permissions` создаёт новые права, `require_permission("agents.delete")` работает

- [ ] **1.5. [Server] Docker rebuild**
  - **Агент:** Deploy Agent
  - **Что делать:** `docker-compose build --no-cache && docker-compose up -d`
  - **Критерий готовности:** Сервер стартует, таблица `cities` создана, seed данные на месте

### Фаза 2: Клиент — слой данных

- [ ] **1.6. [Client DB] Таблица cities в SQLite + миграция**
  - **Агент:** Database Agent
  - **Файлы:** `database/db_manager.py`, `database/migrations.py`
  - **Что делать:**
    - Добавить миграцию `create_cities_table_migration()` в `run_migrations()`:
      - `CREATE TABLE IF NOT EXISTS cities (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, status TEXT DEFAULT 'активный', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)`
      - Seed из `config.CITIES`: `INSERT OR IGNORE INTO cities (name) VALUES (?)`
    - Добавить CRUD методы в `DatabaseManager`:
      - `get_all_cities()` — `SELECT id, name, status FROM cities WHERE status != 'удалён' ORDER BY name`
      - `add_city(name)` — `INSERT INTO cities (name) VALUES (?)`, возвращает `{'id', 'name', 'status'}`
      - `delete_city(city_id)` — `UPDATE cities SET status = 'удалён' WHERE id = ?`
      - `delete_agent(agent_id)` — `UPDATE agents SET status = 'удалён' WHERE id = ?`, сброс `_agent_colors_cache`
  - **Критерий готовности:** Миграция выполняется без ошибок, CRUD методы работают на SQLite

- [ ] **1.7. [Client API] Методы для городов + delete_agent**
  - **Агент:** API Client Agent
  - **Файлы:** `utils/api_client/misc_mixin.py:185`
  - **Что делать:**
    - Добавить методы:
      - `delete_agent(agent_id: int) -> bool` — `DELETE /api/v1/agents/{agent_id}`
      - `get_all_cities() -> List[Dict]` — `GET /api/v1/cities`
      - `add_city(name: str) -> bool` — `POST /api/v1/cities` + `{"name": name}`
      - `delete_city(city_id: int) -> bool` — `DELETE /api/v1/cities/{city_id}`
  - **Критерий готовности:** Все 4 метода реализованы по шаблону существующих (try/except, `_request`, `_handle_response`)

- [ ] **1.8. [Client DataAccess] CRUD городов + delete агентов**
  - **Агент:** Worker Agent
  - **Файлы:** `utils/data_access.py:1527+`
  - **Что делать:**
    - Добавить методы с паттерном API-first + fallback + offline-очередь:
      - `delete_agent(agent_id)` — локальная БД + API + offline queue
      - `get_all_cities()` — API → fallback DB → fallback config.CITIES
      - `add_city(name)` — локальная БД + API + offline queue
      - `delete_city(city_id)` — локальная БД + API + offline queue
  - **Критерий готовности:** Все методы работают в online и offline режимах, fallback на config.py для городов

### Фаза 3: Клиент — UI

- [ ] **1.9. [UI] AgentsCitiesWidget для AdminDialog**
  - **Агент:** Frontend Agent
  - **Файлы:** `ui/agents_cities_widget.py` (NEW)
  - **Что делать:**
    - Создать `AgentsCitiesWidget(QWidget)` с двумя панелями:
      - **Левая панель "Агенты":** список агентов (имя + цветной индикатор), кнопки [Цвет] / [Удалить] на каждой строке, форма добавления (название + выбор цвета + кнопка [Добавить])
      - **Правая панель "Города":** список городов, кнопка [Удалить] на каждой строке, форма добавления (название + кнопка [Добавить])
    - Подтверждение перед удалением (QMessageBox)
    - Обработка 409 (показать сообщение "Нельзя удалить: N активных договоров")
    - Стилизация: рамки 1px solid #E0E0E0, border-radius 10px, accent #ffd93c, danger #e74c3c
    - **Без emoji** — только SVG через IconLoader
  - **Критерий готовности:** Виджет отображает агентов/города, позволяет добавлять/удалять/менять цвет

- [ ] **1.10. [UI] Интеграция в AdminDialog (5-я вкладка)**
  - **Агент:** Frontend Agent
  - **Файлы:** `ui/admin_dialog.py:81-98`
  - **Что делать:**
    - Добавить 5-ю вкладку "Агенты и города" в `QTabWidget` с ленивой загрузкой:
      - `_create_agents_cities_tab()` — placeholder с "Загрузка..."
      - `_init_agents_cities_widget()` — инициализация через `QTimer.singleShot(300, ...)`
      - Передать `api_client`, `data_access`, `employee` в `AgentsCitiesWidget`
  - **Критерий готовности:** Вкладка появляется в AdminDialog, виджет загружается корректно

- [ ] **1.11. [UI] Убрать кнопки управления из ContractDialog**
  - **Агент:** Frontend Agent
  - **Файлы:** `ui/contract_dialogs.py:400-424, 1742-1877, 4207+`
  - **Что делать:**
    - **Строки 400-411:** Удалить `add_agent_btn`, `agent_layout` → оставить только `self.agent_combo` + `main_layout_form.addRow('Агент:', self.agent_combo)`
    - **Строки 413-424:** Удалить `add_city_btn`, `city_layout` → заменить на `self.city_combo` + `self.reload_cities()` + `main_layout_form.addRow('Город:', self.city_combo)`
    - **Строки 1742-1747:** Удалить метод `add_agent()`
    - **Строки 1764-1877:** Удалить метод `add_city()`
    - **Строки 4207-4424:** Удалить класс `AgentDialog` полностью (он переедет в `agents_cities_widget.py`)
  - **Критерий готовности:** В карточке договора только ComboBox без кнопок управления

- [ ] **1.12. [UI] Обновить загрузку городов в ComboBox**
  - **Агент:** Frontend Agent
  - **Файлы:** `ui/contract_dialogs.py:415`, `ui/rates_dialog.py:425`
  - **Что делать:**
    - Добавить метод `reload_cities()` в `ContractDialog`:
      - Вызывает `self.data.get_all_cities()`
      - Заполняет `self.city_combo` из результата
      - Сохраняет текущий выбор
    - Обновить `ui/rates_dialog.py:_get_all_cities()`:
      - Загрузка через `self.data_access.get_all_cities()` вместо `config.CITIES`
      - Fallback на `config.CITIES` при ошибке
    - Проверить, передаётся ли `data_access` в `RatesSettingsWidget` — если нет, добавить
  - **Критерий готовности:** ComboBox городов загружается из БД, fallback на config работает

- [ ] **1.13. [UI] Обновить матрицу прав**
  - **Агент:** Frontend Agent
  - **Файлы:** `ui/permissions_matrix_widget.py:42, 120`
  - **Что делать:**
    - Добавить в `PERMISSION_GROUPS` (строка 42):
      - `'Агенты': ['agents.create', 'agents.update', 'agents.delete']`
      - `'Города': ['cities.create', 'cities.delete']`
    - Добавить описания новых прав в словарь (строка 120):
      - `"agents.delete": "Удаление агентов"`
      - `"cities.create": "Создание городов"`
      - `"cities.delete": "Удаление городов"`
  - **Критерий готовности:** Новые права отображаются в PermissionsMatrixWidget

### Фаза 4: Тесты

- [ ] **1.14. E2E тесты CRUD городов**
  - **Агент:** Test Runner Agent
  - **Файлы:** `tests/e2e/test_cities_crud.py` (NEW)
  - **Тест-кейсы:**
    - `test_get_cities_returns_seeded_defaults` — GET возвращает СПБ, МСК, ВН
    - `test_add_city` — POST создаёт новый город
    - `test_add_duplicate_city_returns_400` — дубликат → 400
    - `test_delete_city` — DELETE soft delete, город не в списке
    - `test_delete_city_with_contracts_returns_409` — 409 при активных договорах
    - `test_readd_deleted_city_restores_it` — повторный POST восстанавливает удалённый

- [ ] **1.15. E2E тесты удаления агентов**
  - **Агент:** Test Runner Agent
  - **Файлы:** `tests/e2e/test_agents_delete.py` (NEW)
  - **Тест-кейсы:**
    - `test_delete_agent` — soft delete работает
    - `test_delete_agent_with_contracts_returns_409` — 409 при активных договорах
    - `test_delete_nonexistent_agent_returns_404` — 404
    - `test_delete_requires_permission` — 403 без права agents.delete

- [ ] **1.16. DB тесты SQLite для городов**
  - **Агент:** Test Runner Agent
  - **Файлы:** `tests/db/test_cities_local.py` (NEW)
  - **Тест-кейсы:**
    - `test_cities_table_created_on_migration` — таблица создана
    - `test_cities_seeded_from_config` — seed из config.py
    - `test_add_and_get_city` — добавление + получение
    - `test_delete_city_soft` — мягкое удаление

---

## Задача 2: QA прав доступа

### 2.1. Анализ кода прав

- [ ] **2.1.1. Инвентаризация всех 34 permissions и их использования**
  - **Агент:** QA Monitor Agent
  - **Файлы:** `server/permissions.py:18-63`, все роутеры в `server/routers/`
  - **Что проверить:**
    - Все 34 права из `ALL_PERMISSIONS` используются хотя бы в одном endpoint (через `require_permission`)
    - Нет "мёртвых" прав, которые объявлены, но нигде не проверяются
    - Нет endpoint-ов, которые должны проверять право, но не проверяют
  - **Формат отчёта:** Таблица: `Право → Файл:строка → Endpoint → Статус (OK / Не используется / Отсутствует проверка)`

- [ ] **2.1.2. Проверка DEFAULT_ROLE_PERMISSIONS**
  - **Агент:** QA Monitor Agent
  - **Файлы:** `server/permissions.py:102-122`
  - **Что проверить:**
    - Соответствие дефолтных прав ролей бизнес-логике:
      - Руководитель студии — полный доступ (SUPERUSER_ROLES)
      - Старший менеджер — расширенный набор
      - СДП, ГАП — reset_designer/draftsman + messenger
      - Менеджер — ограниченный набор
      - ДАН — supervision.complete_stage + messenger
    - Нет ли ролей, которые должны иметь право, но не имеют (и наоборот)

- [ ] **2.1.3. Проверка SUPERUSER_ROLES**
  - **Агент:** QA Monitor Agent
  - **Файлы:** `server/permissions.py:125`
  - **Что проверить:**
    - `SUPERUSER_ROLES = {"admin", "director", "Руководитель студии"}` — корректность
    - Суперюзер обходит все проверки прав (не попадает в `require_permission`)

### 2.2. E2E тесты прав доступа

- [ ] **2.2.1. Тестирование каждого endpoint с разными ролями**
  - **Агент:** Test Runner Agent
  - **Файлы:** `tests/e2e/test_permissions_audit.py` (NEW)
  - **Что тестировать для каждого protected endpoint:**
    - Запрос с ролью, имеющей право → 200/201
    - Запрос с ролью, НЕ имеющей право → 403
    - Запрос без авторизации → 401
  - **Группы endpoints:**
    - Сотрудники: employees.create, employees.update, employees.delete
    - CRM: crm_cards.update, crm_cards.move, crm_cards.delete, crm_cards.assign_executor, crm_cards.delete_executor, crm_cards.reset_stages, crm_cards.reset_approval, crm_cards.complete_approval, crm_cards.reset_designer, crm_cards.reset_draftsman
    - Надзор: supervision.update, supervision.move, supervision.pause_resume, supervision.reset_stages, supervision.complete_stage, supervision.delete_order
    - Платежи: payments.create, payments.update, payments.delete
    - Зарплаты: salaries.create, salaries.update, salaries.delete
    - Ставки: rates.create, rates.delete
    - Агенты: agents.create, agents.update, agents.delete (NEW)
    - Города: cities.create, cities.delete (NEW)
    - Мессенджер: messenger.create_chat, messenger.delete_chat, messenger.view_chat

### 2.3. Проверка UI прав

- [ ] **2.3.1. PermissionsMatrixWidget — загрузка**
  - **Агент:** QA Monitor Agent
  - **Файлы:** `ui/permissions_matrix_widget.py:127-220`
  - **Что проверить:**
    - Виджет загружает матрицу с сервера (`api_client.get_role_permissions_matrix()`)
    - Fallback на `DEFAULT_ROLE_PERMISSIONS` при ошибке загрузки
    - Все 34+ прав отображаются (+ 3 новых: agents.delete, cities.create, cities.delete)
    - 6 ролей отображаются как столбцы

- [ ] **2.3.2. PermissionsMatrixWidget — сохранение**
  - **Агент:** QA Monitor Agent
  - **Что проверить:**
    - Кнопка "Сохранить" отправляет обновлённую матрицу на сервер
    - Кнопка "Сбросить по умолчанию" возвращает к DEFAULT
    - Изменения сохраняются между сессиями (перезагрузка)

### 2.4. Исправление бага crm.update

- [ ] **2.4.1. Баг: 'crm.update' vs 'crm_cards.update' в crm_tab.py:113**
  - **Агент:** Debugger Agent → Backend Agent
  - **Файлы:** `ui/crm_tab.py:113`
  - **Описание бага:**
    - В `crm_tab.py:113` используется `_has_perm(employee, api_client, 'crm.update')`
    - В `server/permissions.py` правильное имя: `'crm_cards.update'`
    - Права `'crm.update'` НЕ СУЩЕСТВУЕТ в системе → `_has_perm` всегда возвращает `False` (если не суперюзер)
    - Это значит, что drag-and-drop в CRM Kanban может быть заблокирован для всех НЕ-суперюзеров
  - **Исправление:** Заменить `'crm.update'` на `'crm_cards.move'` (drag-and-drop = перемещение)
  - **Также проверить:**
    - `crm_tab.py:2339` — кнопки редактирования (какое право используется?)
    - `crm_tab.py:2411` — кнопка замера
    - `crm_tab.py:2443` — кнопка ТЗ
  - **Критерий готовности:** Все проверки прав в crm_tab.py используют корректные имена из permissions.py

---

## Задача 3: QA основной CRM — 14 вариаций карточек

### Матрица вариаций

| # | Тип проекта | Подтип | Агент | Стадий |
|---|---|---|---|---|
| 1 | Индивидуальный | Полный (с 3д визуализацией) | ФЕСТИВАЛЬ | 7 |
| 2 | Индивидуальный | Полный (с 3д визуализацией) | ПЕТРОВИЧ | 7 |
| 3 | Индивидуальный | Эскизный (с коллажами) | ФЕСТИВАЛЬ | 7 |
| 4 | Индивидуальный | Эскизный (с коллажами) | ПЕТРОВИЧ | 7 |
| 5 | Индивидуальный | Планировочный | ФЕСТИВАЛЬ | 7 |
| 6 | Индивидуальный | Планировочный | ПЕТРОВИЧ | 7 |
| 7 | Шаблонный | Стандарт | ФЕСТИВАЛЬ | 6 |
| 8 | Шаблонный | Стандарт | ПЕТРОВИЧ | 6 |
| 9 | Шаблонный | Стандарт с визуализацией | ФЕСТИВАЛЬ | 6 |
| 10 | Шаблонный | Стандарт с визуализацией | ПЕТРОВИЧ | 6 |
| 11 | Шаблонный | Проект ванной комнаты | ФЕСТИВАЛЬ | 6 |
| 12 | Шаблонный | Проект ванной комнаты | ПЕТРОВИЧ | 6 |
| 13 | Шаблонный | Проект ванной комнаты с визуализацией | ФЕСТИВАЛЬ | 6 |
| 14 | Шаблонный | Проект ванной комнаты с визуализацией | ПЕТРОВИЧ | 6 |

### Стадии

**Индивидуальный** (INDIVIDUAL_COLUMNS — 7 стадий):
1. Новый заказ
2. В ожидании
3. Стадия 1: планировочные решения
4. Стадия 2: концепция дизайна
5. Стадия 3: рабочие чертежи
6. Стадия 4: комплектация
7. Выполненный проект

**Шаблонный** (TEMPLATE_COLUMNS — 6 стадий):
1. Новый заказ
2. В ожидании
3. Стадия 1: планировочные решения
4. Стадия 2: рабочие чертежи
5. Стадия 3: 3д визуализация (Дополнительная)
6. Выполненный проект

### Чеклист тестирования (для КАЖДОЙ из 14 вариаций)

- [ ] **3.1. Создание карточки CRM**
  - **Агент:** Test Runner Agent
  - **Файлы:** `tests/e2e/test_crm_14_variations.py` (NEW)
  - **Для каждой вариации (1-14):**
    - [ ] Создать CRM-карточку с нужным типом/подтипом/агентом
    - [ ] Проверить что карточка появилась в колонке "Новый заказ"
    - [ ] Проверить что набор стадий соответствует типу (7 для индивидуального, 6 для шаблонного)

- [ ] **3.2. Таблица сроков (norm_days_templates)**
  - **Агент:** Test Runner Agent
  - **Файлы:** `utils/timeline_calc.py`, `ui/timeline_widget.py`
  - **Для каждой вариации:**
    - [ ] Проверить загрузку norm_days для типа/подтипа/агента через API: `GET /api/norm-days/templates?project_type=X&project_subtype=Y&agent_type=Z`
    - [ ] Проверить что все стадии имеют нормо-дни (не пустые)
    - [ ] Проверить расчёт плановых дат на основе нормо-дней

- [ ] **3.3. Проход по стадиям (move column)**
  - **Агент:** Test Runner Agent
  - **Для каждой вариации:**
    - [ ] Переместить карточку: Новый заказ → Стадия 1 → ... → Выполненный проект
    - [ ] Проверить правила: нельзя вернуть в "Новый заказ" из другой колонки
    - [ ] Проверить: из "В ожидании" — только в previous_column или "Выполненный проект"
    - [ ] Проверить drag-and-drop (если UI тест) или API `PUT /crm/{id}/move`

- [ ] **3.4. Назначение исполнителей по стадиям**
  - **Агент:** Test Runner Agent
  - **Файлы:** `ui/crm_card_edit_dialog.py:259-277`
  - **Для каждой вариации:**
    - [ ] Назначить исполнителя на каждую стадию
    - [ ] Проверить что исполнитель видит карточку в своём представлении
    - [ ] Проверить ограничения исполнителя (Дизайнер, Чертёжник, Замерщик — ограниченный доступ)

- [ ] **3.5. Дашборды**
  - **Агент:** Test Runner Agent
  - **Файлы:** `ui/dashboard_tab.py`, `ui/dashboards.py`, `ui/dashboard_widget.py`
  - **Что проверить:**
    - [ ] Подсчёт карточек по колонкам — корректный
    - [ ] Фильтрация по агенту работает
    - [ ] Фильтрация по типу проекта работает
    - [ ] Данные обновляются после перемещения карточки

- [ ] **3.6. Оплаты**
  - **Агент:** Test Runner Agent
  - **Файлы:** `ui/crm_card_edit_dialog.py:3797-3834`
  - **Для каждой вариации:**
    - [ ] Создать оплату (сумма, дата, тип)
    - [ ] Проверить отображение оплаты в вкладке "Оплаты"
    - [ ] Проверить доступ — только Руководитель/Старший/СДП/ГАП/Менеджер
    - [ ] Проверить редактирование и удаление оплаты

- [ ] **3.7. История проекта**
  - **Агент:** Test Runner Agent
  - **Файлы:** `ui/crm_card_edit_dialog.py:150` (метод `_add_action_history`)
  - **Для каждой вариации:**
    - [ ] Проверить запись в историю при перемещении
    - [ ] Проверить запись при назначении исполнителя
    - [ ] Проверить запись при загрузке/удалении файлов
    - [ ] Проверить отображение истории в вкладке "История по проекту"

- [ ] **3.8. Чат/мессенджер**
  - **Агент:** Test Runner Agent
  - **Файлы:** `ui/crm_card_edit_dialog.py:1025-1044`
  - **Для каждой вариации (выборочно):**
    - [ ] Создать чат для карточки
    - [ ] Открыть чат → MessengerSelectDialog
    - [ ] Проверить право `messenger.create_chat` / `messenger.view_chat`
    - [ ] Проверить удаление чата → `messenger.delete_chat`

- [ ] **3.9. Архивирование**
  - **Агент:** Test Runner Agent
  - **Файлы:** `ui/crm_archive.py:24-231`, `ui/crm_dialogs.py:975-1105`
  - **Для каждой вариации:**
    - [ ] Завершить проект со статусом **СДАН** → проверить зелёную карточку в архиве
    - [ ] Завершить проект со статусом **РАСТОРГНУТ** → проверить красную карточку в архиве
    - [ ] Завершить проект со статусом **АВТОРСКИЙ НАДЗОР** → проверить голубую карточку в архиве + создание supervision_card
    - [ ] Проверить `ArchiveCardDetailsDialog` — данные карточки, оплаты

- [ ] **3.10. Заполнение дат в таблице сроков**
  - **Агент:** Test Runner Agent
  - **Файлы:** `ui/timeline_widget.py`, `utils/timeline_calc.py`
  - **Для каждой вариации:**
    - [ ] Проверить автоматический расчёт плановых дат
    - [ ] Проверить ручное изменение фактических дат
    - [ ] Проверить пересчёт при изменении нормо-дней
    - [ ] Проверить корректность отображения (зелёный — в срок, красный — просрочка)

---

## Задача 4: QA CRM надзора (отдельный отчёт)

### Стадии надзора (VALID_SUPERVISION_COLUMNS — 15 записей, 12 рабочих стадий)

1. Новый заказ
2. В ожидании
3. Стадия 1: Закупка керамогранита
4. Стадия 2: Закупка сантехники
5. Стадия 3: Закупка оборудования
6. Стадия 4: Закупка дверей и окон
7. Стадия 5: Закупка настенных материалов
8. Стадия 6: Закупка напольных материалов
9. Стадия 7: Лепного декора
10. Стадия 8: Освещения
11. Стадия 9: бытовой техники
12. Стадия 10: Закупка заказной мебели
13. Стадия 11: Закупка фабричной мебели
14. Стадия 12: Закупка декора
15. Выполненный проект

### Чеклист тестирования

- [ ] **4.1. Переход из основной CRM в надзор**
  - **Агент:** Test Runner Agent
  - **Файлы:** `ui/crm_dialogs.py:975-1105`, `tests/e2e/test_supervision_qa.py` (NEW)
  - **Что проверить:**
    - [ ] В `CompleteProjectDialog` выбрать "Проект передан в АВТОРСКИЙ НАДЗОР"
    - [ ] Вызывается `self.data.create_supervision_card(supervision_data)`
    - [ ] Карточка в основной CRM получает статус АВТОРСКИЙ НАДЗОР (голубой в архиве)
    - [ ] В CRM надзора появляется новая карточка

- [ ] **4.2. Данные в карточке надзора**
  - **Агент:** Test Runner Agent
  - **Файлы:** `ui/supervision_card_edit_dialog.py:27`
  - **Что проверить:**
    - [ ] Номер договора перенесён из основной CRM
    - [ ] Адрес перенесён
    - [ ] Город перенесён
    - [ ] Агент (тип) перенесён
    - [ ] Площадь перенесена

- [ ] **4.3. Проход по 12 стадиям надзора**
  - **Агент:** Test Runner Agent
  - **Файлы:** `server/routers/supervision_router.py:292-318`
  - **Что проверить:**
    - [ ] Перемещение карточки: Новый заказ → Стадия 1 → ... → Стадия 12 → Выполненный проект
    - [ ] Приостановленную карточку нельзя переместить (кроме выхода из "В ожидании")
    - [ ] `POST /supervision/{id}/complete-stage` — требует право `supervision.complete_stage`
    - [ ] `POST /supervision/{id}/reset-stages` — требует право `supervision.reset_stages`
    - [ ] Маппинг стадий через `SUPERVISION_STAGE_MAPPING` (ui/crm_supervision_tab.py:30-43)

- [ ] **4.4. Назначение сотрудников (ДАН)**
  - **Агент:** Test Runner Agent
  - **Файлы:** `ui/supervision_card_edit_dialog.py:44-45`
  - **Что проверить:**
    - [ ] Роль ДАН (позиция ДАН или вторичная позиция ДАН) определяется корректно
    - [ ] ДАН видит ограниченный набор вкладок (нет вкладки "Редактирование")
    - [ ] ДАН может завершить стадию (`supervision.complete_stage`)
    - [ ] Не-ДАН видит все вкладки

- [ ] **4.5. История, файлы, оплаты надзора**
  - **Агент:** Test Runner Agent
  - **Файлы:** `ui/supervision_card_edit_dialog.py:305-325`
  - **Что проверить:**
    - [ ] Вкладка "Информация о проекте" — история действий отображается
    - [ ] Вкладка "Файлы надзора" — загрузка/удаление файлов по стадиям
    - [ ] Вкладка "Оплаты надзора" — создание/редактирование/удаление оплат
    - [ ] Оплаты привязаны к `supervision_card_id`

- [ ] **4.6. Бюджет/поставщик/комиссия/примечание в timeline entries**
  - **Агент:** Test Runner Agent
  - **Файлы:** `ui/supervision_timeline_widget.py:504`, `server/routers/supervision_timeline_router.py:21`
  - **Что проверить:**
    - [ ] Для каждой стадии: поле "Бюджет" — ввод и сохранение
    - [ ] Поле "Поставщик" — ввод и сохранение
    - [ ] Поле "Комиссия" — ввод и сохранение
    - [ ] Поле "Примечание" — ввод и сохранение
    - [ ] Данные сохраняются на сервере и восстанавливаются при перезагрузке

- [ ] **4.7. Архив надзора**
  - **Агент:** Test Runner Agent
  - **Файлы:** `ui/crm_supervision_tab.py:513-723`
  - **Что проверить:**
    - [ ] Завершённый проект со статусом **СДАН** → зелёная карточка в архиве надзора
    - [ ] Завершённый проект со статусом **РАСТОРГНУТ** → красная карточка в архиве надзора
    - [ ] Используется `ArchiveCard(card_data, self.db, card_type='supervision', ...)` — тот же класс, что и в основной CRM
    - [ ] Кнопка удаления заказа (строки 335-348) — только для Руководителя студии

- [ ] **4.8. Чат надзора**
  - **Агент:** Test Runner Agent
  - **Файлы:** `ui/supervision_card_edit_dialog.py:354-400, 599-680`
  - **Что проверить:**
    - [ ] `sv_create_chat_btn` → `_on_create_supervision_chat` (строка 631) — создание чата
    - [ ] `sv_open_chat_btn` → `_on_open_supervision_chat` (строка 647) — открытие чата
    - [ ] `sv_delete_chat_btn` → `_on_delete_supervision_chat` (строка 660) — удаление чата
    - [ ] Состояние чата загружается при открытии: `self.data.get_supervision_chat(sv_id)` (строка 604)
    - [ ] Приостановка/возобновление (`pause_resume`) — право `supervision.pause_resume`

---

## Граф зависимостей и параллелизм

```
ФАЗА 1 (Сервер):
  1.1 (City модель) ──┐
  1.2 (cities_router) ─┼──> 1.5 (Docker rebuild)
  1.3 (agents DELETE) ─┤
  1.4 (permissions) ───┘

ФАЗА 2 (Клиент данные):         │ ПАРАЛЛЕЛЬНО с Задачей 2
  1.6 (SQLite cities) ──┐        │
  1.7 (API client)  ────┼──> Фаза 3   2.1 (анализ прав) ─┐
  1.8 (DataAccess)  ────┘              2.2 (E2E тесты) ──┤
                                       2.3 (UI прав) ─────┤
ФАЗА 3 (Клиент UI):                   2.4 (баг crm.update)┘
  1.9  (AgentsCitiesWidget) ──┐
  1.10 (AdminDialog вкладка) ─┤
  1.11 (ContractDialog)  ─────┼──> Фаза 4 (Тесты)
  1.12 (города ComboBox) ─────┤
  1.13 (матрица прав) ────────┘

ФАЗА 4 (Тесты):
  1.14 (cities E2E) ──┐
  1.15 (agents E2E) ──┼──> ЗАДАЧИ 3 и 4 (QA)
  1.16 (cities DB) ───┘

ЗАДАЧА 3 (QA CRM):              ЗАДАЧА 4 (QA Надзор):
  3.1-3.10 (14 вариаций) ─────>   4.1-4.8 (отдельный отчёт)
  (после завершения Задачи 1)     (после Задачи 3.9 — АВТОРСКИЙ НАДЗОР)
```

---

## Назначение агентов

| Подзадача | Агент | Описание |
|-----------|-------|----------|
| 1.1–1.5 | Backend Agent | Серверная часть: модели, роутеры, permissions, seed |
| 1.5 | Deploy Agent | Docker rebuild |
| 1.6 | Database Agent | SQLite миграция и CRUD |
| 1.7 | API Client Agent | Клиентские API-методы |
| 1.8 | Worker Agent | DataAccess с fallback |
| 1.9–1.13 | Frontend Agent | UI виджеты, AdminDialog, ContractDialog |
| 1.14–1.16 | Test Runner Agent | E2E и DB тесты |
| 2.1.1–2.1.3 | QA Monitor Agent | Анализ кода прав |
| 2.2.1 | Test Runner Agent | E2E тесты прав |
| 2.3.1–2.3.2 | QA Monitor Agent | UI прав |
| 2.4.1 | Debugger Agent → Backend Agent | Исправление бага |
| 3.1–3.10 | Test Runner Agent + QA Monitor Agent | QA 14 вариаций |
| 4.1–4.8 | Test Runner Agent + QA Monitor Agent | QA надзора |

---

## Список затронутых файлов (сводный)

### Сервер (изменения)

| Файл | Действие | Подзадача |
|------|----------|-----------|
| `server/database.py:174` | EDIT — модель City | 1.1 |
| `server/routers/agents_router.py` | EDIT — DELETE + фильтрация | 1.3 |
| `server/routers/cities_router.py` | NEW — полный CRUD | 1.2 |
| `server/permissions.py:57-58, 95-96` | EDIT — 3 новых права | 1.4 |
| `server/main.py:351` | EDIT — include_router + seed | 1.2 |

### Клиент (изменения)

| Файл | Действие | Подзадача |
|------|----------|-----------|
| `ui/agents_cities_widget.py` | NEW — виджет | 1.9 |
| `ui/admin_dialog.py:81-98` | EDIT — 5-я вкладка | 1.10 |
| `ui/contract_dialogs.py:400-424` | EDIT — убрать кнопки | 1.11 |
| `ui/contract_dialogs.py:1742-1877` | DELETE — add_agent/add_city | 1.11 |
| `ui/contract_dialogs.py:4207+` | DELETE — AgentDialog класс | 1.11 |
| `ui/permissions_matrix_widget.py:42,120` | EDIT — новые права | 1.13 |
| `ui/rates_dialog.py:425` | EDIT — города из DataAccess | 1.12 |
| `ui/crm_tab.py:113` | FIX — crm.update → crm_cards.move | 2.4 |
| `utils/api_client/misc_mixin.py:185` | EDIT — 4 новых метода | 1.7 |
| `utils/data_access.py:1527` | EDIT — 4 новых метода | 1.8 |
| `database/db_manager.py` | EDIT — миграция + CRUD | 1.6 |
| `config.py:95` | NO CHANGE — fallback | — |

### Тесты (новые)

| Файл | Описание | Подзадача |
|------|----------|-----------|
| `tests/e2e/test_cities_crud.py` | CRUD городов | 1.14 |
| `tests/e2e/test_agents_delete.py` | Удаление агентов | 1.15 |
| `tests/db/test_cities_local.py` | SQLite города | 1.16 |
| `tests/e2e/test_permissions_audit.py` | Аудит прав | 2.2 |
| `tests/e2e/test_crm_14_variations.py` | 14 вариаций CRM | 3.1 |
| `tests/e2e/test_supervision_qa.py` | QA надзора | 4.1 |

---

## Оценка трудозатрат

| Задача | Подзадач | Оценка | Приоритет |
|--------|----------|--------|-----------|
| Задача 1: Перенос агентов/городов | 16 | 8–12 часов | P0 (основная) |
| Задача 2: QA прав доступа | 7 | 4–6 часов | P1 |
| Задача 3: QA CRM 14 вариаций | 10 | 6–10 часов | P1 |
| Задача 4: QA CRM надзора | 8 | 4–6 часов | P2 |
| **ИТОГО** | **41** | **22–34 часа** | — |

---

## Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Потеря пользовательских городов при seed | Низкая | Высокое | `INSERT OR IGNORE` / `ON CONFLICT DO NOTHING` |
| Удаление агента с активными договорами | Средняя | Высокое | Проверка 409 Conflict перед soft delete |
| Offline-режим: города не синхронизированы | Средняя | Среднее | Тройной fallback: API → SQLite → config.py |
| rates_dialog ломается без городов из БД | Низкая | Среднее | Fallback `_get_all_cities()` на config |
| Баг crm.update блокирует drag-and-drop | Высокая | Высокое | Исправить в задаче 2.4 (P0) |
| 14 вариаций — не все norm_days настроены | Средняя | Среднее | Проверить в 3.2, добавить недостающие |
| AdminDialog слишком широкий (5 вкладок) | Низкая | Низкое | minSize 1100x700 если нужно |
