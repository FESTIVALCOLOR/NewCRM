# Методология поиска багов — Interior Studio CRM

## Обзор

Проактивный аудит кодовой базы для нахождения реальных багов до того, как их найдут пользователи.
Методология выработана в ходе аудита 60+ багов в марте 2026 года.

## Категории багов (по частоте)

### 1. Прямой SQL вместо DataAccess (КРИТИЧЕСКИЙ)
**Паттерн:** `cursor.execute()`, `execute_raw_query()`, `execute_raw_update()`, `self.data.db.connect()`
**Почему баг:** В online-режиме пишет только в локальную SQLite, изменения не попадают на сервер (PostgreSQL). Другие пользователи не видят изменений.
**Grep-запрос:**
```bash
Grep "cursor\.execute|execute_raw_query|execute_raw_update|\.db\.connect\(\)" ui/
```
**Исправление:** Заменить на вызовы DataAccess (`self.data.create_*`, `self.data.update_*`, `self.data.delete_*`).

### 2. NoneType crash при итерации (ВЫСОКИЙ)
**Паттерн:** `for item in self.data.get_something()` без `or []`
**Почему баг:** DataAccess методы возвращают `None` если API недоступен и локальная БД пуста. `for x in None` → `TypeError`.
**Grep-запрос:**
```bash
Grep "for \w+ in self\.data\." ui/ --output_mode content
```
Проверить каждое вхождение: есть ли `or []` после вызова.

### 3. CustomMessageBox вместо CustomQuestionBox (СРЕДНИЙ)
**Паттерн:** `CustomMessageBox(self, ..., 'question')` или `QMessageBox.question` или сравнение с `QMessageBox.Yes`
**Почему баг:** `CustomMessageBox` имеет только кнопку OK и всегда возвращает `Accepted`. Пользователь не может отменить операцию.
**Grep-запрос:**
```bash
Grep "CustomMessageBox.*question|QMessageBox\.question|QMessageBox\.Yes" ui/
```
**Правило:** Подтверждения (Yes/No) → `CustomQuestionBox`. Информирование (OK) → `CustomMessageBox`.
Сравнение: `reply.exec_() == QDialog.Accepted` (НЕ `QMessageBox.Yes`).

### 4. Отсутствие offline-очереди в DataAccess (ВЫСОКИЙ)
**Паттерн:** DataAccess метод вызывает API без `_queue_operation` в except
**Почему баг:** При потере сети изменения теряются. Offline-очередь должна буферизировать операции.
**Grep-запрос:**
```bash
Grep "def (create|update|delete)_" utils/data_access.py --output_mode content
```
Проверить каждый метод: есть ли `_queue_operation` в except и elif ветках.

### 5. Двойное подключение сигналов Qt (СРЕДНИЙ)
**Паттерн:** `.connect()` в `showEvent()` или в цикле без защиты
**Почему баг:** При каждом открытии диалога обработчик подключается заново. Действие выполняется N раз.
**Grep-запрос:**
```bash
Grep "def showEvent" ui/ --output_mode content -A 10
```
Искать `.connect()` вызовы внутри showEvent без `hasattr` guard.

### 6. prefer_local обход API (СРЕДНИЙ)
**Паттерн:** `self.data.prefer_local = True` перед загрузкой данных
**Почему баг:** Принудительно читает из локальной SQLite вместо API. Пользователь не видит свежие данные.
**Grep-запрос:**
```bash
Grep "prefer_local\s*=\s*True" ui/
```

### 7. Dead code (дублирующие методы) (НИЗКИЙ)
**Паттерн:** Два метода с одинаковым именем в одном классе (Python берёт последний)
**Почему баг:** Первый метод "мёртвый" — никогда не вызывается. Часто содержит устаревшую логику.
**Grep-запрос:**
```bash
Grep "def (\w+)\(" ui/file.py | sort | uniq -d
```

### 8. Прямой SQL в фоновых потоках (КРИТИЧЕСКИЙ)
**Паттерн:** `DatabaseManager()` + `connect()` + `cursor.execute()` в `threading.Thread`
**Почему баг:** Дублирует DataAccess + потоконебезопасно (SQLite write lock) + f-string SQL injection.
**Grep-запрос:**
```bash
Grep "DatabaseManager\(\)" ui/
```

### 9. Авторасчёт с граничными значениями (СРЕДНИЙ)
**Паттерн:** Таблицы пороговых значений с `return 0` для значений за пределами таблицы
**Проверка:** Искать `return 0` после цикла по thresholds.

### 10. Утечка виджетов Qt (НИЗКИЙ)
**Паттерн:** `self.sender()` после `setRowCount(0)` — виджет уже уничтожен
**Почему баг:** `setRowCount(0)` уничтожает cellWidgets, включая кнопку-sender. `RuntimeError: wrapped C/C++ object has been deleted`.

## Процедура аудита

### Шаг 1: Автоматическое сканирование
Запустить скрипт `scripts/bug_scanner.py` — находит потенциальные баги по паттернам.

### Шаг 2: Ручная верификация
Каждое найденное место проверить вручную:
1. Прочитать контекст (±20 строк)
2. Проверить есть ли try/except или `or []` защита
3. Проверить есть ли DataAccess метод для замены
4. Классифицировать: баг / ложное срабатывание / tech debt

### Шаг 3: Исправление
1. Применить минимальное исправление
2. Запустить тесты затронутого модуля
3. Закоммитить с описанием бага

### Шаг 4: Документирование
Обновить этот документ если найден новый паттерн бага.

## Статистика аудитов

| Дата | Файлов проверено | Багов найдено | Критических | Ложных |
|------|-----------------|---------------|-------------|--------|
| 2026-03-06 | 12 | 60+ | 15 | 5 |

## Агент и инструменты

- **Агент:** `.claude/agents/bug-hunter-agent.md` — субагент для оркестратора
- **Скилл:** `/bug-hunt` — ручной запуск аудита
- **Скрипт:** `scripts/bug_scanner.py` — автоматический сканер паттернов
