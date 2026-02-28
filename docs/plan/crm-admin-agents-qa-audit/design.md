# Design: Перенос управления агентами и городами в администрирование

**Дата:** 2026-02-25
**Статус:** Draft
**Задача:** Перенести управление агентами и городами из карточки договора в AdminDialog, добавить удаление, создать модель City в БД

---

## 1. C4 Model

### 1.1 Container Diagram (ДО изменений)

```
+------------------+        +------------------+        +------------------+
|   PyQt5 Client   |  REST  |   FastAPI Server  |  SQL   |   PostgreSQL DB  |
|                  |------->|                  |------->|                  |
|  ContractDialog  |  API   |  agents_router   |        |  agents table    |
|  (агенты + города)|        |  (CRUD агентов)  |        |  (нет cities!)   |
+------------------+        +------------------+        +------------------+
        |                                                        |
        | config.py:CITIES                                       |
        | (жесткий список)                                       |
        +-- города НЕ сохраняются в БД! ---------X               |
```

**Проблемы текущей архитектуры:**
- Города хранятся только в `config.py:95` как `CITIES = ['СПБ', 'МСК', 'ВН']`
- Добавление города в `contract_dialogs.py:1764-1877` — чисто локальное (в ComboBox), теряется при перезапуске
- Управление агентами встроено в диалог договора — нарушает SRP (Single Responsibility)
- Нет endpoint DELETE для агентов
- Нет никакого API для городов

### 1.2 Container Diagram (ПОСЛЕ изменений)

```
+------------------+        +------------------+        +------------------+
|   PyQt5 Client   |  REST  |   FastAPI Server  |  SQL   |   PostgreSQL DB  |
|                  |------->|                  |------->|                  |
|  AdminDialog     |  API   |  agents_router   |        |  agents table    |
|  [5 вкладок]     |        |  cities_router   |        |  cities table    |
|                  |        |  (полный CRUD)    |        |  (НОВАЯ)         |
|  ContractDialog  |        |                  |        |                  |
|  (только ComboBox)|        |                  |        |                  |
+------------------+        +------------------+        +------------------+
        |                           |
        |  DataAccess               |  Permissions:
        |  (API-first + fallback)   |  agents.create/update/delete
        |                           |  cities.create/delete
```

### 1.3 Component Diagram — затронутые модули

```
+-----------------------------------------------------------------------+
|                           СЕРВЕР (FastAPI)                             |
+-----------------------------------------------------------------------+
|                                                                       |
|  server/database.py:166      Agent (id, name, color, status)          |
|  server/database.py:NEW      City (id, name, status, created_at) NEW  |
|                                                                       |
|  server/routers/agents_router.py    GET / POST / GET{id} / PATCH      |
|                                     + DELETE{id} NEW                   |
|                                                                       |
|  server/routers/cities_router.py    GET / POST / DELETE{id} NEW       |
|                                                                       |
|  server/schemas.py                  CityCreate, CityResponse NEW      |
|  server/permissions.py:57-58        + agents.delete NEW               |
|                                     + cities.create, cities.delete NEW|
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|                          КЛИЕНТ (PyQt5)                                |
+-----------------------------------------------------------------------+
|                                                                       |
|  ui/admin_dialog.py:81-98      + Вкладка 5: "Агенты и города" NEW     |
|  ui/agents_cities_widget.py    AgentsCitiesWidget NEW                  |
|                                                                       |
|  ui/contract_dialogs.py:400-423   УДАЛИТЬ кнопки управления           |
|  ui/contract_dialogs.py:4207      AgentDialog — DEPRECATED            |
|  ui/contract_dialogs.py:1764      add_city() — УДАЛИТЬ                |
|                                                                       |
|  utils/api_client/misc_mixin.py:185  + delete_agent() NEW             |
|                                      + get_all_cities() NEW           |
|                                      + add_city() NEW                 |
|                                      + delete_city() NEW              |
|                                                                       |
|  utils/data_access.py:1527           + delete_agent() NEW             |
|                                      + get_all_cities() NEW           |
|                                      + add_city() NEW                 |
|                                      + delete_city() NEW              |
|                                                                       |
|  database/db_manager.py:3730         + delete_agent() NEW             |
|                                      + create_cities_table() NEW      |
|                                      + get_all_cities() NEW           |
|                                      + add_city() NEW                 |
|                                      + delete_city() NEW              |
|                                                                       |
|  config.py:94-95                     CITIES — оставить как fallback   |
+-----------------------------------------------------------------------+
```

---

## 2. DFD (Data Flow Diagrams)

### 2.1 Агенты — ДО изменений

```
ContractDialog          DataAccess           API Client          FastAPI           PostgreSQL
     |                      |                    |                  |                  |
     |--add_agent_btn------>|                    |                  |                  |
     |  (click)             |                    |                  |                  |
     |                      |                    |                  |                  |
     |  AgentDialog.exec()  |                    |                  |                  |
     |  [ui/contract_       |                    |                  |                  |
     |   dialogs.py:4207]   |                    |                  |                  |
     |                      |                    |                  |                  |
     |---add_agent(name)--->|                    |                  |                  |
     |                      |--db.add_agent()--->|                  |                  |
     |                      |  (SQLite local)    |                  |                  |
     |                      |                    |                  |                  |
     |                      |--api.add_agent()-->|--POST /agents--->|--INSERT agents-->|
     |                      |                    |                  |                  |
     |<--reload_agents()----|<---agents list-----|<---200 OK--------|<---rows----------|
```

### 2.2 Агенты — ПОСЛЕ изменений

```
AdminDialog             AgentsCitiesWidget    DataAccess          API Client         FastAPI           PostgreSQL
     |                      |                    |                  |                  |                  |
     |--tab "Агенты и       |                    |                  |                  |                  |
     |   города" selected-->|                    |                  |                  |                  |
     |                      |                    |                  |                  |                  |
     |                      |--load_agents()---->|                  |                  |                  |
     |                      |                    |--api.get_all()-->|--GET /agents---->|--SELECT agents-->|
     |                      |<---agents list-----|<---list----------|<---200 OK--------|<---rows----------|
     |                      |                    |                  |                  |                  |
     |                      |--add_agent(name)-->|                  |                  |                  |
     |                      |                    |--db.add_agent()->|                  |                  |
     |                      |                    |--api.add()------>|--POST /agents--->|--INSERT--------->|
     |                      |<---result----------|                  |                  |                  |
     |                      |                    |                  |                  |                  |
     |                      |--delete_agent(id)->|                  |                  |                  |
     |                      |   [confirm dialog] |--db.delete()---->|                  |                  |
     |                      |                    |--api.delete()--->|--DELETE /agents/N|--UPDATE status-->|
     |                      |<---result----------|                  |  (soft delete)   |  ='удалён'       |
```

### 2.3 Города — ДО изменений (СЛОМАННЫЙ поток)

```
ContractDialog                config.py
     |                           |
     |--city_combo.addItems()--->|  CITIES = ['СПБ', 'МСК', 'ВН']
     |  [строка 415]             |  (жёсткий список)
     |                           |
     |--add_city_btn.click()---->|
     |  city_input.text()        |
     |  city_combo.addItem(text) |  <-- НЕ СОХРАНЯЕТСЯ В БД!
     |  [строка 1876]            |      Теряется при перезапуске
```

### 2.4 Города — ПОСЛЕ изменений

```
AdminDialog             AgentsCitiesWidget    DataAccess          API Client         FastAPI           PostgreSQL
     |                      |                    |                  |                  |                  |
     |                      |--load_cities()---->|                  |                  |                  |
     |                      |                    |--api.get_all()-->|--GET /cities---->|--SELECT cities-->|
     |                      |                    |  fallback:       |                  |                  |
     |                      |                    |  db.get_cities() |                  |                  |
     |                      |<---cities list-----|                  |                  |                  |
     |                      |                    |                  |                  |                  |
     |                      |--add_city(name)--->|                  |                  |                  |
     |                      |                    |--db.add_city()-->|                  |                  |
     |                      |                    |--api.add()------>|--POST /cities--->|--INSERT cities-->|
     |                      |<---result----------|                  |                  |                  |
     |                      |                    |                  |                  |                  |
     |                      |--delete_city(id)-->|                  |                  |                  |
     |                      |   [confirm dialog] |--db.delete()---->|                  |                  |
     |                      |                    |--api.delete()--->|--DELETE /cities/N|--UPDATE status-->|
     |                      |<---result----------|                  |  (soft delete)   |  ='удалён'       |
```

### 2.5 ContractDialog — загрузка городов ПОСЛЕ изменений

```
ContractDialog              DataAccess           API / SQLite
     |                          |                     |
     |--init: reload_cities()-->|                     |
     |                          |--get_all_cities()-->|
     |                          |  (API-first,        |
     |                          |   fallback SQLite,  |
     |                          |   fallback config)  |
     |<---cities list-----------|                     |
     |  city_combo.addItems()   |                     |
     |  (без кнопки "Добавить"!)|                     |
```

---

## 3. API контракты

### 3.1 Новый endpoint: DELETE /api/v1/agents/{agent_id}

**Файл:** `server/routers/agents_router.py`
**Право:** `agents.delete`

```python
# Pydantic-схема (уже есть StatusResponse в schemas.py:14)
# Используем существующий StatusResponse

@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: int,
    current_user: Employee = Depends(require_permission("agents.delete")),
    db: Session = Depends(get_db)
) -> dict:
    """Мягкое удаление агента (status='удалён')"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")

    # Проверка: есть ли активные договоры с этим агентом
    active_contracts = db.query(Contract).filter(
        Contract.agent_type == agent.name,
        Contract.status != 'РАСТОРГНУТ'
    ).count()

    if active_contracts > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Нельзя удалить агента: {active_contracts} активных договоров"
        )

    agent.status = "удалён"
    db.commit()
    return {"status": "success", "message": f"Агент '{agent.name}' удалён"}
```

**Запрос:** `DELETE /api/v1/agents/3`
**Ответ 200:** `{"status": "success", "message": "Агент 'ПЕТРОВИЧ' удалён"}`
**Ответ 404:** `{"detail": "Агент не найден"}`
**Ответ 409:** `{"detail": "Нельзя удалить агента: 5 активных договоров"}`

**Важно:** Мягкое удаление (soft delete) через `status='удалён'`. Существующий GET `/` должен фильтровать: `Agent.status != 'удалён'`.

### 3.2 Изменение: GET /api/v1/agents — фильтрация удалённых

**Файл:** `server/routers/agents_router.py:29-42`

```python
@router.get("/")
async def get_all_agents(
    include_deleted: bool = False,  # NEW: параметр для админки
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Agent).order_by(Agent.name)
    if not include_deleted:
        query = query.filter(Agent.status != "удалён")
    agents = query.all()
    return [{"id": a.id, "name": a.name, "full_name": a.name,
             "color": a.color or "#FFFFFF", "status": a.status or "активный"} for a in agents]
```

### 3.3 Новый router: cities_router.py

**Файл:** `server/routers/cities_router.py` (НОВЫЙ)
**Prefix:** `/api/v1/cities` (зарегистрировать в `server/main.py:351`)

#### Pydantic-схемы

```python
# В server/routers/cities_router.py (inline, как в agents_router.py)
class CityCreate(BaseModel):
    name: str

class CityResponse(BaseModel):
    id: int
    name: str
    status: str
```

#### GET /api/v1/cities

```python
@router.get("/")
async def get_all_cities(
    include_deleted: bool = False,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[dict]:
    """Получить список всех городов"""
    query = db.query(City).order_by(City.name)
    if not include_deleted:
        query = query.filter(City.status != "удалён")
    cities = query.all()
    return [{"id": c.id, "name": c.name, "status": c.status or "активный"} for c in cities]
```

**Запрос:** `GET /api/v1/cities`
**Ответ 200:** `[{"id": 1, "name": "СПБ", "status": "активный"}, ...]`

#### POST /api/v1/cities

```python
@router.post("/")
async def add_city(
    data: CityCreate,
    current_user: Employee = Depends(require_permission("cities.create")),
    db: Session = Depends(get_db)
) -> dict:
    """Добавить новый город"""
    existing = db.query(City).filter(City.name == data.name).first()
    if existing:
        if existing.status == "удалён":
            existing.status = "активный"
            db.commit()
            return {"status": "success", "id": existing.id, "name": existing.name}
        raise HTTPException(status_code=400, detail="Город с таким названием уже существует")

    city = City(name=data.name)
    db.add(city)
    db.commit()
    db.refresh(city)
    return {"status": "success", "id": city.id, "name": data.name}
```

**Запрос:** `POST /api/v1/cities` + `{"name": "КЗН"}`
**Ответ 200:** `{"status": "success", "id": 4, "name": "КЗН"}`
**Ответ 400:** `{"detail": "Город с таким названием уже существует"}`

#### DELETE /api/v1/cities/{city_id}

```python
@router.delete("/{city_id}")
async def delete_city(
    city_id: int,
    current_user: Employee = Depends(require_permission("cities.delete")),
    db: Session = Depends(get_db)
) -> dict:
    """Мягкое удаление города"""
    city = db.query(City).filter(City.id == city_id).first()
    if not city:
        raise HTTPException(status_code=404, detail="Город не найден")

    # Проверка: есть ли активные договоры с этим городом
    active_contracts = db.query(Contract).filter(
        Contract.city == city.name,
        Contract.status != 'РАСТОРГНУТ'
    ).count()

    if active_contracts > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Нельзя удалить город: {active_contracts} активных договоров"
        )

    city.status = "удалён"
    db.commit()
    return {"status": "success", "message": f"Город '{city.name}' удалён"}
```

**Запрос:** `DELETE /api/v1/cities/2`
**Ответ 200:** `{"status": "success", "message": "Город 'МСК' удалён"}`
**Ответ 409:** `{"detail": "Нельзя удалить город: 12 активных договоров"}`

---

## 4. DB Schema Changes

### 4.1 Новая модель City (сервер — PostgreSQL)

**Файл:** `server/database.py` — добавить ПОСЛЕ класса `Agent` (строка 174)

```python
class City(Base):
    """Города"""
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    status = Column(String, default='активный')  # 'активный' / 'удалён'
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 4.2 Серверная миграция — seed из config.py

**Файл:** `server/main.py` — в блоке `@app.on_event("startup")` или отдельная функция seed:

```python
def seed_cities(db: Session):
    """Начальное заполнение таблицы cities из config.py"""
    from sqlalchemy import text
    default_cities = ['СПБ', 'МСК', 'ВН']
    for city_name in default_cities:
        existing = db.query(City).filter(City.name == city_name).first()
        if not existing:
            db.add(City(name=city_name))
    db.commit()
```

Вызов: `Base.metadata.create_all(bind=engine)` создаст таблицу, затем `seed_cities(db)` заполнит начальные данные.

### 4.3 Локальная миграция — SQLite (клиент)

**Файл:** `database/db_manager.py` — новая миграция в `run_migrations()`

```python
def create_cities_table_migration(self):
    """Миграция: создание таблицы cities в локальной SQLite"""
    try:
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'активный',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Seed из config.py
        from config import CITIES
        for city_name in CITIES:
            cursor.execute(
                "INSERT OR IGNORE INTO cities (name) VALUES (?)",
                (city_name,)
            )

        conn.commit()
        self.close()
    except Exception as e:
        print(f"[WARN] create_cities_table_migration: {e}")
```

### 4.4 ERD (Entity-Relationship) — затронутые таблицы

```
+------------------+       +------------------+       +------------------+
|     agents       |       |    contracts     |       |     cities       |
+------------------+       +------------------+       +------------------+
| id (PK)          |       | id (PK)          |       | id (PK)          |
| name (UNIQUE)    |<------| agent_type (FK*) |       | name (UNIQUE)    |
| color            |  ref  | city (FK*)       |------>| status           |
| status           |  by   | ...              |  ref  | created_at       |
| created_at       |  name | status           |  by   +------------------+
+------------------+       +------------------+  name

* FK — логическая ссылка по имени (String), НЕ настоящий ForeignKey.
  Contract.agent_type хранит имя агента (строка).
  Contract.city хранит название города (строка).
  Это legacy-дизайн, менять FK сейчас НЕ целесообразно (см. ADR 7.2).
```

---

## 5. UI Component Design

### 5.1 Новый виджет: AgentsCitiesWidget

**Файл:** `ui/agents_cities_widget.py` (НОВЫЙ)

#### Layout

```
+------------------------------------------------------------------+
|  Агенты и города                                    [вкладка 5]   |
+------------------------------------------------------------------+
|                                                                    |
|  +-- Агенты (левая половина) --+  +-- Города (правая половина) -+ |
|  |                              |  |                             | |
|  |  +------------------------+  |  |  +----------------------+   | |
|  |  | ФЕСТИВАЛЬ    [#ffd93c] |  |  |  | СПБ                  |   | |
|  |  | [Цвет] [Удалить]       |  |  |  | [Удалить]            |   | |
|  |  +------------------------+  |  |  +----------------------+   | |
|  |  | ПЕТРОВИЧ     [#4CAF50] |  |  |  | МСК                  |   | |
|  |  | [Цвет] [Удалить]       |  |  |  | [Удалить]            |   | |
|  |  +------------------------+  |  |  +----------------------+   | |
|  |                              |  |  | ВН                   |   | |
|  |  ............................ |  |  | [Удалить]            |   | |
|  |  Название: [_______________] |  |  +----------------------+   | |
|  |  Цвет:    [#] [Выбрать]     |  |                             | |
|  |  [+ Добавить агента]         |  |  .......................... | |
|  |                              |  |  Название: [_____________] | |
|  +------------------------------+  |  [+ Добавить город]        | |
|                                     |                             | |
|                                     +-----------------------------+ |
+------------------------------------------------------------------+
```

#### Структура класса

```python
class AgentsCitiesWidget(QWidget):
    """Виджет управления агентами и городами для AdminDialog"""

    def __init__(self, parent=None, api_client=None, data_access=None, employee=None):
        super().__init__(parent)
        self.api_client = api_client
        self.data_access = data_access
        self.employee = employee or {}
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        """Создание UI: два столбца (QSplitter или QHBoxLayout)"""
        ...

    # --- Агенты ---
    def _create_agents_panel(self) -> QWidget: ...
    def _load_agents(self): ...
    def _add_agent(self): ...
    def _delete_agent(self, agent_id: int, agent_name: str): ...
    def _change_agent_color(self, agent_name: str): ...

    # --- Города ---
    def _create_cities_panel(self) -> QWidget: ...
    def _load_cities(self): ...
    def _add_city(self): ...
    def _delete_city(self, city_id: int, city_name: str): ...

    def _load_data(self):
        """Загрузка агентов и городов при инициализации"""
        self._load_agents()
        self._load_cities()
```

#### Стилизация (согласно правилам проекта)

```python
# Рамка панели
PANEL_STYLE = """
    QFrame#agentsPanel, QFrame#citiesPanel {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 10px;
    }
"""

# Строка элемента (агент/город) в списке
ITEM_STYLE = """
    QFrame#itemRow {
        background-color: #FAFAFA;
        border: 1px solid #E0E0E0;
        border-radius: 6px;
        padding: 8px;
        margin: 2px 0;
    }
    QFrame#itemRow:hover {
        background-color: #F5F5F5;
        border-color: #ffd93c;
    }
"""

# Кнопка "Добавить" (accent)
ADD_BTN_STYLE = """
    QPushButton {
        background-color: #ffd93c;
        color: #333333;
        padding: 8px 20px;
        font-weight: bold;
        border-radius: 6px;
        border: none;
        font-size: 13px;
    }
    QPushButton:hover { background-color: #f0c929; }
    QPushButton:pressed { background-color: #e0b919; }
"""

# Кнопка "Удалить" (danger)
DELETE_BTN_STYLE = """
    QPushButton {
        background-color: #ffffff;
        color: #e74c3c;
        border: 1px solid #e74c3c;
        border-radius: 6px;
        padding: 4px 12px;
        font-size: 11px;
    }
    QPushButton:hover {
        background-color: #fdecea;
    }
"""
```

### 5.2 Интеграция в AdminDialog

**Файл:** `ui/admin_dialog.py:81-98`

Добавить 5-ю вкладку по аналогии с существующими (ленивая загрузка):

```python
# --- Вкладка 5: Агенты и города ---
self._tab_agents_cities = self._create_agents_cities_tab()
self._tabs.addTab(self._tab_agents_cities, "Агенты и города")
```

```python
def _create_agents_cities_tab(self):
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.addWidget(QLabel("Загрузка..."))
    from PyQt5.QtCore import QTimer
    QTimer.singleShot(300, self._init_agents_cities_widget)
    return w

def _init_agents_cities_widget(self):
    try:
        from ui.agents_cities_widget import AgentsCitiesWidget
        widget = AgentsCitiesWidget(
            parent=self._tab_agents_cities,
            api_client=self.api_client,
            data_access=self.data_access,
            employee=self.employee,
        )
        layout = self._tab_agents_cities.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        layout.addWidget(widget)
    except Exception as e:
        print(f"[WARN] Не удалось загрузить AgentsCitiesWidget: {e}")
        lbl = self._tab_agents_cities.findChild(QLabel)
        if lbl:
            lbl.setText(f"Ошибка загрузки: {e}")
```

### 5.3 Удаление из ContractDialog

**Файл:** `ui/contract_dialogs.py`

#### Агенты (строки 400-411)

**ДО:**
```python
agent_layout = QHBoxLayout()
self.agent_combo = CustomComboBox()
self.reload_agents()
agent_layout.addWidget(self.agent_combo)
add_agent_btn = IconLoader.create_icon_button('settings2', '', 'Добавить', icon_size=14)
add_agent_btn.setMaximumWidth(28)
add_agent_btn.setFixedHeight(28)
add_agent_btn.setStyleSheet('padding: 0px 0px; font-size: 14px;')
add_agent_btn.setToolTip('Управление агентами')
add_agent_btn.clicked.connect(self.add_agent)
agent_layout.addWidget(add_agent_btn)
main_layout_form.addRow('Агент:', agent_layout)
```

**ПОСЛЕ:**
```python
self.agent_combo = CustomComboBox()
self.reload_agents()
main_layout_form.addRow('Агент:', self.agent_combo)
```

#### Города (строки 413-424)

**ДО:**
```python
city_layout = QHBoxLayout()
self.city_combo = CustomComboBox()
self.city_combo.addItems(CITIES)
city_layout.addWidget(self.city_combo)
add_city_btn = IconLoader.create_icon_button('settings2', '', 'Добавить', icon_size=14)
add_city_btn.setMaximumWidth(28)
add_city_btn.setFixedHeight(28)
add_city_btn.setStyleSheet('padding: 0px 0px; font-size: 14px;')
add_city_btn.setToolTip('Управление городами')
add_city_btn.clicked.connect(self.add_city)
city_layout.addWidget(add_city_btn)
main_layout_form.addRow('Город:', city_layout)
```

**ПОСЛЕ:**
```python
self.city_combo = CustomComboBox()
self.reload_cities()  # Загрузка из БД вместо config.py
main_layout_form.addRow('Город:', self.city_combo)
```

#### Новый метод reload_cities()

```python
def reload_cities(self):
    """Загрузка городов из БД (API-first, fallback на config.py)"""
    current_text = self.city_combo.currentText()
    self.city_combo.clear()

    cities = self.data.get_all_cities()
    for city in cities:
        name = city['name'] if isinstance(city, dict) else city
        self.city_combo.addItem(name)

    if current_text:
        index = self.city_combo.findText(current_text)
        if index >= 0:
            self.city_combo.setCurrentIndex(index)
```

#### Удаление методов

- `add_agent()` (строка 1742-1747) — УДАЛИТЬ
- `add_city()` (строка 1764-1877) — УДАЛИТЬ
- `class AgentDialog` (строка 4207-4360+) — УДАЛИТЬ (весь класс)

### 5.4 Обновление rates_dialog.py

**Файл:** `ui/rates_dialog.py:425-443`

Метод `_get_all_cities()` (строка 425) сейчас берёт города из `config.CITIES` + `DISTINCT city FROM contracts`. После изменений:

```python
def _get_all_cities(self):
    """Получить все города из БД (через DataAccess)"""
    try:
        cities_data = self.data_access.get_all_cities()
        return [c['name'] if isinstance(c, dict) else c for c in cities_data]
    except Exception:
        # Fallback на config
        from config import CITIES
        return list(CITIES)
```

**Примечание:** Нужно проверить, передаётся ли `data_access` в `RatesSettingsWidget`. Если нет — добавить параметр.

---

## 6. Слой данных: API Client + DataAccess + SQLite

### 6.1 API Client — новые методы

**Файл:** `utils/api_client/misc_mixin.py`

```python
# === Агенты: удаление ===

def delete_agent(self, agent_id: int) -> bool:
    """Удалить агента (soft delete)"""
    try:
        response = self._request(
            'DELETE',
            f"{self.base_url}/api/v1/agents/{agent_id}"
        )
        self._handle_response(response)
        return True
    except Exception as e:
        print(f"[API] Ошибка удаления агента: {e}")
        raise

# === Города: CRUD ===

def get_all_cities(self) -> List[Dict[str, Any]]:
    """Получить список всех городов"""
    try:
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/cities"
        )
        return self._handle_response(response)
    except Exception:
        return []

def add_city(self, name: str) -> bool:
    """Добавить новый город"""
    try:
        response = self._request(
            'POST',
            f"{self.base_url}/api/v1/cities",
            json={'name': name}
        )
        self._handle_response(response)
        return True
    except Exception as e:
        print(f"[API] Ошибка добавления города: {e}")
        raise

def delete_city(self, city_id: int) -> bool:
    """Удалить город (soft delete)"""
    try:
        response = self._request(
            'DELETE',
            f"{self.base_url}/api/v1/cities/{city_id}"
        )
        self._handle_response(response)
        return True
    except Exception as e:
        print(f"[API] Ошибка удаления города: {e}")
        raise
```

### 6.2 DataAccess — новые методы

**Файл:** `utils/data_access.py` — добавить после блока `# ==================== АГЕНТЫ ====================`

```python
def delete_agent(self, agent_id: int) -> bool:
    """Удалить агента (soft delete)"""
    # Локально
    try:
        self.db.delete_agent(agent_id)
    except Exception as e:
        _safe_log(f"[DataAccess] DB delete_agent: {e}")

    if self.is_online and self.api_client:
        try:
            return self.api_client.delete_agent(agent_id)
        except Exception as e:
            _safe_log(f"[DataAccess] API delete_agent: {e}")
            self._queue_operation('delete', 'agent', agent_id, {})
    elif self.api_client:
        self._queue_operation('delete', 'agent', agent_id, {})

    return True

# ==================== ГОРОДА ====================

def get_all_cities(self) -> List[Dict]:
    """Получить все города"""
    if self.api_client:
        try:
            result = self.api_client.get_all_cities()
            if result:
                return result
        except Exception as e:
            _safe_log(f"[DataAccess] API error get_all_cities, fallback: {e}")

    # Fallback на локальную БД
    try:
        return self.db.get_all_cities()
    except Exception as e:
        _safe_log(f"[DataAccess] DB get_all_cities: {e}")

    # Последний fallback — config.py
    from config import CITIES
    return [{'id': i, 'name': c, 'status': 'активный'} for i, c in enumerate(CITIES, 1)]

def add_city(self, name: str) -> Optional[Dict]:
    """Добавить город"""
    local_result = None
    try:
        local_result = self.db.add_city(name)
    except Exception as e:
        _safe_log(f"[DataAccess] DB add_city: {e}")

    if self.is_online and self.api_client:
        try:
            return self.api_client.add_city(name)
        except Exception as e:
            _safe_log(f"[DataAccess] API add_city: {e}")
            self._queue_operation('create', 'city', 0, {'name': name})
    elif self.api_client:
        self._queue_operation('create', 'city', 0, {'name': name})

    return local_result

def delete_city(self, city_id: int) -> bool:
    """Удалить город (soft delete)"""
    try:
        self.db.delete_city(city_id)
    except Exception as e:
        _safe_log(f"[DataAccess] DB delete_city: {e}")

    if self.is_online and self.api_client:
        try:
            return self.api_client.delete_city(city_id)
        except Exception as e:
            _safe_log(f"[DataAccess] API delete_city: {e}")
            self._queue_operation('delete', 'city', city_id, {})
    elif self.api_client:
        self._queue_operation('delete', 'city', city_id, {})

    return True
```

### 6.3 SQLite DatabaseManager — новые методы

**Файл:** `database/db_manager.py`

```python
# === Города ===

def get_all_cities(self):
    """Получение всех активных городов"""
    try:
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, status FROM cities WHERE status != 'удалён' ORDER BY name"
        )
        rows = cursor.fetchall()
        self.close()
        return [{'id': r[0], 'name': r[1], 'status': r[2]} for r in rows]
    except Exception as e:
        print(f"[ERROR] Ошибка получения городов: {e}")
        # Fallback на config
        from config import CITIES
        return [{'id': i, 'name': c, 'status': 'активный'} for i, c in enumerate(CITIES, 1)]

def add_city(self, name):
    """Добавление нового города"""
    try:
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO cities (name) VALUES (?)', (name,))
        conn.commit()
        city_id = cursor.lastrowid
        self.close()
        return {'id': city_id, 'name': name, 'status': 'активный'}
    except Exception as e:
        print(f"[ERROR] Ошибка добавления города: {e}")
        return None

def delete_city(self, city_id):
    """Мягкое удаление города"""
    try:
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE cities SET status = 'удалён' WHERE id = ?", (city_id,))
        conn.commit()
        self.close()
        return True
    except Exception as e:
        print(f"[ERROR] Ошибка удаления города: {e}")
        return False

def delete_agent(self, agent_id):
    """Мягкое удаление агента"""
    try:
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE agents SET status = 'удалён' WHERE id = ?", (agent_id,))
        conn.commit()
        self.close()
        DatabaseManager._agent_colors_cache = None
        return True
    except Exception as e:
        print(f"[ERROR] Ошибка удаления агента: {e}")
        return False
```

---

## 7. Permissions (права доступа)

### 7.1 Новые права

**Файл:** `server/permissions.py`

Добавить в `ALL_PERMISSIONS` (строка 57-58):

```python
# Агенты
"agents.create": "Создание агентов",
"agents.update": "Редактирование агентов",
"agents.delete": "Удаление агентов",       # NEW
# Города
"cities.create": "Создание городов",        # NEW
"cities.delete": "Удаление городов",        # NEW
```

Добавить в `_BASE_MANAGER` (строка 95-96):

```python
"agents.create",
"agents.update",
"agents.delete",    # NEW
"cities.create",    # NEW
"cities.delete",    # NEW
```

### 7.2 Обновление матрицы UI

**Файл:** `ui/permissions_matrix_widget.py:42`

```python
'Агенты': ['agents.create', 'agents.update', 'agents.delete'],
'Города': ['cities.create', 'cities.delete'],  # NEW
```

**Файл:** `ui/permissions_matrix_widget.py:120`

```python
"agents.create": "Создание агентов",
"agents.update": "Редактирование агентов",
"agents.delete": "Удаление агентов",       # NEW
"cities.create": "Создание городов",        # NEW
"cities.delete": "Удаление городов",        # NEW
```

---

## 8. Test Strategy

### 8.1 E2E тесты — новые endpoints

**Файл:** `tests/e2e/test_cities_crud.py` (НОВЫЙ)

```python
"""E2E тесты для CRUD городов"""
import pytest

class TestCitiesCRUD:
    """Тесты endpoints /api/v1/cities"""

    def test_get_cities_returns_seeded_defaults(self, auth_client):
        """GET /cities возвращает города из seed (СПБ, МСК, ВН)"""
        resp = auth_client.get("/api/v1/cities")
        assert resp.status_code == 200
        names = [c["name"] for c in resp.json()]
        assert "СПБ" in names
        assert "МСК" in names

    def test_add_city(self, auth_client_manager):
        """POST /cities создаёт новый город"""
        resp = auth_client_manager.post(
            "/api/v1/cities", json={"name": "КЗН"}
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "КЗН"

    def test_add_duplicate_city_returns_400(self, auth_client_manager):
        """POST /cities с существующим именем → 400"""
        auth_client_manager.post("/api/v1/cities", json={"name": "ДУБЛЬ"})
        resp = auth_client_manager.post("/api/v1/cities", json={"name": "ДУБЛЬ"})
        assert resp.status_code == 400

    def test_delete_city(self, auth_client_manager):
        """DELETE /cities/{id} — мягкое удаление"""
        # Создаём город
        resp = auth_client_manager.post(
            "/api/v1/cities", json={"name": "УДАЛИТЬ"}
        )
        city_id = resp.json()["id"]

        # Удаляем
        resp = auth_client_manager.delete(f"/api/v1/cities/{city_id}")
        assert resp.status_code == 200

        # Проверяем что его нет в списке
        resp = auth_client_manager.get("/api/v1/cities")
        names = [c["name"] for c in resp.json()]
        assert "УДАЛИТЬ" not in names

    def test_delete_city_with_contracts_returns_409(self, auth_client_manager, create_contract_with_city):
        """DELETE /cities/{id} при наличии активных договоров → 409"""
        city_id = create_contract_with_city("ЗАНЯТ")
        resp = auth_client_manager.delete(f"/api/v1/cities/{city_id}")
        assert resp.status_code == 409

    def test_readd_deleted_city_restores_it(self, auth_client_manager):
        """POST /cities с удалённым городом — восстанавливает"""
        resp = auth_client_manager.post("/api/v1/cities", json={"name": "ВОССТ"})
        city_id = resp.json()["id"]
        auth_client_manager.delete(f"/api/v1/cities/{city_id}")

        resp = auth_client_manager.post("/api/v1/cities", json={"name": "ВОССТ"})
        assert resp.status_code == 200
```

**Файл:** `tests/e2e/test_agents_delete.py` (НОВЫЙ)

```python
"""E2E тесты для удаления агентов"""
import pytest

class TestAgentsDelete:
    def test_delete_agent(self, auth_client_manager):
        """DELETE /agents/{id} — мягкое удаление"""
        # Создаём агента
        resp = auth_client_manager.post(
            "/api/v1/agents", json={"name": "ТЕСТ_УДАЛ", "color": "#FF0000"}
        )
        agent_id = resp.json()["id"]

        # Удаляем
        resp = auth_client_manager.delete(f"/api/v1/agents/{agent_id}")
        assert resp.status_code == 200

        # Проверяем что его нет в списке
        resp = auth_client_manager.get("/api/v1/agents")
        names = [a["name"] for a in resp.json()]
        assert "ТЕСТ_УДАЛ" not in names

    def test_delete_agent_with_contracts_returns_409(self, auth_client_manager, create_contract_with_agent):
        """DELETE /agents/{id} при наличии активных договоров → 409"""
        agent_id = create_contract_with_agent("ЗАНЯТ_АГЕНТ")
        resp = auth_client_manager.delete(f"/api/v1/agents/{agent_id}")
        assert resp.status_code == 409

    def test_delete_nonexistent_agent_returns_404(self, auth_client_manager):
        """DELETE /agents/99999 → 404"""
        resp = auth_client_manager.delete("/api/v1/agents/99999")
        assert resp.status_code == 404

    def test_delete_requires_permission(self, auth_client_designer):
        """DELETE /agents/{id} без права agents.delete → 403"""
        resp = auth_client_designer.delete("/api/v1/agents/1")
        assert resp.status_code == 403
```

### 8.2 DB тесты

**Файл:** `tests/db/test_cities_local.py` (НОВЫЙ)

```python
"""Тесты локальной БД для городов (SQLite, без сервера)"""

def test_cities_table_created_on_migration(db_manager):
    """Миграция создаёт таблицу cities"""
    conn = db_manager.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cities'")
    assert cursor.fetchone() is not None

def test_cities_seeded_from_config(db_manager):
    """Seed заполняет города из config.py"""
    cities = db_manager.get_all_cities()
    names = [c['name'] for c in cities]
    assert 'СПБ' in names
    assert 'МСК' in names
    assert 'ВН' in names

def test_add_and_get_city(db_manager):
    """Добавление и получение города"""
    db_manager.add_city('ТЕСТ')
    cities = db_manager.get_all_cities()
    names = [c['name'] for c in cities]
    assert 'ТЕСТ' in names

def test_delete_city_soft(db_manager):
    """Мягкое удаление — город не появляется в get_all_cities"""
    result = db_manager.add_city('УДАЛИТЬ')
    db_manager.delete_city(result['id'])
    cities = db_manager.get_all_cities()
    names = [c['name'] for c in cities]
    assert 'УДАЛИТЬ' not in names
```

### 8.3 Что НЕ тестируем автоматически

- UI виджет `AgentsCitiesWidget` — тестируется вручную (PyQt5 UI тесты через отдельный фреймворк)
- Визуальное отображение цвета агентов — ручная проверка

---

## 9. ADR (Architecture Decision Records)

### ADR-1: Города переносятся в БД

**Контекст:** Города хранятся в `config.py:95` как жёсткий список. Добавление нового города из UI (`contract_dialogs.py:1764`) работает только в рамках текущей сессии — при перезапуске всё теряется. Тарифы (`rates_dialog.py:427`) также берут города из config.

**Решение:** Создать таблицу `cities` в PostgreSQL (сервер) и SQLite (клиент). Seed начальных данных из `config.py:CITIES`.

**Обоснование:**
- Данные, управляемые пользователем, должны храниться в БД
- Единый источник правды для всех клиентов (multi-user CRM)
- Возможность удаления/добавления без пересборки приложения

**Последствия:**
- `config.py:CITIES` остаётся как fallback последней инстанции
- `rates_dialog.py:_get_all_cities()` нужно обновить для загрузки из DataAccess
- Все ComboBox городов загружаются из DataAccess вместо config

### ADR-2: Мягкое удаление (soft delete) для агентов и городов

**Контекст:** Агенты и города используются как строковые ссылки в `contracts.agent_type` и `contracts.city`. Жёсткое удаление (DELETE FROM) может нарушить целостность данных.

**Решение:** Soft delete через поле `status = 'удалён'`. GET endpoints по умолчанию фильтруют удалённые записи.

**Обоснование:**
- Сохранение ссылочной целостности (строковые FK в contracts)
- Возможность восстановления (re-add = восстановление для городов)
- Исторические отчёты продолжают работать

**Последствия:**
- GET endpoints получают параметр `include_deleted` для админских нужд
- При повторном добавлении удалённого города — восстанавливается `status = 'активный'`
- `get_all_agents()` на клиенте тоже должен фильтровать `status != 'удалён'`

### ADR-3: Строковые ссылки (НЕ FK) между contracts и agents/cities

**Контекст:** `Contract.agent_type` (строка 308) и `Contract.city` (строка 309) хранят имена строками, а не id. Нет настоящих ForeignKey.

**Решение:** Оставить как есть. НЕ менять на FK.

**Обоснование:**
- Массовая миграция (переход на FK) затрагивает все существующие контракты
- Ломает offline-режим (SQLite не знает о серверных id)
- Риск несовместимости слишком высок для данного изменения
- Защита от удаления (409 при наличии активных контрактов) решает проблему целостности

### ADR-4: Управление агентами и городами — в администрировании, а не в карточке договора

**Контекст:** Кнопки управления агентами и городами расположены в `ContractDialog` — диалоге создания/редактирования договора. Это смешивает роли: менеджер при создании договора не должен управлять справочниками.

**Решение:** Перенести в `AdminDialog` (5-я вкладка "Агенты и города"). В `ContractDialog` оставить только ComboBox для выбора.

**Обоснование:**
- Разделение ответственности (SRP)
- Управление справочниками — административная функция
- Доступ через систему прав (`agents.create`, `cities.create` и т.д.)
- `AdminDialog` уже содержит другие настройки (права, тарифы, нормо-дни)

---

## 10. Порядок реализации (Implementation Order)

```
Фаза 1: Сервер (БД + API)
  1.1  server/database.py — модель City
  1.2  server/routers/cities_router.py — CRUD endpoints
  1.3  server/routers/agents_router.py — DELETE endpoint + фильтрация удалённых
  1.4  server/permissions.py — agents.delete, cities.create, cities.delete
  1.5  server/main.py — include_router + seed_cities
  1.6  Docker rebuild

Фаза 2: Клиент — слой данных
  2.1  database/db_manager.py — миграция cities, CRUD методы
  2.2  utils/api_client/misc_mixin.py — delete_agent, cities CRUD
  2.3  utils/data_access.py — delete_agent, cities CRUD с fallback

Фаза 3: Клиент — UI
  3.1  ui/agents_cities_widget.py — новый виджет
  3.2  ui/admin_dialog.py — 5-я вкладка
  3.3  ui/contract_dialogs.py — удалить кнопки, добавить reload_cities()
  3.4  ui/contract_dialogs.py — удалить AgentDialog, add_city()
  3.5  ui/permissions_matrix_widget.py — обновить матрицу прав
  3.6  ui/rates_dialog.py — загрузка городов из DataAccess

Фаза 4: Тесты
  4.1  tests/e2e/test_cities_crud.py
  4.2  tests/e2e/test_agents_delete.py
  4.3  tests/db/test_cities_local.py
```

---

## 11. Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Потеря городов при обновлении (seed перезаписывает пользовательские) | Низкая | Высокое | `INSERT OR IGNORE` / `ON CONFLICT DO NOTHING` |
| Удаление агента с активными договорами | Средняя | Высокое | Проверка 409 Conflict перед soft delete |
| Offline-режим: города не синхронизированы | Средняя | Среднее | Fallback на config.py + offline queue |
| rates_dialog ломается без городов из БД | Низкая | Среднее | Fallback `_get_all_cities()` на config |
| AdminDialog слишком широкий (5 вкладок) | Низкая | Низкое | minSize увеличить до 1100x700 если нужно |

---

## 12. Список затронутых файлов

### Сервер (изменения)
| Файл | Действие | Описание |
|------|----------|----------|
| `server/database.py:174` | EDIT | Добавить модель `City` |
| `server/routers/agents_router.py` | EDIT | Добавить `DELETE /{agent_id}`, фильтрация удалённых в GET |
| `server/routers/cities_router.py` | NEW | Полный CRUD для городов |
| `server/permissions.py:57-58` | EDIT | Добавить `agents.delete`, `cities.create`, `cities.delete` |
| `server/permissions.py:95-96` | EDIT | Добавить в `_BASE_MANAGER` |
| `server/main.py:351` | EDIT | `include_router(cities_router)` + seed |
| `server/schemas.py` | NO CHANGE | Схемы inline в роутерах (как agents_router) |

### Клиент (изменения)
| Файл | Действие | Описание |
|------|----------|----------|
| `ui/agents_cities_widget.py` | NEW | Виджет управления агентами и городами |
| `ui/admin_dialog.py:81-98` | EDIT | Добавить 5-ю вкладку |
| `ui/contract_dialogs.py:400-424` | EDIT | Убрать кнопки, добавить reload_cities() |
| `ui/contract_dialogs.py:1742-1877` | DELETE | Удалить add_agent(), add_city() |
| `ui/contract_dialogs.py:4207+` | DELETE | Удалить класс AgentDialog |
| `ui/permissions_matrix_widget.py:42` | EDIT | Добавить rights для cities |
| `ui/rates_dialog.py:425` | EDIT | Обновить _get_all_cities() |
| `utils/api_client/misc_mixin.py:185` | EDIT | Добавить delete_agent, cities CRUD |
| `utils/data_access.py:1527` | EDIT | Добавить delete_agent, cities CRUD |
| `database/db_manager.py` | EDIT | Миграция cities, CRUD методы |
| `config.py:95` | NO CHANGE | CITIES остаётся как fallback |

### Тесты (новые)
| Файл | Описание |
|------|----------|
| `tests/e2e/test_cities_crud.py` | E2E тесты CRUD городов |
| `tests/e2e/test_agents_delete.py` | E2E тесты удаления агентов |
| `tests/db/test_cities_local.py` | Тесты SQLite для городов |
