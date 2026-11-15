<template>
  <q-page padding class="guest-page">
    <div v-if="loading" class="text-center q-pa-xl">
      <q-spinner size="40px" color="grey-7" />
    </div>

    <q-card v-else-if="!data" class="is-card q-pa-lg text-center guest-empty">
      <q-icon name="link_off" size="40px" color="grey-5" class="q-mb-sm" />
      <div class="text-subtitle1 text-weight-bold q-mb-xs" style="color: var(--fc-text)">
        Ссылка недействительна
      </div>
      <div class="text-caption q-mb-md" style="color: var(--fc-text-muted)">
        Попросите менеджера прислать актуальную ссылку на заказ или войдите в CRM.
      </div>
      <q-btn
        flat
        no-caps
        class="guest-btn"
        label="Войти в CRM"
        to="/login"
      />
    </q-card>

    <template v-else>
      <div class="guest-banner q-mb-md">
        <q-icon name="visibility" size="18px" />
        <span class="col">Просмотр без входа. Чтобы работать с карточкой — войдите.</span>
        <q-btn
          flat
          dense
          no-caps
          label="Войти"
          :to="loginLink"
          class="guest-btn"
        />
      </div>

      <!-- Шапка — как в карточке CRM -->
      <q-card class="is-card q-mb-md">
        <q-card-section style="background: var(--fc-bg-info); border-radius: 8px 8px 0 0">
          <div class="row items-start justify-between q-mb-xs">
            <div style="flex: 1; min-width: 0">
              <div class="text-subtitle1 text-weight-bold" style="color: var(--fc-text)">
                {{ data.contract_number }}
              </div>
              <div class="text-body2 q-mt-xs">
                <a
                  v-if="data.address"
                  :href="'https://yandex.ru/maps/?text=' + encodeURIComponent(data.address)"
                  target="_blank"
                  rel="noopener"
                  style="color: var(--fc-text); text-decoration: none"
                >
                  <q-icon name="location_on" size="14px" color="red" class="q-mr-xs" />{{ data.address }}
                </a>
              </div>
            </div>
            <div class="column items-end q-ml-sm" style="flex-shrink: 0; gap: 4px">
              <span class="guest-pill" :style="{ background: stageColor(data.column_name) }">{{ data.column_name }}</span>
              <span v-if="data.agent_type" class="guest-pill" :style="{ background: data.agent_color || '#95A5A6' }">{{ data.agent_type }}</span>
            </div>
          </div>
          <div class="text-caption q-mt-xs" style="color: var(--fc-text-light)">
            {{ [data.project_type, data.project_subtype, data.area ? `${data.area} м²` : '', data.city].filter(Boolean).join(' | ') }}
          </div>
          <div v-if="tags.length" class="row q-mt-xs" style="gap: 4px">
            <span v-for="(tag, i) in tags" :key="i" class="guest-tag" :style="{ background: tag.color }">{{ tag.text }}</span>
          </div>
        </q-card-section>
      </q-card>

      <div class="guest-grid">
        <!-- Информация -->
        <q-card class="is-card q-mb-md">
          <q-card-section class="q-pb-none">
            <div class="guest-title">
              Информация
            </div>
          </q-card-section>
          <q-card-section>
            <div class="row">
              <div class="col-6" style="padding-right: 12px; border-right: 1px solid var(--fc-border-light)">
                <div class="guest-field">
                  <div>Договор</div><b>{{ data.contract_number || '-' }}</b>
                </div>
                <div class="guest-field">
                  <div>Тип проекта</div><b>{{ data.project_type || '-' }}</b>
                </div>
                <div v-if="data.project_subtype" class="guest-field">
                  <div>Подтип проекта</div><b>{{ data.project_subtype }}</b>
                </div>
              </div>
              <div class="col-6" style="padding-left: 12px">
                <div class="guest-field">
                  <div>Срок договора</div><b>{{ data.contract_period ? `${data.contract_period} раб.дн.` : '-' }}</b>
                </div>
                <div class="guest-field">
                  <div>Дата начала</div><b>{{ fmtDate(m?.start_date) || '-' }}</b>
                </div>
                <div class="guest-field">
                  <div>Дедлайн проекта</div>
                  <b :style="{ color: m?.overdue_days > 0 ? '#E53935' : 'var(--fc-text)' }">{{ fmtDate(m?.deadline) || '-' }}</b>
                </div>
                <div v-if="m?.closure_date" class="guest-field">
                  <div>Закрыт</div><b style="color: #27AE60">{{ fmtDate(m.closure_date) }}</b>
                </div>
                <div v-if="m?.overdue_days > 0" class="guest-field">
                  <div>Просрочка</div><b style="color: #E53935">{{ m.overdue_days }} р.д.</b>
                </div>
              </div>
            </div>
          </q-card-section>
        </q-card>

        <!-- Команда -->
        <q-card v-if="data.team?.length" class="is-card q-mb-md">
          <q-card-section class="q-pb-xs">
            <div class="guest-title">
              Команда проекта
            </div>
          </q-card-section>
          <q-list dense separator>
            <q-item v-for="(t, i) in data.team" :key="i">
              <q-item-section avatar style="min-width: 36px">
                <div class="guest-avatar">
                  {{ initials(t.name) }}
                </div>
              </q-item-section>
              <q-item-section>
                <q-item-label style="font-size: 13px; color: var(--fc-text)">
                  {{ t.name }}
                </q-item-label>
                <q-item-label caption style="color: var(--fc-text-light)">
                  {{ t.role }}
                </q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
      </div>

      <!-- Данные — блоки как во вкладке «Данные» карточки -->
      <div class="guest-grid">
        <q-card class="is-card q-mb-md">
          <q-card-section class="q-pb-xs row items-center justify-between">
            <div class="guest-title">
              Техническое задание
            </div>
            <q-btn
              v-if="data.folders?.tech_task"
              flat
              dense
              no-caps
              size="sm"
              icon="open_in_new"
              class="guest-btn"
              label="Открыть в ЯД"
              :href="data.folders.tech_task"
              target="_blank"
              rel="noopener"
            />
          </q-card-section>
          <q-card-section class="q-pt-xs">
            <div class="text-caption" style="color: var(--fc-text-light)">
              Дата анкеты: <span style="color: var(--fc-text)">{{ fmtDate(data.tech_task_date) || 'Не установлена' }}</span>
            </div>
            <div v-if="data.survey" class="row items-center q-mt-sm" style="gap: 8px">
              <span class="text-caption" style="color: var(--fc-text-light)">Анкета ТЗ</span>
              <q-btn
                flat
                dense
                no-caps
                size="sm"
                icon="visibility"
                class="guest-btn"
                label="Просмотр анкеты"
                @click="surveyOpen = true"
              />
            </div>
            <GuestFileList :files="filesOf('tech_task').concat(filesOf('questionnaire'))" class="q-mt-sm" />
          </q-card-section>
        </q-card>

        <q-card class="is-card q-mb-md">
          <q-card-section class="q-pb-xs">
            <div class="guest-title">
              Замер
            </div>
          </q-card-section>
          <q-card-section class="q-pt-xs">
            <a
              v-if="data.folders?.measurement"
              :href="data.folders.measurement"
              target="_blank"
              rel="noopener"
              class="guest-link"
            >Открыть папку с замером</a>
            <div v-else class="text-caption" style="color: var(--fc-text-disabled)">
              Не загружен
            </div>
            <div class="text-caption q-mt-xs" style="color: var(--fc-text-light)">
              Дата: {{ fmtDate(data.measurement_date) || 'Не установлена' }}
            </div>
          </q-card-section>
        </q-card>

        <q-card class="is-card q-mb-md">
          <q-card-section class="q-pb-xs">
            <div class="guest-title">
              Фотофиксация
            </div>
          </q-card-section>
          <q-card-section class="q-pt-xs">
            <a
              v-if="data.folders?.photo_documentation"
              :href="data.folders.photo_documentation"
              target="_blank"
              rel="noopener"
              class="guest-link"
            >Открыть папку с фотофиксацией</a>
            <div v-else class="text-caption" style="color: var(--fc-text-disabled)">
              Не загружена
            </div>
          </q-card-section>
        </q-card>

        <q-card class="is-card q-mb-md">
          <q-card-section class="q-pb-xs">
            <div class="guest-title">
              {{ data.project_type === 'Шаблонный' ? 'Шаблоны' : 'Референсы' }}
            </div>
          </q-card-section>
          <q-card-section class="q-pt-xs">
            <a
              v-if="data.folders?.references"
              :href="data.folders.references"
              target="_blank"
              rel="noopener"
              class="guest-link"
            >Открыть папку</a>
            <div v-else class="text-caption" style="color: var(--fc-text-disabled)">
              Не загружены
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Стадии проекта с вариациями -->
      <q-card v-for="stage in stages" :key="stage.code" class="is-card q-mb-md">
        <q-card-section class="q-pb-xs">
          <div class="guest-title">
            {{ stage.label }}
          </div>
        </q-card-section>
        <div v-for="sub in (stage.substages || [stage])" :key="sub.code" :style="stage.substages ? 'border-top: 1px solid var(--fc-tab-hover); padding: 8px 16px 4px' : 'padding: 0 16px 8px'">
          <div v-if="stage.substages" class="text-caption text-weight-bold q-mb-xs" style="color: var(--fc-text-medium)">
            {{ sub.label }}
          </div>
          <q-tabs
            v-if="variations(sub.code).length > 1"
            v-model="activeVariation[sub.code]"
            dense
            no-caps
            align="left"
            active-color="dark"
            indicator-color="accent"
            style="font-size: 11px"
          >
            <q-tab v-for="v in variations(sub.code)" :key="v" :name="v" :label="`Вариация ${v}`" />
          </q-tabs>
          <GuestFileList :files="filesOf(sub.code, activeVariation[sub.code] || 1)" empty-text="Нет файлов" />
        </div>
      </q-card>

      <q-dialog v-model="surveyOpen" maximized>
        <q-card style="display: flex; flex-direction: column; overflow: hidden">
          <q-bar class="guest-dialog-bar">
            <span style="font-weight: 600">Анкета ТЗ</span>
            <q-space />
            <q-btn
              dense
              flat
              icon="close"
              aria-label="Закрыть"
              @click="surveyOpen = false"
            />
          </q-bar>
          <div v-if="data.survey" style="overflow-y: auto; flex: 1">
            <SurveyReadonlyView
              :template-data="data.survey.template_data"
              :answers="data.survey.answers"
              :hide-personal-data="true"
              :contract-number="data.survey.contract_number"
              :project-type="data.survey.project_type"
              :agent-logo-url="data.survey.agent_logo_url || ''"
            />
          </div>
        </q-card>
      </q-dialog>
    </template>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, h } from 'vue'
import { useRoute } from 'vue-router'
import { QBtn, QIcon } from 'quasar'
import { publicCardApi } from 'src/services/api'
import SurveyReadonlyView from 'src/components/survey/SurveyReadonlyView.vue'

const route = useRoute()
const loading = ref(true)
const data = ref(null)
const surveyOpen = ref(false)
const activeVariation = ref({})

const m = computed(() => data.value?.metrics || null)
const loginLink = computed(() => (data.value ? `/login?redirect=${encodeURIComponent(`/crm/${data.value.card_id}`)}` : '/login'))

const tags = computed(() => {
  const raw = data.value?.tags
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed)) return parsed.map(t => ({ text: String(t.text || ''), color: String(t.color || '#FF6B6B') }))
  } catch { /* старый формат — одна строка */ }
  return [{ text: String(raw), color: '#FF6B6B' }]
})

// Те же стадии, что во вкладке «Данные» карточки CRM
const stages = computed(() => {
  if (data.value?.project_type === 'Шаблонный') {
    return [
      { code: 'stage1', label: 'Стадия 1: Планировочное решение' },
      { code: 'stage3', label: 'Стадия 2: Чертёжная документация' },
      { code: 'stage2_3d', label: 'Стадия 3: 3D визуализация (Доп.)' },
    ]
  }
  return [
    { code: 'stage1', label: 'Стадия 1: Планировочное решение' },
    {
      code: 'stage2_group',
      label: 'Стадия 2: Концепция дизайна',
      substages: [
        { code: 'stage2_concept', label: 'Мудборды' },
        { code: 'stage2_3d', label: 'Визуализация' },
      ],
    },
    { code: 'stage3', label: 'Стадия 3: Чертёжная документация' },
  ]
})

function filesOf(stage, variation = null) {
  return (data.value?.files || []).filter(f => f.stage === stage && (variation === null || f.variation === variation))
}

function variations(stage) {
  const set = new Set(filesOf(stage).map(f => f.variation))
  set.add(1)
  return [...set].sort((a, b) => a - b)
}

function stageColor(col = '') {
  if (col.includes('Новый')) return '#85C1E9'
  if (col.includes('ожидании')) return '#F39C12'
  if (col.includes('Стадия')) return '#E6B800'
  if (col.includes('Выполненный')) return '#27AE60'
  return '#95A5A6'
}

const fmtDate = (d) => (d ? new Date(d).toLocaleDateString('ru-RU') : '')
const initials = (name = '') => name.split(' ').filter(Boolean).slice(0, 2).map(p => p[0]).join('').toUpperCase()

function fileIcon(name = '') {
  const n = name.toLowerCase()
  if (n.endsWith('.pdf')) return 'picture_as_pdf'
  if (/\.(jpe?g|png|gif|webp|heic|heif|bmp)$/.test(n)) return 'image'
  if (/\.(mp4|mov|avi|mkv|webm)$/.test(n)) return 'videocam'
  if (/\.(dwg|dxf)$/.test(n)) return 'architecture'
  return 'description'
}

// Список файлов как в карточке: иконка, имя, кнопка «Открыть»
const GuestFileList = (props) => {
  if (!props.files?.length) {
    return props.emptyText
      ? h('div', { class: 'q-py-sm text-center', style: 'color: var(--fc-text-disabled); font-size: 11px' }, props.emptyText)
      : null
  }
  return h('div', props.files.map(f => h('div', { class: 'guest-file' }, [
    h(QIcon, { name: fileIcon(f.name), size: '18px', color: 'grey-7' }),
    h('a', { href: f.link, target: '_blank', rel: 'noopener', class: 'guest-file-name' }, f.name),
    h(QBtn, { flat: true, dense: true, noCaps: true, size: 'sm', icon: 'open_in_new', label: 'Открыть', class: 'guest-btn', href: f.link, target: '_blank', rel: 'noopener' }),
  ])))
}
GuestFileList.props = ['files', 'emptyText']

onMounted(async () => {
  try {
    const { data: d } = await publicCardApi.get(route.params.token)
    data.value = d
    for (const code of ['stage1', 'stage2_concept', 'stage2_3d', 'stage3']) activeVariation.value[code] = 1
    document.title = `${d.contract_number || 'Заказ'} — ${d.address || ''}`
  } catch {
    data.value = null
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.guest-page {
  background: var(--fc-bg);
}
.guest-empty {
  max-width: 480px;
  margin: 40px auto;
}
.guest-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  background: var(--fc-bg-alt);
  color: var(--fc-text-secondary);
  font-size: 13px;
}
:deep(.guest-btn) {
  height: 28px;
  padding: 0 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: var(--fc-bg-card, #fff);
  color: var(--fc-text);
  font-size: 12px;
  white-space: nowrap;
}
.guest-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #eeeeee;
  color: #424242;
  font-size: 11px;
  font-weight: 600;
}
/* Общая тема красит текст кнопок в тёмный — на тёмной полосе диалога возвращаем белый */
.guest-dialog-bar {
  flex-shrink: 0;
  background: #444;
  color: #fff;
}
.guest-dialog-bar span,
.guest-dialog-bar :deep(.q-btn__content),
.guest-dialog-bar :deep(.q-icon) {
  color: #fff !important;
}
.guest-pill {
  min-width: 100px;
  padding: 5px 8px;
  border-radius: 4px;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  text-align: center;
}
.guest-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 4px;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
}
.guest-title {
  font-weight: 700;
  font-size: 14px;
  color: var(--fc-text);
}
.guest-field {
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--fc-text);
}
.guest-field > div {
  font-size: 12px;
  color: var(--fc-text-muted);
}
.guest-field > b {
  font-weight: 400;
}
.guest-link {
  color: var(--fc-link);
  font-size: 12px;
}
:deep(.guest-file) {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  min-width: 0;
}
:deep(.guest-file-name) {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  color: var(--fc-link);
  text-decoration: none;
}
/* Широкий экран / ландшафт — блоки в две колонки, как вкладка «Данные» карточки */
@media (orientation: landscape) and (min-width: 700px) {
  .guest-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 12px;
  }
  .guest-grid > .is-card {
    margin-bottom: 0 !important;
  }
}
</style>
