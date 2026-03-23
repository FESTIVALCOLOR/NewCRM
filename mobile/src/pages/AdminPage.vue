<template>
  <q-page padding>
    <!-- Подвкладки -->
    <q-tabs v-model="tab" dense active-color="dark" indicator-color="accent" no-caps class="q-mb-md text-grey-7" align="left">
      <q-tab name="rates" label="Тарифы" icon="price_change" />
      <q-tab name="agents" label="Агенты" icon="groups" />
      <q-tab name="cities" label="Города" icon="location_city" />
      <q-tab name="notifications" label="Уведомления" icon="notifications" />
    </q-tabs>

    <q-tab-panels v-model="tab" animated class="bg-transparent">
      <!-- Тарифы -->
      <q-tab-panel name="rates" class="q-pa-none">
        <q-pull-to-refresh @refresh="loadRates">
          <q-card class="is-card q-mb-md" v-for="rate in rates" :key="rate.id">
            <q-card-section class="q-pa-md">
              <div class="row items-center justify-between">
                <div>
                  <div class="text-weight-bold">{{ rate.role }}</div>
                  <div class="text-caption" style="color: #888">
                    {{ rate.project_type }}
                    <span v-if="rate.stage_name"> — {{ rate.stage_name }}</span>
                    <span v-if="rate.city"> — {{ rate.city }}</span>
                  </div>
                </div>
                <div class="text-right">
                  <div class="text-weight-bold" v-if="rate.rate_per_m2">{{ rate.rate_per_m2 }} ₽/м²</div>
                  <div class="text-weight-bold" v-else-if="rate.fixed_price">{{ rate.fixed_price }} ₽</div>
                  <div class="text-weight-bold" v-else-if="rate.surveyor_price">{{ rate.surveyor_price }} ₽</div>
                </div>
              </div>
            </q-card-section>
          </q-card>
          <div v-if="rates.length === 0" class="text-center q-pa-xl" style="color: #999">Нет тарифов</div>
        </q-pull-to-refresh>
      </q-tab-panel>

      <!-- Агенты -->
      <q-tab-panel name="agents" class="q-pa-none">
        <q-card class="is-card">
          <q-list separator>
            <q-item v-for="agent in refs.agents" :key="agent.id">
              <q-item-section avatar>
                <q-avatar size="32px" :style="{ background: agent.color || '#95A5A6' }" text-color="white">
                  {{ agent.name ? agent.name[0] : '?' }}
                </q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-weight-medium">{{ agent.name }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <div class="row q-gutter-xs">
                  <q-btn flat dense size="sm" icon="palette" @click="editAgentColor(agent)">
                    <q-tooltip>Изменить цвет</q-tooltip>
                  </q-btn>
                </div>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
        <q-page-sticky position="bottom-right" :offset="[18, 18]">
          <q-btn fab icon="add" color="accent" text-color="dark" @click="addAgent" />
        </q-page-sticky>
      </q-tab-panel>

      <!-- Города -->
      <q-tab-panel name="cities" class="q-pa-none">
        <q-card class="is-card">
          <q-list separator>
            <q-item v-for="city in refs.cities" :key="city">
              <q-item-section avatar><q-icon name="location_on" color="grey-7" /></q-item-section>
              <q-item-section>{{ city }}</q-item-section>
            </q-item>
          </q-list>
        </q-card>
        <q-page-sticky position="bottom-right" :offset="[18, 18]">
          <q-btn fab icon="add" color="accent" text-color="dark" @click="addCity" />
        </q-page-sticky>
      </q-tab-panel>

      <!-- Настройки уведомлений -->
      <q-tab-panel name="notifications" class="q-pa-none">
        <q-card class="is-card" v-if="notifSettings">
          <q-card-section class="q-pb-none">
            <div class="text-subtitle2 text-weight-bold">Мои уведомления</div>
          </q-card-section>
          <q-list>
            <q-item tag="label" v-for="opt in notifOptions" :key="opt.key">
              <q-item-section>
                <q-item-label>{{ opt.label }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-toggle v-model="notifSettings[opt.key]" color="accent" @update:model-value="saveNotifSettings" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
        <div v-else class="text-center q-pa-xl">
          <q-spinner size="40px" color="accent" />
        </div>
      </q-tab-panel>
    </q-tab-panels>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'src/boot/axios'
import { useAuthStore } from 'src/stores/auth'
import { useReferencesStore } from 'src/stores/references'

const $q = useQuasar()
const authStore = useAuthStore()
const refs = useReferencesStore()
const tab = ref('rates')
const rates = ref([])
const notifSettings = ref(null)

const notifOptions = [
  { key: 'telegram_enabled', label: 'Telegram уведомления' },
  { key: 'email_enabled', label: 'Email уведомления' },
  { key: 'notify_crm_stage', label: 'Смена стадии CRM' },
  { key: 'notify_assigned', label: 'Назначение задач' },
  { key: 'notify_deadline', label: 'Дедлайны' },
  { key: 'notify_payment', label: 'Оплаты' },
  { key: 'notify_supervision', label: 'Авторский надзор' },
  { key: 'notify_individual', label: 'Индивидуальные проекты' },
  { key: 'notify_template', label: 'Шаблонные проекты' }
]

async function loadRates(done) {
  try {
    const { data } = await api.get('/api/v1/rates')
    rates.value = data
  } catch { rates.value = [] }
  if (done) done()
}

async function loadNotifSettings() {
  const empId = authStore.user?.id
  if (!empId) return
  try {
    const { data } = await api.get(`/api/v1/notifications/settings/${empId}`)
    notifSettings.value = data
  } catch {}
}

async function saveNotifSettings() {
  const empId = authStore.user?.id
  if (!empId || !notifSettings.value) return
  try {
    await api.put(`/api/v1/notifications/settings/${empId}`, notifSettings.value)
    $q.notify({ type: 'positive', message: 'Настройки сохранены' })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

function addAgent() {
  $q.dialog({
    title: 'Новый агент',
    prompt: { model: '', type: 'text', label: 'Название' },
    cancel: true
  }).onOk(async (name) => {
    try {
      await api.post('/api/v1/agents', { name, color: '#95A5A6' })
      $q.notify({ type: 'positive', message: 'Агент добавлен' })
      refs.loaded = false
      refs.loadAll()
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
    }
  })
}

function addCity() {
  $q.dialog({
    title: 'Новый город',
    prompt: { model: '', type: 'text', label: 'Название' },
    cancel: true
  }).onOk(async (name) => {
    try {
      await api.post('/api/v1/cities', { name })
      $q.notify({ type: 'positive', message: 'Город добавлен' })
      refs.loaded = false
      refs.loadAll()
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
    }
  })
}

function editAgentColor(agent) {
  $q.dialog({
    title: `Цвет: ${agent.name}`,
    prompt: { model: agent.color || '#95A5A6', type: 'text', label: 'HEX цвет' },
    cancel: true
  }).onOk(async (color) => {
    try {
      await api.patch(`/api/v1/agents/${encodeURIComponent(agent.name)}/color`, { color })
      $q.notify({ type: 'positive', message: 'Цвет обновлён' })
      refs.loaded = false
      refs.loadAll()
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
    }
  })
}

onMounted(() => {
  loadRates()
  loadNotifSettings()
})
</script>
