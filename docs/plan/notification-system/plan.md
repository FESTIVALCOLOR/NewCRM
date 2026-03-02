# Система уведомлений о дедлайнах — План реализации

## Текущее состояние
- `server/services/notification_service.py` — уведомления в Telegram-чат проекта при workflow-событиях
- `trigger_messenger_notification()` — отправляет по скриптам (project_start, stage_complete, project_end)
- Привязка к `MessengerChat` → `telegram_chat_id`

## Цель
Добавить уведомления о приближающихся/просроченных дедлайнах по 3 каналам:
1. **Telegram-бот** — личные уведомления исполнителю
2. **CRM popup** — всплывающее уведомление в клиенте при открытии
3. **OS desktop** — через plyer (Windows toast)

## Архитектура

### 1. Серверный планировщик (cron-задача)
- `server/services/deadline_checker.py` — проверка дедлайнов раз в час
- Запускается через `apscheduler` или `asyncio.create_task` при старте сервера
- Проверяет:
  - StageExecutor.deadline < today → `ПРОСРОЧЕН`
  - StageExecutor.deadline - today <= 1 → `ЗАВТРА ДЕДЛАЙН`
  - SupervisionCard.deadline → аналогично
  - SupervisionTimelineEntry.plan_date → аналогично

### 2. Модель уведомлений (БД)
```sql
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    recipient_id INTEGER REFERENCES employees(id),
    notification_type VARCHAR(30),  -- 'deadline_warning', 'deadline_overdue', 'stage_complete'
    entity_type VARCHAR(30),        -- 'crm_card', 'supervision_card'
    entity_id INTEGER,
    title VARCHAR(255),
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    sent_telegram BOOLEAN DEFAULT FALSE,
    sent_desktop BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 3. API endpoints
- `GET /api/notifications/unread` — список непрочитанных (для CRM popup)
- `POST /api/notifications/{id}/read` — пометить прочитанным
- `GET /api/notifications/count` — количество непрочитанных (для бейджа)

### 4. Клиентская часть
- Фоновый поллинг `/api/notifications/unread` каждые 60 сек
- Бейдж на иконке колокольчика в шапке MainWindow
- Панель уведомлений (выпадающая) при клике
- OS toast через `plyer.notification.notify()` при появлении нового уведомления

### 5. Типы уведомлений
| Тип | Когда | Кому | Текст |
|-----|-------|------|-------|
| deadline_warning | deadline - 1 раб.день | Исполнитель | «Дедлайн по {стадия}: завтра {дата}» |
| deadline_overdue | deadline < today | Исполнитель + СДП | «ПРОСРОЧЕН дедлайн по {стадия} на {N} дн.» |
| stage_complete | workflow submit/accept | СДП / Менеджер | «{ФИО} сдал работу: {стадия}» |
| client_approved | workflow client-ok | Исполнитель | «Клиент согласовал: {стадия}» |
| supervision_deadline | plan_date - 2 дня | ДАН / Старший менеджер | «Закупка {стадия}: дедлайн {дата}» |

## Приоритет реализации
1. Модель Notification + миграция
2. Серверный deadline_checker
3. API endpoints
4. Telegram-бот (личные сообщения)
5. CRM popup + бейдж
6. OS desktop (plyer)

## Зависимости
- `apscheduler` — планировщик задач (pip install)
- `plyer` — OS уведомления (уже в requirements.txt)
- Telegram Bot API — уже подключен через telegram_service.py
