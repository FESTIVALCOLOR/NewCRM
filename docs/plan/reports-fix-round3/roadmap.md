# Reports Fix Round 3 — План конкретных правок

## Проблема 1: KPI надзора — размещение в grid(2,1)

**Файл:** `ui/reports_tab.py`
**Суть:** 3 KPI-блока (Экономия, Дефекты, Визиты) сейчас горизонтально (QHBoxLayout) ПОД grid-ом через `section.add_widget()`. Нужно: вертикальная стопка (QVBoxLayout) ВНУТРИ grid в ячейке (2, 1), рядом с Pie chart "Типы проектов" в (2, 0).

### Правка 1.1 — Сменить layout и поместить в grid

**Строки 574–590** (`_create_supervision_section`):

**Было (строки 574–590):**
```python
        # Мини-KPI: экономия, дефекты, визиты — горизонтальный ряд ПОД графиками
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

        sv_kpi_widget = QWidget()
        sv_kpi_widget.setLayout(sv_kpi_layout)
        section.add_widget(sv_kpi_widget)
```

**Стало:**
```python
        # Мини-KPI: экономия, дефекты, визиты — ВЕРТИКАЛЬНО в grid(2,1) рядом с Pie
        self._mini_sv_kpi = {}
        sv_kpi_layout = QVBoxLayout()
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

        sv_kpi_widget = QWidget()
        sv_kpi_widget.setLayout(sv_kpi_layout)
        grid.addWidget(sv_kpi_widget, 2, 1)
```

**Изменения:**
1. `QHBoxLayout` -> `QVBoxLayout` (стопка вместо ряда)
2. Добавить `sv_kpi_layout.addStretch()` чтобы прижать карточки к верху ячейки
3. `section.add_widget(sv_kpi_widget)` -> `grid.addWidget(sv_kpi_widget, 2, 1)` (поместить в grid)
4. **Убрать строку** `section.add_widget(sv_kpi_widget)` — блок не должен добавляться отдельно в секцию

**Порядок кода:** Блок KPI нужно переместить ПЕРЕД `section.add_layout(grid)` (строка 572), потому что grid добавляется в section, а KPI-виджет нужно добавить в grid до этого. Альтернативно — поставить его сразу после создания `chart_sv_project_types` и перед `section.add_layout(grid)`.

**Конкретно:**
- Переместить блок определения `self._mini_sv_kpi` (строки 574-590) перед строку 572 (`section.add_layout(grid)`)
- Заменить последнюю строку `section.add_widget(sv_kpi_widget)` на `grid.addWidget(sv_kpi_widget, 2, 1)`


---

## Проблема 2: HorizontalBarWidget — подсказки обрезаются

**Файл:** `ui/chart_widget.py`
**Суть:** Текст значений справа от баров (`ax.text(bar.get_width() + max_val * 0.02, ...)`) рисуется за пределами xlim. Нужно расширить xlim.

### Правка 2.1 — Расширить xlim в HorizontalBarWidget.set_data()

**Строка 563** (перед `self._finalize()`):

**Было (строки 550–563):**
```python
                    va='center', fontsize=8, fontweight='bold', color='#333')

        ax.tick_params(axis='y', labelsize=7, pad=2)
        ax.tick_params(axis='x', labelsize=7)
        ...
        self._finalize()
```

**Стало — добавить строку ПОСЛЕ цикла подписей, ПЕРЕД `ax.tick_params` (после строки 549):**
```python
        # Расширить xlim чтобы подписи значений не обрезались
        ax.set_xlim(right=max_val * 1.15)
```

**Вставить после строки 549** (после закрытия `for bar, val in zip(...):`), перед строкой 551 (`ax.tick_params`).

### Правка 2.2 — Расширить xlim в FunnelBarChart.set_data()

**Файл:** `ui/chart_widget.py`
**Аналогичная проблема в FunnelBarChart** — строка 159.

**Вставить после строки 159** (после закрытия цикла `for bar, val in zip(bars, values):`), перед строкой 161 (`ax.set_title`):
```python
        # Расширить xlim чтобы подписи значений не обрезались
        ax.set_xlim(right=max_val * 1.15)
```

### Правка 2.3 — Расширить xlim в ExecutorLoadChart.set_data()

**Файл:** `ui/chart_widget.py`
**Аналогичная проблема** — строка 207.

**Вставить после строки 207** (после закрытия цикла), перед строкой 209 (`ax.set_title`):
```python
        # Расширить xlim чтобы подписи значений не обрезались
        ax.set_xlim(right=max_val * 1.15)
```


---

## Проблема 3: PDF экспорт — системный подход

**Файл:** `ui/reports_tab.py`

### Правка 3.1 — Ограничить max_height для широких графиков

**Метод:** `_pdf_chart_flowables()`, строка 1363–1367

**Было (строки 1363–1367):**
```python
                # Широкие: авто-высота
                img = self._chart_to_rl_image(chart, width_mm=page_w_mm - 4)
                if img:
                    elements.append(img)
                    elements.append(Spacer(1, 3 * mm))
```

**Стало:**
```python
                # Широкие: авто-высота, но ограничена max 90мм
                img = self._chart_to_rl_image(chart, width_mm=page_w_mm - 4, max_height_mm=90)
                if img:
                    elements.append(img)
                    elements.append(Spacer(1, 3 * mm))
```

### Правка 3.2 — Фиксированная высота для Pie в парном режиме

**Метод:** `_pdf_chart_flowables()`, строки 1369–1371

**Было (строки 1369–1371):**
```python
                # Парные: стандартная высота для обычных, авто для динамических
                h = None if _is_dynamic(chart) else HALF_H
                img = self._chart_to_rl_image(chart, width_mm=col_w - 2, height_mm=h)
```

**Стало:**
```python
                # Парные: стандартная высота для обычных, авто для динамических
                # Pie charts — фиксированная высота как у обычных парных
                if isinstance(chart, ProjectTypePieChart):
                    h = HALF_H
                elif _is_dynamic(chart):
                    h = None
                else:
                    h = HALF_H
                img = self._chart_to_rl_image(chart, width_mm=col_w - 2, height_mm=h)
```

**Замечание:** Нужен import `ProjectTypePieChart` — он уже импортирован в строке 23.

### Правка 3.3 — Добавить параметр max_height_mm в _chart_to_rl_image

**Метод:** `_chart_to_rl_image()`, строка 1239

**Было (строка 1239):**
```python
    def _chart_to_rl_image(self, chart, width_mm, height_mm=None, dpi=150):
```

**Стало:**
```python
    def _chart_to_rl_image(self, chart, width_mm, height_mm=None, dpi=150, max_height_mm=None):
```

**Также: добавить ограничение высоты** в теле метода, после вычисления `target_h` (после строки 1274):

**Было (строки 1270–1274):**
```python
            target_w = width_mm / 25.4
            if height_mm:
                target_h = height_mm / 25.4
            else:
                aspect = orig_size[1] / orig_size[0] if orig_size[0] > 0 else 0.6
                target_h = target_w * aspect
```

**Стало:**
```python
            target_w = width_mm / 25.4
            if height_mm:
                target_h = height_mm / 25.4
            else:
                aspect = orig_size[1] / orig_size[0] if orig_size[0] > 0 else 0.6
                target_h = target_w * aspect

            # Ограничить максимальную высоту (для широких графиков типа Воронки)
            if max_height_mm and target_h > max_height_mm / 25.4:
                target_h = max_height_mm / 25.4
```

И аналогичное ограничение для итоговой `h` (строка 1288):

**Было (строка 1288):**
```python
            h = (height_mm if height_mm else width_mm * (target_h / target_w)) * mm
```

**Стало:**
```python
            actual_h_mm = height_mm if height_mm else width_mm * (target_h / target_w)
            if max_height_mm and actual_h_mm > max_height_mm:
                actual_h_mm = max_height_mm
            h = actual_h_mm * mm
```

### Правка 3.4 — Уменьшить пустое пространство между секциями

**Метод:** `export_to_pdf()` — уменьшить Spacer-ы между секциями

**Строки 1701, 1730, 1761, 1791:**

Заменить все `Spacer(1, 4 * mm)` между секциями на `Spacer(1, 2 * mm)`:
- Строка 1701: `elements.append(Spacer(1, 4 * mm))` -> `elements.append(Spacer(1, 2 * mm))`
- Строка 1730: `elements.append(Spacer(1, 4 * mm))` -> `elements.append(Spacer(1, 2 * mm))`
- Строка 1761: `elements.append(Spacer(1, 4 * mm))` -> `elements.append(Spacer(1, 2 * mm))`
- Строка 1791: `elements.append(Spacer(1, 4 * mm))` -> `elements.append(Spacer(1, 2 * mm))`

Также уменьшить межграфиковые Spacer-ы в `_pdf_chart_flowables()`:
- Строки 1360, 1367, 1380, 1387: `Spacer(1, 3 * mm)` -> `Spacer(1, 2 * mm)`

### Правка 3.5 — CondPageBreak перед секцией если мало места

**Метод:** `export_to_pdf()` — использовать `CondPageBreak` перед каждой секцией

**Добавить import** в строке 1501:

**Было:**
```python
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, KeepTogether,
                Image as RLImage
            )
```

**Стало:**
```python
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, KeepTogether,
                Image as RLImage, CondPageBreak
            )
```

**Вставить `CondPageBreak(60 * mm)` перед каждым заголовком секции** (перед KeepTogether):

- Перед строкой 1646 (KPI): не нужен — первая секция
- Перед строкой 1722 (Клиенты):
  ```python
  elements.append(CondPageBreak(60 * mm))
  ```
- Перед строкой 1751 (Договоры):
  ```python
  elements.append(CondPageBreak(60 * mm))
  ```
- Перед строкой 1785 (CRM) — в цикле, перед `elements.append(KeepTogether(crm_header_block))`:
  ```python
  elements.append(CondPageBreak(60 * mm))
  ```
- Перед строкой 1813 (Авторский надзор):
  ```python
  elements.append(CondPageBreak(60 * mm))
  ```

**Смысл:** `CondPageBreak(60mm)` означает: "если до конца страницы осталось менее 60мм — начать новую страницу". Это предотвращает ситуацию когда заголовок секции начинается внизу страницы, а графики переносятся на следующую.


---

## Сводка правок

| # | Файл | Метод | Суть |
|---|------|-------|------|
| 1.1 | reports_tab.py | `_create_supervision_section` | QHBoxLayout->QVBoxLayout, grid(2,1) вместо section.add_widget |
| 2.1 | chart_widget.py | `HorizontalBarWidget.set_data` | `ax.set_xlim(right=max_val*1.15)` |
| 2.2 | chart_widget.py | `FunnelBarChart.set_data` | `ax.set_xlim(right=max_val*1.15)` |
| 2.3 | chart_widget.py | `ExecutorLoadChart.set_data` | `ax.set_xlim(right=max_val*1.15)` |
| 3.1 | reports_tab.py | `_pdf_chart_flowables` | max_height_mm=90 для широких |
| 3.2 | reports_tab.py | `_pdf_chart_flowables` | Pie -> HALF_H фиксированная высота |
| 3.3 | reports_tab.py | `_chart_to_rl_image` | Параметр max_height_mm + ограничение |
| 3.4 | reports_tab.py | `export_to_pdf` + `_pdf_chart_flowables` | Spacer 4mm->2mm, 3mm->2mm |
| 3.5 | reports_tab.py | `export_to_pdf` | CondPageBreak(60mm) перед секциями |

**Всего: 9 точечных правок в 2 файлах.**
