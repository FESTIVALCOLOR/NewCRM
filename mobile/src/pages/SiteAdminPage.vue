<template>
  <q-page class="site-admin q-pa-md">
    <div class="page-header q-mb-lg">
      <div class="text-h5 text-weight-bold">
        Управление сайтом
      </div>
      <div class="text-caption text-grey">
        festivalcolor.ru
      </div>
    </div>

    <!-- Вкладки секций -->
    <q-tabs
      v-model="tab"
      dense
      align="left"
      class="q-mb-md"
      indicator-color="primary"
    >
      <q-tab name="settings" label="Настройки" icon="settings" />
      <q-tab name="team" label="Команда" icon="people" />
      <q-tab name="stats" label="Статистика" icon="bar_chart" />
      <q-tab name="services" label="Услуги" icon="design_services" />
      <q-tab name="pricing" label="Тарифы" icon="price_change" />
      <q-tab name="reviews" label="Отзывы" icon="star" />
      <q-tab name="portfolio" label="Портфолио" icon="photo_library" />
    </q-tabs>

    <q-tab-panels v-model="tab" animated>
      <!-- НАСТРОЙКИ -->
      <q-tab-panel name="settings">
        <div v-if="loading" class="flex justify-center q-pa-xl">
          <q-spinner size="40px" />
        </div>
        <q-list v-else bordered separator>
          <q-item v-for="s in settings" :key="s.key" class="q-py-sm">
            <q-item-section>
              <q-item-label class="text-caption text-grey">
                {{ s.label || s.key }}
              </q-item-label>
              <q-input v-model="s.value" dense filled @blur="saveSetting(s)" />
            </q-item-section>
          </q-item>
        </q-list>
      </q-tab-panel>

      <!-- КОМАНДА -->
      <q-tab-panel name="team">
        <q-btn
          label="Добавить участника"
          icon="add"
          color="primary"
          class="q-mb-md"
          @click="openTeamDialog(null)"
        />
        <q-list bordered separator>
          <q-item v-for="m in team" :key="m.id">
            <q-item-section avatar>
              <q-avatar color="orange" text-color="white">
                {{ m.name[0] }}
              </q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ m.name }}</q-item-label>
              <q-item-label caption>
                {{ m.position }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="row gap-xs">
                <q-btn
                  flat
                  round
                  icon="edit"
                  size="sm"
                  @click="openTeamDialog(m)"
                />
                <q-btn
                  flat
                  round
                  icon="delete"
                  size="sm"
                  color="negative"
                  @click="deleteTeam(m.id)"
                />
              </div>
            </q-item-section>
          </q-item>
        </q-list>
      </q-tab-panel>

      <!-- СТАТИСТИКА -->
      <q-tab-panel name="stats">
        <q-btn
          label="Добавить"
          icon="add"
          color="primary"
          class="q-mb-md"
          @click="openStatDialog(null)"
        />
        <q-list bordered separator>
          <q-item v-for="s in stats" :key="s.id">
            <q-item-section>
              <q-item-label class="text-weight-bold text-h6">
                {{ s.value }}
              </q-item-label>
              <q-item-label caption>
                {{ s.label }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="row gap-xs">
                <q-btn
                  flat
                  round
                  icon="edit"
                  size="sm"
                  @click="openStatDialog(s)"
                />
                <q-btn
                  flat
                  round
                  icon="delete"
                  size="sm"
                  color="negative"
                  @click="deleteStat(s.id)"
                />
              </div>
            </q-item-section>
          </q-item>
        </q-list>
      </q-tab-panel>

      <!-- УСЛУГИ -->
      <q-tab-panel name="services">
        <q-btn
          label="Добавить"
          icon="add"
          color="primary"
          class="q-mb-md"
          @click="openServiceDialog(null)"
        />
        <q-list bordered separator>
          <q-item v-for="s in services" :key="s.id">
            <q-item-section>
              <q-item-label>{{ s.title }}</q-item-label>
              <q-item-label caption>
                {{ s.description?.slice(0,80) }}…
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="row gap-xs">
                <q-btn
                  flat
                  round
                  icon="edit"
                  size="sm"
                  @click="openServiceDialog(s)"
                />
                <q-btn
                  flat
                  round
                  icon="delete"
                  size="sm"
                  color="negative"
                  @click="deleteService(s.id)"
                />
              </div>
            </q-item-section>
          </q-item>
        </q-list>
      </q-tab-panel>

      <!-- ТАРИФЫ -->
      <q-tab-panel name="pricing">
        <q-btn
          label="Добавить тариф"
          icon="add"
          color="primary"
          class="q-mb-md"
          @click="openPricingDialog(null)"
        />
        <q-list bordered separator>
          <q-item v-for="p in pricing" :key="p.id">
            <q-item-section>
              <q-item-label>{{ p.title }}</q-item-label>
              <q-item-label caption>
                {{ p.items.length }} пунктов
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="row gap-xs">
                <q-btn
                  flat
                  round
                  icon="edit"
                  size="sm"
                  @click="openPricingDialog(p)"
                />
                <q-btn
                  flat
                  round
                  icon="delete"
                  size="sm"
                  color="negative"
                  @click="deletePricing(p.id)"
                />
              </div>
            </q-item-section>
          </q-item>
        </q-list>
      </q-tab-panel>

      <!-- ОТЗЫВЫ -->
      <q-tab-panel name="reviews">
        <q-btn
          label="Добавить"
          icon="add"
          color="primary"
          class="q-mb-md"
          @click="openReviewDialog(null)"
        />
        <q-list bordered separator>
          <q-item v-for="r in reviews" :key="r.id">
            <q-item-section>
              <q-item-label>{{ r.author_name }}</q-item-label>
              <q-item-label caption>
                {{ r.text.slice(0, 100) }}…
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="row gap-xs">
                <q-btn
                  flat
                  round
                  icon="edit"
                  size="sm"
                  @click="openReviewDialog(r)"
                />
                <q-btn
                  flat
                  round
                  icon="delete"
                  size="sm"
                  color="negative"
                  @click="deleteReview(r.id)"
                />
              </div>
            </q-item-section>
          </q-item>
        </q-list>
      </q-tab-panel>

      <!-- ПОРТФОЛИО -->
      <q-tab-panel name="portfolio">
        <q-btn
          label="Добавить фото"
          icon="add_photo_alternate"
          color="primary"
          class="q-mb-md"
          @click="openPortfolioDialog(null)"
        />
        <div class="portfolio-grid">
          <div v-for="img in portfolio" :key="img.id" class="portfolio-item">
            <img :src="img.url" :alt="img.alt">
            <div class="portfolio-item__actions">
              <q-btn
                flat
                round
                icon="edit"
                size="sm"
                dark
                @click="openPortfolioDialog(img)"
              />
              <q-btn
                flat
                round
                icon="delete"
                size="sm"
                dark
                color="negative"
                @click="deletePortfolio(img.id)"
              />
            </div>
          </div>
        </div>
      </q-tab-panel>
    </q-tab-panels>

    <!-- Диалог КОМАНДА -->
    <q-dialog v-model="dialogs.team">
      <q-card style="min-width:360px">
        <q-card-section class="text-h6">
          {{ form.team.id ? 'Редактировать' : 'Добавить' }} участника
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-input v-model="form.team.name" label="Имя" filled dense />
          <q-input v-model="form.team.position" label="Должность" filled dense />
          <q-input v-model="form.team.role_label" label="Роль" filled dense />
          <q-input
            v-model="form.team.description"
            label="Описание"
            filled
            dense
            type="textarea"
            rows="4"
          />
          <q-input v-model="form.team.photo_url" label="URL фото" filled dense />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" />
          <q-btn label="Сохранить" color="primary" @click="saveTeam" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог СТАТИСТИКА -->
    <q-dialog v-model="dialogs.stat">
      <q-card style="min-width:320px">
        <q-card-section class="text-h6">
          {{ form.stat.id ? 'Редактировать' : 'Добавить' }} показатель
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-input v-model="form.stat.value" label="Значение (напр. 1000+)" filled dense />
          <q-input v-model="form.stat.label" label="Подпись" filled dense />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" />
          <q-btn label="Сохранить" color="primary" @click="saveStat" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог УСЛУГА -->
    <q-dialog v-model="dialogs.service">
      <q-card style="min-width:360px">
        <q-card-section class="text-h6">
          {{ form.service.id ? 'Редактировать' : 'Добавить' }} услугу
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-input v-model="form.service.title" label="Название" filled dense />
          <q-input
            v-model="form.service.description"
            label="Описание"
            filled
            dense
            type="textarea"
            rows="3"
          />
          <q-select
            v-model="form.service.icon"
            label="Иконка"
            filled
            dense
            :options="iconOptions"
            emit-value
            map-options
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" />
          <q-btn label="Сохранить" color="primary" @click="saveService" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог ТАРИФ -->
    <q-dialog v-model="dialogs.pricing">
      <q-card style="min-width:400px; max-width:95vw">
        <q-card-section class="text-h6">
          {{ form.pricing.id ? 'Редактировать' : 'Добавить' }} тариф
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-input v-model="form.pricing.title" label="Название тарифа" filled dense />
          <q-input
            v-model="form.pricing.whatsapp_text"
            label="Текст WhatsApp"
            filled
            dense
            type="textarea"
            rows="2"
          />
          <q-toggle v-model="form.pricing.is_featured" label="Выделенный (цветной)" />
          <div class="text-subtitle2 q-mt-md">
            Пункты тарифа
          </div>
          <div v-for="(item, i) in form.pricing.items" :key="i" class="row items-center gap-xs q-mb-xs">
            <q-input
              v-model="form.pricing.items[i].text"
              dense
              filled
              class="col"
              :label="`Пункт ${i+1}`"
            />
            <q-btn
              flat
              round
              icon="delete"
              size="sm"
              color="negative"
              @click="form.pricing.items.splice(i,1)"
            />
          </div>
          <q-btn
            flat
            label="+ Добавить пункт"
            color="primary"
            size="sm"
            @click="form.pricing.items.push({text:'',sort_order:form.pricing.items.length})"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" />
          <q-btn label="Сохранить" color="primary" @click="savePricing" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог ОТЗЫВ -->
    <q-dialog v-model="dialogs.review">
      <q-card style="min-width:360px">
        <q-card-section class="text-h6">
          {{ form.review.id ? 'Редактировать' : 'Добавить' }} отзыв
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-input v-model="form.review.author_name" label="Имя автора" filled dense />
          <q-input
            v-model="form.review.text"
            label="Текст отзыва"
            filled
            dense
            type="textarea"
            rows="5"
          />
          <q-toggle v-model="form.review.is_active" label="Активный" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" />
          <q-btn label="Сохранить" color="primary" @click="saveReview" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог ПОРТФОЛИО -->
    <q-dialog v-model="dialogs.portfolio">
      <q-card style="min-width:360px">
        <q-card-section class="text-h6">
          {{ form.portfolio.id ? 'Редактировать' : 'Добавить' }} фото
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-input v-model="form.portfolio.url" label="URL изображения" filled dense />
          <q-input v-model="form.portfolio.alt" label="Alt-текст (описание)" filled dense />
          <img v-if="form.portfolio.url" :src="form.portfolio.url" class="q-mt-sm" style="max-width:100%;border-radius:8px">
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" />
          <q-btn label="Сохранить" color="primary" @click="savePortfolio" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'src/services/api'

const $q = useQuasar()
const tab = ref('settings')
const loading = ref(false)

const settings  = ref([])
const team      = ref([])
const stats     = ref([])
const services  = ref([])
const pricing   = ref([])
const reviews   = ref([])
const portfolio = ref([])

const dialogs = reactive({ team: false, stat: false, service: false, pricing: false, review: false, portfolio: false })

const form = reactive({
  team:      { id: null, name: '', position: '', role_label: '', description: '', photo_url: '' },
  stat:      { id: null, value: '', label: '' },
  service:   { id: null, title: '', description: '', icon: 'design' },
  pricing:   { id: null, title: '', is_featured: false, whatsapp_text: '', items: [] },
  review:    { id: null, author_name: '', text: '', is_active: true },
  portfolio: { id: null, url: '', alt: '' },
})

const iconOptions = [
  { label: 'Консультации', value: 'consultation' },
  { label: 'Дизайн',       value: 'design' },
  { label: 'Надзор',       value: 'supervision' },
  { label: 'Комплектация', value: 'equipment' },
  { label: 'Ремонт',       value: 'repair' },
]

async function load() {
  loading.value = true
  try {
    const [s, t, st, sv, p, r, pf] = await Promise.all([
      api.get('/api/site/admin/settings').then(r => r.data),
      api.get('/api/site/admin/team').then(r => r.data),
      api.get('/api/site/admin/stats').then(r => r.data),
      api.get('/api/site/admin/services').then(r => r.data),
      api.get('/api/site/admin/pricing').then(r => r.data),
      api.get('/api/site/admin/reviews').then(r => r.data),
      api.get('/api/site/admin/portfolio').then(r => r.data),
    ])
    settings.value  = s
    team.value      = t
    stats.value     = st
    services.value  = sv
    pricing.value   = p
    reviews.value   = r
    portfolio.value = pf
  } catch(e) {
    $q.notify({ type: 'negative', message: 'Ошибка загрузки данных сайта' })
  } finally {
    loading.value = false
  }
}

async function saveSetting(s) {
  try {
    await api.put(`/api/site/admin/settings/${s.key}`, { value: s.value })
    $q.notify({ type: 'positive', message: 'Сохранено', timeout: 1200 })
  } catch { $q.notify({ type: 'negative', message: 'Ошибка сохранения' }) }
}

// ── Команда ────────────────────────────────────────────────
function openTeamDialog(m) {
  Object.assign(form.team, m ? { ...m } : { id: null, name: '', position: '', role_label: '', description: '', photo_url: '' })
  dialogs.team = true
}
async function saveTeam() {
  try {
    if (form.team.id) await api.put(`/api/site/admin/team/${form.team.id}`, form.team)
    else              await api.post('/api/site/admin/team', form.team)
    dialogs.team = false; await load()
    $q.notify({ type: 'positive', message: 'Сохранено' })
  } catch { $q.notify({ type: 'negative', message: 'Ошибка' }) }
}
async function deleteTeam(id) {
  await api.delete(`/api/site/admin/team/${id}`); await load()
}

// ── Статистика ─────────────────────────────────────────────
function openStatDialog(s) {
  Object.assign(form.stat, s ? { ...s } : { id: null, value: '', label: '' })
  dialogs.stat = true
}
async function saveStat() {
  try {
    if (form.stat.id) await api.put(`/api/site/admin/stats/${form.stat.id}`, form.stat)
    else              await api.post('/api/site/admin/stats', form.stat)
    dialogs.stat = false; await load()
    $q.notify({ type: 'positive', message: 'Сохранено' })
  } catch { $q.notify({ type: 'negative', message: 'Ошибка' }) }
}
async function deleteStat(id) { await api.delete(`/api/site/admin/stats/${id}`); await load() }

// ── Услуги ─────────────────────────────────────────────────
function openServiceDialog(s) {
  Object.assign(form.service, s ? { ...s } : { id: null, title: '', description: '', icon: 'design' })
  dialogs.service = true
}
async function saveService() {
  try {
    if (form.service.id) await api.put(`/api/site/admin/services/${form.service.id}`, form.service)
    else                 await api.post('/api/site/admin/services', form.service)
    dialogs.service = false; await load()
    $q.notify({ type: 'positive', message: 'Сохранено' })
  } catch { $q.notify({ type: 'negative', message: 'Ошибка' }) }
}
async function deleteService(id) { await api.delete(`/api/site/admin/services/${id}`); await load() }

// ── Тарифы ─────────────────────────────────────────────────
function openPricingDialog(p) {
  Object.assign(form.pricing, p
    ? { ...p, items: p.items.map(i => ({ ...i })) }
    : { id: null, title: '', is_featured: false, whatsapp_text: '', items: [] })
  dialogs.pricing = true
}
async function savePricing() {
  try {
    if (form.pricing.id) await api.put(`/api/site/admin/pricing/${form.pricing.id}`, form.pricing)
    else                 await api.post('/api/site/admin/pricing', form.pricing)
    dialogs.pricing = false; await load()
    $q.notify({ type: 'positive', message: 'Сохранено' })
  } catch { $q.notify({ type: 'negative', message: 'Ошибка' }) }
}
async function deletePricing(id) { await api.delete(`/api/site/admin/pricing/${id}`); await load() }

// ── Отзывы ─────────────────────────────────────────────────
function openReviewDialog(r) {
  Object.assign(form.review, r ? { ...r } : { id: null, author_name: '', text: '', is_active: true })
  dialogs.review = true
}
async function saveReview() {
  try {
    if (form.review.id) await api.put(`/api/site/admin/reviews/${form.review.id}`, form.review)
    else                await api.post('/api/site/admin/reviews', form.review)
    dialogs.review = false; await load()
    $q.notify({ type: 'positive', message: 'Сохранено' })
  } catch { $q.notify({ type: 'negative', message: 'Ошибка' }) }
}
async function deleteReview(id) { await api.delete(`/api/site/admin/reviews/${id}`); await load() }

// ── Портфолио ──────────────────────────────────────────────
function openPortfolioDialog(img) {
  Object.assign(form.portfolio, img ? { ...img } : { id: null, url: '', alt: '' })
  dialogs.portfolio = true
}
async function savePortfolio() {
  try {
    if (form.portfolio.id) await api.put(`/api/site/admin/portfolio/${form.portfolio.id}`, form.portfolio)
    else                   await api.post('/api/site/admin/portfolio', form.portfolio)
    dialogs.portfolio = false; await load()
    $q.notify({ type: 'positive', message: 'Сохранено' })
  } catch { $q.notify({ type: 'negative', message: 'Ошибка' }) }
}
async function deletePortfolio(id) { await api.delete(`/api/site/admin/portfolio/${id}`); await load() }

onMounted(load)
</script>

<style scoped>
.page-header { border-bottom: 1px solid rgba(0,0,0,0.08); padding-bottom: 12px; }
.portfolio-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; }
.portfolio-item { position: relative; border-radius: 8px; overflow: hidden; aspect-ratio: 4/3; }
.portfolio-item img { width: 100%; height: 100%; object-fit: cover; }
.portfolio-item__actions { position: absolute; top: 4px; right: 4px; display: flex; gap: 4px; background: rgba(0,0,0,0.5); border-radius: 6px; padding: 2px; }
</style>
