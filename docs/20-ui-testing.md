# UI тесты — pytest-qt offscreen

> Автоматизированное тестирование всех Qt виджетов Interior Studio CRM
> с помощью [pytest-qt](https://pytest-qt.readthedocs.io/) в headless режиме (`QT_QPA_PLATFORM=offscreen`).

**Всего: 460 тестов | 13 файлов тестов + conftest.py | ~3 500 строк кода**
**Время прогона: ~1 мин 42 сек**

---

## Содержание

- [Архитектура](#архитектура)
- [Ключевые особенности](#ключевые-особенности)
- [Структура файлов](#структура-файлов)
- [Запуск тестов](#запуск-тестов)
- [Инфраструктура (conftest.py)](#инфраструктура-conftestpy)
- [Покрытие по модулям](#покрытие-по-модулям)
- [Матрица ролей](#матрица-ролей)
- [Паттерны тестирования](#паттерны-тестирования)
- [Безопасность](#безопасность)

---

## Архитектура

```
┌────────────────────────────────────────────────────────────────┐
│                      pytest runner                              │
│  pytest tests/ui/ -v --timeout=30                              │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  QT_QPA_PLATFORM=offscreen      ← Headless, без окон           │
│  pytest-qt (qtbot)              ← Управление Qt виджетами       │
│  unittest.mock (patch)          ← Изоляция от БД/API/Я.Диск    │
│  tmp_path                       ← Изолированная SQLite БД       │
│                                                                  │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  conftest.py                    ← Фикстуры: 11 ролей, БД,     │
│                                    safety-net блокировки        │
│                                                                  │
│  12 тестовых файлов:                                            │
│  ├── test_login.py              (14)  Авторизация               │
│  ├── test_data_access.py        (17)  DataAccess CRUD           │
│  ├── test_clients.py            (36)  Клиенты                   │
│  ├── test_main_window.py        (18)  Главное окно              │
│  ├── test_contracts.py          (44)  Договора                  │
│  ├── test_employees.py          (30)  Сотрудники                │
│  ├── test_crm.py                (92)  CRM Kanban                │
│  ├── test_crm_supervision.py    (40)  CRM Надзора               │
│  ├── test_salaries.py           (34)  Зарплаты                  │
│  ├── test_dashboard.py          (14)  Дашборд                   │
│  ├── test_reports.py            (8)   Отчёты                    │
│  └── test_roles.py              (95)  Ролевой доступ            │
│                                                                  │
│  ИТОГО: 460 тестов, 100% PASSED                                  │
└────────────────────────────────────────────────────────────────┘
```

### Преимущества перед pywinauto

| Критерий | pywinauto (было) | pytest-qt (стало) |
|----------|:----------------:|:-----------------:|
| Фокус окна | Требует реальный | Не нужен (offscreen) |
| CI/CD | Невозможно | Работает в CI |
| Скорость | ~5 мин (108 тестов) | ~1:50 (460 тестов) |
| Стабильность | Нестабильно (таймауты) | 100% стабильно |
| Изоляция БД | Нет (production SQLite) | tmp_path (изолировано) |
| Покрытие | 108 тестов | 460 тестов (+326%) |

---

## Ключевые особенности

1. **Headless** — `QT_QPA_PLATFORM=offscreen`, без окон и фокуса
2. **Изоляция БД** — каждый тест получает tmp_path SQLite, production БД не затрагивается
3. **Safety-net** — autouse фикстуры блокируют реальные HTTP запросы и production БД
4. **11 ролей** — фикстуры для 9 должностей + 2 двойные роли
5. **Mock DataAccess** — все CRUD через MagicMock, нет побочных эффектов
6. **Ролевое тестирование** — 95 тестов проверяют доступ каждой роли

---

## Структура файлов

```
tests/ui/
├── __init__.py
├── conftest.py                    # Инфраструктура + 11 фикстур ролей + safety-net
├── test_login.py                  # 14 тестов — Авторизация
├── test_data_access.py            # 17 тестов — DataAccess CRUD
├── test_clients.py                # 36 тестов — Клиенты (диалоги, поля, валидация)
├── test_main_window.py            # 18 тестов — Главное окно (табы, навигация)
├── test_contracts.py              # 44 теста — Договора (типы, подтипы, поля)
├── test_employees.py              # 30 тестов — Сотрудники (CRUD, должности)
├── test_crm.py                    # 92 теста — CRM Kanban (карточки, стадии, дедлайны)
├── test_crm_supervision.py        # 40 тестов — CRM Надзора (12 стадий, ДАН)
├── test_salaries.py               # 34 теста — Зарплаты (5 вкладок, диалоги)
├── test_dashboard.py              # 14 тестов — Дашборд (6 карточек, метрики)
├── test_reports.py                # 8 тестов — Отчёты (4 вкладки, фильтры)
└── test_roles.py                  # 95 тестов — Ролевой доступ (9+2 роли)
```

---

## Запуск тестов

```bash
# Установка зависимостей
pip install pytest-qt pytest-timeout

# Полный прогон (460 тестов, ~1:50)
pytest tests/ui/ -v --timeout=30

# Конкретный файл
pytest tests/ui/test_crm.py -v --timeout=30

# Только ролевые тесты
pytest tests/ui/test_roles.py -v --timeout=30

# С покрытием
pytest tests/ui/ -v --timeout=30 --cov=ui --cov-report=html
```

---

## Инфраструктура (conftest.py)

### Safety-net: блокировка production

```python
@pytest.fixture(autouse=True)
def _block_real_db(monkeypatch):
    """Блокирует создание DatabaseManager с реальным путём к production БД."""
    # Разрешаем только tmp-пути и :memory:
    # Любая попытка открыть production БД → RuntimeError

@pytest.fixture(autouse=True)
def _block_real_api(monkeypatch):
    """Блокирует реальные HTTP-запросы к серверу из тестов."""
    # requests.get/post/put/delete/patch → RuntimeError
```

### Фикстуры БД

| Фикстура | Назначение | Очистка |
|----------|-----------|---------|
| `test_db(tmp_path)` | Изолированная SQLite в tmp_path | Автоматически (pytest) |
| `data_access(test_db)` | DataAccess с реальной tmp БД | Автоматически |
| `mock_data_access()` | MagicMock DataAccess | Память (GC) |

### Фикстуры ролей (11 штук)

| Фикстура | Должность | Уровень |
|----------|-----------|---------|
| `mock_employee_admin` | Руководитель студии | Полный |
| `mock_employee_senior_manager` | Старший менеджер проектов | Полный |
| `mock_employee_sdp` | СДП | Управленческий |
| `mock_employee_gap` | ГАП | Управленческий |
| `mock_employee_manager` | Менеджер | Управленческий |
| `mock_employee_designer` | Дизайнер | Исполнительский |
| `mock_employee_draftsman` | Чертёжник | Исполнительский |
| `mock_employee_surveyor` | Замерщик | Исполнительский |
| `mock_employee_dan` | ДАН | Надзор (read-only) |
| `mock_employee_designer_manager` | Дизайнер + Менеджер | Двойная |
| `mock_employee_designer_draftsman` | Дизайнер + Чертёжник | Двойная |

### Фикстуры данных

| Фикстура | Описание |
|----------|----------|
| `sample_client_individual` | Физическое лицо |
| `sample_client_legal` | Юридическое лицо (ООО) |
| `sample_contract_individual` | Индивидуальный договор |
| `sample_contract_template` | Шаблонный договор |
| `sample_crm_card` | CRM карточка |
| `sample_employee` | Сотрудник |
| `parent_widget` | QWidget с mock данными |

---

## Покрытие по модулям

### test_login.py — 14 тестов

| Класс | Тестов | Покрытие |
|-------|:------:|----------|
| TestLoginWindowRendering | 8 | Создание, поля, кнопки, frameless |
| TestLoginAuthentication | 6 | Пустые поля, неверный пароль, offline вход |

### test_data_access.py — 17 тестов

| Класс | Тестов | Покрытие |
|-------|:------:|----------|
| TestDataAccessWithDB | 11 | CRUD клиенты/контракты/сотрудники с tmp БД |
| TestDataAccessMock | 6 | Mock DataAccess без БД |

### test_clients.py — 36 тестов

| Класс | Тестов | Покрытие |
|-------|:------:|----------|
| TestClientsTabRendering | 6 | Таблица, кнопки, колонки |
| TestClientDialogRendering | 8 | Диалог добавления/редактирования |
| TestClientDynamicFields | 6 | Переключение физ./юр. лицо |
| TestClientValidation | 8 | Пустые поля, спецсимволы, длинные имена |
| TestClientCRUD | 6 | Создание, обновление, целостность данных |
| TestClientSearch | 2 | Поиск по имени, пустой поиск |

### test_main_window.py — 18 тестов

| Класс | Тестов | Покрытие |
|-------|:------:|----------|
| TestMainWindowRendering | 6 | Создание, QTabWidget, статус-бар |
| TestMainWindowNavigation | 6 | Переключение табов, lazy loading |
| TestMainWindowRoles | 6 | Вкладки для разных ролей |

### test_contracts.py — 44 теста

| Класс | Тестов | Покрытие |
|-------|:------:|----------|
| TestContractsTabRendering | 5 | Таблица, кнопки |
| TestContractDialogRendering | 10 | Все поля диалога |
| TestContractDynamicFields | 12 | Тип проекта, подтипы, оплаты, этажность |
| TestContractValidation | 7 | Пустые поля, дубликаты |
| TestContractCRUD | 6 | Создание/редактирование |
| TestContractSearch | 4 | Поиск по номеру, адресу |

### test_employees.py — 30 тестов

| Класс | Тестов | Покрытие |
|-------|:------:|----------|
| TestEmployeesTabRendering | 6 | Таблица, кнопки |
| TestEmployeeDialogRendering | 8 | Поля, должности, ComboBox |
| TestEmployeeValidation | 6 | Пустые поля, дублирование |
| TestEmployeeCRUD | 6 | Создание/обновление |
| TestEmployeePositions | 4 | 9 должностей, совместительство |

### test_crm.py — 92 теста

| Класс | Тестов | Покрытие |
|-------|:------:|----------|
| TestCRMTabRendering | 8 | Вкладки, колонки, кнопки |
| TestCRMRoleVisibility | 8 | Архив, статистика по ролям |
| TestCRMColumn | 6 | Сворачивание, заголовки |
| TestCRMCard | 10 | Карточки, меню, переходы |
| TestExecutorSelectionDialog | 8 | Назначение исполнителей |
| TestProjectCompletionDialog | 6 | Завершение проекта |
| TestSurveyDateDialog | 4 | Дата замера |
| TestReassignExecutorDialog | 6 | Переназначение |
| TestCRMDeadlines | 8 | Цвета дедлайнов, расчёт |
| TestCRMHelperFunctions | 8 | _emp_has_pos, _emp_only_pos |
| TestCRMCardMovement | 10 | Перемещение между колонками |
| TestCRMLazyLoading | 4 | Ленивая загрузка |
| TestCRMDialogsAndWidgets | 6 | Диалоги статистики, данных |

### test_crm_supervision.py — 40 тестов

| Класс | Тестов | Покрытие |
|-------|:------:|----------|
| TestSupervisionRendering | 6 | 15 колонок, вкладки |
| TestSupervisionRoles | 8 | ДАН read-only, архив, статистика |
| TestSupervisionColumns | 6 | Колонки, заголовки, сворачивание |
| TestSupervisionLazyLoading | 4 | Ленивая загрузка |
| TestSupervisionStages | 6 | 12 стадий, порядок |
| TestSupervisionNavigation | 10 | Переключение, refresh, сигналы |

### test_salaries.py — 34 теста

| Класс | Тестов | Покрытие |
|-------|:------:|----------|
| TestSalariesRendering | 6 | 5 вкладок, таблица, итоги |
| TestSalariesTabs | 6 | Названия, колонки, виджеты |
| TestSalariesFilters | 6 | Период, год, адрес, сброс |
| TestSalariesRoles | 6 | Тарифы, удаление, lazy loading |
| TestPaymentDialog | 6 | Оклад vs проект, поля |
| TestEditPaymentDialog | 4 | Редактирование, предзаполнение |

### test_dashboard.py — 14 тестов

| Класс | Тестов | Покрытие |
|-------|:------:|----------|
| TestDashboardTabRendering | 6 | 6 карточек, юзер-инфо |
| TestDashboardStatCards | 4 | Все карточки метрик |
| TestDashboardWidget | 4 | MetricCard, обновление значений |

### test_reports.py — 8 тестов

| Класс | Тестов | Покрытие |
|-------|:------:|----------|
| TestReportsRendering | 4 | 4 вкладки, lazy loading |
| TestReportsFilters | 4 | Год, квартал, месяц, ensure_data |

### test_roles.py — 95 тестов

| Класс | Тестов | Покрытие |
|-------|:------:|----------|
| TestEmpHasPos | 10 | Helper: ЛЮБАЯ должность совпадает |
| TestEmpOnlyPos | 10 | Helper: ВСЕ должности в наборе |
| TestRolesConfig | 8 | ROLES/POSITIONS из config.py |
| TestTabVisibilityFull | 8 | Руководитель/Старший менеджер |
| TestTabVisibilityManagement | 8 | СДП/ГАП/Менеджер |
| TestTabVisibilityExecutors | 8 | Дизайнер/Чертёжник/Замерщик |
| TestTabVisibilityDAN | 4 | ДАН — только СРМ надзора |
| TestDualRoles | 10 | Union вкладок, OR can_edit |
| TestCanEditFlag | 8 | can_edit для каждой роли |
| TestCRMRoleActions | 10 | Кнопки CRM по ролям |
| TestSupervisionRoles | 8 | Надзор: admin/manager/ДАН |

---

## Матрица ролей

### Видимость вкладок

| Должность | Клиенты | Договора | СРМ | Надзор | Отчёты | Сотрудники | Зарплаты | Отчёты сотр. |
|-----------|:-------:|:--------:|:---:|:------:|:------:|:----------:|:--------:|:------------:|
| Руководитель студии | + | + | + | + | + | + | + | + |
| Старший менеджер | + | + | + | + | + | + | + | + |
| СДП | - | - | + | - | + | + | - | - |
| ГАП | - | - | + | - | + | + | - | - |
| Менеджер | - | - | + | + | + | + | - | - |
| Дизайнер | - | - | + | - | - | - | - | - |
| Чертёжник | - | - | + | - | - | - | - | - |
| Замерщик | - | - | + | - | - | - | - | - |
| ДАН | - | - | - | + | - | - | - | - |

### can_edit в CRM

| Должность | can_edit | Примечание |
|-----------|:-------:|-----------|
| Все кроме Замерщика | True | Полный доступ к виджетам |
| Замерщик | **False** | Только просмотр |

### Двойные роли

| Комбинация | Доп. вкладки | can_edit |
|-----------|-------------|:-------:|
| Дизайнер + Менеджер | +Надзор +Отчёты +Сотрудники | True |
| Дизайнер + Чертёжник | (без изменений) | True |
| Замерщик + Менеджер | +Надзор +Отчёты +Сотрудники | **True** (OR) |
| Дизайнер + ДАН | +Надзор | True |

---

## Паттерны тестирования

### 1. Mock IconLoader

CRM и Supervision используют `IconLoader.load()` для SVG иконок. В тестах нужен реальный `QIcon`:

```python
def _mock_icon_loader():
    mock = MagicMock()
    mock.load = MagicMock(return_value=QIcon())
    mock.create_icon_button = MagicMock(
        side_effect=lambda *a, **k: QPushButton(a[1] if len(a) > 1 else '')
    )
    return mock
```

### 2. Создание виджета с патчами

```python
def _create_crm_tab(qtbot, mock_data_access, employee, can_edit=True):
    with patch('ui.crm_tab.DataAccess') as MockDA, \
         patch('ui.crm_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_tab.YandexDiskManager', return_value=None), \
         patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.crm_tab.TableSettings') as MockTS:
        MockDA.return_value = mock_data_access
        MockTS.return_value.load_column_collapse_state.return_value = {}
        from ui.crm_tab import CRMTab
        tab = CRMTab(employee=employee, can_edit=can_edit, api_client=None)
        qtbot.addWidget(tab)
        return tab
```

### 3. Критично: api_client = None

```python
mock_da.api_client = None  # Иначе MagicMock (truthy) → API path → ошибки итерации
```

### 4. Parametrize для ролей

```python
@pytest.mark.parametrize('position,expected', [
    ('Руководитель студии', True),
    ('Дизайнер', True),
    ('Замерщик', False),
])
def test_can_edit(self, position, expected):
    emp = _make_employee(position)
    assert _get_can_edit(emp) is expected
```

---

## Безопасность

### Гарантии изоляции

1. **Production SQLite не затрагивается** — autouse фикстура `_block_real_db` блокирует открытие `interior_studio.db`
2. **Сервер не затрагивается** — autouse фикстура `_block_real_api` блокирует `requests.get/post/put/delete/patch`
3. **Каждый тест изолирован** — `tmp_path` создаёт уникальную папку, удаляемую pytest после теста
4. **Нет зависимостей между тестами** — тесты можно запускать в любом порядке
5. **Нет сетевых запросов** — все API замоканы через `MagicMock`
