# Архитектурный дизайн: Перестройка тестирования Interior Studio CRM

**Дата:** 2026-03-06
**Фаза:** Design (на основе research.md)
**Цель:** Спроектировать 6-слойную систему тестирования, которая ловит реальные баги ДО пользователей

---

## 1. C4 Model — интеграция тестирования с архитектурой

### 1.1 Context Level — внешние границы системы

```
┌─────────────────────────────────────────────────────────────────┐
│                    INTERIOR STUDIO CRM                          │
│                                                                 │
│  ┌──────────────┐    REST API     ┌──────────────┐              │
│  │  PyQt5       │ ◄────────────► │  FastAPI      │              │
│  │  Desktop     │    JSON/JWT     │  Server       │              │
│  │  (Py 3.14)   │                │  (Py 3.11)    │              │
│  └──────┬───────┘                └──────┬────────┘              │
│         │ fallback                      │                       │
│  ┌──────▼───────┐                ┌──────▼────────┐              │
│  │  SQLite      │                │  PostgreSQL   │              │
│  │  (offline)   │                │  (production) │              │
│  └──────────────┘                └───────────────┘              │
└─────────────────────────────────────────────────────────────────┘

                    ТЕСТОВЫЕ СИСТЕМЫ:

┌─────────────────┐  ┌────────────────┐  ┌──────────────────────┐
│ Schemathesis    │  │ Hypothesis     │  │ pytest-qt + qtbot    │
│ (API Fuzzing)   │  │ (Property)     │  │ (Реальный UI)        │
│ Py 3.11         │  │ Py 3.14        │  │ Py 3.14              │
│ → FastAPI       │  │ → Расчёты      │  │ → Виджеты+DataAccess │
└─────────────────┘  └────────────────┘  └──────────────────────┘
┌─────────────────┐  ┌────────────────┐
│ Smart Smoke     │  │ Visual Regr.   │
│ (Данные, не коды│  │ QWidget.grab() │
│ → Production API│  │ → Снимки CI    │
└─────────────────┘  └────────────────┘
```

**Какие тесты на каком уровне:**

| Слой тестирования | Целевой компонент | Среда выполнения | Что проверяет |
|-------------------|-------------------|------------------|---------------|
| Schemathesis | FastAPI Server | Python 3.11 (серверный) | Валидация, 500-ки, схемы |
| Умные Smoke | REST API (Production) | Python 3.11 | Правильность данных |
| pytest-qt + DataAccess | UI + DataAccess | Python 3.14 (клиентский) | Реальная загрузка данных в виджеты |
| Hypothesis | Расчётные функции | Python 3.14 (клиентский) | Edge cases в вычислениях |
| QWidget.grab() | Визуальный рендеринг | Python 3.14 + offscreen | Визуальные регрессии |
| pywinauto (10 мин) | Запущенное приложение | Windows + GUI | Видимость, данные в таблицах, кликабельность |

### 1.2 Container Level — где живут тесты

```
┌─ Desktop Container (Python 3.14) ─────────────────────────────┐
│                                                                │
│  tests/ui_real/          pytest-qt + реальный DataAccess       │
│  tests/property/         Hypothesis property-based             │
│  tests/visual/snapshots/ QWidget.grab() baseline-сравнение     │
│                                                                │
│  Зависимости: pytest-qt (уже есть), hypothesis (новая),        │
│               Pillow (уже есть)                                │
│                                                                │
│  CI переменная: QT_QPA_PLATFORM=offscreen                     │
└────────────────────────────────────────────────────────────────┘

┌─ Server Container (Python 3.11) ──────────────────────────────┐
│                                                                │
│  tests/fuzz/             Schemathesis API fuzzing              │
│  tests/smoke/            Улучшенные smoke (проверка данных)    │
│                                                                │
│  Зависимости: schemathesis (новая)                             │
│                                                                │
│  Запуск: против production API или Docker-dev                  │
└────────────────────────────────────────────────────────────────┘

┌─ CI Container (GitHub Actions) ───────────────────────────────┐
│                                                                │
│  Job: test-fuzz          Schemathesis → OpenAPI spec           │
│  Job: test-smoke-data    Smart smoke → production/staging      │
│  Job: test-ui-real       pytest-qt offscreen                   │
│  Job: test-property      Hypothesis → расчёты                  │
│  Job: test-visual        QWidget.grab() → diff с baseline      │
│                                                                │
│  Триггеры: push (fuzz, property), deploy (smoke), weekly       │
│  (visual)                                                      │
└────────────────────────────────────────────────────────────────┘
```

### 1.3 Component Level — конкретные модули

```
tests/
├── fuzz/                          # СЛОЙ 1: API Fuzzing
│   ├── conftest.py                # Base URL, auth headers
│   ├── test_schemathesis_all.py   # Автогенерация из OpenAPI
│   └── schemathesis.yaml          # Конфигурация (исключения, лимиты)
│
├── smoke/                         # СЛОЙ 2: Умные Smoke (расширение)
│   ├── test_data_validation.py    # Новый: проверка ЗНАЧЕНИЙ данных
│   ├── test_business_rules.py     # Расширить: area*rate=amount
│   ├── test_orphan_records.py     # Новый: сиротские записи
│   └── test_dashboard_accuracy.py # Расширить: цифры = реальным
│
├── ui_real/                       # СЛОЙ 3: Реальные UI тесты
│   ├── conftest.py                # qtbot + реальный DataAccess
│   ├── test_crm_tab_real.py       # CRM Kanban с реальными данными
│   ├── test_contract_dialog.py    # Диалог договора
│   ├── test_salaries_tab_real.py  # Зарплаты
│   └── test_supervision_real.py   # Авторский надзор
│
├── property/                      # СЛОЙ 4: Hypothesis
│   ├── conftest.py                # Стратегии (area, rate, date)
│   ├── test_payment_calc.py       # Расчёт оплат
│   ├── test_salary_calc.py        # Расчёт зарплат
│   └── test_date_utils.py         # Утилиты дат
│
└── visual/                        # СЛОЙ 5: Визуальная регрессия
    ├── conftest.py                # offscreen setup, grab helpers
    ├── test_widget_snapshots.py   # QWidget.grab() тесты
    ├── baselines/                 # Эталонные снимки
    │   ├── crm_tab.png
    │   ├── contract_dialog.png
    │   └── ...
    └── snapshots/                 # Текущие снимки (gitignore)
```

---

## 2. DFD — Data Flow Diagram

### 2.1 ТЕКУЩИЙ поток (проблемный)

```
┌──────────┐     mock()      ┌──────────────┐    assert     ┌────────────┐
│          │ ──────────────► │              │ ────────────► │            │
│   Test   │   MagicMock     │  Мок-объект  │  status==200  │  PASS      │
│          │   return_value  │  (фейковые   │  isinstance   │  (ложный)  │
│          │   = [...]       │   данные)    │  (data, list) │            │
└──────────┘                 └──────────────┘               └────────────┘

Проблема: тест НИКОГДА не видит реальные данные.
Баги в API, расчётах, отображении — невидимы.
```

### 2.2 НОВЫЙ поток (5 слоёв)

```
СЛОЙ 1: Schemathesis (API Fuzzing)
┌──────────┐   OpenAPI spec   ┌──────────────┐   HTTP      ┌────────────┐
│Schemathesis────────────────►│ Генератор    │───────────►│ FastAPI    │
│          │   auto-generate  │ 1000+ кейсов │ fuzz data  │ Server     │
└──────────┘                  └──────────────┘            └─────┬──────┘
                                                                │
                              ┌──────────────┐            ┌─────▼──────┐
                              │ Assert:      │◄───────────│ Response   │
                              │ no 500       │  JSON      │ code+body  │
                              │ schema valid │            └────────────┘
                              │ no crashes   │
                              └──────────────┘

СЛОЙ 2: Умные Smoke (проверка данных)
┌──────────┐   real HTTP      ┌──────────────┐   assert     ┌────────────┐
│  Test    │ ──────────────► │  Production  │ ────────────►│  ДАННЫЕ:   │
│  (smoke) │   GET /contracts │  API Server  │  area > 0    │  area=45.5 │
│          │   GET /payments  │  PostgreSQL  │  amount > 0  │  amount>0  │
│          │                  │              │  no orphans  │  client_id │
└──────────┘                  └──────────────┘              └────────────┘

СЛОЙ 3: pytest-qt + реальный DataAccess
┌──────────┐   DataAccess     ┌──────────────┐   render    ┌────────────┐
│  qtbot   │ ──────────────► │  Реальный    │ ──────────►│  QWidget   │
│  test    │   .get_contracts │  API/DB      │  setText    │  (живой)   │
│          │                  │  (не мок!)   │  addItem    │            │
└──────────┘                  └──────────────┘             └─────┬──────┘
                                                                │
                              ┌──────────────┐                  │
                              │ Assert:      │◄─────────────────┘
                              │ text() != "" │  widget.text()
                              │ isVisible()  │  widget.isVisible()
                              │ count() > 0  │  table.rowCount()
                              └──────────────┘

СЛОЙ 4: Hypothesis (property-based)
┌──────────┐   strategies     ┌──────────────┐   assert     ┌────────────┐
│Hypothesis│ ──────────────► │ calculate_   │ ────────────►│ Инварианты:│
│ @given() │   area=0.1..1e4 │ payment()    │  result > 0  │ result > 0 │
│          │   rate=100..1e5 │ calc_salary()│  not NaN     │ not NaN    │
│          │   100+ вариантов│              │  not Inf     │ finite     │
└──────────┘                  └──────────────┘              └────────────┘

СЛОЙ 5: Visual Regression (QWidget.grab)
┌──────────┐   qtbot+render   ┌──────────────┐   compare   ┌────────────┐
│  Test    │ ──────────────► │  QWidget     │ ──────────►│  Pillow    │
│  (visual)│   .grab()       │  .grab()     │  pixel diff │  ImageChops │
│          │   offscreen     │  → QPixmap   │  < 5%       │  .difference│
└──────────┘                  └──────────────┘              └────────────┘
```

### 2.3 Сводная диаграмма потоков

```
                     ┌──────────────────────────┐
                     │    PRODUCTION SERVER      │
                     │    FastAPI + PostgreSQL   │
                     └─────────┬────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
     ┌────────▼──────┐ ┌──────▼───────┐ ┌──────▼──────┐
     │ Schemathesis  │ │ Smart Smoke  │ │ DataAccess  │
     │ (fuzzing)     │ │ (validation) │ │ (real API)  │
     │ → 500, schema │ │ → data values│ │ → UI data   │
     └───────────────┘ └──────────────┘ └──────┬──────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │ pytest-qt (qtbot)   │
                                    │ → widget assertions │
                                    │ → visibility checks │
                                    └──────────┬──────────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │ QWidget.grab()      │
                                    │ → visual regression │
                                    └─────────────────────┘

     ┌───────────────┐
     │ Hypothesis    │  (независимый, чистые функции)
     │ → edge cases  │
     └───────────────┘
```

---

## 3. ADR — Architecture Decision Records

### ADR-1: Schemathesis vs ручные API тесты

| Параметр | Решение |
|----------|---------|
| **Статус** | Принято |
| **Контекст** | 603 smoke-assertions проверяют только `status_code`. Ручное написание edge-case тестов для 214 endpoints — нереалистично. |
| **Решение** | Schemathesis — автогенерация тестов из OpenAPI spec FastAPI |
| **Альтернативы** | (1) Ручное написание — потребует 2000+ тестов, месяцы работы. (2) Dredd — привязан к OpenAPI 2.0, хуже поддержка FastAPI. (3) Postman/Newman — ручное описание каждого кейса. |
| **Обоснование** | FastAPI автоматически генерирует OpenAPI spec (`/openapi.json`). Schemathesis читает этот spec и генерирует тысячи запросов — невалидные значения, граничные типы, пустые строки, null. Находит 5-15 багов на первом прогоне (статистика проекта). Покрытие 214 endpoints за 1 команду вместо ручного описания каждого. |
| **Ограничения** | Запуск только на Python 3.11 (серверный). Требует доступ к работающему серверу. Не проверяет бизнес-логику — только валидацию и устойчивость. |
| **Последствия** | Новый CI job `test-fuzz`. Файлы в `tests/fuzz/`. Schemathesis в серверных зависимостях (requirements-dev.txt). |

### ADR-2: pytest-qt с реальным DataAccess vs моки

| Параметр | Решение |
|----------|---------|
| **Статус** | Принято |
| **Контекст** | 2889 UI тестов используют `MagicMock()` для DataAccess. Тесты проверяют что виджет создаётся, но не что он показывает реальные данные. Баг "DataAccess вернул None → TypeError" не ловится ни одним тестом. |
| **Решение** | Новая категория `tests/ui_real/` — pytest-qt qtbot + реальный DataAccess (API к тестовому/production серверу) |
| **Альтернативы** | (1) Замена всех моков — сломает 2889 тестов, CI станет зависим от сервера. (2) pywinauto — блокирует машину, требует GUI, нестабилен. (3) Selenium/Playwright — для браузера, не для PyQt5. |
| **Обоснование** | Существующие мок-тесты остаются в `tests/ui/` — они ловят регрессии при рефакторинге и работают в CI без сервера. Новые тесты в `tests/ui_real/` создают РЕАЛЬНЫЙ виджет с РЕАЛЬНЫМ DataAccess, проверяют что данные загрузились, поля видимы, кнопки работают. Два набора дополняют друг друга. |
| **Ограничения** | Требует работающий сервер. Auto-skip если сервер недоступен (как smoke-тесты). Медленнее мок-тестов (сетевые запросы). |
| **Последствия** | Новая директория `tests/ui_real/`. Conftest с реальным DataAccess и auto-skip. QT_QPA_PLATFORM=offscreen для headless CI. 20 ключевых диалогов/вкладок покрыты первыми. |

### ADR-3: QWidget.grab() vs pywinauto для визуального тестирования

| Параметр | Решение |
|----------|---------|
| **Статус** | Принято |
| **Контекст** | Ни один тест не проверяет что видит пользователь. pywinauto тестировался на практике — блокирует машину, отнимает фокус, клики попадают не туда. |
| **Решение** | QWidget.grab() — headless снимки виджетов через Qt API + сравнение с baseline через Pillow |
| **Альтернативы** | (1) pywinauto — проверено, непригоден (блокирует работу). (2) PyAutoGUI locateOnScreen — хрупкий, зависит от DPI/темы/разрешения. (3) Squish for Qt — $15000/год. (4) Appium/WinAppDriver — WinAppDriver заморожен Microsoft. |
| **Обоснование** | `QWidget.grab()` — встроенный метод Qt, возвращает `QPixmap` виджета из памяти. Не требует экрана, фокуса, не мешает работе. Работает с `QT_QPA_PLATFORM=offscreen` в CI. Pillow `ImageChops.difference()` даёт pixel-level сравнение. Порог различия 5% — допускает мелкие шрифтовые вариации между ОС. |
| **Ограничения** | Не проверяет взаимодействие (клики, drag-and-drop). Baseline-снимки зависят от ОС/DPI — отдельные baseline для CI (Linux) и dev (Windows). Offscreen рендеринг может отличаться от экранного. |
| **Последствия** | `tests/visual/baselines/` — эталонные снимки (в git). `tests/visual/snapshots/` — текущие (в gitignore). CI job `test-visual` с offscreen. Обновление baseline при намеренных UI-изменениях. |

### ADR-4: Hypothesis vs ручные edge-case тесты

| Параметр | Решение |
|----------|---------|
| **Статус** | Принято |
| **Контекст** | Расчётные функции (оплаты, зарплаты, тарифы) тестируются единичными примерами. Edge cases (area=0, rate=0, NaN, огромные числа) не покрыты. |
| **Решение** | Hypothesis property-based тесты для всех расчётных функций |
| **Альтернативы** | (1) Ручные edge-case тесты — человек не придумает все граничные случаи. (2) Fuzzing параметров через pytest-parametrize — ограниченный набор, не генеративный. |
| **Обоснование** | Hypothesis генерирует сотни комбинаций входных параметров и проверяет инварианты: результат > 0, не NaN, не Inf, корректный тип. При нахождении бага — автоматически shrinks пример до минимального воспроизводимого. Покрывает деление на 0, переполнение float, отрицательные значения — то что человек забывает проверить. |
| **Ограничения** | Тестирует только чистые функции (без side effects). Не подходит для UI или API. Требует формулировки инвариантов (property), а не конкретных ожидаемых значений. |
| **Последствия** | `tests/property/` — новая директория. Hypothesis в клиентских зависимостях. `.hypothesis/` уже в gitignore. Покрытие: calculate_payment, calc_salary, date_utils, rate_calculations. |

---

## 4. Стратегия тестирования — детализация по слоям

### Слой 1: API Fuzzing (Schemathesis)

| Параметр | Значение |
|----------|---------|
| **Покрываемые модули** | Все 214 endpoints FastAPI (22 роутера) |
| **Среда** | Python 3.11, против работающего сервера |
| **Запуск** | CI: после каждого деплоя. Ручной: `st run` из `tests/fuzz/` |
| **Создаваемые файлы** | `tests/fuzz/conftest.py`, `tests/fuzz/test_schemathesis_all.py`, `tests/fuzz/schemathesis.yaml` |

**Acceptance Criteria:**
1. Schemathesis запускается против `/openapi.json` без ошибок конфигурации
2. Все endpoints покрыты автогенерацией (не менее 200 из 214)
3. Ни один endpoint не возвращает 500 на невалидные данные (допустимо: 400, 422, 401, 403, 404)
4. Ответы соответствуют OpenAPI-схеме (поля, типы, required)
5. Найденные баги документируются и создаются issues
6. Исключения для известных ограничений задокументированы в `schemathesis.yaml`

**Конфигурация (schemathesis.yaml):**
- Исключить endpoints требующие file upload (Yandex Disk)
- Установить `--max-response-time=10000` (10 сек)
- Авторизация через `--header "Authorization: Bearer {JWT}"`
- `--stateful=links` — проверка связанных endpoints

### Слой 2: Умные Smoke-тесты (проверка данных)

| Параметр | Значение |
|----------|---------|
| **Покрываемые модули** | Договоры, клиенты, CRM-карточки, оплаты, зарплаты, dashboard |
| **Среда** | Python 3.11, production API |
| **Запуск** | CI: после каждого деплоя. Ручной: `pytest tests/smoke/test_data_validation.py` |
| **Создаваемые файлы** | `tests/smoke/test_data_validation.py`, `tests/smoke/test_orphan_records.py` |

**Acceptance Criteria:**
1. Все договоры имеют `area > 0` и `total_amount > 0`
2. Все оплаты с тарифами имеют `amount > 0` (area * rate_per_m2 != 0)
3. Все CRM-карточки находятся в допустимых колонках
4. Нет сиротских записей: карточка без договора, договор без клиента
5. Dashboard цифры совпадают с реальными подсчётами (с погрешностью < 1%)
6. Все обязательные поля не null/пустые
7. Даты в правильном порядке: created_at < deadline, start_date < end_date
8. Тест выводит конкретные ID проблемных записей при ошибке

**Шаблон assertions (вместо status_code):**
```
Было:   assert resp.status_code == 200
Стало:  for contract in contracts[:50]:
            assert contract["area"] > 0, f"Договор {contract['id']}: area=0"
            assert contract["total_amount"] > 0, f"Договор {contract['id']}: сумма=0"
            assert contract["client_id"] is not None, f"Договор {contract['id']}: нет клиента"
```

### Слой 3: Реальное UI тестирование (pytest-qt + DataAccess)

| Параметр | Значение |
|----------|---------|
| **Покрываемые модули** | 20 ключевых диалогов/вкладок |
| **Среда** | Python 3.14, QT_QPA_PLATFORM=offscreen |
| **Запуск** | CI: отдельный job. Ручной: `pytest tests/ui_real/ -v` |
| **Создаваемые файлы** | `tests/ui_real/conftest.py`, 10-15 тестовых файлов |

**Приоритетные виджеты (первая волна):**

| # | Виджет | Файл теста | Что проверять |
|---|--------|-----------|---------------|
| 1 | CRM Kanban (crm_tab.py) | test_crm_tab_real.py | Карточки загрузились, колонки не пустые |
| 2 | Диалог договора | test_contract_dialog.py | area, client, dates заполнены |
| 3 | Диалог CRM-карточки | test_crm_card_dialog.py | Стадии, исполнители загрузились |
| 4 | Вкладка зарплат | test_salaries_real.py | Таблица не пустая, суммы > 0 |
| 5 | Вкладка надзора | test_supervision_real.py | Адреса загрузились |
| 6 | Таблица оплат | test_payments_real.py | Суммы рассчитаны |
| 7 | Dashboard | test_dashboard_real.py | Графики содержат данные |
| 8 | Диалог тарифов | test_rates_dialog.py | Тарифы загрузились |
| 9 | Окно логина | test_login_real.py | Поля видимы, кнопка активна |
| 10 | Отчёты | test_reports_real.py | PDF генерируется без ошибок |

**Acceptance Criteria:**
1. Виджет создаётся без исключений с реальным DataAccess
2. Данные загружаются из API (text() != "", rowCount() > 0)
3. Обязательные элементы видимы (isVisible() == True)
4. Кнопки активны (isEnabled() == True)
5. При ошибке DataAccess (None/Exception) — виджет не падает
6. Auto-skip если сервер недоступен

**Conftest паттерн:**
```
conftest.py:
- fixture real_data_access: создаёт DataAccess с реальным api_client
- fixture skip_if_no_server: проверяет доступность сервера, skip если нет
- fixture qtbot: стандартный pytest-qt
- QT_QPA_PLATFORM=offscreen для headless
```

### Слой 4: Property-Based Testing (Hypothesis)

| Параметр | Значение |
|----------|---------|
| **Покрываемые модули** | Расчётные функции: оплаты, зарплаты, даты, тарифы |
| **Среда** | Python 3.14 (клиентский) |
| **Запуск** | CI: в основном test job. Ручной: `pytest tests/property/ -v` |
| **Создаваемые файлы** | `tests/property/conftest.py`, 3-4 тестовых файла |

**Целевые функции:**

| # | Функция/Модуль | Файл теста | Инварианты |
|---|---------------|-----------|------------|
| 1 | calculate_payment (area, rate) | test_payment_calc.py | result > 0, not NaN, not Inf |
| 2 | calc_salary (hours, rate, bonuses) | test_salary_calc.py | result >= 0, корректный тип |
| 3 | date_utils (parse, format, diff) | test_date_utils.py | round-trip: parse(format(d)) == d |
| 4 | norm_days calculation | test_norm_days.py | 0 <= result <= 31, int |

**Acceptance Criteria:**
1. Hypothesis выполняет минимум 100 примеров на каждый тест
2. Ни одна расчётная функция не возвращает NaN, Inf, отрицательные значения
3. Ни одна функция не бросает необработанное исключение на граничных входных данных
4. При нахождении бага — Hypothesis предоставляет minimal failing example
5. `.hypothesis/` в .gitignore (уже есть)

**Стратегии входных данных:**
```
Области:     st.floats(min_value=0.1, max_value=50000.0)
Тарифы:      st.floats(min_value=1.0, max_value=500000.0)
Часы:        st.integers(min_value=0, max_value=744)
Даты:        st.dates(min_value=date(2020,1,1), max_value=date(2030,12,31))
Проценты:    st.floats(min_value=0.0, max_value=100.0)
```

### Слой 5: Visual Regression (QWidget.grab())

| Параметр | Значение |
|----------|---------|
| **Покрываемые модули** | Ключевые виджеты: вкладки, диалоги, таблицы |
| **Среда** | Python 3.14, QT_QPA_PLATFORM=offscreen |
| **Запуск** | CI: weekly job. Ручной: `pytest tests/visual/ -v` |
| **Создаваемые файлы** | `tests/visual/conftest.py`, `tests/visual/test_widget_snapshots.py` |

**Покрываемые виджеты:**

| # | Виджет | Baseline файл | Что ловит |
|---|--------|--------------|-----------|
| 1 | CRM Kanban | crm_tab.png | Поехавшие колонки, наложение |
| 2 | Диалог договора | contract_dialog.png | Исчезнувшие поля |
| 3 | Таблица зарплат | salaries_tab.png | Смещение столбцов |
| 4 | Timeline | timeline_widget.png | Сломанная шкала |
| 5 | Dashboard графики | dashboard_charts.png | Пустые графики |

**Acceptance Criteria:**
1. QWidget.grab() создаёт непустой QPixmap (size > 0x0)
2. Pixel diff с baseline < 5% (порог для шрифтовых вариаций)
3. При обновлении baseline — обязательный ручной визуальный контроль
4. Baseline хранятся в git (tests/visual/baselines/)
5. Текущие снимки — в gitignore (tests/visual/snapshots/)
6. Offscreen рендеринг корректен (не пустой чёрный прямоугольник)

**Механизм сравнения:**
```
1. QWidget.grab() → QPixmap → .save() PNG
2. Pillow Image.open() текущий + baseline
3. ImageChops.difference() → diff image
4. Подсчёт непрозрачных пикселей diff / total pixels
5. Если > 5% — FAIL + сохранить diff.png для анализа
```

---

## 5. Структура файлов — полная карта

```
tests/
├── fuzz/                              # НОВОЕ: Schemathesis API fuzzing
│   ├── __init__.py
│   ├── conftest.py                    # BASE_URL, JWT auth, server check
│   ├── test_schemathesis_all.py       # Автогенерация из OpenAPI
│   └── schemathesis.yaml              # Конфиг: исключения, лимиты, таймауты
│
├── smoke/                             # РАСШИРЕНИЕ: умные assertions
│   ├── test_data_validation.py        # НОВОЕ: проверка ЗНАЧЕНИЙ (area>0, amount>0)
│   ├── test_orphan_records.py         # НОВОЕ: сиротские записи
│   ├── test_business_rules.py         # РАСШИРИТЬ: area*rate=amount
│   ├── test_dashboard_accuracy.py     # РАСШИРИТЬ: dashboard = реальные данные
│   ├── test_critical_workflows.py     # Без изменений (уже хорошие)
│   └── ...                            # Остальные smoke без изменений
│
├── ui_real/                           # НОВОЕ: реальные UI тесты
│   ├── __init__.py
│   ├── conftest.py                    # qtbot + real DataAccess + skip_if_no_server
│   ├── test_crm_tab_real.py           # CRM Kanban
│   ├── test_contract_dialog.py        # Диалог договора
│   ├── test_crm_card_dialog.py        # Диалог CRM-карточки
│   ├── test_salaries_real.py          # Вкладка зарплат
│   ├── test_supervision_real.py       # Авторский надзор
│   ├── test_payments_real.py          # Таблица оплат
│   ├── test_dashboard_real.py         # Dashboard
│   ├── test_rates_dialog.py           # Диалог тарифов
│   ├── test_login_real.py             # Окно логина
│   └── test_reports_real.py           # Отчёты
│
├── property/                          # НОВОЕ: Hypothesis property-based
│   ├── __init__.py
│   ├── conftest.py                    # Стратегии: area, rate, date, hours
│   ├── test_payment_calc.py           # Расчёт оплат
│   ├── test_salary_calc.py            # Расчёт зарплат
│   ├── test_date_utils.py             # Утилиты дат
│   └── test_norm_days.py              # Нормо-дни
│
├── visual/                            # РАСШИРЕНИЕ: regression + baselines
│   ├── __init__.py
│   ├── conftest.py                    # НОВОЕ: offscreen setup, grab helpers, diff
│   ├── test_widget_snapshots.py       # НОВОЕ: QWidget.grab() + сравнение
│   ├── baselines/                     # НОВОЕ: эталонные снимки (в git)
│   │   ├── crm_tab.png
│   │   ├── contract_dialog.png
│   │   ├── salaries_tab.png
│   │   ├── timeline_widget.png
│   │   └── dashboard_charts.png
│   ├── snapshots/                     # Текущие снимки (в gitignore)
│   ├── full_ui_test.py                # Существующий (без изменений)
│   ├── visual_tester.py               # Существующий (без изменений)
│   └── auto_test.py                   # Существующий (без изменений)
│
├── integration/                       # НОВОЕ: pywinauto запущенное приложение
│   ├── __init__.py
│   ├── conftest.py                    # app launch, auto-login, timeout=600
│   └── test_running_app.py            # Вкладки, таблицы, кнопки (< 10 мин)
│
├── ui/                                # БЕЗ ИЗМЕНЕНИЙ: мок-тесты (CI regression)
├── client/                            # БЕЗ ИЗМЕНЕНИЙ: unit-тесты
├── db/                                # БЕЗ ИЗМЕНЕНИЙ: SQLite тесты
├── e2e/                               # БЕЗ ИЗМЕНЕНИЙ: E2E интеграция
├── contract/                          # БЕЗ ИЗМЕНЕНИЙ: API контракты
└── conftest.py                        # Без изменений
```

**Обновления вне tests/:**

| Файл | Действие |
|------|----------|
| `requirements-dev.txt` | Добавить: `schemathesis>=3.30`, `hypothesis>=6.0`, `pywinauto>=0.6.8` |
| `.gitignore` | Добавить: `tests/visual/snapshots/` |
| `pytest.ini` | Добавить маркеры: `fuzz`, `ui_real`, `property`, `visual`, `integration` |
| `.github/workflows/ci.yml` | Добавить jobs: test-fuzz, test-property, test-visual |

---

## 6. Зависимости и совместимость

### Матрица совместимости

| Зависимость | Версия | Python | Среда | Статус |
|-------------|--------|--------|-------|--------|
| **schemathesis** | >=3.30 | 3.11 (серверный) | CI + ручной | Новая установка |
| **hypothesis** | >=6.0 | 3.14 (клиентский) | CI + ручной | Новая установка |
| **pytest-qt** | >=4.4.0 | 3.14 (клиентский) | CI (offscreen) | Уже установлен |
| **Pillow** | (текущая) | 3.14 (клиентский) | CI + ручной | Уже установлен |

### Критические ограничения

**Schemathesis на Python 3.11:**
- Schemathesis зависит от `jsonschema`, `requests`, `hypothesis` — все совместимы с 3.11
- НЕ запускать на Python 3.14 (клиентский) — возможны проблемы совместимости с экспериментальной версией Python
- В CI: отдельный job с Python 3.11

**Hypothesis на Python 3.14:**
- Hypothesis 6.x поддерживает последние версии Python
- Проверить совместимость при первом запуске, при проблемах — закрепить версию
- `.hypothesis/` директория уже существует в проекте и untracked

**QT_QPA_PLATFORM=offscreen для CI:**
- Обязателен для pytest-qt и QWidget.grab() в headless CI
- Установить в CI environment: `QT_QPA_PLATFORM: offscreen`
- На Windows dev-машине: не требуется (есть GUI)
- На Linux CI: требуется `xvfb` или `offscreen` platform plugin
- Проверить что offscreen рендеринг даёт корректные снимки (не чёрные прямоугольники)

**Auto-skip при недоступности сервера:**
- `tests/ui_real/` и `tests/smoke/` — auto-skip если сервер не отвечает
- Паттерн из существующих smoke-тестов: `pytest.skip("Сервер недоступен")`
- CI job для этих тестов помечается как `continue-on-error: true`

### CI интеграция — новые jobs

| Job | Когда запускается | Python | Зависит от |
|-----|-------------------|--------|------------|
| test-fuzz | После деплоя (ручной trigger) | 3.11 | Работающий сервер |
| test-property | Каждый push | 3.14 | Ничего (чистые функции) |
| test-ui-real | Каждый push | 3.14 + offscreen | Работающий сервер (auto-skip) |
| test-visual | Weekly + ручной | 3.14 + offscreen | Ничего |

**Порядок добавления в CI:**
1. `test-property` — без зависимостей, добавляется сразу
2. `test-visual` — offscreen, добавляется вторым
3. `test-ui-real` — зависит от сервера, auto-skip
4. `test-fuzz` — последний, ручной trigger после деплоя

---

## 7. Метрики успеха (acceptance criteria проекта)

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

## 8. Слой 6: pywinauto — Integration Testing запущенного приложения (до 10 минут)

### ADR-5: pywinauto с жёстким ограничением времени

| Параметр | Решение |
|----------|---------|
| **Статус** | Принято (с условием) |
| **Контекст** | Ранее pywinauto отнимал фокус машины на неопределённое время, блокировал работу. Пользователь согласен на блокировку НЕ БОЛЕЕ 10 минут. |
| **Решение** | pywinauto accessibility tree + жёсткий timeout 10 минут на весь прогон |
| **Ограничения** | (1) Только ручной запуск (НЕ CI). (2) Timeout 10 мин = hard kill. (3) Только быстрые проверки: видимость элементов, наличие данных в таблицах, кликабельность кнопок. (4) НЕ пытаться вводить текст или навигировать сложные диалоги. |
| **Последствия** | `tests/integration/` — новая директория. pywinauto в requirements-dev.txt. Запуск: `pytest tests/integration/ -v --timeout=600` |

### Детализация слоя 6

| Параметр | Значение |
|----------|---------|
| **Покрываемые модули** | Запущенное приложение: главное окно, навигация, таблицы |
| **Среда** | Windows с GUI, Python 3.14 |
| **Запуск** | Только ручной: `pytest tests/integration/ -v --timeout=600` |
| **Создаваемые файлы** | `tests/integration/conftest.py`, `tests/integration/test_running_app.py` |

**Сценарий прогона (укладывается в 10 минут):**
1. Запуск `main.py` (30 сек на загрузку)
2. Автологин через Qt inject (10 сек)
3. Проверка главного окна: все вкладки существуют (30 сек)
4. Обход 6 вкладок: проверка что таблицы не пустые (3 мин)
5. Открытие 3 ключевых диалогов: проверка что поля заполнены (2 мин)
6. Закрытие приложения (10 сек)
7. **Итого: ~6-7 минут** (запас 3-4 минуты)

**Acceptance Criteria:**
1. Весь прогон завершается за < 10 минут (hard timeout)
2. Главное окно открывается после логина
3. Все основные вкладки доступны через accessibility tree
4. Таблицы содержат > 0 строк данных
5. Ключевые кнопки кликабельны (enabled + visible)
6. Приложение не крашится за время прогона

**Технический подход:**
```
# backend="uia" для Qt5 accessibility
from pywinauto import Application
app = Application(backend="uia").connect(title_re="Festival.*")

# Быстрые проверки через accessibility tree (НЕ координатные клики):
main_window = app.window(title_re="Festival.*")
assert main_window.exists(), "Главное окно не найдено"

# Проверка вкладок через child_window
tabs = main_window.child_window(control_type="TabControl")
assert tabs.tab_count() >= 5, "Не все вкладки загрузились"

# Проверка таблиц через DataGrid/Table
table = main_window.child_window(control_type="Table")
assert table.item_count() > 0, "Таблица пуста"
```

---

## 9. Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|------------|---------|-----------|
| Schemathesis не совместим с Python 3.14 | Высокая | Низкое | Запускать на 3.11 (серверный) |
| Offscreen рендеринг отличается от экранного | Средняя | Среднее | Отдельные baseline для CI, порог 5% |
| Flaky тесты при сетевых запросах в ui_real | Высокая | Среднее | Retry логика, timeout 10s, auto-skip |
| Baseline снимки устаревают при UI-изменениях | Средняя | Низкое | Команда обновления: `pytest tests/visual/ --update-baseline` |
| Hypothesis находит слишком много edge cases | Низкая | Низкое | `@settings(max_examples=200)` — ограничить |
| pywinauto превышает 10 минут | Средняя | Среднее | Hard timeout `--timeout=600`, kill процесса, минимальный набор проверок |
| pywinauto не находит элементы через UIA | Средняя | Среднее | `QT_USE_NATIVE_WINDOWS=1`, fallback на Qt accessibility bridge |
