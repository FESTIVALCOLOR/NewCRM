# QA-аудит прав доступа v2
Дата: 2026-02-25
Аудитор: QA Monitor Agent (повторный аудит)

---

## Статус предыдущих проблем (П1–П10)

| ID | Описание | Статус | Верификация |
|----|----------|--------|-------------|
| П1 | `contracts.update` не защищал PUT /{contract_id} и PATCH /{contract_id}/files | **ИСПРАВЛЕНО** | `contracts_router.py:140` — `Depends(require_permission("contracts.update"))` на update_contract; строка 201 — аналогично на update_contract_files |
| П2 | Мессенджер: create/delete без require_permission | **ИСПРАВЛЕНО** | `messenger_router.py:205,225,328,397` — все POST /chats/* используют `require_permission("messenger.create_chat")`; строка 549 — DELETE /chats/{id} использует `require_permission("messenger.delete_chat")` |
| П3 | `agents.delete` отсутствовал в PERMISSION_GROUPS клиента | **ИСПРАВЛЕНО** | `ui/permissions_matrix_widget.py:42` — `'Агенты': ['agents.create', 'agents.update', 'agents.delete']`; группа `Города`: строка 43 — `'Города': ['cities.create', 'cities.delete']` — также добавлена |
| П4 | `agents.update` отсутствовал в _BASE_MANAGER сервера | **ИСПРАВЛЕНО** | `server/permissions.py:102` — `"agents.update"` добавлен в `_BASE_MANAGER`; также присутствует в DEFAULT_ROLE_PERMISSIONS для Руководителя и Старшего менеджера через _BASE_MANAGER |
| П5 | Расхождение DEFAULT_ROLE_PERMISSIONS клиент vs сервер | **ИСПРАВЛЕНО** | Клиентские дефолты (`ui/permissions_matrix_widget.py:61–101`) синхронизированы с серверными. Руководитель: 38 прав (полный набор); Старший менеджер: 29 прав с salaries.delete=нет (верно); Города и agents.delete присутствуют |
| П6 | `project_templates`: add/delete без require_permission | **ИСПРАВЛЕНО** | `project_templates_router.py:26` — POST / использует `require_permission("crm_cards.update")`; строка 82 — DELETE использует `require_permission("crm_cards.delete")` |
| П7 | Дублирующее условие роли в update_permissions | **ИСПРАВЛЕНО** | `employees_router.py:307` — `if current_user.role not in SUPERUSER_ROLES:` (без дублирующего `and current_user.role != 'Руководитель студии'`); аналогично строка 337 — `reset_permissions_to_defaults` |
| П8 | Кэш прав не инвалидировался при смене роли | **ИСПРАВЛЕНО** | `employees_router.py:141–143` — после db.commit() в update_employee: `if 'role' in update_data or 'position' in update_data or 'secondary_position' in update_data: invalidate_perm_cache(employee_id)` |
| П9 | GET /permissions/role-matrix требовал `employees.update` | **ИСПРАВЛЕНО** | `employees_router.py:224–231` — `get_role_matrix` теперь использует `Depends(get_current_user)` (чтение матрицы доступно всем авторизованным); PUT /permissions/role-matrix (строка 237) по-прежнему требует `require_permission("employees.update")` |
| П10 | `crm complete_stage` доступен любому без проверки назначения | **ИСПРАВЛЕНО** | `crm_router.py:728–747` — добавлена проверка: `is_card_member = current_user.id in [card.senior_manager_id, card.sdp_id, card.gap_id, card.manager_id]`; `is_stage_executor` — проверка StageExecutor; `is_superuser` — superuser bypass. Если ни одно — 403. |

---

## Новые проблемы

### НП1 — Мессенджер: скрипты изменяются без проверки прав
**Серьёзность: СРЕДНЯЯ**
**Файл:** `server/routers/messenger_router.py`

| Endpoint | Строка | Защита |
|----------|--------|--------|
| POST /scripts (create_messenger_script) | 775–786 | `get_current_user` |
| PUT /scripts/{id} (update_messenger_script) | 789–807 | `get_current_user` |
| DELETE /scripts/{id} (delete_messenger_script) | 810–822 | `get_current_user` |
| PATCH /scripts/{id}/toggle (toggle_messenger_script) | 825–838 | `get_current_user` |
| PUT /settings (update_messenger_settings) | 855–889 | `get_current_user` |

Скрипты мессенджера — критические системные настройки (шаблоны приветственных сообщений, скрипты отправки файлов клиентам). Их создание, редактирование и удаление доступно любому авторизованному пользователю без проверки прав.

**Ожидаемое поведение:** только пользователи с правом `messenger.create_chat` (или специальным правом) должны управлять скриптами.

**Текущее право, подходящее как ограничение:** `messenger.create_chat` (есть у Руководителя, Старшего менеджера; нет у СДП, ГАП, ДАН, Менеджера).

---

### НП2 — Мессенджер: настройки изменяются без проверки прав
**Серьёзность: ВЫСОКАЯ**
**Файл:** `server/routers/messenger_router.py:855`

`PUT /settings` (update_messenger_settings) защищён только `get_current_user`. Настройки содержат API-ключи Telegram (bot_token, api_id, api_hash, phone), что является чувствительными данными. Любой авторизованный пользователь (включая ДАН, Менеджера) может перезаписать Telegram-токены, что нарушит работу мессенджера.

**Рекомендация:** добавить `require_permission("messenger.create_chat")` или, предпочтительнее, ввести отдельное право `messenger.configure` для настроек инфраструктуры.

---

### НП3 — complete_stage_for_executor без проверки прав
**Серьёзность: НИЗКАЯ**
**Файл:** `server/routers/crm_router.py:1607–1639`

`PATCH /cards/{card_id}/stage-executor/{stage_name}/complete` (complete_stage_for_executor) защищён только `get_current_user` без проверки назначения или суперпользователя. Любой авторизованный может завершить стадию за любого исполнителя, зная card_id, stage_name и executor_id.

При этом `complete_stage` (строка 718) — аналогичный endpoint — уже имеет полную проверку (is_card_member, is_stage_executor, is_superuser).

**Несоответствие:** два родственных endpoint-а с разным уровнем защиты.

---

## Итого

| Метрика | Значение |
|---------|----------|
| Проблем в предыдущем аудите | 10 |
| Исправлено | **10 из 10** |
| Осталось нерешённых из П1–П10 | **0** |
| Новых проблем найдено | **3** |
| — высоких | 1 (НП2: настройки мессенджера) |
| — средних | 1 (НП1: скрипты мессенджера) |
| — низких | 1 (НП3: complete_stage_for_executor) |

---

## Детальный отчёт по ключевым файлам

### server/permissions.py — состояние на 2026-02-25

- **PERMISSION_NAMES:** 37 прав — полный набор (сотрудники, клиенты, договоры, CRM, надзор, платежи, зарплаты, ставки, агенты, города, мессенджер)
- **_BASE_MANAGER (строки 76–109):** содержит agents.update (исправление П4), agents.delete, cities.create, cities.delete
- **DEFAULT_ROLE_PERMISSIONS:**
  - Руководитель студии: _BASE_MANAGER + employees.create/update/delete + crm_cards.reset_designer/draftsman + salaries.delete
  - Старший менеджер: _BASE_MANAGER + employees.update + crm_cards.reset_designer/draftsman
  - СДП/ГАП: crm_cards.reset_designer/draftsman + messenger.view_chat
  - Менеджер: crm_cards.reset_designer/draftsman
  - ДАН: supervision.complete_stage + messenger.view_chat
- **SUPERUSER_ROLES:** `{"admin", "director", "Руководитель студии"}` — корректно
- **Кэш:** TTL=300 сек, `invalidate_cache` вызывается корректно

### ui/permissions_matrix_widget.py — состояние на 2026-02-25

- **PERMISSION_GROUPS:** все 11 групп включая Города (исправление П3); Агенты содержит agents.delete (исправление П3)
- **DEFAULT_ROLE_PERMISSIONS клиент:** синхронизированы с сервером (исправление П5)
- **Расхождение клиент vs сервер:** не обнаружено

### server/routers — покрытие require_permission

| Роутер | Мутирующие с require_permission | Без protect (намеренно) |
|--------|---------------------------------|------------------------|
| agents_router.py | POST /, PATCH /{name}/color, DELETE /{id} | GET / |
| cities_router.py | POST /, DELETE /{id} | GET / |
| contracts_router.py | PUT /{id}, PATCH /{id}/files | POST / (создание — намеренно), GET |
| crm_router.py | 11 endpoints | GET, complete_stage (с проверкой назначения) |
| employees_router.py | POST, PUT, DELETE /employees; PUT /permissions/role-matrix | GET, PUT/POST /permissions/{id} (хардкод SUPERUSER) |
| messenger_router.py | POST /chats, /chats/bind, /chats/supervision, /trigger-script, DELETE /chats/{id} | PUT /settings, POST/PUT/DELETE /scripts (**проблема**) |
| payments_router.py | 7 endpoints с require_permission | GET |
| project_templates_router.py | POST /, DELETE /{id} | GET /{contract_id} |
| salaries_router.py | POST, PUT, DELETE | GET |
| rates_router.py | 8 endpoints | GET |
| supervision_router.py | 7 endpoints с require_permission | GET, POST /cards, POST /history |

---

## Рекомендации по новым проблемам

### НП2 (ВЫСОКАЯ) — немедленно

```python
# messenger_router.py:855
async def update_messenger_settings(
    data: MessengerSettingsBulkUpdate,
    current_user: Employee = Depends(require_permission("messenger.create_chat")),
    ...
```

### НП1 (СРЕДНЯЯ) — в следующей итерации

```python
# messenger_router.py:775, 789, 810, 825
current_user: Employee = Depends(require_permission("messenger.create_chat")),
```

### НП3 (НИЗКАЯ) — технический долг

```python
# crm_router.py:1607 — complete_stage_for_executor
# Добавить аналогичную проверку как в complete_stage (строка 728–747):
is_card_member = current_user.id in [card.senior_manager_id, card.sdp_id, ...]
is_stage_executor = db.query(StageExecutor).filter(...).first() is not None
if not (is_card_member or is_stage_executor or is_superuser):
    raise HTTPException(status_code=403, detail="Недостаточно прав")
```
