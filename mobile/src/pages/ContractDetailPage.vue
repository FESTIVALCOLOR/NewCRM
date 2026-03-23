<template>
  <q-page padding>
    <template v-if="contract">
      <!-- Шапка -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="row items-center justify-between q-mb-sm">
            <div class="text-h6 text-weight-bold">{{ contract.contract_number }}</div>
            <q-badge :color="statusColor(contract.status)" :label="contract.status" />
          </div>
          <div class="text-body1 q-mb-sm">{{ contract.address }}</div>
          <div class="row q-gutter-md text-caption text-grey-7">
            <span>{{ contract.project_type }}</span>
            <span v-if="contract.area">{{ contract.area }} м²</span>
            <span v-if="contract.city">{{ contract.city }}</span>
            <span v-if="contract.floors">{{ contract.floors }} эт.</span>
          </div>
        </q-card-section>
      </q-card>

      <!-- Суммы -->
      <q-card class="is-card q-mb-md" v-if="contract.total_amount">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm">Финансы</div>
          <div class="row q-col-gutter-sm">
            <div class="col-6">
              <div class="text-caption text-grey-7">Общая сумма</div>
              <div class="text-weight-bold">{{ formatMoney(contract.total_amount) }}</div>
            </div>
            <div class="col-6" v-if="contract.advance_payment">
              <div class="text-caption text-grey-7">Аванс</div>
              <div class="text-weight-bold">{{ formatMoney(contract.advance_payment) }}</div>
            </div>
            <div class="col-6" v-if="contract.additional_payment">
              <div class="text-caption text-grey-7">Доп. оплата</div>
              <div>{{ formatMoney(contract.additional_payment) }}</div>
            </div>
            <div class="col-6" v-if="contract.third_payment">
              <div class="text-caption text-grey-7">Третий платёж</div>
              <div>{{ formatMoney(contract.third_payment) }}</div>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Детали -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold">Детали</div>
        </q-card-section>
        <q-list dense>
          <q-item v-if="contract.contract_date">
            <q-item-section avatar><q-icon name="event" color="grey-7" /></q-item-section>
            <q-item-section>
              <q-item-label caption>Дата договора</q-item-label>
              <q-item-label>{{ formatDate(contract.contract_date) }}</q-item-label>
            </q-item-section>
          </q-item>
          <q-item v-if="contract.contract_period">
            <q-item-section avatar><q-icon name="schedule" color="grey-7" /></q-item-section>
            <q-item-section>
              <q-item-label caption>Срок выполнения</q-item-label>
              <q-item-label>{{ contract.contract_period }} дней</q-item-label>
            </q-item-section>
          </q-item>
          <q-item v-if="contract.agent_type">
            <q-item-section avatar><q-icon name="business" color="grey-7" /></q-item-section>
            <q-item-section>
              <q-item-label caption>Тип агента</q-item-label>
              <q-item-label>{{ contract.agent_type }}</q-item-label>
            </q-item-section>
          </q-item>
          <q-item v-if="contract.comments">
            <q-item-section avatar><q-icon name="comment" color="grey-7" /></q-item-section>
            <q-item-section>
              <q-item-label caption>Комментарий</q-item-label>
              <q-item-label>{{ contract.comments }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Файлы -->
      <q-card class="is-card q-mb-md" v-if="files.length > 0">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold">Файлы ({{ files.length }})</div>
        </q-card-section>
        <q-list dense>
          <q-item
            v-for="file in files"
            :key="file.id"
            clickable
            @click="openFile(file)"
          >
            <q-item-section avatar>
              <q-icon :name="fileIcon(file.file_type)" :color="fileColor(file.file_type)" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ file.file_name }}</q-item-label>
              <q-item-label caption>{{ file.stage }}</q-item-label>
            </q-item-section>
            <q-item-section side><q-icon name="open_in_new" color="grey-5" /></q-item-section>
          </q-item>
        </q-list>
      </q-card>
    </template>

    <div v-else-if="!loading" class="text-center q-pa-xl text-grey-5">
      <q-icon name="description" size="48px" class="q-mb-sm" />
      <div>Договор не найден</div>
    </div>
    <div v-else class="text-center q-pa-xl">
      <q-spinner size="40px" color="primary" />
    </div>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { contractsApi, filesApi } from 'src/services/api'

const route = useRoute()
const contract = ref(null)
const files = ref([])
const loading = ref(true)

function statusColor(status) {
  if (!status) return 'grey'
  if (status === 'В работе') return 'orange'
  if (status.includes('СДАН')) return 'positive'
  if (status.includes('РАСТОРГНУТ')) return 'negative'
  return 'blue'
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('ru-RU', {
    day: 'numeric', month: 'long', year: 'numeric'
  })
}

function formatMoney(amount) {
  if (!amount) return '0 ₽'
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency', currency: 'RUB', maximumFractionDigits: 0
  }).format(amount)
}

function fileIcon(type) {
  const icons = { image: 'image', pdf: 'picture_as_pdf', excel: 'table_chart', word: 'article', cad: 'architecture' }
  return icons[type] || 'insert_drive_file'
}

function fileColor(type) {
  const colors = { image: 'green', pdf: 'red', excel: 'teal', word: 'blue', cad: 'purple' }
  return colors[type] || 'grey-7'
}

function openFile(file) {
  if (file.public_link) window.open(file.public_link, '_blank')
}

onMounted(async () => {
  const id = route.params.id
  try {
    const [contractRes, filesRes] = await Promise.allSettled([
      contractsApi.getById(id),
      filesApi.getContractFiles(id)
    ])
    if (contractRes.status === 'fulfilled') contract.value = contractRes.value.data
    if (filesRes.status === 'fulfilled') files.value = filesRes.value.data || []
  } finally {
    loading.value = false
  }
})
</script>
