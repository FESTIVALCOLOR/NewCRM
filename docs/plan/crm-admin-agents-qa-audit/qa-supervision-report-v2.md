# QA-аудит: Авторский надзор -- v2

## Дата: 2026-02-25

**Ревизор:** QA-аудитор (повторный аудит после исправлений v1)

**Проверяемые файлы:**
- `server/routers/supervision_router.py` (836 строк)
- `server/routers/supervision_timeline_router.py` (408 строк)
- `server/routers/contracts_router.py` (частично, строки 158-182)
- `server/schemas.py` (строки 577-666, 1111-1155)
- `server/database.py` (строки 489-596, 717-735, 777-795)
- `ui/crm_supervision_tab.py` (2173 строк)
- `ui/supervision_dialogs.py` (2430 строк)
- `ui/supervision_card_edit_dialog.py` (3205 строк)
- `ui/supervision_timeline_widget.py` (872 строк)
- `utils/timeline_calc.py` (48 строк)
- `utils/data_access.py` (частично, строки 910-927)
- `utils/api_client/supervision_mixin.py` (частично)
- `database/migrations.py` (частично, строки 875-894)

---

## Статус предыдущих проблем

| ID | Описание (v1) | Статус v2 | Верификация |
|----|---------------|-----------|-------------|
| 1 | Расхождение имён стадий 7, 8, 9 между Kanban и timeline | ИСПРАВЛЕНО | `supervision_router.py:36-38`: маппинг содержит `'Стадия 7: Лепной декор'`, `'Стадия 8: Освещение'`, `'Стадия 9: Бытовая техника'`. `supervision_timeline_router.py:28-30`: `SUPERVISION_STAGES` содержит идентичные имена. `ui/crm_supervision_tab.py:37-39,189-191`: UI-колонки совпадают. **Остаток:** `database/migrations.py:881-882` содержит СТАРЫЕ имена (клиентская миграция); не влияет на серверную логику, но может оставить inconsistent column_name в локальной SQLite. |
| 2 | `commission` не включена в `SupervisionTimelineUpdate` | ИСПРАВЛЕНО | `schemas.py:1141`: `commission: Optional[float] = None` присутствует в классе `SupervisionTimelineUpdate`. Обновление через API теперь доступно. |
| 3 | `status_changed_date` не заполняется при смене статуса | ИСПРАВЛЕНО | `contracts_router.py:161-163`: `if new_status and new_status != old_status: contract.status_changed_date = datetime.utcnow().strftime('%Y-%m-%d')`. Работает при ВСЕХ сменах статуса, включая переход в АВТОРСКИЙ НАДЗОР и завершение (СДАН/РАСТОРГНУТ). |
| 4 | Файлы надзора не привязаны к `supervision_card_id` | НЕ ИСПРАВЛЕНО | `database.py:717-735`: таблица `project_files` по-прежнему не имеет поля `supervision_card_id`. Привязка идёт по `contract_id` + строковому полю `stage`. Архитектурное ограничение -- требует миграции БД. |
| 5 | При удалении карточки надзора файлы не удаляются | ЧАСТИЧНО ИСПРАВЛЕНО | `supervision_router.py:806-810`: добавлено удаление `ProjectFile` с фильтром `contract_id == card.contract_id AND stage LIKE 'Стадия%'`. Файлы удаляются, но фильтр некорректен (см. В-2 ниже). |
| 6 | Дублирование логики resume | ЧАСТИЧНО ИСПРАВЛЕНО | Авто-resume при перемещении из "В ожидании" (`supervision_router.py:426-468`) записывает историю (`entry_type="resume"`). Явный `/resume` (`supervision_router.py:582-655`) содержит аналогичную логику. **Дублирование кода сохраняется**, но UI-вызов (строка 1020) безвреден: сервер проверяет `if not card.is_paused: raise 422`, и после авто-resume повторный вызов возвращает 422, которое UI игнорирует в except. Однако это лишний сетевой запрос. |
| 7 | Нет валидации роли при назначении ДАН | ЧАСТИЧНО ИСПРАВЛЕНО | `supervision_router.py:307-313`: добавлена проверка `dan_employee.role not in DAN_ROLES`. Однако результат -- только `logger.warning`, назначение всё равно выполняется. Не блокирующая валидация. |
| 8 | История не фиксирует смену ДАН/менеджера | ИСПРАВЛЕНО | `supervision_router.py:316-337`: при изменении `dan_id` или `senior_manager_id` записывается `SupervisionProjectHistory` с `entry_type="assignment_change"` и сообщением `'{Роль} изменён: {старый} -> {новый}'`. Получаются имена сотрудников из БД. |
| 9 | Аватар чата только для 2 типов агентов | НЕ ИСПРАВЛЕНО | `messenger_router.py:440-446`: по-прежнему только `festival` и `petrovich`. Новые типы агентов получают `festival` по умолчанию. Низкий приоритет. |
| 10 | `_count_business_days` не учитывает праздники | НЕ ИСПРАВЛЕНО | `supervision_router.py:96-104`: функция считает только пн-пт (weekday < 5). В `crm_router.py:46-57` есть полноценная реализация с `RUSSIAN_HOLIDAYS`, но она не импортирована и не используется в модуле надзора. |
| 11 | Оплаты создаются только на стороне UI | ИСПРАВЛЕНО | `supervision_router.py:65-93`: функция `_auto_create_supervision_payments` вызывается при уходе из рабочей стадии (строка 507). Создаёт оплаты для ДАН и СМП. Проверка дублей по `(supervision_card_id, stage_name)` на строках 68-73. UI-оплаты при авто-принятии (строки 928-997) тоже проверяют дубли. |
| 12 | Нет fallback для привязки чата вручную | НЕ ИСПРАВЛЕНО | `messenger_router.py:327`: `MessengerChatBind` существует для обычных чатов, но для надзора (`SupervisionChatCreate` строка 26) доступно только автосоздание через MTProto. Ручная привязка не реализована. Низкий приоритет. |

---

## Проверка конкретных функций

### Валидация роли ДАН при назначении dan_id

**Файл:** `server/routers/supervision_router.py:306-313`

```python
DAN_ROLES = ['ДАН', 'Дизайнер авторского надзора']
if 'dan_id' in update_data and update_data['dan_id']:
    dan_employee = db.query(Employee).filter(Employee.id == update_data['dan_id']).first()
    if not dan_employee:
        raise HTTPException(status_code=404, detail="Сотрудник (ДАН) не найден")
    if dan_employee.role not in DAN_ROLES:
        logger.warning(f"Назначен ДАН с ролью '{dan_employee.role}' (ожидается {DAN_ROLES})")
```

**Результат:** Валидация реализована, но не блокирующая (warning без HTTP-ошибки). Проверяется только `employee.role`, не `secondary_position`. Если сотрудник имеет `role='Менеджер'` и `secondary_position='ДАН'`, он пройдёт проверку с предупреждением.

### История изменений при смене dan_id / senior_manager_id

**Файл:** `server/routers/supervision_router.py:316-337`

```python
for field_name, label in [('dan_id', 'ДАН'), ('senior_manager_id', 'Старший менеджер')]:
    if field_name in update_data:
        old_val = getattr(card, field_name)
        new_val = update_data[field_name]
        if old_val != new_val:
            # Получаем имена старого/нового сотрудника...
            history = SupervisionProjectHistory(
                supervision_card_id=card_id,
                entry_type="assignment_change",
                message=msg,
                created_by=current_user.id
            )
            db.add(history)
```

**Результат:** Корректно. Записывается только при фактическом изменении значения (`old_val != new_val`). Имена сотрудников резолвятся через БД, с fallback на `ID:{val}`.

### Каскадное удаление ProjectFile при удалении карточки надзора

**Файл:** `server/routers/supervision_router.py:805-810`

```python
if card.contract_id:
    db.query(ProjectFile).filter(
        ProjectFile.contract_id == card.contract_id,
        ProjectFile.stage.like('Стадия%')
    ).delete(synchronize_session=False)
```

**Результат:** Реализовано, но с дефектом (см. В-2). Фильтр `stage LIKE 'Стадия%'` также захватит CRM-файлы того же договора, если их стадия начинается с "Стадия". CRM-стадии проекта (ProjectTimelineEntry) имеют коды вида `STAGE_1`, `SDP_DESIGN` и т.д., а `ProjectFile.stage` хранит человекочитаемое имя (например, `'Стадия 1: Замер'`). Потенциальный конфликт.

### Авто-создание платежей при переходе стадии

**Файл:** `server/routers/supervision_router.py:65-93, 506-507`

Серверная функция `_auto_create_supervision_payments` вызывается при уходе карточки из рабочей стадии:
1. Проверяет дубли по `(supervision_card_id, stage_name)` (строки 68-73)
2. Создаёт оплаты для ДАН и СМП (если назначены) (строки 77-93)
3. Рассчитывает сумму через `_calc_supervision_payment_amount` (area * rate_per_m2) (строки 47-62)

**Результат:** Корректно. Дубли блокируются. Оплаты создаются с `payment_type='Полная оплата'` и привязкой к `report_month`.

### Авто-resume: запись в историю

**Файл:** `server/routers/supervision_router.py:452-459`

```python
resume_history = SupervisionProjectHistory(
    supervision_card_id=card_id,
    entry_type="resume",
    message=f"Авто-возобновлено (пауза: {pause_days} дн.)" if pause_days > 0 else "Авто-возобновлено",
    created_by=current_user.id
)
db.add(resume_history)
```

**Результат:** Корректно записывается. Текстовая метка "Авто-" отличает от явного resume. Однако `entry_type` одинаковый ("resume") -- нельзя различить программно без парсинга message.

### Все 12 стадий надзора

**Сервер (маппинг):** `supervision_router.py:29-42` -- 12 стадий STAGE_1..STAGE_12
**Сервер (timeline init):** `supervision_timeline_router.py:21-34` -- 12 стадий, имена совпадают
**UI (Kanban):** `crm_supervision_tab.py:180-195` -- 15 колонок (2 служебных + 12 рабочих + 1 итоговая)
**UI (маппинг):** `crm_supervision_tab.py:30-43` -- 12 стадий, совпадает с сервером
**UI (timeline widget):** `supervision_timeline_widget.py:512` -- 12 стадий, совпадает

**Результат:** Все 12 стадий синхронизированы между сервером, UI и timeline. Имена стадий идентичны.

---

## Новые проблемы

### НС1 -- СРЕДНЯЯ: MessengerChat не удаляется при DELETE карточки надзора

**Файл:** `server/routers/supervision_router.py:799-827`

При удалении карточки надзора (`DELETE /api/supervision/orders/{id}`) удаляются:
- `ProjectFile` (фильтр `stage LIKE 'Стадия%'`)
- `SupervisionProjectHistory`
- `Payment` (по `supervision_card_id`)
- `SupervisionTimelineEntry`
- `SupervisionCard`

НО НЕ удаляется `MessengerChat` (`database.py:783`), имеющая поле `supervision_card_id`. В БД остаётся "осиротевший" чат, ссылающийся на несуществующую карточку. Поле `supervision_card_id` в `MessengerChat` объявлено как `nullable=True` без `ForeignKey`, поэтому каскадного удаления нет.

**Рекомендация:** Добавить перед удалением карточки:
```python
from database import MessengerChat
db.query(MessengerChat).filter(
    MessengerChat.supervision_card_id == supervision_card_id
).delete(synchronize_session=False)
```

### НС2 -- СРЕДНЯЯ: Удаление ProjectFile по `stage LIKE 'Стадия%'` может удалить CRM-файлы

**Файл:** `server/routers/supervision_router.py:806-810`

Фильтр `ProjectFile.stage.like('Стадия%')` удаляет ВСЕ файлы данного договора, чья стадия начинается с "Стадия". Если у договора в основной CRM-карточке есть файлы со стадиями вида "Стадия X: ..." (например, при ручной загрузке), они тоже будут удалены.

**Текущий фактический риск:** CRM-стадии проекта (ProjectTimelineEntry) имеют stage_code вроде `SDP_DESIGN`, `START`, а не "Стадия X: ...". Однако `ProjectFile.stage` хранит произвольную строку, и нет гарантии что ни один CRM-файл не будет иметь stage, начинающийся со "Стадия".

**Рекомендация:** Добавить более специфический фильтр, например `stage LIKE 'Стадия%: Закупка%'` или использовать перечень конкретных стадий из `_SUPERVISION_COLUMN_TO_STAGE.keys()`.

### НС3 -- СРЕДНЯЯ: UI вызывает resume после move из "В ожидании" (лишний запрос)

**Файл:** `ui/crm_supervision_tab.py:1017-1023`

```python
if from_column == 'В ожидании':
    try:
        self.data.resume_supervision_card(card_id, self.employee['id'])
    except Exception as e:
        print(f"   Ошибка resume: {e}")
```

UI вызывает `data.move_supervision_card` (строка 1013), после чего отдельно вызывает `data.resume_supervision_card` (строка 1020). Но `move_supervision_card` на сервере уже делает авто-resume (`supervision_router.py:426-468`). Повторный `resume` получает HTTP 422 ("Карточка не приостановлена"), которое ловится в except и подавляется.

**Последствия:** Лишний HTTP-запрос, шум в логах сервера (exception логируется), потенциальная путаница при дебаге. Фактического двойного сдвига дедлайнов не происходит благодаря серверной проверке.

**Рекомендация:** Убрать вызов `resume_supervision_card` из UI строки 1020, т.к. авто-resume на сервере полностью покрывает этот сценарий.

### НС4 -- СРЕДНЯЯ: Сравнение String deadline с date-объектом в статистике

**Файл:** `server/routers/statistics_router.py:537-540`

```python
today = date_type.today()
overdue = len([
    c for c in cards
    if c.deadline and c.deadline < today and c.contract.status == 'АВТОРСКИЙ НАДЗОР'
])
```

`SupervisionCard.deadline` объявлен как `Column(String)` (`database.py:499`). Сравнение строки `'2026-01-15'` с объектом `datetime.date(2026, 2, 25)` через `<` вызывает `TypeError` в Python 3. Баг проявится при первой карточке надзора с заполненным дедлайном.

**Рекомендация:** Заменить на `c.deadline < str(today)` или `datetime.strptime(c.deadline, '%Y-%m-%d').date() < today`.

### НС5 -- НИЗКАЯ: Клиентская миграция содержит старые имена стадий

**Файл:** `database/migrations.py:881-882`

```python
'Стадия 7: Лепного декора', 'Стадия 8: Освещения',
'Стадия 9: бытовой техники', ...
```

Миграция оффлайн-БД использует старые имена стадий в SQL-фильтре NOT IN. Карточки со СТАРЫМИ именами стадий не будут сброшены (корректно), но карточки с НОВЫМИ именами ("Лепной декор") тоже не будут сброшены (корректно). Однако если создать карточку в оффлайне с новым именем и потом синхронизировать -- несоответствие может вызвать проблемы.

**Рекомендация:** Обновить имена стадий в миграции до актуальных.

### НС6 -- НИЗКАЯ: `_count_business_days` без праздников (подтверждение Н-10)

**Файл:** `server/routers/supervision_router.py:96-104`

```python
def _count_business_days(start_date, end_date):
    days = 0
    current = start_date
    while current < end_date:
        if current.weekday() < 5:
            days += 1
        current += timedelta(days=1)
    return days
```

В `crm_router.py:46-57` есть `RUSSIAN_HOLIDAYS` и `_is_workday(d)`, но в supervision_router.py используется упрощённая версия.

**Рекомендация:** Вынести `RUSSIAN_HOLIDAYS` и `_is_workday` в общий модуль `utils/calendar_helpers.py` и использовать в обоих роутерах.

### НС7 -- НИЗКАЯ: Нет серверной фильтрации карточек по роли ДАН

**Файл:** `server/routers/supervision_router.py:112-148`

Эндпоинт `GET /api/supervision/cards` не принимает параметр `dan_id` для фильтрации. Сервер возвращает ВСЕ карточки. Фильтрация (`dan_id == employee_id`) выполняется только на клиенте (UI). Это:
1. Передаёт лишние данные по сети (все карточки вместо только своих)
2. Позволяет ДАН-у увидеть чужие карточки через прямой API-запрос (минорная проблема безопасности)

**Рекомендация:** Добавить необязательный параметр `dan_id: Optional[int] = None` с фильтром `SupervisionCard.dan_id == dan_id`.

### НС8 -- ИНФОРМАЦИОННАЯ: Авто-resume и явный resume имеют одинаковый entry_type

**Файл:** `supervision_router.py:455` vs `supervision_router.py:634-639`

Оба записывают `entry_type="resume"`. Различить можно только по тексту сообщения ("Авто-возобновлено" vs "Возобновлено"). Для аудита/отчётов это неудобно.

**Рекомендация:** Использовать `entry_type="auto_resume"` для авто-возобновления.

### НС9 -- ИНФОРМАЦИОННАЯ: Excel-экспорт не включает commission

**Файл:** `server/routers/supervision_timeline_router.py:214-252`

Заголовки Excel: `["Стадия", "План. дата", "Факт. дата", "Дней", "Бюджет план", "Бюджет факт", "Экономия", "Поставщик", "Статус", "Примечания"]`. Поле `commission` не включено, хотя доступно в БД и API-ответе.

**Рекомендация:** Добавить колонку "Комиссия" в Excel-экспорт.

---

## Проверка 12 стадий надзора

| # | Стадия | Сервер (router) | Сервер (timeline) | UI Kanban | UI Mapping | Статус |
|---|--------|-----------------|-------------------|-----------|------------|--------|
| 1 | Закупка керамогранита | строка 30 | строка 22 | строка 183 | строка 31 | OK |
| 2 | Закупка сантехники | строка 31 | строка 23 | строка 184 | строка 32 | OK |
| 3 | Закупка оборудования | строка 32 | строка 24 | строка 185 | строка 33 | OK |
| 4 | Закупка дверей и окон | строка 33 | строка 25 | строка 186 | строка 34 | OK |
| 5 | Закупка настенных материалов | строка 34 | строка 26 | строка 187 | строка 35 | OK |
| 6 | Закупка напольных материалов | строка 35 | строка 27 | строка 188 | строка 36 | OK |
| 7 | Лепной декор | строка 36 | строка 28 | строка 189 | строка 37 | OK |
| 8 | Освещение | строка 37 | строка 29 | строка 190 | строка 38 | OK |
| 9 | Бытовая техника | строка 38 | строка 30 | строка 191 | строка 39 | OK |
| 10 | Закупка заказной мебели | строка 39 | строка 31 | строка 192 | строка 40 | OK |
| 11 | Закупка фабричной мебели | строка 40 | строка 32 | строка 193 | строка 41 | OK |
| 12 | Закупка декора | строка 41 | строка 33 | строка 194 | строка 42 | OK |

Все 12 стадий синхронизированы между всеми компонентами.

---

## Итого

### Статус предыдущих проблем (v1)

- **Исправлено полностью:** 5 из 12 (проблемы 1, 2, 3, 8, 11)
- **Исправлено частично:** 3 из 12 (проблемы 5, 6, 7)
- **Не исправлено (архитектурное/низкий приоритет):** 4 из 12 (проблемы 4, 9, 10, 12)

### Новые проблемы: 9

| Серьёзность | Количество | ID |
|-------------|------------|----|
| Средняя | 4 | НС1, НС2, НС3, НС4 |
| Низкая | 3 | НС5, НС6, НС7 |
| Информационная | 2 | НС8, НС9 |

### Приоритет исправлений

1. **НС4** (Средняя): `TypeError` при сравнении String deadline с date в статистике -- реальный баг, проявится при первой карточке с дедлайном
2. **НС1** (Средняя): MessengerChat не удаляется -- утечка данных в БД
3. **НС2** (Средняя): Удаление файлов по `LIKE 'Стадия%'` -- потенциальная потеря CRM-файлов
4. **НС3** (Средняя): Лишний resume-запрос из UI -- простое исправление, убрать строки 1018-1023

### Общая оценка

Модуль надзора после исправлений v1 значительно улучшился. Ключевые бизнес-функции работают корректно:
- Авто-создание оплат на сервере (а не только в UI)
- История назначений ДАН/СМП
- Автоматическое заполнение `status_changed_date`
- Синхронизация имён стадий между всеми компонентами
- Поле `commission` доступно для обновления через API

Критических багов нет. Из средних наиболее опасен НС4 (TypeError в статистике), который проявится при реальном использовании.

---

*Отчёт подготовлен: 2026-02-25*
*Версия: v2 (повторный аудит после исправлений v1)*
*Файлы: supervision_router.py, supervision_timeline_router.py, contracts_router.py, schemas.py, database.py, crm_supervision_tab.py, supervision_dialogs.py, supervision_card_edit_dialog.py, supervision_timeline_widget.py, timeline_calc.py, statistics_router.py, messenger_router.py, migrations.py*
