# Design: Workflow V2 Redesign

Технический дизайн на основе [research.md](research.md) и [workflow-guide.md](../../workflow-guide.md).

---

## 1. Изменения в модели данных

### 1.1 Новые значения status в StageWorkflowState

Поле `status` в `StageWorkflowState` (файл `server/database.py:668`) — тип `String`. Валидация на уровне модели отсутствует, поэтому новые строковые значения принимаются автоматически.

**Текущие значения:** `in_progress`, `pending_review`, `revision`, `client_approval`, `pending_decision`, `completed`

**Добавляемые значения:**
- `stage_completed` — стадия полностью завершена, акт подписан, reviewer может перемещать карточку в канбане
- `act_signing` — ожидание подписания акта (после закрытия этапа / согласования последнего круга, до `stage_completed`)

**Миграция БД:** НЕ требуется. Поле `status` — произвольная строка, новые значения записываются без изменения схемы.

### 1.2 Новая строка в шаблоне timeline

В конце каждого `stage_group` добавляется строка "Акт подписан" (или "Акт/Планировка подписаны" для Стадии 1). Подробности — в разделе 3.4.

---

## 2. Серверные изменения (crm_router.py)

### 2.1 workflow/reject — добавить пересчёт дедлайна (пункт 7)

**Файл:** `server/routers/crm_router.py`
**Текущее поведение (строка 1664):** Комментарий `# НЕ обновляем дедлайн — правки не двигают timeline`.
**Целевое поведение:** При reject дедлайн ПЕРЕСЧИТЫВАЕТСЯ — вызвать `_update_executor_deadline_for_next_substep()`.

**Изменение:**
- Заменить строку 1664 (`# НЕ обновляем дедлайн — правки не двигают timeline`) на вызов:
  ```
  _update_executor_deadline_for_next_substep(db, card_id, stage_name, contract_id)
  ```
- Вызов должен быть ДО `db.commit()` (строка 1666).

**Логика пересчёта:** `_update_executor_deadline_for_next_substep()` уже находит первый незаполненный подэтап с `is_in_contract_scope=True` и рассчитывает дедлайн. При reject текущий подэтап продвигается на строку "Правка", и функция пересчитает дедлайн от этой строки.

---

### 2.2 workflow/reject — перезапись даты при повторных правках (пункт 2)

**Файл:** `server/routers/crm_router.py`, строки 1616–1628
**Текущее поведение:** Ищет ПЕРВУЮ ПУСТУЮ строку reviewer (`actual_date IS NULL`) после текущего подэтапа → записывает дату. Никогда не перезаписывает.
**Целевое поведение:** Если повторный reject (revision_count > 1), дата в строке "Повторная проверка" ПЕРЕЗАПИСЫВАЕТСЯ на текущую.

**Изменение в блоке записи даты reviewer (строки 1616–1628):**

Текущий код ищет reviewer_entry с фильтром `actual_date IS NULL`. Нужно добавить fallback:

1. Сначала ищем пустую строку reviewer (как сейчас).
2. Если пустой нет (все заполнены) И `wf.revision_count > 1` — ищем ПОСЛЕДНЮЮ ЗАПОЛНЕННУЮ строку reviewer в текущем подэтапе (substage_group) с `sort_order > current_entry.sort_order` → перезаписываем её `actual_date` на текущую дату.

**Pseudocode:**
```
reviewer_entry = найти_первую_пустую_reviewer()
if not reviewer_entry and wf.revision_count > 1:
    # Повторный reject — перезаписываем последнюю reviewer строку
    reviewer_entry = db.query(ProjectTimelineEntry).filter(
        contract_id, stage_group, executor_role IN reviewer_roles,
        sort_order > current_entry.sort_order,
        actual_date IS NOT NULL AND actual_date != '',
        # В рамках текущего substage_group (если иерархическая стадия)
    ).order_by(sort_order DESC).first()
if reviewer_entry:
    reviewer_entry.actual_date = utcnow().strftime('%Y-%m-%d')
```

**Дополнительно (submit при revision):** В endpoint `workflow/submit` (строка 1414–1428) уже реализована перезапись даты исполнителя при `wf.status == 'revision'` — он перезаписывает `actual_date` в строке `wf.current_substep_code`. Это корректно и соответствует workflow-guide.

---

### 2.3 workflow/client-ok — убрать запись "Сбор правок" (пункт 10)

**Файл:** `server/routers/crm_router.py`, строки 1910–1924
**Текущее поведение:** После записи даты в клиентскую строку, ищет следующую строку с `'сбор правок'` в названии → записывает дату.
**Целевое поведение:** НЕ записывать дату в строку "Сбор правок" при client-ok. Дата "Сбор правок" записывается ПОЗЖЕ — при advance-round или close-stage.

**Изменение:**
- Удалить блок строк 1910–1924 (поиск и запись `collection_entry`).
- Переменная `collection_entry` далее используется в строке 1981 для определения `last_recorded`:
  ```python
  last_recorded = collection_entry or (client_entry if stage_group else None)
  ```
  Заменить на:
  ```python
  last_recorded = client_entry if stage_group else None
  ```
- Возвращаемое значение endpoint уже содержит `has_next_round` — для UI этого достаточно.

**Новое поле в ответе:** Добавить `is_last_round: bool` — указывает, является ли текущий круг последним (нет ROUND_PAIRS для текущего подэтапа И нет следующего подэтапа в stage_group). Это нужно для UI, чтобы показать кнопки "Платный круг" и "Акт подписан".

**Pseudocode ответа:**
```python
return {
    "status": "client_approved",
    "has_next_round": has_next,
    "next_round_name": next_name,
    "is_last_round": not has_next and not has_next_substage,
}
```

Для определения `is_last_round`: если `has_next_round == False` — проверить, есть ли ещё незаполненные подэтапы в stage_group (исполнительские строки с `actual_date IS NULL`, `status != 'skipped'` после текущей клиентской строки). Если нет — это последний круг.

---

### 2.4 workflow/advance-round — добавить запись "Сбор правок" (пункт 10)

**Файл:** `server/routers/crm_router.py`, строки 2043–2104
**Текущее поведение:** Только переключает `wf.current_substep_code` и `wf.current_substage_group` на первый подэтап следующего круга.
**Целевое поведение:** ПЕРЕД переключением — записать дату в строку "Сбор правок" текущего подэтапа.

**Изменение — добавить блок ПОСЛЕ проверки `next_subgroup` (строка 2069), ПЕРЕД поиском `next_entry` (строка 2073):**

**Pseudocode:**
```python
# Записываем дату в строку "Сбор правок" текущего подэтапа
if contract_id and stage_group:
    reviewer_roles = ['СДП', 'Менеджер', 'ГАП']
    # Ищем строку "Сбор правок" в текущем substage_group
    collection_entry = db.query(ProjectTimelineEntry).filter(
        contract_id == contract_id,
        stage_group == stage_group,
        executor_role IN reviewer_roles,
        substage_group == current_subgroup,
        'сбор правок' in lower(stage_name),
        actual_date IS NULL or actual_date == ''
    ).order_by(sort_order).first()
    if collection_entry:
        collection_entry.actual_date = utcnow().strftime('%Y-%m-%d')
        collection_entry.updated_at = utcnow()
```

---

### 2.5 workflow/close-stage — добавить запись "Сбор правок" + статус act_signing (пункты 4, 10)

**Файл:** `server/routers/crm_router.py`, строки 2107–2165
**Текущее поведение:** Помечает все незаполненные строки как `skipped`, устанавливает `wf.status = 'completed'`.
**Целевое поведение:**
1. ПЕРЕД пометкой skipped — записать дату в строку "Сбор правок" текущего подэтапа (если есть).
2. Установить `wf.status = 'act_signing'` (НЕ `completed`). Статус `completed` заменяется на `stage_completed` и устанавливается только при подписании акта (endpoint sign-act).

**Изменение 1 — запись "Сбор правок":**

Добавить блок ПЕРЕД пометкой unfilled как skipped (строка 2131):

**Pseudocode:**
```python
# Записываем дату в строку "Сбор правок" текущего подэтапа
if wf and wf.current_substage_group:
    reviewer_roles = ['СДП', 'Менеджер', 'ГАП']
    collection_entry = db.query(ProjectTimelineEntry).filter(
        contract_id == contract_id,
        stage_group == stage_group,
        executor_role IN reviewer_roles,
        substage_group == wf.current_substage_group,
        'сбор правок' in lower(stage_name),
        actual_date IS NULL or actual_date == ''
    ).order_by(sort_order).first()
    if collection_entry:
        collection_entry.actual_date = utcnow().strftime('%Y-%m-%d')
        collection_entry.updated_at = utcnow()
```

**Изменение 2 — статус:**

Заменить строку 2144:
```python
wf.status = 'completed'
```
На:
```python
wf.status = 'act_signing'
```

---

### 2.6 НОВЫЙ endpoint: workflow/sign-act (пункты 4, 5)

**Файл:** `server/routers/crm_router.py`
**Расположение:** После `workflow/close-stage` (строка 2166), перед `workflow/add-extra-round` (строка 2168).

**Спецификация:**
```
POST /cards/{card_id}/workflow/sign-act
Права: crm_cards.complete_approval
```

**Логика:**
1. Получить card, stage_name, contract_id, stage_group
2. Найти строку "Акт" в таймлайне текущего stage_group:
   ```python
   act_entry = db.query(ProjectTimelineEntry).filter(
       contract_id, stage_group,
       stage_name содержит 'акт' (lower),
       actual_date IS NULL or actual_date == ''
   ).order_by(sort_order.desc()).first()
   ```
   Поиск: `'акт' in stage_name.lower()` — покрывает "Принятие проекта. Акт финальный", "Согласование дизайна. Акт", "Акт/Планировка подписаны", "Акт подписан / Закрытие".
3. Записать `actual_date = utcnow().strftime('%Y-%m-%d')` в найденную строку.
4. Обновить `wf.status = 'stage_completed'`.
5. Запись в ActionHistory: `action_type='sign_act'`.
6. Вызвать `_server_recalculate_actual_days()`.
7. Вызвать `_update_executor_deadline_for_next_substep()`.
8. Уведомление в чат через `trigger_messenger_notification()`.
9. `db.commit()`.

**Ответ:**
```json
{"status": "act_signed", "stage_name": "..."}
```

**Доступность кнопки:** Endpoint доступен когда `wf.status == 'act_signing'`. На уровне endpoint-а проверка:
```python
if wf.status != 'act_signing':
    raise HTTPException(400, "Акт можно подписать только в статусе act_signing")
```

---

### 2.7 workflow/add-extra-round — доработка для UI-кнопки (пункт 6)

**Файл:** `server/routers/crm_router.py`, строки 2168–2294
**Текущее состояние:** Endpoint реализован и работает. Создаёт 4 строки: HDR + работа + проверка + клиент.

**Необходимые изменения:**

1. **После создания записей** — обновить `wf.current_substep_code` и `wf.current_substage_group` на первую строку нового круга (сейчас НЕ делается):
   ```python
   wf = db.query(StageWorkflowState).filter(...).first()
   if wf:
       wf.current_substep_code = f'{prefix}{stage_num}_EXT{ext_num}_01'
       wf.current_substage_group = f'Доп. круг {ext_num}'
       wf.status = 'in_progress'
       wf.revision_count = 0
       wf.updated_at = utcnow()
   ```

2. **Добавить строки "Правка" и "Повторная проверка"** в структуру платного круга (сейчас их нет — только работа + проверка + клиент). По workflow-guide, платный круг имеет 5 строк:
   - HDR
   - _01: Работа исполнителя
   - _02: Проверка reviewer
   - _03: Правка исполнителем
   - _04: Повторная проверка reviewer
   - _05: Согласование клиента

   Это значит сдвигать sort_order на 6 (а не 4) и создавать 6 записей.

3. **Обновить `_ROUND_PAIRS`** или создать аналогичный механизм для платных кругов — после согласования клиентом платного круга должна быть возможность создать ещё один платный круг.

**Автоопределение ролей:** Endpoint принимает `executor_role` и `reviewer_role` из body, но UI должен передавать их автоматически. Роли определяются по стадии:
- Стадия 1 (инд.): executor=Чертежник, reviewer=СДП
- Стадия 2 (инд.): executor=Дизайнер, reviewer=СДП
- Стадия 3 (инд.): executor=Чертежник, reviewer=ГАП

---

### 2.8 workflow/client-ok — определение is_last_round для UI (пункты 5, 6)

**Файл:** `server/routers/crm_router.py`, строки 1956–1978
**Текущее поведение:** Проверяет `ROUND_PAIRS` → если есть следующий круг: `pending_decision`, иначе `in_progress`.
**Целевое поведение:**
- Если есть следующий круг по `ROUND_PAIRS`: `wf.status = 'pending_decision'`
- Если нет следующего круга по `ROUND_PAIRS` — это "последний круг". Проверить, есть ли ещё незаполненные подэтапы:
  - Если есть → `wf.status = 'in_progress'` (как сейчас — переход к следующему подэтапу)
  - Если нет (все заполнены/skipped) → `wf.status = 'act_signing'` (переход к подписанию акта)

**Для определения "последнего круга":** Нужно проверить, есть ли вне текущего substage_group ещё незаполненные исполнительские строки (не header, не skipped, actual_date IS NULL) в данном stage_group.

**Ответ дополняется:**
```python
return {
    "status": "client_approved",
    "has_next_round": has_next,
    "next_round_name": next_name,
    "is_last_round": is_last,     # для кнопки "Платный круг"
    "act_signing": wf.status == 'act_signing',  # для кнопки "Акт подписан"
}
```

---

### 2.9 Пауза дедлайна при подэтапах вне срока (пункт 8)

**Файл:** `server/routers/crm_router.py`, функция `_update_executor_deadline_for_next_substep()` (строка 1273)
**Текущее поведение (строки 1298–1305):** Если следующий подэтап `is_in_contract_scope=False` → дедлайн не обновляется (молча пропускает). Пауза работает ТОЛЬКО при `client_approval` (явное поле `client_approval_deadline_paused`).
**Целевое поведение:** Все подэтапы вне срока = пауза дедлайна. Пауза начинается когда текущий подэтап `is_in_contract_scope=False` и заканчивается когда следующий `is_in_contract_scope=True`.

**Анализ:** Текущая реализация уже фактически реализует это поведение:
- Когда `is_in_contract_scope=False` → `return` (дедлайн не обновляется = замораживается на текущем значении).
- Когда переходим к подэтапу с `is_in_contract_scope=True` → дедлайн пересчитывается от `base_date` (последняя `actual_date`).

**Проблема:** При `is_in_contract_scope=False` дедлайн не просто "замораживается" — он должен СДВИГАТЬСЯ ВПЕРЁД на время, проведённое в паузе. Это делается в `client-ok` через `_count_business_days()` для `client_approval_deadline_paused`. Но для других пауз (сбор правок, платные круги) такого механизма нет.

**Решение:** Обобщить механизм паузы:
1. В `_update_executor_deadline_for_next_substep()` — когда `is_in_contract_scope=False`, зафиксировать `wf.pause_started_at = utcnow()` (новое поле или использовать `client_approval_started_at`).
2. Когда переходим обратно к подэтапу с `is_in_contract_scope=True` — посчитать рабочие дни паузы и сдвинуть `card.deadline` и все `StageExecutor.deadline` вперёд.

**Однако** для MVP можно использовать существующий механизм `client_approval_deadline_paused` + `client_approval_started_at`, расширив его на ВСЕ паузы (не только client_approval). Переименование не обязательно — можно использовать как есть с комментарием.

**Минимальное изменение для пункта 8:**
- В endpoint-ах, которые переходят к подэтапу с `is_in_contract_scope=False` (client-send, а также advance-round при переходе на вне-срочный подэтап): устанавливать `wf.client_approval_deadline_paused = True` и `wf.client_approval_started_at = utcnow()`.
- В endpoint-ах, которые возвращаются к подэтапу с `is_in_contract_scope=True`: считать паузу и сдвигать дедлайн (как в client-ok).

**Статус:** Текущая реализация покрывает основной кейс (клиентское согласование). Полная реализация паузы для ВСЕХ вне-срочных подэтапов — отдельная задача, НЕ включённая в текущий scope. Для MVP достаточно текущего поведения + пересчёт при reject (пункт 2.1).

---

## 3. Timeline Service (timeline_service.py)

### 3.1 Убрать S3_01 — "Подготовка файлов, выдача" (пункт 11)

**Файл:** `server/services/timeline_service.py`, строка 173
**Текущая строка:**
```python
add('S3_01', 'Подготовка файлов, выдача', 'STAGE3', '', 1, 'СДП', True)
```
**Действие:** Удалить эту строку целиком. Стадия 3 начинается сразу с `S3_02` ("Разработка комплекта РД").

**Важно:** Перенумерация sort_order происходит автоматически в конце функции (строка 198–199), поэтому удаление строки не нарушит порядок.

**Влияние на существующие данные:** Только новые контракты. Для существующих контрактов записи уже в БД и не пересоздаются. Если нужно убрать у существующих — SQL миграция:
```sql
UPDATE project_timeline_entries SET status = 'skipped' WHERE stage_code = 'S3_01';
```

---

### 3.2 Убрать T2_01 — "Подготовка файлов, выдача чертежнику" (пункт 11)

**Файл:** `server/services/timeline_service.py`, строка 360
**Текущая строка:**
```python
add('T2_01', 'Подготовка файлов, выдача чертежнику', 'STAGE2', '', 1, 'Менеджер', True)
```
**Действие:** Удалить эту строку целиком. Стадия 2 шаблонная начинается с `T2_02` ("Разработка комплекта РД").

**Влияние:** Аналогично 3.1.

---

### 3.3 Подэтап 1.2 — is_in_contract_scope=True для ВСЕХ строк (пункт 12)

**Файл:** `server/services/timeline_service.py`

**Индивидуальный проект (строки 89–94):**

Текущее состояние:
| Код | is_in_contract_scope |
|-----|---------------------|
| S1_2_01 | True |
| S1_2_02 | **False** → True |
| S1_2_03 | **False** → True |
| S1_2_04 | **False** → True |
| S1_2_05 | **False** (оставить — клиент, пауза) |
| S1_2_06 | **False** (оставить — сбор правок, пауза) |

**Изменения:**
- Строка 90: `S1_2_02` — `False` → `True`
- Строка 91: `S1_2_03` — `False` → `True`
- Строка 92: `S1_2_04` — `False` → `True`
- Строки S1_2_05 (Клиент) и S1_2_06 (Сбор правок) — оставить `False` (это паузы по определению).

**Шаблонный проект (строки 351–355):**

| Код | is_in_contract_scope |
|-----|---------------------|
| T1_2_01 | True |
| T1_2_02 | **False** → True |
| T1_2_03 | **False** → True |
| T1_2_04 | **False** → True |
| T1_2_05 | **False** (оставить — клиент, пауза) |

**Изменения:**
- Строка 352: `T1_2_02` — `False` → `True`
- Строка 353: `T1_2_03` — `False` → `True`
- Строка 354: `T1_2_04` — `False` → `True`

**Влияние:** Изменения затрагивают расчёт дедлайна — строки проверки и правки Подэтапа 1.2 теперь входят в срок договора. Нормо-дни этих строк будут учитываться в общем сроке.

---

### 3.4 Добавить строку "Акт подписан" в конце каждого stage_group (пункт 5)

В шаблоне timeline уже есть строки, связанные с актами, но они привязаны к роли "Клиент" (например, S1_3_05, S2_7_05, S3_12). Нужно добавить ОТДЕЛЬНЫЕ строки "Акт подписан" в конце каждого stage_group.

**Анализ существующих строк-актов:**

| Стадия | Код | Текущее название | Роль |
|--------|-----|-----------------|------|
| STAGE1 инд. | S1_3_05 | "Согласование планировки. Акт" | Клиент |
| STAGE2 инд. | S2_7_05 | "Согласование дизайна. Акт" | Клиент |
| STAGE3 инд. | S3_12 | "Принятие проекта. Акт финальный" | Клиент |
| STAGE1 шабл. | — | Нет строки акта | — |
| STAGE2 шабл. | T2_12 | "Принятие проекта. Закрытие." | Клиент |
| STAGE3 шабл. | T3_06 | "Принятие проекта. Закрытие." | Клиент |

**Проблема:** Текущие строки актов имеют роль "Клиент", но по workflow-guide акт подписывает Менеджер/Старший менеджер. Нужно:

**Вариант А (рекомендуемый):** Изменить executor_role существующих строк-актов с "Клиент" на соответствующего reviewer:

- `S1_3_05` → executor_role=`'СДП'`, stage_name=`'Акт/Планировка подписаны'`
- `S2_7_05` → executor_role=`'СДП'`, stage_name=`'Акт подписан'`
- `S3_12` → executor_role=`'Менеджер'`, stage_name=`'Акт подписан'`
- `T2_12` → executor_role=`'Менеджер'`, stage_name=`'Акт подписан / Закрытие'`
- `T3_06` → executor_role=`'Менеджер'`, stage_name=`'Этап завершён / Акт подписан'`

**Добавить новую строку для STAGE1 шаблонного:**
```python
add('T1_2_06', 'Акт/Планировка подписаны', 'STAGE1', 'Подэтап 1.2', 0, 'Менеджер', False)
```
(после T1_2_05, sort_order автоматически пересчитается)

**Вариант Б (минимальный):** Не менять существующие строки, но endpoint `sign-act` будет искать строку по паттерну `'акт'` в `stage_name.lower()` — покроет все варианты.

**Рекомендация:** Вариант А для новых контрактов + Вариант Б для совместимости с существующими.

---

### 3.5 Подэтап 2.1 — restructure клиентские круги (пункт 13)

**Файл:** `server/services/timeline_service.py`, строки 107–117

**Текущая структура подэтапа 2.1:**
```
S2_1_01  Разработка мудбордов          Дизайнер  True
S2_1_02  Проверка СДП                  СДП       True
S2_1_03  Правка дизайнером             Дизайнер  True
S2_1_04  Проверка повторная СДП         СДП       True
S2_1_05  Отправка клиенту              Клиент    False
S2_1_06  Сбор правок СДП               СДП       False
S2_1_07  Правка дизайнером             Дизайнер  False
S2_1_08  Проверка СДП                  СДП       False
S2_1_09  Согласование мудборда          Клиент    False
```

**Целевая структура (по workflow-guide, раздел "Подэтап 2.1 — Мудборды"):**

Структура уже соответствует workflow-guide. В research.md указано: "Записи 'Подготовка файлов СДП' в 2.1 нет в шаблоне". Пункт 13 упоминает "убрать Подготовка файлов СДП" — убирать нечего.

**Действие:** Пункт 13 уже реализован в текущем шаблоне. Никаких изменений не требуется.

---

## 4. UI изменения (crm_tab.py)

### 4.1 should_show_card_for_employee() — не скрывать при pending_review (пункт 1)

**Файл:** `ui/crm_tab.py`, строки 1473–1490
**Текущее поведение:**
- Дизайнер: `return (designer_name == employee_name) and (designer_completed != 1)` — при `designer_completed == 1` (pending_review) карточка скрывается.
- Чертёжник: `return (draftsman_name == employee_name) and (draftsman_completed != 1)` — аналогично.

**Целевое поведение:** Карточка ВИДНА исполнителю при `pending_review` (показывается надпись "Ожидайте проверку").

**Изменение:**

Для дизайнера (строка 1478):
```python
# БЫЛО:
return (designer_name == employee_name) and (designer_completed != 1)
# СТАЛО:
return designer_name == employee_name
```

Для чертёжника (строка 1490):
```python
# БЫЛО:
return (draftsman_name == employee_name) and (draftsman_completed != 1)
# СТАЛО:
return draftsman_name == employee_name
```

**Логика "Ожидайте проверку"** (строки 2522–2539) уже реализована — показывает неактивную кнопку при `work_already_submitted = True`. После снятия фильтра в `should_show_card_for_employee()` эта логика заработает автоматически.

---

### 4.2 Кнопка "Акт подписан" при act_signing (пункт 4)

**Файл:** `ui/crm_tab.py`
**Расположение:** После блока "Клиент согласовал" (строка 2501), добавить новый блок.

**Pseudocode:**
```python
# Кнопка "Акт подписан" — при статусе act_signing
if self.employee and can_review_work:
    if current_wf_status == 'act_signing':
        sign_act_btn = QPushButton('Акт подписан')
        sign_act_btn.setStyleSheet("""
            QPushButton {
                background-color: #2980B9;
                color: white;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                max-height: 19px;
                min-height: 19px;
            }
            QPushButton:hover { background-color: #2471A3; }
            QPushButton:pressed { background-color: #1F618D; }
        """)
        sign_act_btn.clicked.connect(self.sign_act)
        layout.addWidget(sign_act_btn, 0)
```

**Новый метод `sign_act()`:**
```python
def sign_act(self):
    """Подписание акта — финализация стадии"""
    if not _has_perm(self.employee, self.api_client, 'crm_cards.complete_approval'):
        CustomMessageBox(self, 'Ошибка', 'У вас нет прав.', 'error').exec_()
        return
    try:
        result = self.data.workflow_sign_act(self.card_data['id'])
        CustomMessageBox(
            self, 'Акт подписан',
            f'Акт подписан. Переместите карточку на следующую стадию.',
            'success'
        ).exec_()
        # Обновить вкладку
        parent = self.parent()
        while parent:
            if isinstance(parent, CRMTab):
                parent.refresh_current_tab()
                break
            parent = parent.parent()
    except Exception as e:
        CustomMessageBox(self, 'Ошибка', f'Не удалось подписать акт: {e}', 'error').exec_()
```

---

### 4.3 Кнопка "Платный круг" при pending_decision (пункт 6)

**Файл:** `ui/crm_tab.py`, метод `client_approved()` (строка 3243)
**Текущее поведение:** При `has_next_round == True`: CustomQuestionBox "Да" → advance-round, "Нет" → close-stage.
**Целевое поведение:** При `is_last_round == True` (последний круг, индивидуальный проект): показать 3 кнопки вместо 2.

**Изменение в `client_approved()` (строка 3254):**

Заменить текущую логику на:

**Pseudocode:**
```python
if result and result.get('has_next_round'):
    # Есть следующий круг — 2 кнопки: "Перейти к кругу" / "Закрыть этап"
    reply = CustomQuestionBox(...)
    if reply == Accepted:
        self.data.workflow_advance_round(card_id)
    else:
        self.data.workflow_close_stage(card_id)

elif result and result.get('is_last_round') and project_type == 'Индивидуальный':
    # Последний круг, индивидуальный — 2 кнопки: "Завершить этап" / "Платный круг"
    reply = CustomQuestionBox(
        self,
        'Последний круг',
        'Клиент согласовал.\n\n'
        'Завершить этап (перейти к подписанию акта) или отправить на платный круг правок?\n\n'
        'Да — завершить этап\nНет — платный круг',
    ).exec_()
    if reply == Accepted:
        # Статус уже act_signing (установлен сервером)
        CustomMessageBox(self, 'Этап завершён', 'Нажмите "Акт подписан" для завершения.', 'success').exec_()
    else:
        # Определяем роли для платного круга
        executor_role, reviewer_role = self._get_stage_roles()
        self.data.workflow_add_extra_round(
            card_id, stage_name=current_column,
            executor_role=executor_role, reviewer_role=reviewer_role
        )
        CustomMessageBox(self, 'Платный круг', 'Создан платный круг правок.', 'success').exec_()

elif result and result.get('act_signing'):
    # Все подэтапы завершены, шаблонный или без платных — переход к акту
    CustomMessageBox(self, 'Согласовано', 'Нажмите "Акт подписан" для завершения стадии.', 'success').exec_()

else:
    CustomMessageBox(self, 'Согласовано', '...', 'success').exec_()
```

**Вспомогательный метод `_get_stage_roles()`:**
```python
def _get_stage_roles(self):
    """Определить executor и reviewer по текущей стадии"""
    column = self.card_data.get('column_name', '')
    project_type = self.card_data.get('project_type', '')
    if project_type == 'Индивидуальный':
        if 'Стадия 1' in column:
            return 'Чертежник', 'СДП'
        elif 'Стадия 2' in column:
            return 'Дизайнер', 'СДП'
        elif 'Стадия 3' in column:
            return 'Чертежник', 'ГАП'
    else:
        if 'Стадия 1' in column:
            return 'Чертежник', 'Менеджер'
        elif 'Стадия 2' in column:
            return 'Чертежник', 'ГАП'
        elif 'Стадия 3' in column:
            return 'Дизайнер', 'Менеджер'
    return 'Чертежник', 'Менеджер'  # fallback
```

---

### 4.4 Обновить get_work_status() для новых статусов (пункты 3, 4)

**Файл:** `ui/crm_tab.py`, метод `get_work_status()` (строка 1943)

**Добавить обработку новых статусов после строки 1979:**

```python
if workflow_status == 'act_signing':
    return "Подписание акта"
if workflow_status == 'stage_completed':
    return "Этап завершён"
```

---

### 4.5 Обновить отображение статусов на карточке (пункты 3, 4)

**Файл:** `ui/crm_tab.py`, строки 2083–2106

**Добавить обработку новых статусов в блок цветовой кодировки:**

```python
elif workflow_status == 'act_signing':
    substep_text = f"Подписание акта: {current_substep}"
    substep_color = '#2980B9'  # синий
elif workflow_status == 'stage_completed':
    substep_text = f"Этап завершён"
    substep_color = '#27AE60'  # зелёный
```

---

### 4.6 "Клиент согласовал" — ограничение ролей (пункт 9)

**Файл:** `ui/crm_tab.py`, строка 2483
**Текущее поведение:** Кнопка "Клиент согласовал" доступна ВСЕМ с правом `crm_cards.complete_approval`.
**Целевое поведение по workflow-guide:** "Клиент согласовал" нажимает СДП, ГАП или Менеджер.

**Анализ:** Право `crm_cards.complete_approval` уже назначается только ролям СДП/ГАП/Менеджер/Старший менеджер/Руководитель. Дизайнеры и чертёжники это право не имеют. Дополнительная проверка НЕ требуется — текущая проверка прав достаточна.

**Действие:** Изменений не требуется. Пункт 9 уже покрыт текущей системой прав.

---

## 5. API Client + DataAccess

### 5.1 Новый метод workflow_sign_act()

**Файл:** `utils/api_client/crm_mixin.py`

Добавить после `workflow_close_stage()` (строка 367):
```python
def workflow_sign_act(self, card_id: int) -> Dict[str, Any]:
    """Подписать акт — финализация стадии"""
    return self._post(f'/api/crm/cards/{card_id}/workflow/sign-act')
```

**Файл:** `utils/data_access.py`

Добавить после `workflow_close_stage()` (строка 982):
```python
def workflow_sign_act(self, card_id: int) -> Optional[Dict]:
    """Подписать акт"""
    if self.is_multi_user and self.api_client:
        return self.api_client.workflow_sign_act(card_id)
    return None
```

---

## 6. Порядок реализации

### Фаза 1: Server (независимо)

| # | Задача | Файл | Зависимости |
|---|--------|------|-------------|
| 1a | Новый endpoint sign-act | crm_router.py | Нет |
| 1b | reject — пересчёт дедлайна | crm_router.py | Нет |
| 1c | reject — перезапись даты | crm_router.py | Нет |
| 1d | client-ok — убрать запись "Сбор правок", добавить is_last_round | crm_router.py | Нет |
| 1e | advance-round — запись "Сбор правок" | crm_router.py | Нет |
| 1f | close-stage — запись "Сбор правок" + статус act_signing | crm_router.py | Нет |
| 1g | add-extra-round — обновить wf, расширить структуру | crm_router.py | Нет |

### Фаза 2: Timeline Service (независимо от Фазы 1)

| # | Задача | Файл | Зависимости |
|---|--------|------|-------------|
| 2a | Убрать S3_01 | timeline_service.py | Нет |
| 2b | Убрать T2_01 | timeline_service.py | Нет |
| 2c | is_in_contract_scope=True для S1_2_02–S1_2_04, T1_2_02–T1_2_04 | timeline_service.py | Нет |
| 2d | Обновить строки актов (роль, название) | timeline_service.py | Нет |
| 2e | Добавить T1_2_06 "Акт/Планировка подписаны" для шаблонного | timeline_service.py | Нет |

### Фаза 3: API Client + DataAccess (после Фазы 1)

| # | Задача | Файл | Зависимости |
|---|--------|------|-------------|
| 3a | workflow_sign_act() в crm_mixin.py | crm_mixin.py | 1a |
| 3b | workflow_sign_act() в data_access.py | data_access.py | 3a |

### Фаза 4: UI (после Фазы 3)

| # | Задача | Файл | Зависимости |
|---|--------|------|-------------|
| 4a | should_show_card_for_employee() — убрать фильтр completed | crm_tab.py | Нет |
| 4b | Кнопка "Акт подписан" + метод sign_act() | crm_tab.py | 3b |
| 4c | Обновить client_approved() — 3 варианта (next_round/last_round/act_signing) | crm_tab.py | 1d, 1g |
| 4d | get_work_status() — новые статусы | crm_tab.py | Нет |
| 4e | Отображение статусов — цветовая кодировка | crm_tab.py | Нет |

### Порядок деплоя

1. **Сервер (Фаза 1 + 2):** Все серверные изменения можно деплоить одним коммитом. Docker rebuild обязателен.
2. **Клиент (Фаза 3 + 4):** Деплоить после серверных изменений.

---

## 7. Тесты

### 7.1 Существующие тесты для запуска после изменений

```bash
# Регрессионные тесты UI (ОБЯЗАТЕЛЬНО при изменении crm_tab.py)
pytest tests/anti_pattern/test_ui_regression_guards.py tests/ui/test_widget_config_regression.py -v --timeout=30

# Контрактные тесты API
pytest tests/contract/ -v --timeout=60

# E2E тесты (нужен сервер)
pytest tests/e2e/ -v --timeout=60
```

### 7.2 Новые тесты (написать)

| Тест | Что проверяет | Файл |
|------|-------------|------|
| test_reject_updates_deadline | reject вызывает _update_executor_deadline_for_next_substep | tests/e2e/ |
| test_reject_overwrites_reviewer_date | Повторный reject перезаписывает дату reviewer | tests/e2e/ |
| test_client_ok_no_collection_entry | client-ok НЕ записывает дату в "Сбор правок" | tests/e2e/ |
| test_advance_round_writes_collection | advance-round записывает дату в "Сбор правок" | tests/e2e/ |
| test_close_stage_writes_collection | close-stage записывает дату в "Сбор правок" | tests/e2e/ |
| test_close_stage_status_act_signing | close-stage ставит act_signing (не completed) | tests/e2e/ |
| test_sign_act_sets_stage_completed | sign-act ставит stage_completed | tests/e2e/ |
| test_sign_act_writes_date | sign-act записывает дату в строку акта | tests/e2e/ |
| test_card_visible_at_pending_review | Исполнитель видит карточку при pending_review | tests/ui/ |
| test_s3_01_removed | S3_01 не генерируется в шаблоне | tests/contract/ |
| test_t2_01_removed | T2_01 не генерируется в шаблоне | tests/contract/ |
| test_s1_2_in_contract_scope | S1_2_02–S1_2_04 is_in_contract_scope=True | tests/contract/ |

### 7.3 Верификация после деплоя

1. Docker rebuild на production
2. Health check: `curl http://localhost:8000/health`
3. Проверка нового endpoint:
   ```bash
   curl -X POST -H "Authorization: Bearer TOKEN" \
     http://localhost:8000/api/crm/cards/{card_id}/workflow/sign-act
   ```
4. Smoke-тест клиента: запустить `main.py`, проверить:
   - Карточка видна исполнителю при pending_review
   - Кнопка "Акт подписан" при act_signing
   - Правильные статусы в карточке

---

## 8. Риски и edge cases

### 8.1 Обратная совместимость

- **Существующие карточки с `status='completed'`:** Уже завершённые стадии сохраняют статус `completed`. Новый статус `stage_completed` используется только для НОВЫХ завершений. UI должен обрабатывать ОБА: `completed` и `stage_completed` как "этап завершён".
- **Карточки в process:** Карточки, находящиеся в процессе (любой статус кроме completed), продолжат работать по новой логике.

### 8.2 Параллельные действия

- **Два reviewer одновременно:** Endpoint-ы работают с `db.commit()` — SQLAlchemy с PostgreSQL обеспечивает транзакционность. Гонки маловероятны, но при необходимости можно добавить `SELECT ... FOR UPDATE` на `StageWorkflowState`.

### 8.3 Строки актов в существующих контрактах

- Строки типа "Согласование планировки. Акт" (S1_3_05) имеют роль "Клиент", а не "Менеджер". Endpoint `sign-act` ищет по паттерну `'акт'` в `stage_name.lower()`, поэтому найдёт эти строки независимо от роли.
- Для новых контрактов — роль будет обновлена (раздел 3.4).

### 8.4 Пункт 8 (все пункты не в сроке = пауза)

- Полная реализация обобщённой паузы выходит за scope текущего redesign. Текущий механизм `client_approval_deadline_paused` покрывает основной кейс. Для MVP достаточно добавить пересчёт дедлайна при reject (пункт 2.1).
