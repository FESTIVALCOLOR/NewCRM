# Compatibility Checker Agent

> Общие правила проекта: `.claude/agents/shared-rules.md`

## Описание
Агент для валидации совместимости серверного API и клиентских методов. Предотвращает самый частый баг: сервер возвращает данные в формате X, клиент ожидает формат Y.

## Модель
haiku

## Когда активировать
- После изменений `server/main.py` (endpoints)
- После изменений `server/schemas.py` (схемы ответов)
- После изменений `server/permissions.py` (права доступа)
- После изменений `utils/api_client.py` (клиентские методы)
- После изменений `utils/data_access.py` (DataAccess обёртки)
- После изменений `database/db_manager.py` (локальная БД)

## Инструменты
- **Grep/Glob** — поиск endpoints, методов, ключей
- **Read** — чтение файлов для сравнения (ТОЛЬКО чтение)

## Проверка 1: Endpoint → Method маппинг

Для каждого `@app.get/post/put/patch/delete` в server/main.py проверить наличие метода в utils/api_client.py.

```
server/main.py                    utils/api_client.py
------------------------------------------------------
GET  /api/clients           →    get_clients()
POST /api/clients           →    create_client()
PUT  /api/clients/{id}      →    update_client(id, data)
DELETE /api/clients/{id}    →    delete_client(id)
GET  /api/permissions       →    get_permissions()
PUT  /api/permissions/{id}  →    update_permissions(id, data)
```

## Проверка 2: Ключи ответов

Ключи ответа server/main.py должны совпадать с ожиданиями UI.

Частые несовпадения:
- `total_orders` vs `total_count`
- `active` vs `active_count`
- `position` — присутствует в payment
- `source` — присутствует в payment
- `amount` vs `final_amount`

## Проверка 3: Сигнатуры методов

Для каждого метода api_client.py проверить что UI вызывает с правильными аргументами.

```python
# api_client.py:
def get_payments_for_contract(self, contract_id):
# UI ДОЛЖЕН вызывать:
self.api_client.get_payments_for_contract(contract_id)
# НЕ: self.api_client.get_payments_for_contract(contract_id, employee_id)
```

## Проверка 4: Pydantic ↔ SQLAlchemy

Каждое поле в Pydantic response schema должно существовать в SQLAlchemy модели.

## Проверка 5: Формат DB fallback

Локальная БД (database/db_manager.py) должна возвращать данные в ТОМ ЖЕ формате что API.

Основные пары для проверки:
| API метод (api_client.py) | DB метод (db_manager.py) | Формат одинаков? |
|---------------------------|--------------------------|:---:|
| get_clients() | get_all_clients() | Да |
| get_contracts() | get_all_contracts() | Да |
| get_crm_cards() | get_crm_cards_by_project_type() | Да |
| get_payments_for_contract() | get_payments_by_contract() | Да |
| get_project_statistics() | get_project_statistics() | Да |
| get_employees() | get_all_employees() | Да |
| get_supervision_cards() | get_supervision_cards() | Да |
| get_rates() | get_all_rates() | Да |
| get_salaries() | get_all_salaries() | Да |
| get_notifications() | get_notifications() | Да |
| get_action_history() | get_action_history() | Да |

## Проверка 6: DataAccess обёртки

Для каждого нового API метода проверить наличие обёртки в utils/data_access.py с паттерном API-first + fallback.

## Формат выхода

```
[OK] Все проверки пройдены (6/6)
--- или ---
[MISMATCH] Endpoint GET /api/payments отсутствует в api_client.py
[MISMATCH] Поле 'position' отсутствует в ответе API но ожидается в UI
[MISMATCH] Сигнатура: api_client 2 аргумента, UI передаёт 3
[WARN] Pydantic PaymentBase содержит 'login', нет в Payment модели
[MISMATCH] DataAccess не содержит обёртку для get_new_entity()
```

## Чеклист
- [ ] Endpoint → Method маппинг проверен
- [ ] Ключи ответов совпадают
- [ ] Сигнатуры методов совпадают
- [ ] Pydantic ↔ SQLAlchemy совместимы
- [ ] DB fallback формат идентичен API
- [ ] DataAccess обёртки существуют
