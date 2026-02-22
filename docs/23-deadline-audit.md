# Аудит системы дедлайнов — Полный отчёт

**Дата:** 21.02.2026
**Версия:** 1.0
**Проведён:** 6 параллельных агентов (CRM Server, Supervision Server, DataAccess, API Client, UI, DB Manager)

---

## Оглавление

1. [Архитектурный вывод](#1-архитектурный-вывод)
2. [Критические проблемы (K1-K11)](#2-критические-проблемы)
3. [Серьёзные проблемы (С1-С12)](#3-серьёзные-проблемы)
4. [Средние проблемы (M1-M8)](#4-средние-проблемы)
5. [Низкие проблемы (L1-L6)](#5-низкие-проблемы)
6. [План исправлений](#6-план-исправлений)
7. [Прогресс реализации](#7-прогресс-реализации)

---

## 1. Архитектурный вывод

**Сервер — "тупое хранилище".** Вся бизнес-логика каскадного расчёта дедлайнов выполняется на PyQt5-клиенте. Сервер только записывает `actual_date` при workflow-действиях и хранит данные.

**Последствия:**
- Race conditions при работе нескольких клиентов
- Неконсистентность при крашах клиента
- Невозможность доверять данным без клиентского пересчёта

**Текущая архитектура расчёта:**
- `utils/timeline_calc.py` — `calc_planned_dates()`: цепочка `planned[N] = prev_date + norm_days[N]`
- `utils/calendar_helpers.py` — `add_working_days()`, `working_days_between()`
- `ui/timeline_widget.py` — `_calc_planned_dates()`, `_recalculate_days()`
- На сервере каскадного пересчёта **НЕТ**

---

## 2. Критические проблемы

### K1. Нет пересчёта дедлайна CRM при "В ожидании"
- **Файл:** `server/routers/crm_router.py:389-487`
- **Суть:** CRMCard не имеет полей `is_paused`/`paused_at`. При переходе в "В ожидании" дедлайн не приостанавливается. Дни паузы "сгорают"
- **Решение:** Добавить `paused_at`, `total_pause_days` в CRMCard. При move в "В ожидании" — сохранять `paused_at`. При возврате — считать pause_days и сдвигать deadline + все StageExecutor.deadline

### K2. Нет пересчёта дедлайна Supervision при pause/resume
- **Файл:** `server/routers/supervision_router.py:354-436`
- **Суть:** При pause ставится `paused_at`, при resume — очищается. Но `deadline` карточки и `plan_date` timeline entries не сдвигаются
- **Решение:** На сервере в resume endpoint: считать pause_days, сдвигать deadline и plan_dates

### K3. `manager-acceptance` не закрывает стадию
- **Файл:** `server/routers/crm_router.py:1401-1436`
- **Суть:** Endpoint только записывает ActionHistory. Не обновляет StageExecutor.completed, ProjectTimelineEntry.actual_date
- **Решение:** Документировать как фасадный endpoint (UI делает остальное)

### K4. Offline move не сохраняет `previous_column`
- **Файл:** `utils/data_access.py:570`, `database/db_manager.py:921`
- **Суть:** `db.update_crm_card_column()` делает простой UPDATE без previous_column
- **Решение:** Обновить `update_crm_card_column()` и `update_supervision_card_column()`

### K5. `init_project_timeline` нет offline fallback
- **Файл:** `utils/data_access.py:2213, 2294`
- **Суть:** init_timeline работает только через API. Методы есть в db_manager.py, но DataAccess их не вызывает
- **Решение:** Добавить fallback на db.init_project_timeline() / db.init_supervision_timeline()

### K6. UI делает raw SQL вместо DataAccess
- **Файл:** `ui/crm_tab.py:650-758`, `ui/crm_dialogs.py:527-539,1114-1124,3078-3188`
- **Суть:** Автопринятие стадий, payments.report_month, история исполнителей — через raw SQL, минуя DataAccess и API
- **Решение:** Вынести в DataAccess с API-first паттерном

### K7. `client_approval_deadline_paused` — флаг без серверной логики
- **Файл:** `server/routers/crm_router.py:1089,1144`
- **Суть:** Флаг устанавливается/снимается, но нигде не читается для пересчёта дедлайна
- **Решение:** При client-ok считать pause_days и сдвигать дедлайн

### K8. Несоответствие падежей в маппинге Supervision стадий 7-9
- **Файл:** `ui/crm_supervision_tab.py:30-43 vs :189-191`
- **Суть:** SUPERVISION_STAGE_MAPPING (именительный падеж) не совпадает с column_names (генитивный) для стадий 7, 8, 9
- **Решение:** Привести в соответствие

### K9. `get_crm_card_by_contract_id` вызывает несуществующий endpoint
- **Файл:** `utils/api_client/compat_mixin.py:243`
- **Суть:** GET `/api/crm/cards/by-contract/{contract_id}` — endpoint не существует
- **Решение:** Удалить мёртвый код

### K10. `timeline/reinit` уничтожает все actual_date без подтверждения
- **Файл:** `server/routers/timeline_router.py:114-168`
- **Суть:** reinit удаляет ВСЕ ProjectTimelineEntry. Теряются actual_date, actual_days, custom_norm_days
- **Решение:** Добавить проверку наличия заполненных actual_date

### K11. Дедлайн-события не записываются в историю проекта
- **Файл:** `server/routers/crm_router.py`, `ui/crm_tab.py`, `server/routers/supervision_router.py`
- **Суть:** Критичные действия (move, submit, accept, reject, client-send, client-ok, reinit, назначение исполнителя) НЕ записываются в видимую пользователю историю. Покрытие: CRM ~30%, Supervision ~60%
- **Решение:** Добавить запись ActionHistory/SupervisionProjectHistory на стороне СЕРВЕРА для всех дедлайн-событий

**Полный список событий для логирования:**

CRM (ActionHistory):
| Действие | action_type |
|----------|-------------|
| Move карточки | `card_moved` |
| Move в "В ожидании" | `card_paused` |
| Move из "В ожидании" | `card_resumed` |
| Назначение исполнителя | `executor_assigned` |
| Сдача работы (submit) | `work_submitted` |
| Принятие работы (accept) | `work_accepted` |
| Отправка на правки (reject) | `work_rejected` |
| Отправка клиенту | `client_send` |
| Согласование клиентом | `client_approved` |
| Reinit timeline | `timeline_reinit` |
| Сброс стадий | `stages_reset` |

Supervision (SupervisionProjectHistory):
| Действие | entry_type |
|----------|-----------|
| Move карточки | `card_moved` |
| Корректировка дедлайна при resume | `deadline_extended` |
| actual_date при уходе из стадии | `stage_date_set` |

---

## 3. Серьёзные проблемы

### С1. Нечёткий поиск stage_name через ILIKE
- **Файл:** `server/routers/crm_router.py:1305, 1337-1356`
- **Решение:** Точное совпадение stage_name вместо LIKE

### С2. `workflow/reject` сбрасывает все совпадающие стадии
- **Файл:** `server/routers/crm_router.py:982-994`
- **Решение:** Точное совпадение `ex.stage_name == stage_name`

### С3. Утечка DB сессии в timeline_service.py
- **Файл:** `server/services/timeline_service.py:203-226`
- **Решение:** try/finally: db_session.close()

### С4. Supervision pause не блокирует перемещение
- **Файл:** `server/routers/supervision_router.py:251-351`
- **Решение:** Проверка is_paused при move

### С5. Нет проверки already-paused / not-paused
- **Файл:** `server/routers/supervision_router.py:354,398`
- **Решение:** Проверки if card.is_paused / if not card.is_paused

### С6. Resume в UI считает календарные дни вместо рабочих
- **Файл:** `ui/supervision_card_edit_dialog.py:2791-2815`
- **Решение:** Использовать add_working_days() из utils/calendar_helpers.py

### С7. `asyncio.create_task` с `db` session после commit
- **Файл:** `server/routers/crm_router.py:894`, `supervision_router.py:332`
- **Решение:** Создавать новую session внутри task или передавать только IDs

### С8. `StageExecutor.deadline` хранится как String
- **Файл:** `server/database.py:461, 414`
- **Решение:** Миграция на Date тип (перспективная задача)

### С9. Дублирование `_add_business_days` на сервере и клиенте
- **Файл:** `server/routers/crm_router.py:32`, `utils/calendar_helpers.py:163`
- **Решение:** Вынести в серверный сервис

### С10. `workflow/submit` использует UTC вместо локального времени
- **Файл:** `server/routers/crm_router.py:872`
- **Решение:** Принимать дату от клиента или UTC+3

### С11. Workflow endpoints без try/except
- **Файл:** `server/routers/crm_router.py:835-898`
- **Решение:** Добавить try/except/rollback

### С12. DataAccess `update_stage_executor_deadline` использует не тот API метод
- **Файл:** `utils/data_access.py:1587`
- **Решение:** Удалить мёртвый код в compat_mixin.py

---

## 4. Средние проблемы

| # | Файл | Суть |
|---|------|------|
| M1 | data_access.py:2256 | get_timeline_summary() нет offline fallback |
| M2 | data_access.py:2692 | get_norm_days_template() offline — пустой шаблон |
| M3 | data_access.py:2828 | update_stage_executor raw SQL с LIKE |
| M4 | supervision_router.py:319-326 | actual_days в календарных днях (не рабочих) |
| M5 | crm_router.py:1065-1077 | Deadline от prev_entry может быть из другой стадии |
| M6 | supervision_router.py:573-605 | Timeline entries не удаляются явно при delete order |
| M7 | supervision_mixin.py:94 | complete_supervision_stage передаёт stage_name, сервер игнорирует |
| M8 | crm_mixin.py:199,245,258,279,293 | 5 методов глушат исключения в False |

---

## 5. Низкие проблемы

| # | Файл | Суть |
|---|------|------|
| L1 | timeline_router.py:171-193 | Нет валидации формата actual_date |
| L2 | database.py:740-754 | ApprovalStageDeadline — возможно мёртвая таблица |
| L3 | norm_days_router.py:104-150 | Сохранение шаблона не обновляет существующие проекты |
| L4 | docs/14-crm-supervision.md:151 | Документация: PATCH → реально POST для pause/resume |
| L5 | supervision_router.py:14 | Неиспользуемый импорт StageExecutor |
| L6 | supervision_router.py:577 | Неиспользуемый param contract_id в delete |

---

## 6. План исправлений

### Фаза 1: Стабилизация (быстрые фиксы)
- K4: previous_column в offline move (db_manager.py)
- K5: Offline fallback для init_timeline (data_access.py)
- K8: Падежи Supervision стадий 7-9
- K9: Удалить мёртвый get_crm_card_by_contract_id
- С1-С2: Точное совпадение stage_name вместо ILIKE
- С3: try/finally для db_session в timeline_service.py
- С4-С5: Проверки is_paused при move/pause/resume
- С7: Новая session в asyncio task
- С11: try/except для workflow endpoints

### Фаза 2: Бизнес-логика дедлайнов
- K1: Пауза дедлайна CRM при "В ожидании" (paused_at + total_pause_days)
- K2: Серверный пересчёт при Supervision resume
- K7: Серверная логика client_approval_deadline_paused
- K11: Запись дедлайн-событий в историю проекта
- С6: Рабочие дни при resume вместо календарных

### Фаза 3: Архитектурная
- K6: raw SQL из UI → DataAccess
- K3: Документация manager-acceptance
- K10: Защита reinit от потери actual_date
- С12: Очистка дублирования API методов
- M1-M8: Средние исправления

### Фаза 4: Перспективная (отдельный спринт)
- С8: Миграция deadline с String на Date
- Каскадный пересчёт дедлайнов на сервере
- С10: UTC → локальное время

---

## 7. Прогресс реализации

| Фаза | Статус | Дата |
|------|--------|------|
| Фаза 1: Стабилизация | Завершена | 21.02.2026 |
| Фаза 2: Бизнес-логика | Завершена | 21.02.2026 |
| Фаза 3: Архитектурная | Завершена (частично) | 21.02.2026 |
| Фаза 4: Перспективная | Планируется | — |

### Реализованные исправления

**Фаза 1:**
- K4: previous_column в offline move (db_manager.py) — CRM + Supervision
- K5: Offline fallback для init_project_timeline и init_supervision_timeline
- K8: Падежи стадий 7-9 надзора приведены в соответствие (SUPERVISION_STAGE_MAPPING)
- K9: Удалён мёртвый get_crm_card_by_contract_id
- С1: ILIKE → exact match для stage_executor_deadline
- С2: Нечёткий сброс стадий при reject → точное совпадение
- С3: try/finally для db_session в timeline_service.py
- С4: Блокировка перемещения приостановленной карточки надзора
- С5: Проверки already-paused/not-paused
- С7: Notification service создаёт собственную DB-сессию (не использует request-scoped)
- С11: try/except/rollback для workflow submit/accept/reject

**Фаза 2:**
- K1: Пауза дедлайна CRM при "В ожидании" (paused_at, total_pause_days, сдвиг дедлайна + исполнителей)
- K2: Серверный пересчёт plan_dates при resume надзора
- K7: Пересчёт дедлайна при client-ok (client_approval_deadline_paused)
- K11: Запись дедлайн-событий в историю (card_moved/paused/resumed, work_submitted/accepted/rejected, client_send/approved)

**Фаза 3:**
- K3: Документирован manager-acceptance как фасадный endpoint
- K10: Защита reinit от потери actual_date (проверка + force флаг)
- С12: Удалён дублирующий update_stage_executor_deadline из compat_mixin
- M1: Offline fallback для get_timeline_summary
- M3: LIKE → exact match для update_stage_executor в data_access.py
