# Agent Skills

> Переиспользуемые навыки, шаблоны, автоматизация повторяющихся задач.

## Скилл-оркестратор

### /orkester — Полный конвейер разработки

```
Вызов: /orkester <описание задачи>
       /orkester --mode=<режим> <описание задачи>

Режимы:
  full     — полный цикл (план → код → тесты → ревью → совместимость → безопасность → документация)
  fix      — исправление бага (анализ → отладка → тесты → проверка)
  test     — запуск тестов (определение → запуск → отладка падений → отчёт)
  refactor — рефакторинг (архитектурный анализ → рефакторинг → тесты → ревью)
  security — аудит безопасности (аудит → план → исправления → тесты)
  deploy   — деплой (совместимость → тесты → деплой → smoke test)

Примеры:
  /orkester Добавить CRUD для проектных шаблонов
  /orkester --mode=fix Не работает загрузка клиентов в offline
  /orkester --mode=test Проверить модуль платежей
  /orkester --mode=deploy Обновить сервер
```

**Подробности:** [docs/17-subagents.md](17-subagents.md) — полная схема оркестрации, 16 агентов, циклы обратной связи.

---

## Повторяющиеся паттерны проекта

### 1. Создание нового CRUD endpoint (Full-Stack)

**Частота:** Очень высокая
**Затрагивает:** server/main.py, server/schemas.py, utils/api_client.py, utils/data_access.py, UI таб

**Шаблон:**

```
Шаг 1: server/schemas.py — Pydantic схема
    class EntityBase(BaseModel):
        field1: str
        field2: Optional[int] = None

    class EntityCreate(EntityBase): pass
    class EntityResponse(EntityBase):
        id: int
        created_at: datetime
        class Config: from_attributes = True

Шаг 2: server/main.py — endpoints (статические ПЕРЕД динамическими!)
    @app.get("/api/entities")
    @app.get("/api/entities/{id}")
    @app.post("/api/entities")
    @app.put("/api/entities/{id}")
    @app.delete("/api/entities/{id}")

Шаг 3: utils/api_client.py — методы клиента
    def get_entities(self): ...
    def get_entity(self, id): ...
    def create_entity(self, data): ...
    def update_entity(self, id, data): ...
    def delete_entity(self, id): ...

Шаг 4: utils/data_access.py — обёртка с fallback
    def get_all_entities(self): # API → fallback DB

Шаг 5: UI таб — вызов через self.data

Шаг 6: tests/e2e/ — тест
```

### 2. Создание UI диалога (Frontend)

**Частота:** Высокая
**Шаблон:**

```python
class SomeDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.data_access = getattr(parent, 'data', DataAccess())
        self.db = self.data_access.db

        # Border frame (1px!)
        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                border: 1px solid #E0E0E0;
                border-radius: 10px;
                background: white;
            }
        """)

        # Title bar
        title_bar = CustomTitleBar(self, "Заголовок", simple_mode=True)

        # Content layout
        content_layout = QVBoxLayout()
        # ... поля ввода, кнопки ...

        # Кнопки
        btn_save = QPushButton("Сохранить")
        btn_save.setStyleSheet(UnifiedStyles.get_primary_button_style())
```

### 3. Добавление таба в MainWindow (Frontend)

**Частота:** Средняя
**Шаблон:**

```python
# 1. Создать ui/new_tab.py
class NewTab(QWidget):
    def __init__(self, api_client=None, employee=None, parent=None):
        super().__init__(parent)
        self.data = DataAccess(api_client=api_client)
        self.db = self.data.db
        self._data_loaded = False
        self._setup_ui()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._data_loaded:
            self.load_data()
            self._data_loaded = True

# 2. Зарегистрировать в config.ROLES
# 3. Добавить в InteriorStudio.spec → hiddenimports
# 4. Добавить в ui/main_window.py → _create_tabs()
```

### 4. Миграция SQLite (Database)

**Частота:** Средняя
**Шаблон:**

```python
# В database/db_manager.py → __init__():
cursor.execute("PRAGMA table_info(table_name)")
columns = [col[1] for col in cursor.fetchall()]
if 'new_column' not in columns:
    cursor.execute('ALTER TABLE table_name ADD COLUMN new_column TYPE DEFAULT value')
    self.conn.commit()
```

### 5. API-first обёртка для DB write (Data Access)

**Частота:** Очень высокая
**Шаблон:**

```python
# В UI коде — ОБЯЗАТЕЛЬНАЯ обёртка:
if self.api_client:
    try:
        result = self.api_client.method(...)
    except Exception as e:
        print(f"[WARN] API error: {e}")
        result = self.db.method(...)
else:
    result = self.db.method(...)
```

### 6. Загрузка файла на Яндекс.Диск (Integration)

**Частота:** Средняя
**Шаблон:**

```python
from utils.yandex_disk import YandexDiskManager

yd = YandexDiskManager.get_instance(token)
yd.upload_file_to_contract_folder(
    local_path="path/to/file.pdf",
    contract_folder="ФЕСТИВАЛЬ/Индивидуальные/СПБ/Иванов",
    subfolder="Стадия 1",
    progress_callback=lambda pct: progress_bar.setValue(pct)
)
```

### 7. Стилизация таблицы (Design)

**Частота:** Высокая
**Шаблон:**

```python
from utils.unified_styles import UnifiedStyles
from utils.table_settings import ProportionalResizeTable, apply_no_focus_delegate

table = ProportionalResizeTable()
table.setStyleSheet(UnifiedStyles.get_table_style())
table.setup_proportional_resize(
    column_ratios={0: 3, 1: 2, 2: 1, 3: 1},
    min_width=50
)
apply_no_focus_delegate(table)
table.setAlternatingRowColors(True)
table.horizontalHeader().setStretchLastSection(True)
```

### 8. Docker деплой (DevOps)

**Частота:** При каждом серверном изменении
**Шаблон:**

```bash
# Локально
python -m py_compile server/main.py
git add server/ && git commit -m "описание" && git push

# На сервере
ssh timeweb
cd /opt/interior_studio
docker exec crm_postgres pg_dump -U crm_user interior_studio_crm > backup.sql
docker-compose down && docker-compose build --no-cache api && docker-compose up -d
sleep 5 && docker-compose logs --tail=30 api
```

## Скиллы (slash-команды)

### /orkester — Оркестратор конвейера

```
Триггер: любая задача разработки
Действие: Полный конвейер из 16 агентов
1. Определение режима (full/fix/test/refactor/security/deploy)
2. Planner → план + подзадачи
3. Worker → код + делегирование
4. Test-Runner ⟷ Debugger → тесты
5. Reviewer → ревью
6. Compat Checker → совместимость
7. Security Auditor → безопасность (если server/)
8. Documenter → документация
9. Senior Reviewer → архитектура (если 3+ файлов)
```

### /deploy — Деплой

```
Триггер: "deploy", "деплой", "обнови сервер"
Действие: Запуск deploy agent
1. Pre-checks
2. Backup
3. Deploy (git pull + docker rebuild)
4. Verify
5. Smoke test
```

### /style — Применение стилей

```
Триггер: "дизайн", "стили", "внешний вид", "цвет"
Действие: Запуск design-stylist agent
1. Анализ unified_styles.py
2. Применение стилей по палитре
3. Проверка консистентности
```
