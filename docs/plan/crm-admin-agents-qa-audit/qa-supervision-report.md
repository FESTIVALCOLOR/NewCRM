# QA Отчёт: CRM Надзора (Авторский надзор)
Дата: 2026-02-25

---

## Сводка

| Функция | Код | Статус | Проблемы |
|---------|-----|--------|----------|
| Переход из основной CRM | contracts_router.py:152-178 | Реализован | status_changed_date не обновляется при переходе в АВТОРСКИЙ НАДЗОР |
| 12 стадий (Kanban) | supervision_router.py:27-40, supervision_timeline_router.py:21-34 | Реализован | Расхождение имён стадий между роутерами |
| Назначение ДАН / старшего менеджера | supervision_router.py:240-280, schemas.py:606-614 | Реализован | Нет валидации ролей при назначении |
| Timeline (бюджет/поставщик/комиссия) | supervision_timeline_router.py:103-138 | Реализован | commission не входит в SupervisionTimelineUpdate |
| История | supervision_router.py:561-679 | Реализован | Нет систематической фиксации всех событий |
| Файлы | ui/supervision_card_edit_dialog.py | Через ProjectFile | Нет привязки файлов к stage_code в БД |
| Оплаты | payments_router.py:931-969 | Реализован отдельно | Оплаты создаются на стороне UI (не сервера) |
| Архив | supervision_dialogs.py:1145-1171 | Реализован | status_changed_date не устанавливается при завершении |
| Чат | messenger_router.py:357-482 | Реализован (MTProto) | Чат требует MTProto, нет fallback |
| Пауза/возобновление | supervision_router.py:437-558 | Реализован | Дублирование логики resume в pause_card и move_card |

---

## Детальный анализ

### 1. Переход из основной CRM в надзор

**Файл:** `server/routers/contracts_router.py:148-178`

Механизм реализован в эндпоинте `PUT /api/contracts/{contract_id}`:
- При смене статуса договора на `АВТОРСКИЙ НАДЗОР` автоматически создаётся `SupervisionCard` с `column_name='Новый заказ'`
- Перед созданием проверяется отсутствие существующей карточки (защита от дублей)
- В CRM-архиве статус `АВТОРСКИЙ НАДЗОР` включён в список архивных (карточка уходит из активной CRM-доски)

Данные, которые переносятся в надзор (через связь с `Contract`):
- `contract_number`, `address`, `city`, `agent_type`, `area` — читаются из договора по `contract_id`
- Прямой перенос в `SupervisionCard` только: `contract_id`, `column_name='Новый заказ'`, `created_at`

**Что НЕ переносится автоматически:**
- `senior_manager_id`, `dan_id` — назначаются отдельно после создания карточки
- `deadline`, `tags` — заполняются вручную

**Проблема:** `status_changed_date` в таблице `contracts` не обновляется при смене статуса на `АВТОРСКИЙ НАДЗОР` (логика обновления этого поля отсутствует в `contracts_router.py`). Поле существует в БД и схеме, но нигде не устанавливается автоматически.

---

### 2. Стадии надзора

**Файл:** `server/routers/supervision_router.py:27-40` (маппинг), `server/routers/supervision_timeline_router.py:21-34` (инициализация)

**Kanban-колонки** (15 колонок, включая служебные):
```
Новый заказ, В ожидании,
Стадия 1: Закупка керамогранита, Стадия 2: Закупка сантехники,
Стадия 3: Закупка оборудования, Стадия 4: Закупка дверей и окон,
Стадия 5: Закупка настенных материалов, Стадия 6: Закупка напольных материалов,
Стадия 7: Лепного декора, Стадия 8: Освещения,
Стадия 9: бытовой техники, Стадия 10: Закупка заказной мебели,
Стадия 11: Закупка фабричной мебели, Стадия 12: Закупка декора,
Выполненный проект
```

**Timeline-стадии** (12 производственных, инициализируются при открытии таблицы):
```python
SUPERVISION_STAGES = [
    ('STAGE_1_CERAMIC',  'Стадия 1: Закупка керамогранита'),
    ('STAGE_2_PLUMBING', 'Стадия 2: Закупка сантехники'),
    ...
    ('STAGE_7_STUCCO',   'Стадия 7: Лепной декор'),        # <-- расхождение
    ('STAGE_8_LIGHTING', 'Стадия 8: Освещение'),            # <-- расхождение
    ('STAGE_9_APPLIANCES','Стадия 9: Бытовая техника'),     # <-- расхождение
    ...
]
```

**Проблема (серьёзная):** Расхождение в именах стадий между маппингом Kanban и инициализацией timeline:
- В маппинге Kanban: `'Стадия 7: Лепного декора'`, `'Стадия 8: Освещения'`, `'Стадия 9: бытовой техники'`
- В `SUPERVISION_STAGES`: `'Стадия 7: Лепной декор'`, `'Стадия 8: Освещение'`, `'Стадия 9: Бытовая техника'`

Это означает, что при уходе карточки из колонки `'Стадия 7: Лепного декора'` `_SUPERVISION_COLUMN_TO_STAGE.get(old_column)` найдёт `'STAGE_7_STUCCO'`, и `actual_date` будет установлена правильно (маппинг использует stage_code, а не stage_name). Но в timeline запись будет иметь другое `stage_name`, что создаёт визуальное несоответствие в отчётах.

**Валидация перемещений** (supervision_router.py:292-334):
- Нельзя вернуться в "Новый заказ" после выхода из него
- Из "В ожидании" — только в `previous_column` или "Выполненный проект"
- Приостановленную карточку нельзя переместить (кроме возврата из "В ожидании")

---

### 3. Карточка надзора (поля, ДАН, старший менеджер)

**Файл:** `server/schemas.py:577-627`, `server/routers/supervision_router.py:240-280`

`SupervisionCardBase` содержит:
- `contract_id` — обязательное
- `column_name` (default='Новый заказ')
- `previous_column`, `start_date`, `deadline`, `tags`
- `senior_manager_id`, `dan_id` — ID сотрудников
- `dan_completed` (bool) — флаг "ДАН сдал работу"

`SupervisionCardUpdate` (PATCH `/cards/{card_id}`) позволяет обновить:
- `column_name`, `previous_column`, `start_date`, `deadline`, `tags`
- `senior_manager_id`, `dan_id`, `dan_completed`

**Назначение ДАН:** эндпоинт `PATCH /api/supervision/cards/{card_id}` с `{dan_id: ...}`. Нет проверки, что назначаемый сотрудник действительно имеет роль 'ДАН'.

**Назначение старшего менеджера:** аналогично через `senior_manager_id`. Нет проверки роли.

**Пауза:** отдельные эндпоинты `POST /cards/{card_id}/pause` и `POST /cards/{card_id}/resume`. Требуют права `supervision.pause_resume`.

---

### 4. Timeline надзора

**Файл:** `server/routers/supervision_timeline_router.py`

**Инициализация:** `POST /api/supervision-timeline/{card_id}/init` — создаёт 12 записей `SupervisionTimelineEntry` с `status='Не начато'`. Если записи уже есть — возвращает `already_initialized` без изменений.

**Поля записи timeline** (модель `SupervisionTimelineEntry` в database.py:569-595):
- `plan_date`, `actual_date` — даты (строки)
- `actual_days` — дней факт
- `budget_planned`, `budget_actual`, `budget_savings` — бюджет (Float)
- `supplier` — поставщик (String)
- `commission` — комиссия (Float)
- `notes` — примечания (Text)
- `status` — статус ('Не начато', 'Закуплено', etc.)
- `executor` — исполнитель (String)
- `defects_found`, `defects_resolved` — дефекты
- `site_visits` — выезды на объект

**Автоматический расчёт экономии** (supervision_timeline_router.py:124-126):
```python
entry.budget_savings = entry.budget_planned - entry.budget_actual
```
Выполняется при каждом обновлении записи.

**Автозаполнение `actual_date`:** при уходе карточки из стадии (supervision_router.py:390-410) автоматически устанавливается `actual_date = today` и `status = 'Закуплено'`.

**Уведомление в чат** при изменении статуса на 'выполнено'/'завершено' (supervision_timeline_router.py:131-136).

**Проблема:** `commission` НЕ включена в `SupervisionTimelineUpdate` (schemas.py:1133-1148). Схема позволяет обновить только: `plan_date`, `actual_date`, `actual_days`, `budget_planned`, `budget_actual`, `budget_savings`, `status`, `notes`, `executor`, `defects_found`, `defects_resolved`, `site_visits`. Поле `commission` есть в БД и базовой схеме, но недоступно для обновления через API.

**Экспорт в Excel:** `GET /api/supervision-timeline/{card_id}/export/excel` — экспортирует без поля `commission`.

---

### 5. История проекта надзора

**Файл:** `server/routers/supervision_router.py:561-679`

Модель `SupervisionProjectHistory` с полями: `supervision_card_id`, `entry_type`, `message`, `created_by`, `created_at`.

**Автоматически записываются события:**
- `card_moved` — при перемещении между колонками (supervision_router.py:381-388)
- `pause` — при приостановке
- `resume` — при возобновлении (с указанием дней паузы)
- `stage_completed` — при `dan_completed = True`
- `accepted` — при принятии работы менеджером (ui/crm_supervision_tab.py:905-911)

**Ручное добавление:** `POST /cards/{card_id}/history` с `{entry_type, message}` (supervision_router.py:642-679).

**Проблема:** события "назначение ДАН" и "назначение старшего менеджера" не записываются в историю. При PATCH `/cards/{card_id}` нет автоматического логирования изменения `dan_id` / `senior_manager_id`.

---

### 6. Файлы надзора

**Файл:** `ui/supervision_card_edit_dialog.py:2104-2205`, `server/routers/files_router.py`

Загрузка файлов реализована через Яндекс.Диск:
1. Пользователь выбирает файл и стадию в `SupervisionFileUploadDialog`
2. Файл загружается в папку: `{contract_folder}/Авторский надзор/{stage_name}/{file_name}`
3. Метаданные сохраняются в `ProjectFile` (таблица `project_files`)
4. После загрузки обновляется соответствующая запись `SupervisionTimelineEntry` по `stage_name`

**Проблема (критическая):** Файлы надзора хранятся в общей таблице `project_files` без поля `supervision_card_id` или `stage_code`. Связь с карточкой надзора определяется по `contract_id` и `stage` (строка — имя стадии). Это означает:
- Нет строгой привязки файла к конкретной карточке надзора (если у одного договора будет несколько карточек надзора — файлы перемешаются)
- Нет возможности фильтрации файлов по stage_code через API; фильтрация делается на UI-стороне по строковому полю `stage`
- При удалении карточки надзора файлы в `project_files` НЕ удаляются (supervision_router.py:695-732 удаляет только timeline, history, payments и саму карточку)

---

### 7. Оплаты надзора

**Файл:** `server/routers/payments_router.py`

Оплаты надзора хранятся в общей таблице `payments` с полем `supervision_card_id`. Отдельной таблицы нет.

**Создание оплат:** происходит на стороне UI (ui/crm_supervision_tab.py:947-997) при перемещении карточки из рабочей стадии руководством. Сервер не создаёт оплаты автоматически.

**Расчёт суммы:** `GET /api/payments/calculate?supervision_card_id=...&role=ДАН&stage_name=...` — использует тариф `project_type='Авторский надзор'` (payments_router.py:253-264).

**Отображение в зарплатах:** в reports (payments_router.py:458-474) оплаты надзора отфильтровываются по `supervision_card_id IS NOT NULL`. `project_type` выставляется как `'Авторский надзор'`.

**Проблемы:**
- Оплаты создаются только при автопринятии руководством (supervision_router, когда `dan_completed==0`). Если ДАН сдал работу и менеджер явно нажал "Принять" (кнопка на карточке), оплата создаётся отдельным путём (accept_work), но логика не унифицирована.
- Нет серверной валидации при создании оплаты надзора: можно создать оплату с `role='ДАН'` без проверки, что в карточке назначен ДАН.

---

### 8. Архив надзора

**Файл:** `ui/supervision_dialogs.py:1000-1189`, `server/routers/supervision_router.py:80-83`

Завершение надзора происходит при перемещении карточки в колонку `'Выполненный проект'`:
1. Открывается `SupervisionCompletionDialog` с выбором статуса
2. Пользователь выбирает: `'Проект СДАН'` или `'Проект РАСТОРГНУТ'`
3. При РАСТОРГНУТ — обязательно указывается причина расторжения
4. Вызывается `DataAccess.update_contract(contract_id, {'status': 'СДАН'/'РАСТОРГНУТ', ...})`
5. Карточка остаётся в `supervision_cards` с `column_name='Выполненный проект'`
6. Архивный список: фильтрация `Contract.status IN ('СДАН', 'РАСТОРГНУТ')`

**Проблема (серьёзная):** `status_changed_date` в таблице `contracts` НЕ устанавливается при изменении статуса на СДАН/РАСТОРГНУТ. Поле есть в БД и схеме (`ContractUpdate.status_changed_date: Optional[str]`), но при вызове `update_contract` через `SupervisionCompletionDialog` оно не передаётся. Это критично для фильтрации архива по дате завершения — поле используется в `supervision_router.py:128` для фильтрации, но всегда будет `None`.

**Цветовая кодировка:** логика цветового различия СДАН (зелёный) / РАСТОРГНУТ (красный) реализована в UI при отображении `ArchiveCard`, но не проверялась в рамках текущего аудита.

---

### 9. Чат надзора

**Файл:** `server/routers/messenger_router.py:357-482`, `server/services/notification_service.py:249-358`

**Создание чата:** `POST /api/messenger/chats/supervision` (создаёт Telegram-группу через MTProto). Требует:
- Настроенного MTProto (Telethon)
- `SupervisionChatCreate` с полями: `supervision_card_id`, `messenger_type`, дополнительные члены

**Название чата:** генерируется из данных договора (адрес, тип агента).

**Аватар чата:** определяется по `agent_type` — 'festival' или 'petrovich' (захардкожено, только два варианта).

**Автоуведомления** (trigger_supervision_notification):
- `supervision_move` — при перемещении между стадиями
- `supervision_stage_complete` — при смене статуса timeline на 'выполнено'/'завершено'

Контекст уведомления включает: `stage_name`, `client_name`, `address`, `city`, `contract_number`, `senior_manager`, `dan`, `deadline`.

**Скрипты:** хранятся в `MessengerScript` с `script_type='supervision_move'` или `'supervision_stage_complete'`. Поддерживаются stage-specific скрипты (поле `stage_name` в скрипте).

**Получение чата карточки:** `GET /api/messenger/chats/by-supervision/{supervision_card_id}`.

**Проблемы:**
- MTProto обязателен для создания чата; нет fallback для привязки существующего чата вручную (аналог `MessengerChatBind` для обычных чатов)
- Аватар выбирается только из 2 вариантов (festival/petrovich); новые типы агентов будут получать 'festival' по умолчанию
- При отправке уведомления используется `asyncio.create_task()` (fire-and-forget); ошибки доставки логируются, но не влияют на результат операции — корректно

---

### 10. Пауза/возобновление надзора

**Файл:** `server/routers/supervision_router.py:437-558`

**Пауза** (`POST /cards/{card_id}/pause`):
- Требует `pause_reason` (обязательно)
- Устанавливает `is_paused=True`, `paused_at=datetime.utcnow()`
- Записывает в историю (`entry_type='pause'`)
- Приостановленную карточку нельзя переместить (кроме выхода из "В ожидании")

**Возобновление** (`POST /cards/{card_id}/resume`):
- Считает дни паузы через `_count_business_days(paused_at, now)`
- Сдвигает все `plan_date` в timeline на `pause_days` (только записи без `actual_date`)
- Сдвигает `deadline` карточки на те же дни
- Записывает в историю (`entry_type='resume'`)
- Суммирует в `card.total_pause_days`

**Дублирование логики:** аналогичная логика авто-resume при перемещении из "В ожидании" в другую колонку (supervision_router.py:341-376). Фактически resume реализован в двух местах:
1. Явный `POST /cards/{card_id}/resume`
2. Неявный при перемещении из "В ожидании" (в `move_supervision_card_to_column`)

Разница: явный resume вызывается из UI через `data.resume_supervision_card()` (crm_supervision_tab.py:1020), а неявный — на стороне сервера при перемещении. Есть риск двойного применения, если UI вызывает оба.

**Проблема:** `_count_business_days` считает только пн-пт, не учитывает праздники.

---

### 11. UI карточки надзора (SupervisionCardEditDialog)

**Файл:** `ui/supervision_card_edit_dialog.py`

**Вкладки диалога:**
1. `Редактирование` — только для НЕ-ДАН ролей; поля: назначение ДАН, старшего менеджера, дедлайн, теги; кнопки чата (создать/открыть/удалить)
2. `Таблица сроков` — `SupervisionTimelineWidget` с 12 строками (plan_date, actual_date, budget, supplier, commission, notes, status)
3. `Оплаты надзора` — таблица оплат по карточке
4. `Информация о проекте` — данные из договора (адрес, площадь, тип агента и пр.)
5. `Файлы надзора` — список файлов с возможностью загрузки на Яндекс.Диск

**Особенности:**
- Для роли ДАН: заголовок меняется на `'История проекта'`, вкладка "Редактирование" скрыта
- Автосохранение подключается только для НЕ-ДАН ролей
- Вкладки "Таблица сроков", "Оплаты", "Информация", "Файлы" создаются с отложенной инициализацией (после `showEvent`) для оптимизации

---

### 12. UI вкладки надзора (Kanban)

**Файл:** `ui/crm_supervision_tab.py`

**Структура:**
- Вкладка 1: `'Активные проекты (N)'` — Kanban-доска с 15 колонками (горизонтальный скролл)
- Вкладка 2: `'Архив (N)'` — только для НЕ-ДАН; список ArchiveCard с фильтрами

**Kanban-колонки:** 15 (2 служебных + 12 рабочих + 1 итоговая). Реализованы как `BaseKanbanColumn` с drag-and-drop.

**Фильтрация архива:** по периоду (всё время/год/квартал/месяц), адресу, городу, типу агента. Применяется на стороне клиента из уже загруженных данных.

**Ролевое поведение:**
- ДАН видит только свои карточки (`dan_id == employee_id`)
- Кнопка "Статистика" скрыта для ДАН
- Архивная вкладка скрыта для ДАН

**Карточка в Kanban** (`SupervisionCardWidget`):
- Отображает адрес, город, тип агента, дедлайн, теги, назначенных исполнителей
- Индикатор "РАБОТА СДАНА" (оранжевый) при `dan_completed=True`
- Кнопки: "Сдать работу" (для ДАН), "Принять работу" (для менеджеров), "Пауза", "Возобновить", "Заметка", "Переназначить ДАН", "Редактировать"

---

## Найденные проблемы

| # | Проблема | Серьёзность | Файл:строка | Описание |
|---|----------|-------------|-------------|----------|
| 1 | Расхождение имён стадий 7, 8, 9 | Средняя | supervision_timeline_router.py:27-34 vs supervision_router.py:34-36 | В Kanban: "Лепного декора", "Освещения", "бытовой техники"; в timeline: "Лепной декор", "Освещение", "Бытовая техника". Визуальное несоответствие в отчётах и Excel-экспорте. |
| 2 | `commission` не редактируется через API | Средняя | schemas.py:1133-1148 | `SupervisionTimelineUpdate` не содержит поле `commission`. Поле есть в БД и базовой схеме, но недоступно через PATCH. |
| 3 | `status_changed_date` не заполняется | Средняя | contracts_router.py:148-178, supervision_dialogs.py:1154-1165 | При переходе в АВТОРСКИЙ НАДЗОР и при завершении (СДАН/РАСТОРГНУТ) поле `status_changed_date` не устанавливается. Фильтрация архива по дате работает некорректно (supervision_router.py:128 пробует вызвать `.isoformat()` на None, защищён `if hasattr...`, но дата всегда None). |
| 4 | Файлы надзора не привязаны к supervision_card_id | Средняя | server/database.py:717-735 | Таблица `project_files` не имеет поля `supervision_card_id`. Файлы привязаны только по `contract_id` и строковому `stage`. При нескольких карточках надзора для одного договора файлы перемешаются. |
| 5 | При удалении карточки надзора файлы не удаляются | Низкая | supervision_router.py:695-723 | При DELETE `/orders/{supervision_card_id}` удаляются timeline, history, payments, но НЕ файлы в `project_files`. |
| 6 | Дублирование логики resume | Низкая | supervision_router.py:341-376 vs 485-551 | Логика авто-resume дублируется в `move_supervision_card_to_column` и `resume_supervision_card`. UI вызывает resume явно после перемещения из "В ожидании" (crm_supervision_tab.py:1020), что может привести к двойному сдвигу дедлайнов. |
| 7 | Нет валидации роли при назначении ДАН/старшего | Низкая | supervision_router.py:240-280 | PATCH `/cards/{card_id}` принимает любой `employee_id` как `dan_id` без проверки, что у сотрудника роль 'ДАН'. |
| 8 | История не фиксирует смену ДАН/менеджера | Низкая | supervision_router.py:240-280 | При изменении `dan_id` / `senior_manager_id` в истории проекта нет записи. Аудиторский след неполный. |
| 9 | Аватар чата только для 2 типов агентов | Низкая | messenger_router.py:230-237 | Только `festival` и `petrovich`. Новый тип агента получит аватар `festival` по умолчанию. |
| 10 | `_count_business_days` не учитывает праздники | Низкая | supervision_router.py:45-53 | Функция считает только пн-пт. Праздники (1 января и пр.) учитываются как рабочие дни при пересчёте паузы. |
| 11 | Оплаты создаются только на стороне UI | Средняя | ui/crm_supervision_tab.py:947-997 | Бизнес-логика создания оплат при принятии стадии находится в UI, а не в сервере. Если оплата создаётся через другой клиент/API-вызов — логика не сработает. |
| 12 | Нет fallback для привязки чата вручную | Низкая | messenger_router.py:385-390 | Если MTProto недоступен, чат создать нельзя. Нет аналога `MessengerChatBind` для надзора. |

---

## Бизнес-логика: вопросы

1. **Статус "Авторский надзор" в основной CRM:** карточка с этим статусом уходит в архив основной CRM (crm_router.py:114-117). Это означает, что карточка дизайн-проекта становится архивной, когда начинается надзор. Является ли это намеренным поведением? Или надзор должен быть параллельным активным статусом?

2. **Несколько карточек надзора для одного договора:** технически возможно создать несколько `SupervisionCard` для одного `contract_id` (проверяется только при автосоздании через contracts_router). Нужна ли защита от дублей при ручном создании через `POST /api/supervision/cards`?

3. **Завершение надзора и архив:** при переходе в "Выполненный проект" статус договора меняется на СДАН/РАСТОРГНУТ. Но `column_name` карточки надзора остаётся `'Выполненный проект'`. При последующей загрузке архива карточка фильтруется по `Contract.status IN ('СДАН', 'РАСТОРГНУТ')`. Что происходит с карточкой, если менеджер отменил диалог завершения (`dialog.exec_() != Accepted`)? Карточка уже перемещена в "Выполненный проект", но статус договора не изменился.

4. **ДАН видит только свои карточки:** фильтрация в UI (`dan_id == employee_id`). Это клиентская фильтрация, сервер возвращает все карточки. Нет серверной фильтрации по роли ДАН. Является ли это проблемой безопасности?

5. **Комиссия (commission):** для кого фиксируется комиссия? Это комиссия агента от суммы закупки? Как она соотносится с оплатами сотрудников?

6. **Стадия 12 = "Выполненный проект"?** После последней рабочей стадии карточка должна перейти в "Выполненный проект" вручную. Нет автоматического перехода после завершения всех 12 стадий.

7. **Инициализация timeline:** `POST /supervision-timeline/{card_id}/init` не вызывается автоматически при создании карточки надзора. Когда именно должна происходить инициализация? При открытии диалога редактирования?

---

## Рекомендации

### Приоритет 1 (Исправить немедленно)

1. **Исправить `status_changed_date`** — при смене статуса договора (contracts_router.py:157-163) автоматически устанавливать:
   ```python
   if new_status and new_status != old_status:
       contract.status_changed_date = datetime.utcnow().strftime('%Y-%m-%d')
   ```

2. **Добавить `commission` в `SupervisionTimelineUpdate`** (schemas.py:1133-1148):
   ```python
   commission: Optional[float] = None
   ```

3. **Устранить расхождение имён стадий** — привести имена в `SUPERVISION_STAGES` (supervision_timeline_router.py) к точному совпадению с Kanban-колонками.

### Приоритет 2 (Исправить в ближайшем спринте)

4. **Добавить `supervision_card_id` в `project_files`** или создать отдельную таблицу `supervision_files` с привязкой к карточке и `stage_code`.

5. **Устранить дублирование логики resume** — убрать авто-resume из `move_supervision_card_to_column`, оставить только явный endpoint `resume_supervision_card`. UI должен явно вызывать resume перед перемещением.

6. **Добавить запись в историю** при изменении `dan_id` / `senior_manager_id` в `update_supervision_card`.

7. **Перенести создание оплат на сервер** — при принятии стадии (`complete_supervision_stage` или новый endpoint) создавать оплаты на стороне сервера.

### Приоритет 3 (По возможности)

8. **Добавить валидацию роли** при назначении ДАН — проверять `employee.position == 'ДАН' or employee.secondary_position == 'ДАН'`.

9. **Добавить fallback для чата надзора** — поддержка ручной привязки существующего Telegram-чата.

10. **Каскадное удаление файлов** при удалении карточки надзора.

11. **Серверная фильтрация по роли ДАН** — добавить `dan_id` как параметр фильтрации в `GET /api/supervision/cards`.

---

*Отчёт подготовлен: 2026-02-25*
*Файлы проверены: server/routers/supervision_router.py, server/routers/supervision_timeline_router.py, server/routers/contracts_router.py, server/routers/payments_router.py, server/routers/files_router.py, server/routers/messenger_router.py, server/services/notification_service.py, server/schemas.py, server/database.py, ui/supervision_card_edit_dialog.py, ui/crm_supervision_tab.py, ui/supervision_dialogs.py*
