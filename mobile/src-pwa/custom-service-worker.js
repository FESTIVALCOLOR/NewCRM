/*
 * Кастомный Service Worker для Interior Studio CRM PWA.
 * Включает:
 * - Workbox precaching (автоматический inject манифеста)
 * - Web Push обработчик (push + notificationclick)
 * - Runtime caching для API
 */

import { precacheAndRoute, cleanupOutdatedCaches } from 'workbox-precaching'
import { registerRoute } from 'workbox-routing'
import { CacheFirst, NetworkFirst } from 'workbox-strategies'
import { ExpirationPlugin } from 'workbox-expiration'
import { clientsClaim } from 'workbox-core'

// Активировать SW сразу, без ожидания закрытия вкладок
self.skipWaiting()
clientsClaim()

// Precache — Workbox inject-ит манифест при сборке
cleanupOutdatedCaches()
precacheAndRoute(self.__WB_MANIFEST)

// === Кеш изображений и файлов из Yandex Disk (chat) ===
// ВАЖНО: этот route должен быть ПЕРЕД общим /api/v1/ route
// Ключ кеша = только yandex_path (без token), чтобы изображения кешировались
// независимо от смены JWT-токена. TTL = 7 дней, до 300 файлов.
registerRoute(
  ({ url }) => url.pathname === '/api/v1/files/stream',
  new CacheFirst({
    cacheName: 'chat-images-v1',
    plugins: [
      {
        // Кастомный ключ: только yandex_path, без token
        cacheKeyWillBeUsed: async ({ request }) => {
          const url = new URL(request.url)
          const path = url.searchParams.get('yandex_path') || ''
          return `${url.origin}/api/v1/files/stream?yandex_path=${encodeURIComponent(path)}`
        },
      },
      new ExpirationPlugin({
        maxEntries: 300,
        maxAgeSeconds: 7 * 24 * 60 * 60, // 7 дней
      }),
    ],
  }),
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
