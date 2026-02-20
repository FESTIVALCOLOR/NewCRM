# Фронтенд проекта

> PyQt5 Desktop клиент, модули UI, виджеты, диалоги.

## Архитектура фронтенда

```
main.py (точка входа)
    │
    ▼
LoginWindow (ui/login_window.py)
    │  authenticate → JWT token + employee data
    ▼
MainWindow (ui/main_window.py)
    ├── CustomTitleBar
    ├── QTabWidget
    │   ├── DashboardWidget      (ui/dashboard_widget.py)
    │   ├── CRMTab               (ui/crm_tab.py) — 17K+ строк
    │   ├── CRMSupervisionTab    (ui/crm_supervision_tab.py)
    │   ├── ClientsTab           (ui/clients_tab.py)
    │   ├── ContractsTab         (ui/contracts_tab.py)
    │   ├── SalariesTab          (ui/salaries_tab.py)
    │   ├── EmployeesTab         (ui/employees_tab.py)
    │   └── EmployeeReportsTab   (ui/employee_reports_tab.py)
    └── SyncManager (utils/sync_manager.py)
```

## Модули UI

### Главное окно ([ui/main_window.py](../ui/main_window.py))

**Класс:** `MainWindow(QMainWindow)`

**Назначение:** Главное окно приложения с табами, CustomTitleBar, SyncManager.

**Ключевые методы:**
- `__init__(employee, api_client)` — инициализация, создание табов по ролям
- `_create_tabs()` — создание табов согласно `config.ROLES[employee.role]`
- `_on_tab_changed(index)` — lazy loading: загрузка данных при первом переключении
- `closeEvent()` — остановка SyncManager, освобождение блокировок

**Сигналы:**
- Подписка на `SyncManager.data_updated` для обновления табов

### Окно входа ([ui/login_window.py](../ui/login_window.py))

**Класс:** `LoginWindow(QMainWindow)`

**Назначение:** Авторизация пользователя.

**Ключевые методы:**
- `_try_login()` — попытка авторизации (API → fallback на локальную БД)
- `_on_login_success(employee, api_client)` — переход к MainWindow
- `_check_server_connection()` — проверка доступности сервера

### CRM Kanban ([ui/crm_tab.py](../ui/crm_tab.py)) — 17K+ строк

**Класс:** `CRMTab(QWidget)`

**Назначение:** Kanban доска проектов с Drag & Drop, стадиями согласования, workflow.

**Ключевые методы:**
- `load_data()` — загрузка карточек по типу проекта
- `_create_kanban_board()` — построение колонок Kanban
- `_on_card_dropped()` — обработка Drag & Drop между колонками
- `_open_card_dialog()` — открытие детальной карточки
- `_assign_executor()` — назначение исполнителя на стадию
- `submit_work()` — сдача работы исполнителем
- `accept_work()` — принятие работы менеджером
- `reject_work()` — отправка на исправление
- `_send_to_client()` — отправка клиенту на согласование
- `_client_approved()` — подтверждение согласования клиентом

**Внутренние классы:**
- `DraggableListWidget` — виджет с поддержкой Drag & Drop
- `KanbanCardWidget` — карточка на доске
- `ExecutorSelectionDialog` — диалог назначения исполнителя

### Авторский надзор ([ui/crm_supervision_tab.py](../ui/crm_supervision_tab.py))

**Класс:** `CRMSupervisionTab(QWidget)`

**Назначение:** Kanban доска авторского надзора, управление ДАН.

**Ключевые методы:**
- `load_data()` — загрузка карточек надзора
- `_open_supervision_dialog()` — детальная карточка надзора
- `_pause_card()` / `_resume_card()` — пауза/возобновление

### Договоры ([ui/contracts_tab.py](../ui/contracts_tab.py))

**Класс:** `ContractsTab(QWidget)`

**Назначение:** CRUD договоров, таблица с фильтрацией, привязка к клиентам.

**Ключевые методы:**
- `load_data()` — загрузка списка договоров
- `_add_contract()` — создание нового договора (+ папка на Я.Диске)
- `_edit_contract()` — редактирование
- `_delete_contract()` — удаление (+ папка на Я.Диске)

### Зарплаты ([ui/salaries_tab.py](../ui/salaries_tab.py))

**Класс:** `SalariesTab(QWidget)`

**Назначение:** Управление платежами, зарплатные отчёты по месяцам.

**Ключевые методы:**
- `load_data()` — загрузка платежей
- `_add_payment()` — создание платежа
- `_calculate_payment()` — расчёт суммы через API
- `_filter_by_month()` — фильтрация по отчётному месяцу

### Сотрудники ([ui/employees_tab.py](../ui/employees_tab.py))

**Класс:** `EmployeesTab(QWidget)`

**Назначение:** CRUD сотрудников, фильтрация по отделу/должности.

### Дашборд ([ui/dashboard_widget.py](../ui/dashboard_widget.py))

**Класс:** `DashboardWidget(QWidget)`

**Назначение:** Статистика, графики, сводка по проектам.

**Ключевые методы:**
- `load_data()` — загрузка статистики с сервера
- `_build_widgets()` — построение виджетов дашборда

## Вспомогательные виджеты

### Таблица сроков ([ui/timeline_widget.py](../ui/timeline_widget.py))

**Класс:** `ProjectTimelineWidget(QWidget)`

**7 колонок:** Действия по этапам | Дата | Кол-во дней | Норма дней | Статус | Исполнитель | ФИО

### Таблица сроков надзора ([ui/supervision_timeline_widget.py](../ui/supervision_timeline_widget.py))

**Класс:** `SupervisionTimelineWidget(QWidget)`

**11 колонок:** Стадия | План. дата | Факт. дата | Дней | Бюджет план | Бюджет факт | Экономия | Поставщик | Комиссия | Статус | Примечания

### Галерея файлов ([ui/file_gallery_widget.py](../ui/file_gallery_widget.py))

**Класс:** `FileGalleryWidget(QWidget)`

**Назначение:** Отображение файлов проекта в виде сетки превью.

### Список файлов ([ui/file_list_widget.py](../ui/file_list_widget.py))

**Класс:** `FileListWidget(QWidget)`

**Назначение:** Отображение файлов проекта в виде таблицы.

### Превью файлов ([ui/file_preview_widget.py](../ui/file_preview_widget.py))

**Класс:** `FilePreviewWidget(QWidget)`

**Назначение:** Предпросмотр изображений и документов.

### Галерея вариаций ([ui/variation_gallery_widget.py](../ui/variation_gallery_widget.py))

**Класс:** `VariationGalleryWidget(QWidget)`

**Назначение:** Отображение вариаций дизайн-проекта.

## Кастомные компоненты

| Компонент | Файл | Назначение |
|-----------|------|-----------|
| CustomTitleBar | [ui/custom_title_bar.py](../ui/custom_title_bar.py) | Frameless заголовок окна (простой/полный режим) |
| CustomComboBox | [ui/custom_combobox.py](../ui/custom_combobox.py) | Стилизованный ComboBox |
| CustomDateEdit | [ui/custom_dateedit.py](../ui/custom_dateedit.py) | Стилизованный DateEdit |
| CustomMessageBox | [ui/custom_message_box.py](../ui/custom_message_box.py) | Стилизованные диалоги (info/warning/error/question) |
| FlowLayout | [ui/flow_layout.py](../ui/flow_layout.py) | Flow-раскладка (как CSS flex-wrap) |

## Паттерны инициализации

### Инициализация таба

```python
class SomeTab(QWidget):
    def __init__(self, api_client=None, employee=None, parent=None):
        super().__init__(parent)
        from utils.data_access import DataAccess
        self.data = DataAccess(api_client=api_client)
        self.db = self.data.db
        self.api_client = api_client
        self.employee = employee
        self._data_loaded = False  # lazy loading
        self._setup_ui()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._data_loaded:
            self.load_data()
            self._data_loaded = True
```

### Инициализация диалога

```python
class SomeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.data = getattr(parent, 'data', DataAccess())
        self.db = self.data.db
        self._setup_ui()
```

## Lazy Loading табов

Табы загружают данные **только при первом переключении** — это ускоряет запуск приложения:

```
MainWindow.__init__()
    → создаёт все QWidget табов
    → НЕ загружает данные
    → при переключении таба → showEvent → load_data()
```

Оптимизация: `setUpdatesEnabled(False)` на время загрузки данных, затем `setUpdatesEnabled(True)`.
