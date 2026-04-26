/*
 * Кастомный Service Worker для Interior Studio CRM PWA.
 * Включает:
 * - Workbox precaching (автоматический inject манифеста)
 * - Web Push обработчик (push + notificationclick)
 * - Runtime caching для API
 */

import { precacheAndRoute, cleanupOutdatedCaches, createHandlerBoundToURL } from 'workbox-precaching'
import { registerRoute, NavigationRoute } from 'workbox-routing'
import { CacheFirst, NetworkFirst, StaleWhileRevalidate } from 'workbox-strategies'
import { ExpirationPlugin } from 'workbox-expiration'
import { clientsClaim } from 'workbox-core'

// Активировать SW сразу, без ожидания закрытия вкладок
self.skipWaiting()
clientsClaim()

// Precache — Workbox inject-ит манифест при сборке
cleanupOutdatedCaches()
precacheAndRoute(self.__WB_MANIFEST)

// SPA fallback: все навигационные запросы кроме /api → index.html
registerRoute(
  new NavigationRoute(createHandlerBoundToURL('/index.html'), {
    denylist: [/^\/api/],
  }),
)

// Runtime caching для тяжёлых JS-чанков (исключены из precache)
// CacheFirst: загружается один раз, потом всегда из кеша
registerRoute(
  ({ url }) => /\/(pdf|BarChart)-[^/]+\.m?js$/.test(url.pathname),
  new CacheFirst({
    cacheName: 'heavy-chunks-v1',
    plugins: [
      new ExpirationPlugin({ maxEntries: 10, maxAgeSeconds: 30 * 24 * 60 * 60 }),
    ],
  }),
)

// === Кеш изображений и файлов из Yandex Disk (chat) ===
// ВАЖНО: эти routes должны быть ПЕРЕД общим /api/v1/ route
// Ключ кеша = только yandex_path (без token/URL-токена), TTL = 7 дней, до 300 файлов.
const imagesCachePlugin = [
  {
    cacheKeyWillBeUsed: async ({ request }) => {
      const url = new URL(request.url)
      const path = url.searchParams.get('yandex_path') || ''
      return `${url.origin}/stream-cache?yandex_path=${encodeURIComponent(path)}`
    },
  },
  {
    // Кешировать только успешные ответы (status 200) — иначе Cache.put() бросает NetworkError
    cacheWillUpdate: async ({ response }) => {
      if (response && response.status === 200) return response
      return null
    },
  },
  new ExpirationPlugin({
    maxEntries: 300,
    maxAgeSeconds: 7 * 24 * 60 * 60,
  }),
]

// /api/v1/files/stream — для сотрудников
registerRoute(
  ({ url }) => url.pathname === '/api/v1/files/stream',
  new CacheFirst({ cacheName: 'chat-images-v1', plugins: imagesCachePlugin }),
)

// /api/v1/client-chat/{token}/stream — для клиентского чата (без JWT, только yandex_path)
registerRoute(
  ({ url }) => /^\/api\/v1\/client-chat\/[^/]+\/stream$/.test(url.pathname),
  new CacheFirst({ cacheName: 'chat-images-v1', plugins: imagesCachePlugin }),
)

// Runtime caching для остальных API запросов
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/v1/'),
  new NetworkFirst({
    cacheName: 'api-cache',
    plugins: [
      new ExpirationPlugin({
        maxEntries: 100,
        maxAgeSeconds: 300 // 5 минут
      })
    ],
    networkTimeoutSeconds: 5
  })
)

// === Web Push: обработка входящих уведомлений ===
self.addEventListener('push', (event) => {
  let data = {}
  try {
    data = event.data?.json() || {}
  } catch {
    data = { title: 'Interior Studio CRM', message: event.data?.text() || '' }
  }

  const title = data.title || 'Interior Studio CRM'
  const options = {
    body: data.message || '',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/icon-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      url: data.url || '/'
    },
    // Группировка уведомлений — одно на тег
    tag: data.tag || 'crm-notification',
    renotify: true
  }

  event.waitUntil(
    self.registration.showNotification(title, options)
  )
})

// === Web Push: клик по уведомлению — открыть/сфокусировать приложение ===
self.addEventListener('notificationclick', (event) => {
  event.notification.close()

  const targetUrl = event.notification.data?.url || '/'

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // Если приложение уже открыто — сфокусировать и перейти
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.focus()
          client.navigate(targetUrl)
          return
        }
      }
      // Иначе открыть новое окно
      return self.clients.openWindow(targetUrl)
    })
  )
})
