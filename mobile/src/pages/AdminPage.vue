<template>
  <q-page padding>
    <!-- Подвкладки -->
    <q-tabs v-model="tab" dense active-color="dark" indicator-color="accent" no-caps class="q-mb-md" style="color: #666" align="left">
      <q-tab name="rates" label="Тарифы" />
      <q-tab name="agents" label="Агенты" />
      <q-tab name="cities" label="Города" />
      <q-tab name="roles" label="Роли" />
      <q-tab name="timeline-template" label="Шаблон сроков" />
    </q-tabs>

    <q-tab-panels v-model="tab" animated class="bg-transparent">
      <!-- Тарифы — подвкладки по типам -->
      <q-tab-panel name="rates" class="q-pa-none">
        <q-tabs v-model="rateTab" dense active-color="dark" indicator-color="accent" no-caps class="q-mb-sm" style="color: #888" align="left">
          <q-tab name="individual" label="Индивидуальные" />
          <q-tab name="template" label="Шаблонные" />
          <q-tab name="supervision" label="Надзор" />
          <q-tab name="surveyor" label="Замерщик" />
        </q-tabs>

        <q-card class="is-card" v-for="rate in filteredRates" :key="rate.id">
          <q-card-section class="q-pa-sm">
            <div class="row items-center justify-between">
              <div>
                <div class="text-weight-bold" style="font-size: 12px; color: #333">{{ rate.role }}</div>
                <div class="text-caption" style="color: #888">
                  {{ rate.stage_name || '' }}
                  <span v-if="rate.city"> | {{ rate.city }}</span>
                  <span v-if="rate.area_from"> | {{ rate.area_from }}-{{ rate.area_to }} м²</span>
                </div>
              </div>
              <div class="text-weight-bold" style="color: #333">
                <span v-if="rate.rate_per_m2">{{ rate.rate_per_m2 }} ₽/м²</span>
                <span v-else-if="rate.fixed_price">{{ rate.fixed_price }} ₽</span>
                <span v-else-if="rate.surveyor_price">{{ rate.surveyor_price }} ₽</span>
              </div>
            </div>
          </q-card-section>
        </q-card>
        <div v-if="filteredRates.length === 0" class="text-center q-pa-md" style="color: #999">Нет тарифов</div>
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
                <q-item-label class="text-weight-medium" style="color: #333">{{ agent.name }}</q-item-label>
                <q-item-label caption style="color: #999">{{ agent.color }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <!-- Кнопка выбора цвета -->
                <q-btn flat dense size="sm" icon="palette" @click="editAgentColor(agent)">
                  <q-tooltip>Изменить цвет</q-tooltip>
                </q-btn>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
        <q-page-sticky position="bottom-right" :offset="[18, 70]">
          <q-btn fab icon="add" style="background: #ffd93c; color: #333" @click="addAgent" />
        </q-page-sticky>
      </q-tab-panel>

      <!-- Города -->
      <q-tab-panel name="cities" class="q-pa-none">
        <q-card class="is-card">
          <q-list separator>
            <q-item v-for="city in refs.cities" :key="city">
              <q-item-section avatar><q-icon name="location_on" color="grey-7" /></q-item-section>
              <q-item-section style="color: #333">{{ city }}</q-item-section>
              <q-item-section side>
                <q-btn flat dense size="sm" icon="edit" color="grey-7" @click="editCity(city)">
                  <q-tooltip>Редактировать</q-tooltip>
                </q-btn>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
        <q-page-sticky position="bottom-right" :offset="[18, 70]">
          <q-btn fab icon="add" style="background: #ffd93c; color: #333" @click="addCity" />
        </q-page-sticky>
      </q-tab-panel>

      <!-- Роли и права -->
      <q-tab-panel name="roles" class="q-pa-none">
        <q-card class="is-card q-mb-md">
          <q-card-section>
            <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: #333">Матрица ролей</div>
            <div class="text-caption" style="color: #888">Управление правами доступа по должностям</div>
          </q-card-section>
          <q-list separator>
            <q-item v-for="role in rolesList" :key="role" clickable v-ripple @click="viewRolePermissions(role)">
              <q-item-section avatar><q-icon name="security" color="grey-7" /></q-item-section>
              <q-item-section style="color: #333">{{ role }}</q-item-section>
              <q-item-section side><q-icon name="chevron_right" color="grey-5" /></q-item-section>
            </q-item>
          </q-list>
        </q-card>
      </q-tab-panel>

      <!-- Шаблон таблицы сроков -->
      <q-tab-panel name="timeline-template" class="q-pa-none">
        <q-card class="is-card">
          <q-card-section>
            <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: #333">Шаблон таблицы сроков</div>
            <div class="text-caption" style="color: #888">Нормодни для стадий проектов</div>
          </q-card-section>
          <q-list dense separator v-if="normDays.length > 0">
            <q-item v-for="nd in normDays" :key="nd.id">
              <q-item-section>
                <q-item-label style="font-size: 12px; color: #333">{{ nd.stage_name }}</q-item-label>
                <q-item-label caption style="color: #888">{{ nd.executor_role }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <div class="text-weight-bold" style="color: #333">{{ nd.norm_days }} дн.</div>
              </q-item-section>
            </q-item>
          </q-list>
          <q-card-section v-else class="text-center" style="color: #999">Не настроено</q-card-section>
        </q-card>
      </q-tab-panel>
    </q-tab-panels>

    <!-- Диалог прав роли -->
    <q-dialog v-model="showRoleDialog" maximized transition-show="slide-up" transition-hide="slide-down">
      <q-card>
        <q-toolbar style="background: #ffd93c; color: #333">
          <q-btn flat round dense icon="close" @click="showRoleDialog = false" />
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">Права: {{ selectedRole }}</q-toolbar-title>
        </q-toolbar>
        <q-card-section style="max-height: calc(100vh - 50px); overflow-y: auto">
          <q-list dense>
            <q-item v-for="perm in rolePermissions" :key="perm.name" tag="label">
              <q-item-section>
                <q-item-label style="font-size: 12px">{{ perm.description || perm.name }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-toggle v-model="perm.granted" color="accent" dense />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'src/boot/axios'
import { useReferencesStore } from 'src/stores/references'

const $q = useQuasar()
const refs = useReferencesStore()
const tab = ref('rates')
const rateTab = ref('individual')
const rates = ref([])
const normDays = ref([])
const showRoleDialog = ref(false)
const selectedRole = ref('')
const rolePermissions = ref([])

const rolesList = refs.positions

const rateTypeMap = {
  individual: 'Индивидуальный',
  template: 'Шаблонный',
  supervision: 'Авторский надзор',
  surveyor: 'Замерщик'
}

const filteredRates = computed(() => {
  const pt = rateTypeMap[rateTab.value]
  if (rateTab.value === 'surveyor') {
    return rates.value.filter(r => r.surveyor_price)
  }
  return rates.value.filter(r => r.project_type === pt)
})

async function loadRates() {
  try {
    const { data } = await api.get('/api/v1/rates')
    rates.value = data
  } catch { rates.value = [] }
}

async function loadNormDays() {
  try {
    const { data } = await api.get('/api/v1/norm-days')
    normDays.value = data
  } catch { normDays.value = [] }
}

async function viewRolePermissions(role) {
  selectedRole.value = role
  try {
    const [defsRes, matrixRes] = await Promise.allSettled([
      api.get('/api/v1/permissions/definitions'),
      api.get('/api/v1/permissions/role-matrix')
    ])
    const defs = defsRes.status === 'fulfilled' ? defsRes.value.data : []
    const matrix = matrixRes.status === 'fulfilled' ? matrixRes.value.data?.roles || {} : {}
    const rolePerms = matrix[role] || []
    rolePermissions.value = defs.map(d => ({
      name: d.name,
      description: d.description,
      granted: rolePerms.includes(d.name)
    }))
    showRoleDialog.value = true
  } catch {}
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

function editAgentColor(agent) {
  // Простой ввод цвета (в будущем — карта цветов)
  $q.dialog({
    title: `Цвет: ${agent.name}`,
    prompt: { model: agent.color || '#95A5A6', type: 'color' },
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

function editCity(city) {
  $q.dialog({
    title: 'Редактировать город',
    prompt: { model: city, type: 'text', label: 'Название' },
    cancel: true
  }).onOk(async (newName) => {
    // API не поддерживает rename напрямую — создаём новый, удаляем старый
    $q.notify({ type: 'info', message: 'Переименование городов — через удаление и создание нового' })
  })
}

onMounted(() => {
  loadRates()
  loadNormDays()
})
</script>
