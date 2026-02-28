# Research: PDF-экспорт — текущее состояние

> Агент: Research Agent
> Дата: 2026-02-28
> Slug: pdf-export-update

---

## Обзор

В проекте Interior Studio CRM существует **6 точек PDF-экспорта** в 5 файлах (исключая `ui/reports_tab.py` — эталон).
Используются **3 механизма** генерации PDF.

---

## Карта файлов с PDF-экспортом

| # | Файл | Строк | Метод | Механизм |
|---|------|-------|-------|----------|
| 1 | `ui/crm_dialogs.py` | 4876 | `CRMStatisticsDialog.export_to_pdf()` (стр. 1814) + `perform_pdf_export_with_params()` (стр. 2058) | QPrinter + QTextDocument |
| 2 | `ui/supervision_dialogs.py` | 2430 | `SupervisionStatisticsDialog.export_to_pdf()` (стр. 580) + `perform_pdf_export()` (стр. 656) | QPrinter + QTextDocument |
| 3 | `ui/timeline_widget.py` | 1023 | `TimelineWidget._export_pdf()` (стр. 1008) | API (серверный ReportLab) |
| 4 | `ui/supervision_timeline_widget.py` | 1058 | `SupervisionTimelineWidget._export_pdf()` (стр. 1043) | API (серверный ReportLab) |
| 5 | `ui/employee_reports_tab.py` | 469 | `EmployeeReportsTab.export_report()` (стр. 396) | PDFGenerator (ReportLab Platypus) |

**Эталон:** `ui/reports_tab.py` (1905 строк) — `ReportsTab.export_to_pdf()` (стр. 1697), механизм: ReportLab Platypus + widget screenshots.

---

## Детальный анализ каждого экспорта

### 1. CRMStatisticsDialog — `ui/crm_dialogs.py`

#### Кнопка (стр. 1447–1459)
```python
pdf_btn = IconLoader.create_icon_button('export', 'Экспорт в PDF', icon_size=12)
pdf_btn.setStyleSheet("""
    QPushButton {
        background-color: #E74C3C; color: white;
        padding: 4px 12px; border-radius: 4px; font-weight: bold;
    }
    QPushButton:hover { background-color: #C0392B; }
""")
pdf_btn.clicked.connect(self.export_to_pdf)
```

#### Поток вызовов
1. `export_to_pdf()` (стр. 1814) — открывает `ExportPDFDialog` (отдельный класс стр. 2380)
2. `ExportPDFDialog.select_folder()` → выбор папки → `dialog.accept()`
3. При `QDialog.Accepted` → собирает `folder` + `filename` → вызывает `perform_pdf_export_with_params(folder, filename)` (стр. 2058)

**Примечание:** Метод `export_to_pdf()` на стр. 1814 НЕ вызывает `perform_pdf_export_with_params` напрямую. Поток: `export_to_pdf` создаёт `ExportPDFDialog`, проверяет `dialog.exec_() == QDialog.Accepted`, затем сам строит PDF через QPrinter + QTextDocument (стр. 1825–2049). `perform_pdf_export_with_params` — дублирующий метод на стр. 2058, содержит почти идентичный код (используется из внешнего контекста).

#### Реализация `export_to_pdf()` (стр. 1814–2055)
```
Механизм: QPrinter(HighResolution) → QTextDocument → doc.print_(printer)
Ориентация: A4 Portrait (QPrinter.A4)
Поля: setPageMargins(0, 0, 0, 0, QPrinter.Millimeter) — нулевые поля
Шрифт: 'Arial' hardcoded в QTextCharFormat
Импорты: from PyQt5.QtPrintSupport import QPrinter (внутри метода, стр. 1826)
```

**Структура документа:**
- Логотип: `resource_path('resources/logo.png')` через `QPixmap.scaledToHeight(80)` + `QTextImageFormat`; fallback — текст 'FC' оранжевым шрифтом Arial 36
- Заголовок: "FESTIVAL COLOR" + "Система управления проектами"
- Разделители: `'─' * 60` / `'─' * 80` символами (Unicode)
- Краткая сводка: подсчёт из `stats_table` по col=5 (статус: 'Завершено'/'Просрочено'/другое)
- Таблица: `QTextTableFormat` — 100% ширина, 1px border `#CCCCCC`, заголовок `#808080` на белом, чередование строк `#FFFFFF`/`#F5F5F5`
- Цветная подсветка статуса (col=5): 'Просрочено' → `#E74C3C`, 'Завершено' → `#27AE60`
- Подвал: текст "Документ сформирован автоматически системой Festival Color" + дата

**После генерации:** `PDFExportSuccessDialog` (стр. 2563) — custom frameless QDialog с CustomTitleBar, кнопкой "Открыть папку" (вызывает `os.startfile(folder)`)

**Автооткрытие файла:** ОТСУТСТВУЕТ — только открытие папки через кнопку в SuccessDialog.

#### `perform_pdf_export_with_params()` (стр. 2058–2352)
Дублирует логику `export_to_pdf()` почти полностью. Отличия:
- Принимает `folder, filename` параметрами (не через `ExportPDFDialog`)
- После `doc.print_()` создаёт inline `QDialog` (стр. 2281–2344) — стандартный не-frameless диалог
- Затем повторно вызывает `PDFExportSuccessDialog` (стр. 2345) — дублирование диалога успеха
- Ошибка обработки: `print(f" Ошибка экспорта PDF: {e}")` (с пробелом в начале) + traceback + `CustomMessageBox`

---

### 2. SupervisionStatisticsDialog — `ui/supervision_dialogs.py`

#### Кнопка (стр. 431–443)
```python
pdf_btn = IconLoader.create_icon_button('export', 'Экспорт в PDF', icon_size=12)
pdf_btn.setStyleSheet("""
    QPushButton {
        background-color: #E74C3C; color: white;
        padding: 8px 16px; border-radius: 4px; font-weight: bold;
    }
    QPushButton:hover { background-color: #C0392B; }
""")
pdf_btn.clicked.connect(self.export_to_pdf)
```
*Отличие от CRMStatisticsDialog: padding 8px 16px вместо 4px 12px.*

#### Поток вызовов
1. `export_to_pdf()` (стр. 580) — создаёт inline `QDialog` (не выделенный класс)
2. Кнопка "Выбрать папку и экспортировать" → `perform_pdf_export(dialog)` (стр. 656)
3. `QFileDialog.getExistingDirectory()` → генерация PDF

**Отличие от CRMStatisticsDialog:** `export_to_pdf` создаёт простой inline QDialog без frameless/CustomTitleBar, а не `ExportPDFDialog`.

#### Реализация `perform_pdf_export()` (стр. 656–897)
```
Механизм: QPrinter(HighResolution) → QTextDocument → doc.print_(printer)
Ориентация: A4 Portrait
Поля: setPageMargins(0, 0, 0, 0, QPrinter.Millimeter)
Импорты: внутри метода (стр. 660–663)
```

**Структура документа (идентична CRMStatisticsDialog за исключением):**
- Заголовок: "Статистика CRM Авторского надзора"
- Краткая сводка: col=6, статусы 'Приостановлено'/'Работа сдана'/другое
- Цветная подсветка (col=6): 'Приостановлено' → `#F39C12`, 'Работа сдана' → `#27AE60`

**После генерации:** inline `success_dialog = QDialog(self)` (стр. 901–965) — НЕ выделенный класс, НЕ frameless, содержит кнопки "Открыть папку" и "OK". Не использует `PDFExportSuccessDialog`.

**Ошибка:** `print(f" Ошибка экспорта PDF: {e}")` + traceback + `QMessageBox.critical` (не `CustomMessageBox`).

---

### 3. TimelineWidget — `ui/timeline_widget.py`

#### Кнопка (стр. 272–281)
```python
self.btn_pdf = QPushButton('Экспорт в PDF')
self.btn_pdf.setFixedHeight(32)
self.btn_pdf.setStyleSheet("""
    QPushButton {
        background-color: #C62828; color: white; border: none;
        border-radius: 4px; padding: 0 16px; font-size: 12px;
    }
    QPushButton:hover { background-color: #a52222; }
""")
self.btn_pdf.clicked.connect(self._export_pdf)
```
*Цвет кнопки: `#C62828` (другой оттенок красного, не `#E74C3C`).*

#### Реализация `_export_pdf()` (стр. 1008–1023)
```python
def _export_pdf(self):
    """Экспорт в PDF через API"""
    if not self.contract_id:
        return
    try:
        file_bytes = self.data.export_timeline_pdf(self.contract_id)
        if file_bytes:
            path, _ = QFileDialog.getSaveFileName(
                self, 'Сохранить PDF', f'timeline_{self.contract_id}.pdf',
                'PDF (*.pdf)'
            )
            if path:
                with open(path, 'wb') as f:
                    f.write(file_bytes)
    except Exception as e:
        print(f"[TimelineWidget] Ошибка экспорта PDF: {e}")
```

**Механизм:** API-вызов `DataAccess.export_timeline_pdf(contract_id)` → серверная генерация → бинарные байты → `QFileDialog.getSaveFileName()` → запись файла.

**Endpoint:** `GET /api/timeline/{contract_id}/export-pdf`

**Особенности:**
- Нет уведомления об успехе (молчаливое сохранение)
- Нет автооткрытия файла после сохранения
- Ошибка: только `print()`, нет UI-уведомления пользователю
- Нет проверки `file_bytes is None` с UI-сообщением

---

### 4. SupervisionTimelineWidget — `ui/supervision_timeline_widget.py`

#### Кнопка (стр. 535–544)
```python
self.btn_pdf = QPushButton('Экспорт в PDF (без бюджетов)')
self.btn_pdf.setFixedHeight(32)
self.btn_pdf.setStyleSheet("""
    QPushButton {
        background-color: #C62828; color: white; border: none;
        border-radius: 4px; padding: 0 16px; font-size: 12px;
    }
    QPushButton:hover { background-color: #a52222; }
""")
self.btn_pdf.clicked.connect(self._export_pdf)
```

#### Реализация `_export_pdf()` (стр. 1043–1058)
```python
def _export_pdf(self):
    """Экспорт в PDF (без бюджетов)"""
    if not self.card_id:
        return
    try:
        file_bytes = self.data.export_supervision_timeline_pdf(self.card_id)
        if file_bytes:
            path, _ = QFileDialog.getSaveFileName(
                self, 'Сохранить PDF', f'supervision_timeline_{self.card_id}.pdf',
                'PDF (*.pdf)'
            )
            if path:
                with open(path, 'wb') as f:
                    f.write(file_bytes)
    except Exception as e:
        print(f"[SupervisionTimelineWidget] Ошибка экспорта PDF: {e}")
```

**Механизм:** API-вызов `DataAccess.export_supervision_timeline_pdf(card_id)` → серверная генерация → бинарные байты → сохранение файла.

**Endpoint:** `GET /api/supervision-timeline/{card_id}/export-pdf`

**Особенности:** идентичны `TimelineWidget._export_pdf()` — нет уведомления об успехе, нет автооткрытия, ошибка только через `print()`.

---

### 5. EmployeeReportsTab — `ui/employee_reports_tab.py`

#### Кнопки (стр. 258–268)
```python
# Две кнопки — для разных типов отчётов:
export_completed_btn = IconLoader.create_icon_button('export', 'Экспорт: Выполненные заказы', icon_size=12)
export_completed_btn.clicked.connect(lambda: self.export_report(project_type, 'completed'))

export_salary_btn = IconLoader.create_icon_button('export', 'Экспорт: Зарплаты', icon_size=12)
export_salary_btn.clicked.connect(lambda: self.export_report(project_type, 'salary'))
```
*Кнопки без явного setStyleSheet — используют стиль по умолчанию IconLoader.*

#### Реализация `export_report()` (стр. 396–469)
```
Механизм: PDFGenerator (utils/pdf_generator.py) — ReportLab Platypus SimpleDocTemplate
Диалог: QFileDialog.getSaveFileName() — стандартный диалог сохранения файла
```

**Поток:**
1. Определяет вкладку по `project_type` ('Индивидуальный'/'Шаблонный'/'Авторский надзор')
2. Извлекает параметры периода через `findChild()` по именам виджетов
3. `DataAccess.get_employee_report_data(employee_id, ...)` — API-first с fallback
4. `PDFGenerator.generate_report(filename, title, pdf_data, headers)` — ReportLab

**PDFGenerator.generate_report() — `utils/pdf_generator.py` (стр. 74–166):**
```
Страница: A4 Portrait (если заголовков <= 6), иначе landscape(A4)
Поля: 2cm со всех сторон (rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
Шрифт: Arial (если C:/Windows/Fonts/arial.ttf существует), иначе Helvetica
Логотип: ОТСУТСТВУЕТ
Footer: ОТСУТСТВУЕТ
Фильтры в шапке: ОТСУТСТВУЮТ
```

**Структура документа:**
- Заголовок: Paragraph с ParagraphStyle (fontSize=14, alignment=CENTER, цвет `#333333`)
- Дата: `f"Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M')}"` (стандартный Normal стиль)
- Spacer(1, 20)
- Таблица: `reportlab.platypus.Table` + `TableStyle`
  - Заголовок таблицы: bg `#2C3E50`, fg `#FFFFFF`, font Arial/Helvetica 10
  - Тело: чередование `#FFFFFF`/`#F8F9FA`, border `#DEE2E6`, font 9
  - `repeatRows=1` — повтор заголовков на каждой странице
  - Ширина колонок: `doc.width / len(headers)` — равномерно
- Нет сводки / нет цветных статусов

**Уведомления:**
- Успех: `QMessageBox.information` (стандартный, не `CustomMessageBox`)
- Ошибка: `QMessageBox.critical` (стандартный, не `CustomMessageBox`)

**Автооткрытие файла:** ОТСУТСТВУЕТ.

---

## Эталон: ReportsTab — `ui/reports_tab.py`

### Кнопка (стр. ~243–260)
```python
btn_export = QPushButton('Экспорт PDF')
# Желтая кнопка: background: #ffd93c, border: 1px solid #E0E0E0, color: #333
btn_export.clicked.connect(self.export_to_pdf)
```

### Реализация `export_to_pdf()` (стр. 1697–1905)
```
Механизм: ReportLab Platypus — SimpleDocTemplate + widget screenshots (pixel-perfect)
Ориентация: landscape(A4) — 297×210 мм
Поля: leftMargin=10mm, rightMargin=10mm, topMargin=8mm, bottomMargin=12mm
Шрифт: Arial (TrueType регистрация через pdfmetrics), fallback Helvetica
Диалог: QFileDialog.getSaveFileName()
```

**Ключевые методы:**
- `_grab_widget_png(widget, scale=3.0)` — QPixmap(w*3, h*3) + `setDevicePixelRatio(3.0)` + `widget.render()` + PNG BytesIO
- `_chart_to_png(chart_widget, dpi=300)` — `figure.savefig()` напрямую (обход QScrollArea обрезки)
- `_grab_crm_both_tabs(scale)` — покомпонентный захват: mini KPI cards + funnel + stage charts
- `_fit_image(buf, w_px, h_px, max_w_mm, max_h_mm)` — пропорциональное масштабирование в `RLImage`
- `_pdf_section_header(text, font)` — заголовок секции с жёлтой полоской
- `_pdf_hr(page_w_mm)` — горизонтальная разделительная линия

**Структура документа:**
- Footer callback `_page_footer()` на каждой странице: `resources/footer.jpg` (12мм полоса) + номер страницы
- Шапка: логотип (`resources/logo.png`, 18×18мм), заголовок, HR-разделитель
- Фильтры: `style_filter` с `backColor=#F8F9FA` — отображает активные фильтры
- 5 секций (скриншоты): KPI, Клиенты, Договоры, CRM Аналитика, Авторский надзор
- CRM-секция: CondPageBreak(120мм) + покомпонентный захват [18мм + 55мм + 95мм]
- `CondPageBreak` — умный перенос страницы только если не помещается

**Технические решения:**
- `QGraphicsDropShadowEffect` снимается перед `render()` и пересоздаётся после
- `canvas.draw()` для всех `FigureCanvasQTAgg` перед захватом
- `figure.savefig(dpi=300)` для графиков в QScrollArea
- `logger.info/error` (не `print()`) для логирования
- После успеха: `os.startfile(os.path.normpath(filename))` — автооткрытие PDF (Windows) / `subprocess.Popen(['xdg-open', filename])` (Linux/Mac)
- Ошибка: `CustomMessageBox` — кастомный диалог

---

## Сравнительная таблица

| Характеристика | reports_tab (эталон) | crm_dialogs | supervision_dialogs | timeline_widget | supervision_timeline | employee_reports |
|---------------|---------------------|-------------|---------------------|-----------------|---------------------|-----------------|
| **Механизм** | ReportLab Platypus | QPrinter + QTextDocument | QPrinter + QTextDocument | API (серверный) | API (серверный) | ReportLab Platypus (PDFGenerator) |
| **Ориентация** | landscape(A4) | A4 portrait | A4 portrait | сервер | сервер | A4 portrait (landscape если >6 колонок) |
| **Шрифт** | Arial TTF + Helvetica fallback | Arial hardcoded в QFont | Arial hardcoded в QFont | сервер | сервер | Arial TTF + Helvetica fallback |
| **Логотип** | Да (18×18мм RLImage) | Да (QPixmap+QTextImageFormat, 80px) | Да (идентично crm_dialogs) | н/а | н/а | Нет |
| **Footer** | Да (footer.jpg + номер стр.) | Текстовый (символы '─') | Текстовый (символы '─') | н/а | н/а | Нет |
| **Фильтры в шапке** | Да | Нет | Нет | н/а | н/а | Нет |
| **Автооткрытие PDF** | Да (os.startfile) | Нет (только открытие папки) | Нет (только открытие папки) | Нет | Нет | Нет |
| **Диалог выбора файла** | QFileDialog.getSaveFileName | ExportPDFDialog (custom frameless) | inline QDialog + QFileDialog.getExistingDirectory | QFileDialog.getSaveFileName | QFileDialog.getSaveFileName | QFileDialog.getSaveFileName |
| **Диалог успеха** | Нет (автооткрытие) | PDFExportSuccessDialog (custom) | inline QDialog (не frameless) | Нет | Нет | QMessageBox.information |
| **Ошибка** | CustomMessageBox + logger.error | CustomMessageBox + print | QMessageBox.critical + print | print() только | print() только | QMessageBox.critical |
| **Цвет кнопки** | #ffd93c (жёлтый) | #E74C3C (красный) | #E74C3C (красный) | #C62828 (тёмно-красный) | #C62828 (тёмно-красный) | нет стиля (IconLoader default) |
| **Кнопка SVG-иконка** | Нет | IconLoader.create_icon_button | IconLoader.create_icon_button | Нет (QPushButton) | Нет (QPushButton) | IconLoader.create_icon_button |
| **Logging** | logger.info/error | print() | print() | print() | print() | print() + traceback |

---

## Дублирование кода

### Дублирование 1: QPrinter-логотип (crm_dialogs / supervision_dialogs)
Блоки загрузки логотипа идентичны в 3 местах:
- `CRMStatisticsDialog.export_to_pdf()` стр. 1846–1881
- `CRMStatisticsDialog.perform_pdf_export_with_params()` стр. 2077–2112
- `SupervisionStatisticsDialog.perform_pdf_export()` стр. 700–733

Код: `resource_path('resources/logo.png')` → `QPixmap.scaledToHeight(80)` → `doc.addResource()` → `QTextImageFormat`. Fallback: текст 'FC' Arial 36 оранжевый `#FF9800`.

### Дублирование 2: QPrinter-таблица (crm_dialogs / supervision_dialogs)
Шаблон таблицы `QTextTableFormat` идентичен в 3 местах (border=1, `#CCCCCC`, CellPadding=4, заголовок `#808080`).

### Дублирование 3: perform_pdf_export_with_params (crm_dialogs)
`perform_pdf_export_with_params()` (стр. 2058) — полный дубликат `export_to_pdf()` (стр. 1814). Оба метода генерируют идентичный документ. Разница только в источнике `folder/filename`.

### Дублирование 4: Inline success-dialog в perform_pdf_export_with_params (crm_dialogs)
На стр. 2281–2344 создаётся inline `QDialog` с success-сообщением, после которого на стр. 2345 тот же `PDFExportSuccessDialog` вызывается повторно. Фактически показываются 2 диалога успеха подряд (один за другим).

---

## Особые находки

### Проблема: print() вместо logger в 4 из 5 экспортов
`reports_tab.py` использует `logger.info/error`. Остальные модули используют `print()`.

### Проблема: Несовместимость диалогов успеха
- `CRMStatisticsDialog.export_to_pdf()` → `PDFExportSuccessDialog` (frameless custom)
- `CRMStatisticsDialog.perform_pdf_export_with_params()` → inline QDialog + затем PDFExportSuccessDialog (двойной вызов)
- `SupervisionStatisticsDialog.perform_pdf_export()` → inline QDialog (не custom, не frameless)
- Timeline-виджеты → нет диалога вообще
- `EmployeeReportsTab` → стандартный `QMessageBox.information`

### Проблема: QPrinter поля = 0
В `crm_dialogs.py` и `supervision_dialogs.py`: `setPageMargins(0, 0, 0, 0, QPrinter.Millimeter)` — нулевые поля. Текст может вплотную прилегать к краям страницы.

### Проблема: Несовместимость цвета кнопки
- Эталон: `#ffd93c` (жёлтый)
- CRM/Supervision Statistics: `#E74C3C` (красный)
- Timeline-виджеты: `#C62828` (тёмно-красный, другой оттенок)

### Проблема: employee_reports_tab — ошибочный импорт на уровне модуля
Строка 10: `from utils.pdf_generator import PDFGenerator` — импорт на уровне модуля. Если `reportlab` не установлен, модуль завершится с ошибкой при импорте. В `pdf_generator.py` используется `try/except` для `reportlab`, но если `REPORTLAB_AVAILABLE = False`, метод `generate_report()` всё равно вызывает ReportLab-классы и упадёт.

### Проблема: employee_reports_tab — QMessageBox вместо CustomMessageBox
На стр. 464 и 467 используется стандартный `QMessageBox`, хотя в других модулях — `CustomMessageBox`.

### Проблема: PDFGenerator не имеет логотипа, footer, фильтров
`utils/pdf_generator.py` содержит минималистичный генератор без фирменного оформления (нет logo.png, нет footer.jpg, нет фильтров, нет номеров страниц).

---

## Структура вспомогательных классов

### ExportPDFDialog (crm_dialogs.py, стр. 2380–2561)
- Frameless QDialog с CustomTitleBar
- Поля: имя файла (QLineEdit), кнопка "Выбрать папку и экспортировать"
- `select_folder()` → `QFileDialog.getExistingDirectory()` → `self.accept()`
- `get_filename()` / `get_folder()` — геттеры
- Применяется только в `CRMStatisticsDialog`, не в `SupervisionStatisticsDialog`

### PDFExportSuccessDialog (crm_dialogs.py, стр. 2563–2703)
- Frameless QDialog с CustomTitleBar
- Показывает полный путь файла, кнопку "Открыть папку" (`os.startfile(folder)`)
- Применяется только в `CRMStatisticsDialog`

---

## Файловая карта (абсолютные пути)

| Файл | Строк | Назначение |
|------|-------|------------|
| `c:\+CRM+\interior_studio\ui\crm_dialogs.py` | 4876 | CRM статистика, ExportPDFDialog, PDFExportSuccessDialog |
| `c:\+CRM+\interior_studio\ui\supervision_dialogs.py` | 2430 | Надзор статистика |
| `c:\+CRM+\interior_studio\ui\timeline_widget.py` | 1023 | Таймлайн договора (API) |
| `c:\+CRM+\interior_studio\ui\supervision_timeline_widget.py` | 1058 | Таймлайн надзора (API) |
| `c:\+CRM+\interior_studio\ui\employee_reports_tab.py` | 469 | Отчёты сотрудников (PDFGenerator) |
| `c:\+CRM+\interior_studio\ui\reports_tab.py` | 1905 | ЭТАЛОН (ReportLab Platypus + screenshots) |
| `c:\+CRM+\interior_studio\utils\pdf_generator.py` | 324 | Утилита-генератор для employee_reports_tab |

---

🔍 ОТЧЁТ: Research Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Сводка
| Метрика | Значение |
|---------|----------|
| Статус | ✅ Успех |
| Файлов исследовано | 7 |
| Точек экспорта найдено | 6 (в 5 файлах) |
| Механизмов PDF | 3 (QPrinter, API, ReportLab Platypus) |
| Дубликатов кода | 4 |

📁 Исследованные файлы
| Файл | Действие | Строк |
|------|----------|-------|
| `ui/crm_dialogs.py` | ✅ Прочитан (стр. 1814–2380) | 4876 |
| `ui/supervision_dialogs.py` | ✅ Прочитан (стр. 580–997) | 2430 |
| `ui/timeline_widget.py` | ✅ Прочитан (стр. 272–282, 1008–1023) | 1023 |
| `ui/supervision_timeline_widget.py` | ✅ Прочитан (стр. 535–544, 1043–1058) | 1058 |
| `ui/employee_reports_tab.py` | ✅ Прочитан полностью | 469 |
| `ui/reports_tab.py` | ✅ Прочитан (стр. 1697–1905) | 1905 |
| `utils/pdf_generator.py` | ✅ Прочитан полностью | 324 |

🔍 Направления исследования
| # | Направление | Статус | Ключевые находки |
|---|-------------|--------|------------------|
| 1 | Поиск всех точек PDF-экспорта | ✅ | 14 файлов с pdf-паттернами, 5 активных точек (кроме эталона) |
| 2 | Механизмы генерации | ✅ | 3 механизма: QPrinter, API, ReportLab Platypus |
| 3 | Дублирование кода | ✅ | 4 дубликата, крупнейший — perform_pdf_export_with_params |
| 4 | Расхождения с эталоном | ✅ | logger vs print, автооткрытие, footer, логотип, диалоги |
| 5 | Вспомогательные классы | ✅ | ExportPDFDialog, PDFExportSuccessDialog, PDFGenerator |

📎 Артефакт: docs/plan/pdf-export-update/research.md

🔍 Итог: Исследованы все 5 точек PDF-экспорта, задокументированы механизмы, дублирование и расхождения с эталоном.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
