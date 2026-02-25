# QA-аудит CRM надзора v2 (2026-02-25)

**Ревизор:** QA-аудитор (повторный аудит после исправлений)
**Проверяемые файлы:**
- `server/routers/supervision_router.py`
- `server/routers/supervision_timeline_router.py`
- `server/schemas.py`
- `server/database.py`
- `ui/crm_archive.py`
- `ui/supervision_card_edit_dialog.py`
- `ui/supervision_timeline_widget.py`
- `utils/api_client/supervision_mixin.py`, `timeline_mixin.py`, `messenger_mixin.py`
- `utils/data_access.py`
- `server/routers/contracts_router.py` (частично)

---

## Статус предыдущих проблем

| ID | Описание | Статус | Верификация |
|----|----------|--------|-------------|
| Н-1 | Расхождение имён стадий 7, 8, 9 | ИСПРАВЛЕНО | `supervision_router.py:36-38`: `'Стадия 7: Лепной декор'`, `'Стадия 8: Освещение'`, `'Стадия 9: Бытовая техника'` — совпадают с `supervision_timeline_router.py:28-30` |
| Н-2 | `commission` не в `SupervisionTimelineUpdate` | ИСПРАВЛЕНО | `schemas.py:1141`: `commission: Optional[float] = None` присутствует в классе |
| Н-3 | `status_changed_date` не заполняется | ИСПРАВЛЕНО | `contracts_router.py:161-163`: `contract.status_changed_date = datetime.utcnow().strftime('%Y-%m-%d')` при любой смене статуса |
| Н-4 | `supervision_card_id` в `project_files` отсутствует | НЕ ИСПРАВЛЕНО (арх. ограничение) | `database.py:717-735`: таблица `project_files` по-прежнему без `supervision_card_id`; каскадная очистка по `stage.like('Стадия%')` — частичный workaround |
| Н-5 | Cascade delete файлов | ИСПРАВЛЕНО (частично) | `supervision_router.py:806-810`: при DELETE удаляются `ProjectFile` где `contract_id == card.contract_id AND stage LIKE 'Стадия%'`. **Риск:** удалятся файлы CRM-стадий того же договора, если они называются `'Стадия X: ...'` |
| Н-6 | Дублирование логики resume | ИСПРАВЛЕНО | Авто-resume при перемещении из "В ожидании" (`supervision_router.py:426-459`) записывает `entry_type="resume"` в историю; явный `/resume` тоже записывает. Дублирование логики технически сохраняется, но UI-путь защищён блокировкой перемещения (`is_paused AND old_column != 'В ожидании'`) |
| Н-7 | ДАН валидация роли | ИСПРАВЛЕНО | `supervision_router.py:307-313`: проверка `dan_employee.role not in DAN_ROLES` с `logger.warning`. **Замечание:** это только warning, не ошибка; назначение всё равно произойдёт |
| Н-8 | История смены ДАН/СМП | ИСПРАВЛЕНО | `supervision_router.py:316-337`: при изменении `dan_id` или `senior_manager_id` записывается `entry_type="assignment_change"` с именами старого и нового сотрудника |
| Н-10 | `_count_business_days` без праздников в supervision_router | НЕ ИСПРАВЛЕНО | `supervision_router.py:96-104`: функция считает только пн-пт. В `crm_router.py:46-67` реализована версия с `RUSSIAN_HOLIDAYS`, но в `supervision_router.py` она не импортирована и не используется |
| Н-11 | Оплаты надзора создаются только на UI-стороне | ИСПРАВЛЕНО | `supervision_router.py:65-93`: `_auto_create_supervision_payments` вызывается при уходе из рабочей стадии; проверка дублей по `(supervision_card_id, stage_name)` |
| (новое) | Авто-resume записывает историю | ИСПРАВЛЕНО | `supervision_router.py:452-459`: запись `entry_type="resume"` с сообщением `"Авто-возобновлено (пауза: N дн.)"` |

---

## Ранее непроверенные пункты

| # | Описание | Результат проверки |
|---|----------|--------------------|
| П-1 | Кнопки скриптов в карточке надзора | Реализованы корректно. `supervision_card_edit_dialog.py:409-443`: кнопки `sv_start_script_btn` и `sv_end_script_btn` созданы через `IconLoader`, подключены к `_on_send_supervision_start_script` и `_on_send_supervision_end_script`. Видимость управляется правом `messenger.view_chat` (строки 84-85). Активность — при наличии чата и онлайн-режима (строки 663-665). Маршрут: `data.trigger_script → api_client.trigger_script → POST /api/messenger/trigger-script`. |
| П-2 | Строка "Итого" в timeline | Реализована корректно. `supervision_timeline_widget.py:699-770`: `_add_totals_row` добавляет нередактируемую строку с серым фоном `'#F5F5F5'`. Суммы берутся из `totals` сервера; fallback — локальный подсчёт из `self.entries`. Отображаются: бюджет-план, бюджет-факт, экономия (с цветовым кодированием: зелёный/красный), комиссия. |
| П-3 | Формат totals в `supervision_timeline_router.py` | Верифицирован. `supervision_timeline_router.py:67-79`: `{"entries": [...], "totals": {"budget_planned": ..., "budget_actual": ..., "budget_savings": ..., "commission": ...}}`. `data_access.py:2502-2517` и `timeline_mixin.py:71-96` корректно обрабатывают этот формат. |
| П-4 | Кнопка "В авторский надзор" в архиве | Реализована. `crm_archive.py:199-224`: кнопка показывается если `'АВТОРСКИЙ НАДЗОР' not in status AND 'НАДЗОР' not in status`. При нажатии: `_transfer_to_supervision → data.update_contract → {'status': 'АВТОРСКИЙ НАДЗОР'}`. На сервере `contracts_router.py:170-182` автоматически создаётся `SupervisionCard` если её нет. Обновление списка — через `parent.refresh_current_tab()`. |
| П-5 | Цветовое кодирование архивных карточек | Реализовано. `crm_archive.py:43-54`: СДАН → зелёный (`#E8F8F5`, `#27AE60`); РАСТОРГНУТ → красный (`#FADBD8`, `#E74C3C`); АВТОРСКИЙ НАДЗОР → синий (`#E3F2FD`, `#2196F3`). |
| П-6 | DELETE `/orders/{supervision_card_id}` — полнота очистки | Очищаются: `ProjectFile` (фильтр `stage.like('Стадия%')`), `SupervisionProjectHistory`, `Payment` (по `supervision_card_id`), `SupervisionTimelineEntry`, `SupervisionCard`. НЕ очищаются: `MessengerChat` с `supervision_card_id` (утечка записей в таблице чатов). |
| П-7 | Блокировка перемещения приостановленной карточки | Корректна. `supervision_router.py:397-403`: `is_paused AND new_column != old_column AND old_column != 'В ожидании'` — raise 422. Исключение для выхода из "В ожидании" (авто-resume) работает правильно. |
| П-8 | Авто-оплаты при уходе из стадии | Верифицировано. `supervision_router.py:506-507`: `_auto_create_supervision_payments` вызывается только если `old_column not in ['Новый заказ', 'В ожидании', 'Выполненный проект']` и `old_column != new_column`. Проверка дублей по `(supervision_card_id, stage_name)` на строках 68-73. Суммы рассчитываются из тарифа `Rate` с `project_type='Авторский надзор'`. |
| П-9 | `deadline` тип: String vs Date в статистике | `statistics_router.py:537-540`: сравнение `c.deadline < today` где `c.deadline` — строка `String`, а `today = date_type.today()`. В Python строка `'2026-01-15'` сравнивается с объектом `date`, что вызовет `TypeError` если `deadline` не None (строка не равна объекту date напрямую). Однако Python неявно попытается сравнить их через `<`, что даёт `TypeError` в Python 3. **Потенциально бесшумный баг** — `len([...])` обернёт исключение, если элемент с deadline выдаёт ошибку. Нужно проверить. |

---

## Новые проблемы

| ID | Серьёзность | Описание | Файл:строка |
|----|-------------|----------|-------------|
| В-1 | Средняя | **`MessengerChat` не удаляется при DELETE карточки надзора.** При `DELETE /api/supervision/orders/{id}` удаляются история, оплаты, timeline, файлы, карточка — но не запись `MessengerChat` с `supervision_card_id`. В БД остаётся "осиротевший" чат, ссылающийся на несуществующую карточку. | `supervision_router.py:799-827` |
| В-2 | Средняя | **Н-5 частично некорректен: удаление `ProjectFile` по `stage.like('Стадия%')` может задеть CRM-файлы.** Фильтр `ProjectFile.contract_id == card.contract_id AND stage LIKE 'Стадия%'` удалит любые файлы этого договора с именем стадии вида "Стадия X: ...", включая файлы CRM-карточки (ProjectTimelineEntry). Это некорректное каскадное удаление. | `supervision_router.py:806-810` |
| В-3 | Низкая | **`_count_business_days` в `supervision_router` не учитывает праздники** (Н-10 подтверждён). В `crm_router.py:46-67` есть полная версия с `RUSSIAN_HOLIDAYS`, но в `supervision_router.py:96-104` используется упрощённая (только пн-пт). Расчёт дней паузы будет завышен в праздничные периоды. | `supervision_router.py:96-104` |
| В-4 | Низкая | **Н-7 выполнен как warning, не ошибка.** Валидация роли при назначении ДАН (`supervision_router.py:312-313`) только логирует предупреждение, но не блокирует назначение. Можно назначить ДАНом сотрудника с любой ролью (например, уборщика). | `supervision_router.py:312-313` |
| В-5 | Низкая | **`deadline` в `SupervisionCard` хранится как `String`, сравнивается с `date`-объектом.** В `statistics_router.py:537-540` выражение `c.deadline < today` сравнивает `str` с `datetime.date`. В Python 3 это вызовет `TypeError`. Баг скрыт: если записей с `deadline != None` нет, список пустой и ошибка не возникнет. При первой записи с дедлайном возникнет `TypeError` в list comprehension. | `statistics_router.py:537-540` |
| В-6 | Информационная | **Авто-resume пишет в историю `entry_type="resume"`, но не `entry_type="auto_resume"`.** Нельзя различить явное возобновление (кнопка) и авто-возобновление при перемещении из "В ожидании" по типу записи. Только по тексту `"Авто-возобновлено"`. | `supervision_router.py:455-456` |
| В-7 | Информационная | **`_auto_create_supervision_payments` не создаёт оплату для старшего менеджера без роли.** Цикл `for emp_id, role in [(card.dan_id, 'ДАН'), (card.senior_manager_id, 'Старший менеджер проектов')]` пропускает сотрудника если `emp_id is None`. Корректное поведение (skip если не назначен), но нет записи в историю о том, что оплата не создана. | `supervision_router.py:77-93` |

---

## Итого

### Результаты проверки исправлений

| Категория | Количество |
|-----------|------------|
| Полностью исправлено | 8 (Н-1, Н-2, Н-3, Н-6, Н-7, Н-8, Н-11, авто-resume history) |
| Частично исправлено / с оговорками | 1 (Н-5: cascade delete файлов — логика некорректна, может удалить CRM-файлы) |
| Не исправлено (архитектурное ограничение) | 2 (Н-4: `supervision_card_id` в `project_files`; Н-10: праздники в `_count_business_days`) |

### Новые находки

| Серьёзность | Количество |
|-------------|------------|
| Средняя | 2 (В-1, В-2) |
| Низкая | 3 (В-3, В-4, В-5) |
| Информационная | 2 (В-6, В-7) |

### Наиболее приоритетные к исправлению

1. **В-2** (Средняя): логика удаления файлов `stage.like('Стадия%')` потенциально удалит CRM-файлы. Нужно ограничить только файлами надзора (например, добавить доп. фильтр по пути или источнику).
2. **В-1** (Средняя): `MessengerChat` не удаляется при DELETE надзора. Добавить `db.query(MessengerChat).filter(MessengerChat.supervision_card_id == supervision_card_id).delete()`.
3. **В-5** (Низкая): сравнение `String` с `date` в `statistics_router.py` — добавить `str(today)` или парсинг строки.
4. **В-3** (Низкая): заменить `_count_business_days` в `supervision_router.py` на версию из `crm_router.py` с учётом `RUSSIAN_HOLIDAYS`.

### Общая оценка

Модуль надзора после исправлений заметно улучшился: ключевые бизнес-функции (авто-оплаты, история назначений, авто-resume) работают корректно. Новые фичи (кнопки скриптов, строка "Итого", кнопка "В авторский надзор") реализованы без критических дефектов. Остаются два средних дефекта (В-1, В-2) требующих исправления до следующего релиза.

---

*Отчёт подготовлен: 2026-02-25*
*Версия: v2 (повторный аудит после исправлений)*
