# API и Endpoints

> Полный каталог всех 144+ API endpoints сервера. Файл: [server/main.py](../server/main.py)

## Базовая информация

- **URL:** `http://crm.festivalcolor.ru:8000`
- **Формат:** JSON
- **Авторизация:** Bearer JWT Token
- **Таймауты:** READ=10 сек, WRITE=15 сек

## Авторизация

| Метод | Путь | Описание | Тело запроса |
|-------|------|----------|-------------|
| POST | `/api/auth/login` | Вход | `{login, password}` |
| POST | `/api/auth/register` | Регистрация | `{full_name, login, password, role, position}` |
| GET | `/api/auth/me` | Текущий пользователь | — |
| POST | `/api/auth/change-password` | Смена пароля | `{old_password, new_password}` |

## Сотрудники (Employees)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/employees` | Список всех сотрудников |
| GET | `/api/employees/{id}` | Сотрудник по ID |
| POST | `/api/employees` | Создать сотрудника |
| PUT | `/api/employees/{id}` | Обновить сотрудника |
| DELETE | `/api/employees/{id}` | Удалить сотрудника |
| GET | `/api/employees/position/{position}` | Сотрудники по должности |

## Клиенты (Clients)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/clients` | Список всех клиентов |
| GET | `/api/clients/{id}` | Клиент по ID |
| POST | `/api/clients` | Создать клиента |
| PUT | `/api/clients/{id}` | Обновить клиента |
| DELETE | `/api/clients/{id}` | Удалить клиента |

## Договоры (Contracts)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/contracts` | Список всех договоров |
| GET | `/api/contracts/{id}` | Договор по ID |
| POST | `/api/contracts` | Создать договор |
| PUT | `/api/contracts/{id}` | Обновить договор |
| DELETE | `/api/contracts/{id}` | Удалить договор |
| GET | `/api/contracts/client/{client_id}` | Договоры клиента |

## CRM карточки (CRM Cards)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/crm/cards` | Все CRM карточки |
| GET | `/api/crm/cards/{id}` | Карточка по ID |
| POST | `/api/crm/cards` | Создать карточку |
| PUT | `/api/crm/cards/{id}` | Обновить карточку |
| PATCH | `/api/crm/cards/{id}` | Частичное обновление |
| DELETE | `/api/crm/cards/{id}` | Удалить карточку |
| GET | `/api/crm/cards/by-type/{project_type}` | Карточки по типу проекта |
| PATCH | `/api/crm/cards/{id}/column` | Переместить в колонку |
| PATCH | `/api/crm/cards/{id}/order` | Изменить порядок |

## Исполнители стадий (Stage Executors)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/crm/cards/{card_id}/stage-executor` | Назначить исполнителя |
| PATCH | `/api/crm/cards/{card_id}/stage-executor/{stage_name}` | Обновить исполнителя |
| PATCH | `/api/crm/cards/{card_id}/stage-executor-deadline` | Обновить дедлайн |
| PATCH | `/api/crm/cards/{card_id}/stage-executor/{stage_name}/complete` | Завершить стадию |
| DELETE | `/api/crm/stage-executors/{executor_id}` | Удалить назначение |
| GET | `/api/sync/stage-executors` | Синхронизация исполнителей |

## Workflow (Рабочий процесс)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/crm/cards/{card_id}/workflow/submit` | Сдать работу |
| POST | `/api/crm/cards/{card_id}/workflow/accept` | Принять работу |
| POST | `/api/crm/cards/{card_id}/workflow/reject` | На исправление |
| POST | `/api/crm/cards/{card_id}/workflow/client-send` | Клиенту на согласование |
| POST | `/api/crm/cards/{card_id}/workflow/client-ok` | Клиент согласовал |
| GET | `/api/crm/cards/{card_id}/workflow/state` | Состояние workflow |
| POST | `/api/crm/cards/{card_id}/manager-acceptance` | Запись приёмки менеджером |
| POST | `/api/crm/cards/{card_id}/reset-designer` | Сбросить дизайнера |
| POST | `/api/crm/cards/{card_id}/reset-draftsman` | Сбросить чертёжника |

## Согласование (Approval)

| Метод | Путь | Описание |
|-------|------|----------|
| PATCH | `/api/crm/cards/{card_id}/approval` | Обновить статус согласования |
| GET | `/api/crm/cards/{card_id}/approval-stages` | Стадии согласования |
| PATCH | `/api/crm/cards/{card_id}/approval-stages` | Обновить стадии |
| POST | `/api/crm/cards/{card_id}/approval-stage-deadlines` | Дедлайны стадий |
| GET | `/api/crm/cards/{card_id}/approval-stage-deadlines` | Получить дедлайны |

## Карточки надзора (Supervision Cards)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/supervision/cards` | Все карточки надзора |
| GET | `/api/supervision/cards/{id}` | Карточка по ID |
| POST | `/api/supervision/cards` | Создать карточку |
| PUT | `/api/supervision/cards/{id}` | Обновить карточку |
| PATCH | `/api/supervision/cards/{id}` | Частичное обновление |
| DELETE | `/api/supervision/cards/{id}` | Удалить карточку |
| PATCH | `/api/supervision/cards/{id}/pause` | Приостановить |
| PATCH | `/api/supervision/cards/{id}/resume` | Возобновить |

## Платежи/Зарплаты (Payments)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/payments` | Все платежи |
| GET | `/api/payments/{id}` | Платёж по ID |
| POST | `/api/payments` | Создать платёж |
| PUT | `/api/payments/{id}` | Обновить платёж |
| DELETE | `/api/payments/{id}` | Удалить платёж |
| GET | `/api/payments/contract/{contract_id}` | Платежи по договору |
| GET | `/api/payments/employee/{employee_id}` | Платежи сотрудника |
| POST | `/api/payments/calculate` | Рассчитать сумму платежа |
| GET | `/api/payments/report` | Зарплатный отчёт по месяцу |

## Тарифы (Rates)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/rates` | Все тарифы |
| GET | `/api/rates/template` | Шаблон тарифов (СТАТИЧЕСКИЙ!) |
| GET | `/api/rates/{rate_id}` | Тариф по ID |
| POST | `/api/rates` | Создать тариф |
| PUT | `/api/rates/{rate_id}` | Обновить тариф |
| DELETE | `/api/rates/{rate_id}` | Удалить тариф |

> **Важно:** `/api/rates/template` ПЕРЕД `/api/rates/{rate_id}`!

## Файлы проектов (Project Files)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/files` | Все файлы |
| GET | `/api/files/{id}` | Файл по ID |
| POST | `/api/files` | Создать запись файла |
| PUT | `/api/files/{id}` | Обновить файл |
| DELETE | `/api/files/{id}` | Удалить файл |
| GET | `/api/files/contract/{contract_id}` | Файлы договора |
| GET | `/api/files/contract/{contract_id}/stage/{stage}` | Файлы по стадии |

## Таблица сроков (Timeline)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/timeline/{contract_id}` | Записи таймлайна |
| POST | `/api/timeline/{contract_id}/init` | Инициализировать из шаблона |
| POST | `/api/timeline/{contract_id}/reinit` | Пересоздать таймлайн |
| PUT | `/api/timeline/{contract_id}/entry/{stage_code}` | Обновить запись |
| GET | `/api/timeline/{contract_id}/summary` | Сводка |
| GET | `/api/timeline/{contract_id}/export/excel` | Экспорт в Excel |
| GET | `/api/timeline/{contract_id}/export/pdf` | Экспорт в PDF |

## Таблица сроков надзора (Supervision Timeline)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/supervision-timeline/{card_id}` | Записи |
| POST | `/api/supervision-timeline/{card_id}/init` | Инициализировать |
| PUT | `/api/supervision-timeline/{card_id}/entry/{stage_code}` | Обновить запись |
| GET | `/api/supervision-timeline/{card_id}/summary` | Сводка |
| GET | `/api/supervision-timeline/{card_id}/export/excel` | Экспорт в Excel |
| GET | `/api/supervision-timeline/{card_id}/export/pdf` | Экспорт в PDF |

## Дашборд (Dashboard)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/dashboard/statistics` | Общая статистика |
| GET | `/api/dashboard/project-stats` | Статистика по проектам |

## Синхронизация (Sync)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/sync/clients` | Синхронизация клиентов |
| GET | `/api/sync/contracts` | Синхронизация договоров |
| GET | `/api/sync/employees` | Синхронизация сотрудников |
| GET | `/api/sync/crm-cards` | Синхронизация CRM карточек |
| GET | `/api/sync/supervision-cards` | Синхронизация карточек надзора |
| GET | `/api/sync/payments` | Синхронизация платежей |
| GET | `/api/sync/rates` | Синхронизация тарифов |
| GET | `/api/sync/files` | Синхронизация файлов |
| GET | `/api/sync/stage-executors` | Синхронизация исполнителей |
| POST | `/api/sync/heartbeat` | Heartbeat онлайн-статуса |
| GET | `/api/sync/online-users` | Онлайн-пользователи |
| POST | `/api/sync/lock` | Блокировка записи |
| DELETE | `/api/sync/lock` | Снятие блокировки |

## Яндекс.Диск

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/yandex/create-folder` | Создать папку |
| POST | `/api/yandex/move-folder` | Переместить папку |
| DELETE | `/api/yandex/delete-folder` | Удалить папку |
| POST | `/api/yandex/upload` | Загрузить файл |
| GET | `/api/yandex/download` | Скачать файл |
| GET | `/api/yandex/public-link` | Публичная ссылка |

## История действий

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/action-history` | Вся история |
| GET | `/api/action-history/{entity_type}/{entity_id}` | История по сущности |
| POST | `/api/action-history` | Добавить запись |

## Клиентский метод → Endpoint маппинг

Файл: [utils/api_client.py](../utils/api_client.py)

```python
# Примеры маппинга:
APIClient.get_clients()         → GET  /api/clients
APIClient.create_client(data)   → POST /api/clients
APIClient.update_client(id, d)  → PUT  /api/clients/{id}
APIClient.get_crm_cards()       → GET  /api/crm/cards
APIClient.calculate_payment()   → POST /api/payments/calculate
```
