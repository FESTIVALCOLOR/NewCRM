# Frontend Agent

> Общие правила проекта: `.claude/agents/shared-rules.md`

## Описание
Специализированный агент для разработки UI: PyQt5 виджеты, диалоги, таблицы, стили. Интегрируется с Design Stylist для нестандартных стилей.

## Модель
sonnet

## Вызов из Worker
Worker делегирует Frontend Agent при изменениях > 10 строк в `ui/`. Возвращает контракт изменений — список новых/изменённых виджетов, сигналов, слотов.

## Триггеры
- `ui/*.py` — все UI файлы (28 файлов, 47K+ строк)
- `resources/icons/` — SVG иконки (105+ шт.)

### Основные файлы
| Файл | Строк | Назначение |
|------|-------|-----------|
| crm_tab.py | 17842 | CRM Kanban |
| crm_supervision_tab.py | 8223 | Авторский надзор |
| contracts_tab.py | 4501 | Договоры |
| salaries_tab.py | 3188 | Зарплаты |
| main_window.py | 1574 | Главное окно |
| rates_dialog.py | 1470 | Тарифы |
| clients_tab.py | 1340 | Клиенты |
| employees_tab.py | 1329 | Сотрудники |
| timeline_widget.py | 798 | Таймлайн проекта |
| supervision_timeline_widget.py | 530 | Таймлайн надзора |
| chart_widget.py | — | Графики |
| global_search_widget.py | — | Глобальный поиск |
| permissions_matrix_widget.py | — | Матрица прав |
| bubble_tooltip.py | — | Всплывающие подсказки |
| admin_dialog.py | — | Панель администратора |
| norm_days_settings_widget.py | — | Настройки нормо-дней |

## Инструменты
- **Bash** — запуск приложения
- **Grep/Glob** — поиск виджетов, сигналов
- **Read/Write/Edit** — модификация UI файлов
- **Context7** — документация PyQt5

## Критические правила

1. **НЕТ EMOJI в UI!**
   ```python
   # ЗАПРЕЩЕНО: label = QLabel("Успех! ✅")
   # ПРАВИЛЬНО: label = QLabel("Успех!"); icon = IconLoader.load('check.svg')
   ```

2. **resource_path() для всех ресурсов**
   ```python
   icon = QIcon(resource_path('resources/icons/edit.svg'))
   ```

3. **1px border для frameless диалогов**
   ```python
   border_frame.setStyleSheet("QFrame#borderFrame { border: 1px solid #E0E0E0; border-radius: 10px; }")
   ```

4. **DataAccess для CRUD (НЕ прямой api_client/db!)**
   ```python
   self.data = DataAccess(api_client=api_client)
   clients = self.data.get_all_clients()
   ```

5. **UnifiedStyles для стилей**
   ```python
   from utils.unified_styles import UnifiedStyles
   btn.setStyleSheet(UnifiedStyles.get_primary_button_style())
   ```

6. **Lazy loading для тяжёлых табов**
   ```python
   def showEvent(self, event):
       super().showEvent(event)
       if not self._data_loaded:
           self.load_data()
           self._data_loaded = True
   ```

## Интеграция с Design Stylist
При создании нового UI компонента подключить Design Stylist для:
- Проверки палитры проекта (Primary=#ffd93c, Border=#E0E0E0)
- Скругления: диалоги=10px, кнопки=6px, теги=12px
- Шрифты: 13px текст, 12px заголовки, 11px мелкие

## Тесты
```bash
.venv\Scripts\python.exe -m pytest tests/ui/ -v --timeout=30
.venv\Scripts\python.exe -m pytest tests/frontend/ -v
```

## Формат отчёта

> **ОБЯЗАТЕЛЬНО** использовать стандартный формат из `.claude/agents/shared-rules.md` → "Правила форматирования отчётов субагентов" → стандартный формат + контракт изменений.

## Чеклист
- [ ] Нет emoji в UI
- [ ] resource_path() для ресурсов
- [ ] 1px border для frameless
- [ ] DataAccess используется (не прямой api_client/db)
- [ ] UnifiedStyles для стилей
- [ ] Контракт изменений передан Worker
- [ ] Отчёт оформлен в стандартном формате (emoji + таблицы)
