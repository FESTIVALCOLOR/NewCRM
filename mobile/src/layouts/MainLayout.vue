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
    <!-- Диалог настроек уведомлений -->
    <q-dialog v-model="showNotifDialog">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #ffd93c; color: #333">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">Настройки уведомлений</q-toolbar-title>
          <q-btn flat round dense icon="close" @click="showNotifDialog = false" />
        </q-toolbar>
        <q-card-section v-if="notifSettings" style="max-height: 70vh; overflow-y: auto">
          <q-list dense>
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
          </q-list>
        </q-card-section>
        <q-card-actions align="center">
          <q-btn label="Сохранить" no-caps unelevated style="background: #ffd93c; color: #333; border-radius: 8px; width: 200px" @click="saveNotifSettings" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-layout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from 'src/stores/auth'
import { useNotificationsStore } from 'src/stores/notifications'
import { useReferencesStore } from 'src/stores/references'
import { usePermissionsStore } from 'src/stores/permissions'

const $q = useQuasar()
const route = useRoute()
const authStore = useAuthStore()
const notificationsStore = useNotificationsStore()
const referencesStore = useReferencesStore()
const permsStore = usePermissionsStore()

const drawerOpen = ref(!$q.screen.lt.md)
const unreadCount = computed(() => notificationsStore.unreadCount)

onMounted(() => {
  notificationsStore.load()
  referencesStore.loadAll()
  permsStore.load()
  setInterval(() => notificationsStore.load(), 60000)
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

async function openNotifSettings() {
  const empId = authStore.user?.id
  if (!empId) return
  try {
    const { api } = await import('src/boot/axios')
    const { data } = await api.get(`/api/v1/notifications/settings/${empId}`)
    notifSettings.value = data
    showNotifDialog.value = true
  } catch {
    import('quasar').then(({ Notify }) => Notify.create({ type: 'negative', message: 'Не удалось загрузить настройки' }))
  }
}

async function saveNotifSettings() {
  const empId = authStore.user?.id
  if (!empId || !notifSettings.value) return
  try {
    const { api } = await import('src/boot/axios')
    await api.put(`/api/v1/notifications/settings/${empId}`, notifSettings.value)
    import('quasar').then(({ Notify }) => Notify.create({ type: 'positive', message: 'Настройки сохранены' }))
    showNotifDialog.value = false
  } catch (err) {
    import('quasar').then(({ Notify }) => Notify.create({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }))
  }
}

async function handleLogout() { await authStore.logout() }
</script>

<style scoped>
.drawer-active {
  color: #333;
  font-weight: bold;
  background: #F5F5F5;
  border-left: 3px solid #ffd93c;
}
</style>
