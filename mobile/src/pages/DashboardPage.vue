<template>
  <q-page padding>
    <q-pull-to-refresh @refresh="onRefresh">
      <!-- Баннер установки PWA -->
      <install-banner />

      <!-- Приветствие -->
      <div class="q-mb-md">
        <div class="text-h6 text-weight-bold">
          {{ greeting }}, {{ firstName }}
        </div>
        <div class="text-caption text-grey-7">{{ todayDate }}</div>
      </div>

      <!-- Карточки статистики -->
      <div class="row q-col-gutter-sm q-mb-md">
        <div class="col-6" v-for="stat in statsCards" :key="stat.label">
          <q-card class="is-card" :class="{ 'cursor-pointer': stat.to }" @click="stat.to && $router.push(stat.to)">
            <q-card-section class="q-pa-md">
              <div class="row items-center justify-between">
                <q-icon :name="stat.icon" :color="stat.color" size="24px" />
                <div class="text-h5 text-weight-bold">
                  <q-skeleton v-if="dashboard.loading" type="text" width="40px" />
                  <span v-else>{{ stat.value }}</span>
                </div>
              </div>
              <div class="text-caption text-grey-7 q-mt-xs">{{ stat.label }}</div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Быстрые действия -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pa-sm">
          <div class="row q-col-gutter-sm">
            <div class="col-4" v-for="action in quickActions" :key="action.label">
              <q-btn
                :icon="action.icon"
                :label="action.label"
                :to="action.to"
                stack
                flat
                no-caps
                class="full-width"
                color="primary"
                size="sm"
              />
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Последние уведомления -->
      <q-card class="is-card">
        <q-card-section class="q-pb-none">
          <div class="row items-center justify-between">
            <div class="text-subtitle2 text-weight-bold">Уведомления</div>
            <q-badge v-if="notificationsStore.unreadCount > 0" color="negative" :label="notificationsStore.unreadCount" />
          </div>
        </q-card-section>

        <q-list v-if="recentNotifications.length > 0" separator>
          <q-item
            v-for="n in recentNotifications"
            :key="n.id"
            clickable
            v-ripple
            :class="{ 'bg-blue-1': !n.is_read }"
            @click="handleNotificationClick(n)"
          >
            <q-item-section avatar>
              <q-icon :name="notificationIcon(n.notification_type)" :color="n.is_read ? 'grey-5' : 'primary'" />
            </q-item-section>
            <q-item-section>
              <q-item-label :class="{ 'text-weight-bold': !n.is_read }">{{ n.title }}</q-item-label>
              <q-item-label caption lines="1">{{ n.message }}</q-item-label>
              <q-item-label caption class="text-grey-5">{{ formatTime(n.created_at) }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <q-card-section v-else class="text-center text-grey-5 q-py-lg">
          <q-icon name="notifications_none" size="32px" class="q-mb-xs" />
          <div class="text-caption">Нет уведомлений</div>
        </q-card-section>
      </q-card>
    </q-pull-to-refresh>
  </q-page>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from 'src/stores/auth'
import InstallBanner from 'src/components/InstallBanner.vue'
import { useDashboardStore } from 'src/stores/dashboard'
import { useNotificationsStore } from 'src/stores/notifications'

const router = useRouter()
const authStore = useAuthStore()
const dashboard = useDashboardStore()
const notificationsStore = useNotificationsStore()

const firstName = computed(() =>
  authStore.user?.full_name?.split(' ')[0] || ''
)

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return 'Доброй ночи'
  if (hour < 12) return 'Доброе утро'
  if (hour < 18) return 'Добрый день'
  return 'Добрый вечер'
})

const todayDate = computed(() =>
  new Date().toLocaleDateString('ru-RU', {
    weekday: 'long', day: 'numeric', month: 'long'
  })
)

const statsCards = computed(() => [
  {
    label: 'Активных проектов',
    value: dashboard.crmStats?.active_orders ?? '—',
    icon: 'folder_open',
    color: 'primary',
    to: '/crm'
  },
  {
    label: 'Всего клиентов',
    value: dashboard.clientsStats?.total_clients ?? '—',
    icon: 'people',
    color: 'positive',
    to: '/clients'
  },
  {
    label: 'Надзорных объектов',
    value: dashboard.crmStats?.agent_active_orders ?? '—',
    icon: 'engineering',
    color: 'warning',
    to: '/supervision'
  },
  {
    label: 'Сотрудников',
    value: dashboard.employeesStats?.active_employees ?? '—',
    icon: 'badge',
    color: 'info'
  }
])

const quickActions = [
  { label: 'CRM', icon: 'view_kanban', to: '/crm' },
  { label: 'Клиенты', icon: 'people', to: '/clients' },
  { label: 'Надзор', icon: 'engineering', to: '/supervision' }
]

const recentNotifications = computed(() =>
  notificationsStore.items.slice(0, 5)
)

function notificationIcon(type) {
  const icons = {
    assigned: 'assignment_ind',
    deadline: 'schedule',
    payment: 'payments',
    crm_stage: 'swap_horiz',
    supervision: 'engineering'
  }
  return icons[type] || 'notifications'
}

function formatTime(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  const now = new Date()
  const diff = now - date
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return 'только что'
  if (minutes < 60) return `${minutes} мин. назад`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} ч. назад`
  return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
}

function handleNotificationClick(n) {
  if (!n.is_read) {
    notificationsStore.markRead(n.id)
  }
  // Навигация к связанной сущности
  if (n.related_entity_type === 'crm_card' && n.related_entity_id) {
    router.push(`/crm/${n.related_entity_id}`)
  }
}

onMounted(() => {
  dashboard.loadAll()
})

function onRefresh(done) {
  Promise.all([
    dashboard.loadAll(),
    notificationsStore.load()
  ]).finally(done)
}
</script>
