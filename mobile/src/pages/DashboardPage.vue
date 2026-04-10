<template>
  <q-page padding>
    <q-pull-to-refresh @refresh="onRefresh">
      <install-banner />

      <!-- Приветствие -->
      <div class="q-mb-md">
        <div class="text-h6 text-weight-bold" style="color: #333">
          {{ greeting }}, {{ firstName }}
        </div>
        <div class="text-caption" style="color: #999">
          {{ todayDate }}
        </div>
      </div>

      <!-- 6 KPI карточек (2×3) -->
      <div class="row q-col-gutter-sm q-mb-md">
        <div v-for="kpi in kpiCards" :key="kpi.label" class="col-4">
          <q-card class="is-card" style="min-height: 80px" :style="{ borderLeft: `3px solid ${kpi.border}` }">
            <q-card-section class="q-pa-sm text-center">
              <div class="text-h6 text-weight-bold" style="color: #333">
                <q-skeleton v-if="dashboard.loading" type="text" width="30px" style="margin: 0 auto" />
                <span v-else>{{ kpi.value }}</span>
              </div>
              <div class="text-caption" style="color: #888; font-size: 10px; line-height: 1.2">
                {{ kpi.label }}
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Кнопки быстрого доступа — порядок: Клиенты, Договора, СРМ, СРМ надзора -->
      <div class="row q-col-gutter-sm q-mb-md">
        <div v-for="action in quickActions" :key="action.to" class="col-6">
          <q-btn
            :icon="action.icon"
            :label="action.label"
            :to="action.to"
            no-caps
            unelevated
            class="full-width"
            style="background: #F5F5F5; color: #333; border: 1px solid #E0E0E0; border-radius: 8px; height: 48px"
          />
        </div>
      </div>

      <!-- Мои задачи (ближайшие дедлайны) -->
      <q-card v-if="myTasks.length > 0" class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold" style="color: #333">
            Мои задачи
          </div>
        </q-card-section>
        <q-list dense separator>
          <q-item
            v-for="task in myTasks"
            :key="task.id"
            v-ripple
            clickable
            @click="$router.push(`/crm/${task.id}`)"
          >
            <q-item-section avatar>
              <q-icon name="assignment" :color="taskColor(task)" size="20px" />
            </q-item-section>
            <q-item-section>
              <q-item-label style="font-size: 12px; color: #333">
                {{ task.address || task.contract_number }}
              </q-item-label>
              <q-item-label caption style="color: #888">
                {{ task.column_name }}
              </q-item-label>
            </q-item-section>
            <q-item-section v-if="task.deadline" side>
              <div class="text-caption text-weight-bold" :style="{ color: dlColor(task.deadline) }">
                {{ fmtDeadline(task.deadline) }}
              </div>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Уведомления -->
      <q-card class="is-card">
        <q-card-section class="q-pb-none">
          <div class="row items-center justify-between">
            <div class="text-subtitle2 text-weight-bold" style="color: #333">
              Уведомления
            </div>
            <div class="row items-center q-gutter-xs">
              <q-btn
                v-if="notificationsStore.unreadCount > 0"
                flat
                dense
                no-caps
                size="xs"
                color="primary"
                label="Прочитать все"
                style="font-size: 10px"
                @click="markAllNotificationsRead"
              />
              <q-badge v-if="notificationsStore.unreadCount > 0" color="negative" :label="notificationsStore.unreadCount" />
            </div>
          </div>
        </q-card-section>
        <q-list v-if="recentNotifications.length > 0" separator>
          <q-item
            v-for="n in recentNotifications"
            :key="n.id"
            v-ripple
            clickable
            :class="{ 'bg-blue-1': !n.is_read }"
            @click="handleNotificationClick(n)"
          >
            <q-item-section avatar>
              <q-icon :name="notificationIcon(n.notification_type)" :color="n.is_read ? 'grey-5' : 'warning'" size="20px" />
            </q-item-section>
            <q-item-section>
              <q-item-label :class="{ 'text-weight-bold': !n.is_read }" style="font-size: 13px; color: #333">
                {{ n.title }}
              </q-item-label>
              <q-item-label caption lines="1" style="color: #888">
                {{ n.message }}
              </q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
        <q-card-section v-else class="text-center q-py-md" style="color: #999">
          <q-icon name="notifications_none" size="28px" class="q-mb-xs" />
          <div class="text-caption">
            Нет уведомлений
          </div>
        </q-card-section>
      </q-card>
    </q-pull-to-refresh>
  </q-page>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from 'src/stores/auth'
import { ref } from 'vue'
import { useDashboardStore } from 'src/stores/dashboard'
import { crmApi } from 'src/services/api'
import { useNotificationsStore } from 'src/stores/notifications'
import InstallBanner from 'src/components/InstallBanner.vue'

const router = useRouter()
const authStore = useAuthStore()
const dashboard = useDashboardStore()
const notificationsStore = useNotificationsStore()

const firstName = computed(() => authStore.user?.full_name?.split(' ')[0] || '')
const greeting = computed(() => { const h = new Date().getHours(); return h < 6 ? 'Доброй ночи' : h < 12 ? 'Доброе утро' : h < 18 ? 'Добрый день' : 'Добрый вечер' })
const todayDate = computed(() => new Date().toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' }))

const kpiCards = computed(() => {
  const crm = dashboard.crmStats || {}
  const cli = dashboard.clientsStats || {}
  const emp = dashboard.employeesStats || {}
  return [
    { label: 'Индивидуальные', value: crm.active_orders ?? '—', border: '#ffd93c' },
    { label: 'Шаблонные', value: crm.agent_active_orders ?? '—', border: '#F39C12' },
    { label: 'Авт. надзор', value: crm.archive_orders ?? '—', border: '#27AE60' },
    { label: 'Клиентов', value: cli.total_clients ?? '—', border: '#9B59B6' },
    { label: 'Договоров', value: cli.clients_by_year ?? '—', border: '#E74C3C' },
    { label: 'Сотрудников', value: emp.active_employees ?? '—', border: '#1ABC9C' },
  ]
})

// Порядок: Клиенты, Договора, СРМ, СРМ надзора
const quickActions = [
  { label: 'Клиенты', icon: 'people', to: '/clients' },
  { label: 'Договора', icon: 'description', to: '/contracts' },
  { label: 'СРМ', icon: 'view_kanban', to: '/crm' },
  { label: 'СРМ надзора', icon: 'engineering', to: '/supervision' },
]

const myTasks = ref([])

const recentNotifications = computed(() => notificationsStore.items.slice(0, 5))

function taskColor(task) {
  if (!task.deadline) return 'grey-5'
  const days = Math.ceil((new Date(task.deadline) - new Date()) / 86400000)
  if (days < 0) return 'negative'
  if (days <= 2) return 'warning'
  return 'grey-7'
}

function dlColor(d) {
  const days = Math.ceil((new Date(d) - new Date()) / 86400000)
  if (days < 0) return '#E74C3C'
  if (days <= 2) return '#F39C12'
  return '#888'
}

function fmtDeadline(d) {
  const days = Math.ceil((new Date(d) - new Date()) / 86400000)
  if (days < 0) return `${Math.abs(days)} дн. просрочено`
  if (days === 0) return 'Сегодня'
  if (days === 1) return 'Завтра'
  return `${days} дн.`
}
function notificationIcon(t) { return { assigned: 'assignment_ind', deadline: 'schedule', payment: 'payments', crm_stage: 'swap_horiz', supervision: 'engineering' }[t] || 'notifications' }
function handleNotificationClick(n) { if (!n.is_read) notificationsStore.markRead(n.id); if (n.related_entity_type === 'crm_card') router.push(`/crm/${n.related_entity_id}`) }
async function loadMyTasks() {
  try {
    const { data } = await crmApi.getCards('Индивидуальный', false)
    // Сортируем по дедлайну — ближайшие первыми
    myTasks.value = (data || [])
      .filter(c => c.deadline)
      .sort((a, b) => new Date(a.deadline) - new Date(b.deadline))
      .slice(0, 5)
  } catch {}
}

async function markAllNotificationsRead() {
  try {
    const { notificationsApi } = await import('../services/api.js')
    const { useAuthStore } = await import('../stores/auth.js')
    const auth = useAuthStore()
    await notificationsApi.markAllRead(auth.user?.id)
    notificationsStore.items.forEach(n => { n.is_read = true })
  } catch (err) {
    console.error('markAllRead error', err)
  }
}

function onRefresh(done) { Promise.all([dashboard.loadAll(), notificationsStore.load(), loadMyTasks()]).finally(done) }

onMounted(() => { dashboard.loadAll(); loadMyTasks() })
</script>
