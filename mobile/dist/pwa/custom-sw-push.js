/*
 * Push-обработчик для Service Worker
 * Подключается через importScripts в GenerateSW
 */

// Обработка входящих push-уведомлений
self.addEventListener('push', function(event) {
  var data = {}
  try {
    data = event.data ? event.data.json() : {}
  } catch(e) {
    data = { title: 'Interior Studio CRM', message: event.data ? event.data.text() : '' }
  }

  var title = data.title || 'Interior Studio CRM'
  var options = {
    body: data.message || '',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/icon-72x72.png',
    vibrate: [100, 50, 100],
    data: { url: data.url || '/' },
    tag: data.tag || 'crm-notification',
    renotify: true
  }

  event.waitUntil(
    self.registration.showNotification(title, options)
  )
})

// Клик по уведомлению — открыть приложение
self.addEventListener('notificationclick', function(event) {
  event.notification.close()
  var targetUrl = event.notification.data && event.notification.data.url ? event.notification.data.url : '/'

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
      for (var i = 0; i < clientList.length; i++) {
        var client = clientList[i]
        if ('focus' in client) {
          client.focus()
          if ('navigate' in client) client.navigate(targetUrl)
          return
        }
      }
      return self.clients.openWindow(targetUrl)
    })
  )
})
