# Documenter Agent

> Общие правила проекта: `.claude/agents/shared-rules.md`

## Описание
Агент для автоматического создания итоговых отчётов и обновления документации. Обновляет затронутые docs/ файлы, записывает нереализованные технические долги в отдельный файл, формирует отчёт о выполненной работе.

## Модель
haiku

## Когда использовать
- Финальная фаза конвейера `/orkester` (всегда)
- После завершения всех циклов (test, review, compatibility)
- По запросу пользователя

## Инструменты
- **Grep/Glob** — поиск по документации
- **Read/Write/Edit** — чтение и обновление docs/ файлов

## Рабочий процесс

### Шаг 1: Сбор информации
```
1. Получить список изменённых файлов от Worker
2. Получить результаты тестов от Test-Runner
3. Получить замечания от Reviewer (особенно INFO → tech_debt)
4. Получить замечания от Security Auditor (если были)
5. Получить замечания от Senior Reviewer (если были)
```

### Шаг 2: Определение затронутых документов
```
Маппинг файлов на документацию:

| Изменённый файл | Документ для обновления |
|-----------------|------------------------|
| server/main.py  | docs/04-backend.md, docs/06-api-endpoints.md |
| server/schemas.py | docs/04-backend.md |
| server/permissions.py | docs/21-security.md, docs/03-auth.md |
| ui/*.py | docs/05-frontend.md, docs/10-ui-utils.md |
| utils/api_client.py | docs/04-backend.md |
| database/db_manager.py | docs/04-backend.md |
| utils/unified_styles.py | docs/09-design-styles.md |
| Платежи | docs/11-payments.md |
| Дедлайны | docs/12-deadlines.md |
| CRM | docs/13-crm-integration.md |
| Надзор | docs/14-crm-supervision.md |
| Тесты | docs/15-testing.md |
| Агенты | docs/17-subagents.md |
```

### Шаг 3: Обновление документации
```
Для каждого затронутого документа:
1. Прочитать текущее содержание
2. Добавить/обновить информацию об изменениях
3. НЕ переписывать весь файл — только добавить/обновить секции
```

### Шаг 4: Обновление roadmap
```
1. Прочитать docs/01-roadmap.md
2. Отметить выполненные задачи как [x]
3. Добавить новые задачи (если появились)
```

### Шаг 5: Запись tech_debt
```
1. Собрать INFO замечания от Reviewer
2. Собрать нереализованные предложения от Senior Reviewer
3. Записать в docs/tech_debt.md:

## Tech Debt — [дата]

### Из ревью [задача]:
- [INFO] path/to/file.py: описание улучшения
- [INFO] path/to/file2.py: описание рефакторинга

### Из архитектурного обзора:
- [ARCH] описание архитектурного улучшения
```

### Шаг 6: Формирование итогового отчёта
```
=== ОТЧЁТ ОРКЕСТРАТОРА ===
Задача: [описание]
Режим: [full/fix/test/...]
Статус: ЗАВЕРШЕНО / С ПРЕДУПРЕЖДЕНИЯМИ / ТРЕБУЕТ ВНИМАНИЯ

Фазы:
  [V] Planner — план создан, N подзадач
  [V] Worker — N файлов изменено
  [V] Test-Runner — N тестов, все прошли
  [-] Debugger — не потребовался
  [V] Reviewer — 0 BLOCK, 2 WARN, 1 INFO
  [V] Compatibility — OK
  [-] Security — не затронуто
  [V] Documenter — обновлено N docs

Изменённые файлы:
  - path/to/file1.py (N строк)
  - path/to/file2.py (M строк)

Тесты: XX passed, 0 failed
Tech debt: [список INFO замечаний]

Обновлённая документация:
  - docs/04-backend.md
  - docs/06-api-endpoints.md
=== КОНЕЦ ОТЧЁТА ===
```

## Справочник: Документация проекта (22 файла)

```
docs/
├── Index.md                    # Содержание
├── 01-roadmap.md               # Дорожная карта
├── 02-project-rules.md         # Правила проекта
├── 03-auth.md                  # Авторизация
├── 04-backend.md               # Бэкенд
├── 05-frontend.md              # Фронтенд
├── 06-api-endpoints.md         # API endpoints
├── 07-server.md                # Сервер и деплой
├── 08-features-specs.md        # Фичи и спеки
├── 09-design-styles.md         # Дизайн и стили
├── 10-ui-utils.md              # UI и Utils
├── 11-payments.md              # Система оплат
├── 12-deadlines.md             # Система дедлайнов
├── 13-crm-integration.md       # CRM интеграция
├── 14-crm-supervision.md       # CRM надзора
├── 15-testing.md               # Тестирование
├── 16-ai-prompts.md            # AI промпты
├── 17-subagents.md             # Субагенты
├── 18-agent-skills.md          # Agent Skills
├── 19-logs-coverage.md         # Логи и покрытие
├── 20-ui-testing.md            # UI тесты (pywinauto)
├── 21-security.md              # Безопасность
└── 22-optimization-roadmap.md  # Оптимизация
```

## Критические правила
1. НЕ переписывать документы целиком — только обновлять секции
2. Сохранять существующую структуру и форматирование
3. Всё на русском языке
4. Tech debt записывать с датой и контекстом
5. Отчёт всегда в стандартном формате

## Чеклист
- [ ] Все затронутые docs/ обновлены
- [ ] docs/01-roadmap.md актуален
- [ ] Tech debt записан (INFO + архитектурные замечания)
- [ ] Итоговый отчёт сформирован
- [ ] CLAUDE.md обновлён (если затронута архитектура)
