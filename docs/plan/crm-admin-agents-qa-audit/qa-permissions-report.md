# QA Отчёт: Система прав доступа
Дата: 2026-02-25
Аудитор: QA Monitor Agent

---

## 1. Инвентаризация прав

Источник: `server/permissions.py` — PERMISSION_NAMES (всего **37 прав**).

| # | Право | Описание | Endpoint (require_permission) | UI (_has_perm) | Статус |
|---|-------|----------|-------------------------------|----------------|--------|
| 1 | `employees.create` | Создание сотрудников | `employees_router.py:72` | — | OK |
| 2 | `employees.update` | Редактирование сотрудников | `employees_router.py:108,222,233` `norm_days_router.py:107,202` | — | OK |
| 3 | `employees.delete` | Удаление сотрудников | `employees_router.py:157` | — | OK |
| 4 | `clients.delete` | Удаление клиентов | `clients_router.py:149` | — | OK |
| 5 | `contracts.update` | Редактирование договоров | **НЕТ** (update_contract использует только get_current_user) | `contracts_tab.py:309,661` | ПРОБЛЕМА — см. §5.1 |
| 6 | `contracts.delete` | Удаление договоров | `contracts_router.py:248` | — | OK |
| 7 | `crm_cards.update` | Редактирование CRM карточек | `crm_router.py:386` | `crm_tab.py:113,2339,2411,2443` | OK |
| 8 | `crm_cards.move` | Перемещение CRM карточек | `crm_router.py:449` | — | OK |
| 9 | `crm_cards.delete` | Удаление CRM карточек | `crm_router.py:722` | — | OK |
| 10 | `crm_cards.assign_executor` | Назначение исполнителей | `crm_router.py:615` | — | OK |
| 11 | `crm_cards.delete_executor` | Удаление исполнителей | `crm_router.py:783` | — | OK |
| 12 | `crm_cards.reset_stages` | Сброс стадий CRM | `crm_router.py:821` | — | OK |
| 13 | `crm_cards.reset_approval` | Сброс согласования | `crm_router.py:852` | — | OK |
| 14 | `crm_cards.complete_approval` | Завершение согласования | `crm_router.py:1464` | — | OK |
| 15 | `crm_cards.reset_designer` | Сброс отметки дизайнера | `crm_router.py:1378` | — | OK |
| 16 | `crm_cards.reset_draftsman` | Сброс отметки чертежника | `crm_router.py:1410` | — | OK |
| 17 | `supervision.update` | Редактирование карточек надзора | `supervision_router.py:244` | — | OK |
| 18 | `supervision.move` | Перемещение карточек надзора | `supervision_router.py:287` | — | OK |
| 19 | `supervision.pause_resume` | Приостановка/возобновление надзора | `supervision_router.py:441,488` | — | OK |
| 20 | `supervision.reset_stages` | Сброс стадий надзора | `supervision_router.py:583` | — | OK |
| 21 | `supervision.complete_stage` | Завершение стадии надзора | `supervision_router.py:610` | — | OK |
| 22 | `supervision.delete_order` | Удаление заказа надзора | `supervision_router.py:699` | — | OK |
| 23 | `payments.create` | Создание платежей | `payments_router.py:779` | — | OK |
| 24 | `payments.update` | Редактирование платежей | `payments_router.py:671,909,1072,1119,1156` | — | OK |
| 25 | `payments.delete` | Удаление платежей | `payments_router.py:1093` | — | OK |
| 26 | `salaries.create` | Создание зарплат | `salaries_router.py:113` | — | OK |
| 27 | `salaries.update` | Редактирование зарплат | `salaries_router.py:128` | — | OK |
| 28 | `salaries.delete` | Удаление зарплат | `salaries_router.py:148` | — | OK |
| 29 | `rates.create` | Создание/редактирование ставок | `rates_router.py:62,102,172,233,284,299` | — | OK |
| 30 | `rates.delete` | Удаление ставок | `rates_router.py:146,320` | — | OK |
| 31 | `agents.create` | Создание агентов | `agents_router.py:46` | — | OK |
| 32 | `agents.update` | Редактирование агентов | `agents_router.py:93` | — | OK |
| 33 | `agents.delete` | Удаление агентов | `agents_router.py:119` | — | OK |
| 34 | `cities.create` | Создание городов | `cities_router.py:35` | — | OK |
| 35 | `cities.delete` | Удаление городов | `cities_router.py:65` | — | OK |
| 36 | `messenger.create_chat` | Создание чатов | **НЕТ** (messenger_router.py использует только get_current_user) | `crm_card_edit_dialog.py:1172` `supervision_card_edit_dialog.py:77` | ПРОБЛЕМА — см. §5.2 |
| 37 | `messenger.delete_chat` | Удаление чатов | **НЕТ** (messenger_router.py:512 использует get_current_user) | `crm_card_edit_dialog.py:1174` `supervision_card_edit_dialog.py:79` | ПРОБЛЕМА — см. §5.2 |
| 38 | `messenger.view_chat` | Просмотр/открытие чатов | **НЕТ** (нет отдельного endpoint для просмотра) | `crm_card_edit_dialog.py:1173` `supervision_card_edit_dialog.py:78` | INFO — только UI |

---

## 2. Роли и дефолтные права

### 2.1 Сводная таблица

| Роль | Кол-во прав (сервер) | Кол-во прав (клиент) | Соответствие | Проблемы |
|------|----------------------|----------------------|--------------|----------|
| Руководитель студии | 37 (SUPERUSER: все) | 31 | Суперпользователь — в матрице клиент показывает 31 право (без payments.create, payments.update, salaries.create, salaries.update, agents.update, cities.*) | Несоответствие клиент/сервер — см. §5.3 |
| Старший менеджер проектов | 29 прав | 27 прав | Расхождение | §5.3 |
| СДП | 3 | 3 | OK | — |
| ГАП | 3 | 3 | OK | — |
| Менеджер | 2 | 2 | OK | — |
| ДАН | 2 | 2 | OK | — |

### 2.2 Права в PERMISSION_NAMES, отсутствующие в DEFAULT_ROLE_PERMISSIONS

Следующие права существуют в PERMISSION_NAMES, но **не входят ни в одну роль** по умолчанию (недоступны никому кроме superuser через дефолты):

| Право | Роли с правом (через DEFAULT_ROLE_PERMISSIONS) |
|-------|------------------------------------------------|
| `agents.update` | **Нет ни в одной роли** (есть agents.create у _BASE_MANAGER, но update — только через назначение) |
| `cities.create` | _BASE_MANAGER (Руководитель, Старший менеджер) — OK |
| `cities.delete` | _BASE_MANAGER — OK |

**Уточнение**: `agents.update` есть в `agents_router.py:93` с `require_permission("agents.update")`, но **не входит** ни в одну роль в `DEFAULT_ROLE_PERMISSIONS` сервера. Это означает, что только superuser (Руководитель студии/admin/director) смогут редактировать агентов. Остальным роль matrix не предоставит это право.

### 2.3 Права в PermissionsMatrixWidget (клиент), отсутствующие в DEFAULT_ROLE_PERMISSIONS (клиент)

В `ui/permissions_matrix_widget.py` PERMISSION_GROUPS содержит группу `Агенты`:
```python
'Агенты': ['agents.create', 'agents.update'],
```
Но `agents.delete` **отсутствует** в PERMISSION_GROUPS клиента, хотя есть в PERMISSION_NAMES сервера и в DEFAULT_ROLE_PERMISSIONS (_BASE_MANAGER).

---

## 3. Endpoints без защиты require_permission

Список endpoints, защищённых только `get_current_user` (доступны любому авторизованному пользователю):

### 3.1 Потенциально проблемные (мутирующие операции)

| # | Endpoint | Файл:строка | Текущая защита | Рекомендация |
|---|----------|-------------|----------------|--------------|
| 1 | `PUT /{contract_id}` (update_contract) | `contracts_router.py:137` | `get_current_user` | Добавить `require_permission("contracts.update")` — UI уже проверяет, но backend не защищён |
| 2 | `PATCH /{contract_id}/files` (update_contract_files) | `contracts_router.py:194` | `get_current_user` | Добавить `require_permission("contracts.update")` — изменение файлов = часть редактирования |
| 3 | `POST /messenger/create` (create_messenger_chat) | `messenger_router.py:195` | `get_current_user` | Добавить `require_permission("messenger.create_chat")` |
| 4 | `POST /messenger/bind` (bind_messenger_chat) | `messenger_router.py:289` | `get_current_user` | Добавить `require_permission("messenger.create_chat")` |
| 5 | `POST /messenger/supervision` (create_supervision_chat) | `messenger_router.py:358` | `get_current_user` | Добавить `require_permission("messenger.create_chat")` |
| 6 | `DELETE /messenger/{chat_id}` (delete_messenger_chat) | `messenger_router.py:510` | `get_current_user` | Добавить `require_permission("messenger.delete_chat")` |
| 7 | `PUT /permissions/{employee_id}` (update_permissions) | `employees_router.py:295` | `get_current_user` + хардкод роли | Заменить хардкод на `require_permission("employees.update")` или оставить как есть (только superuser) |
| 8 | `POST /permissions/{employee_id}/reset-to-defaults` | `employees_router.py:327` | `get_current_user` + хардкод роли | Аналогично п.7 |
| 9 | `PUT /crm/{card_id}/stages/{stage_name}/complete` (complete_stage) | `crm_router.py:673` | `get_current_user` | Намеренно доступно всем (исполнитель может завершить свою стадию) — OK, но стоит задокументировать |
| 10 | `POST /project_templates` (add_project_template) | `project_templates_router.py:23` | `get_current_user` | Без ограничений — любой авторизованный создаёт шаблон |
| 11 | `DELETE /project_templates/{id}` (delete_project_template) | `project_templates_router.py:79` | `get_current_user` | Любой авторизованный удаляет шаблоны — потенциальная проблема |
| 12 | `PUT /timeline/{card_id}/{entry_id}` (update_timeline_entry) | `timeline_router.py:184` | `get_current_user` | Редактирование таймлайна без ограничений — низкий приоритет |
| 13 | `POST /clients` (create_client) | `clients_router.py:89` | `get_current_user` | Любой авторизованный создаёт клиента — вероятно намеренно |
| 14 | `PUT /clients/{id}` (update_client) | `clients_router.py:114` | `get_current_user` | Любой авторизованный редактирует клиента — вероятно намеренно |
| 15 | `POST /contracts` (create_contract) | `contracts_router.py:85` | `get_current_user` | Создание договора без ограничений — намеренно |

### 3.2 Системные (ожидаемо без ограничений)

| Endpoint | Обоснование |
|----------|-------------|
| Все GET-запросы (список, карточка, etc.) | Чтение данных доступно всем сотрудникам |
| `send_heartbeat` | Системный сигнал жизни |
| `login`, `refresh_token`, `logout`, `get_me` | Авторизация без JWT |
| `create_action_history`, `add_supervision_history` | Лог-запросы от всех |
| Locks endpoints | Блокировки для совместной работы |
| `calculate_payment_amount` | Вычислительный endpoint |
| `messenger/scripts/*` | Скрипты — настройки мессенджера |

---

## 4. Исправленные баги (PERMISSION_NAMES)

| # | Баг | Файл | Было | Стало | Статус |
|---|-----|------|------|-------|--------|
| 1 | Неверное имя права CRM | `ui/crm_tab.py` (ранее) | `crm.update` | `crm_cards.update` | Исправлено |
| 2 | Отсутствующее право в UI | `ui/contracts_tab.py` | — | `contracts.update` | Добавлено |

### 4.1 Проверка UI — все вызовы _has_perm

| Файл | Строка | Имя права | Есть в PERMISSION_NAMES | Статус |
|------|--------|-----------|------------------------|--------|
| `ui/crm_tab.py` | 113 | `crm_cards.update` | Да | OK |
| `ui/crm_tab.py` | 2339 | `crm_cards.update` | Да | OK |
| `ui/crm_tab.py` | 2411 | `crm_cards.update` | Да | OK |
| `ui/crm_tab.py` | 2443 | `crm_cards.update` | Да | OK |
| `ui/contracts_tab.py` | 309 | `contracts.update` | Да | OK |
| `ui/contracts_tab.py` | 661 | `contracts.update` | Да | OK |
| `ui/crm_card_edit_dialog.py` | 1172 | `messenger.create_chat` | Да | OK |
| `ui/crm_card_edit_dialog.py` | 1173 | `messenger.view_chat` | Да | OK |
| `ui/crm_card_edit_dialog.py` | 1174 | `messenger.delete_chat` | Да | OK |
| `ui/supervision_card_edit_dialog.py` | 77 | `messenger.create_chat` | Да | OK |
| `ui/supervision_card_edit_dialog.py` | 78 | `messenger.view_chat` | Да | OK |
| `ui/supervision_card_edit_dialog.py` | 79 | `messenger.delete_chat` | Да | OK |

**Вывод: все UI-проверки используют корректные имена прав. Дублей или опечаток не найдено.**

---

## 5. Найденные проблемы

| # | Проблема | Серьёзность | Файл:строка | Описание |
|---|----------|-------------|-------------|----------|
| 1 | `contracts.update` не защищает сервер | **ВЫСОКАЯ** | `contracts_router.py:137,194` | PUT /{contract_id} и PATCH /{contract_id}/files используют только `get_current_user`. UI проверяет `contracts.update`, но любой авторизованный пользователь может обойти UI и напрямую вызвать API для редактирования любого договора. |
| 2 | Мессенджер: create/delete без require_permission | **СРЕДНЯЯ** | `messenger_router.py:195,289,358,510` | create_chat, bind, create_supervision, delete_chat — все используют только `get_current_user`. Права `messenger.create_chat` и `messenger.delete_chat` существуют в PERMISSION_NAMES и проверяются в UI, но бэкенд их не проверяет. |
| 3 | `agents.delete` отсутствует в PERMISSION_GROUPS клиента | **НИЗКАЯ** | `ui/permissions_matrix_widget.py:43` | Группа `Агенты` в клиентской матрице содержит только `['agents.create', 'agents.update']`, но `agents.delete` есть в PERMISSION_NAMES сервера и входит в _BASE_MANAGER. Администратор не сможет управлять этим правом через UI матрицы. |
| 4 | `agents.update` отсутствует в DEFAULT_ROLE_PERMISSIONS сервера | **СРЕДНЯЯ** | `server/permissions.py:76-131` | _BASE_MANAGER содержит `agents.create`, `agents.delete`, но **не** `agents.update`. Endpoint `PUT /agents/{id}` защищён `require_permission("agents.update")` (agents_router.py:93). В результате даже Руководитель (если не superuser) и Старший менеджер не смогут редактировать цвет агента без явного назначения права. Только admin/director/Руководитель студии через superuser bypass. |
| 5 | Расхождение DEFAULT_ROLE_PERMISSIONS: клиент vs сервер | **СРЕДНЯЯ** | `ui/permissions_matrix_widget.py:60-93` | Клиентские дефолты для Руководителя не включают: `payments.create`, `payments.update`, `salaries.create`, `salaries.update`, `agents.update`, `cities.create`, `cities.delete`, `agents.delete`. Для Старшего менеджера — расхождение по payments.create, payments.update, cities.*. Если admin нажмёт "Сбросить по умолчанию" в UI матрицы, применятся урезанные права. |
| 6 | `project_templates`: удаление без прав | **НИЗКАЯ** | `project_templates_router.py:79` | Любой авторизованный пользователь может удалить шаблон проекта (используется only `get_current_user`). Нет права `project_templates.delete` в PERMISSION_NAMES. |
| 7 | `update_permissions`/`reset_permissions` — хардкод вместо permission | **НИЗКАЯ** | `employees_router.py:303,333` | Проверка `current_user.role not in SUPERUSER_ROLES and current_user.role != 'Руководитель студии'` является дублированием логики из check_permission. При изменении SUPERUSER_ROLES это место может не обновиться. Примечание: 'Руководитель студии' уже есть в SUPERUSER_ROLES (с 68047d4), поэтому второе условие redundant. |
| 8 | Кэш прав — нет инвалидации при изменении роли | **СРЕДНЯЯ** | `server/permissions.py:140-162` | TTL кэша = 5 минут. Если роль сотрудника изменили через `update_employee`, кэш не инвалидируется (нет вызова `invalidate_cache`). Сотрудник будет иметь старые права до истечения TTL. |
| 9 | `get_role_matrix` требует только `employees.update` | **НИЗКАЯ** | `employees_router.py:221` | Чтение матрицы ролей требует `employees.update`. Логичнее использовать более специфическое право или `employees.create` (read vs write mismatch). |
| 10 | `crm.complete_stage` — любой авторизованный | **INFO** | `crm_router.py:673` | Завершение стадии доступно любому. Это намеренно (исполнитель завершает свою стадию), но нет проверки что текущий пользователь является исполнителем данной стадии. |

---

## 6. PermissionsMatrixWidget — детальное сравнение

### 6.1 PERMISSION_GROUPS (клиент) vs PERMISSION_NAMES (сервер)

| Категория | Права в клиенте | Права в сервере | Расхождение |
|-----------|-----------------|-----------------|-------------|
| Сотрудники | 3 | 3 | OK |
| Клиенты | 1 | 1 | OK |
| Договоры | 2 | 2 | OK |
| CRM | 10 | 10 | OK |
| Надзор | 6 | 6 | OK |
| Платежи | 3 | 3 | OK |
| Зарплаты | 3 | 3 | OK |
| Ставки | 2 | 2 | OK |
| Агенты | 2 (`agents.create`, `agents.update`) | 3 (+ `agents.delete`) | **ПРОБЛЕМА: agents.delete отсутствует в клиенте** |
| Города | **ОТСУТСТВУЕТ** | 2 (`cities.create`, `cities.delete`) | **ПРОБЛЕМА: группа Города не отображается в матрице** |
| Мессенджер | 3 | 3 | OK |

**Итого:** В `PERMISSION_GROUPS` клиента отсутствуют: `agents.delete`, `cities.create`, `cities.delete`. Пользователь не может управлять этими правами через UI матрицы.

### 6.2 ROLES (клиент) — полнота

Все 6 ролей из DEFAULT_ROLE_PERMISSIONS сервера представлены в ROLES клиента. Полное совпадение.

### 6.3 Кэш прав

- TTL = 300 секунд (5 минут) — корректный компромисс между нагрузкой на БД и актуальностью.
- `invalidate_cache` вызывается в `set_employee_permissions` и `reset_to_defaults`.
- **Проблема:** `update_employee` (смена роли) не вызывает `invalidate_cache` — см. §5, п.8.

### 6.4 Superuser bypass

```python
if employee.role in SUPERUSER_ROLES or employee.login in SUPERUSER_ROLES:
    return True
```
- SUPERUSER_ROLES = `{"admin", "director", "Руководитель студии"}` — корректно.
- Проверка по `login` позволяет служебному логину "admin" или "director" получить полный доступ независимо от роли. Это особенность архитектуры, не баг.

### 6.5 seed_permissions

- Использует `pg_advisory_lock(42)` — защита от race condition при нескольких workers. Корректно.
- `INSERT ... ON CONFLICT DO NOTHING` — атомарно, не создаёт дублей.
- Пропускает superuser-роли без дефолтных прав (`if emp.role in SUPERUSER_ROLES and emp.role not in DEFAULT_ROLE_PERMISSIONS: continue`) — корректно, т.к. superuser bypass в check_permission.

---

## 7. Рекомендации

### Критические (необходимо исправить)

**1. Добавить `require_permission("contracts.update")` в contracts_router.py:**
```python
# contracts_router.py:137
async def update_contract(
    contract_id: int,
    contract_data: ContractUpdate,
    current_user: Employee = Depends(require_permission("contracts.update")),
    ...
```
Аналогично для `update_contract_files` (строка 194).

**2. Добавить `require_permission` для мессенджера:**
```python
# messenger_router.py:195
current_user: Employee = Depends(require_permission("messenger.create_chat")),
# messenger_router.py:289, 358 — аналогично
# messenger_router.py:512
current_user: Employee = Depends(require_permission("messenger.delete_chat")),
```

### Средние (желательно исправить)

**3. Добавить `agents.update` в _BASE_MANAGER** или явно задокументировать что редактирование агентов — только для superuser.

**4. Добавить `cities.create`, `cities.delete`, `agents.delete` в PERMISSION_GROUPS** клиентской матрицы:
```python
# ui/permissions_matrix_widget.py
'Агенты': ['agents.create', 'agents.update', 'agents.delete'],
'Города': ['cities.create', 'cities.delete'],
```

**5. Синхронизировать DEFAULT_ROLE_PERMISSIONS** клиента с серверным:
- Для `Руководитель студии`: добавить `payments.create`, `payments.update`, `salaries.create`, `salaries.update`, `agents.update`, `agents.delete`, `cities.create`, `cities.delete`.
- Для `Старший менеджер проектов`: добавить `payments.create`, `payments.update`, `cities.create`, `cities.delete`, `agents.delete`.

**6. Инвалидировать кэш при смене роли** в `employees_router.py:update_employee`:
```python
# После db.commit() в update_employee
from permissions import invalidate_cache
invalidate_cache(employee_id)
```

### Низкие (по возможности)

**7. Добавить право `project_templates.delete`** или явно задокументировать что шаблоны — общедоступный ресурс.

**8. Удалить дублирующее условие** в `employees_router.py:303`:
```python
# Было:
if current_user.role not in SUPERUSER_ROLES and current_user.role != 'Руководитель студии':
# Стало (Руководитель студии уже в SUPERUSER_ROLES):
if current_user.role not in SUPERUSER_ROLES:
```

**9. Задокументировать** намеренное отсутствие ограничений на `complete_stage` в crm_router.py — добавить комментарий что исполнитель завершает свою стадию.

---

## 8. Сводная статистика

| Метрика | Значение |
|---------|----------|
| Всего прав в PERMISSION_NAMES | 37 |
| Прав с endpoint-защитой | 34 |
| Прав только в UI (без endpoint) | 3 (messenger.create_chat, messenger.delete_chat, messenger.view_chat) |
| Прав без UI и без endpoint | 0 |
| UI-вызовов _has_perm | 12 |
| Некорректных имён прав в UI | 0 |
| Endpoints с require_permission | 49 |
| Endpoints только с get_current_user (мутирующие) | 15 (из них критических: 6) |
| Найдено проблем критических | 1 |
| Найдено проблем средних | 3 |
| Найдено проблем низких | 6 |
