<template>
  <q-page padding>
    <q-pull-to-refresh @refresh="onRefresh">
      <install-banner />

      <!-- Приветствие -->
      <div class="q-mb-md">
        <div class="text-h6 text-weight-bold">{{ greeting }}, {{ firstName }}</div>
        <div class="text-caption text-grey-7">{{ todayDate }}</div>
      </div>

      <!-- 6 KPI карточек как в десктопе (2×3) -->
      <div class="row q-col-gutter-sm q-mb-md">
        <div class="col-4" v-for="kpi in kpiCards" :key="kpi.label">
          <q-card class="is-card" style="min-height: 90px" :style="{ borderLeft: `3px solid ${kpi.border}` }">
            <q-card-section class="q-pa-sm text-center">
              <q-icon :name="kpi.icon" size="20px" :style="{ color: kpi.border }" class="q-mb-xs" />
              <div class="text-h6 text-weight-bold">
                <q-skeleton v-if="dashboard.loading" type="text" width="30px" style="margin: 0 auto" />
                <span v-else>{{ kpi.value }}</span>
              </div>
              <div class="text-caption text-grey-7" style="font-size: 10px; line-height: 1.2">{{ kpi.label }}</div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Уведомления -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="row items-center justify-between">
            <div class="text-subtitle2 text-weight-bold">Уведомления</div>
            <q-badge v-if="notificationsStore.unreadCount > 0" color="negative" :label="notificationsStore.unreadCount" />
          </div>
        </q-card-section>
        <q-list v-if="recentNotifications.length > 0" separator>
          <q-item v-for="n in recentNotifications" :key="n.id" clickable v-ripple :class="{ 'bg-blue-1': !n.is_read }" @click="handleNotificationClick(n)">
            <q-item-section avatar><q-icon :name="notificationIcon(n.notification_type)" :color="n.is_read ? 'grey-5' : 'accent'" size="20px" /></q-item-section>
            <q-item-section>
              <q-item-label :class="{ 'text-weight-bold': !n.is_read }" style="font-size: 13px">{{ n.title }}</q-item-label>
              <q-item-label caption lines="1">{{ n.message }}</q-item-label>
              <q-item-label caption class="text-grey-5">{{ formatTime(n.created_at) }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
        <q-card-section v-else class="text-center text-grey-5 q-py-md">
          <q-icon name="notifications_none" size="28px" class="q-mb-xs" />
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
import { useDashboardStore } from 'src/stores/dashboard'
import { useNotificationsStore } from 'src/stores/notifications'
import InstallBanner from 'src/components/InstallBanner.vue'

const router = useRouter()
const authStore = useAuthStore()
const dashboard = useDashboardStore()
const notificationsStore = useNotificationsStore()

const firstName = computed(() => authStore.user?.full_name?.split(' ')[0] || '')
const greeting = computed(() => { const h = new Date().getHours(); return h < 6 ? 'Доброй ночи' : h < 12 ? 'Доброе утро' : h < 18 ? 'Добрый день' : 'Добрый вечер' })
const todayDate = computed(() => new Date().toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' }))

// 6 KPI как в десктопе
const kpiCards = computed(() => {
  const crm = dashboard.crmStats || {}
  const cli = dashboard.clientsStats || {}
  const emp = dashboard.employeesStats || {}
  return [
    { label: 'Индивидуальные', value: crm.active_orders ?? '—', icon: 'assignment', border: '#ffd93c' },
    { label: 'Шаблонные', value: crm.agent_active_orders ?? '—', icon: 'content_copy', border: '#F39C12' },
    { label: 'Авт. надзор', value: crm.archive_orders ?? '—', icon: 'engineering', border: '#27AE60' },
    { label: 'Клиентов', value: cli.total_clients ?? '—', icon: 'people', border: '#9B59B6' },
    { label: 'Договоров', value: cli.clients_by_year ?? '—', icon: 'description', border: '#E74C3C' },
    { label: 'Сотрудников', value: emp.active_employees ?? '—', icon: 'badge', border: '#1ABC9C' }
  ]
})

const recentNotifications = computed(() => notificationsStore.items.slice(0, 5))

function notificationIcon(t) { return { assigned: 'assignment_ind', deadline: 'schedule', payment: 'payments', crm_stage: 'swap_horiz', supervision: 'engineering' }[t] || 'notifications' }
function formatTime(s) { if (!s) return ''; const d = new Date(s); const m = Math.floor((Date.now() - d) / 60000); if (m < 1) return 'сейчас'; if (m < 60) return `${m} мин`; const h = Math.floor(m / 60); if (h < 24) return `${h} ч`; return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }) }
function handleNotificationClick(n) { if (!n.is_read) notificationsStore.markRead(n.id); if (n.related_entity_type === 'crm_card') router.push(`/crm/${n.related_entity_id}`) }
function onRefresh(done) { Promise.all([dashboard.loadAll(), notificationsStore.load()]).finally(done) }

onMounted(() => dashboard.loadAll())
</script>
