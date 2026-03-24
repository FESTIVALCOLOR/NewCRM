<template>
  <q-layout view="hHh lpR fFf">
    <!-- Header: лого + текст + кнопки (инструкция, настройки, выход) -->
    <q-header class="bg-white text-dark" style="border-bottom: 1px solid #E0E0E0">
      <q-toolbar style="min-height: 44px">
        <q-btn flat dense round icon="menu" @click="toggleDrawer" class="lt-md" />
        <img src="/logo.png" alt="" style="height: 24px; width: auto" class="q-mr-xs" />
        <div class="text-weight-bold ellipsis" style="font-size: 12px; color: #333; max-width: 180px">
          Система управления заказами FESTIVAL COLOR
        </div>
        <q-space />
        <!-- Инструкция -->
        <q-btn flat dense round icon="help_outline" size="sm" color="grey-7">
          <q-tooltip>Инструкция</q-tooltip>
        </q-btn>
        <!-- Настройки уведомлений -->
        <q-btn flat dense round icon="settings" size="sm" color="grey-7" @click="$router.push('/admin?tab=notifications')">
          <q-tooltip>Настройки</q-tooltip>
        </q-btn>
        <!-- Уведомления -->
        <q-btn flat dense round icon="notifications" size="sm" color="grey-7" @click="$router.push('/notifications')">
          <q-badge v-if="unreadCount > 0" color="negative" floating style="font-size: 9px">
            {{ unreadCount > 99 ? '99+' : unreadCount }}
          </q-badge>
        </q-btn>
        <!-- Выход -->
        <q-btn flat dense round icon="logout" size="sm" color="grey-7" @click="handleLogout">
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
        <q-item v-for="item in menuItems" :key="item.to" :to="item.to" clickable v-ripple
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
          v-for="tab in bottomTabs"
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
  </q-layout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from 'src/stores/auth'
import { useNotificationsStore } from 'src/stores/notifications'
import { useReferencesStore } from 'src/stores/references'

const $q = useQuasar()
const route = useRoute()
const authStore = useAuthStore()
const notificationsStore = useNotificationsStore()
const referencesStore = useReferencesStore()

const drawerOpen = ref(!$q.screen.lt.md)
const unreadCount = computed(() => notificationsStore.unreadCount)

onMounted(() => {
  notificationsStore.load()
  referencesStore.loadAll()
  setInterval(() => notificationsStore.load(), 60000)
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
