<template>
  <q-layout view="hHh lpR fFf">
    <!-- Header: лого + текст + кнопки (инструкция, настройки, выход) -->
    <q-header class="bg-white text-dark" style="border-bottom: 1px solid #E0E0E0">
      <q-toolbar style="min-height: 44px; padding: 0 4px">
        <q-btn flat dense round icon="menu" @click="toggleDrawer" class="lt-md" size="sm" />
        <img src="/logo.png" alt="" style="height: 22px; width: auto" class="q-mr-xs" />
        <!-- На мобильном: CRM FESTIVAL COLOR, на планшете: полный текст -->
        <div class="text-weight-bold ellipsis gt-xs" style="font-size: 11px; color: #333">
          Система управления заказами FESTIVAL COLOR
        </div>
        <div class="text-weight-bold ellipsis lt-sm" style="font-size: 11px; color: #333">
          CRM FESTIVAL COLOR
        </div>
        <q-space />
        <!-- Глобальный поиск -->
        <q-btn flat dense round icon="search" size="sm" color="grey-7" @click="showGlobalSearch = true">
          <q-tooltip>Поиск</q-tooltip>
        </q-btn>
        <!-- Offline-очередь: badge с количеством ожидающих операций -->
        <q-btn v-if="offlinePending > 0" flat dense round icon="cloud_upload" size="sm" color="orange-7" @click="refreshData">
          <q-badge color="orange" floating style="font-size: 9px">{{ offlinePending }}</q-badge>
          <q-tooltip>{{ offlinePending }} операций ожидают отправки</q-tooltip>
        </q-btn>
        <!-- Обновить сервер (первая) -->
        <q-btn flat dense round icon="refresh" size="sm" color="grey-7" @click="refreshData">
          <q-tooltip>Обновить</q-tooltip>
        </q-btn>
        <!-- Инструкция (иконка как в десктопе — файл) -->
        <q-btn flat dense round icon="menu_book" size="sm" color="grey-7" @click="openManual">
          <q-tooltip>Инструкция</q-tooltip>
        </q-btn>
        <!-- Настройки уведомлений (шестерёнка) -->
        <q-btn flat dense round icon="settings" size="sm" color="grey-7" @click="openNotifSettings">
          <q-tooltip>Настройки уведомлений</q-tooltip>
        </q-btn>
        <!-- Уведомления -->
        <q-btn flat dense round icon="notifications" size="sm" color="grey-7" @click="$router.push('/notifications')">
          <q-badge v-if="unreadCount > 0" color="negative" floating style="font-size: 9px">
            {{ unreadCount > 99 ? '99+' : unreadCount }}
          </q-badge>
        </q-btn>
        <!-- Выход -->
        <q-btn flat dense round icon="logout" size="sm" style="color: #ccc" @click="handleLogout">
          <q-tooltip>Выйти</q-tooltip>
        </q-btn>
      </q-toolbar>
    </q-header>

    <!-- Drawer — порядок как в десктопе -->
    <q-drawer v-model="drawerOpen" :width="260" :breakpoint="1024" bordered class="bg-white">
      <div class="q-pa-md">
        <div class="row items-center q-gutter-sm">
          <q-avatar color="grey-3" text-color="grey-8" size="42px">{{ authStore.initials }}</q-avatar>
          <div>
            <div class="text-subtitle2 text-weight-bold" style="color: #333">{{ authStore.fullName }}</div>
            <div class="text-caption" style="color: #888">{{ authStore.userPosition }}</div>
          </div>
        </div>
      </div>
      <q-separator />
      <q-list padding>
        <q-item v-for="item in filteredMenuItems" :key="item.to" :to="item.to" clickable v-ripple
          active-class="drawer-active">
          <q-item-section avatar><q-icon :name="item.icon" /></q-item-section>
          <q-item-section style="font-size: 13px">{{ item.label }}</q-item-section>
        </q-item>
      </q-list>
      <q-separator />
      <!-- Онлайн счётчик (как в десктопе — внизу бокового меню) -->
      <q-item v-if="onlineCount > 0" clickable v-ripple @click="showOnlinePopup = true" style="color: #555">
        <q-item-section avatar>
          <q-icon name="circle" color="green" size="12px" />
        </q-item-section>
        <q-item-section style="font-size: 13px">{{ onlineCount }} онлайн</q-item-section>
        <q-item-section side>
          <q-icon name="info_outline" color="grey-5" size="16px" />
        </q-item-section>
      </q-item>
      <q-separator />
      <q-list padding>
        <q-item clickable v-ripple @click="handleLogout">
          <q-item-section avatar><q-icon name="logout" color="negative" /></q-item-section>
          <q-item-section class="text-negative" style="font-size: 13px">Выйти</q-item-section>
        </q-item>
      </q-list>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>

    <!-- Bottom bar — все кнопки без подписей, порядок как в десктопе -->
    <q-footer v-if="$q.screen.lt.md" class="bg-white" style="border-top: 1px solid #E0E0E0">
      <div class="row justify-around items-center" style="height: 48px">
        <q-btn
          v-for="tab in filteredBottomTabs"
          :key="tab.to"
          flat
          dense
          round
          :icon="tab.icon"
          :color="$route.path === tab.to ? 'dark' : 'grey-5'"
          size="sm"
          @click="$router.push(tab.to)"
        >
          <q-tooltip>{{ tab.label }}</q-tooltip>
        </q-btn>
      </div>
    </q-footer>

    <!-- Popup онлайн пользователей -->
    <q-dialog v-model="showOnlinePopup" position="bottom">
      <q-card style="width: 100%; max-width: 360px; border-radius: 10px 10px 0 0">
        <q-card-section class="q-pb-xs">
          <div class="text-subtitle2 text-weight-bold" style="color: #333">Пользователи онлайн: {{ onlineCount }}</div>
        </q-card-section>
        <q-list v-if="canSeeOnlineNames" dense separator style="max-height: 300px; overflow-y: auto">
          <q-item v-for="u in onlineUsers" :key="u.id">
            <q-item-section avatar><q-avatar size="28px" color="green-2" text-color="green-8">{{ u.full_name?.[0] || '?' }}</q-avatar></q-item-section>
            <q-item-section>
              <q-item-label style="font-size: 13px">{{ u.full_name }}</q-item-label>
              <q-item-label caption>{{ u.position }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
        <q-card-section v-else class="text-center" style="color: #999; font-size: 12px">
          Список доступен только руководящему составу
        </q-card-section>
        <q-card-actions align="center">
          <q-btn flat label="Закрыть" no-caps v-close-popup style="color: #888" />
        </q-card-actions>
      </q-card>
    </q-dialog>
    <!-- Диалог настроек уведомлений -->
    <q-dialog v-model="showNotifDialog">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #ffd93c; color: #333">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">Настройки уведомлений</q-toolbar-title>
          <q-btn flat round dense icon="close" @click="showNotifDialog = false" />
        </q-toolbar>
        <q-card-section v-if="notifSettings" style="max-height: 70vh; overflow-y: auto">
          <q-list dense>
            <!-- Канал уведомлений -->
            <q-item-label header style="font-size: 12px; color: #666; padding-bottom: 2px">Канал уведомлений</q-item-label>
            <q-item tag="label" clickable @click="setNotifChannel('telegram')">
              <q-item-section avatar><q-radio v-model="notifSettings.notification_channel" val="telegram" color="accent" /></q-item-section>
              <q-item-section>
                <q-item-label>Telegram</q-item-label>
                <q-item-label caption>Через Telegram бот</q-item-label>
              </q-item-section>
            </q-item>
            <q-item tag="label" clickable @click="setNotifChannel('push')">
              <q-item-section avatar><q-radio v-model="notifSettings.notification_channel" val="push" color="accent" /></q-item-section>
              <q-item-section>
                <q-item-label>Push-уведомления</q-item-label>
                <q-item-label caption>Через браузер (PWA)</q-item-label>
              </q-item-section>
            </q-item>
            <q-item tag="label" clickable @click="setNotifChannel('both')">
              <q-item-section avatar><q-radio v-model="notifSettings.notification_channel" val="both" color="accent" /></q-item-section>
              <q-item-section>
                <q-item-label>Оба канала</q-item-label>
                <q-item-label caption>Telegram + Push одновременно</q-item-label>
              </q-item-section>
            </q-item>
            <q-banner v-if="pushPermissionDenied" dense class="bg-orange-1 q-my-xs" rounded>
              <template v-slot:avatar><q-icon name="warning" color="orange" /></template>
              Push-уведомления заблокированы в настройках браузера
            </q-banner>
            <q-separator class="q-my-xs" />
            <q-item tag="label"><q-item-section>Telegram</q-item-section><q-item-section side><q-toggle v-model="notifSettings.telegram_enabled" color="accent" /></q-item-section></q-item>
            <q-item tag="label"><q-item-section>Email</q-item-section><q-item-section side><q-toggle v-model="notifSettings.email_enabled" color="accent" /></q-item-section></q-item>
            <q-separator class="q-my-xs" />
            <q-item tag="label"><q-item-section>Смена стадии CRM</q-item-section><q-item-section side><q-toggle v-model="notifSettings.notify_crm_stage" color="accent" /></q-item-section></q-item>
            <q-item tag="label"><q-item-section>Назначение задач</q-item-section><q-item-section side><q-toggle v-model="notifSettings.notify_assigned" color="accent" /></q-item-section></q-item>
            <q-item tag="label"><q-item-section>Дедлайны</q-item-section><q-item-section side><q-toggle v-model="notifSettings.notify_deadline" color="accent" /></q-item-section></q-item>
            <q-item tag="label"><q-item-section>Оплаты</q-item-section><q-item-section side><q-toggle v-model="notifSettings.notify_payment" color="accent" /></q-item-section></q-item>
            <q-item tag="label"><q-item-section>Авт. надзор</q-item-section><q-item-section side><q-toggle v-model="notifSettings.notify_supervision" color="accent" /></q-item-section></q-item>
            <q-separator class="q-my-xs" />
            <q-item tag="label"><q-item-section>Индивидуальные</q-item-section><q-item-section side><q-toggle v-model="notifSettings.notify_individual" color="accent" /></q-item-section></q-item>
            <q-item tag="label"><q-item-section>Шаблонные</q-item-section><q-item-section side><q-toggle v-model="notifSettings.notify_template" color="accent" /></q-item-section></q-item>
            <q-separator class="q-my-xs" />
            <q-item tag="label"><q-item-section>Дублирование (подчинённые)</q-item-section><q-item-section side><q-toggle v-model="notifSettings.notify_duplicates" color="accent" /></q-item-section></q-item>
            <q-item tag="label"><q-item-section>Исправления подчинённых</q-item-section><q-item-section side><q-toggle v-model="notifSettings.notify_subordinate_revisions" color="accent" /></q-item-section></q-item>
          </q-list>
        </q-card-section>
        <q-card-actions align="center">
          <q-btn label="Сохранить" no-caps unelevated style="background: #ffd93c; color: #333; border-radius: 8px; width: 200px" @click="saveNotifSettings" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Глобальный поиск -->
    <q-dialog v-model="showGlobalSearch" position="top" seamless>
      <q-card style="width: 100%; max-width: 500px; border-radius: 0 0 10px 10px">
        <q-card-section class="q-pb-none">
          <q-input v-model="globalQuery" placeholder="Клиент, договор, адрес..." dense outlined autofocus @keyup.enter="doGlobalSearch" class="q-mb-sm">
            <template v-slot:prepend><q-icon name="search" /></template>
            <template v-slot:append><q-btn v-if="globalQuery" flat round dense icon="close" size="xs" @click="globalQuery = ''" /></template>
          </q-input>
        </q-card-section>
        <q-list v-if="globalResults.length > 0" separator style="max-height: 400px; overflow-y: auto">
          <q-item v-for="r in globalResults" :key="`${r.type}-${r.id}`" clickable v-ripple @click="goToResult(r)">
            <q-item-section avatar><q-icon :name="r.type === 'client' ? 'person' : r.type === 'contract' ? 'description' : 'view_kanban'" :color="r.type === 'client' ? 'green' : r.type === 'contract' ? 'blue' : 'orange'" /></q-item-section>
            <q-item-section>
              <q-item-label>{{ r.title }}</q-item-label>
              <q-item-label caption>{{ r.subtitle }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
        <q-card-section v-else-if="globalSearched && globalQuery" class="text-center" style="color: #999; font-size: 12px">
          Ничего не найдено
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-layout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from 'src/stores/auth'
import { useNotificationsStore } from 'src/stores/notifications'
import { useReferencesStore } from 'src/stores/references'
import { usePermissionsStore } from 'src/stores/permissions'
import { useWebSocket } from 'src/composables/useWebSocket'
import { pendingCount as getOfflinePendingCount } from 'src/services/offlineQueue'

const $q = useQuasar()
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const notificationsStore = useNotificationsStore()
const referencesStore = useReferencesStore()
const permsStore = usePermissionsStore()
const { connect: wsConnect, disconnect: wsDisconnect, isConnected: wsConnected } = useWebSocket()

const drawerOpen = ref(!$q.screen.lt.md)
const unreadCount = computed(() => notificationsStore.unreadCount)

// Offline-очередь: количество ожидающих операций
const offlinePending = ref(0)
let offlinePendingTimer = null

async function refreshOfflinePending() {
  try { offlinePending.value = await getOfflinePendingCount() } catch { offlinePending.value = 0 }
}

// Глобальный поиск
const showGlobalSearch = ref(false)
const globalQuery = ref('')
const globalResults = ref([])
const globalSearched = ref(false)

async function doGlobalSearch() {
  if (!globalQuery.value || globalQuery.value.length < 2) return
  try {
    const { api: ax } = await import('src/boot/axios')
    const { data } = await ax.get('/api/v1/search/global', { params: { q: globalQuery.value } })
    globalResults.value = (data.results || data || []).map(r => ({
      type: r.type || 'client',
      id: r.id,
      title: r.title || r.name || r.full_name || r.contract_number || '',
      subtitle: r.subtitle || r.address || r.phone || ''
    }))
    globalSearched.value = true
  } catch {
    globalResults.value = []
    globalSearched.value = true
  }
}

function goToResult(r) {
  showGlobalSearch.value = false
  globalQuery.value = ''
  globalResults.value = []
  globalSearched.value = false
  if (r.type === 'client') router.push(`/clients/${r.id}`)
  else if (r.type === 'contract') router.push(`/contracts/${r.id}`)
  else if (r.type === 'crm_card') router.push(`/crm/${r.id}`)
}

onMounted(() => {
  notificationsStore.load()
  referencesStore.loadAll()
  permsStore.load()
  setInterval(() => notificationsStore.load(), 60000)

  // WebSocket для real-time обновлений (дополняет polling, не заменяет)
  _connectWebSocket()
})

// Фильтр меню по правам
const filteredMenuItems = computed(() => {
  if (permsStore.isSuperuser) return menuItems
  const visible = permsStore.visiblePages
  if (visible === 'all') return menuItems
  return menuItems.filter(item => visible.includes(item.to))
})

const filteredBottomTabs = computed(() => {
  if (permsStore.isSuperuser) return bottomTabs
  const visible = permsStore.visiblePages
  if (visible === 'all') return bottomTabs
  return bottomTabs.filter(item => visible.includes(item.to))
})

// Порядок как в десктопе: Дашборд, Клиенты, Договора, СРМ, СРМ надзора, Отчёты, Сотрудники, Зарплаты, Отчёты по сотр.
const menuItems = [
  { to: '/', icon: 'dashboard', label: 'Дашборд' },
  { to: '/clients', icon: 'people', label: 'Клиенты' },
  { to: '/contracts', icon: 'description', label: 'Договора' },
  { to: '/crm', icon: 'view_kanban', label: 'СРМ' },
  { to: '/supervision', icon: 'engineering', label: 'СРМ надзора' },
  { to: '/reports', icon: 'bar_chart', label: 'Отчёты и Статистика' },
  { to: '/employees', icon: 'badge', label: 'Сотрудники' },
  { to: '/salaries', icon: 'payments', label: 'Зарплаты' },
  { to: '/employee-reports', icon: 'assessment', label: 'Отчёты по сотрудникам' },
  { to: '/files', icon: 'folder', label: 'Файлы' },
  { to: '/admin', icon: 'admin_panel_settings', label: 'Администрирование' }
]

// Bottom bar — все кнопки без подписей, порядок как десктоп
const bottomTabs = [
  { to: '/', icon: 'dashboard', label: 'Дашборд' },
  { to: '/clients', icon: 'people', label: 'Клиенты' },
  { to: '/contracts', icon: 'description', label: 'Договора' },
  { to: '/crm', icon: 'view_kanban', label: 'СРМ' },
  { to: '/supervision', icon: 'engineering', label: 'Надзор' },
  { to: '/reports', icon: 'bar_chart', label: 'Отчёты' },
  { to: '/employees', icon: 'badge', label: 'Сотрудники' },
  { to: '/salaries', icon: 'payments', label: 'Зарплаты' },
  { to: '/employee-reports', icon: 'assessment', label: 'Отчёты сотр.' },
  { to: '/notifications', icon: 'notifications', label: 'Уведомления' },
  { to: '/admin', icon: 'admin_panel_settings', label: 'Админ' }
]

function toggleDrawer() { drawerOpen.value = !drawerOpen.value }

function refreshData() {
  window.location.reload()
}

function openManual() {
  // Публичные ссылки на инструкции по должности (yadi.sk)
  const MANUAL_URLS = {
    'Руководитель студии': 'https://yadi.sk/i/ri0ccGzd1hixUg',
    'Старший менеджер проектов': 'https://yadi.sk/i/jc_MLORFQJYw8g',
    'Менеджер': 'https://yadi.sk/i/_b3QKB0cxD1RIQ',
    'СДП': 'https://yadi.sk/i/VWlLjErSrnk_Kw',
    'ГАП': 'https://yadi.sk/i/lAhXe7-DNrtcuw',
    'Дизайнер': 'https://yadi.sk/i/FuD7OjI9qGpThg',
    'Чертёжник': 'https://yadi.sk/i/ByeUw6h0erkLuQ',
    'Замерщик': 'https://yadi.sk/i/H4MJFHmKIu0zdQ',
    'ДАН': 'https://yadi.sk/i/LAkkj1h3f5Bv7g'
  }
  const position = authStore.user?.position || ''
  const url = MANUAL_URLS[position] || MANUAL_URLS[position.split('/')[0]?.trim()]
  if (url) {
    window.open(url, '_blank')
  } else {
    import('quasar').then(({ Notify }) => {
      Notify.create({ type: 'info', message: `Инструкция для «${position}» пока не доступна` })
    })
  }
}

const showNotifDialog = ref(false)
const notifSettings = ref(null)
const pushPermissionDenied = ref(false)

async function openNotifSettings() {
  const empId = authStore.user?.id
  if (!empId) return
  try {
    const { api } = await import('src/boot/axios')
    const { data } = await api.get(`/api/v1/notifications/settings/${empId}`)
    // Дефолт для старых записей без notification_channel
    if (!data.notification_channel) data.notification_channel = 'telegram'
    notifSettings.value = data
    // Проверяем статус разрешения push
    if ('Notification' in window) {
      pushPermissionDenied.value = Notification.permission === 'denied'
    }
    showNotifDialog.value = true
  } catch {
    import('quasar').then(({ Notify }) => Notify.create({ type: 'negative', message: 'Не удалось загрузить настройки' }))
  }
}

/**
 * Переключение канала уведомлений.
 * При выборе push/both — запрашиваем разрешение браузера и подписываемся.
 */
async function setNotifChannel(channel) {
  if (!notifSettings.value) return
  notifSettings.value.notification_channel = channel

  // Если выбран push или both — нужно запросить разрешение и подписаться
  if (channel === 'push' || channel === 'both') {
    if (!('Notification' in window) || !('serviceWorker' in navigator)) {
      import('quasar').then(({ Notify }) => Notify.create({
        type: 'warning',
        message: 'Push-уведомления не поддерживаются в этом браузере'
      }))
      notifSettings.value.notification_channel = 'telegram'
      return
    }

    const permission = await Notification.requestPermission()
    if (permission !== 'granted') {
      pushPermissionDenied.value = true
      import('quasar').then(({ Notify }) => Notify.create({
        type: 'warning',
        message: 'Push-уведомления заблокированы. Разрешите в настройках браузера.'
      }))
      notifSettings.value.notification_channel = 'telegram'
      return
    }
    pushPermissionDenied.value = false

    // Подписка через Service Worker + отправка на сервер
    try {
      await subscribeToPush()
      notifSettings.value.push_enabled = true
    } catch (err) {
      console.error('Ошибка подписки на push:', err)
      import('quasar').then(({ Notify }) => Notify.create({
        type: 'negative',
        message: 'Не удалось подписаться на push-уведомления'
      }))
      notifSettings.value.notification_channel = 'telegram'
    }
  }
}

/**
 * Подписаться на Web Push через Service Worker pushManager.
 * Отправляет подписку на сервер.
 */
async function subscribeToPush() {
  const { api } = await import('src/boot/axios')

  // Получить VAPID public key с сервера
  const { data: vapidData } = await api.get('/api/v1/notifications/push/vapid-public-key')
  const vapidPublicKey = vapidData.public_key

  // Конвертация base64 URL-safe в Uint8Array
  const urlBase64ToUint8Array = (base64String) => {
    const padding = '='.repeat((4 - base64String.length % 4) % 4)
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
    const rawData = window.atob(base64)
    const outputArray = new Uint8Array(rawData.length)
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i)
    }
    return outputArray
  }

  const registration = await navigator.serviceWorker.ready
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
  })

  // Отправить подписку на сервер
  await api.post('/api/v1/notifications/push/subscribe', subscription.toJSON())
}

async function saveNotifSettings() {
  const empId = authStore.user?.id
  if (!empId || !notifSettings.value) return
  try {
    const { api } = await import('src/boot/axios')

    // Если push отключён — отписаться на сервере
    if (notifSettings.value.notification_channel === 'telegram' && notifSettings.value.push_enabled) {
      try {
        await api.post('/api/v1/notifications/push/unsubscribe')
        notifSettings.value.push_enabled = false
      } catch { /* игнорируем ошибку отписки */ }
    }

    await api.put(`/api/v1/notifications/settings/${empId}`, notifSettings.value)
    import('quasar').then(({ Notify }) => Notify.create({ type: 'positive', message: 'Настройки сохранены' }))
    showNotifDialog.value = false
  } catch (err) {
    import('quasar').then(({ Notify }) => Notify.create({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }))
  }
}

async function handleLogout() { await authStore.logout() }

// === Онлайн счётчик (heartbeat как десктоп) ===
const onlineUsers = ref([])
const onlineCount = computed(() => onlineUsers.value.length)
const showOnlinePopup = ref(false)
const hiddenRoles = new Set(['Дизайнер', 'Чертёжник', 'Замерщик', 'ДАН'])
const canSeeOnlineNames = computed(() => !hiddenRoles.has(authStore.user?.position || ''))

let heartbeatTimer = null

async function sendHeartbeat() {
  try {
    const { api: ax } = await import('src/boot/axios')
    const { data } = await ax.post('/api/v1/heartbeat', { employee_id: authStore.user?.id || null }, { timeout: 10000 })
    onlineUsers.value = data.online_users || []
  } catch {}
}

// === Auto-refresh при возврате в приложение (visibilitychange) ===
let lastRefreshTime = 0
const MIN_REFRESH_INTERVAL = 30000 // 30 секунд — минимальный интервал между обновлениями

// Маппинг путей к функциям обновления (lazy — загружаем store/api по необходимости)
async function refreshCurrentPageData() {
  const now = Date.now()
  if (now - lastRefreshTime < MIN_REFRESH_INTERVAL) return
  lastRefreshTime = now

  const path = route.path

  // Уведомления обновляем всегда
  notificationsStore.load()

  try {
    if (path === '/' || path === '/dashboard') {
      // Дашборд — перезагружаем stores (страница сама подтянет)
      referencesStore.loadAll()
    } else if (path === '/crm' || path.startsWith('/crm/')) {
      // CRM — страница сама обновится через onActivated/onMounted
      // Но можно отправить событие для принудительного обновления
      window.dispatchEvent(new CustomEvent('app:refresh'))
    } else if (path === '/clients' || path.startsWith('/clients/')) {
      window.dispatchEvent(new CustomEvent('app:refresh'))
    } else if (path === '/contracts' || path.startsWith('/contracts/')) {
      window.dispatchEvent(new CustomEvent('app:refresh'))
    } else if (path === '/supervision' || path.startsWith('/supervision/')) {
      window.dispatchEvent(new CustomEvent('app:refresh'))
    } else if (path === '/salaries') {
      window.dispatchEvent(new CustomEvent('app:refresh'))
    } else if (path === '/employees' || path.startsWith('/employees/')) {
      window.dispatchEvent(new CustomEvent('app:refresh'))
    } else if (path === '/notifications') {
      window.dispatchEvent(new CustomEvent('app:refresh'))
    } else {
      // Остальные страницы — общий refresh event
      window.dispatchEvent(new CustomEvent('app:refresh'))
    }
  } catch {
    // Ошибка обновления — игнорируем, не ломаем UX
  }
}

function handleVisibilityChange() {
  if (document.visibilityState === 'visible') {
    refreshCurrentPageData()
  }
}

onMounted(() => {
  sendHeartbeat()
  heartbeatTimer = setInterval(sendHeartbeat, 60000)

  // Offline-очередь: проверяем количество ожидающих операций
  refreshOfflinePending()
  offlinePendingTimer = setInterval(refreshOfflinePending, 15000)

  // Слушаем возврат в приложение
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

// === WebSocket подключение ===
function _connectWebSocket() {
  const token = authStore.accessToken
  if (!token) return

  wsConnect(token, {
    // CRM карточка перемещена — обновляем CRM store
    onCardMoved(data) {
      window.dispatchEvent(new CustomEvent('app:refresh'))
    },
    // CRM карточка обновлена — обновляем CRM store
    onCardUpdated(data) {
      window.dispatchEvent(new CustomEvent('app:refresh'))
    },
    // Новое уведомление — обновляем store + показываем toast
    onNotificationNew(data) {
      notificationsStore.load()
      import('quasar').then(({ Notify }) => {
        Notify.create({
          type: 'info',
          message: data.title || 'Новое уведомление',
          caption: data.message || '',
          timeout: 5000,
          position: 'top',
          actions: [{ icon: 'close', color: 'white', round: true }],
        })
      })
    },
    // Пользователь online/offline — обновляем список
    onUserOnline() {
      sendHeartbeat()
    },
  })
}

onUnmounted(() => {
  if (heartbeatTimer) clearInterval(heartbeatTimer)
  if (offlinePendingTimer) clearInterval(offlinePendingTimer)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  wsDisconnect()
})
</script>

<style scoped>
.drawer-active {
  color: #333;
  font-weight: bold;
  background: #F5F5F5;
  border-left: 3px solid #ffd93c;
}
</style>
