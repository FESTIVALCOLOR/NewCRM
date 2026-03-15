# Roadmap: Уведомления v2.0

## Оглавление

- ⬜ Этап 1: DB миграция (Employee, NotificationSettings, MessengerScript)
- ⬜ Этап 2: Schemas (NotificationSettingsResponse/Update)
- ⬜ Этап 3: notification_dispatcher — project_type фильтры + дублирование
- ⬜ Этап 4: notification_service — переменные + project_type фильтр скриптов
- ⬜ Этап 5: crm_router — dispatch_notification во все workflow endpoints
- ⬜ Этап 6: messenger_router — seed ~40 скриптов из документации
- ⬜ Этап 7: notifications_router — CRUD для новых полей настроек
- ⬜ Этап 8: UI — панель настроек уведомлений сотрудника
- ⬜ Этап 9: Тесты + Gate Check
- ⬜ Этап 10: PR + CI

---

## ПЛАН

**РЕЖИМ:** full
**СЛОИ:** server (database, routers, services), client (ui, utils)
**ЭТАЛОН:** docs/notifications-scripts-guide.md (read-only)

## Этап 1: DB миграция

**Файлы:** server/database.py
**Агент:** Worker (inline, <10 строк)

### 1.1 Employee — добавить telegram_username
```
telegram_username = Column(String(100), nullable=True)
```
После `telegram_link_token_expires` (строка 77).

### 1.2 NotificationSettings — 4 новых поля
```
notify_individual = Column(Boolean, default=True)
notify_template = Column(Boolean, default=True)
notify_duplicate_info = Column(Boolean, default=False)
notify_revision_info = Column(Boolean, default=False)
```
После `notify_supervision` (строка 268).

### 1.3 MessengerScript — добавить attach_stage_files
```
attach_stage_files = Column(Boolean, default=True)
```
После `use_auto_deadline` (строка 890).

---

## Этап 2: Schemas

**Файлы:** server/schemas.py
**Агент:** Worker (inline)

### 2.1 NotificationSettingsResponse — 4 новых поля
Добавить после `notify_supervision`:
- notify_individual: bool
- notify_template: bool
- notify_duplicate_info: bool
- notify_revision_info: bool

### 2.2 NotificationSettingsUpdate — 4 новых поля
Добавить с дефолтами:
- notify_individual: bool = True
- notify_template: bool = True
- notify_duplicate_info: bool = False
- notify_revision_info: bool = False

---

## Этап 3: notification_dispatcher — расширение

**Файлы:** server/services/notification_dispatcher.py
**Агент:** Backend Agent (>10 строк)

### 3.1 Добавить параметр project_type в dispatch_notification
Новые параметры: project_type, card_id, is_duplicate

### 3.2 Добавить проверку project_type фильтров
```python
# После проверки event_flag_map:
project_type_flag_map = {
    'individual': settings.notify_individual,
    'template': settings.notify_template,
    'supervision': settings.notify_supervision,
}
if project_type and not project_type_flag_map.get(project_type, True):
    db.commit()
    return
```

### 3.3 Добавить проверку дубль-флагов
```python
if is_duplicate:
    # Для информационных дублей — проверить отдельные флаги
    if not settings.notify_duplicate_info:
        db.commit()
        return
```

### 3.4 Реализовать _apply_duplication_rules()
4 правила из документации раздел 5:
1. Ст.менеджер → Руководитель + Менеджер
2. СДП/ГАП → Ст.менеджер (без призывов)
3. Исправления → Ст.менеджер (инфо)
4. Шаблонные Менеджер/ГАП → Ст.менеджер (без призывов)

### 3.5 Реализовать _strip_action_phrases()
Убирает "Проверьте.", "Вы — проверяющий.", "Приступайте к работе." из текста.

---

## Этап 4: notification_service — расширение

**Файлы:** server/services/notification_service.py
**Агент:** Backend Agent (>10 строк)

### 4.1 build_script_context — новые переменные
Добавить: client_first_name, *_username (5 шт), stage_files, review_link, revision_count, visit_date, pause_reason, amount

### 4.2 Хелпер _get_stage_files()
Запрос ProjectFile по contract_id + stage → форматирование ссылок.

### 4.3 trigger_messenger_notification — фильтр по project_type
Добавить фильтр `MessengerScript.project_type` при выборе скрипта.

### 4.4 trigger_supervision_notification — новые переменные
Добавить client_first_name, *_username, review_link в контекст надзора.

### 4.5 Отправка stage_files
Если script.attach_stage_files → добавить ссылки на файлы в сообщение.

---

## Этап 5: crm_router — интеграция dispatch_notification

**Файлы:** server/routers/crm_router.py
**Агент:** Backend Agent (>10 строк)

### 5.1 Хелпер _dispatch_crm_notification()
```python
async def _dispatch_crm_notification(db, card, event_type, recipients, message_template, **kwargs):
    """Отправить личное уведомление нескольким получателям"""
```

### 5.2 Создание карточки — assigned уведомления
При создании CRM-карточки → уведомление ст.менеджеру (если не он создал).

### 5.3 Назначение сотрудника — assigned
При назначении дизайнера/чертёжника/СДП/ГАП/менеджера/замерщика.

### 5.4 workflow/submit — crm_stage_change
"Исполнитель сдал работу" → reviewer.

### 5.5 workflow/reject — crm_stage_change
"На исправление" → исполнитель + ст.менеджер (правило 3).

### 5.6 workflow/client-send — crm_stage_change
"Отправлено клиенту" → ст.менеджер (+ исполнитель для стадии 2).

### 5.7 workflow/client-ok — crm_stage_change
"Клиент согласовал" → ст.менеджер + исполнитель.

### 5.8 workflow/sign-act — crm_stage_change
"Акт подписан" → reviewer.

### 5.9 Перемещение по колонкам — crm_stage_change
"Проект перешёл в стадию X" → исполнитель + reviewer.

### 5.10 Перемещение в "Выполненный проект" — crm_stage_change
"Проект завершён" → менеджер + ст.менеджер + СДП + ГАП.

---

## Этап 6: messenger_router — seed скриптов

**Файлы:** server/routers/messenger_router.py
**Агент:** Backend Agent

### 6.1 Полностью переписать seed_default_messenger_scripts()
Заменить 3 generic скрипта на ~40 конкретных из документации:

**CRM индивидуальные (project_type='Индивидуальный'):**
- project_start (1 скрипт)
- stage_complete × 15 подэтапов (1.1, 1.2, 1.3, 1.paid, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.paid, 3, 3.paid)
- project_end (1 скрипт)

**CRM шаблонные (project_type='Шаблонный'):**
- project_start (1 скрипт)
- stage_complete × 4 (Стадия 1, Стадия 1 подэтап 1.2, Стадия 2, Стадия 3)
- project_end (1 скрипт)

**Надзор (project_type='Авторский надзор'):**
- supervision_start (1 скрипт)
- supervision_stage_complete (1 универсальный)
- supervision_visit (1 скрипт)
- supervision_end (1 скрипт)

### 6.2 Добавить миграцию скриптов
Удалить старые 3 скрипта и создать новые (если таблица содержит только legacy).

---

## Этап 7: notifications_router — CRUD

**Файлы:** server/routers/notifications_router.py
**Агент:** Worker (inline)

### 7.1 GET /settings — добавить новые поля в response
### 7.2 PUT /settings — принимать новые поля
### 7.3 Дефолты при создании — учитывать роль сотрудника
- Ст.менеджер: notify_duplicate_info=True, notify_revision_info=True
- ДАН, Ст.менеджер: notify_supervision=True
- Остальные: notify_supervision=False

---

## Этап 8: UI — настройки уведомлений

**Файлы:** ui/notification_settings_widget.py (или аналог)
**Агент:** Frontend Agent (если >10 строк)

### 8.1 Добавить чекбоксы новых настроек
- "Индивидуальные проекты" (notify_individual)
- "Шаблонные проекты" (notify_template)
- "Дублирование (инфо)" (notify_duplicate_info)
- "Исправления (инфо)" (notify_revision_info)

### 8.2 Обновить сохранение/загрузку настроек

---

## Этап 9: Тесты

- Регрессионные UI тесты
- E2E тесты dispatch_notification (если сервер доступен)
- Локальные unit-тесты новых хелперов

---

## Этап 10: PR + CI

- Feature branch: feat/notifications-v2
- PR с описанием всех изменений
- CI green → Docker rebuild

---

## Зависимости

```
Этап 1 (DB) ← Этап 2 (Schemas) ← Этап 7 (Router CRUD)
Этап 1 (DB) ← Этап 3 (Dispatcher)
Этап 1 (DB) ← Этап 4 (Service)
Этап 3 + 4 ← Этап 5 (crm_router интеграция)
Этап 1 ← Этап 6 (seed скриптов)
Этап 2 + 7 ← Этап 8 (UI)
Все ← Этап 9 (Тесты) ← Этап 10 (PR)
```

**Параллелизм:** Этапы 3, 4, 6 можно параллельно после этапа 1.
