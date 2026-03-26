# Fix: Reports & Charts — Roadmap

**Ветка:** feat/admin-agents-cities-qa-audit
**Файлы:** `ui/reports_tab.py`, `ui/chart_widget.py`
**Режим:** fix (lite) — 4 задачи, без серверных изменений

---

## Задача 1: Вернуть KPI надзора (Экономия, Дефекты, Визиты)

### Проблема
В коммите `ef98670` (fix: 5 исправлений ReportsTab) были удалены 3 KPI-карточки из секции "Авторский надзор":
- **Экономия бюджета** (`savings`, цвет `#4CAF50`)
- **Дефекты** (`defects`, цвет `#FF9800`)
- **Визиты на объект** (`visits`, цвет `#2196F3`)

В старой версии (`bc2790b`) они были внутри grid layout на позиции `(2, 1)` — рядом с ProjectTypePieChart.

### Что нужно сделать

**Файл: `ui/reports_tab.py`**

#### Шаг 1.1: Создать KPI-карточки ПОСЛЕ grid layout (строка ~572)

Текущий код (`_create_supervision_section`, строка 568-573):
```python
        grid.addWidget(self.chart_sv_project_types, 2, 0)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        section.add_layout(grid)
        self.sections_layout.addWidget(section)
```

Вставить ПОСЛЕ `section.add_layout(grid)` и ПЕРЕД `self.sections_layout.addWidget(section)`:
```python
        # Мини-KPI надзора: экономия, дефекты, визиты — горизонтально под графиками
        self._mini_sv_kpi = {}
        sv_kpi_layout = QHBoxLayout()
        sv_kpi_layout.setSpacing(8)
        for key, title, color in [
            ("savings", "Экономия бюджета", "#4CAF50"),
            ("defects", "Дефекты", "#FF9800"),
            ("visits", "Визиты на объект", "#2196F3"),
        ]:
            card = MiniKPICard(title=title, border_color=color)
            card.set_value("—")
            self._mini_sv_kpi[key] = card
            sv_kpi_layout.addWidget(card)
        sv_kpi_layout.addStretch()
        sv_kpi_w = QWidget()
        sv_kpi_w.setLayout(sv_kpi_layout)
        section.add_widget(sv_kpi_w)
```

#### Шаг 1.2: Восстановить обновление значений (строка ~1172)

Текущий код (строка 1172):
```python
        # Мини-KPI: экономия, дефекты, визиты — убраны из UI по запросу
```

Заменить на (восстановить из `bc2790b`, строка 1102-1114):
```python
        # Мини-KPI: экономия, дефекты, визиты
        budget = sv.get("budget", {}) or {}
        savings = budget.get("total_savings", 0) or 0
        savings_pct = budget.get("savings_pct", 0) or 0
        self._mini_sv_kpi["savings"].set_value(
            f"{savings:,.0f}\u00a0руб ({savings_pct:.0f}%)".replace(",", "\u00a0")
        )

        defects = sv.get("defects", {}) or {}
        self._mini_sv_kpi["defects"].set_value(
            f"{defects.get('found', 0) or 0}\u00a0/\u00a0{defects.get('resolved', 0) or 0}"
        )

        self._mini_sv_kpi["visits"].set_value(str(sv.get("site_visits", 0) or 0))
```

**Внимание:** переменная `budget` уже используется выше (строка 1131) для `chart_sv_budget`. Убедиться, что `budget` определён до этого блока. Текущий код: `budget = sv.get("budget", {}) or {}` на строке 1131 — KPI-код можно поставить ПОСЛЕ строки 1170 (после chart_sv_project_types.set_data), и `budget` уже будет определён. Не дублировать определение `budget`.

#### Шаг 1.3: Добавить KPI в PDF экспорт (строка ~1777)

Текущий код PDF надзора (строки 1774-1778):
```python
                sv_header_block = [
                    self._pdf_section_header('Авторский надзор', font_bold),
                    Spacer(1, 2 * mm),
                    self._pdf_kpi_row(kpi_list, font_name, PAGE_W_MM),
                ]
```

Добавить ПОСЛЕ `self._pdf_kpi_row(kpi_list, ...)`:
```python
                # Дополнительные KPI: экономия, дефекты, визиты
                sv_extra_kpi = []
                for key, label, color in [
                    ("savings", "Экономия бюджета", "#4CAF50"),
                    ("defects", "Дефекты", "#FF9800"),
                    ("visits", "Визиты на объект", "#2196F3"),
                ]:
                    card = self._mini_sv_kpi.get(key)
                    val = card.value_label.text() if card and hasattr(card, 'value_label') else "—"
                    sv_extra_kpi.append((label, val, color))
                sv_header_block.append(Spacer(1, 2 * mm))
                sv_header_block.append(
                    self._pdf_kpi_row(sv_extra_kpi, font_name, PAGE_W_MM)
                )
```

### Риски
- Переменная `budget` — убедиться, что не дублируется определение
- `_mini_sv_kpi` используется и в PDF, и в `_update_supervision` — инициализация должна быть в `_create_supervision_section`, до любого вызова обновления

---

## Задача 2: Выравнивание осей CRM (FunnelBarChart)

### Проблема
`FunnelBarChart.set_data()` (chart_widget.py:169) использует:
```python
self.figure.subplots_adjust(left=0.22, right=0.97, top=0.88, bottom=0.12)
```
Это **не вызывает `_finalize()`** — обходит систему выравнивания через `_AXIS_LEFT` / `_AXIS_RIGHT`.

В секции CRM оба графика (Funnel + "Время стадий") на полную ширину (не парные), так что их оси НЕ ДОЛЖНЫ совпадать друг с другом. Но `left=0.22` — это слишком много, из-за чего длинные подписи воронки "съедают" место для данных.

### Что нужно сделать

**Файл: `ui/chart_widget.py`**

#### Шаг 2.1: Заменить hardcoded subplots_adjust на _finalize() (строка 169)

Текущий код:
```python
        self.figure.subplots_adjust(left=0.22, right=0.97, top=0.88, bottom=0.12)
        if self.canvas:
            self.canvas.draw()
```

Заменить на:
```python
        self.figure.subplots_adjust(top=0.88, bottom=0.12)
        self._finalize()
```

**Почему:** `_finalize()` сначала вызывает `tight_layout()` (автоподбор), затем фиксирует `left` и `right` из `_AXIS_LEFT` и `_AXIS_RIGHT`. Но для FunnelBarChart нужен собственный `_AXIS_LEFT`, потому что у него горизонтальные подписи слева (длинные названия колонок Kanban).

#### Шаг 2.2: Задать FunnelBarChart._AXIS_LEFT (класс, строка ~115)

Добавить class-level override:
```python
class FunnelBarChart(ChartBase):
    _AXIS_LEFT = 0.18   # было 0.22, уменьшено — tight_layout подберёт оптимально
```

**Значение 0.18:** компромисс — tight_layout даст первичный расчёт, а потом `_finalize()` зафиксирует left=0.18. Если подписи ещё обрезаются — можно поднять до 0.20.

### Риски
- Если подписи очень длинные (>25 символов), `truncate=25` в FunnelBarChart может не хватить — проверить визуально
- `top=0.88, bottom=0.12` — оставить как есть, они корректные для этого типа графика

---

## Задача 3: HorizontalBarWidget — обрезка подписей

### Проблема
1. `_AXIS_RIGHT = 0.96` (из ChartBase) — значения на барах (текст справа от бара) обрезаются
2. `truncate=12` — слишком короткий для названий городов/агентов, из-за чего "Санкт-Пет..." нечитаемо

### Что нужно сделать

**Файл: `ui/chart_widget.py`**

#### Шаг 3.1: Переопределить _AXIS_RIGHT в HorizontalBarWidget (строка ~494)

Добавить:
```python
class HorizontalBarWidget(ChartBase):
    _AXIS_RIGHT = 0.92   # оставить место для значений справа от баров
```

#### Шаг 3.2: Увеличить truncate до 18 символов (строка 531)

Текущий код:
```python
sorted_labels = [self._truncate(p[1], 12) for p in paired]
```

Заменить на:
```python
sorted_labels = [self._truncate(p[1], 18) for p in paired]
```

### Риски
- Если `_AXIS_LEFT=0.15` + `_AXIS_RIGHT=0.92` — полезная область уменьшается. Для парных графиков (половина ширины) подписи по 18 символов могут залезать в бар-область. Проверить на реальных данных.
- Альтернатива: `truncate=15` как компромисс.

---

## Задача 4: PDF экспорт — оптимизация компоновки

### Проблема
- `Spacer(1, 6 * mm)` между секциями — слишком много, занимает место
- `KeepTogether` для больших KPI-блоков может вызывать перенос на новую страницу
- `HALF_H = int(col_w * 0.55)` — графики высоковаты для landscape A4, мало контента на странице

### Что нужно сделать

**Файл: `ui/reports_tab.py`**

#### Шаг 4.1: Уменьшить HALF_H (строка 1306)

Текущий код:
```python
HALF_H = int(col_w * 0.55)  # ~73мм для landscape
```

Заменить на:
```python
HALF_H = int(col_w * 0.45)  # ~60мм — компактнее, больше контента на странице
```

#### Шаг 4.2: Уменьшить межсекционные Spacer с 6mm до 4mm

Заменить ВСЕ `Spacer(1, 6 * mm)` в `export_to_pdf()` на `Spacer(1, 4 * mm)`.

Строки: 1668, 1697, 1728, 1758.

#### Шаг 4.3: Оценить KeepTogether для KPI-блока (строка 1667)

Текущий код:
```python
elements.append(KeepTogether(kpi_block))
```

`kpi_block` содержит до 4 рядов KPI (основные + по агентам x3). При 3+ агентах это может быть слишком большой блок для KeepTogether — ReportLab перенесёт его целиком на новую страницу, оставляя пустое место.

**Решение:** разбить на 2 KeepTogether:
```python
# Основные KPI — всегда вместе
elements.append(KeepTogether(kpi_block[:4]))  # header + 2 ряда + spacer
# KPI по агентам — отдельный блок (может перенестись)
if len(kpi_block) > 4:
    elements.append(KeepTogether(kpi_block[4:]))
```

**Внимание:** индексы зависят от количества элементов. Лучше собрать `kpi_base` и `kpi_agents` в отдельные списки:
```python
kpi_base = [
    self._pdf_section_header(...),
    Spacer(1, 2 * mm),
    self._pdf_kpi_row([...], ...),   # клиенты/договоры
    Spacer(1, 2 * mm),
    self._pdf_kpi_row([...], ...),   # суммы/площади
]
elements.append(KeepTogether(kpi_base))

kpi_agents = []
if by_agent:
    # ... формирование agent KPI rows ...
    pass
if kpi_agents:
    elements.append(KeepTogether(kpi_agents))
```

### Риски
- `HALF_H = col_w * 0.45` — графики могут стать нечитаемыми, если в них много данных. Проверить на реальном PDF.
- Разбиение KeepTogether может привести к разрыву между заголовком секции и KPI.

---

## Порядок применения

| # | Задача | Файл | Сложность |
|---|--------|------|-----------|
| 1 | KPI надзора — создание виджетов | `reports_tab.py:572` | Простая |
| 2 | KPI надзора — обновление значений | `reports_tab.py:1172` | Простая |
| 3 | KPI надзора — PDF экспорт | `reports_tab.py:1777` | Простая |
| 4 | FunnelBarChart — _AXIS_LEFT + _finalize | `chart_widget.py:115,169` | Средняя |
| 5 | HorizontalBarWidget — _AXIS_RIGHT + truncate | `chart_widget.py:494,531` | Простая |
| 6 | PDF — HALF_H | `reports_tab.py:1306` | Простая |
| 7 | PDF — Spacer 6→4mm | `reports_tab.py:1668,1697,1728,1758` | Простая |
| 8 | PDF — разбиение KeepTogether | `reports_tab.py:1598-1667` | Средняя |

## Проверка

1. Запустить `main.py`, перейти на вкладку "Отчёты и Статистика"
2. Проверить секцию "Авторский надзор" — 3 KPI должны быть горизонтально ПОД графиками
3. Проверить CRM: воронка — подписи не обрезаны, ось не слишком сдвинута
4. Проверить HorizontalBarWidget: "Надзоры по городам" / "по агентам" — значения видны, подписи читаемы
5. Экспортировать PDF — проверить компактность и читаемость
