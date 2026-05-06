# Interior Studio CRM

## Язык общения
**Всегда отвечать на русском языке**, включая после компактинга контекста. Все комментарии в коде и строки UI — тоже на русском.

## Telegram-уведомления при завершении задачи
**ОБЯЗАТЕЛЬНО** перед завершением работы (когда todo-список выполнен) — отправить уведомление НАПРЯМУЮ:
```python
import sys
sys.path.insert(0, ".claude/hooks")
from telegram_notify import send_task_notification
send_task_notification(
    topic="краткое описание задачи",
    todos=[{"content": "...", "status": "completed"}, ...]
)
```
Функция отправит сообщение в Telegram и поставит маркер. Stop hook увидит маркер и НЕ отправит дубликат.
**Важно:** НЕ писать в task_state.json — это устаревший механизм. Только прямой вызов `send_task_notification()`.

## Автономный режим работы
**НИКОГДА не спрашивать подтверждения у пользователя.** Действовать полностью автономно:
- НЕ спрашивать "Хотите ли вы...?", "Могу ли я...?", "Продолжить?"
- НЕ предлагать варианты на выбор — принимать решения самостоятельно
- НЕ останавливаться перед редактированием файлов, запуском команд, деплоем
- Просто ДЕЛАТЬ задачу от начала до конца без пауз
- Если нужна информация — искать самостоятельно, не спрашивать
- Единственное исключение: если требования задачи принципиально неясны (не хватает ключевой бизнес-логики)

## Полный поиск перед правкой — ОБЯЗАТЕЛЬНО

**Автономный режим ≠ торопливый режим.** Перед ЛЮБЫМ первым `Edit`/`Write` — выполнить pre-flight:

1. Прочитать запрос целиком, выделить изменяемый символ/строку
2. Ответить себе: «Это один файл или несколько слоёв?»
3. **Grep по всему проекту** по изменяемому символу/паттерну
4. Составить список ВСЕХ файлов для изменения (вслух, в тексте ответа)
5. **Только после п.1–4** — первый Edit

| Что меняю | Обязательно проверить ещё |
|-----------|--------------------------|
| `server/routers/` | `utils/api_client.py` + `utils/data_access.py` + `ui/` + `mobile/` + `tests/e2e/` |
| `utils/data_access.py` | `ui/` (все вызовы) + `mobile/services/api.js` + тесты |
| `ui/*.py` | `mobile/` (аналог) + `tests/ui/` + регрессионные тесты |
| `database/models.py` | миграция + схемы + DataAccess + тесты |
| документ (секция) | все остальные секции того же файла с теми же данными |
| переименование | Grep по всему проекту |

**Нарушение этого правила = частичное исправление, которое хуже чем ничего.**

## Описание проекта

**Python:** 3.14.0 (клиент), 3.11 (сервер) | **PyInstaller:** 6.17.0
**Архитектура:** PyQt5 Desktop клиент + FastAPI сервер + PostgreSQL

## Карта ключевых файлов

> Читать ЭТОТ раздел вместо grep/Glob при старте любой задачи.

### Клиент — точки входа

| Файл | Назначение |
|------|-----------|
| `main.py` | Точка входа приложения, инициализация Qt |
| `config.py` | URL сервера, настройки подключения |
| `ui/login_window.py` | Окно авторизации, проверка токена |
| `ui/main_window.py` | Главное окно, tab-система, WebSocket подключение |

### Клиент — UI вкладки

| Файл | Назначение |
|------|-----------|
| `ui/dashboard_tab.py` | Дашборд — статистика и виджеты |
| `ui/dashboards.py` | Мультидашборд (набор виджетов) |
| `ui/crm_tab.py` | CRM канбан-доска (активные проекты) |
| `ui/crm_archive.py` | CRM архив (завершённые) |
| `ui/crm_supervision_tab.py` | Надзор (supervision) |
| `ui/contracts_tab.py` | Договоры |
| `ui/clients_tab.py` | Клиенты |
| `ui/employees_tab.py` | Сотрудники |
| `ui/salaries_tab.py` | Зарплаты и выплаты |
| `ui/reports_tab.py` | Отчёты |
| `ui/employee_reports_tab.py` | Отчёты по сотрудникам (детальные) |
| `ui/employee_analytics_tab.py` | Аналитика сотрудников |
| `ui/employee_chats_tab.py` | Чат сотрудников (список комнат) |
| `ui/client_chats_tab.py` | Чат с клиентами (список комнат) |
| `ui/notifications_list_widget.py` | Уведомления |

### Клиент — диалоги

| Файл | Назначение |
|------|-----------|
| `ui/crm_card_edit_dialog.py` | Редактирование CRM карточки |
| `ui/crm_dialogs.py` | Диалоги CRM (создание, история) |
| `ui/supervision_card_edit_dialog.py` | Редактирование карточки надзора |
| `ui/supervision_dialogs.py` | Диалоги надзора |
| `ui/contract_dialogs.py` | Диалоги договоров |
| `ui/rates_dialog.py` | Ставки сотрудников |
| `ui/admin_dialog.py` | Настройки администратора |
| `ui/update_dialogs.py` | Диалог обновления приложения |
| `ui/messenger_admin_dialog.py` | Управление скриптами мессенджера |
| `ui/messenger_select_dialog.py` | Выбор чата для отправки скрипта |
| `ui/chat_members_dialog.py` | Управление участниками чата |

### Клиент — чат-виджеты

| Файл | Назначение |
|------|-----------|
| `ui/chat_room_widget.py` | Комната чата (сообщения, файлы) |
| `ui/chat_message_bubble.py` | Пузырь сообщения |
| `ui/chat_gallery_widget.py` | Галерея медиа в чате |
| `ui/card_chat_widget.py` | Чат внутри CRM карточки |

### Клиент — базовые компоненты

| Файл | Назначение |
|------|-----------|
| `ui/custom_message_box.py` | Кастомный MessageBox и QuestionBox (используются повсюду) |
| `ui/custom_title_bar.py` | Title bar всех frameless окон |
| `ui/custom_combobox.py` | ComboBox с поиском |
| `ui/custom_dateedit.py` | Кастомный DateEdit |
| `ui/base_kanban_tab.py` | Базовый класс для канбан-вкладок (CRM и надзор) |
| `ui/bubble_tooltip.py` | Всплывающие подсказки-пузыри |
| `ui/flow_layout.py` | Flow-layout для динамической раскладки |
| `ui/chart_widget.py` | Виджет графиков (статистика) |

### Клиент — виджеты

| Файл | Назначение |
|------|-----------|
| `ui/timeline_widget.py` | Виджет timeline проекта (CRM карточка) |
| `ui/supervision_timeline_widget.py` | Timeline надзора |
| `ui/supervision_visits_widget.py` | Журнал визитов надзора |
| `ui/global_search_widget.py` | Глобальный поиск по системе |
| `ui/file_list_widget.py` | Список файлов проекта |
| `ui/file_gallery_widget.py` | Галерея файлов проекта |
| `ui/file_preview_widget.py` | Превью файлов (PDF, изображения) |
| `ui/variation_gallery_widget.py` | Галерея вариантов дизайна |
| `ui/notification_settings_widget.py` | Настройки уведомлений |
| `ui/permissions_matrix_widget.py` | Матрица прав доступа |
| `ui/agents_cities_widget.py` | Виджет агентов и городов |
| `ui/norm_days_settings_widget.py` | Настройки нормодней |
| `ui/dashboard_widget.py` | Отдельный виджет дашборда |

### Слой данных — utils/

| Файл | Назначение |
|------|-----------|
| `utils/data_access.py` | **Единый CRUD фасад** (API-first + SQLite fallback) |
| `utils/offline_manager.py` | Offline-режим, очередь операций |
| `utils/sync_manager.py` | Синхронизация SQLite ↔ API |
| `utils/cache_manager.py` | Кэш-менеджер (TTL, инвалидация) |
| `utils/update_manager.py` | Менеджер авто-обновлений приложения |
| `utils/unified_styles.py` | CSS-стили всего приложения |
| `utils/icon_loader.py` | Загрузка SVG иконок |
| `utils/pdf_generator.py` | Генерация PDF отчётов (ReportLab) |
| `utils/pdf_utils.py` | Вспомогательные утилиты PDF |
| `utils/preview_generator.py` | Генерация превью медиа-файлов |
| `utils/yandex_disk.py` | Яндекс.Диск API (загрузка/ссылки) |
| `utils/permissions.py` | Проверка прав текущего пользователя |
| `utils/resource_path.py` | Пути к ресурсам (PyInstaller-safe) |
| `utils/logger.py` | Логирование (настройка handlers) |
| `utils/validators.py` | Валидация вводимых данных |
| `utils/date_utils.py` | Утилиты работы с датами |
| `utils/calendar_helpers.py` | Хелперы calendar (рабочие дни) |
| `utils/timeline_calc.py` | Расчёт timeline на стороне клиента |
| `utils/dialog_helpers.py` | Хелперы для диалогов |
| `utils/tab_helpers.py` | Хелперы вкладок главного окна |
| `utils/table_settings.py` | Сохранение ширины/порядка столбцов таблиц |
| `utils/session_storage.py` | Хранилище токенов сессии |
| `utils/button_debounce.py` | Debounce кнопок (защита от двойного клика) |
| `utils/tooltip_fix.py` | Фикс тултипов Qt (позиционирование) |
| `utils/message_helper.py` | Хелперы формирования сообщений |
| `utils/db_sync.py` | Синхронизация локальной БД |
| `utils/db_security.py` | Безопасность локальной БД |
| `utils/password_utils.py` | Утилиты работы с паролями |
| `utils/add_indexes.py` | Скрипт добавления индексов в БД (запускается вручную) |
| `utils/migrate_passwords.py` | Скрипт миграции паролей plain→hash (однократный запуск) |

### Слой данных — utils/api_client/

| Файл | Назначение |
|------|-----------|
| `utils/api_client/base.py` | HTTP клиент — базовый класс (сборка из mixins) |
| `utils/api_client/exceptions.py` | Исключения API (APIConnectionError, APITimeoutError) |
| `utils/api_client/auth_mixin.py` | API методы авторизации |
| `utils/api_client/crm_mixin.py` | API методы CRM |
| `utils/api_client/supervision_mixin.py` | API методы надзора |
| `utils/api_client/chat_mixin.py` | API методы чата сотрудников |
| `utils/api_client/payments_mixin.py` | API методы выплат |
| `utils/api_client/salaries_mixin.py` | API методы зарплат |
| `utils/api_client/files_mixin.py` | API методы файлов |
| `utils/api_client/clients_mixin.py` | API методы клиентов |
| `utils/api_client/contracts_mixin.py` | API методы договоров |
| `utils/api_client/employees_mixin.py` | API методы сотрудников |
| `utils/api_client/permissions_mixin.py` | API методы прав доступа |
| `utils/api_client/rates_mixin.py` | API методы ставок |
| `utils/api_client/timeline_mixin.py` | API методы timeline |
| `utils/api_client/analytics_mixin.py` | API методы аналитики |
| `utils/api_client/statistics_mixin.py` | API методы статистики |
| `utils/api_client/messenger_mixin.py` | API методы мессенджера |
| `utils/api_client/misc_mixin.py` | Прочие API методы (города, справочники) |
| `utils/api_client/compat_mixin.py` | Методы совместимости |

### База данных — database/

| Файл | Назначение |
|------|-----------|
| `database/db_manager.py` | SQLite manager (offline хранилище) |
| `database/migrations.py` | Миграции локальной SQLite |

### Сервер — server/

| Файл | Назначение |
|------|-----------|
| `server/main.py` | FastAPI app, регистрация роутеров, scheduler |
| `server/auth.py` | JWT токены, хеширование паролей |
| `server/database.py` | SQLAlchemy + PostgreSQL подключение |
| `server/schemas.py` | Pydantic схемы всех сущностей |
| `server/permissions.py` | Матрица прав ролей |
| `server/config.py` | Настройки сервера (.env) |
| `server/constants.py` | Константы должностей, ролей, групп (POSITION_*, ADMIN_POSITIONS и др.) |
| `server/telegram_service.py` | Telegram-бот интеграция (отправка уведомлений) |
| `server/telegram_bot_handlers.py` | Хэндлеры входящих сообщений Telegram-бота |
| `server/email_service.py` | Email-уведомления |
| `server/rate_limit.py` | Rate limiting для API endpoint-ов |
| `server/messenger_schemas.py` | Pydantic схемы мессенджера |
| `server/yandex_disk_service.py` | Яндекс.Диск сервис (серверная сторона) |
| `server/pdf_helper.py` | PDF хелпер (серверная генерация) |
| `server/generate_session.py` | Генерация Pyrogram-сессии для Telegram-бота (запуск в Docker) |

### Сервер — роутеры (server/routers/)

| Файл | Назначение |
|------|-----------|
| `auth_router.py` | POST /login, /refresh, /logout |
| `crm_router.py` | CRUD CRM карточек, workflow |
| `supervision_router.py` | CRUD надзора, этапы |
| `supervision_timeline_router.py` | Timeline надзора |
| `supervision_visits_router.py` | Визиты надзора |
| `contracts_router.py` | CRUD договоров |
| `clients_router.py` | CRUD клиентов |
| `employees_router.py` | CRUD сотрудников |
| `payments_router.py` | Выплаты, расчёты |
| `salaries_router.py` | Зарплаты |
| `rates_router.py` | Ставки сотрудников |
| `timeline_router.py` | Timeline проектов |
| `chat_router.py` | Чат сотрудников (REST) |
| `client_chat_router.py` | Чат с клиентами (REST) |
| `messenger_router.py` | Мессенджер (скрипты, Telegram-чаты) |
| `websocket_router.py` | WebSocket — real-time чат + уведомления |
| `notifications_router.py` | Уведомления пользователей |
| `files_router.py` | Файлы проектов (Яндекс.Диск) |
| `reports_router.py` | Отчёты и статистика |
| `employee_analytics_router.py` | Аналитика сотрудников |
| `dashboard_router.py` | Данные дашборда |
| `statistics_router.py` | Статистика проектов и воронка |
| `sync_router.py` | Синхронизация offline-клиентов |
| `agents_router.py` | CRUD агентов |
| `cities_router.py` | Справочник городов |
| `norm_days_router.py` | Нормодни (шаблоны) |
| `project_templates_router.py` | Шаблоны проектов |
| `survey_router.py` | Опросы клиентов |
| `action_history_router.py` | История действий |
| `locks_router.py` | Блокировки concurrent edit |
| `heartbeat_router.py` | Healthcheck / heartbeat |

### Сервер — сервисы (server/services/)

| Файл | Назначение |
|------|-----------|
| `notification_service.py` | Создание и доставка уведомлений |
| `notification_dispatcher.py` | WebSocket + Web Push + Telegram рассылка |
| `chat_service.py` | Бизнес-логика чата |
| `deadline_checker.py` | APScheduler — проверка дедлайнов |
| `timeline_service.py` | Расчёт timeline проектов |
| `kpi_calculator.py` | Расчёт KPI сотрудников |
| `kpi_snapshot.py` | Снапшоты KPI по месяцам |
| `maintenance_service.py` | Фоновые задачи обслуживания |
| `access_filter.py` | Фильтрация данных по правам доступа |
| `date_helpers.py` | Хелперы дат (серверная сторона) |

### Мобиль PWA — mobile/src/pages/

| Файл | Назначение |
|------|-----------|
| `LoginPage.vue` | Авторизация |
| `DashboardPage.vue` | Дашборд |
| `CrmBoardPage.vue` | CRM доска |
| `CrmCardPage.vue` | Детали CRM карточки |
| `SupervisionPage.vue` | Надзор (список карточек) |
| `SupervisionDetailPage.vue` | Детали карточки надзора |
| `ContractsPage.vue` | Договоры (список) |
| `ContractDetailPage.vue` | Детали договора |
| `ClientsPage.vue` | Клиенты (список) |
| `ClientDetailPage.vue` | Детали клиента |
| `SalariesPage.vue` | Зарплаты |
| `ReportsPage.vue` | Отчёты |
| `EmployeesPage.vue` | Сотрудники |
| `EmployeeReportsPage.vue` | Отчёты по сотрудникам |
| `FilesPage.vue` | Файлы проекта (Яндекс.Диск) |
| `AdminPage.vue` | Административные настройки |
| `EmployeeChatsPage.vue` | Чат сотрудников (список комнат) |
| `EmployeeChatRoomPage.vue` | Комната чата сотрудников |
| `ClientChatsPage.vue` | Чат с клиентами (список) |
| `ClientChatPage.vue` | Клиентский чат (без авторизации) |
| `ClientChatRoomPage.vue` | Комната клиентского чата |
| `NotificationsPage.vue` | Уведомления |
| `NotificationSettingsPage.vue` | Настройки уведомлений |
| `ProfilePage.vue` | Профиль пользователя |
| `ClientRegisterPage.vue` | Регистрация клиента через приглашение |
| `OfflinePage.vue` | Страница offline-режима |
| `ErrorNotFound.vue` | 404 страница |

### Мобиль PWA — mobile/src/stores/

| Файл | Назначение |
|------|-----------|
| `stores/auth.js` | Хранилище авторизации (JWT) |
| `stores/permissions.js` | Права ролей |
| `stores/crm.js` | CRM состояние (карточки, колонки) |
| `stores/notifications.js` | Уведомления + WebSocket |
| `stores/dashboard.js` | Данные дашборда |
| `stores/chatUnread.js` | Счётчики непрочитанных сообщений |
| `stores/clients.js` | Клиенты |
| `stores/references.js` | Справочники (города, типы проектов) |
| `stores/index.js` | Регистрация всех stores |

### Мобиль PWA — mobile/src/composables/

| Файл | Назначение |
|------|-----------|
| `useWebSocket.js` | Глобальный WS с авто-реконнектом и ping |
| `useChatWebSocket.js` | WS конкретной чат-комнаты |
| `usePermission.js` | Хелпер проверки прав в компонентах |
| `useOptimistic.js` | Оптимистичные обновления UI с rollback |
| `useDeadline.js` | Расчёт дедлайнов и рабочих дней |
| `useCalendar.js` | Экспорт событий в календарь (ICS, Google) |
| `usePdfThumbnail.js` | Превью PDF-файлов |
| `usePwaInstall.js` | Установка PWA (beforeinstallprompt) |

### Мобиль PWA — mobile/src/services/

| Файл | Назначение |
|------|-----------|
| `services/api.js` | API-клиент (axios, JWT, auto-refresh) |
| `services/offlineQueue.js` | Offline-очередь операций (IndexedDB) |

### CI / Тесты

| Путь | Назначение |
|------|-----------|
| `.github/workflows/` | CI pipeline (5 jobs) |
| `tests/e2e/` | E2E тесты (нужен сервер) |
| `tests/db/` | Тесты БД (без сервера) |
| `tests/business/` | Бизнес-логика |
| `tests/anti_pattern/` | Регрессионные guards UI |
| `.claude/hooks/telegram_notify.py` | Telegram уведомления о завершении |

## Атрибуты ключевых файлов

> Этот раздел позволяет найти нужный метод/endpoint без открытия файла.

### utils/data_access.py — класс DataAccess

**Режим и состояние:**
`is_online()`, `is_multi_user()`, `force_sync()`, `get_pending_operations_count()`

**Клиенты:**
`get_all_clients()`, `get_clients_paginated()`, `get_client(id)`, `create_client(data)`, `update_client(id, data)`, `delete_client(id)`, `get_contracts_count_by_client(id)`

**Договоры:**
`get_all_contracts()`, `get_contracts_paginated()`, `get_contract(id)`, `create_contract(data)`, `update_contract(id, data)`, `delete_contract(id)`, `check_contract_number_exists(num)`, `get_contracts_count(status, project_type, year)`

**Сотрудники:**
`get_all_employees()`, `get_employees_by_position(pos)`, `get_employee(id)`, `create_employee(data)`, `update_employee(id, data)`, `delete_employee(id)`, `get_employee_active_assignments(id)`

**CRM карточки:**
`get_crm_cards(project_type)`, `get_archived_crm_cards(project_type)`, `get_crm_card(id)`, `create_crm_card(data)`, `update_crm_card(id, data)`, `delete_crm_card(id)`, `move_crm_card(id, column)`, `get_contract_id_by_crm_card(id)`

**CRM workflow:**
`get_workflow_state(card_id)`, `workflow_submit(id)`, `workflow_accept(id)`, `workflow_reject(id, stage, reason, path)`, `workflow_client_send(id)`, `workflow_client_ok(id)`, `workflow_advance_round(id)`, `workflow_close_stage(id)`, `workflow_sign_act(id)`, `workflow_add_extra_round(id, ...)`, `workflow_repair(id)`

**Надзор:**
`get_supervision_cards_active()`, `get_supervision_cards_archived()`, `get_supervision_card(id)`, `create_supervision_card(data)`, `update_supervision_card(id, data)`, `move_supervision_card(id, column)`, `complete_supervision_stage(id, ...)`, `get_supervision_statistics(address, dan_id, manager_id)`

**Выплаты:**
`get_payments()`, `create_payment_record(data)`, `mark_payment_as_paid(id)`, `update_payment_manual(id, data)`, `delete_payment(id)`, `get_payments_by_supervision_card(id)`, `recalculate_payments(contract_id)`

**Зарплаты/ставки:**
`get_template_rates(project_type)`, `save_template_rate(data)`, `save_individual_rate(data)`, `delete_individual_rate(id)`, `save_supervision_rate(data)`, `save_manager_acceptance(data)`, `save_surveyor_rate(data)`

**Timeline:**
`get_project_timeline(contract_id)`, `init_project_timeline(id, data)`, `update_timeline_entry(id, stage, data)`, `get_timeline_summary(id)`, `export_timeline_excel(id)`, `export_timeline_pdf(id)`, `get_supervision_timeline(id)`, `export_supervision_timeline_excel(id)`

**Чат/мессенджер:**
`create_messenger_chat(crm_card_id, type, members)`, `get_messenger_chat(crm_card_id)`, `get_supervision_chat(id)`, `add_member_to_chat(chat_id, emp_id)`, `send_messenger_message(chat_id, text)`, `trigger_script(card_id, type, entity)`, `preview_script(...)`, `send_act(id, text)`, `send_edited_script(...)`

**Уведомления:**
`get_notifications(unread_only)`, `mark_notification_read(id)`, `mark_all_notifications_read()`, `get_notification_settings(emp_id)`, `update_notification_settings(emp_id, data)`

**Права:**
`get_role_permissions_matrix()`, `save_role_permissions_matrix(data)`, `get_employee_permissions(id)`, `set_employee_permissions(id, perms)`, `reset_employee_permissions(id)`, `get_permission_definitions()`

**Дашборд/статистика:**
`get_clients_dashboard_stats()`, `get_contracts_dashboard_stats()`, `get_crm_dashboard_stats()`, `get_employees_dashboard_stats()`, `get_salaries_dashboard_stats()`, `get_salaries_all_payments_stats()`, `get_project_statistics()`, `get_supervision_statistics_report()`, `get_employee_report_data(emp_id, project_type, period)`

**Яндекс.Диск:**
`get_project_files(contract_id)`, `delete_project_file(id)`, `global_search(query)`, `get_cities()`, `get_contract_years()`, `get_current_user()`

---

### server/routers/ — HTTP Endpoints

**auth_router** (prefix `/api`):
```
POST /api/login          → JWT токен
POST /api/refresh        → обновить токен
POST /api/logout         → выход
GET  /api/me             → текущий пользователь
```

**crm_router** (prefix `/api/crm`):
```
GET    /api/crm/cards                              → список карточек (?project_type, ?archived)
GET    /api/crm/cards/{id}                         → карточка
POST   /api/crm/cards                              → создать
PATCH  /api/crm/cards/{id}                         → обновить
PATCH  /api/crm/cards/{id}/column                  → переместить в колонку
DELETE /api/crm/cards/{id}                         → удалить
POST   /api/crm/cards/{id}/stage-executor          → назначить исполнителя
PATCH  /api/crm/cards/{id}/stage-executor/{stage}  → завершить этап
POST   /api/crm/cards/{id}/reset-stages            → сбросить этапы
POST   /api/crm/cards/{id}/reset-stage-by-name     → сбросить конкретный этап
POST   /api/crm/cards/{id}/reset-approval          → сбросить согласование
GET    /api/crm/cards/{id}/workflow/state          → состояние workflow
POST   /api/crm/cards/{id}/workflow/submit         → сдать работу
POST   /api/crm/cards/{id}/workflow/accept         → принять работу
POST   /api/crm/cards/{id}/workflow/reject         → отклонить работу
POST   /api/crm/cards/{id}/workflow/client-send    → отправить клиенту
POST   /api/crm/cards/{id}/workflow/client-ok      → клиент одобрил
POST   /api/crm/cards/{id}/workflow/repair         → ремонт workflow
```

**supervision_router** (prefix `/api/supervision`):
```
GET    /api/supervision/cards            → список (?archived)
GET    /api/supervision/addresses        → адреса
GET    /api/supervision/cards/{id}       → карточка
POST   /api/supervision/cards            → создать
PATCH  /api/supervision/cards/{id}       → обновить
PATCH  /api/supervision/cards/{id}/column           → переместить
POST   /api/supervision/cards/{id}/pause            → приостановить
POST   /api/supervision/cards/{id}/resume           → возобновить
POST   /api/supervision/cards/{id}/complete-stage   → завершить этап
POST   /api/supervision/cards/{id}/reset-stages     → сбросить этапы
DELETE /api/supervision/orders/{id}                 → удалить
GET    /api/supervision/cards/{id}/contract         → ID договора
```

**contracts_router** (prefix `/api/contracts`):
```
GET    /api/contracts/           GET /count
GET    /api/contracts/{id}       POST /api/contracts/
PUT    /api/contracts/{id}       PATCH /{id}/files
DELETE /api/contracts/{id}       POST /fix-all-folders
```

**clients_router** (prefix `/api/clients`):
```
GET/POST /api/clients/    GET/PUT/DELETE /api/clients/{id}
```

**employees_router** (prefix `/api`):
```
GET/POST /api/employees/                   GET/PUT/DELETE /api/employees/{id}
GET  /api/employees/{id}/telegram-info     POST /{id}/create-telegram-token
GET  /api/permissions/definitions          GET/PUT /api/permissions/role-matrix
GET/PUT  /api/permissions/{id}             POST /api/permissions/{id}/reset-to-defaults
```

**payments_router** (prefix `/api/payments`):
```
GET  /api/payments/                 → список (?filters)
GET  /api/payments/calculate        → расчёт суммы
GET  /api/payments/summary          → сводка
GET  /api/payments/by-type          → по типам
GET  /api/payments/all-optimized    → оптимизированный список
POST /api/payments/recalculate      → пересчёт
POST /api/payments/                 → создать
GET  /api/payments/contract/{id}    PATCH /{contract_id}/report-month
GET  /api/payments/crm/{id}         GET /supervision/{id}
PATCH /api/payments/{id}/manual     PATCH /{id}/mark-paid
PUT/DELETE /api/payments/{id}
```

**chat_router** (prefix `/api/chats`):
```
POST   /api/chats/                              → создать чат
GET    /api/chats/                              → список чатов
GET    /api/chats/{id}                          → детали чата
DELETE /api/chats/{id}
GET    /api/chats/{id}/messages                 → сообщения
POST   /api/chats/{id}/messages                 → отправить
PATCH  /api/chats/{id}/messages/{msg_id}        → редактировать
DELETE /api/chats/{id}/messages/{msg_id}
POST   /api/chats/{id}/messages/{msg_id}/read   → прочитать
POST   /api/chats/{id}/files                    → загрузить файл
POST   /api/chats/{id}/messages/{msg_id}/pin    → закрепить
POST   /api/chats/{id}/members                  → добавить участника
DELETE /api/chats/{id}/members/{member_id}      → удалить участника
POST   /api/chats/{id}/invite-links             → создать приглашение
GET/DELETE /api/chats/{id}/invite-links
POST   /api/chats/{id}/forward/{target_id}      → переслать
WS     /ws/chat/{chat_id}                       → WebSocket чата сотрудников
```

**client_chat_router**:
```
GET/POST /client-chat/{token}           → клиентский чат (без авторизации)
GET      /client-chat/{token}/messages  → сообщения
POST     /client-chat/{token}/files     → файл от клиента
GET      /client-chat/{token}/stream    → SSE поток
WS       /ws/client-chat/{token}        → WebSocket клиентского чата
```

**notifications_router** (prefix `/api`):
```
GET /api/notifications                           → список
PUT /api/notifications/{id}/read                 → прочитать
POST /api/notifications/mark-all-read            → все прочитаны
GET/PUT /api/notifications/settings/{emp_id}     → настройки
GET  /api/notifications/push/vapid-public-key    → VAPID ключ (Web Push)
POST /api/notifications/push/subscribe           → подписаться
POST /api/notifications/push/unsubscribe         → отписаться
PUT  /api/notifications/channel/{emp_id}         → обновить канал
POST /api/employees/{id}/send-invite             → пригласить сотрудника
```

**websocket_router**:
```
WS /ws   → главный WebSocket (уведомления real-time)
```

**files_router** (prefix `/api/files`):
```
GET  /api/files/all          GET /updated    GET /public-link
GET  /api/files/list         GET /public-folder
POST /api/files/             → создать запись    POST /upload → загрузить в ЯД
POST /api/files/folder       POST /move-folder   POST /validate
DELETE /api/files/yandex     → удалить из ЯД
GET  /api/files/contract/{id}    POST /scan/{id}
GET  /api/files/stream           GET/DELETE /{id}
```

**dashboard_router** (prefix `/api/dashboard`):
```
GET /api/dashboard/clients    /contracts    /crm       /employees
GET /api/dashboard/salaries   /salaries-by-type  /salaries-all
GET /api/dashboard/salaries-individual  /salaries-template  /salaries-salary  /salaries-supervision
GET /api/dashboard/agent-types    /contract-years
GET /api/dashboard/reports/summary    /reports/clients-dynamics
```

**reports_router** (prefix `/api/reports`):
```
GET /api/reports/employee          → отчёт по сотруднику
GET /api/reports/employee-report   → детальный отчёт
```

---

### Сервисы — ключевые функции

**server/services/notification_service.py:**
`build_script_context(db, card, contract)`, `trigger_messenger_notification(...)`, `send_survey_to_chat(crm_card_id)`, `trigger_supervision_notification(...)`, `send_invites_to_members(chat_id)`

**server/services/notification_dispatcher.py:**
`dispatch_notification(...)` — главная точка отправки (WebSocket + Web Push + Telegram), `_send_web_push(...)`, `_send_telegram(telegram_user_id, title, msg)`

**server/services/chat_service.py:**
Бизнес-логика чата: создание, доставка, участники

**server/services/deadline_checker.py:**
APScheduler job: проверяет дедлайны CRM/Надзор и вызывает `dispatch_notification`

**server/services/timeline_service.py:**
Расчёт нормодней, рабочих дней, дедлайнов этапов

**server/services/kpi_calculator.py + kpi_snapshot.py:**
Расчёт KPI сотрудников по завершённым этапам

---

### utils/ — ключевые классы и функции

**utils/unified_styles.py:**
`get_unified_stylesheet()` → возвращает единый CSS для всего приложения

**utils/icon_loader.py — класс IconLoader:**
`IconLoader.load(name, size)` → QIcon из SVG
`IconLoader.load_colored(name, color, size)` → перекрашенный SVG
`IconLoader.create_icon_button(name, text, tooltip)` → QPushButton с иконкой
`IconLoader.create_action_button(name, tooltip, bg_color, hover_color)` → кнопка-действие

**utils/permissions.py:**
`get_allowed_tabs(employee, api_client)` → список разрешённых вкладок
`has_any_perm(employee, api_client, *perm_names)` → проверка прав
`invalidate_cache(employee_id)` → сброс кэша прав

**utils/offline_manager.py:**
`OfflineManager` — управляет режимом online/offline, очередью отложенных операций

**utils/pdf_generator.py:**
Генерация PDF отчётов через ReportLab. Основные функции: `generate_employee_report()`, `generate_salary_report()`

**utils/yandex_disk.py:**
Яндекс.Диск API: загрузка файлов, получение публичных ссылок, создание папок

---

### UI — ключевые классы и сигналы

**ui/main_window.py — MainWindow(QMainWindow):**
Сигналы: `_sig_update_available(dict)`, `_sig_update_disabled()`, `_sig_update_error(str)`, `_sig_no_updates()`
Методы: `on_tab_changed(index)`, `switch_dashboard(key)`

**ui/crm_tab.py — CRMTab(QWidget):**
Классы: `CRMTab`, `CRMColumn(BaseKanbanColumn)`, `CRMCard(QFrame)`
Сигналы: `CRMColumn.card_moved(int, str, str, str)`
Методы: `load_cards_for_current_tab()`, `load_cards_for_type(project_type)`, `refresh_current_tab()`, `show_crm_statistics(project_type)`, `load_archive_cards(project_type)`

**ui/chat_room_widget.py — ChatRoomWidget:**
Виджет чата с сообщениями, файлами, WebSocket real-time обновлениями

**ui/notifications_list_widget.py — NotificationsListWidget:**
Список уведомлений с фильтрацией и отметкой прочитанных

---

### Мобильная PWA — Pinia Stores (mobile/src/stores/)

**stores/auth.js — useAuthStore:**
Состояние: `user`, `accessToken`, `refreshToken`, `loading`, `error`
Computed: `isAuthenticated`, `fullName`, `userRole`, `userPosition`, `initials`
Действия: `login(username, password)`, `fetchMe()`, `logout()`, `refreshTokens()`
API prefix: `/api/v1/auth/`

**stores/permissions.js — usePermissionsStore:**
Состояние: `permissions[]`, `loaded`
Computed: `isSuperuser` (Руководитель студии / admin / director), `visiblePages`
Действия: `load()`, `has(permName)` → bool
Суперпользователи: positions=['Руководитель студии'], roles=['admin', 'director']

**stores/crm.js — useCrmStore:**
Состояние: `cards[]`, `loading`, `projectType` ('Индивидуальный'/'Шаблонный'), `showArchive`, `selectedCard`, `cardLoading`
Computed: `columns` (сгруппированы по column_name), `roleFilteredCards`, `filteredCards`, `totalCards`, `countIndividual`, `countTemplate`, `columnOrder`
Действия: `loadCards()`, `moveCardOptimistic(cardId, newColumn)`, `rollbackMoveCard(cardId, oldColumn)`

**stores/chatUnread.js — useChatUnreadStore:**
Состояние: `employeeChats[]`, `clientChats[]`
Computed: `totalEmployeeUnread`, `totalClientUnread`, `totalUnread`
Действия: `fetchUnreadCounts()`, `markChatRead(chatId)`, `incrementUnread(chatId)`, `unreadByCardId(cardId)`, `unreadByCardAndType(cardId, type)`

**stores/notifications.js — useNotificationsStore:**
Состояние: `items[]`, `loading`
Computed: `unreadCount`
Действия: `load()`, `markRead(id)`

**stores/dashboard.js — useDashboardStore:**
Состояние: `loading`, `stats`, `clientsStats`, `contractsStats`, `crmStats`, `employeesStats`
Действия: `loadAll()` — параллельно загружает clients/contracts/crm/employees/general

---

### Мобильная PWA — API клиент (mobile/src/services/api.js)

Базовый axios: prefix `/api/v1/`, JWT в Authorization header, auto-refresh при 401.

| Объект | Ключевые методы |
|--------|----------------|
| `dashboardApi` | `getClients()`, `getContracts()`, `getCrm()`, `getEmployees()`, `getReportsSummary()` |
| `statisticsApi` | `getDashboard()`, `getGeneral()`, `getFunnel()`, `getProjects()`, `getContractsByPeriod()`, `getEmployees()` |
| `crmApi` | `getCards(projectType, archived)`, `getCard(id)`, `getWorkflowState(id)`, `moveCard(id, column)`, `updateCard(id, data)`, `assignExecutor(id, data)`, `completeStage(id, stageName, executorId)`, `submitWork(id)`, `acceptWork(id)`, `rejectWork(id, data)`, `sendToClient(id)`, `clientApproved(id)`, `signAct(id)`, `advanceRound(id)`, `closeStage(id)`, `addExtraRound(id)`, `repairWorkflow(id)`, `resetApproval(id)`, `resetStageByName(id, name)`, `getPayments(id)`, `getStageHistory(id)`, `getActionHistory(id)` |
| `clientsApi` | `getList(params)`, `getById(id)`, `create(data)`, `update(id, data)`, `delete(id)` |
| `contractsApi` | `getList(params)`, `getById(id)`, `create(data)`, `update(id, data)`, `delete(id)`, `updateFiles(id, data)` |
| `notificationsApi` | `getList(unreadOnly)`, `markRead(id)`, `getSettings(empId)`, `updateSettings(empId, data)`, `markAllRead(empId)`, `testNotification()` |
| `pushApi` | `getVapidKey()`, `subscribe(subscription)`, `unsubscribe()` |
| `employeesApi` | `getList(params)`, `getById(id)`, `create(data)`, `update(id, data)`, `delete(id)`, `getPermissions(id)`, `updatePermissions(id, data)`, `resetPermissions(id)`, `sendInvite(id)`, `getTelegramInfo(id)`, `connectTelegram(id, code)` |
| `paymentsApi` | `getList(params)`, `calculate(params)`, `create(data)`, `update(id, data)`, `delete(id)`, `markPaid(id, empId)`, `markUnpaid(id)`, `getSummary(params)`, `getByType(params)` |
| `salariesApi` | `getList(params)`, `getReport(params)`, `create(data)`, `update(id, data)`, `delete(id)` |
| `reportsApi` | `getSummary(params)`, `getClientsDynamics(params)`, `getCrmAnalytics(params)`, `getFunnel(params)`, `getAgentTypes()`, `getCities()`, `getContractYears()` |
| `supervisionApi` | `getCards(params)`, `getCard(id)`, `getTimeline(id)`, `getVisits(id)`, `updateCard(id, data)`, `moveCard(id, column)`, `pause(id, reason)`, `resume(id)`, `completeStage(id)`, `createVisit(id, data)`, `updateTimelineEntry(id, stage, data)` |
| `timelineApi` | `get(contractId)`, `init(id, data)`, `getSummary(id)`, `exportExcel(id)`, `exportPdf(id)` |
| `searchApi` | `global(params)` |
| `messengerApi` | `getChats(params)`, `createChat(data)`, `deleteChat(id)`, `sendMessage(chatId, data)`, `getScripts(params)`, `triggerScript(scriptId, chatId)` |
| `filesApi` | `getContractFiles(contractId, stage)`, `listFolder(path)`, `getPublicLink(yandexPath)`, `upload(file, path)` |

---

### Мобильная PWA — Composables (mobile/src/composables/)

| Файл | Экспорт |
|------|---------|
| `useWebSocket.js` | `useWebSocket()` — глобальный WS с авто-реконнектом и ping |
| `useChatWebSocket.js` | `useChatWebSocket()` — WS конкретной чат-комнаты |
| `usePermission.js` | `usePermission()` — хелпер проверки прав в компонентах |
| `useOptimistic.js` | `useOptimistic()` — оптимистичные обновления UI с rollback |
| `useDeadline.js` | `countWorkingDaysUntil(date)`, `addWorkingDays(date, days)`, `getStageDeadlineInfo(entries, column)`, `calcDeadlineFromTimeline(entries, column)` |
| `useCalendar.js` | `generateICS(event)`, `downloadICS(event)`, `googleCalendarUrl(event)`, `addToCalendar(event, $q)` |
| `usePdfThumbnail.js` | `getPdfThumbnail(source, cacheKey)`, `clearPdfCache()` |
| `usePwaInstall.js` | `usePwaInstall()` — установка PWA (beforeinstallprompt) |

### Мобильная PWA — Offline Queue (mobile/src/services/offlineQueue.js)

`enqueue(operation)` — добавить операцию в IndexedDB очередь
`getPending()` — получить отложенные операции
`syncAll(onProgress)` — синхронизировать все отложенные с сервером
`pendingCount()` → число ожидающих
`clearAll()` — очистить очередь
`isNetworkError(error)` → bool — является ли ошибка сетевой

CRM-система для интерьерного бюро с двухрежимной архитектурой:
- **Сетевой режим:** REST API (FastAPI) + PostgreSQL + JWT авторизация
- **Автономный режим:** Локальная SQLite БД с offline-очередью синхронизации

**Документация:** [docs/Index.md](../docs/Index.md) — 25 файлов
**Оркестрация:** 21 агент, 6-фазный конвейер (Research → Design → Plan → Implement → PR → CI)

---

## Бизнес-словарь (domain vocabulary)

> Значения полей, не требующие поиска по коду.

### Типы и колонки CRM-доски

**project_type:**
- `'Индивидуальный'` — индивидуальный дизайн-проект
- `'Шаблонный'` — шаблонный проект
- `'Авторский надзор'` — надзор (отдельная доска)

**Колонки Индивидуальный** (CRMCard.column_name):
`'Новый заказ'` → `'В ожидании'` → `'Стадия 1: планировочные решения'` → `'Стадия 2: концепция дизайна'` → `'Стадия 3: рабочие чертежи'` → `'Выполненный проект'`

**Колонки Шаблонный** (CRMCard.column_name):
`'Новый заказ'` → `'В ожидании'` → `'Стадия 1: планировочные решения'` → `'Стадия 2: рабочие чертежи'` → `'Стадия 3: 3д визуализация (Дополнительная)'` → `'Выполненный проект'`

**Статусы договора** (Contract.status):
`'Новый заказ'`, `'СДАН'`, `'РАСТОРГНУТ'`, `'АВТОРСКИЙ НАДЗОР'`

**Статусы workflow** (StageWorkflowState.status):
`'in_progress'`, `'pending_review'`, `'revision'`, `'client_approval'`, `'pending_decision'`, `'act_signing'`, `'stage_completed'`

**Статусы сотрудника/агента:** `'активный'`, `'уволен'`

### Должности и роли (server/constants.py)

**Должности (position):**
| Константа | Значение |
|-----------|---------|
| `POSITION_STUDIO_DIRECTOR` | `'Руководитель студии'` |
| `POSITION_SENIOR_MANAGER` | `'Старший менеджер проектов'` |
| `POSITION_SDP` | `'СДП'` |
| `POSITION_GAP` | `'ГАП'` |
| `POSITION_DAN` | `'ДАН'` |
| `POSITION_DAN_FULL` | `'Дизайнер авторского надзора'` |
| `POSITION_MANAGER` | `'Менеджер'` |
| `POSITION_MEASURER` | `'Замерщик'` |
| `POSITION_DESIGNER` | `'Дизайнер'` |
| `POSITION_DRAFTSMAN` | `'Чертёжник'` |

**Группы должностей:**
- `ADMIN_POSITIONS` = [Руководитель студии, Старший менеджер, СДП, ГАП]
- `EXEC_POSITIONS` = [Менеджер, ДАН, Замерщик]
- `REVIEWER_ROLES` = [СДП, Менеджер, ГАП]
- `FREE_MOVE_ROLES` = [admin, director, Руководитель студии, Старший менеджер]
- `SUPERUSER_ROLES` = {admin, director, Руководитель студии}
- `DAN_ROLES` = [ДАН, Дизайнер авторского надзора]

**Роли (role):** `'admin'`, `'director'` (технические, для суперпользователей)

### Полный список ключей прав доступа (server/permissions.py)

**Доступ к страницам (access.*):**
`access.clients`, `access.contracts`, `access.crm`, `access.supervision`, `access.reports`, `access.employees`, `access.salaries`, `access.employee_reports`, `access.employee_analytics`, `access.admin`, `access.dashboards`

**Сотрудники:** `employees.create`, `employees.update`, `employees.delete`

**Клиенты:** `clients.create`, `clients.view`, `clients.update`, `clients.delete`

**Договоры:** `contracts.create`, `contracts.view`, `contracts.update`, `contracts.delete`

**CRM карточки:**
`crm_cards.update`, `crm_cards.move`, `crm_cards.delete`, `crm_cards.assign_executor`, `crm_cards.delete_executor`, `crm_cards.reset_stages`, `crm_cards.reset_approval`, `crm_cards.complete_approval`, `crm_cards.reset_designer`, `crm_cards.reset_draftsman`, `crm_cards.files_upload`, `crm_cards.files_delete`, `crm_cards.deadlines`, `crm_cards.payments`

**Надзор:**
`supervision.update`, `supervision.move`, `supervision.pause_resume`, `supervision.reset_stages`, `supervision.complete_stage`, `supervision.delete_order`, `supervision.assign_executor`, `supervision.files_upload`, `supervision.files_delete`, `supervision.deadlines`, `supervision.payments`

**Финансы:**
`payments.create`, `payments.update`, `payments.delete`
`salaries.create`, `salaries.update`, `salaries.delete`, `salaries.mark_to_pay`, `salaries.mark_paid`
`rates.create`, `rates.delete`

**Агенты:** `agents.create`, `agents.update`, `agents.delete`

**Мессенджер:** `messenger.manage_scripts`

**Уведомления:** `notifications.settings_projects`, `notifications.settings_duplication`, `notifications.settings_supervision`, `notifications.settings_payment`

---

## Модели базы данных (server/database.py — SQLAlchemy)

> PostgreSQL (production) и SQLite (offline). Все модели наследуют Base.

### Пользователи и доступ

| Модель | Таблица | Ключевые поля |
|--------|---------|--------------|
| `Employee` | employees | id, full_name, phone, email, login, password_hash, position, secondary_position, department, role, status, agent_color, payment_type, telegram_user_id, telegram_link_token |
| `UserSession` | user_sessions | id, employee_id→employees, session_token, refresh_token, ip_address, login_time, is_active |
| `UserPermission` | user_permissions | id, employee_id→employees, permission_name, granted_by→employees |
| `RoleDefaultPermission` | role_default_permissions | id, role, permission_name |

### Клиенты и договоры

| Модель | Таблица | Ключевые поля |
|--------|---------|--------------|
| `Client` | clients | id, full_name, phone, email, address, source, comment |
| `Contract` | contracts | id, client_id→clients, contract_number, project_type, status, address, area, agent_id, yandex_folder_path, scan_files |

### CRM и надзор

| Модель | Таблица | Ключевые поля |
|--------|---------|--------------|
| `CRMCard` | crm_cards | id, contract_id→contracts, column_name, order_position, is_archived |
| `StageExecutor` | stage_executors | id, card_id→crm_cards, stage_name, employee_id→employees, deadline, completed, completed_date |
| `StageWorkflowState` | stage_workflow_states | id, card_id→crm_cards, stage_name, status, submitted_by, submitted_at |
| `SupervisionCard` | supervision_cards | id, contract_id→contracts, column_name, address, is_paused, pause_reason |
| `SupervisionProjectHistory` | supervision_project_history | id, card_id→supervision_cards, stage_name, executor_id, completed_date |
| `SupervisionVisit` | supervision_visits | id, card_id→supervision_cards, visit_date, comment |

### Финансы

| Модель | Таблица | Ключевые поля |
|--------|---------|--------------|
| `Payment` | payments | id, contract_id→contracts, employee_id→employees, role, stage_name, amount, payment_status, project_type |
| `Rate` | rates | id, employee_id→employees, project_type, role, stage_name, rate_value |
| `Salary` | salaries | id, employee_id→employees, amount, stage_name, payment_status, project_type |

### Timeline и нормодни

| Модель | Таблица | Ключевые поля |
|--------|---------|--------------|
| `ProjectTimelineEntry` | project_timeline_entries | id, contract_id→contracts, stage_code, stage_name, stage_group, norm_days, k_multiplier, executor_role |
| `SupervisionTimelineEntry` | supervision_timeline_entries | id, card_id→supervision_cards, stage_name, status, executor_role |
| `NormDaysTemplate` | norm_days_templates | id, project_type, project_subtype, stage_code, base_norm_days, k_multiplier, executor_role, agent_type |
| `ApprovalStageDeadline` | approval_stage_deadlines | id, contract_id→contracts, stage_name, deadline, executor_id→employees |

### Уведомления и чаты

| Модель | Таблица | Ключевые поля |
|--------|---------|--------------|
| `Notification` | notifications | id, employee_id→employees, title, message, type, is_read, created_at |
| `NotificationSettings` | notification_settings | id, employee_id→employees, telegram_enabled, web_push_enabled, channels JSON |
| `InternalChat` | internal_chats | id, title, chat_type, crm_card_id, created_by→employees |
| `InternalChatMember` | internal_chat_members | id, chat_id→internal_chats, employee_id→employees, role_in_project |
| `InternalChatMessage` | internal_chat_messages | id, chat_id→internal_chats, sender_id→employees, text, file_path, is_pinned, reply_to_id |

### Мессенджер и файлы

| Модель | Таблица | Ключевые поля |
|--------|---------|--------------|
| `MessengerChat` | messenger_chats | id, crm_card_id, supervision_card_id, messenger_type, invite_link, telegram_chat_id |
| `MessengerScript` | messenger_scripts | id, script_type, project_type, template_text, is_active |
| `ProjectFile` | project_files | id, contract_id→contracts, filename, yandex_path, stage, file_type |
| `FileStorage` | file_storage | id, original_name, stored_name, file_size, mime_type |

### Прочее

| Модель | Таблица | Ключевые поля |
|--------|---------|--------------|
| `ActionHistory` | action_history | id, entity_type, entity_id, employee_id→employees, action, details JSON |
| `Agent` | agents | id, name, color, status |
| `City` | cities | id, name |
| `ConcurrentEdit` | concurrent_edits | id, entity_type, entity_id, employee_id, started_at |
| `ClientSurvey` | client_surveys | id, contract_id→contracts, project_type, invite_status |
| `EmployeeKpiSnapshot` | employee_kpi_snapshots | id, employee_id→employees, report_month, project_type, kpi_data JSON |

### Pydantic схемы (server/schemas.py) — основные

| Схема | Назначение |
|-------|-----------|
| `EmployeeCreate / EmployeeResponse` | CRUD сотрудников |
| `ClientCreate / ClientResponse` | CRUD клиентов |
| `ContractCreate / ContractUpdate / ContractResponse` | CRUD договоров |
| `CRMCardCreate / CRMCardUpdate / CRMCardResponse` | CRUD CRM карточек |
| `ColumnMoveRequest` | Перемещение карточки в колонку |
| `StageExecutorCreate / StageExecutorUpdate / StageExecutorResponse` | Исполнители этапов |
| `SupervisionCardCreate / SupervisionCardUpdate / SupervisionCardResponse` | CRUD надзора |
| `PaymentCreate / PaymentUpdate / PaymentResponse` | CRUD выплат |
| `RateCreate / RateResponse` | Тарифы |
| `SalaryCreate / SalaryResponse` | Зарплаты |
| `ProjectFileCreate / ProjectFileResponse` | Файлы проектов |
| `LoginResponse / RefreshTokenResponse` | Авторизация (JWT) |
| `NotificationResponse` | Уведомления |
| `ActionHistoryCreate / ActionHistoryResponse` | История действий |

## Критические правила

1. **`__init__.py` обязательны** в database/, ui/, utils/
2. **Запрет emoji в UI** — только SVG через IconLoader
3. **`resource_path()`** для всех ресурсов
4. **Рамки диалогов = 1px** (`border: 1px solid #E0E0E0`)
5. **Docker rebuild** после серверных изменений (не restart!)
6. **Совместимость API/DB** ключей ответов
7. **Статические пути ПЕРЕД динамическими** в FastAPI
8. **Двухрежимная архитектура** (online + offline)
9. **DataAccess** для всех CRUD в UI (не api_client/db напрямую)
10. **API-first с fallback** на локальную БД при записи
11. **PyQt Signal Safety** — emit из threading.Thread только через `QTimer.singleShot(0, ...)`
12. **Offline-очередь** — только сетевые ошибки (APIConnectionError/APITimeoutError), НЕ бизнес-ошибки (409/400)
13. **Border-radius диалогов** — ВСЕ виджеты внутри `borderFrame` ДОЛЖНЫ иметь соответствующий `border-radius`: title_bar → `border-top-left/right-radius: 10px`, нижний контейнер (кнопки/scroll_area) → `border-bottom-left/right-radius: 10px`. Без этого фон вылазит за углы.
14. **setAlternatingRowColors(False)** — если таблица использует ручную окраску строк через `setBackground()`, альтернирующие цвета ДОЛЖНЫ быть отключены (иначе Qt перезатирает фон)
15. **ЯД URL формат** — `yandex_folder_path` начинается с `disk:` (напр. `disk:/CRM/Проекты/...`). Для URL: убрать `disk:` prefix, закодировать кириллицу через `quote(path, safe='/')`, формат: `https://disk.yandex.ru/client/disk{encoded_path}`
16. **Выравнивание кнопок со строкой/блоком** — `setFixedHeight(28)` + CSS `max-height: 26px; padding: 0px 14px; font-size: 12px; border: 1px solid #d9d9d9; border-radius: 4px;` (паттерн из employee_reports_tab.py). НЕ использовать `setFixedSize` — ширина кнопки должна определяться текстом. Делегат для окраски строк: `QStyledItemDelegate.paint()` + `option.palette.setColor(Base/AlternateBase)` (как PaymentStatusDelegate)

> Подробности: [docs/02-project-rules.md](../docs/02-project-rules.md)

## Docker rebuild — ОБЯЗАТЕЛЬНАЯ процедура

**После ЛЮБЫХ изменений в `server/`** — ОБЯЗАТЕЛЬНО пересобрать Docker на production:
```bash
ssh timeweb "cd /opt/interior_studio && git pull origin <branch> && docker-compose down && docker-compose build --no-cache api && docker-compose up -d"
```
**Когда:** после каждого push, содержащего изменения в `server/` (роутеры, модели, схемы, миграции).
**Проверка:** после rebuild выполнить `ssh timeweb 'curl -s http://localhost:8000/health'` — должен вернуть `{"status":"healthy"}`.
**НЕЛЬЗЯ:** использовать `docker-compose restart` — это НЕ подхватывает новый код.

## Верификация после исправлений

**ОБЯЗАТЕЛЬНО** после каждого цикла исправлений:
1. CI green (все 5 jobs)
2. Если есть серверные изменения → Docker rebuild → health check
3. Проверка исправленных endpoint-ов через `curl` с JWT токеном
4. НЕ отмечать баг как исправленный, если нет доказательства работоспособности

## Текущая модель (тариф Pro)

**Модель:** `claude-sonnet-4-6` — установлена в `settings.local.json`.

- **Чат:** Sonnet 4.6 по умолчанию (opus недоступен на Pro)
- **Оркестр (субагенты):** Task tool принимает `"sonnet"`, `"haiku"`. Все агенты переведены на `sonnet`.
- **Контекст:** стандартный ~200K токенов (1M контекст доступен только на Max тарифе)

## Экономия токенов

- **docs/**: Использовать Grep для поиска нужных секций, НЕ Read целиком
- **Крупные файлы** (>2000 строк): Grep + Read с offset/limit
- **UI тест логи**: ТОЛЬКО через парсер: `.venv/Scripts/python.exe tests/ui/parse_results.py <файл>`

## Клиент

```bash
.venv\Scripts\python.exe main.py                                        # Запуск
.venv\Scripts\pyinstaller.exe InteriorStudio.spec --clean --noconfirm   # Сборка
```

## Тестирование

```bash
pytest tests/db/ -v                          # DB (без сервера)
pytest tests/e2e/ -v --timeout=60            # E2E (нужен сервер)
pytest tests/ -m critical -v --timeout=60    # Критические
```

## Стратегия тестирования и предотвращения ошибок

### 4 уровня проверки (обязательны после каждого цикла исправлений)

**Уровень 0: Регрессионные тесты UI (ПЕРЕД коммитом)**
- **ОБЯЗАТЕЛЬНО** при изменении ui/*.py — запустить:
  ```bash
  pytest tests/anti_pattern/test_ui_regression_guards.py tests/ui/test_widget_config_regression.py -v --timeout=30
  ```
- Эти тесты ловят потерю: searchable combo, PNG фильтров, substring match, хардкода, CRM карточки, truncate_filename
- Если FAIL — значит правка сломала существующую фичу. ОСТАНОВИТЬСЯ и исправить

**Уровень 1: Автотесты (CI)**
- Все 5 CI jobs должны быть green перед любым деплоем
- При добавлении нового endpoint — писать E2E тест в `tests/e2e/`
- При исправлении бага — писать regression тест, воспроизводящий баг

**Уровень 2: API верификация (curl)**
- После Docker rebuild проверить ВСЕ изменённые endpoint-ы через curl
- Генерация JWT: `ssh timeweb 'docker exec crm_api python3 -c "from auth import create_access_token; print(create_access_token({\"sub\": \"1\"}))"'`
- Проверка: `ssh timeweb "curl -sL -H 'Authorization: Bearer TOKEN' 'URL'" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin), indent=2))"`

**Уровень 3: Smoke-тест клиента**
- Запустить `.venv\Scripts\python.exe main.py` и проверить каждый исправленный модуль
- Для невозможности запуска (headless) — проверить логи на ошибки

### Защита от регрессий при правке UI файлов
**ОБЯЗАТЕЛЬНО** при изменении файлов ui/*.py:
1. **ЧИТАЙ** весь файл перед правкой (Grep по init, eventFilter, _setup_*, getOpenFileName)
2. **ТОЧЕЧНЫЕ ПРАВКИ** — запрещено переписывать >20 строк целиком, используй Edit tool
3. **ЗАПУСТИ** регрессионные тесты после правки (Уровень 0)
4. **ЗАПРЕЩЁННЫЕ ПАТТЕРНЫ:**
   - `addItem('Фестиваль')` — хардкод типов агентов (загружать из данных)
   - `payment.get('address') != f_address` — exact match (нужен substring)
   - `getOpenFileName(..."*.pdf *.jpg"...)` без `*.png` — потеря PNG
   - `truncate_filename(max_length=30)` — слишком длинный (макс 25)
   - Удаление `eventFilter`, `_setup_searchable_combo`, `_searchable` — потеря фич

### Правило новых тестов
При каждом баге, который не был пойман существующими тестами:
1. Определить какой тест мог бы поймать баг
2. Написать этот тест в соответствующую директорию (tests/e2e/, tests/client/, tests/db/)
3. Убедиться что тест FAIL на старом коде и PASS на новом

## Расширенный контекст

Читать через Read при необходимости:
- **Сервер, Docker, CI, агенты:** `.claude/CLAUDE-extended.md`
- **Общие правила агентов:** `.claude/agents/shared-rules.md`
- **Оркестрация:** `/orkester` (skill) | [docs/17-subagents.md](../docs/17-subagents.md)
