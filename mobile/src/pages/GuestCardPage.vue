<template>
  <q-page class="guest-page">
    <div class="guest-wrap">
      <div v-if="loading" class="text-center q-pa-xl">
        <q-spinner size="40px" color="primary" />
      </div>

      <q-card v-else-if="!data" class="is-card q-pa-lg text-center">
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
            unelevated
            flat
            dense
            no-caps
            label="Войти"
            :to="loginLink"
            class="guest-btn"
          />
        </div>

        <!-- Шапка -->
        <q-card class="is-card q-mb-md">
          <q-card-section style="background: var(--fc-bg-info); border-radius: 8px 8px 0 0">
            <div class="text-subtitle1 text-weight-bold" style="color: var(--fc-text)">
              {{ data.contract_number }}
            </div>
            <a
              v-if="data.address"
              :href="'https://yandex.ru/maps/?text=' + encodeURIComponent(data.address)"
              target="_blank"
              rel="noopener"
              class="guest-address"
            >
              <q-icon name="location_on" size="14px" color="red" class="q-mr-xs" />{{ data.address }}
            </a>
            <div class="text-caption q-mt-xs" style="color: var(--fc-text-light)">
              {{ [data.project_type, data.project_subtype, data.area ? `${data.area} м²` : '', data.city].filter(Boolean).join(' | ') }}
            </div>
            <div v-if="data.column_name" class="guest-stage">
              {{ data.column_name }}
            </div>
          </q-card-section>

          <q-card-section v-if="m" class="q-pa-sm">
            <div class="guest-row">
              <span>Норма по договору</span><b>{{ m.norm_days }} дн.</b>
            </div>
            <div v-if="m.deadline" class="guest-row">
              <span>Дедлайн</span><b>{{ fmtDate(m.deadline) }}</b>
            </div>
            <div v-if="m.closure_date" class="guest-row" style="color: #27AE60">
              <span>Закрыт</span><b>{{ fmtDate(m.closure_date) }}</b>
            </div>
            <div v-else-if="m.deadline" class="guest-row" style="color: #F39C12">
              <span>Статус</span><b>В работе</b>
            </div>
            <div v-if="m.fact_days > 0" class="guest-row">
              <span>Факт по договору</span><b>{{ m.fact_days }} дн.</b>
            </div>
            <div v-if="m.overdue_days > 0" class="guest-row" style="color: #E53935">
              <span>Просрочка</span><b>{{ m.overdue_days }} р.д.</b>
            </div>
          </q-card-section>
        </q-card>

        <!-- Команда -->
        <q-card v-if="data.team?.length" class="is-card q-mb-md">
          <q-card-section class="q-pb-xs">
            <div class="guest-title">
              Команда
            </div>
          </q-card-section>
          <q-list dense separator>
            <q-item v-for="(t, i) in data.team" :key="i">
              <q-item-section>
                <q-item-label style="color: var(--fc-text)">
                  {{ t.name }}
                </q-item-label>
                <q-item-label caption style="color: var(--fc-text-light)">
                  {{ t.role }}<template v-if="t.deadline">
                    · срок {{ fmtDate(t.deadline) }}
                  </template>
                </q-item-label>
              </q-item-section>
              <q-item-section v-if="t.completed" side>
                <q-icon name="check_circle" color="positive" size="18px" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>

        <!-- Файлы -->
        <q-card v-if="data.files?.length" class="is-card q-mb-md">
          <q-card-section class="q-pb-xs">
            <div class="guest-title">
              Файлы проекта
            </div>
          </q-card-section>
          <div v-for="g in data.files" :key="g.stage" class="q-px-md q-pb-sm">
            <div class="row items-center q-mb-xs" style="gap: 8px">
              <div class="col text-weight-medium" style="font-size: 13px; color: var(--fc-text)">
                {{ g.title }}
              </div>
              <q-btn
                v-if="isHttp(g.folder_link)"
                flat
                dense
                no-caps
                size="sm"
                icon="folder_open"
                label="Папка"
                :href="g.folder_link"
                target="_blank"
                rel="noopener"
              />
            </div>
            <a
              v-for="(f, i) in g.files.filter(x => isHttp(x.link))"
              :key="i"
              :href="f.link"
              target="_blank"
              rel="noopener"
              class="guest-file"
            >
              <q-icon :name="fileIcon(f.name)" size="16px" class="q-mr-xs" />
              <span class="ellipsis">{{ f.name }}</span>
              <span v-if="f.variation > 1" class="q-ml-xs" style="color: var(--fc-text-muted); white-space: nowrap; flex-shrink: 0">(вар. {{ f.variation }})</span>
            </a>
          </div>
        </q-card>

        <!-- Таблица сроков -->
        <q-card v-if="data.timeline?.length" class="is-card q-mb-md">
          <q-card-section class="q-pb-xs">
            <div class="guest-title">
              Таблица сроков
            </div>
          </q-card-section>
          <q-list dense separator>
            <template v-for="(r, i) in data.timeline" :key="i">
              <q-item v-if="r.kind !== 'row'" :class="r.kind === 'group' ? 'guest-tl-group' : 'guest-tl-sub'">
                <q-item-section>
                  <q-item-label>{{ r.stage }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item v-else :class="{ 'guest-tl-skipped': r.skipped }">
                <q-item-section avatar style="min-width: 28px">
                  <q-icon :name="r.skipped ? 'block' : (r.date ? 'check_circle' : 'radio_button_unchecked')" :color="r.skipped ? 'grey-4' : (r.date ? 'positive' : 'grey-5')" size="16px" />
                </q-item-section>
                <q-item-section>
                  <q-item-label style="font-size: 12px; color: var(--fc-text)">
                    {{ r.stage }}
                  </q-item-label>
                  <q-item-label caption style="color: var(--fc-text-light)">
                    <span v-if="r.norm">Норма: {{ r.norm }} дн.</span>
                    <span v-if="r.fact"> | Факт: {{ r.fact }} дн.</span>
                    <span v-if="r.role"> | {{ r.role }}</span>
                    <span v-if="r.out_of_scope" style="color: #e74c3c; font-style: italic"> | вне объёма</span>
                  </q-item-label>
                </q-item-section>
                <q-item-section v-if="r.date" side>
                  <span class="text-caption" style="color: #27AE60">{{ fmtDate(r.date) }}</span>
                </q-item-section>
              </q-item>
            </template>
          </q-list>
        </q-card>
      </template>
    </div>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { publicCardApi } from 'src/services/api'

const route = useRoute()
const loading = ref(true)
const data = ref(null)

const m = computed(() => data.value?.metrics || null)
const loginLink = computed(() => (data.value ? `/login?redirect=${encodeURIComponent(`/crm/${data.value.card_id}`)}` : '/login'))

const isHttp = (link) => typeof link === 'string' && /^https?:\/\//i.test(link)
const fmtDate = (d) => (d ? new Date(d).toLocaleDateString('ru-RU') : '')

function fileIcon(name) {
  const n = (name || '').toLowerCase()
  if (n.endsWith('.pdf')) return 'picture_as_pdf'
  if (/\.(jpe?g|png|gif|webp|heic|heif|bmp)$/.test(n)) return 'image'
  if (/\.(mp4|mov|avi|mkv|webm)$/.test(n)) return 'videocam'
  if (/\.(dwg|dxf)$/.test(n)) return 'architecture'
  return 'description'
}

onMounted(async () => {
  try {
    const { data: d } = await publicCardApi.get(route.params.token)
    data.value = d
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
  min-height: 100vh;
}
.guest-wrap {
  max-width: 720px;
  margin: 0 auto;
  padding: 12px;
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
.guest-btn {
  height: 28px;
  padding: 0 14px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: var(--fc-bg-card, #fff);
  color: var(--fc-text);
  font-size: 12px;
  white-space: nowrap;
}
.guest-stage {
  display: inline-block;
  margin-top: 8px;
  padding: 2px 8px;
  border: 1px solid var(--fc-border, #d9d9d9);
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--fc-text);
  background: var(--fc-bg-card, #fff);
}
.guest-address {
  display: inline-flex;
  align-items: center;
  margin-top: 4px;
  color: var(--fc-text);
  text-decoration: none;
  font-size: 14px;
}
.guest-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--fc-text);
}
.guest-row {
  display: flex;
  justify-content: space-between;
  padding: 3px 8px;
  font-size: 13px;
  color: var(--fc-text-medium);
}
.guest-file {
  display: flex;
  align-items: center;
  min-width: 0;
  padding: 5px 0;
  font-size: 13px;
  color: var(--fc-link, #1976d2);
  text-decoration: none;
}
.guest-tl-group {
  background: var(--fc-tab-inactive);
  font-weight: bold;
  font-size: 12px;
}
.guest-tl-sub {
  background: var(--fc-bg-alt);
  font-weight: 600;
  font-size: 12px;
}
.guest-tl-skipped {
  opacity: 0.6;
}
</style>
