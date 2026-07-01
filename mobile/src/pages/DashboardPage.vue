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
          <q-card
            v-ripple
            class="is-card"
            style="min-height: 80px; cursor: pointer"
            :style="{ borderLeft: `3px solid ${kpi.border}` }"
            clickable
            @click="router.push(kpi.to)"
          >
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
        <div v-for="action in quickActions" :key="action.to" :class="quickActions.length === 1 ? 'col-12' : 'col-6'">
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
          <div style="height: 1px; background: #222; margin-top: 6px" />
        </q-card-section>
        <q-list dense separator>
          <template v-for="(task, idx) in myTasks" :key="`${task._card_type || 'crm'}-${task.id}`">
            <!-- Разделитель между CRM и надзором -->
            <div
              v-if="task._card_type === 'supervision' && (idx === 0 || myTasks[idx - 1]._card_type !== 'supervision')"
              style="height: 3px; background: #1565C0; margin: 2px 0"
            />
            <q-item
              v-ripple
              clickable
              :style="taskBg(task)"
              @click="$router.push(task._card_type === 'supervision' ? `/supervision/${task.id}` : `/crm/${task.id}`)"
            >
              <q-item-section avatar>
                <q-icon :name="task._card_type === 'supervision' ? 'engineering' : 'assignment'" :color="taskColor(task)" size="20px" />
              </q-item-section>
              <q-item-section>
                <q-item-label style="font-size: 12px; color: #333">
                  {{ task.address || task.contract_number }}
                </q-item-label>
                <q-item-label caption style="color: #888">
                  {{ task.column_name }}
                </q-item-label>
              </q-item-section>
              <q-item-section side style="padding-left: 4px">
                <div style="display: flex; align-items: center; gap: 10px; flex-shrink: 0">
                  <button
                    class="dash-mute-bell-btn"
                    @click.stop="cardMutes.toggleMute(entityType(task), task.id)"
                  >
                    <span
                      class="material-icons"
                      :style="{ fontSize: '16px', color: cardMutes.isMuted(entityType(task), task.id) ? '#333' : '#CCC' }"
                    >
                      {{ cardMutes.isMuted(entityType(task), task.id) ? 'notifications_off' : 'notifications' }}
                    </span>
                  </button>
                  <div
                    v-if="task.is_paused"
                    style="width: 52px; text-align: right; font-size: 10px; font-weight: 600; color: #B8860B; line-height: 1.2; white-space: normal"
                  >
                    Пауза
                  </div>
                  <div
                    v-else-if="task.deadline || task.current_stage_deadline"
                    style="width: 52px; text-align: right; font-size: 10px; font-weight: 600; line-height: 1.2; white-space: normal"
                    :style="{ color: dlColor(task.deadline || task.current_stage_deadline) }"
                  >
                    {{ fmtDeadline(task.deadline || task.current_stage_deadline) }}
                  </div>
                  <div v-else style="width: 52px" />
                </div>
              </q-item-section>
            </q-item>
          </template>
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
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from 'src/stores/auth'
import { useDashboardStore } from 'src/stores/dashboard'
import { crmApi, supervisionApi } from 'src/services/api'
import { useNotificationsStore } from 'src/stores/notifications'
import { usePermissionsStore } from 'src/stores/permissions'
import { useCardMutesStore } from 'src/stores/cardMutes'
import InstallBanner from 'src/components/InstallBanner.vue'

const router = useRouter()
const authStore = useAuthStore()
const dashboard = useDashboardStore()
const notificationsStore = useNotificationsStore()
const permissionsStore = usePermissionsStore()
const cardMutes = useCardMutesStore()

function entityType(task) {
  return task._card_type === 'supervision' ? 'supervision_card' : 'crm_card'
}

const firstName = computed(() => authStore.user?.full_name?.split(' ')[0] || '')
const greeting = computed(() => { const h = new Date().getHours(); return h < 6 ? 'Доброй ночи' : h < 12 ? 'Доброе утро' : h < 18 ? 'Добрый день' : 'Добрый вечер' })
const todayDate = computed(() => new Date().toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' }))

const kpiCards = computed(() => {
  const crm = dashboard.crmStats || {}
  const crmT = dashboard.crmTemplateStats || {}
  const crmN = dashboard.crmNadzorStats || {}
  const cli = dashboard.clientsStats || {}
  const con = dashboard.contractsStats || {}
  const emp = dashboard.employeesStats || {}
  const totalContracts = (con.individual_orders ?? 0) + (con.template_orders ?? 0)
  return [
    { label: 'Индивидуальные', value: crm.active_orders ?? '—', border: '#ffd93c', to: '/crm?type=Индивидуальный' },
    { label: 'Шаблонные', value: crmT.active_orders ?? '—', border: '#F39C12', to: '/crm?type=Шаблонный' },
    { label: 'Авт. надзор', value: crmN.active_orders ?? '—', border: '#27AE60', to: '/supervision' },
    { label: 'Клиентов', value: cli.total_clients ?? '—', border: '#9B59B6', to: '/clients' },
    { label: 'Договоров', value: totalContracts || '—', border: '#E74C3C', to: '/contracts' },
    { label: 'Сотрудников', value: emp.active_employees ?? '—', border: '#1ABC9C', to: '/employees' },
  ]
})

// Порядок: Клиенты, Договора, СРМ, СРМ надзора — фильтруются по правам
const ALL_QUICK_ACTIONS = [
  { label: 'Клиенты', icon: 'people', to: '/clients', perm: 'access.clients' },
  { label: 'Договора', icon: 'description', to: '/contracts', perm: 'access.contracts' },
  { label: 'СРМ', icon: 'view_kanban', to: '/crm', perm: 'access.crm' },
  { label: 'СРМ надзора', icon: 'engineering', to: '/supervision', perm: 'access.supervision' },
]
const quickActions = computed(() =>
  ALL_QUICK_ACTIONS.filter(a => permissionsStore.has(a.perm)),
)

const myTasks = ref([])

const recentNotifications = computed(() => notificationsStore.items.slice(0, 5))

function taskBg(task) {
  if (task.is_paused) return { background: '#FFFDE7' }
  if (task._card_type === 'supervision') return { background: '#E3F2FD' }
  return {}
}

function taskColor(task) {
  if (task.is_paused) return 'amber-7'
  if (task._card_type === 'supervision') return 'blue-5'
  const d = task.deadline || task.current_stage_deadline
  if (!d) return 'grey-5'
  const days = Math.ceil((new Date(d) - new Date()) / 86400000)
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
const STUDIO_DIRECTOR_POSITION = 'Руководитель студии'

function _isAssignedCrm(c, userId) {
  return (
    c.manager_id === userId ||
    c.senior_manager_id === userId ||
    c.sdp_id === userId ||
    c.gap_id === userId ||
    c.surveyor_id === userId ||
    c.stage_plan_executor_id === userId ||
    c.designer_executor_id === userId ||
    c.draftsman_executor_id === userId ||
    c.current_stage_executor_id === userId
  )
}

function _isAssignedSupervision(c, userId) {
  return c.senior_manager_id === userId || c.dan_id === userId || c.studio_director_id === userId
}

async function loadMyTasks() {
  try {
    const userId = authStore.user?.id
    if (!userId) return
    const isDirector =
      authStore.user?.position === STUDIO_DIRECTOR_POSITION ||
      ['admin', 'director'].includes(authStore.user?.role)

    const [{ data: ind }, { data: tmpl }, svResp] = await Promise.all([
      crmApi.getCards('Индивидуальный', false),
      crmApi.getCards('Шаблонный', false),
      supervisionApi.getCards({ status: 'active' }).catch(() => ({ data: [] })),
    ])
    const svData = svResp?.data || []

    // CRM карточки (уже не архивные — archived=false передан в getCards)
    const crmFiltered = [...(ind || []), ...(tmpl || [])].filter(c =>
      isDirector ? true : _isAssignedCrm(c, userId),
    )

    // Карточки надзора (status=active, включая паузированные — они выделяются цветом)
    const svFiltered = svData
      .filter(c => (isDirector ? true : _isAssignedSupervision(c, userId)))
      .map(c => ({ ...c, _card_type: 'supervision' }))

    const byDeadline = (a, b) => {
      const da = a.deadline || a.current_stage_deadline
      const db2 = b.deadline || b.current_stage_deadline
      if (!da && !db2) return 0
      if (!da) return 1
      if (!db2) return -1
      return new Date(da) - new Date(db2)
    }

    // CRM сначала (отсортированные по дедлайну), потом надзор (отсортированный по дедлайну)
    myTasks.value = [
      ...crmFiltered.sort(byDeadline).slice(0, 7),
      ...svFiltered.sort(byDeadline).slice(0, 7),
    ].slice(0, 10)
  } catch (e) {
    console.error('loadMyTasks error', e)
  }
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

onMounted(() => { dashboard.loadAll(); loadMyTasks(); cardMutes.load() })
</script>

<style scoped>
.dash-mute-bell-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  padding: 2px;
  cursor: pointer;
  line-height: 1;
}
</style>
