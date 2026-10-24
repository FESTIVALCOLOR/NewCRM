# Design: Уведомления v2.0

## C4 Component Diagram

```
[Desktop Client (PyQt5)]
    |
    | REST API
    v
[FastAPI Server]
    |-- crm_router.py (workflow endpoints)
    |      |-- dispatch_notification()     → Личные уведомления сотрудникам
    |      |-- trigger_messenger_notification() → Групповые чаты клиентам
    |
    |-- notification_dispatcher.py  ← ЦЕНТРАЛЬНЫЙ ДИСПЕТЧЕР
    |      |-- Создаёт Notification в БД
    |      |-- Проверяет NotificationSettings (project_type фильтры + event flags)
    |      |-- Применяет правила дублирования (4 правила)
    |      |-- Отправляет через Telegram Bot API
    |
    |-- notification_service.py     ← СЕРВИС СКРИПТОВ
    |      |-- build_script_context()  → Формирует все переменные
    |      |-- trigger_messenger_notification() → CRM групповые чаты
    |      |-- trigger_supervision_notification() → Надзор групповые чаты
    |
    |-- notifications_router.py     ← CRUD настроек
    |-- messenger_router.py         ← Управление скриптами + seed
    |
    v
[PostgreSQL]
    |-- employees (+ telegram_username)
    |-- notification_settings (+ notify_individual, notify_template, notify_duplicate_info, notify_revision_info)
    |-- messenger_scripts (+ attach_stage_files)
    |-- notifications
    |-- project_files (stage_files source)
```

## DFD: Поток личных уведомлений (ПОСЛЕ)

```
[Workflow Event] → crm_router.py
    |
    v
dispatch_notification(db, employee_id, event_type, title, message, project_type, ...)
    |
    ├─ 1. Создать Notification в БД
    |
    ├─ 2. Загрузить NotificationSettings
    |     ├─ Проверить event_type flag (notify_assigned, notify_crm_stage, etc.)
    |     ├─ Проверить project_type flag (notify_individual / notify_template / notify_supervision)
    |     └─ Проверить duplicate flags (notify_duplicate_info / notify_revision_info)
    |
    ├─ 3. Если всё включено → отправить Telegram
    |
    └─ 4. Применить правила дублирования:
          Правило 1: Ст.менеджер уведомления → копия Руководителю + Менеджеру
          Правило 2: СДП/ГАП уведомления → копия Ст.менеджеру (без призывов)
          Правило 3: Исправления исполнителям → копия Ст.менеджеру
          Правило 4: Шаблонные Менеджер/ГАП → копия Ст.менеджеру (без призывов)
```

## API Contracts

### Изменения в существующих схемах

#### NotificationSettingsResponse (schemas.py)
```python
class NotificationSettingsResponse(BaseModel):
    employee_id: int
    telegram_enabled: bool
    email_enabled: bool
    notify_crm_stage: bool
    notify_assigned: bool
    notify_deadline: bool
    notify_payment: bool
    notify_supervision: bool
    # НОВЫЕ ПОЛЯ:
    notify_individual: bool      # Индивидуальные проекты
    notify_template: bool        # Шаблонные проекты
    notify_duplicate_info: bool  # Получать дубли от СДП/ГАП
    notify_revision_info: bool   # Получать дубли об исправлениях
    telegram_connected: bool
```

#### NotificationSettingsUpdate (schemas.py)
```python
class NotificationSettingsUpdate(BaseModel):
    telegram_enabled: bool = True
    email_enabled: bool = False
    notify_crm_stage: bool = True
    notify_assigned: bool = True
    notify_deadline: bool = True
    notify_payment: bool = False
    notify_supervision: bool = False
    # НОВЫЕ ПОЛЯ:
    notify_individual: bool = True
    notify_template: bool = True
    notify_duplicate_info: bool = False  # Вкл только для Ст.менеджера
    notify_revision_info: bool = False   # Вкл только для Ст.менеджера
```

### Изменения в моделях БД

#### Employee — добавить telegram_username
```python
telegram_username = Column(String(100), nullable=True)
```

#### NotificationSettings — 4 новых поля
```python
notify_individual = Column(Boolean, default=True)
notify_template = Column(Boolean, default=True)
notify_duplicate_info = Column(Boolean, default=False)
notify_revision_info = Column(Boolean, default=False)
```

#### MessengerScript — добавить attach_stage_files
```python
attach_stage_files = Column(Boolean, default=True)
```

### Новые переменные build_script_context

| Переменная | Источник | Логика |
|-----------|---------|--------|
| client_first_name | Client.full_name.split()[1] | Второе слово ФИО (Фамилия Имя → Имя) |
| senior_manager_username | Employee.telegram_username | Где employee.id = card.senior_manager_id |
| manager_username | Employee.telegram_username | Где employee.id = card.manager_id |
| sdp_username | Employee.telegram_username | Где employee.id = card.sdp_id |
| director_username | Employee.telegram_username | Где employee.position = 'Руководитель студии' |
| dan_username | Employee.telegram_username | Где employee.id = sv_card.dan_id |
| stage_files | ProjectFile → public_link | Все файлы по contract_id + stage |
| review_link | MessengerSetting('review_link') | Глобальная настройка |
| revision_count | StageWorkflowState.revision_count | Через card.id + column_name |
| visit_date | extra_context | Передаётся при вызове |
| pause_reason | extra_context | Передаётся при вызове |
| amount | extra_context | Передаётся при вызове |

### dispatch_notification — новая сигнатура

```python
async def dispatch_notification(
    db: Session,
    employee_id: int,
    event_type: str,
    title: str,
    message: str,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[int] = None,
    project_type: Optional[str] = None,  # НОВЫЙ: 'individual' / 'template' / 'supervision'
    card_id: Optional[int] = None,       # НОВЫЙ: для правил дублирования
    is_duplicate: bool = False,          # НОВЫЙ: предотвращение рекурсии
) -> None:
```

### Правила дублирования — реализация

```python
async def _apply_duplication_rules(
    db, employee_id, event_type, title, message,
    related_entity_type, related_entity_id, project_type, card_id
):
    """Применить 4 правила дублирования после отправки основного уведомления"""
    card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
    if not card:
        return

    recipient = db.query(Employee).filter(Employee.id == employee_id).first()
    if not recipient:
        return

    # Правило 1: Ст.менеджер → Руководитель + Менеджер
    if recipient.position == 'Старший менеджер проектов':
        director = db.query(Employee).filter(Employee.position == 'Руководитель студии').first()
        if director and director.id != employee_id:
            await dispatch_notification(db, director.id, event_type, title, message,
                related_entity_type, related_entity_id, project_type, card_id, is_duplicate=True)
        if card.manager_id and card.manager_id != employee_id:
            await dispatch_notification(db, card.manager_id, event_type, title, message,
                related_entity_type, related_entity_id, project_type, card_id, is_duplicate=True)

    # Правило 2: СДП/ГАП → Ст.менеджер (без призывов)
    if recipient.position in ('СДП', 'ГАП') and card.senior_manager_id:
        info_message = _strip_action_phrases(message)
        await dispatch_notification(db, card.senior_manager_id, 'crm_stage_change',
            title, info_message, related_entity_type, related_entity_id,
            project_type, card_id, is_duplicate=True)

    # Правило 3: Исправления исполнителям → Ст.менеджер
    # (обрабатывается в конкретных вызовах в crm_router)

    # Правило 4: Шаблонные Менеджер/ГАП → Ст.менеджер (без призывов)
    if project_type == 'template' and recipient.position in ('Менеджер', 'ГАП'):
        if card.senior_manager_id and card.senior_manager_id != employee_id:
            info_message = _strip_action_phrases(message)
            await dispatch_notification(db, card.senior_manager_id, 'crm_stage_change',
                title, info_message, related_entity_type, related_entity_id,
                project_type, card_id, is_duplicate=True)
```

## Стратегия тестирования

1. **Unit-тесты** dispatch_notification: проверка фильтров event_type + project_type
2. **Unit-тесты** duplication rules: проверка 4 правил отдельно
3. **Unit-тесты** build_script_context: все новые переменные
4. **E2E-тесты** workflow endpoints: проверка что dispatch_notification вызывается
5. **UI-тесты**: новые чекбоксы настроек отображаются корректно
