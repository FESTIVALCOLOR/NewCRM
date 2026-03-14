# Research: Workflow V2 Redesign

## 1. Архитектура серверных endpoint-ов

### workflow/submit (`POST /cards/{card_id}/workflow/submit`, строка 1385)

**Текущие статусы:** устанавливает `wf.status = 'pending_review'`.

**Запись дат:**
- Если `wf.status == 'revision'` → перезаписывает `actual_date` в **существующую** строку `wf.current_substep_code` (не ищет новую пустую).
- Если обычная сдача → ищет первую строку с `executor_role IN ('Чертежник', 'Дизайнер')` и `actual_date IS NULL`. Записывает `datetime.utcnow().strftime('%Y-%m-%d')`.
- Таким образом: при ревизии — перезапись той же строки; при обычной сдаче — заполнение следующей пустой. **Проблема пункта 2**: при повторных правках поведение уже исправлено для случая `revision`, но не для случая когда нажимается `submit` после `revision` первый раз — там продвижения нет.

**Дедлайн:** вызывает `_update_executor_deadline_for_next_substep()` — обновляет `StageExecutor.deadline` по `norm_days` следующего незаполненного подэтапа.

**Сбор правок:** не затрагивается.

---

### workflow/accept (`POST /cards/{card_id}/workflow/accept`, строка 1477)

**Текущие статусы:** устанавливает `wf.status = 'in_progress'`.

**Запись дат:** ищет первую строку с `executor_role IN ('СДП', 'Менеджер', 'ГАП')` и `actual_date IS NULL` → записывает `utcnow()`. Всегда ищет следующую пустую строку reviewer — **не перезаписывает**.

**Дедлайн:** вызывает `_update_executor_deadline_for_next_substep()`.

**Сбор правок:** не затрагивается.

**Примечание:** кнопка "Принять работу" в UI существует (`accept_work()` на строке 3007), но в основном интерфейсе больше не показывается — заменена на "Отправить клиенту" (`send_to_client_combined`). Метод `accept_work()` сохранён в коде, но кнопка в UI не создаётся (блок `send_client_btn` создаётся вместо неё).

---

### workflow/reject (`POST /cards/{card_id}/workflow/reject`, строка 1550)

**Текущие статусы:** устанавливает `wf.status = 'revision'`, инкрементирует `wf.revision_count`.

**Запись дат:**
- Записывает дату в строку reviewer (первая пустая `СДП/Менеджер/ГАП` после `current_substep_code`) — всегда **следующая пустая**, не перезаписывает.
- Продвигает `wf.current_substep_code` на первую пустую строку исполнителя ("Правка") в том же `substage_group`.

**Дедлайн:** НЕ обновляет (комментарий: "правки не двигают timeline").

**Сбор правок:** не затрагивается.

---

### workflow/client-send (`POST /cards/{card_id}/workflow/client-send`, строка 1677)

**Текущие статусы:** устанавливает `wf.status = 'client_approval'`, `wf.client_approval_deadline_paused = True`, `wf.client_approval_started_at = utcnow()`.

**Запись дат:**
- Записывает дату reviewer (строка `СДП/Менеджер/ГАП` ДО клиентской строки) — **первая пустая**.
- Все строки между reviewer_entry и client_entry помечаются как `status = 'skipped'`.
- Дата НЕ записывается в клиентскую строку — это делается в `client-ok`.

**Дедлайн:** приостанавливается (`client_approval_deadline_paused = True`).

**Сбор правок:** не затрагивается напрямую.

---

### workflow/client-ok (`POST /cards/{card_id}/workflow/client-ok`, строка 1879)

**Требуемые права:** `crm_cards.complete_approval`.

**Текущие статусы:**
- Если есть следующий круг (`ROUND_PAIRS`): `wf.status = 'pending_decision'`
- Если следующего круга нет: `wf.status = 'in_progress'`
- Сбрасывает `wf.revision_count = 0`, `wf.client_approval_deadline_paused = False`

**Запись дат:**
- Записывает `actual_date` в первую пустую строку `executor_role = 'Клиент'`.
- Если за ней идёт строка "Сбор правок" (`СДП/Менеджер/ГАП`) — тоже записывает дату.

**Дедлайн:** пересчитывает с учётом паузы согласования (`_count_business_days` от `client_approval_started_at`). Сдвигает `card.deadline` и все `StageExecutor.deadline` на количество рабочих дней паузы.

**Сбор правок:** дата "Сбор правок" **записывается автоматически** в `client-ok`, если строка называется "Сбор правок" (проверка через `in 'сбор правок'` в stage_name).

---

### workflow/advance-round (`POST /cards/{card_id}/workflow/advance-round`, строка 2043)

**Текущие статусы:** устанавливает `wf.status = 'in_progress'`, обновляет `wf.current_substep_code` и `wf.current_substage_group` на первый подэтап следующего круга.

**ROUND_PAIRS (серверная константа, строка 2036):**
```python
_ROUND_PAIRS = {
    'Подэтап 1.2': 'Подэтап 1.3',
    'Подэтап 2.3': 'Подэтап 2.4',
    'Подэтап 2.6': 'Подэтап 2.7',
}
```

**Дедлайн:** вызывает `_update_executor_deadline_for_next_substep()`.

---

### workflow/close-stage (`POST /cards/{card_id}/workflow/close-stage`, строка 2107)

**Текущие статусы:** устанавливает `wf.status = 'completed'`.

**Запись дат:** все незаполненные строки текущего `stage_group` помечаются `status = 'skipped'`.

**Дедлайн:** вызывает `_update_executor_deadline_for_next_substep()`.

---

### workflow/add-extra-round (`POST /cards/{card_id}/workflow/add-extra-round`, строка 2168)

Добавляет 4 записи в таймлайн: заголовок `Доп. круг N (платный)`, работа исполнителя, проверка reviewer, отправка клиенту. Коды: `S{N}_EXT{n}_HDR`, `_01`, `_02`, `_03`. Все с `is_in_contract_scope=False`.

---

## 2. Timeline Service

### Записи "Подготовка файлов"

**Индивидуальный проект (Стадия 3):**
```
S3_01 | 'Подготовка файлов, выдача' | STAGE3 | substage_group='' | executor='СДП' | is_in_contract_scope=True | norm=1
```
(строка 173 в `timeline_service.py`)

**Шаблонный проект (Стадия 2):**
```
T2_01 | 'Подготовка файлов, выдача чертежнику' | STAGE2 | substage_group='' | executor='Менеджер' | is_in_contract_scope=True | norm=1
```
(строка 360 в `timeline_service.py`)

**Итог:** обе записи существуют и имеют `is_in_contract_scope=True`, т.е. входят в расчёт срока договора.

---

### is_in_contract_scope для подэтапа 1.2

Индивидуальный проект, Подэтап 1.2 (строки 88–94):

| Код | Название | executor | is_in_contract_scope |
|-----|----------|----------|---------------------|
| S1_2_HDR | Подэтап 1.2 — Фин. план 1 круг | header | False |
| S1_2_01 | Фин. план. решение (1 круг) | Чертежник | **True** |
| S1_2_02 | Проверка СДП | СДП | False |
| S1_2_03 | Правка чертежником | Чертежник | False |
| S1_2_04 | Проверка повторная СДП | СДП | False |
| S1_2_05 | Отправка клиенту | Клиент | False |
| S1_2_06 | Сбор правок от клиента СДП | СДП | False |

Шаблонный проект, Подэтап 1.2 (строки 350–355):

| Код | Название | executor | is_in_contract_scope |
|-----|----------|----------|---------------------|
| T1_2_HDR | Подэтап 1.2 — Финальное план. решение | header | False |
| T1_2_01 | Финальное план. решение (1 круг) | Чертежник | **True** |
| T1_2_02 | Проверка менеджером | Менеджер | False |
| T1_2_03 | Правка чертежником | Чертежник | False |
| T1_2_04 | Проверка повторная менеджером | Менеджер | False |
| T1_2_05 | Отправка клиенту / Согласование | Клиент | False |

**Итог:** Только первая исполнительская строка каждого подэтапа 1.2 (`S1_2_01` / `T1_2_01`) имеет `is_in_contract_scope=True`. Остальные строки подэтапа — `False`.

---

### Структура подэтапа 2.1 (индивидуальный проект)

Строки 107–117 `timeline_service.py`:

| Код | Название | executor | is_in_contract_scope |
|-----|----------|----------|---------------------|
| S2_1_HDR | Подэтап 2.1 — Мудборды | header | False |
| S2_1_01 | Разработка мудбордов | Дизайнер | True |
| S2_1_02 | Проверка СДП | СДП | True |
| S2_1_03 | Правка дизайнером | Дизайнер | True |
| S2_1_04 | Проверка повторная СДП | СДП | True |
| S2_1_05 | Отправка клиенту | Клиент | False |
| S2_1_06 | Сбор правок СДП | СДП | False |
| S2_1_07 | Правка дизайнером | Дизайнер | False |
| S2_1_08 | Проверка СДП | СДП | False |
| S2_1_09 | Согласование мудборда | Клиент | False |

В шаблонном проекте для подтипа "Эскизный" подэтап 2.1 включается (фильтр строка 192–194):
```python
elif project_subtype and 'Эскизный' in project_subtype:
    entries = [e for e in entries if e['stage_group'] in ('START', 'STAGE1', 'STAGE3')
               or (e['stage_group'] == 'STAGE2' and e['substage_group'] == 'Подэтап 2.1')
               or e['stage_code'] == 'S2_HDR']
```

**Записи "Подготовка файлов СДП" в подэтапе 2.1:** отсутствуют. Подэтап 2.1 начинается напрямую с "Разработка мудбордов" (Дизайнер). Пункт 13 требует "убрать Подготовка файлов СДП" — такой записи нет в шаблоне, значит либо она добавлялась вручную, либо пункт относится к другому месту.

---

## 3. UI (клиентская часть)

### Фильтрация карточек (`should_show_card_for_employee`, строка 1445)

Метод определяет, показывать ли карточку конкретному сотруднику:

- **Руководитель студии / Старший менеджер проектов:** видят все карточки.
- **Менеджер:** видит карточки, где `manager_id == employee_id`.
- **ГАП:** видит карточки, где `gap_id == employee_id`.
- **СДП:** видит карточки, где `sdp_id == employee_id`.
- **Дизайнер:** видит карточку в колонке "Стадия 2: концепция дизайна" ТОЛЬКО если: `designer_name == employee_name` **И** `designer_completed != 1`.
  - Таким образом: **при `pending_review` (`designer_completed == 1`) карточка исчезает** у дизайнера.
- **Чертёжник:** видит карточку в допустимых колонках (`Стадия 1`, `Стадия 3`/`Стадия 2` в зависимости от типа) ТОЛЬКО если: `draftsman_name == employee_name` **И** `draftsman_completed != 1`.
  - Таким образом: **при `pending_review` (`draftsman_completed == 1`) карточка исчезает** у чертёжника.

**Итог для пункта 1:** карточка исполнителя **исчезает** при `pending_review`. Флаги `designer_completed`/`draftsman_completed` == 1 устанавливаются при вызове `workflow/submit`. Исполнитель не видит карточку в состоянии ожидания проверки.

---

### Кнопки reviewer (строки 2386–2501)

Блок отображается только если `can_review_work == True` (право `crm_cards.complete_approval`) И (`designer_completed == 1` или `draftsman_completed == 1`):

1. **"Отправить клиенту"** (`send_client_btn`) — показывается если `current_wf_status in ('pending_review', None)`. Вызывает `send_to_client_combined()` → `data.workflow_client_send()`.

2. **"На исправление"** (`reject_btn`) — показывается если `current_wf_status in ('pending_review', None)`. Вызывает `reject_work()` → диалог `RejectWithCorrectionsDialog` → `data.workflow_reject()`.

3. **"Клиент согласовал"** (`client_ok_btn`) — показывается ОТДЕЛЬНО от блока `completed_info`, в отдельном `if current_wf_status == 'client_approval'`. Вызывает `client_approved()` → `data.workflow_client_ok()`.

Кнопка **"Принять работу"** (`accept_work`) — **не создаётся** в UI при текущей реализации. Метод существует (строка 3007), но не вызывается из блока инициализации.

---

### Метод `client_approved()` (строка 3243)

1. Вызывает `data.workflow_client_ok(card_id)`.
2. Если ответ содержит `has_next_round == True`: показывает `CustomQuestionBox` "Перейти к кругу 2 или закрыть этап?":
   - Да → `data.workflow_advance_round(card_id)`
   - Нет → `data.workflow_close_stage(card_id)`
3. Если нет следующего круга — просто показывает сообщение об успехе.
4. Обновляет вкладку через `parent.refresh_current_tab()`.

**Права:** только при наличии `crm_cards.complete_approval`. Кнопка "Клиент согласовал" доступна менеджеру, СДП, ГАП, руководителю — всем у кого есть это право. Отдельного ограничения "только СДП/ГАП/Менеджер" нет.

---

### Метод `get_work_status()` (строка 1943)

Возвращает текстовый статус для отображения в карточке:

| workflow_status | Возвращаемое значение |
|---|---|
| `pending_review` | `"Проверка {reviewer}"` (СДП/ГАП/Менеджер) |
| `revision` | `"На исправлении"` |
| `client_approval` | `"Согласование клиента"` |
| `pending_decision` | `"Решение {reviewer}"` |
| None + designer_completed==1 | `"В работе у {reviewer}"` |
| None + draftsman_completed==1 | `"В работе у {reviewer}"` |
| иначе | `None` |

---

### Отображение workflow_status на карточке (строки 2083–2106)

Строка подэтапа `current_substep_name` отображается с цветовой кодировкой:

| workflow_status | Цвет | Текст |
|---|---|---|
| `pending_review` | `#8E44AD` (фиолетовый) | `"Ожидает проверки: {substep}"` |
| `revision` | `#E74C3C` (красный) | `"На исправлении: {substep}"` |
| `client_approval` | `#3498DB` (синий) | `"Согласование: {substep}"` |
| `pending_decision` | `#8E44AD` (фиолетовый) | `"Ожидает решения: {substep}"` |
| иначе | `#E67E22` (оранжевый) | `{substep}` |

---

### API-методы workflow в `crm_mixin.py` (строки 329–370)

Все методы существуют и работают:
- `get_workflow_state(card_id)` — GET
- `workflow_submit(card_id)` — POST
- `workflow_accept(card_id)` — POST (используется в `accept_work()`, но не в основном UI)
- `workflow_reject(card_id, corrections_path)` — POST с JSON body
- `workflow_client_send(card_id)` — POST
- `workflow_client_ok(card_id)` — POST
- `workflow_advance_round(card_id)` — POST
- `workflow_close_stage(card_id)` — POST
- `workflow_add_extra_round(card_id, stage_name, ...)` — POST

---

### `utils/data_access.py` — проксирование

Все методы workflow в `DataAccess` проксируются через `api_client` (в online-режиме). Offline-fallback для workflow не реализован — операции workflow работают только в `is_multi_user` режиме.

---

## 4. Сводка текущего состояния по каждому пункту

| # | Пункт | Текущее состояние | Затронутые файлы |
|---|-------|-------------------|-----------------|
| 1 | КАРТОЧКА ВИДНА при pending_review | **Не реализовано.** `should_show_card_for_employee()` скрывает карточку у исполнителя когда `designer_completed == 1` или `draftsman_completed == 1` (флаги устанавливаются при submit). Кнопка "Ожидайте проверку" (строка 2522–2539) показывается, но карточка уже невидима. | `ui/crm_tab.py:1445–1498` |
| 2 | ПЕРЕЗАПИСЬ ДАТ при повторных правках | **Частично реализовано.** При `wf.status == 'revision'` submit перезаписывает `current_substep_code`. При обычной сдаче — ищет следующую пустую строку. Строки reviewer в reject — всегда новая пустая (нет перезаписи). | `server/routers/crm_router.py:1414–1428` |
| 3 | НОВЫЙ СТАТУС stage_completed | **Не реализован.** В `StageWorkflowState.status` определены: `in_progress`, `pending_review`, `revision`, `client_approval`, `pending_decision`, `completed`. Статуса `stage_completed` нет ни в модели, ни в endpoint-ах. | `server/database.py:668` |
| 4 | НОВЫЙ СТАТУС act_signing + кнопка "Акт подписан" | **Не реализован.** Статуса `act_signing` нет. Кнопки "Акт подписан" нет ни в UI, ни в endpoint-ах. | — |
| 5 | ПОДПИСАНИЕ АКТА — отдельная кнопка после каждой стадии | **Не реализовано.** Нет отдельного workflow endpoint для акта. Записи типа "Согласование планировки. Акт" (S1_3_05), "Согласование дизайна. Акт" (S2_7_05) существуют в шаблоне timeline, но не связаны с отдельным действием. | `server/services/timeline_service.py:102,168` |
| 6 | ПЛАТНЫЕ КРУГИ — создание блока в timeline | **Реализовано** (`workflow/add-extra-round`, строка 2168). Создаёт 4 строки: HDR + работа + проверка + отправка клиенту. Код: `S{N}_EXT{n}_HDR/_01/_02/_03`. | `server/routers/crm_router.py:2168–2280` |
| 7 | ДЕДЛАЙН ПЕРЕСЧЁТ ПРИ ПРАВКАХ | **Частично реализовано.** `_update_executor_deadline_for_next_substep()` вызывается после submit/accept/client-ok/advance-round/close-stage. При reject — **не вызывается** (комментарий строка 1664: "правки не двигают timeline"). | `server/routers/crm_router.py:1273–1343, 1664` |
| 8 | ВСЕ ПУНКТЫ НЕ В СРОКЕ = ПАУЗА | **Не реализовано.** Нет проверки "все подэтапы стадии вне срока → дедлайн на паузе". Пауза работает только при `client_approval` (явное поле `client_approval_deadline_paused`). | — |
| 9 | "КЛИЕНТ СОГЛАСОВАЛ" нажимает СДП/ГАП/Менеджер | **Не разграничено.** Кнопка "Клиент согласовал" доступна всем у кого есть `crm_cards.complete_approval`. Нет дополнительного ограничения "только СДП/ГАП/Менеджер". | `ui/crm_tab.py:2473–2501` |
| 10 | ДАТА "СБОР ПРАВОК" по кнопке "Перейти к кругу" / "Закрыть этап" | **Частично реализовано.** Дата "Сбор правок" записывается в `client-ok` (строка 1919) — если строка называется "Сбор правок". При `advance-round` и `close-stage` — **не записывается** отдельно. | `server/routers/crm_router.py:1910–1922` |
| 11 | УБРАТЬ "Подготовка файлов" из Стадии 3 инд. и Стадии 2 шабл. | **Не реализовано.** `S3_01` ("Подготовка файлов, выдача", `СДП`, `is_in_contract_scope=True`) и `T2_01` ("Подготовка файлов, выдача чертежнику", `Менеджер`, `is_in_contract_scope=True`) существуют в шаблоне. | `server/services/timeline_service.py:173,360` |
| 12 | Подэтап 1.2 — входит в срок (is_in_contract_scope=True) | **Частично реализовано.** Только `S1_2_01` (Чертежник) и `T1_2_01` (Чертежник) имеют `is_in_contract_scope=True`. Проверочные строки `S1_2_02`–`S1_2_04` / `T1_2_02`–`T1_2_04` — `False`. Если по пункту 12 нужно чтобы ВСЕ строки 1.2 входили в срок, то изменение требуется. | `server/services/timeline_service.py:89–94, 351–355` |
| 13 | Подэтап 2.1 — убрать "Подготовка файлов СДП", restructure клиентские круги | **Не реализовано (убирать нечего в шаблоне).** В шаблоне `build_project_timeline_template` подэтап 2.1 начинается напрямую с `S2_1_01 = Разработка мудбордов`. Записи "Подготовка файлов СДП" в 2.1 нет. Если записи добавлялись вручную в БД существующих договоров — они живут в `project_timeline_entries`, не в шаблоне. Клиентские круги 2.1 (S2_1_05–S2_1_09): 2 клиентских строки существуют — "Отправка клиенту" (S2_1_05) и "Согласование мудборда" (S2_1_09). | `server/services/timeline_service.py:107–117` |

---

## 5. Модель StageWorkflowState — полный список полей

```python
id, crm_card_id, stage_name, current_substep_code, current_substage_group,
status,  # in_progress | pending_review | revision | client_approval | pending_decision | completed
revision_count, revision_file_path,
client_approval_started_at, client_approval_deadline_paused,
created_at, updated_at
```
(`server/database.py:659–674`)

Статусы `stage_completed` и `act_signing` в модели **отсутствуют**.

---

## 6. Вспомогательные функции пересчёта дедлайна

`_update_executor_deadline_for_next_substep()` (строка 1273):
- Берёт первый незаполненный подэтап с `is_in_contract_scope=True`, `status != 'skipped'`, `norm_days > 0`
- Если следующий подэтап `is_in_contract_scope=False` → **не обновляет дедлайн** (пауза)
- Считает `base_date` от последней заполненной строки
- Записывает в `StageExecutor.deadline`

`_server_recalculate_actual_days()` (строка 1248):
- Пересчитывает `actual_days` для каждой строки как рабочие дни между последовательными `actual_date`

---

## 7. Ключевые файлы для изменений

| Файл | Что содержит |
|------|-------------|
| `server/routers/crm_router.py` | Все workflow endpoints (submit/accept/reject/client-send/client-ok/advance-round/close-stage/add-extra-round) |
| `server/services/timeline_service.py` | Шаблоны подэтапов (S3_01, T2_01, S2_1_*, S1_2_*, T1_2_*) |
| `server/database.py` | Модель StageWorkflowState (список допустимых status) |
| `ui/crm_tab.py` | `should_show_card_for_employee()`, `init_ui()` карточки, `client_approved()`, `get_work_status()` |
| `utils/api_client/crm_mixin.py` | Клиентские proxy-методы для workflow endpoints |
| `utils/data_access.py` | DataAccess-обёртки над workflow методами |
