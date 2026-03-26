# Исследование: Перестройка тестирования Interior Studio CRM

**Дата:** 2026-03-06
**Проблема:** 8997 тестов не ловят реальные баги, которые находят пользователи
**Инструменты исследования:** /feature-research, 4 субагента, GitHub MCP, Context7 MCP, WebSearch

---

## 1. Диагноз: ТРИ уровня проблемы

### Проблема 1: 73% тестов — моки (6590 из 8997)

| Категория | Тестов | % | Реальность |
|-----------|--------|---|------------|
| Client (моки `_request()`) | 3701 | 41% | Проверяют что клиент ФОРМИРУЕТ запрос, не что сервер ОТВЕЧАЕТ |
| UI (моки DataAccess) | 2889 | 32% | Проверяют что виджет СОЗДАЁТСЯ, не что он РАБОТАЕТ |
| **Итого бесполезных** | **6590** | **73%** | **Никогда не найдут реальный баг** |

**Что делать с 6590 мок-тестами:** НЕ удалять. Они нужны для CI — ловят regression при рефакторинге. Но добавить поверх них РЕАЛЬНЫЕ тесты.

### Проблема 2: Smoke/E2E тесты проверяют HTTP-коды, а не данные

Точный анализ smoke/e2e тестов (субагент Explore):
- **603 assertions** на `status_code` — "сервер ответил 200/404/422"
- **427 assertions** на типы/структуру — `isinstance(data, list)`
- **49 assertions** на реальные значения данных — "area > 0, amount правильный"
- **0 assertions** на "что видит пользователь в UI"

Итого: **92% проверок бесполезны** для нахождения бизнес-багов.

**Пример типичного smoke-теста (бесполезного):**
```python
def test_get_clients(self, admin_headers):
    resp = self.session.get(f"{BASE}/api/clients", headers=admin_headers)
    assert resp.status_code == 200  # Сервер ответил — ОК
    assert isinstance(resp.json(), list)  # Вернул список — ОК
    # НО: area=0? total_amount=None? Имя пустое? — НЕ ПРОВЕРЯЕТСЯ
```

**Пример полезного smoke-теста (которых почти нет):**
```python
def test_contract_has_valid_data(self, admin_headers):
    contracts = self.get("/api/contracts").json()
    for c in contracts[:10]:
        assert c["area"] > 0, f"Договор {c['id']} — area=0!"
        assert c["total_amount"] > 0, f"Договор {c['id']} — сумма=0!"
        assert c["client_id"] is not None, f"Договор {c['id']} без клиента!"
```

### Проблема 3: Ни один тест не видит ЧТО ВИДИТ ПОЛЬЗОВАТЕЛЬ

Пользователь говорит: "Дата не вводится в поле". Тест проверяет:
- API тест: "endpoint /api/contracts/{id} возвращает `deadline: '2026-03-01'`" — PASS
- UI мок-тест: "виджет `QDateEdit` существует в диалоге" — PASS
- **НО:** на реальном экране `QDateEdit` невидим потому что перекрыт другим виджетом

**Ни smoke, ни e2e, ни UI тесты НЕ могут это обнаружить**, потому что:
- Smoke/E2E — тестируют только API, не видят UI
- UI моки — виджет создаётся в памяти, не рендерится реально
- `tests/visual/` — делают скриншоты, но НЕ проверяют что на них

---

## 2. Что уже есть в проекте (Фаза 4: сканирование)

### tests/visual/ — зачатки визуального тестирования

| Файл | Подход | Что делает | Проверяет данные? |
|------|--------|-----------|-------------------|
| `visual_tester.py` | PyAutoGUI | Скриншоты + клики по координатам | НЕТ |
| `full_ui_test.py` | QTest + Qt API | Вход -> навигация -> скриншоты | НЕТ |
| `auto_test.py` | Win32 SendInput | Ввод текста + клики | НЕТ |
| `qt_auto_login.py` | Qt inject | `setText()` + `click()` | НЕТ |

**Вывод:** Инфраструктура для UI-тестирования ЕСТЬ, но она только делает скриншоты. Нужно добавить ПРОВЕРКИ.

### Зависимости уже установлены
- `pytest-qt>=4.4.0` — qtbot для реального UI
- `pyautogui` — скриншоты + поиск на экране
- `Pillow` — работа с изображениями
- `keyboard`, `pyperclip` — ввод текста

### Проблема 3 (детали): 5 критических GAP-ов

| GAP | Что проверяют тесты | Что НЕ ловится |
|-----|---------------------|-----------------|
| **HTTP vs DATA** | `status_code == 200` | Значения в JSON неправильные (area=0, amount=null) |
| **API vs UI** | Мокируют DataAccess | Реальный UI падает когда DataAccess вернул None |
| **Структура vs Видимость** | Поля существуют в объекте | Пользователь НЕ видит данные на экране |
| **Unit vs Integration** | Каждый компонент отдельно | Цепочка API->DataAccess->UI сломана в середине |
| **Auto vs Manual** | Smoke в CI auto-run | Data consistency — ручной запуск, забывают |

**Конкретный пример пропущенного бага:**
```python
# В UI коде:
cards = self.data.get_crm_cards()  # возвращает None (ошибка БД)
for card in cards:  # TypeError: NoneType is not iterable
    ...

# В тесте:
mock_data_access.get_crm_cards.return_value = [...]  # никогда не вернёт None!
# Тест проходит, на production падает
```

---

## 3. Найденные решения

### Решение 1: Schemathesis — автоматический фаззинг API (КРИТИЧНО)

**Релевантность: 10/10**

| Параметр | Значение |
|----------|---------|
| GitHub | [schemathesis/schemathesis](https://github.com/schemathesis/schemathesis) (2100+ stars) |
| Что делает | Генерирует тысячи тестов из OpenAPI spec FastAPI |
| Находит | 500 ошибки, нарушения схемы, edge cases, валидация |
| Статистика | 5-15 багов на первом прогоне, 1.4x-4.5x больше чем другие |
| Установка | `pip install schemathesis` |
| Запуск | `st run http://server:8000/openapi.json --base-url http://server:8000` |

**Почему это критично:** Наши smoke-тесты проверяют `status_code == 200` для happy path. Schemathesis отправляет тысячи НЕВАЛИДНЫХ запросов и находит когда сервер отвечает 500 вместо 400/422. Это ИМЕННО те баги что находят пользователи — "ввёл неправильные данные и всё сломалось".

### Решение 2: pytest-qt qtbot — РЕАЛЬНОЕ UI тестирование (КРИТИЧНО)

**Релевантность: 9/10**

Уже установлен! Но используется только для:
```python
# Текущее использование (бесполезное):
dialog = SomeDialog(parent=None, api_client=MagicMock())
assert dialog.tabs.count() == 5
```

**Нужное использование:**
```python
# РЕАЛЬНОЕ тестирование с qtbot:
def test_contract_dialog_shows_data(qtbot, real_api_client):
    dialog = ContractEditDialog(contract_id=123, api_client=real_api_client)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitUntil(lambda: dialog.area_input.text() != "", timeout=5000)

    # Проверяем что РЕАЛЬНЫЕ данные загрузились
    assert float(dialog.area_input.text()) > 0, "Площадь не загрузилась!"
    assert dialog.client_combo.currentText() != "", "Клиент не выбран!"
    assert dialog.date_edit.isVisible(), "Поле даты не видно!"
```

### Решение 3: Claude Code + Скриншоты — AI-анализ UI (ИННОВАЦИЯ)

**Релевантность: 9/10**

Claude Code умеет ЧИТАТЬ изображения. Стратегия:
1. `tests/visual/full_ui_test.py` делает скриншоты каждой вкладки/диалога
2. Claude Code читает скриншоты через `Read` tool
3. Claude Code анализирует: "На этом скриншоте поле даты пустое, хотя в API данные есть"

**Это УНИКАЛЬНОЕ преимущество** — ни один инструмент не может так. Claude видит то же что пользователь.

### Решение 4: Hypothesis — property-based тестирование расчётов

**Релевантность: 8/10**

```python
from hypothesis import given, strategies as st

@given(area=st.floats(min_value=0.1, max_value=10000),
       rate=st.floats(min_value=100, max_value=100000))
def test_payment_always_positive(area, rate):
    result = calculate_payment(area, rate)
    assert result > 0, f"area={area}, rate={rate} => result={result}"
    assert not math.isnan(result), f"NaN при area={area}, rate={rate}"
```

Находит: деление на 0, NaN, overflow, отрицательные суммы — edge cases которые человек не придумает.

### Решение 5: Playwright MCP — для API тестирования (НЕ для UI)

**Релевантность: 6/10**

Ты правильно заметил — Playwright для БРАУЗЕРА, а наш проект десктопный PyQt5. НО:
- Playwright MCP может тестировать FastAPI Swagger UI (`/docs`)
- Может проверять что документация API актуальна
- НЕ подходит для тестирования самого десктоп-приложения

**Вердикт:** Подключить, но как вспомогательный инструмент для API, не как основной.

---

### Решение 6: Headless Visual Testing — QWidget.grab() + Claude AI анализ

**Релевантность: 7/10**

**Проблема с pywinauto (проверено на практике):**
pywinauto отнимает фокус у машины, блокирует работу пользователя, клики попадают не туда.
Синхронизация тестов с живым приложением не работала.

**Замена — двухуровневый подход БЕЗ захвата фокуса:**

**Уровень A: QWidget.grab() через pytest-qt (headless, в CI)**
```python
def test_contract_dialog_visual(qtbot, real_data_access):
    """Визуальная проверка диалога договора — БЕЗ отображения на экране."""
    dialog = ContractEditDialog(contract_id=123, data=real_data_access)
    qtbot.addWidget(dialog)
    dialog.load_data()
    qtbot.waitUntil(lambda: dialog.area_input.text() != "", timeout=5000)

    # Снимок виджета из памяти — не требует фокуса/экрана
    pixmap = dialog.grab()
    pixmap.save(f"tests/visual/snapshots/contract_dialog_{contract_id}.png")

    # Сравнение с эталоном
    from PIL import Image
    current = Image.open(f"tests/visual/snapshots/contract_dialog_{contract_id}.png")
    baseline = Image.open(f"tests/visual/baselines/contract_dialog.png")
    diff = ImageChops.difference(current, baseline)
    assert diff.getbbox() is None or pixel_diff_percent(diff) < 5.0
```
- Работает в CI headless (QT_QPA_PLATFORM=offscreen)
- Не блокирует машину, не нужен фокус
- Ловит: "поехала" таблица, наложение текста, исчез элемент

**Уровень B: Ручной visual QA через Claude Code (по запросу)**
1. Запустить `tests/visual/full_ui_test.py` — делает скриншоты реального приложения
2. Claude Code читает скриншоты и анализирует: "поле пустое", "кнопка не видна"
3. Скилл `/qa-visual` для запуска
4. Выполняется ТОЛЬКО по запросу, когда пользователь не работает за машиной

---

## 4. Что НЕ подходит

| Инструмент | Почему не подходит |
|------------|-------------------|
| Selenium/Playwright | Для браузера, не для PyQt5 десктопа |
| Appium/WinAppDriver | WinAppDriver **заморожен Microsoft**, Qt-совместимость плохая (2/10) |
| testRigor | SaaS платный, тестирует через RDP, русский UI — проблема (4/10) |
| Squish for Qt | $15000/год, закрытый код |
| PyAutoGUI locateOnScreen | Хрупкий — зависит от DPI, темы, разрешения |
| Claude Code MCP (AI Testing) | MCP-экосистема заточена под веб, нет MCP для Qt (3/10) |
| **pywinauto (управление)** | **Отнимает фокус у машины, блокирует работу, клики не попадают** |

---

## 5. Рекомендуемый подход (5 слоёв)

### Слой 1: API Fuzzing (Schemathesis) — находит серверные баги

```bash
pip install schemathesis
st run https://fc-interior.ru/openapi.json --checks all --stateful=links
```

- Автоматически генерирует тысячи запросов
- Находит 500, нарушения схемы, невалидные ответы
- Запускается в CI после каждого деплоя
- **Ожидаемый результат: 5-15 багов на первом прогоне**

### Слой 2: Умные Smoke-тесты — проверяют ДАННЫЕ, не коды

Переписать существующие smoke-тесты: вместо `status_code == 200` проверять:
- Все обязательные поля не null
- area > 0, total_amount > 0 для договоров
- Нет сиротских записей (карточка без договора)
- Dashboard цифры = реальным данным
- Расчёты оплат корректны (area * rate = amount)

### Слой 3: Реальное UI тестирование — qtbot + DataAccess

Переписать ключевые UI-тесты:
- Вместо `MagicMock()` — реальный DataAccess (с real API или тестовой БД)
- Проверять что данные загрузились в виджеты
- Проверять что кнопки РАБОТАЮТ (не просто существуют)
- Проверять видимость элементов

### Слой 4: pywinauto — тестирование запущенного приложения

Тесты на РЕАЛЬНО запущенном приложении через accessibility tree:
- Запустить `main.py` -> авторизоваться -> обойти все вкладки
- Проверить что таблицы содержат данные
- Проверить что кнопки кликабельны
- Проверить что диалоги открываются и закрываются
- Минус: требует Windows с GUI, не CI-headless
- **Файлы:** `tests/integration/`, `requirements-dev.txt`

### Слой 5: Visual Regression + AI анализ

Два подхода:

**A) Widget-level visual regression (автоматический):**
```python
# Захват скриншота конкретного виджета (не всего экрана)
pixmap = dialog.grab()  # QWidget.grab() — точный снимок виджета
pixmap.save("baseline/contract_dialog.png")
# При следующем запуске — сравнение через Pillow/pixelmatch
```
- Не зависит от DPI, положения окна, других окон
- Ловит визуальные регрессии: "поехала" таблица, наложение текста

**B) AI Visual QA через Claude Code (ручной):**
1. `tests/visual/full_ui_test.py` обходит ВСЕ вкладки и диалоги
2. Делает скриншоты каждого состояния
3. Claude Code читает скриншоты и анализирует: "поле пустое", "кнопка не видна"
4. Скилл `/qa-visual` для запуска

---

## 6. Новые зависимости

| Библиотека | Версия | Зачем | pip install |
|------------|--------|-------|-------------|
| schemathesis | >=3.30 | API fuzzing по OpenAPI | `pip install schemathesis` |
| hypothesis | >=6.0 | Property-based testing | `pip install hypothesis` |
| pywinauto | >=0.6.8 | Accessibility tree UI тесты | `pip install pywinauto` |

Уже установлены:
- pytest-qt >= 4.4.0
- pyautogui
- Pillow

---

## 7. Конфликты с проектом

- **Python 3.14 (клиент):** Schemathesis может не поддерживать 3.14 — проверить. Запускать на сервере (3.11).
- **Hypothesis + .hypothesis/:** Папка уже есть в проекте (git untracked) — добавить в .gitignore.
- **Visual тесты требуют экран:** Не запускаются в headless CI. Запускать на Windows машине.

---

## 8. План разработки

### Шаг 1: Schemathesis — API fuzzing (1 день)
- Установить `schemathesis` на сервер
- Запустить `st run` против production API
- Собрать и исправить найденные баги
- Добавить в CI (GitHub Actions)
- **Файлы:** `tests/fuzz/`, `requirements-dev.txt`, CI workflow

### Шаг 2: Переписать smoke-тесты на проверку данных (2-3 дня)
- Добавить assertions на значения, не только status_code
- Создать `tests/smoke/test_data_validation.py` — обход ВСЕХ сущностей
- Добавить бизнес-правила: area*rate=amount, deadline > created_at, etc.
- **Файлы:** `tests/smoke/test_data_validation.py`, `tests/smoke/conftest.py`

### Шаг 3: Реальные UI тесты через qtbot (3-5 дней)
- Выбрать 20 ключевых диалогов/вкладок
- Для каждого: создать тест с реальным DataAccess
- Проверять: данные загрузились, кнопки работают, поля видны
- **Файлы:** `tests/ui_real/`, `tests/ui_real/conftest.py`

### Шаг 4: AI Visual QA скилл (2 дня)
- Расширить `tests/visual/full_ui_test.py` — полный обход всех экранов
- Создать скилл `/qa-visual` — запуск + анализ скриншотов Claude Code
- Интегрировать с Telegram уведомлениями
- **Файлы:** `.claude/skills/qa-visual/SKILL.md`, `tests/visual/`

### Шаг 5: Hypothesis property-based (1 день)
- Покрыть ВСЕ расчётные функции (оплаты, зарплаты, тарифы)
- Найти edge cases с NaN, 0, отрицательными
- **Файлы:** `tests/property/`

### Шаг 6: Мониторинг production (1 день)
- Cron-скрипт на сервере каждые 30 мин
- Health + ключевые endpoints + бизнес-правила
- Telegram алерт при ошибке
- **Файлы:** `tests/smoke/run_post_deploy.py`, crontab

---

## 9. Чеклист верификации

- [ ] Schemathesis находит баги на production API
- [ ] Smoke-тесты проверяют ЗНАЧЕНИЯ данных (area > 0, amount > 0)
- [ ] UI-тесты загружают РЕАЛЬНЫЕ данные в виджеты
- [ ] Visual тесты делают скриншоты ВСЕХ экранов
- [ ] Claude Code может прочитать скриншоты и найти проблемы
- [ ] Hypothesis находит edge cases в расчётах
- [ ] Мониторинг production шлёт алерты при ошибках

---

## 10. Метрики успеха

| Метрика | Сейчас | Цель (1 месяц) |
|---------|--------|-----------------|
| Тесты на реальном сервере | 1222 | 2000+ |
| Assertions на данные (не status_code) | ~22 | 500+ |
| API fuzzing (Schemathesis) | 0 | автоматически |
| UI тесты с реальными данными | 0 | 100+ |
| Баги найденные ДО пользователя | ~0% | >50% |
