<template>
  <q-layout view="hHh lpR fFf">
    <!-- Шапка -->
    <q-header elevated class="bg-white text-dark">
      <q-toolbar>
        <q-btn
          flat
          dense
          round
          icon="menu"
          aria-label="Меню"
          @click="toggleDrawer"
          class="lt-md"
        />

        <img src="/logo.png" alt="" class="fc-logo q-mr-sm" />
        <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
          {{ pageTitle }}
        </q-toolbar-title>

        <q-btn flat round icon="notifications" @click="$router.push('/notifications')">
          <q-badge v-if="unreadCount > 0" color="negative" floating>
            {{ unreadCount > 99 ? '99+' : unreadCount }}
          </q-badge>
        </q-btn>
      </q-toolbar>
    </q-header>

    <!-- Боковое меню (drawer) — видно на планшетах/десктопе, overlay на телефонах -->
    <q-drawer
      v-model="drawerOpen"
      :width="260"
      :breakpoint="1024"
      bordered
      class="bg-white"
    >
      <!-- Профиль в drawer -->
      <div class="q-pa-md">
        <div class="row items-center q-gutter-sm">
          <q-avatar color="primary" text-color="white" size="42px">
            {{ authStore.initials }}
          </q-avatar>
          <div>
            <div class="text-subtitle2 text-weight-bold">{{ authStore.fullName }}</div>
            <div class="text-caption text-grey-7">{{ authStore.userPosition }}</div>
          </div>
        </div>
      </div>

      <q-separator />

      <!-- Навигация -->
      <q-list padding>
        <q-item
          v-for="item in menuItems"
          :key="item.to"
          :to="item.to"
          clickable
          v-ripple
          :active="$route.path === item.to"
          active-class="text-primary bg-blue-1"
        >
          <q-item-section avatar>
            <q-icon :name="item.icon" />
          </q-item-section>
          <q-item-section>{{ item.label }}</q-item-section>
        </q-item>
      </q-list>

      <q-separator />

      <q-list padding>
        <q-item clickable v-ripple @click="handleLogout">
          <q-item-section avatar>
            <q-icon name="logout" color="negative" />
          </q-item-section>
          <q-item-section class="text-negative">Выйти</q-item-section>
        </q-item>
      </q-list>
    </q-drawer>

    <!-- Контент страниц -->
    <q-page-container>
      <router-view />
    </q-page-container>

    <!-- Нижние вкладки (телефон) -->
    <q-footer elevated class="bg-white gt-sm" style="display: none" />
    <q-footer v-if="$q.screen.lt.md" elevated class="bg-white" bordered>
      <q-tabs
        v-model="currentTab"
        active-color="primary"
        indicator-color="primary"
        class="text-grey-7"
        dense
        narrow-indicator
      >
        <q-route-tab
          v-for="tab in bottomTabs"
          :key="tab.to"
          :to="tab.to"
          :icon="tab.icon"
          :label="tab.label"
          :name="tab.to"
          no-caps
        />
      </q-tabs>
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

const currentTab = computed(() => route.path)

const pageTitle = computed(() => {
  return route.meta.title || 'Interior Studio'
})

// Все вкладки как в десктопе
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
  { to: '/admin', icon: 'admin_panel_settings', label: 'Администрирование' },
  { to: '/notifications', icon: 'notifications', label: 'Уведомления' },
  { to: '/profile', icon: 'person', label: 'Профиль' }
]

// Bottom tabs — 5 основных как в десктопе (телефон)
const bottomTabs = [
  { to: '/', icon: 'dashboard', label: 'Дашборд' },
  { to: '/clients', icon: 'people', label: 'Клиенты' },
  { to: '/contracts', icon: 'description', label: 'Договора' },
  { to: '/crm', icon: 'view_kanban', label: 'СРМ' },
  { to: '/supervision', icon: 'engineering', label: 'Надзор' }
]

function toggleDrawer() {
  drawerOpen.value = !drawerOpen.value
}

async function handleLogout() {
  await authStore.logout()
}
</script>
