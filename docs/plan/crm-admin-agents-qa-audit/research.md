# Research: CRM Admin Agents QA Audit

**Дата:** 2026-02-25
**Задача:** Перенос агентов/городов в администрирование, права доступа, тестирование CRM (14 вариаций), тестирование CRM надзора

---

## Часть 1: Перенос агентов/городов в администрирование

### 1.1 Где хранятся агенты

**config.py:94**
```python
AGENTS = ['ФЕСТИВАЛЬ', 'ПЕТРОВИЧ']
CITIES = ['СПБ', 'МСК', 'ВН']
```
Статические списки — захардкожены в конфиге. Города в `contract_dialogs.py:415` заполняются из этого статичного списка.

**server/routers/agents_router.py** — полноценный роутер:
- `GET /` (строка 29) — список всех агентов из таблицы `Agent`
- `POST /` (строка 45) — добавить агента (требует `agents.create`)
- `GET /{agent_id}` (строка 72) — получить агента по ID
- `PATCH /{name}/color` (строка 91) — обновить цвет (требует `agents.update`)
- **DELETE эндпоинта НЕТ** — удаление агентов не реализовано на бэкенде

**server/database.py:309** — таблица `Agent` существует (поля: id, name, color, status)

### 1.2 Где добавляются агенты/города в UI

**ui/contract_dialogs.py**

Кнопка добавления агента (строки 404–409):
```python
add_agent_btn = IconLoader.create_icon_button('settings2', '', 'Добавить', icon_size=14)
add_agent_btn.setMaximumWidth(28)
add_agent_btn.setFixedHeight(28)
add_agent_btn.setToolTip('Управление агентами')
add_agent_btn.clicked.connect(self.add_agent)
```

Кнопка добавления города (строки 417–422):
```python
add_city_btn = IconLoader.create_icon_button('settings2', '', 'Добавить', icon_size=14)
add_city_btn.setMaximumWidth(28)
add_city_btn.setFixedHeight(28)
add_city_btn.setToolTip('Управление городами')
add_city_btn.clicked.connect(self.add_city)
```

Оба добавлены в `main_layout_form` (форма создания/редактирования договора).

### 1.3 Метод add_agent (contract_dialogs.py:1742)

```python
def add_agent(self):
    dialog = AgentDialog(self)
    if dialog.exec_() == QDialog.Accepted:
        self.reload_agents()
```
Открывает `AgentDialog` — полноценный диалог управления агентами (класс строки 4207–4424).

**AgentDialog** (contract_dialogs.py:4207–4424):
- Показывает список существующих агентов с кнопкой "Изменить цвет"
- Форма добавления нового агента (название + выбор цвета)
- Метод `add_new_agent` (строка 4386) вызывает `self.data.add_agent(name, color)`
- Метод `edit_agent_color` (строка 4399) вызывает `self.data.update_agent_color(name, color)`
- **Удаления агентов НЕТ**

### 1.4 Метод add_city (contract_dialogs.py:1764)

Инлайн-диалог (не отдельный класс), строки 1764–1877:
- Поле ввода названия города
- При подтверждении: `self.city_combo.addItem(text)` — добавляет только локально в комбобокс текущего диалога
- **НЕ сохраняется в БД и не передаётся на сервер**
- Города хранятся только как статический список `CITIES` в `config.py:95`

### 1.5 Серверная сторона: города

Нет отдельной таблицы `City` и нет роутера для управления городами.
`GET /api/statistics/cities` (statistics_router.py:263–276) — возвращает уникальные города из поля `Contract.city`.
Города добавляются просто как строки при создании договора.

### 1.6 DataAccess методы

**utils/data_access.py**:
- `get_all_agents()` (строка 1529) — API с fallback на локальную БД
- `add_agent(name, color)` (строка 1557) — API-first с offline-очередью
- `update_agent_color(name, color)` (строка 1577) — API-first с offline-очередью
- `get_agent_types()` (строка 1596) — получить типы агентов
- `get_cities()` (строка 2907) — только API (`/api/statistics/cities`)
- **`delete_agent()` — отсутствует**
- **`delete_city()` — отсутствует** (города не в БД)

### 1.7 Структура employees_tab.py

**ui/employees_tab.py:21** — класс `EmployeesTab(QWidget)`

Структура:
- Заголовок "Управление сотрудниками" + кнопки поиск/добавить
- Кнопки-фильтры по отделам: Все, Административный, Проектный, Исполнительный (строки 73–78)
- Таблица сотрудников `ProportionalResizeTable`
- Права: `can_edit` — Руководитель студии, Старший менеджер проектов; `can_delete` — только Руководитель студии

Вкладки `QTabWidget` в `employees_tab.py` **отсутствуют** — только фильтры-кнопки.

### 1.8 Структура admin_dialog.py

**ui/admin_dialog.py:38** — `AdminDialog(QDialog)`, открывается только для Руководителя студии

Существующие вкладки (строки 84–98):
1. **"Права доступа"** — `PermissionsMatrixWidget` (ленивая загрузка)
2. **"Настройка чата"** — `MessengerSettingsWidget`
3. **"Настройка норма дней"** — `NormDaysSettingsWidget`
4. **"Тарифы"** — `RatesSettingsWidget`

Все вкладки создаются с ленивой загрузкой через `QTimer.singleShot`.

### 1.9 Выводы по части 1

| Компонент | Состояние |
|---|---|
| Бэкенд AgentRouter GET/POST/PATCH | Готов |
| Бэкенд AgentRouter DELETE | Отсутствует |
| Бэкенд Cities (отдельная таблица) | Отсутствует |
| UI AgentDialog (добавление+цвет) | В contract_dialogs.py:4207 |
| UI удаление агентов | Отсутствует |
| UI города в БД | Отсутствует — только статичный список |
| AdminDialog структура | 4 вкладки, готова к расширению |

---

## Часть 2: Права доступа

### 2.1 Архитектура системы прав

**server/permissions.py** — центральный модуль, 406 строк

**34 именованных права** (PERMISSION_NAMES, строки 18–63):
- Сотрудники: `employees.create`, `employees.update`, `employees.delete`
- Клиенты: `clients.delete`
- Договоры: `contracts.delete`
- CRM (10 прав): `crm_cards.update`, `crm_cards.move`, `crm_cards.delete`, `crm_cards.assign_executor`, `crm_cards.delete_executor`, `crm_cards.reset_stages`, `crm_cards.reset_approval`, `crm_cards.complete_approval`, `crm_cards.reset_designer`, `crm_cards.reset_draftsman`
- Надзор (6 прав): `supervision.update`, `supervision.move`, `supervision.pause_resume`, `supervision.reset_stages`, `supervision.complete_stage`, `supervision.delete_order`
- Платежи: `payments.create`, `payments.update`, `payments.delete`
- Зарплаты: `salaries.create`, `salaries.update`, `salaries.delete`
- Ставки: `rates.create`, `rates.delete`
- Агенты: `agents.create`, `agents.update`
- Мессенджер: `messenger.create_chat`, `messenger.delete_chat`, `messenger.view_chat`

### 2.2 Роли и дефолтные права

**DEFAULT_ROLE_PERMISSIONS** (server/permissions.py:102–122):

| Роль | Права |
|---|---|
| Руководитель студии | Весь базовый набор + employees.create/update/delete + crm_cards.reset_designer/draftsman + salaries.delete |
| Старший менеджер проектов | Базовый набор + employees.update + crm_cards.reset_designer/draftsman |
| СДП | crm_cards.reset_designer, crm_cards.reset_draftsman, messenger.view_chat |
| ГАП | crm_cards.reset_designer, crm_cards.reset_draftsman, messenger.view_chat |
| Менеджер | crm_cards.reset_designer, crm_cards.reset_draftsman |
| ДАН | supervision.complete_stage, messenger.view_chat |

**SUPERUSER_ROLES** (строка 125): `{"admin", "director", "Руководитель студии"}` — полный доступ без проверок.

### 2.3 Хранение прав в БД

Таблица `user_permissions` (строка 171 в permissions.py):
- `employee_id` — FK на сотрудника
- `permission_name` — строковый ключ права

Таблица `role_default_permissions` — матрица дефолтных прав по ролям.

**Логика загрузки прав** (строки 160–187):
1. Проверка кэша (TTL 5 минут)
2. Если в БД есть записи `user_permissions` — берёт из БД
3. Если нет — применяет дефолтные по роли/должности

### 2.4 Серверные эндпоинты (employees_router.py)

```
GET    /api/permissions/definitions      — список всех 34 прав с описаниями
GET    /api/permissions/role-matrix      — матрица прав по ролям
PUT    /api/permissions/role-matrix      — обновить матрицу (требует employees.update)
GET    /api/permissions/{employee_id}    — права конкретного сотрудника
PUT    /api/permissions/{employee_id}    — обновить права сотрудника
POST   /api/permissions/{employee_id}/reset-to-defaults — сброс к дефолтным
```

### 2.5 UI: PermissionsMatrixWidget

**ui/permissions_matrix_widget.py** — встроен в AdminDialog вкладка "Права доступа"

Структура виджета:
- Таблица: строки = права, столбцы = роли
- Кнопки: "Сбросить по умолчанию" + "Сохранить"
- PERMISSION_GROUPS (строки 23–43) — группы прав для отображения
- ROLES (строки 47–54): Руководитель студии, Старший менеджер, СДП, ГАП, Менеджер, ДАН
- DEFAULT_ROLE_PERMISSIONS в виджете (строки 60–93) — для fallback при офлайн

Загрузка данных (`_load_data`): вызывает `data_access.get_permission_definitions()` и `api_client.get_role_permissions_matrix()`

Сохранение (`_on_save`): вызывает `api_client.save_role_permissions_matrix()`

### 2.6 UI: Проверка прав в CRM

**ui/crm_tab.py:91** — функция `_has_perm(employee, api_client, perm_name)`:
```python
def _has_perm(employee, api_client, perm_name):
    perms = _load_user_permissions(employee, api_client)
    if perms is None:
        return True  # суперюзер
    return perm_name in perms
```

Используется в:
- `crm_tab.py:113` — проверка `crm.update` при drag-and-drop
- `crm_tab.py:2339` — кнопки редактирования
- `crm_tab.py:2411` — кнопка замера
- `crm_tab.py:2443` — кнопка ТЗ

### 2.7 DataAccess методы для прав

**utils/data_access.py**:
- `get_employee_permissions(employee_id)` (строка 2762) — API с fallback на DB
- `set_employee_permissions(employee_id, permissions)` (строка 2776) — API-first + offline-очередь
- `reset_employee_permissions(employee_id)` (строка 2806) — только API
- `get_permission_definitions()` (строка 2817) — только API

**utils/api_client/permissions_mixin.py**:
- `get_permission_definitions()` — `GET /api/permissions/definitions`
- `get_employee_permissions(employee_id)` — `GET /api/permissions/{id}`
- `set_employee_permissions(employee_id, permissions)` — `PUT /api/permissions/{id}`
- `reset_employee_permissions(employee_id)` — `POST /api/permissions/{id}/reset-to-defaults`
- `get_role_permissions_matrix()` — `GET /api/permissions/role-matrix`
- `save_role_permissions_matrix(data)` — `PUT /api/permissions/role-matrix`

### 2.8 seed_permissions

**server/permissions.py:248** — запускается при старте сервера:
- Использует PostgreSQL advisory lock (pg_advisory_lock(42))
- Для каждого сотрудника дополняет недостающие права дефолтными
- `INSERT ON CONFLICT DO NOTHING` — атомарная операция

### 2.9 Выводы по части 2

Система прав полностью реализована:
- 34 именованных права
- 6 ролей с дефолтными наборами
- Гранулярная матрица в БД (`user_permissions` + `role_default_permissions`)
- Кэш прав на сервере (TTL 5 мин)
- AdminDialog содержит PermissionsMatrixWidget
- DataAccess + API-клиент содержат все нужные методы

**Потенциальная несогласованность:** в `crm_tab.py` используется `'crm.update'`, а в `permissions.py` правильное имя `'crm_cards.update'` (с подчёркиванием и `_cards`).

---

## Часть 3: Тестирование основной CRM (14 вариаций)

### 3.1 Комбинации вариаций

Из `config.py`:
```python
PROJECT_TYPES = ['Индивидуальный', 'Шаблонный']
PROJECT_SUBTYPES = ['Полный (с 3д визуализацией)', 'Эскизный (с коллажами)', 'Планировочный']
TEMPLATE_SUBTYPES = ['Стандарт', 'Стандарт с визуализацией', 'Проект ванной комнаты', 'Проект ванной комнаты с визуализацией']
AGENTS = ['ФЕСТИВАЛЬ', 'ПЕТРОВИЧ']
```

Матрица вариаций:
- **Индивидуальный** × 3 подтипа × 2 агента = **6 вариантов**
- **Шаблонный** × 4 подтипа × 2 агента = **8 вариантов**
- Итого: **14 вариантов**

### 3.2 Стадии CRM

**server/routers/crm_router.py:462–473** — определения колонок:

**Индивидуальный** (INDIVIDUAL_COLUMNS):
1. Новый заказ
2. В ожидании
3. Стадия 1: планировочные решения
4. Стадия 2: концепция дизайна
5. Стадия 3: рабочие чертежи
6. Стадия 4: комплектация
7. Выполненный проект

**Шаблонный** (TEMPLATE_COLUMNS):
1. Новый заказ
2. В ожидании
3. Стадия 1: планировочные решения
4. Стадия 2: рабочие чертежи
5. Стадия 3: 3д визуализация (Дополнительная)
6. Выполненный проект

### 3.3 Правила перемещения карточек

**server/routers/crm_router.py:482–500**:
- Нельзя вернуть в "Новый заказ" из другой колонки
- Из "В ожидании" — только в `previous_column` или "Выполненный проект"

### 3.4 Класс CRMTab (ui/crm_tab.py:157)

Архитектура Kanban:
- `CRMTab(QWidget)` — основной виджет вкладки
- `CRMColumn(BaseKanbanColumn)` — колонка Kanban (строка 1445)
- `DraggableListWidget(BaseDraggableList)` — список карточек с DnD (строка 100)
- Карточки: `KanbanCard` (строка 1625)

Drag-and-drop проверяет `_has_perm(column.employee, column.api_client, 'crm.update')` (строка 113).

### 3.5 Карточка редактирования CrmCardEditDialog

**ui/crm_card_edit_dialog.py** — 8542 строки

Вкладки диалога (строки 941–962):
1. **"Исполнители и дедлайн"** — основные поля (только не-исполнителям)
2. **"Таблица сроков"** — `ProjectTimelineWidget` (строка 948)
3. **"Данные по проекту"** — данные договора, ТЗ, замер, файлы (строка 951)
4. **"История по проекту"** — лог действий (строка 955, только не-исполнителям)
5. **"Оплаты"** — платежи (строка 962, только Руководитель/Старший/СДП/ГАП/Менеджер)

Чат (кнопки в нижней панели, строки 1025–1044):
- "Создать чат" → `_on_create_chat`
- "Открыть чат" → `_on_open_chat` → `MessengerSelectDialog`

### 3.6 Создание исполнителей

Стадийные исполнители (stage_executors):
- Назначаются в вкладке "Исполнители и дедлайн"
- Для исполнителей ограниченный доступ (строки 266–277)
- `is_executor = _emp_only_pos(employee, 'Дизайнер', 'Чертёжник', 'Замерщик')`

### 3.7 Дашборды

**ui/dashboard_tab.py**, **ui/dashboards.py**, **ui/dashboard_widget.py** — три файла дашбордов
Используют данные из `DataAccess`, работают через API.

### 3.8 Таблица сроков (Timeline)

**utils/timeline_calc.py** — расчёт сроков
**ui/timeline_widget.py** — `ProjectTimelineWidget`
Norm_days настраивается через AdminDialog → "Настройка норма дней" → `NormDaysSettingsWidget`
API: `GET /api/norm-days/templates?project_type=&project_subtype=&agent_type=`

### 3.9 Оплаты в CRM-карточке

Вкладка "Оплаты" (строки 959–962) — виджет `create_payments_tab()`, метод строка 3797.
Доступна только для ролей: Руководитель студии, Старший менеджер проектов, СДП, ГАП, Менеджер.

### 3.10 Файлы в CRM-карточке (вкладка "Данные по проекту")

В `create_project_data_widget()` — вкладка "Данные по проекту":
- ТЗ (техническое задание) — файл, методы `_on_upload_tech_task`, `_delete_tech_task_file` (строки 2144, 2663)
- Референсы — множественные файлы (строка 2339)
- Фотофиксация — множественные файлы (строка 2461)
- Фоновая загрузка превью (строка 7498)

Стадийные файлы хранятся на Яндекс.Диске.

### 3.11 История действий

`_add_action_history(action_type, description, ...)` (строка 150) — логирует события:
- `survey_complete`, `survey_date_changed`, `deadline_changed`, `executor_deadline_changed`
- `file_upload`, `file_delete`, `tech_task_date_changed`

Вкладка "История по проекту" — виджет `create_project_info_widget()`.

### 3.12 Архив CRM

**ui/crm_archive.py**:
- `ArchiveCard(QFrame)` (строка 24) — карточка архива для `card_type='crm'`
- `ArchiveCardDetailsDialog(QDialog)` (строка 231) — детали архивной карточки
- Статусы архива: `СДАН`, `РАСТОРГНУТ`, `АВТОРСКИЙ НАДЗОР` (строка 43)
- Для архива CRM: отображает CRM-оплаты при статусах СДАН/РАСТОРГНУТ/АВТОРСКИЙ НАДЗОР (строки 620–621)

---

## Часть 4: Тестирование CRM надзора

### 4.1 Переход из CRM в надзор

**ui/crm_dialogs.py:975–1105** — диалог завершения проекта `CompleteProjectDialog`:

```python
self.status.addItems(['Проект СДАН', 'Проект передан в АВТОРСКИЙ НАДЗОР', 'Проект РАСТОРГНУТ'])
```

При выборе "АВТОРСКИЙ НАДЗОР" (строки 1066–1072):
```python
if 'АВТОРСКИЙ НАДЗОР' in status:
    result = self.data.create_supervision_card(supervision_data)
```

При статусе АВТОРСКИЙ НАДЗОР (строки 1103–1105):
```python
if 'АВТОРСКИЙ НАДЗОР' in status:
    supervision_card_id = self.data.create_supervision_card(contract_id)
```

Создание карточки надзора привязывается к `contract_id`.

### 4.2 Стадии надзора

**server/routers/supervision_router.py:292–300** — VALID_SUPERVISION_COLUMNS:
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

### 4.3 Маппинг стадий → stage_code

**ui/crm_supervision_tab.py:30–43** — `SUPERVISION_STAGE_MAPPING`:
- Стадия 1 → `STAGE_1_CERAMIC`, ..., Стадия 12 → `STAGE_12_DECOR`
- Используется для связи файлов с timeline

### 4.4 Правила перемещения надзора

**server/routers/supervision_router.py:312–318**:
- Приостановленную карточку нельзя переместить (кроме выхода из "В ожидании")

### 4.5 Диалог карточки надзора (SupervisionCardEditDialog)

**ui/supervision_card_edit_dialog.py:27** — диалог редактирования

Роль `is_dan_role` (строка 45): позиция ДАН или вторичная позиция ДАН.

Вкладки (строки 305–325):
1. **"Редактирование"** — основные поля (только для не-ДАН)
2. **"Таблица сроков"** (строка 311) — `SupervisionTimelineWidget`
3. **"Оплаты надзора"** (строка 314)
4. **"Информация о проекте"** (строка 317) — история
5. **"Файлы надзора"** (строка 325)

Кнопка удаления заказа (строки 335–348) — только для Руководителя студии.

### 4.6 Чат надзора

**supervision_card_edit_dialog.py** — кнопки чата (строки 354–400):
- `sv_create_chat_btn` → `_on_create_supervision_chat` (строка 631)
- `sv_open_chat_btn` → `_on_open_supervision_chat` (строка 647)
- `sv_delete_chat_btn` → `_on_delete_supervision_chat` (строка 660)
- Состояние чата загружается при открытии (строка 86, метод `_load_supervision_chat_state`)
- Данные чата: `self.data.get_supervision_chat(sv_id)` (строка 604)

### 4.7 Приостановка/возобновление надзора

**supervision_card_edit_dialog.py** — кнопка `pause_resume`:
- Право `supervision.pause_resume` (из permissions.py:42)
- Флаг `is_paused` у карточки надзора
- При паузе сохраняет дату, перемещает в "В ожидании"

### 4.8 Архив надзора

**ui/crm_supervision_tab.py:513, 554, 701**:
```python
cards = self.data.get_supervision_cards_archived()
archive_card = ArchiveCard(card_data, self.db, card_type='supervision', ...)
```
Используется тот же класс `ArchiveCard` из `crm_archive.py` с `card_type='supervision'`.

### 4.9 Серверный роутер надзора

**server/routers/supervision_router.py** — эндпоинты:
- `GET /api/supervision/cards` (строка 61) — список с фильтрами (status, address, city, agent_type, дата)
- `POST /api/supervision/` — создать карточку
- `PUT /api/supervision/{id}/move` — переместить
- `POST /api/supervision/{id}/pause` / `resume` — пауза/возобновление
- `POST /api/supervision/{id}/complete-stage` — завершить стадию (требует `supervision.complete_stage`)
- `POST /api/supervision/{id}/reset-stages` — сброс стадий (требует `supervision.reset_stages`)
- `DELETE /api/supervision/{id}` — удалить заказ (требует `supervision.delete_order`)

### 4.10 Timeline надзора

**ui/supervision_timeline_widget.py:504** — `SUPERVISION_STAGES` для timeline
**server/routers/supervision_timeline_router.py:21** — те же стадии на сервере

### 4.11 Оплаты надзора

**server/routers/supervision_router.py:67** — параметр `city` в получении карточек
Оплаты надзора привязаны к `supervision_card_id` (crm_supervision_tab.py:930):
```python
'SELECT id FROM payments WHERE supervision_card_id = ? AND stage_name = ?'
```

---

## Сводная карта файлов

### Часть 1 (агенты/города):
| Файл | Строки | Описание |
|---|---|---|
| `config.py` | 94–95 | AGENTS, CITIES — статические списки |
| `server/routers/agents_router.py` | 1–116 | GET/POST/PATCH агентов, нет DELETE |
| `server/routers/statistics_router.py` | 263–276 | GET /statistics/cities — из поля договора |
| `ui/contract_dialogs.py` | 399–424 | Кнопки добавления агента/города в форме |
| `ui/contract_dialogs.py` | 1742–1747 | `add_agent()` — открывает AgentDialog |
| `ui/contract_dialogs.py` | 1764–1877 | `add_city()` — инлайн, только локально |
| `ui/contract_dialogs.py` | 4207–4424 | `AgentDialog` — добавление/изменение цвета |
| `utils/data_access.py` | 1529–1607 | get/add/update_agent_color, get_agent_types |
| `utils/data_access.py` | 2907–2916 | `get_cities()` — только API |
| `utils/api_client/misc_mixin.py` | 185–243 | get_all_agents, add_agent, update_agent_color |
| `utils/api_client/compat_mixin.py` | 392–395 | `get_cities()` |
| `ui/admin_dialog.py` | 80–98 | 4 существующих вкладки AdminDialog |
| `ui/employees_tab.py` | 21–80 | EmployeesTab, нет вкладок, только фильтры |

### Часть 2 (права доступа):
| Файл | Строки | Описание |
|---|---|---|
| `server/permissions.py` | 18–63 | 34 именованных права |
| `server/permissions.py` | 102–122 | DEFAULT_ROLE_PERMISSIONS по ролям |
| `server/permissions.py` | 125 | SUPERUSER_ROLES |
| `server/permissions.py` | 160–187 | load_permissions с кэшем |
| `server/permissions.py` | 226–241 | require_permission FastAPI dependency |
| `server/permissions.py` | 248–302 | seed_permissions с advisory lock |
| `server/routers/employees_router.py` | 209–345 | Все /permissions/* эндпоинты |
| `ui/permissions_matrix_widget.py` | 23–43 | PERMISSION_GROUPS |
| `ui/permissions_matrix_widget.py` | 47–54 | ROLES список |
| `ui/permissions_matrix_widget.py` | 60–93 | DEFAULT_ROLE_PERMISSIONS (UI копия) |
| `ui/permissions_matrix_widget.py` | 127–220 | Класс PermissionsMatrixWidget |
| `ui/crm_tab.py` | 91–96 | `_has_perm()` — проверка в UI |
| `utils/data_access.py` | 2762–2826 | Методы прав в DataAccess |
| `utils/api_client/permissions_mixin.py` | 1–41 | API методы прав |

### Часть 3 (CRM логика):
| Файл | Строки | Описание |
|---|---|---|
| `server/routers/crm_router.py` | 462–477 | INDIVIDUAL_COLUMNS, TEMPLATE_COLUMNS |
| `server/routers/crm_router.py` | 482–500 | Правила перемещения |
| `ui/crm_tab.py` | 157–158 | CRMTab |
| `ui/crm_tab.py` | 1445 | CRMColumn (Kanban) |
| `ui/crm_card_edit_dialog.py` | 259–277 | Права в диалоге |
| `ui/crm_card_edit_dialog.py` | 941–962 | Вкладки диалога (5 вкладок) |
| `ui/crm_card_edit_dialog.py` | 1025–1044 | Кнопки чата |
| `ui/crm_card_edit_dialog.py` | 3797–3834 | refresh_payments_tab |
| `ui/crm_card_edit_dialog.py` | 7440–7498 | Отложенная загрузка вкладок |
| `ui/crm_archive.py` | 24 | ArchiveCard |
| `ui/crm_archive.py` | 231 | ArchiveCardDetailsDialog |

### Часть 4 (CRM надзора):
| Файл | Строки | Описание |
|---|---|---|
| `ui/crm_dialogs.py` | 975–1105 | CompleteProjectDialog — переход в надзор |
| `server/routers/supervision_router.py` | 61–89 | GET /supervision/cards |
| `server/routers/supervision_router.py` | 292–303 | VALID_SUPERVISION_COLUMNS (14 стадий) |
| `ui/crm_supervision_tab.py` | 30–43 | SUPERVISION_STAGE_MAPPING |
| `ui/crm_supervision_tab.py` | 110 | CRM - Авторский надзор заголовок |
| `ui/crm_supervision_tab.py` | 513–723 | Архив надзора |
| `ui/supervision_card_edit_dialog.py` | 27 | SupervisionCardEditDialog |
| `ui/supervision_card_edit_dialog.py` | 44–45 | is_dan_role |
| `ui/supervision_card_edit_dialog.py` | 305–325 | 5 вкладок карточки надзора |
| `ui/supervision_card_edit_dialog.py` | 335–348 | Кнопка удаления (только Руководитель) |
| `ui/supervision_card_edit_dialog.py` | 354–400 | Кнопки чата надзора |
| `ui/supervision_card_edit_dialog.py` | 599–680 | Методы чата надзора |
