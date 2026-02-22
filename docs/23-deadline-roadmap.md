# Дорожная карта: Система дедлайнов

> Полный аудит, текущее состояние и история реализации.
> Дата последнего обновления: 22 февраля 2026 г. | Статус: **Фаза 8 завершена**

---

## 1. Текущее состояние (всё реализовано)

### 1.1 Серверная часть

| Компонент | Файл | Статус |
|-----------|------|--------|
| Генерация таблицы сроков | `server/services/timeline_service.py` | РАБОТАЕТ |
| REST endpoints (7 шт.) | `server/routers/timeline_router.py` | РАБОТАЕТ |
| Настройки нормо-дней (4 шт.) | `server/routers/norm_days_router.py` | РАБОТАЕТ |
| Workflow endpoints (5 шт.) | `server/routers/crm_router.py` | РАБОТАЕТ |
| Модель ProjectTimelineEntry | `server/database.py` | РАБОТАЕТ |
| custom_norm_days в schema | `server/schemas.py` | РАБОТАЕТ |
| Гибкий маппинг stage_group | `server/routers/crm_router.py` | РАБОТАЕТ |

### 1.2 Клиентская часть

| Компонент | Файл | Статус |
|-----------|------|--------|
| Таблица сроков (7 колонок) | `ui/timeline_widget.py` | РАБОТАЕТ |
| Настройки нормо-дней | `ui/norm_days_settings_widget.py` | РАБОТАЕТ |
| Расчёт плановых дат | `utils/timeline_calc.py` | РАБОТАЕТ |
| DataAccess методы (12 шт.) | `utils/data_access.py:2201-2722` | РАБОТАЕТ |
| Авто-расчёт START | `ui/timeline_widget.py:430-489` | РАБОТАЕТ |
| Кнопка-карандаш | `ui/timeline_widget.py:830-917` | РАБОТАЕТ |
| Экспорт Excel/PDF | `ui/timeline_widget.py:964-996` | РАБОТАЕТ |
| Отображение custom_norm_days | `ui/timeline_widget.py:804-826` | РАБОТАЕТ |
| Отображение skipped стадий | `ui/timeline_widget.py:685-695` | РАБОТАЕТ |

### 1.3 Страница "Исполнители и дедлайн" (crm_card_edit_dialog.py)

| Элемент | Виджет | Статус | Описание |
|---------|--------|--------|----------|
| Дедлайн проекта (display) | QLabel | READ-ONLY | Авто-расчёт START + contract_term (pyqtSignal) |
| Кнопка "Изменить дедлайн" | QPushButton | РАБОТАЕТ | Диалог с причиной изменения |
| Дата замера (display) | QLabel | READ-ONLY | OK |
| Кнопка "Изменить дату" | QPushButton | РАБОТАЕТ | Вызывает refresh_start_date() |
| Дедлайн дизайнера | QLabel + кнопка "Изменить" | READ-ONLY | Изменение через диалог с причиной |
| Дедлайн чертёжника | QLabel + кнопка "Изменить" | READ-ONLY | Изменение через диалог с причиной |
| Переназначить дизайнера | IconButton | РАБОТАЕТ | OK |
| Переназначить чертёжника | IconButton | РАБОТАЕТ | OK |

### 1.4 Workflow кнопки и интеграция с timeline

| Кнопка | Сервер | Клиент | Timeline sync |
|--------|--------|--------|---------------|
| Сдать работу | actual_date заполняется | Вызывает API | actual_date записывается |
| Принять работу | actual_date заполняется | Вызывает API | actual_date записывается |
| На исправления | actual_date СДП-проверки | Вызывает API | actual_date записывается |
| Отправить клиенту | actual_date "Клиент" + skip | Вызывает API | Промежуточные status=skipped |
| Клиент согласовал | actual_date согласования | Кнопка по workflow state | actual_date записывается |

---

## 2. История реализации

### Фаза 8.0: Привязка дедлайнов к системе (коммит 651e431)

**Статус:** ЗАВЕРШЕНО

| Задача | Файл | Описание |
|--------|------|----------|
| Дедлайн дизайнера → read-only | `ui/crm_card_edit_dialog.py` | CustomDateEdit → QLabel + кнопка "Изменить" с диалогом (причина обязательна) |
| Дедлайн чертёжника → read-only | `ui/crm_card_edit_dialog.py` | Аналогично дизайнеру |
| Дедлайн проекта → авто-расчёт | `ui/crm_card_edit_dialog.py` | pyqtSignal `deadline_updated` от timeline_widget, авто = START + contract_term |
| Метод `change_executor_deadline()` | `ui/crm_card_edit_dialog.py` | Диалог: текущий дедлайн + новая дата + причина, запись в action_history |
| Сигнал `_on_timeline_deadline_updated()` | `ui/crm_card_edit_dialog.py` | Обновляет deadline_display при пересчёте в timeline |

### Фаза 8.1: Серверные workflow (коммит 8c17368)

**Статус:** ЗАВЕРШЕНО

| Задача | Файл | Описание |
|--------|------|----------|
| workflow_reject → actual_date | `server/routers/crm_router.py` | Записывает дату для первого незаполненного подэтапа (проверка СДП) |
| workflow_client_ok → actual_date | `server/routers/crm_router.py` | Записывает дату согласования клиента в timeline |

### Фаза 8.2: custom_norm_days (коммит 8c17368)

**Статус:** ЗАВЕРШЕНО

| Задача | Файл | Описание |
|--------|------|----------|
| Поле `custom_norm_days` в модели | `server/database.py` | `Column(Integer, nullable=True)` в ProjectTimelineEntry |
| Schema update | `server/schemas.py` | `custom_norm_days` в TimelineEntryBase + TimelineEntryUpdate |
| SQLite миграция | `database/migrations.py` | `add_custom_norm_days_column()` — ALTER TABLE |
| Отображение в timeline | `ui/timeline_widget.py` | HTML: `<s>стандарт</s> <b style="color:red">кастом</b>` + tooltip |
| Сохранение при назначении | `ui/crm_dialogs.py` | ExecutorSelectionDialog: `working_days_between()` → `update_timeline_entry()` |
| Утилита `working_days_between()` | `utils/calendar_helpers.py` | Подсчёт рабочих дней между датами (обратная к add_working_days) |

### Фаза 8.3: Пропуск промежуточных дат (коммит 8c17368)

**Статус:** ЗАВЕРШЕНО

| Задача | Файл | Описание |
|--------|------|----------|
| Серверная логика пропуска | `server/routers/crm_router.py` | В `workflow_client_send`: незаполненные подэтапы до "Клиент" → status='skipped' |
| Отображение пропущенных | `ui/timeline_widget.py` | Серый фон #F5F5F5, текст "Пропущен" |

### Фаза 8.4: Динамические кнопки (коммит 8c17368)

**Статус:** ЗАВЕРШЕНО

| Задача | Файл | Описание |
|--------|------|----------|
| Кнопка "Клиент согласовал" | `ui/crm_tab.py` | Появляется когда `workflow_state.status == 'client_approval'` для текущей стадии |
| Получение workflow state | `ui/crm_tab.py` | `data.get_workflow_state(card_id)` — список состояний по стадиям |

### Фаза 8.5: Валидация и улучшения (коммит 8c17368)

**Статус:** ЗАВЕРШЕНО

| Задача | Файл | Описание |
|--------|------|----------|
| Валидация sum(norm_days) | `ui/norm_days_settings_widget.py` | Уже реализована: блокирует сохранение при расхождении, real-time индикатор |
| Серверное распределение | `server/services/timeline_service.py` | Гарантирует sum(in_scope) == contract_term корректировкой последней записи |
| Односторонняя синхронизация | `ui/timeline_widget.py` | `_sync_norm_days_from_template()`: admin → карточка, пропускает custom_norm_days |
| Гибкий маппинг stage_group | `server/routers/crm_router.py` | `_resolve_stage_group()`: regex `стадия\s*(\d+)` + альтернативные паттерны |

---

## 3. Архитектурные решения

### 3.1 Иерархия дедлайнов

```
Дедлайн проекта (crm_cards.deadline)
  = START + contract_term (рабочие дни)
  = авто-расчёт, ручное изменение через диалог с причиной

  └── Дедлайн исполнителя (stage_executors.deadline)
        = prev_actual_date + norm_days (рабочие дни)
        = авто-расчёт при назначении, изменение через диалог с причиной

        └── Плановые даты подэтапов (project_timeline_entries._planned_date)
              = prev_date + norm_days (цепочка)
              = авто-расчёт, только в tooltip
```

### 3.2 Потоки данных

```
Администрирование (NormDaysTemplate)
  ↓ (односторонняя синхронизация при загрузке карточки)
Карточка CRM → Таблица сроков (norm_days)
  ↓ (при назначении исполнителя)
ExecutorSelectionDialog → дедлайн = prev_date + norm_days
  ↓ (если СДП изменил дату)
custom_norm_days → отображение: зачёркнуто + красным
  ↓ (workflow действия: сдать/принять/отклонить/клиент)
actual_date → зелёный фон в таблице
  ↓ (каскадный пересчёт)
все последующие planned_dates → tooltip обновлены
```

### 3.3 Правила синхронизации norm_days

1. **Направление:** Администрирование → Карточка (НИКОГДА наоборот)
2. **Триггер:** При каждой загрузке карточки (lazy sync)
3. **Поведение:** Обновляет ВСЕ записи norm_days из шаблона (не только нулевые)
4. **Исключение:** Записи с `custom_norm_days` пропускаются (переопределены СДП/ГАП)
5. **Приоритет шаблонов:** Конкретный агент > "Все агенты" > Формулы

### 3.4 Маппинг stage_group

```python
def _resolve_stage_group(column_name: str) -> str:
    # Универсальный: regex 'стадия N' → STAGEN
    # Альтернативы: 'планировочн' → STAGE1, 'концепция/дизайн' → STAGE2, 'чертёж' → STAGE3
```

---

## 4. Затронутые файлы (полная карта)

### Серверные

| Файл | Что изменено | Фаза |
|------|-------------|------|
| `server/database.py` | Поле `custom_norm_days` в ProjectTimelineEntry | 8.2 |
| `server/schemas.py` | `custom_norm_days` в TimelineEntryBase + TimelineEntryUpdate | 8.2 |
| `server/routers/crm_router.py` | workflow_reject/client_ok → timeline, client_send → skip, `_resolve_stage_group()` regex | 8.1, 8.3, 8.5 |

### Клиентские

| Файл | Что изменено | Фаза |
|------|-------------|------|
| `ui/crm_card_edit_dialog.py` | Дедлайны read-only QLabel, `change_executor_deadline()`, `_on_timeline_deadline_updated()` | 8.0 |
| `ui/timeline_widget.py` | custom_norm_days display, skipped display, `deadline_updated` signal, sync всех norm_days | 8.0, 8.2, 8.3, 8.5 |
| `ui/crm_tab.py` | Кнопка "Клиент согласовал" по workflow state | 8.4 |
| `ui/crm_dialogs.py` | `_current_stage_code`, сохранение custom_norm_days при назначении | 8.2 |
| `utils/calendar_helpers.py` | `working_days_between()` | 8.2 |
| `database/migrations.py` | `add_custom_norm_days_column()` — ALTER TABLE SQLite | 8.2 |

---

## 5. Метрики готовности

| Метрика | До Фазы 8 | После Фазы 8 |
|---------|-----------|-------------|
| Дедлайны auto-рассчитываются | 0% | **100%** |
| Workflow → timeline sync | 40% | **100%** |
| Ячейки дат read-only | 100% (timeline) | **100%** (timeline + executor) |
| Превышение norm_days отображается | 0% | **100%** |
| Пропуск промежуточных дат | 0% | **100%** |
| Динамические кнопки подэтапов | 30% | **80%** (кнопка "Клиент согласовал") |
| Тестовое покрытие deadline | 60% | **75%** |

### Что ещё можно улучшить (будущие итерации)

| Область | Описание | Приоритет |
|---------|----------|-----------|
| Полная динамика кнопок | Все кнопки меняются по текущему подэтапу из timeline (не только "Клиент согласовал") | Средний |
| Тесты для Фазы 8 | Unit-тесты для custom_norm_days, skip logic, workflow_reject timeline | Средний |
| WebSocket уведомления | Уведомлять других клиентов об изменении timeline в реальном времени | Низкий |
| Государственные праздники | Учёт праздников в add_working_days / working_days_between | Низкий |

---

## 6. Коммиты

| Коммит | Дата | Описание |
|--------|------|----------|
| `651e431` | 2026-02-21 | Фаза 8.0: executor deadlines read-only + deadline roadmap docs |
| `8c17368` | 2026-02-22 | Фазы 8.1-8.5: workflow dates, custom_norm_days, skip logic, dynamic buttons |
| `0589972` | 2026-02-22 | Docs: mark Phase 8.0-8.5 as completed |
