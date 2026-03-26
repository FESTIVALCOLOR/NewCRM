# Исследование: Мобильное PWA + Встроенный чат для Interior Studio CRM

**Дата:** 2026-03-23
**Статус:** Исследование завершено

---

## 1. Итоговая рекомендация

### Стек решения

| Компонент | Технология | Почему |
|-----------|-----------|--------|
| **Мобильное приложение** | PWA (Quasar Framework + Vue 3) | Один код на Android/iOS/планшеты, без магазинов, обновления мгновенные |
| **Чат (бэкенд)** | FastAPI WebSocket (встроенный) | Уже есть в uvicorn[standard], 0 новых зависимостей |
| **Чат (фронтенд)** | Quasar QChatMessage + QInfiniteScroll | Готовые компоненты чат-пузырей |
| **Файлы** | Яндекс.Диск (уже интегрирован) | HTTP POST загрузка + WebSocket уведомление |
| **Push-уведомления** | Web Push VAPID (PWA) + Telegram Bot (desktop) | Бесплатно, без зависимости от Google |
| **БД** | PostgreSQL (4 новые таблицы) | Уже есть, расширяем |

### Что НЕ нужно

- **Centrifugo** — overkill для 50-100 пользователей (нужен при 500+)
- **Redis** — не нужен при 1 uvicorn worker (текущая конфигурация)
- **Socket.IO** — свой протокол поверх WS, лишняя зависимость
- **Chatwoot** — для customer support, не для team chat
- **APK/IPA** — проблемы с установкой и обновлениями
- **Flutter/React Native** — дольше, сложнее, а PWA покрывает 95% потребностей

---

## 2. PWA — как работает "приложение по ссылке"

### Установка пользователем

```
1. Получает ссылку в welcome-письме: https://crm.festivalcolor.ru
2. Открывает в браузере (Chrome/Safari)
3. Android: баннер "Установить" → системный промпт → иконка на рабочем столе
   iOS: "Поделиться" → "На экран Домой" → иконка на рабочем столе
4. Открывает иконку → приложение запускается БЕЗ адресной строки (standalone)
```

### Ключевые файлы

**manifest.json** — определяет поведение PWA:
```json
{
  "name": "Interior Studio CRM",
  "short_name": "IS CRM",
  "display": "standalone",
  "orientation": "any",
  "theme_color": "#1a1a2e",
  "background_color": "#ffffff",
  "start_url": "/?source=pwa",
  "scope": "/",
  "lang": "ru",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
```

**display: "standalone"** — убирает адресную строку и табы, оставляет системный status bar (часы, батарея). Именно это даёт ощущение нативного приложения.

### iOS особенности (обязательные meta-теги)

```html
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="IS CRM">
<link rel="apple-touch-icon" sizes="180x180" href="/icons/apple-touch-icon.png">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```

### Safe Areas (notch, Dynamic Island)

```css
body {
  padding-top: env(safe-area-inset-top);
  padding-bottom: env(safe-area-inset-bottom);
}
```

### iOS ограничения PWA

| Ограничение | Статус 2026 |
|-------------|-------------|
| Push Notifications | Работают с iOS 16.4+ (нужно добавить на Home Screen) |
| Background Sync | НЕ поддерживается |
| Хранилище | 50 MB лимит, данные удаляются через 7 дней неиспользования |
| Orientation Lock | НЕ работает |
| beforeinstallprompt | НЕ будет (только ручная инструкция) |

---

## 3. Quasar Framework — выбор и обоснование

### Почему Quasar, а не Vuetify/Ionic

| Критерий | Quasar | Vuetify 3 | Ionic Vue |
|----------|--------|-----------|-----------|
| PWA из коробки | Да (одна команда) | Ручная настройка | Частично |
| Mobile-first | Да | Desktop-first | Да |
| Компоненты чата | QChatMessage | Нет | Нет |
| Адаптивная таблица→карточки | QTable grid mode | Нет | Нет |
| Pull-to-refresh | QPullToRefresh | Нет | Да |
| Infinite scroll | QInfiniteScroll (reverse) | Нет | ion-infinite-scroll |
| CLI для PWA | `quasar dev -m pwa` | Нет | Ionic CLI |
| Размер бандла | ~80-120 KB | ~100-150 KB | ~60-100 KB |

### Быстрый старт

```bash
npm init quasar           # Создать проект (Vite + Vue 3)
quasar mode add pwa       # Добавить PWA
quasar dev -m pwa         # Разработка
quasar build -m pwa       # Сборка → dist/pwa/
```

### Ключевые компоненты для CRM

- **QTable** — `grid` prop переключает таблицу в карточки на мобильных
- **QChatMessage** — готовые чат-пузыри (sent/received, аватары, timestamps)
- **QLayout + QDrawer** — сайдбар с auto-overlay на мобильных (`breakpoint` prop)
- **QPullToRefresh** — потянуть для обновления
- **QInfiniteScroll** — подгрузка истории чата (`reverse` prop)
- **QUploader** — загрузка файлов (на мобильных предлагает камеру/галерею)

### Адаптивность — $q.screen

```javascript
import { useQuasar } from 'quasar'
const $q = useQuasar()

// Breakpoints: xs (<600), sm (600-1023), md (1024-1439), lg (1440-1919), xl (1920+)
$q.screen.xs  // true на телефонах
$q.screen.lt.md  // true на телефонах + маленьких планшетах
$q.screen.gt.sm  // true на планшетах горизонтально + десктопе
```

---

## 4. Чат — архитектура

### Схема БД (4 таблицы)

```sql
CREATE TABLE chat (
    id SERIAL PRIMARY KEY,
    guid UUID DEFAULT gen_random_uuid() UNIQUE,
    chat_type VARCHAR(10) NOT NULL,  -- 'direct', 'group', 'project'
    name VARCHAR(255),
    contract_id INTEGER REFERENCES contracts(id),  -- привязка к договору
    created_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE TABLE chat_participant (
    user_id INTEGER REFERENCES employees(id),
    chat_id INTEGER REFERENCES chat(id),
    role VARCHAR(20) DEFAULT 'member',  -- 'admin', 'member', 'client'
    joined_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (user_id, chat_id)
);

CREATE TABLE message (
    id SERIAL PRIMARY KEY,
    guid UUID DEFAULT gen_random_uuid() UNIQUE,
    chat_id INTEGER NOT NULL REFERENCES chat(id),
    user_id INTEGER NOT NULL REFERENCES employees(id),
    content TEXT NOT NULL,
    message_type VARCHAR(10) DEFAULT 'text',  -- 'text', 'file', 'system'
    is_edited BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE read_status (
    user_id INTEGER NOT NULL REFERENCES employees(id),
    chat_id INTEGER NOT NULL REFERENCES chat(id),
    last_read_message_id INTEGER REFERENCES message(id),
    PRIMARY KEY (user_id, chat_id)
);

CREATE TABLE message_attachment (
    id SERIAL PRIMARY KEY,
    message_id INTEGER NOT NULL REFERENCES message(id),
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_type VARCHAR(50),
    file_size INTEGER,
    thumbnail_path VARCHAR(1000),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_message_chat_created ON message(chat_id, created_at DESC);
CREATE INDEX idx_chat_participant_user ON chat_participant(user_id);
CREATE INDEX idx_read_status_user_chat ON read_status(user_id, chat_id);
CREATE INDEX idx_attachment_message ON message_attachment(message_id);
```

**Ключевое:** `read_status` — ОДНА строка на пользователя/чат (как WhatsApp), а не на каждое сообщение. Экономит место и ускоряет запросы.

### WebSocket endpoint

```python
# server/routers/chat_router.py
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    token = websocket.query_params.get("token")
    user = validate_jwt(token)  # проверка JWT

    await manager.connect(websocket, user.id)
    try:
        while True:
            data = await websocket.receive_json()
            # Обработка: new_message, typing, read, join_chat
            await handle_message(data, user, websocket)
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user.id)
```

### JWT через query parameter

Браузеры НЕ позволяют устанавливать заголовки при WebSocket подключении. Решение — передача токена в URL:
```
wss://crm.festivalcolor.ru/ws/chat?token=eyJhbGci...
```

### Файлы в чате

Паттерн: **HTTP POST для загрузки → WebSocket для уведомления**
- Загрузка файла через REST endpoint `/api/v1/chat/{guid}/upload`
- Файл сохраняется на Яндекс.Диск (интеграция уже есть)
- WebSocket broadcast уведомляет участников чата
- Для изображений генерируется thumbnail (Pillow)

### Производительность

| Метрика | Значение |
|---------|----------|
| Соединений на 1 async worker | ~10,000 |
| Память на соединение | ~20-50 KB |
| 50 пользователей | 0 проблем, ~2.5 MB RAM |
| Новые зависимости | 0 (websockets в uvicorn[standard]) |
| Нужен Redis | Нет (при 1 worker) |

---

## 5. Серверная готовность

### Что уже есть и переиспользуется (100%)

- FastAPI с 25+ роутерами
- JWT авторизация + RBAC (granular permissions)
- PostgreSQL с 35+ таблицами + Alembic миграции
- Nginx с WebSocket поддержкой (уже настроен!)
- Яндекс.Диск интеграция
- Email сервис (для welcome-писем с ссылкой)
- Docker (postgres + api + nginx)
- Telegram Bot (для push при закрытом приложении)
- Messenger таблицы (частично переиспользуются)

### Что нужно добавить

- WebSocket endpoint в FastAPI (~300 строк)
- ConnectionManager (~100 строк)
- 5 таблиц чата (миграция Alembic)
- REST endpoints для истории/файлов (~200 строк)
- Quasar PWA проект (папка `mobile/`)
- nginx location для раздачи PWA статики

---

## 6. Архитектура решения

```
┌─────────────────────────────────────────────────────┐
│                  Timeweb сервер                      │
│                                                      │
│  nginx (443)                                         │
│    ├── /              → PWA статика (Quasar build)   │
│    ├── /api/*         → FastAPI REST (уже есть)      │
│    └── /ws/*          → FastAPI WebSocket (добавить) │
│                                                      │
│  FastAPI (uvicorn, 1 worker)                         │
│    ├── REST endpoints (100% готовы)                   │
│    ├── WebSocket /ws/chat (добавить)                 │
│    ├── JWT auth (100% готов)                         │
│    └── Яндекс.Диск (100% готов)                     │
│                                                      │
│  PostgreSQL                                          │
│    ├── 35+ таблиц (100% готовы)                      │
│    └── 5 таблиц чата (добавить)                      │
└─────────────────────────────────────────────────────┘
        ↑            ↑              ↑
   PyQt5 Desktop  Смартфон PWA   Планшет PWA
   (уже есть)     (добавить)     (тот же код)
```

---

## 7. Структура PWA проекта

```
mobile/
├── public/
│   ├── icons/                    # Иконки PWA (192, 512, maskable)
│   └── splash/                   # Splash screens (iOS)
├── src/
│   ├── boot/
│   │   ├── axios.js              # API клиент + JWT interceptor
│   │   └── websocket.js          # WebSocket подключение
│   ├── stores/
│   │   ├── auth.js               # Авторизация (Pinia)
│   │   └── chat.js               # Состояние чата
│   ├── layouts/
│   │   ├── MainLayout.vue        # QLayout + QDrawer + bottom tabs
│   │   └── AuthLayout.vue        # Страница логина
│   ├── pages/
│   │   ├── LoginPage.vue         # Вход
│   │   ├── ChatListPage.vue      # Список чатов
│   │   ├── ChatPage.vue          # Окно чата (QChatMessage)
│   │   ├── ProjectsPage.vue      # Проекты/договоры
│   │   ├── CrmBoardPage.vue      # CRM-доска (свайп колонки)
│   │   ├── SupervisionPage.vue   # Надзор
│   │   ├── FilesPage.vue         # Файлы (Яндекс.Диск)
│   │   └── ProfilePage.vue       # Профиль
│   ├── components/
│   │   ├── ChatBubble.vue        # Обёртка QChatMessage
│   │   ├── FileUploader.vue      # Загрузка файлов/фото
│   │   ├── InstallBanner.vue     # Баннер установки PWA
│   │   └── AdaptiveTable.vue     # QTable с grid mode
│   └── css/
│       └── app.scss              # Стили + safe areas + media queries
├── src-pwa/
│   ├── register-service-worker.js
│   └── custom-service-worker.js
├── package.json
└── quasar.config.js
```

---

## 8. План реализации (поэтапный)

### Этап 1: Бэкенд чата (1-2 недели)
- Alembic миграция (5 таблиц)
- WebSocket endpoint + ConnectionManager
- REST: история сообщений, создание чата, участники
- Загрузка файлов в чат (Яндекс.Диск)
- Интеграция с PyQt5 десктоп-клиентом (QWebSocket)

### Этап 2: PWA — каркас + авторизация (1 неделя)
- Инициализация Quasar проекта
- JWT авторизация (логин/logout/refresh)
- QLayout + навигация (bottom tabs / drawer)
- nginx конфигурация для раздачи PWA
- manifest.json + Service Worker + иконки

### Этап 3: PWA — чат (2 недели)
- Список чатов с непрочитанными
- Окно чата (QChatMessage + QInfiniteScroll)
- WebSocket подключение (VueUse useWebSocket)
- Отправка/получение файлов
- Typing indicator + read status
- Создание чатов (direct / group / по проекту)

### Этап 4: PWA — CRM функционал (2-3 недели)
- Список клиентов / договоров (QTable grid mode)
- CRM-доска (свайп между колонками)
- Карточка проекта (просмотр + редактирование)
- Надзор (отчёты с фото)
- Файлы (Яндекс.Диск)

### Этап 5: Полировка (1 неделя)
- Push-уведомления (Web Push VAPID)
- Офлайн-кэш (Service Worker)
- Splash screens для iOS
- Install flow (баннер + iOS-инструкция)
- Welcome-письмо с ссылкой на установку

**Итого: 7-9 недель**

---

## 9. Ресурсы сервера

Текущий Timeweb сервер **справится** без изменений:

| Ресурс | Текущее использование | С PWA + чат |
|--------|----------------------|-------------|
| RAM | ~1 GB (FastAPI + PostgreSQL) | ~1.5 GB (+WebSocket + nginx кэш) |
| CPU | Минимальная | Минимальная (WebSocket = idle) |
| Диск | API + БД | +PWA статика (~5 MB) |
| Сеть | REST API | +WebSocket (минимальный трафик) |

WebSocket соединение в idle потребляет ~20-50 KB RAM. 100 пользователей = ~5 MB. Это ничтожно.

---

## 10. Референсные проекты

- **[notarious2/fastapi-chat](https://github.com/notarious2/fastapi-chat)** — полный чат на FastAPI + SQLAlchemy 2 + PostgreSQL (наш стек!)
- **[Centrifugo Grand Chat Tutorial](https://github.com/centrifugal/centrifugo)** — React + Django + Centrifugo (для будущего масштабирования)
- **[Quasar PWA docs](https://quasar.dev/quasar-cli-vite/developing-pwa/configuring-pwa/)** — официальная документация

---

## 11. Источники исследования

### PWA
- Quasar PWA Configuration: quasar.dev/quasar-cli-vite/developing-pwa/
- Web App Manifest: developer.mozilla.org/en-US/docs/Web/Manifest
- iOS PWA limitations 2025: firt.dev/notes/pwa-ios/
- PWA Install patterns: web.dev/learn/pwa/installation
- Service Worker strategies: developer.chrome.com/docs/workbox

### Чат
- FastAPI WebSockets: fastapi.tiangolo.com/advanced/websockets/
- notarious2/fastapi-chat: github.com/notarious2/fastapi-chat
- FastAPI 45K concurrent WebSocket benchmark: medium.com/@ar.aldhafeeri11
- PostgreSQL chat schema: tome01.com/efficient-schema-design-for-a-chat-app
- pywebpush (Web Push): github.com/web-push-libs/pywebpush

### Quasar
- QChatMessage: quasar.dev/vue-components/chat/
- QTable grid mode: quasar.dev/vue-components/table/
- Screen Plugin: quasar.dev/options/screen-plugin/
- QLayout: quasar.dev/layout/layout/
- QInfiniteScroll: quasar.dev/vue-components/infinite-scroll/
