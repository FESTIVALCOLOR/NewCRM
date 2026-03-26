# GitHub & Web Search Results

## Поисковые запросы и результаты

### 1. Schemathesis — API fuzzing
- **Repo:** [schemathesis/schemathesis](https://github.com/schemathesis/schemathesis) — 2100+ stars
- **Описание:** Property-based API testing from OpenAPI/GraphQL schemas
- **Совместимость:** Python 3.9+, FastAPI, OpenAPI 3.x
- **Релевантность:** 10/10
- **Рекомендация:** УСТАНОВИТЬ НЕМЕДЛЕННО

### 2. pytest-qt — UI тестирование через qtbot
- **Repo:** [pytest-dev/pytest-qt](https://github.com/pytest-dev/pytest-qt) — 447 stars, MIT
- **Описание:** pytest plugin for PyQt5/PyQt6/PySide testing
- **Совместимость:** PyQt5, Python 3.8+, последний push: 2026-03-02
- **Статус:** УЖЕ УСТАНОВЛЕН (pytest-qt>=4.4.0)
- **Релевантность:** 10/10 — единственный зрелый инструмент для реального PyQt5 тестирования
- **Рекомендация:** Переписать тесты с моков на реальные виджеты

### 3. Hypothesis — property-based testing
- **Repo:** [HypothesisWorks/hypothesis](https://github.com/HypothesisWorks/hypothesis) — 7500+ stars
- **Описание:** Property-based testing with auto-generated test cases
- **Совместимость:** Python 3.8+
- **Релевантность:** 8/10
- **Рекомендация:** Установить для расчётных функций

### 4. PyAutoGUI — desktop automation (НЕ РЕКОМЕНДУЕТСЯ)
- **Repo:** [asweigart/pyautogui](https://github.com/asweigart/pyautogui) — 12326 stars, BSD
- **Статус:** УЖЕ УСТАНОВЛЕН, но МЁРТВЫЙ проект (последний push 2024-08-20)
- **Ограничения:** координатный подход, не понимает Qt, 577 open issues
- **Релевантность:** 4/10
- **Рекомендация:** Использовать ТОЛЬКО для скриншотов, заменить на pytest-qt qtbot для взаимодействия

### 5. Playwright MCP
- **Repo:** [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) — MCP сервер
- **Описание:** Управление браузером через MCP
- **Применимость для проекта:** 6/10 — только для API через Swagger UI
- **Рекомендация:** Подключить как вспомогательный

### 6. pywinauto — accessibility tree тестирование
- **Repo:** [pywinauto/pywinauto](https://github.com/pywinauto/pywinauto)
- **Описание:** Windows GUI automation through accessibility tree (UIA)
- **Совместимость:** Qt5 через `backend="uia"` + `QT_USE_NATIVE_WINDOWS=1`
- **Релевантность:** 7/10
- **Рекомендация:** Установить для тестирования запущенного приложения

### Не рекомендуются
- **Appium/WinAppDriver** (2/10) — WinAppDriver заморожен Microsoft, Qt-совместимость плохая
- **testRigor** (4/10) — платный SaaS, тестирует через RDP, русский UI проблема
- **Claude Code MCP для тестирования** (3/10) — MCP-экосистема заточена под веб
- **Applitools/Percy** (5/10) — визуальные регрессии, но нет нативной Qt-интеграции

### 7. Web Sources
- [Schemathesis: Boost FastAPI reliability](https://medium.com/@jeremy3/boost-your-fastapi-reliability-with-schemathesis-automated-testing-e8b70ff704f6)
- [pytest-qt Tutorial](https://pytest-qt.readthedocs.io/en/latest/tutorial.html)
- [Playwright MCP + Claude Code](https://til.simonwillison.net/claude-code/playwright-mcp-claude-code)
- [AI QA Engineer with Claude Code](https://alexop.dev/posts/building_ai_qa_engineer_claude_code_playwright/)
- [12 AI Test Automation Tools 2026](https://testguild.com/7-innovative-ai-test-automation-tools-future-third-wave/)
