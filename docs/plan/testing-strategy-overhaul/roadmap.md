# Дорожная карта: Перестройка стратегии тестирования

**Дата:** 2026-03-06
**Режим:** plan (реализация по запросу)
**Слои:** 6 (fuzz, smoke, ui_real, property, visual, integration)
**Артефакты:** [research.md](research.md) | [design.md](design.md)

---

## Оглавление

### Фаза 1: Research
- ✅ Анализ текущего состояния тестов (8997 тестов, 73% моки)
- ✅ Поиск инструментов (GitHub, WebSearch, Context7)
- ✅ Оценка pywinauto (отвергнут для управления, принят для accessibility < 10 мин)
- ✅ Оценка Schemathesis, Hypothesis, QWidget.grab()

### Фаза 2: Design
- ✅ C4 Model (Context → Container → Component)
- ✅ DFD — потоки данных для 5 слоёв
- ✅ 5 ADR (Schemathesis, pytest-qt, QWidget.grab, Hypothesis, pywinauto)
- ✅ Стратегия тестирования 6 слоёв с acceptance criteria
- ✅ Структура файлов (полная карта `tests/`)

### Фаза 3: Implement
- ✅ Подзадача 0: Обновление зависимостей и конфигурации
- ✅ Подзадача 1: Schemathesis API Fuzzing (3 файла в tests/fuzz/)
- ✅ Подзадача 2: Умные Smoke-тесты (test_data_validation.py + test_orphan_records.py)
- ✅ Подзадача 3: pytest-qt + реальный DataAccess (23 теста, 5 файлов в tests/ui_real/)
- ✅ Подзадача 4: Hypothesis property-based (50 тестов, 4 файла в tests/property/)
- ✅ Подзадача 5: QWidget.grab() visual regression (3 теста, conftest + test_widget_snapshots.py)
- ✅ Подзадача 6: pywinauto integration (2 файла тестов + conftest в tests/pywinauto/)
- ✅ Подзадача 7: CI интеграция (test-property job добавлен в ci.yml)
- ✅ Подзадача 8: Обновление агентов и скиллов под 6 слоёв (7 файлов обновлено)

### Фаза 4: Проверки
- ✅ Property тесты: 50 passed
- ✅ Visual тесты: 3 passed
- ✅ UI Real тесты: 23 passed
- ⬜ Smoke тесты (нужен сервер)
- ⬜ Fuzz тесты (нужен сервер + Python 3.11)

### Фаза 5: PR & CI
- ⬜ Feature branch (уже на feat/admin-agents-cities-qa-audit)
- ⬜ PR создан
- ⬜ CI passed (все 5 + новые jobs)

---

## Граф зависимостей

```
Подзадача 0 (deps)
├──► Подзадача 1 (Schemathesis)  ─┐
├──► Подзадача 2 (Smoke)         ─┤─► параллельно
├──► Подзадача 3 (UI real)       ─┤─► параллельно
├──► Подзадача 4 (Hypothesis)    ─┘─► параллельно
│
├──► Подзадача 5 (Visual) ◄── зависит от #3 (conftest.py ui_real)
├──► Подзадача 6 (pywinauto) ◄── зависит от #3 (DataAccess паттерн)
│
├──► Подзадача 7 (CI) ◄── зависит от ВСЕХ (#1-#6)
│
└──► Подзадача 8 (Агенты/Скиллы) ◄── зависит от #0 (знать структуру)
```

---

## Фаза 3: Подзадачи реализации

---

### Подзадача 0: Обновление зависимостей и конфигурации

- **Агент:** Worker
- **Приоритет:** P0 (блокирующая — все подзадачи зависят)
- **Зависимости:** нет
- **Параллелизм:** нет (выполняется первой)
- **Файлы для изменения:**
  - `requirements-dev.txt` — добавить `schemathesis>=3.30`, `hypothesis>=6.0`, `pywinauto>=0.6.8`
  - `pytest.ini` — добавить маркеры: `fuzz`, `ui_real`, `property`, `visual`
  - `.gitignore` — добавить `tests/visual/snapshots/`
- **Файлы для создания:**
  - `tests/fuzz/__init__.py` — пустой init
  - `tests/ui_real/__init__.py` — пустой init
  - `tests/property/__init__.py` — пустой init
  - `tests/visual/__init__.py` — пустой init (если не существует)
  - `tests/integration/__init__.py` — пустой init
- **Acceptance Criteria:**
  - [ ] `pip install -r requirements-dev.txt` проходит без ошибок
  - [ ] `pytest --markers` показывает маркеры `fuzz`, `ui_real`, `property`, `visual`, `integration`
  - [ ] `tests/visual/snapshots/` в `.gitignore`
  - [ ] Все `__init__.py` на месте (правило #1 проекта)
  - [ ] Существующие тесты НЕ сломаны (pytest tests/ui/ tests/client/ проходит)
- **Gate Check:** [ ] build [ ] tests [ ] lint [ ] design [ ] security

---

### Подзадача 1: Schemathesis API Fuzzing

- **Агент:** Backend Worker
- **Приоритет:** P0 (критично — найдёт баги сразу, 5-15 на первом прогоне)
- **Зависимости:** Подзадача 0 (зависимости установлены)
- **Параллелизм:** можно параллельно с #2, #3, #4
- **Файлы для создания:**
  - `tests/fuzz/conftest.py` — BASE_URL из env, JWT авторизация, auto-skip если сервер недоступен
  - `tests/fuzz/test_schemathesis_all.py` — автогенерация тестов из `/openapi.json`, `@schema.parametrize()`, проверки: no 500, schema valid
  - `tests/fuzz/schemathesis.yaml` — конфигурация: исключения (file upload endpoints), `max-response-time: 10000`, `stateful: links`
- **Файлы для изменения:**
  - нет (новая директория)
- **Acceptance Criteria:**
  - [ ] Schemathesis запускается против `/openapi.json` без ошибок конфигурации
  - [ ] Покрыто не менее 200 из 214 endpoints автогенерацией
  - [ ] Ни один endpoint не возвращает 500 на невалидные данные (допустимо: 400, 422, 401, 403, 404)
  - [ ] Ответы соответствуют OpenAPI-схеме (поля, типы, required)
  - [ ] Исключения для file-upload endpoints задокументированы в `schemathesis.yaml`
  - [ ] Auto-skip если сервер недоступен
  - [ ] Запуск: `pytest tests/fuzz/ -v` или `st run` из CLI
- **Gate Check:** [ ] build [ ] tests [ ] lint [ ] design [ ] security

**Среда выполнения:** Python 3.11 (серверный). НЕ запускать на Python 3.14 (клиентский).

---

### Подзадача 2: Умные Smoke-тесты

- **Агент:** Backend Worker
- **Приоритет:** P0 (критично — быстрая отдача, проверка ДАННЫХ вместо HTTP-кодов)
- **Зависимости:** Подзадача 0
- **Параллелизм:** можно параллельно с #1, #3, #4
- **Файлы для создания:**
  - `tests/smoke/test_data_validation.py` — проверка ЗНАЧЕНИЙ: area > 0, total_amount > 0, обязательные поля не null, даты в правильном порядке (created_at < deadline)
  - `tests/smoke/test_orphan_records.py` — сиротские записи: карточка без договора, договор без клиента, оплата без договора
- **Файлы для изменения:**
  - `tests/smoke/test_business_rules.py` — расширить: area * rate_per_m2 = amount, проверка формул расчёта
  - `tests/smoke/test_dashboard_accuracy.py` — расширить: dashboard цифры = реальным подсчётам (погрешность < 1%)
- **Acceptance Criteria:**
  - [ ] Все договоры: `area > 0` и `total_amount > 0`
  - [ ] Все оплаты с тарифами: `amount > 0` (area * rate_per_m2 != 0)
  - [ ] CRM-карточки в допустимых колонках
  - [ ] Нет сиротских записей (0 карточек без договора, 0 договоров без клиента)
  - [ ] Dashboard цифры совпадают с реальными подсчётами (< 1% расхождение)
  - [ ] Все обязательные поля не null/пустые
  - [ ] При ошибке — вывод конкретных ID проблемных записей
  - [ ] Auto-skip если сервер недоступен
- **Gate Check:** [ ] build [ ] tests [ ] lint [ ] design [ ] security

**Шаблон перехода от status_code к данным:**
```
Было:   assert resp.status_code == 200
Стало:  for contract in contracts[:50]:
            assert contract["area"] > 0, f"Договор {contract['id']}: area=0"
            assert contract["total_amount"] > 0, f"Договор {contract['id']}: сумма=0"
```

---

### Подзадача 3: pytest-qt + реальный DataAccess

- **Агент:** Frontend Worker
- **Приоритет:** P1 (важно — тестирует что UI показывает реальные данные)
- **Зависимости:** Подзадача 0
- **Параллелизм:** можно параллельно с #1, #2, #4
- **Файлы для создания:**
  - `tests/ui_real/conftest.py` — fixture `real_data_access` (реальный DataAccess + api_client), fixture `skip_if_no_server` (auto-skip), `QT_QPA_PLATFORM=offscreen` для headless
  - `tests/ui_real/test_crm_tab_real.py` — CRM Kanban: карточки загрузились, колонки не пустые
  - `tests/ui_real/test_contract_dialog.py` — диалог договора: area, client, dates заполнены
  - `tests/ui_real/test_crm_card_dialog.py` — диалог CRM-карточки: стадии, исполнители загрузились
  - `tests/ui_real/test_salaries_real.py` — вкладка зарплат: таблица не пустая, суммы > 0
  - `tests/ui_real/test_supervision_real.py` — авторский надзор: адреса загрузились
  - `tests/ui_real/test_payments_real.py` — таблица оплат: суммы рассчитаны
  - `tests/ui_real/test_dashboard_real.py` — dashboard: графики содержат данные
  - `tests/ui_real/test_rates_dialog.py` — диалог тарифов: тарифы загрузились
  - `tests/ui_real/test_login_real.py` — окно логина: поля видимы, кнопка активна
  - `tests/ui_real/test_reports_real.py` — отчёты: PDF генерируется без ошибок
- **Файлы для изменения:**
  - нет (новая директория, существующие `tests/ui/` без изменений)
- **Acceptance Criteria:**
  - [ ] Виджеты создаются без исключений с реальным DataAccess
  - [ ] Данные загружаются из API (`text() != ""`, `rowCount() > 0`)
  - [ ] Обязательные элементы видимы (`isVisible() == True`)
  - [ ] Кнопки активны (`isEnabled() == True`)
  - [ ] При ошибке DataAccess (None/Exception) — виджет не падает
  - [ ] Auto-skip если сервер недоступен
  - [ ] Покрыто 10+ ключевых диалогов/вкладок (первая волна)
  - [ ] Существующие `tests/ui/` НЕ затронуты (мок-тесты остаются для CI)
- **Gate Check:** [ ] build [ ] tests [ ] lint [ ] design [ ] security

**Conftest паттерн:**
```python
@pytest.fixture
def real_data_access(skip_if_no_server):
    api_client = APIClient(base_url=BASE_URL)
    api_client.login(username=TEST_USER, password=TEST_PASS)
    return DataAccess(api_client=api_client, db=None)
```

---

### Подзадача 4: Hypothesis property-based

- **Агент:** Worker
- **Приоритет:** P1 (важно — ловит edge cases в расчётах, которые человек не придумает)
- **Зависимости:** Подзадача 0
- **Параллелизм:** можно параллельно с #1, #2, #3
- **Файлы для создания:**
  - `tests/property/conftest.py` — стратегии: area (0.1..50000), rate (1..500000), hours (0..744), dates (2020..2030), проценты (0..100)
  - `tests/property/test_payment_calc.py` — расчёт оплат: result > 0, not NaN, not Inf
  - `tests/property/test_salary_calc.py` — расчёт зарплат: result >= 0, корректный тип
  - `tests/property/test_date_utils.py` — утилиты дат: round-trip parse(format(d)) == d
  - `tests/property/test_norm_days.py` — нормо-дни: 0 <= result <= 31, int
- **Файлы для изменения:**
  - нет (новая директория)
- **Acceptance Criteria:**
  - [ ] Hypothesis выполняет минимум 100 примеров на каждый тест (`@settings(max_examples=200)`)
  - [ ] Ни одна расчётная функция не возвращает NaN, Inf, отрицательные значения
  - [ ] Ни одна функция не бросает необработанное исключение на граничных входных данных
  - [ ] При нахождении бага — Hypothesis предоставляет minimal failing example
  - [ ] `.hypothesis/` в .gitignore (уже есть)
  - [ ] Покрыты все 4 модуля: payment_calc, salary_calc, date_utils, norm_days
- **Gate Check:** [ ] build [ ] tests [ ] lint [ ] design [ ] security

**Целевые функции для поиска (Grep):**
- `calculate_payment` / `calc_payment` в `utils/` и `server/`
- `calc_salary` / `calculate_salary` в `utils/` и `server/`
- `parse_date` / `format_date` в `utils/date_utils.py` или аналог
- `norm_days` / `working_days` в `utils/`

---

### Подзадача 5: QWidget.grab() visual regression

- **Агент:** Frontend Worker
- **Приоритет:** P2 (полезно — ловит визуальные регрессии)
- **Зависимости:** Подзадача 3 (использует conftest.py из ui_real для реального DataAccess)
- **Параллелизм:** нет (после #3)
- **Файлы для создания:**
  - `tests/visual/conftest.py` — offscreen setup, `grab_widget()` helper, `pixel_diff_percent()` функция сравнения через Pillow
  - `tests/visual/test_widget_snapshots.py` — QWidget.grab() тесты для 5 ключевых виджетов
  - `tests/visual/baselines/` — директория для эталонных снимков (в git)
  - `tests/visual/snapshots/` — директория для текущих снимков (в gitignore)
- **Файлы для изменения:**
  - `.gitignore` — добавить `tests/visual/snapshots/` (если не добавлено в #0)
- **Acceptance Criteria:**
  - [ ] QWidget.grab() создаёт непустой QPixmap (size > 0x0)
  - [ ] Pixel diff с baseline < 5% (порог для шрифтовых вариаций)
  - [ ] Baseline хранятся в git (`tests/visual/baselines/`)
  - [ ] Текущие снимки в gitignore (`tests/visual/snapshots/`)
  - [ ] Offscreen рендеринг корректен (не пустой чёрный прямоугольник)
  - [ ] Покрыто 5 ключевых виджетов: CRM Kanban, диалог договора, таблица зарплат, timeline, dashboard
  - [ ] Команда обновления baseline: `pytest tests/visual/ --update-baseline`
- **Gate Check:** [ ] build [ ] tests [ ] lint [ ] design [ ] security

**Механизм сравнения:**
```
1. QWidget.grab() → QPixmap → .save() PNG
2. Pillow Image.open() текущий + baseline
3. ImageChops.difference() → diff image
4. Подсчёт непрозрачных пикселей diff / total pixels
5. Если > 5% — FAIL + сохранить diff.png для анализа
```

---

### Подзадача 6: pywinauto integration (< 10 мин)

- **Агент:** Frontend Worker
- **Приоритет:** P2 (полезно — тестирует запущенное приложение)
- **Зависимости:** Подзадача 3 (DataAccess паттерн)
- **Параллелизм:** нет (после #3)
- **Файлы для создания:**
  - `tests/integration/conftest.py` — запуск `main.py`, auto-login через Qt inject, hard timeout 600 сек, cleanup (kill процесса)
  - `tests/integration/test_running_app.py` — сценарий < 10 мин: вкладки, таблицы, кнопки, диалоги
- **Файлы для изменения:**
  - нет (новая директория)
- **Acceptance Criteria:**
  - [ ] Весь прогон завершается за < 10 минут (hard timeout `--timeout=600`)
  - [ ] Главное окно открывается после логина
  - [ ] Все основные вкладки доступны через accessibility tree (backend="uia")
  - [ ] Таблицы содержат > 0 строк данных
  - [ ] Ключевые кнопки кликабельны (enabled + visible)
  - [ ] Приложение не крашится за время прогона
  - [ ] Запуск ТОЛЬКО ручной (НЕ CI): `pytest tests/integration/ -v --timeout=600`
- **Gate Check:** [ ] build [ ] tests [ ] lint [ ] design [ ] security

**Сценарий прогона (укладывается в 10 минут):**
1. Запуск `main.py` (30 сек на загрузку)
2. Автологин через Qt inject (10 сек)
3. Проверка главного окна: все вкладки существуют (30 сек)
4. Обход 6 вкладок: проверка что таблицы не пустые (3 мин)
5. Открытие 3 ключевых диалогов: проверка что поля заполнены (2 мин)
6. Закрытие приложения (10 сек)
7. **Итого: ~6-7 минут** (запас 3-4 минуты)

---

### Подзадача 7: CI интеграция (новые jobs)

- **Агент:** Worker (DevOps)
- **Приоритет:** P2 (полезно — автоматизация запуска новых слоёв)
- **Зависимости:** Подзадачи 1-6 (все тесты должны быть готовы)
- **Параллелизм:** нет (последняя)
- **Файлы для изменения:**
  - `.github/workflows/ci.yml` — добавить 4 новых job:

| Job | Триггер | Python | Зависит от | Описание |
|-----|---------|--------|------------|----------|
| `test-fuzz` | `workflow_dispatch` (ручной) | 3.11 | Работающий сервер | Schemathesis → OpenAPI |
| `test-property` | Каждый push | 3.14 | Ничего | Hypothesis → расчёты |
| `test-ui-real` | Каждый push | 3.14 + offscreen | Сервер (auto-skip) | pytest-qt + DataAccess |
| `test-visual` | Weekly + ручной | 3.14 + offscreen | Ничего | QWidget.grab() + diff |

- **Файлы для создания:**
  - нет (изменение существующего workflow)
- **Acceptance Criteria:**
  - [ ] `test-property` запускается на каждый push и проходит
  - [ ] `test-ui-real` запускается на push, auto-skip если сервер недоступен
  - [ ] `test-visual` запускается weekly (cron) или ручным trigger
  - [ ] `test-fuzz` запускается только ручным trigger (`workflow_dispatch`)
  - [ ] Все новые jobs используют `QT_QPA_PLATFORM=offscreen` где нужно
  - [ ] Существующие 5 jobs НЕ затронуты и проходят
  - [ ] `continue-on-error: true` для jobs зависящих от сервера
- **Gate Check:** [ ] build [ ] tests [ ] lint [ ] design [ ] security

**Порядок добавления в CI:**
1. `test-property` — без зависимостей, добавляется сразу
2. `test-visual` — offscreen, добавляется вторым
3. `test-ui-real` — зависит от сервера, auto-skip
4. `test-fuzz` — последний, ручной trigger после деплоя

---

### Подзадача 8: Обновление агентов и скиллов под 6-слойную систему тестирования

- **Агент:** Worker
- **Приоритет:** P1 (важно — без этого агенты не знают о новых слоях тестирования)
- **Зависимости:** Подзадача 0 (знать структуру новых директорий)
- **Параллелизм:** можно параллельно с #1-#4 (не зависит от тестового кода)
- **Файлы для изменения:**

#### 1. `.claude/agents/test-runner-agent.md`
Что менять:
- Добавить в маппинг файлов → тестов новые категории:
  - `tests/fuzz/` — API fuzzing (Schemathesis), Python 3.11
  - `tests/ui_real/` — реальные UI тесты (pytest-qt + DataAccess)
  - `tests/property/` — Hypothesis property-based
  - `tests/visual/` — QWidget.grab() visual regression
  - `tests/integration/` — pywinauto запущенное приложение (только ручной, < 10 мин)
- Добавить команды запуска для каждого нового слоя
- Обновить структуру тестов проекта (`tests/` дерево)
- Добавить правило: `tests/fuzz/` требует Python 3.11, `tests/integration/` — только Windows с GUI

#### 2. `.claude/skills/test-run/SKILL.md`
Что менять:
- Добавить в маппинг новые категории (fuzz, ui_real, property, visual, integration)
- Добавить примеры запуска:
  - `/test-run fuzz` → `tests/fuzz/` (нужен сервер)
  - `/test-run ui_real` → `tests/ui_real/` (нужен сервер, offscreen)
  - `/test-run property` → `tests/property/` (без сервера)
  - `/test-run visual` → `tests/visual/` (offscreen)
  - `/test-run integration` → `tests/integration/` (Windows, GUI, < 10 мин)
- Обновить `argument-hint`: добавить `fuzz|ui_real|property|visual|integration`

#### 3. `.claude/agents/gate-checker-agent.md`
Что менять:
- В проверке 2 (тесты) добавить маппинг для новых категорий:
  - `tests/fuzz/` → при изменении `server/` (если сервер доступен)
  - `tests/property/` → при изменении расчётных функций в `utils/`
  - `tests/ui_real/` → при изменении `ui/` или `utils/data_access.py` (если сервер доступен)
- В проверке 4 (дизайн) учитывать `design.md` с 6 слоями
- Не запускать `tests/integration/` в Gate Check (только ручной)

#### 4. `.claude/skills/post-fix-verify/SKILL.md`
Что менять:
- Добавить в Шаг 4 (запуск тестов) новые категории по маппингу:
  - При изменении `server/` → `tests/fuzz/` (если сервер доступен)
  - При изменении расчётов → `tests/property/`
  - При изменении `ui/` → `tests/ui_real/` (если сервер доступен)
- Добавить Шаг 4.5: Data Consistency — `pytest tests/smoke/test_data_validation.py` при изменениях расчётов/оплат

#### 5. `.claude/agents/qa-monitor-agent.md`
Что менять:
- Добавить ссылку на `tests/integration/` как альтернативу ручному тестированию
- В Шаг 1 (определение тест-сценариев) добавить: если изменены расчёты → порекомендовать `tests/property/` перед ручным QA
- Добавить: при обнаружении ошибки в QA → проверить покрытие новыми слоями (fuzz, property, ui_real)

#### 6. `.claude/CLAUDE.md` — секция "Стратегия тестирования"
Что менять:
- Обновить секцию тестирования: вместо "3 уровня" → "6 слоёв реального тестирования"
- Добавить команды запуска для каждого нового слоя
- Добавить ссылку на `docs/plan/testing-strategy-overhaul/roadmap.md`
- Обновить "Правило новых тестов": добавить рекомендацию по выбору слоя для нового теста

#### 7. `.claude/commands/orkester.md` (skill orkester)
Что менять:
- В ШАГ 3 (TEST-RUNNER) добавить новые категории в маппинг
- В разделе "КОМАНДЫ ТЕСТИРОВАНИЯ" добавить команды для fuzz, property, ui_real, visual, integration

- **Acceptance Criteria:**
  - [ ] test-runner-agent.md знает о 6 новых категориях тестов
  - [ ] `/test-run` скилл принимает аргументы: fuzz, ui_real, property, visual, integration
  - [ ] gate-checker-agent.md запускает property и ui_real тесты в Gate Check
  - [ ] post-fix-verify скилл включает data validation и property тесты
  - [ ] qa-monitor-agent.md ссылается на integration тесты
  - [ ] CLAUDE.md описывает 6 слоёв тестирования
  - [ ] orkester.md содержит новые команды тестирования
  - [ ] Все агенты и скиллы не противоречат друг другу (одинаковый маппинг)
- **Gate Check:** [ ] build [ ] tests [ ] lint [ ] design [ ] security

---

## Сводная таблица подзадач

| # | Подзадача | Агент | Приоритет | Зависит от | Параллельно | Файлов создать | Файлов изменить |
|---|-----------|-------|-----------|------------|-------------|----------------|-----------------|
| 0 | Зависимости и конфиг | Worker | P0 | — | нет | 5 (`__init__.py`) | 3 |
| 1 | Schemathesis API Fuzzing | Backend | P0 | #0 | с #2, #3, #4 | 3 | 0 |
| 2 | Умные Smoke-тесты | Backend | P0 | #0 | с #1, #3, #4 | 2 | 2 |
| 3 | pytest-qt + DataAccess | Frontend | P1 | #0 | с #1, #2, #4 | 12 | 0 |
| 4 | Hypothesis property-based | Worker | P1 | #0 | с #1, #2, #3 | 5 | 0 |
| 5 | QWidget.grab() visual | Frontend | P2 | #3 | нет | 3 + baselines | 1 |
| 6 | pywinauto integration | Frontend | P2 | #3 | нет | 2 | 0 |
| 7 | CI интеграция | DevOps | P2 | #1-#6 | нет | 0 | 1 |
| 8 | Агенты и скиллы | Worker | P1 | #0 | с #1-#4 | 0 | 7 |

---

## Затронутые файлы проекта (полный список)

### Существующие файлы для изменения

| Файл | Подзадача | Что менять |
|------|-----------|-----------|
| `requirements-dev.txt` | #0 | Добавить schemathesis, hypothesis, pywinauto |
| `pytest.ini` | #0 | Добавить маркеры fuzz, ui_real, property, visual |
| `.gitignore` | #0 | Добавить `tests/visual/snapshots/` |
| `tests/smoke/test_business_rules.py` | #2 | Расширить assertions на area*rate=amount |
| `tests/smoke/test_dashboard_accuracy.py` | #2 | Расширить assertions на реальные подсчёты |
| `.github/workflows/ci.yml` | #7 | Добавить 4 новых CI jobs |
| `.claude/agents/test-runner-agent.md` | #8 | Маппинг + команды для 6 новых категорий |
| `.claude/skills/test-run/SKILL.md` | #8 | Аргументы fuzz/ui_real/property/visual/integration |
| `.claude/agents/gate-checker-agent.md` | #8 | Маппинг property и ui_real в Gate Check |
| `.claude/skills/post-fix-verify/SKILL.md` | #8 | Data validation + property в верификации |
| `.claude/agents/qa-monitor-agent.md` | #8 | Ссылки на integration тесты |
| `.claude/CLAUDE.md` | #8 | 6 слоёв тестирования вместо 3 уровней |
| `.claude/commands/orkester.md` | #8 | Новые команды тестирования |

### Новые файлы для создания

| Директория | Файлы | Подзадача |
|-----------|-------|-----------|
| `tests/fuzz/` | `__init__.py`, `conftest.py`, `test_schemathesis_all.py`, `schemathesis.yaml` | #0, #1 |
| `tests/ui_real/` | `__init__.py`, `conftest.py`, 10 тестовых файлов | #0, #3 |
| `tests/property/` | `__init__.py`, `conftest.py`, 4 тестовых файла | #0, #4 |
| `tests/visual/` | `__init__.py`, `conftest.py`, `test_widget_snapshots.py`, `baselines/`, `snapshots/` | #0, #5 |
| `tests/integration/` | `__init__.py`, `conftest.py`, `test_running_app.py` | #0, #6 |
| `tests/smoke/` | `test_data_validation.py`, `test_orphan_records.py` | #2 |

### Существующие файлы для чтения/анализа (Grep при реализации)

| Файл | Зачем |
|------|-------|
| `utils/data_access.py` | DataAccess API для ui_real тестов |
| `utils/api_client/base.py` | APIClient для conftest |
| `tests/ui/conftest.py` | Паттерн конфигурации UI тестов |
| `tests/smoke/conftest.py` | Паттерн auto-skip для сервера |
| `server/main.py` | Список роутеров для Schemathesis |

---

## Метрики успеха (до/после)

| Метрика | Сейчас | После внедрения |
|---------|--------|-----------------|
| Assertions на реальные данные | 49 | 500+ |
| API endpoints под fuzz-тестами | 0 | 200+ (из 214) |
| UI тесты с реальным DataAccess | 0 | 100+ |
| Расчётные функции под property-тестами | 0 | Все ключевые (4+ модуля) |
| Виджеты с visual baseline | 0 | 5+ ключевых |
| Integration тесты запущенного приложения | 0 | 15+ проверок (< 10 мин) |
| Баги найденные ДО пользователя | ~0% | >50% |

---

## Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|------------|---------|-----------|
| Schemathesis не совместим с Python 3.14 | Высокая | Низкое | Запускать на 3.11 (серверный) |
| Offscreen рендеринг отличается от экранного | Средняя | Среднее | Отдельные baseline для CI, порог 5% |
| Flaky тесты при сетевых запросах в ui_real | Высокая | Среднее | Retry логика, timeout 10s, auto-skip |
| Baseline снимки устаревают при UI-изменениях | Средняя | Низкое | Команда: `pytest tests/visual/ --update-baseline` |
| Hypothesis находит слишком много edge cases | Низкая | Низкое | `@settings(max_examples=200)` |
| pywinauto превышает 10 минут | Средняя | Среднее | Hard timeout `--timeout=600`, kill процесса |
| pywinauto не находит элементы через UIA | Средняя | Среднее | `QT_USE_NATIVE_WINDOWS=1`, fallback на Qt accessibility bridge |

---

## Оценка трудозатрат

| Подзадача | Сложность | Оценка (чел-часы) |
|-----------|-----------|-------------------|
| #0 Зависимости | Низкая | 1 |
| #1 Schemathesis | Средняя | 4-6 |
| #2 Умные Smoke | Средняя | 6-8 |
| #3 pytest-qt + DataAccess | Высокая | 10-15 |
| #4 Hypothesis | Средняя | 4-6 |
| #5 Visual regression | Средняя | 6-8 |
| #6 pywinauto | Средняя | 4-6 |
| #7 CI интеграция | Средняя | 4-6 |
| #8 Агенты и скиллы | Средняя | 3-4 |
| **Итого** | | **42-60** |

---

## Рекомендуемый порядок реализации

**Волна 1 (P0, максимальная отдача):**
1. Подзадача 0: Зависимости → сразу
2. Подзадачи 1 + 2 + 4 + 8: Schemathesis + Smoke + Hypothesis + Агенты/Скиллы → параллельно

**Волна 2 (P1, реальное UI тестирование):**
3. Подзадача 3: pytest-qt + DataAccess → после Волны 1

**Волна 3 (P2, визуальное + интеграционное):**
4. Подзадачи 5 + 6: Visual + pywinauto → после #3
5. Подзадача 7: CI → после всех

---

*Артефакт создан Planner Agent. Реализация по запросу через оркестрацию или ручной запуск подзадач.*
