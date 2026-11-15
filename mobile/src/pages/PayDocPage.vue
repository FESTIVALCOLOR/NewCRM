<template>
  <q-page class="pd-page">
    <div v-if="loading" class="text-center q-pa-xl">
      <q-spinner size="40px" />
    </div>
    <div v-else-if="error" class="pd-card text-center">
      <q-icon name="receipt_long" size="48px" color="grey-5" />
      <div class="q-mt-sm">
        {{ error }}
      </div>
    </div>
    <div v-else class="pd-card">
      <img src="/festival_logo.png" alt="Festival Color" class="pd-logo">
      <h1 class="pd-title">
        Документ, подтверждающий расчёт № {{ doc.number }}
      </h1>
      <div class="pd-sub">
        выдан без применения ККТ на основании п. 2.1 ст. 2 Федерального закона № 54-ФЗ
      </div>
      <div v-if="doc.annulled" class="pd-annulled">
        Документ аннулирован
      </div>

      <div class="pd-amount">
        <span>{{ doc.calc_sign === 'Возврат прихода' ? 'Возврат' : 'Оплата' }}</span>
        <b>{{ money(doc.amount) }}</b>
      </div>

      <dl class="pd-list">
        <template v-for="row in rows" :key="row[0]">
          <dt>{{ row[0] }}</dt>
          <dd>{{ row[1] }}</dd>
        </template>
      </dl>

      <div class="pd-actions">
        <a class="pd-btn pd-btn--main" :href="pdfUrl(true)" :download="doc.filename">
          <q-icon name="download" size="18px" />Скачать PDF
        </a>
        <a class="pd-btn" :href="pdfUrl(false)" target="_blank" rel="noopener">
          <q-icon name="open_in_new" size="18px" />Открыть PDF
        </a>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { clientPaymentsApi } from 'src/services/api'

const route = useRoute()
const loading = ref(true)
const error = ref('')
const doc = ref({})

const rows = computed(() => {
  const d = doc.value
  return [
    ['Дата и время расчёта', `${d.date_text || ''} ${d.time || ''} (МСК)`],
    ['Место расчёта', d.place],
    ['Исполнитель', d.seller_name],
    ['ИНН', d.seller_inn],
    ['ОГРНИП', d.seller_ogrnip],
    ['Система налогообложения', d.tax_system],
    ['Признак расчёта', d.calc_sign],
    ['Клиент', d.client_name],
    ['Основание', d.basis],
    ['Услуга', d.service],
    ['НДС', 'без НДС'],
    ['Форма расчёта', d.method_text],
    ['Расчёт осуществил', d.cashier],
  ].filter(row => row[1])
})

function money(v) {
  return new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(v) || 0) + ' ₽'
}
function pdfUrl(download) {
  return clientPaymentsApi.publicPdfUrl(route.params.token, download)
}

onMounted(async () => {
  try {
    const { data } = await clientPaymentsApi.publicDoc(route.params.token)
    doc.value = data
    document.title = `Документ № ${data.number}`
  } catch {
    error.value = 'Документ не найден или ссылка недействительна'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.pd-page { display: flex; justify-content: center; padding: 16px; background: #F4F5F7; min-height: 100vh; }
.pd-card { width: 100%; max-width: 640px; background: #fff; color: #222; border-radius: 12px; padding: 24px 20px; box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06); align-self: flex-start; }
.pd-logo { display: block; height: 64px; margin: 0 auto 14px; object-fit: contain; }
.pd-title { font-size: 18px; line-height: 1.3; font-weight: 700; text-align: center; margin: 0; }
.pd-sub { font-size: 12px; color: #777; text-align: center; margin-top: 6px; }
.pd-annulled { margin-top: 12px; text-align: center; color: #C62828; font-weight: 700; border: 1px solid #F5B7B1; background: #FDEDEC; border-radius: 8px; padding: 8px; }
.pd-amount { display: flex; justify-content: space-between; align-items: baseline; margin: 18px 0 8px; padding: 12px 14px; background: #F8F9FA; border-radius: 8px; }
.pd-amount span { color: #666; }
.pd-amount b { font-size: 22px; }
.pd-list { display: grid; grid-template-columns: minmax(120px, 38%) 1fr; margin: 0; border-top: 1px solid #EEE; }
.pd-list dt, .pd-list dd { margin: 0; padding: 8px 4px; border-bottom: 1px solid #EEE; font-size: 13px; overflow-wrap: anywhere; }
.pd-list dt { color: #666; }
.pd-actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }
.pd-btn { flex: 1 1 180px; display: inline-flex; align-items: center; justify-content: center; gap: 6px; height: 42px; border-radius: 8px; border: 1px solid #D0D4DA; color: #222; text-decoration: none; font-size: 14px; }
.pd-btn--main { background: #222; color: #fff; border-color: #222; }
@media (max-width: 480px) {
  .pd-list { grid-template-columns: 1fr; }
  .pd-list dt { border-bottom: none; padding-bottom: 0; font-size: 12px; }
}
</style>
