# Фронтенд проекта

> PyQt5 Desktop клиент, модули UI, виджеты, диалоги.
> Последнее обновление: 2026-03-29

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
    │   ├── DashboardWidget           (ui/dashboard_widget.py)
    │   ├── CRMTab                    (ui/crm_tab.py)
    │   ├── CRMSupervisionTab         (ui/crm_supervision_tab.py)
    │   ├── ClientsTab                (ui/clients_tab.py)
    │   ├── ContractsTab              (ui/contracts_tab.py)
    │   ├── SalariesTab               (ui/salaries_tab.py)
    │   ├── EmployeesTab              (ui/employees_tab.py)
    │   └── EmployeeReportsTab        (ui/employee_reports_tab.py)
    └── SyncManager (utils/sync_manager.py)
```

## Модули UI — полный список (47 файлов)

### Главное окно ([ui/main_window.py](../ui/main_window.py))

**Класс:** `MainWindow(QMainWindow)`

**Ключевые методы:**
- `__init__(employee, api_client)` — инициализация, создание табов по ролям
- `_create_tabs()` — создание табов согласно `config.ROLES[employee.role]`
- `_on_tab_changed(index)` — lazy loading при первом переключении
- `closeEvent()` — остановка SyncManager, освобождение блокировок

### Окно входа ([ui/login_window.py](../ui/login_window.py))

**Класс:** `LoginWindow(QMainWindow)`

**Ключевые методы:**
- `_try_login()` — авторизация (API → fallback на локальную БД)
- `_on_login_success(employee, api_client)` — переход к MainWindow
- `_check_server_connection()` — проверка доступности сервера

### CRM Kanban ([ui/crm_tab.py](../ui/crm_tab.py))

**Класс:** `CRMTab(QWidget)`

**Назначение:** Kanban доска проектов с Drag & Drop, стадиями, workflow.

**Ключевые методы:**
- `load_data()` — загрузка карточек по типу проекта
- `_create_kanban_board()` — построение колонок Kanban
- `_on_card_dropped()` — Drag & Drop между колонками
- `_open_card_dialog()` — детальная карточка
- `_assign_executor()` — назначение исполнителя на стадию
- `submit_work()` / `accept_work()` / `reject_work()` — workflow
- `_send_to_client()` / `_client_approved()` — согласование

### Авторский надзор ([ui/crm_supervision_tab.py](../ui/crm_supervision_tab.py))

**Класс:** `CRMSupervisionTab(QWidget)`

**Ключевые методы:**
- `load_data()` — загрузка карточек надзора
- `_open_supervision_dialog()` — детальная карточка надзора
- `_pause_card()` / `_resume_card()` — пауза/возобновление

### Диалог карточки надзора ([ui/supervision_card_edit_dialog.py](../ui/supervision_card_edit_dialog.py))

Вкладки:
- **Информация** — данные договора, команда
- **Таблица закупок** — `SupervisionTimelineWidget`
- **Выезды** — `SupervisionVisitsWidget` (новый виджет)
- **История** — голосовые заметки, события
- **Чат** — Telegram чат проекта
- **Файлы** — документы на ЯД

### Виджет выездов надзора ([ui/supervision_visits_widget.py](../ui/supervision_visits_widget.py))

**Класс:** `SupervisionVisitsWidget(QWidget)`

**Назначение:** Таблица выездов и дефектов авторского надзора.

**Функционал:**
- Добавление/удаление выездов
- Выпадающий список стадий (12 стандартных стадий)
- Дата, ФИО исполнителя, примечание
- Счётчики дефектов (найдено/устранено)
- Итого по месяцам (`/visits/summary`)
- Кнопка «Файлы на ЯД» — открывает папку выезда на Яндекс.Диске
- Экспорт PDF и Excel
- Блок «Отчёты» — загрузка и управление отчётами выездов

**Ключевые методы:**
```python
class SupervisionVisitsWidget(QWidget):
    def _load_data(self)          # Загрузка выездов с сервера
    def _populate_table(self)     # Отрисовка таблицы
    def _add_row(self)            # Добавить выезд
    def _delete_row(self, id)     # Удалить выезд
    def _update_summary(self)     # Обновить итого по месяцам
    def _open_visit_folder(self)  # Открыть папку ЯД
    def _export_excel(self)       # Экспорт в Excel
    def _export_pdf(self)         # Экспорт в PDF
    def _upload_report(self)      # Загрузить отчёт
    def load_reports(self)        # Загрузить список отчётов
```

### Виджет договоров ([ui/contracts_tab.py](../ui/contracts_tab.py))

**Класс:** `ContractsTab(QWidget)`

**Ключевые методы:**
- `load_data()` — список договоров с фильтрацией
- `_add_contract()` — создание (+ папка на Я.Диске)
- `_edit_contract()` — редактирование
- `_delete_contract()` — удаление

### Зарплаты ([ui/salaries_tab.py](../ui/salaries_tab.py))

**Класс:** `SalariesTab(QWidget)`

**Ключевые методы:**
- `load_data()` — загрузка платежей
- `_add_payment()` — создание платежа
- `_calculate_payment()` — расчёт через API
- `_filter_by_month()` — фильтрация по месяцу

### Сотрудники ([ui/employees_tab.py](../ui/employees_tab.py))

**Класс:** `EmployeesTab(QWidget)` — CRUD, фильтрация по отделу/должности.

### Дашборд ([ui/dashboard_widget.py](../ui/dashboard_widget.py))

**Класс:** `DashboardWidget(QWidget)` — статистика, графики, сводка по проектам.

## Вспомогательные виджеты

### Таблица сроков ([ui/timeline_widget.py](../ui/timeline_widget.py))

**Класс:** `ProjectTimelineWidget(QWidget)`

**7 колонок:** Этап | Дата | Кол-во дней | Норма дней | Статус | Исполнитель | ФИО

**Особенности:**
- Зелёная рамка текущего активного подэтапа
- Блокировка редактирования завершённых строк
- Предупреждение о превышении нормодней

### Таблица закупок надзора ([ui/supervision_timeline_widget.py](../ui/supervision_timeline_widget.py))

**Класс:** `SupervisionTimelineWidget(QWidget)`

**11 колонок:** Стадия | План. дата | Факт. дата | Дни | Бюджет план | Бюджет факт | Экономия | Поставщик | Комиссия | Статус | Примечания

### Файловые виджеты

| Виджет | Файл | Назначение |
|--------|------|-----------|
| FileGalleryWidget | file_gallery_widget.py | Сетка превью файлов |
| FileListWidget | file_list_widget.py | Таблица файлов |
| FilePreviewWidget | file_preview_widget.py | Предпросмотр файлов |
| VariationGalleryWidget | variation_gallery_widget.py | Вариации дизайна |

### Уведомления

| Виджет | Файл | Назначение |
|--------|------|-----------|
| NotificationsListWidget | notifications_list_widget.py | Список входящих уведомлений |
| NotificationSettingsWidget | notification_settings_widget.py | Настройка каналов уведомлений |

## Кастомные компоненты

| Компонент | Файл | Назначение |
|-----------|------|-----------|
| CustomTitleBar | custom_title_bar.py | Frameless заголовок окна |
| CustomComboBox | custom_combobox.py | Стилизованный ComboBox с поиском |
| CustomDateEdit | custom_dateedit.py | Стилизованный DateEdit |
| CustomMessageBox | custom_message_box.py | Диалоги: info/warning/error |
| CustomQuestionBox | custom_message_box.py | Диалог подтверждения: Yes/No |
| FlowLayout | flow_layout.py | Flow-раскладка (как CSS flex-wrap) |

## Диалоги

| Диалог | Файл | Назначение |
|--------|------|-----------|
| CRMCardEditDialog | crm_card_edit_dialog.py | Редактирование карточки CRM |
| SupervisionCardEditDialog | supervision_card_edit_dialog.py | Редактирование карточки надзора |
| ContractDialogs | contract_dialogs.py | Создание/редактирование договора |
| CRMDialogs | crm_dialogs.py | Отклонение, скрипты, клиент |
| SupervisionDialogs | supervision_dialogs.py | Добавление закупок, выездов |
| AdminDialog | admin_dialog.py | Управление сотрудниками и правами |
| MessengerAdminDialog | messenger_admin_dialog.py | Управление проектными чатами |
| UpdateDialogs | update_dialogs.py | Проверка и установка обновлений |
| RatesDialog | rates_dialog.py | Тарифы и прайс-листы |

## Мобильная PWA (Quasar/Vue3)

### Страницы (mobile/src/pages/ — 21 страница)

| Страница | Назначение |
|----------|-----------|
| LoginPage.vue | Аутентификация |
| DashboardPage.vue | KPI и аналитика |
| CrmBoardPage.vue | Kanban с drag-and-drop |
| CrmCardPage.vue | Детали проекта, workflow |
| ClientsPage.vue / ClientDetailPage.vue | Управление клиентами |
| ContractsPage.vue / ContractDetailPage.vue | Договора |
| SupervisionPage.vue | Канбан надзора |
| SupervisionDetailPage.vue | Выезды, закупки, файлы |
| EmployeesPage.vue | Штат |
| ReportsPage.vue / EmployeeReportsPage.vue | Отчёты |
| SalariesPage.vue | Зарплаты |
| FilesPage.vue | Файлы проекта |
| NotificationsPage.vue | Входящие уведомления |
| **NotificationSettingsPage.vue** | Настройка каналов уведомлений (новая) |
| AdminPage.vue | Управление системой |
| ProfilePage.vue | Профиль пользователя |
| OfflinePage.vue | Индикатор offline режима |
| ErrorNotFound.vue | Страница 404 |

### Компоненты (mobile/src/components/ — 12 компонентов)

| Компонент | Назначение |
|-----------|-----------|
| CrmCardItem.vue | Карточка на канбан-доске |
| CrmActionsSheet.vue | Bottom-sheet действий с карточкой |
| ClientFormDialog.vue | Диалог редактирования клиента |
| ContractFormDialog.vue | Диалог редактирования договора |
| MeasurementDialog.vue | Диалог замеров |
| TechTaskDialog.vue | Техническое задание |
| **VoiceRecorder.vue** | Запись голосовых заметок (новый) |
| InstallBanner.vue | PWA install prompt |
| PageDashboard.vue | Компонент дашборда |
| charts/BarChart.vue | Столбчатая диаграмма |
| charts/LineChart.vue | Линейная диаграмма |
| charts/PieChart.vue | Круговая диаграмма |

### VoiceRecorder.vue — голосовые заметки

**Функционал:**
- Запись голоса через microphone API браузера
- Визуализация записи (пульсирующая анимация)
- Таймер записи
- Воспроизведение записанного аудио
- Загрузка на Яндекс.Диск (папка выезда/проекта)
- Сохранение пути `voice_url` в запись (visit или history)

**Используется в:** SupervisionDetailPage (выезды), CrmCardPage (история)

### Stores (mobile/src/stores/ — 8 stores)

| Store | Назначение |
|-------|-----------|
| auth.js | Авторизация, токены, auto-refresh |
| crm.js | Канбан: карточки, фильтры, перемещение |
| clients.js | Кеш клиентов, поиск |
| dashboard.js | KPI данные, графики |
| notifications.js | Уведомления, badge-счётчик |
| permissions.js | Роли, права доступа |
| references.js | Справочники (агенты, статусы, города) |
| index.js | Инициализация и экспорт всех stores |

### Composables (mobile/src/composables/)

| Composable | Назначение |
|------------|-----------|
| useAuth.js | Проверка авторизации, ролей |
| usePermission.js | Проверка прав (can/cannot) |
| useCalendar.js | Работа с датами |
| useDeadline.js | Расчёт рабочих дней с праздниками РФ |
| useOptimistic.js | Оптимистичные обновления UI |
| useWebSocket.js | WebSocket real-time подписки |

## Паттерны инициализации

### Таб (desktop)

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

### Диалог (desktop)

```python
class SomeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.data = getattr(parent, 'data', DataAccess())
        self.db = self.data.db
        self._setup_ui()
```

## Критические правила UI

1. **Без emoji** — только SVG через IconLoader
2. **`resource_path()`** для всех ресурсов (PyInstaller совместимость)
3. **Рамка диалога = 1px** (`border: 1px solid #E0E0E0`)
4. **Border-radius** у всех виджетов внутри `borderFrame`
5. **`setAlternatingRowColors(False)`** при ручной раскраске строк
6. **PyQt Signal Safety** — emit из Thread только через `QTimer.singleShot(0, ...)`
7. **DataAccess** для всех CRUD — не api_client/db напрямую
8. **Кнопки 28px** — `setFixedHeight(28)` + CSS `max-height: 26px; padding: 0 14px`
