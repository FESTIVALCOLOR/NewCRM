<template>
  <q-page padding>
    <!-- Фильтры -->
    <q-card class="is-card q-mb-md">
      <q-card-section class="q-pa-sm">
        <!-- Строка 1: период -->
        <div class="row q-col-gutter-xs q-mb-xs">
          <div class="col">
            <q-select
              v-model="filters.year"
              :options="years"
              label="Год"
              outlined
              dense
              @update:model-value="loadData"
            />
          </div>
          <div class="col">
            <q-select
              v-model="filters.quarter"
              :options="quarters"
              label="Квартал"
              outlined
              dense
              emit-value
              map-options
              @update:model-value="loadData"
            />
          </div>
          <div class="col">
            <q-select
              v-model="filters.month"
              :options="monthOpts"
              label="Месяц"
              outlined
              dense
              emit-value
              map-options
              @update:model-value="loadData"
            />
          </div>
        </div>
        <!-- Строка 2: кнопки действий -->
        <div class="row q-col-gutter-xs">
          <div class="col">
            <button type="button" class="reset-btn filter-action-btn" @click="resetFilters">
              <q-icon name="refresh" size="18px" />
              <span>Сброс</span>
            </button>
          </div>
          <div class="col">
            <button type="button" class="emp-pdf-btn filter-action-btn" :disabled="pdfLoading || loading" @click="exportPDF">
              <q-spinner v-if="pdfLoading" size="14px" />
              <span v-else>PDF</span>
            </button>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Тип проекта -->
    <q-tabs
      v-model="projectTab"
      dense
      active-color="dark"
      indicator-color="accent"
      no-caps
      class="q-mb-md"
      style="color: var(--fc-text-secondary)"
      align="left"
    >
      <q-tab name="all" label="Все" />
      <q-tab name="individual" label="Индивидуальные" />
      <q-tab name="template" label="Шаблонные" />
      <q-tab name="supervision" label="Авт. надзор" />
    </q-tabs>

    <q-pull-to-refresh @refresh="onRefresh">
      <!-- KPI -->
      <div v-if="dashboard" class="row q-col-gutter-xs q-mb-md">
        <div v-for="kpi in dashboardKpi" :key="kpi.label" class="col-4">
          <q-card class="is-card">
            <q-card-section class="q-pa-sm text-center">
              <div class="text-h6 text-weight-bold" style="color: var(--fc-text)">
                {{ kpi.value }}
              </div>
              <div class="text-caption" style="color: var(--fc-text-light); font-size: 10px">
                {{ kpi.label }}
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Роли (вкладки) -->
      <q-tabs
        v-model="roleTab"
        dense
        active-color="dark"
        indicator-color="accent"
        no-caps
        class="q-mb-md"
        style="color: var(--fc-text-secondary)"
        align="left"
      >
        <q-tab v-for="r in roleTabs" :key="r.code" :name="r.code" :label="r.label" />
      </q-tabs>

      <!-- Рейтинг по роли -->
      <q-card v-if="roleRating.length > 0" class="is-card q-mb-md">
        <q-card-section class="q-pb-xs">
          <div class="text-subtitle2 text-weight-bold" style="color: var(--fc-text)">
            Рейтинг эффективности
          </div>
          <div class="row items-center q-mb-sm">
            <div class="text-caption" style="color: var(--fc-text-light)">
              50% KPI · 25% Объём · 25% Пунктуальность{{ roleRating.some(e => e.clientScore !== null) ? ' · ±10% Клиент' : '' }}
            </div>
            <q-btn
              flat
              round
              icon="help_outline"
              size="xs"
              color="grey-5"
              class="q-ml-xs"
              @click.stop="showRatingHelp = true"
            />
          </div>
          <div
            v-for="(emp, idx) in roleRating"
            :key="emp.name"
            class="row items-center q-py-xs"
            style="border-bottom: 1px solid var(--fc-tab-hover); cursor: pointer"
            @click="selectedEmp = emp._emp"
          >
            <div
              class="text-weight-bold q-mr-sm"
              style="width: 22px; text-align: center; font-size: 13px"
              :style="{ color: idx === 0 ? '#F5A623' : idx === roleRating.length - 1 && roleRating.length > 2 ? '#E53935' : 'var(--fc-text-light)' }"
            >
              {{ idx + 1 }}
            </div>
            <div style="flex: 1; min-width: 0">
              <div class="text-weight-medium" style="font-size: 13px; color: var(--fc-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis">
                {{ emp.name.split(' ').slice(0, 2).join(' ') }}
              </div>
              <div class="row q-gutter-xs q-mt-xs" style="flex-wrap: wrap; gap: 2px 6px">
                <div style="font-size: 10px; color: #27AE60">
                  KPI {{ emp.kpi }}%
                </div>
                <div style="font-size: 10px; color: var(--fc-link)">
                  Объём {{ emp.volume }}%
                </div>
                <div style="font-size: 10px" :style="{ color: emp.punctuality >= 80 ? '#27AE60' : emp.punctuality >= 50 ? '#F5A623' : '#E53935' }">
                  Пункт. {{ emp.punctuality }}%
                </div>
                <div v-if="emp.clientScore !== null" style="font-size: 10px; color: #9C27B0">
                  Клиент {{ emp.clientScore }}%
                </div>
              </div>
            </div>
            <div class="q-ml-sm" style="text-align: right; min-width: 48px">
              <div
                class="text-weight-bold"
                style="font-size: 18px"
                :style="{ color: emp.score >= 80 ? '#27AE60' : emp.score >= 50 ? '#F5A623' : '#E53935' }"
              >
                {{ emp.score }}
              </div>
              <div style="font-size: 10px; color: var(--fc-text-disabled)">
                / 100
              </div>
            </div>
            <q-icon name="chevron_right" size="18px" color="grey-4" class="q-ml-xs" />
          </div>
        </q-card-section>
      </q-card>

      <!-- Три графика в одну строку: Нагрузка · KPI · Просрочки -->
      <div v-if="roleEmployees.length > 0" class="row q-col-gutter-xs q-mb-md">
        <div class="col-12 col-sm-4">
          <q-card class="is-card" style="height: 100%">
            <q-card-section class="q-pa-sm">
              <div class="text-caption text-weight-bold q-mb-xs" style="color: var(--fc-text)">
                Нагрузка
              </div>
              <div v-if="roleExecutorLoad.length === 0" class="text-caption text-center q-pt-sm" style="color: var(--fc-text-disabled); font-size: 10px">
                нет данных
              </div>
              <bar-chart
                v-else
                :labels="roleExecutorLoad.map(e => e.name.split(' ').slice(0, 2).join(' '))"
                :datasets="[{ label: 'Стадий', data: roleExecutorLoad.map(e => e.active_stages), color: '#ffd93c' }]"
                horizontal
              />
            </q-card-section>
          </q-card>
        </div>
        <div class="col-12 col-sm-4">
          <q-card class="is-card" style="height: 100%">
            <q-card-section class="q-pa-sm">
              <div class="text-caption text-weight-bold q-mb-xs" style="color: var(--fc-text)">
                KPI %
              </div>
              <bar-chart
                :labels="roleEmployees.map(e => (e.full_name || e.name || '').split(' ').slice(0, 2).join(' '))"
                :datasets="[{ label: 'KPI %', data: roleEmployees.map(e => e.completion_rate || e.kpi || 0), color: '#27AE60' }]"
                horizontal
              />
            </q-card-section>
          </q-card>
        </div>
        <div class="col-12 col-sm-4">
          <q-card class="is-card" style="height: 100%">
            <q-card-section class="q-pa-sm">
              <div class="text-caption text-weight-bold q-mb-xs" style="color: var(--fc-text)">
                Просрочки
              </div>
              <div v-if="roleOverdueChartData.labels.length === 0" class="text-caption text-center q-pt-sm" style="color: #27AE60; font-size: 10px">
                Все в срок
              </div>
              <bar-chart
                v-else
                :labels="roleOverdueChartData.labels"
                :datasets="[{ label: 'Дней', data: roleOverdueChartData.data, color: '#E53935' }]"
                horizontal
              />
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Опросы клиентов — KPI качества -->
      <q-card v-if="surveyStats" class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold" style="color: var(--fc-text)">
            Качество проектов (опросы клиентов)
          </div>
          <div class="text-caption" style="color: var(--fc-text-light)">
            {{ surveyStats.completed }}/{{ surveyStats.total }} завершённых опросов
          </div>
        </q-card-section>
        <q-card-section>
          <div class="row q-col-gutter-sm">
            <div v-for="kpi in surveyKpis" :key="kpi.label" class="col-6 col-sm-4">
              <q-card flat bordered class="q-pa-sm text-center" style="border-radius: 8px">
                <div class="text-caption" style="color: var(--fc-text-light); font-size: 10px">
                  {{ kpi.label }}
                </div>
                <div class="text-weight-bold q-mt-xs" :style="{ color: kpiColor(kpi.value), fontSize: '18px' }">
                  {{ kpi.value != null ? kpi.value.toFixed(1) : '—' }}
                </div>
                <div class="text-caption" style="color: var(--fc-border-card); font-size: 9px">
                  из {{ kpi.scale }}
                </div>
              </q-card>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <div v-if="!dashboard && !loading" class="text-center q-pa-xl" style="color: var(--fc-text-muted)">
        <q-icon name="analytics" size="48px" class="q-mb-sm" />
        <div>Нет данных</div>
      </div>
    </q-pull-to-refresh>

    <!-- Диалог объяснения рейтинга -->
    <q-dialog v-model="showRatingHelp">
      <q-card style="width: 100%; max-width: 520px; border-radius: 16px">
        <q-card-section class="q-pb-none">
          <div class="row items-center justify-between">
            <div class="text-subtitle1 text-weight-bold" style="color: var(--fc-text)">
              Как считается рейтинг
            </div>
            <q-btn flat round icon="close" @click="showRatingHelp = false" />
          </div>
        </q-card-section>
        <q-card-section style="max-height: 70vh; overflow-y: auto">
          <div class="q-mb-md">
            <div class="text-caption q-mb-xs" style="color: var(--fc-text-secondary); font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px">
              Итоговый балл
            </div>
            <div class="q-pa-sm" style="background: var(--fc-bg-hover); border-radius: 8px; font-size: 13px; color: var(--fc-text)">
              Балл = KPI×50% + Объём×25% + Пунктуальность×25%
              <div style="color: var(--fc-text-light); font-size: 12px; margin-top: 2px">
                × коэффициент клиента (0.9–1.0, если есть оценки)
              </div>
            </div>
          </div>

          <div class="q-mb-md">
            <div class="text-caption q-mb-xs" style="color: #27AE60; font-weight: 700">
              KPI выполнения — 50%
            </div>
            <div style="font-size: 13px; color: var(--fc-text)">
              Доля завершённых этапов от всех назначенных за период:
            </div>
            <div class="q-pa-sm q-mt-xs" style="background: var(--fc-bg-hover); border-radius: 8px; font-size: 12px; color: var(--fc-text)">
              KPI = завершено / всего × 100%
            </div>
            <div class="q-mt-xs" style="font-size: 12px; color: var(--fc-text-light)">
              Этапы берутся из StageExecutor (исполнитель) и назначений на карточке (ГАП, СДП, Менеджер). Для надзора — карточки где назначен как ДАН или Менеджер.
            </div>
          </div>

          <div class="q-mb-md">
            <div class="text-caption q-mb-xs" style="color: var(--fc-link); font-weight: 700">
              Объём — 25%
            </div>
            <div style="font-size: 13px; color: var(--fc-text)">
              Сколько этапов завершил сотрудник относительно самого продуктивного в этой роли:
            </div>
            <div class="q-pa-sm q-mt-xs" style="background: var(--fc-bg-hover); border-radius: 8px; font-size: 12px; color: var(--fc-text)">
              Объём = завершено / максимум_в_роли × 100%
            </div>
            <div class="q-mt-xs" style="font-size: 12px; color: var(--fc-text-light)">
              Сравнение идёт только внутри текущей вкладки роли. У лидера роли всегда 100%.
            </div>
          </div>

          <div class="q-mb-md">
            <div class="text-caption q-mb-xs" style="color: #F5A623; font-weight: 700">
              Пунктуальность — 25%
            </div>
            <div style="font-size: 13px; color: var(--fc-text)">
              Штраф за просрочки: чем больше дней просрочки в среднем на этап — тем ниже:
            </div>
            <div class="q-pa-sm q-mt-xs" style="background: var(--fc-bg-hover); border-radius: 8px; font-size: 12px; color: var(--fc-text)">
              Среднее просрочки = сумма дней / кол-во завершённых<br>
              Пунктуальность = max(0, 1 − среднее / 10) × 100%
            </div>
            <div class="q-mt-xs" style="font-size: 12px; color: var(--fc-text-light)">
              При среднем ≥10 дней просрочки на этап → 0%. При 0 днях → 100%. При 5 днях → 50%.
            </div>
          </div>

          <div>
            <div class="text-caption q-mb-xs" style="color: #9C27B0; font-weight: 700">
              Оценка клиента — ±10%
            </div>
            <div style="font-size: 13px; color: var(--fc-text)">
              Модификатор из анкет клиентов по завершённым проектам. Влияет на итоговый балл от −10% до 0%:
            </div>
            <div class="q-pa-sm q-mt-xs" style="background: var(--fc-bg-hover); border-radius: 8px; font-size: 12px; color: var(--fc-text)">
              Коэффициент = 0.9 + 0.1 × средняя_оценка/100
            </div>
            <div class="q-mt-xs" style="font-size: 12px; color: var(--fc-text-light)">
              Оценки NPS (0–10), CSAT, дизайн, дедлайн, коммуникация, ожидания (1–5) — нормализуются к 0–100 и усредняются. Если анкет нет — коэффициент 1.0 (нейтральный).
            </div>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Диалог деталей сотрудника -->
    <q-dialog v-model="empDialog" position="bottom">
      <q-card v-if="selectedEmp" style="width: 100%; max-width: 600px; border-radius: 16px 16px 0 0">
        <q-card-section class="q-pb-none">
          <div class="row items-center q-mb-sm">
            <q-avatar size="48px" color="grey-3" text-color="grey-8" class="q-mr-md">
              {{ selectedEmp.full_name?.[0] || '?' }}
            </q-avatar>
            <div>
              <div class="text-subtitle1 text-weight-bold" style="color: var(--fc-text)">
                {{ selectedEmp.full_name || selectedEmp.name }}
              </div>
              <div class="text-caption" style="color: var(--fc-text-light)">
                {{ selectedEmp.position }}
              </div>
            </div>
            <q-space />
            <q-btn flat round icon="close" @click="selectedEmp = null" />
          </div>
        </q-card-section>
        <q-card-section style="max-height: 75vh; overflow-y: auto">
          <div class="row q-col-gutter-sm">
            <div class="col-6">
              <q-card flat bordered class="q-pa-sm text-center" style="border-radius: 8px">
                <div class="text-caption" style="color: var(--fc-text-light); font-size: 10px">
                  KPI выполнения
                </div>
                <div class="text-h6 text-weight-bold q-mt-xs" :style="{ color: kpiColor((selectedEmp.completion_rate || 0) / 10) }">
                  {{ selectedEmp.completion_rate?.toFixed(0) || '—' }}%
                </div>
              </q-card>
            </div>
            <div class="col-6">
              <q-card flat bordered class="q-pa-sm text-center" style="border-radius: 8px">
                <div class="text-caption" style="color: var(--fc-text-light); font-size: 10px">
                  Этапы
                </div>
                <div class="text-h6 text-weight-bold q-mt-xs" style="color: var(--fc-text)">
                  {{ selectedEmp.completed_stages || 0 }}/{{ selectedEmp.total_stages || 0 }}
                </div>
              </q-card>
            </div>
          </div>
          <q-linear-progress
            v-if="selectedEmp.total_stages > 0"
            :value="(selectedEmp.completed_stages || 0) / selectedEmp.total_stages"
            color="positive"
            class="q-mt-sm"
            rounded
            style="height: 8px"
          />
          <div v-if="empSurveyScores(selectedEmp).length" class="q-mt-sm">
            <div class="row q-gutter-xs">
              <div v-for="sc in empSurveyScores(selectedEmp)" :key="sc.label" class="col">
                <q-card flat bordered class="q-pa-sm text-center" style="border-radius: 8px; min-width: 60px">
                  <div class="text-caption" style="color: var(--fc-text-light); font-size: 10px">
                    {{ sc.label }}
                  </div>
                  <div class="text-weight-bold q-mt-xs" :style="{ color: sc.value != null ? kpiColor(sc.value) : 'var(--fc-border-card)', fontSize: '18px' }">
                    {{ sc.value != null ? sc.value.toFixed(1) : '—' }}
                  </div>
                  <div class="text-caption" style="color: var(--fc-border-card); font-size: 9px">
                    из {{ sc.scale }}
                  </div>
                </q-card>
              </div>
            </div>
          </div>
          <!-- Выезды на объекты (ДАН и Менеджер) -->
          <div v-if="showVisitStats(selectedEmp)" class="q-mt-md">
            <div class="text-caption q-mb-xs" style="color: var(--fc-text-secondary); font-weight: 600; font-size: 11px">
              Выезды на объекты
            </div>
            <div class="row q-gutter-xs">
              <div class="col">
                <q-card flat bordered class="q-pa-sm text-center" style="border-radius: 8px">
                  <div class="text-caption" style="color: var(--fc-text-light); font-size: 10px">
                    На объект
                  </div>
                  <div class="text-weight-bold q-mt-xs" style="font-size: 18px; color: var(--fc-text)">
                    {{ selectedEmp.visits_object ?? 0 }}
                  </div>
                </q-card>
              </div>
              <div class="col">
                <q-card flat bordered class="q-pa-sm text-center" style="border-radius: 8px">
                  <div class="text-caption" style="color: var(--fc-text-light); font-size: 10px">
                    К поставщику
                  </div>
                  <div class="text-weight-bold q-mt-xs" style="font-size: 18px; color: var(--fc-text)">
                    {{ selectedEmp.visits_supplier ?? 0 }}
                  </div>
                </q-card>
              </div>
              <div class="col">
                <q-card flat bordered class="q-pa-sm text-center" style="border-radius: 8px">
                  <div class="text-caption" style="color: var(--fc-text-light); font-size: 10px">
                    Просрочено
                  </div>
                  <div
                    class="text-weight-bold q-mt-xs"
                    :style="{ fontSize: '18px', color: (selectedEmp.visits_overdue ?? 0) > 0 ? '#E74C3C' : '#27AE60' }"
                  >
                    {{ selectedEmp.visits_overdue ?? 0 }}
                  </div>
                </q-card>
              </div>
            </div>
          </div>

          <!-- Просрочки этапов — inline, без второго диалога -->
          <div class="q-mt-md">
            <div class="text-caption q-mb-xs" style="color: var(--fc-text-secondary); font-weight: 600; font-size: 11px">
              Просрочки этапов за период
            </div>
            <template v-if="empFilteredOverdue && empFilteredOverdue.total_overdue_count > 0">
              <!-- Кликабельная строка summary -->
              <div
                class="row items-center justify-between q-pa-sm cursor-pointer"
                style="background: #FFEBEE; border-radius: 8px"
                @click="showOverdueDetail = !showOverdueDetail"
              >
                <div>
                  <div class="text-weight-bold" style="color: #E53935; font-size: 15px">
                    {{ empFilteredOverdue.total_overdue_days }} дн. просрочки
                  </div>
                  <div class="text-caption" style="color: #C07070">
                    {{ empFilteredOverdue.total_overdue_count }} этапов сданы с опозданием
                  </div>
                </div>
                <q-icon :name="showOverdueDetail ? 'expand_less' : 'expand_more'" color="red-3" size="20px" />
              </div>
              <!-- Инлайн разбивка по этапам -->
              <div v-if="showOverdueDetail" class="q-mt-xs">
                <div
                  v-for="(stage, idx) in empFilteredOverdue.stages"
                  :key="idx"
                  class="row items-start justify-between q-pa-xs"
                  :style="{ background: idx % 2 ? '#fff' : 'var(--fc-bg-hover)', borderRadius: '4px', marginBottom: '2px' }"
                >
                  <div style="flex: 1; min-width: 0">
                    <div class="text-weight-medium" style="color: var(--fc-text); font-size: 12px">
                      {{ stage.contract_number }}
                      <span v-if="stage.address" style="color: var(--fc-text-light); font-weight: 400"> · {{ stage.address }}</span>
                    </div>
                    <div style="color: var(--fc-text-secondary); font-size: 11px">
                      {{ stage.stage_name }}
                    </div>
                    <div style="color: var(--fc-text-disabled); font-size: 10px">
                      Факт: {{ stage.actual_date }}
                    </div>
                  </div>
                  <span class="text-weight-bold q-ml-sm" style="color: #E53935; font-size: 13px; flex-shrink: 0">+{{ stage.overdue_days }} дн.</span>
                </div>
              </div>
            </template>
            <div v-else class="text-caption q-pa-sm" style="background: var(--fc-state-success-bg); color: #27AE60; border-radius: 8px">
              Все этапы сданы в срок
            </div>
          </div>

          <!-- Проекты и этапы за период -->
          <div class="q-mt-md">
            <div
              class="row items-center justify-between cursor-pointer q-mb-xs"
              @click="showEmpProjects = !showEmpProjects"
            >
              <div class="text-caption" style="color: var(--fc-text-secondary); font-weight: 600; font-size: 11px">
                Проекты и этапы за период
                <span v-if="empProjects" style="color: var(--fc-text-light); font-weight: 400">
                  ({{ empProjects.total }})
                </span>
              </div>
              <q-icon v-if="!empProjectsLoading" :name="showEmpProjects ? 'expand_less' : 'expand_more'" color="grey-5" size="18px" />
              <q-spinner v-else size="16px" color="grey-5" />
            </div>
            <div v-if="showEmpProjects">
              <div v-if="empProjectsLoading" class="text-center q-py-sm">
                <q-spinner size="24px" color="primary" />
              </div>
              <template v-else-if="empProjects && empProjects.items.length > 0">
                <div
                  v-for="(item, idx) in empProjects.items"
                  :key="idx"
                  class="q-pa-xs q-mb-xs"
                  :style="{ background: idx % 2 === 0 ? 'var(--fc-bg-hover)' : 'transparent', borderRadius: '6px' }"
                >
                  <div class="row items-start justify-between">
                    <div style="flex: 1; min-width: 0">
                      <div class="row items-center q-gutter-xs">
                        <span class="text-weight-medium" style="font-size: 12px; color: var(--fc-text)">
                          {{ item.contract_number }}
                        </span>
                        <q-badge
                          v-if="item.role"
                          :color="item.source === 'supervision' ? 'purple' : 'blue-grey'"
                          text-color="white"
                          style="font-size: 9px; padding: 1px 5px"
                        >
                          {{ item.role }}
                        </q-badge>
                        <span
                          v-if="empProjectOverdueDays(item)"
                          style="font-size: 10px; color: #E53935; font-weight: 600; flex-shrink: 0"
                        >
                          +{{ empProjectOverdueDays(item) }} дн.
                        </span>
                      </div>
                      <div v-if="item.address" style="font-size: 11px; color: var(--fc-text-light); white-space: nowrap; overflow: hidden; text-overflow: ellipsis">
                        {{ item.address }}
                      </div>
                      <div v-if="item.stage_name" style="font-size: 11px; color: var(--fc-text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
                        {{ item.stage_name }}
                      </div>
                    </div>
                    <div class="q-ml-xs" style="flex-shrink: 0">
                      <q-icon
                        :name="item.is_completed ? 'check_circle' : 'schedule'"
                        :color="item.is_completed ? 'positive' : 'warning'"
                        size="18px"
                      />
                    </div>
                  </div>
                </div>
              </template>
              <div v-else class="text-caption q-pa-sm" style="background: var(--fc-bg-hover); border-radius: 8px; color: var(--fc-text-light)">
                Нет проектов за выбранный период
              </div>
            </div>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { statisticsApi, surveyApi, reportsApi } from 'src/services/api'
import BarChart from 'src/components/charts/BarChart.vue'

const currentYear = new Date().getFullYear()
const filters = ref({ year: currentYear, quarter: null, month: null })
const projectTab = ref('all')
const roleTab = ref('sdp')
const dashboard = ref(null)
const executorLoad = ref([])
const roleEmployees = ref([])
const loading = ref(false)
const pdfLoading = ref(false)
const surveyStats = ref(null)
const selectedEmp = ref(null)
const overdueList = ref([])
const showOverdueDetail = ref(false)
const empProjects = ref(null)
const empProjectsLoading = ref(false)
const showEmpProjects = ref(false)
const showRatingHelp = ref(false)
const empDialog = computed({
  get: () => !!selectedEmp.value,
  set: (v) => { if (!v) { selectedEmp.value = null; showOverdueDetail.value = false; empProjects.value = null; showEmpProjects.value = false } },
})

const years = Array.from({ length: 7 }, (_, i) => currentYear - i)
const quarters = [{ label: 'Все', value: null }, { label: 'Q1', value: 1 }, { label: 'Q2', value: 2 }, { label: 'Q3', value: 3 }, { label: 'Q4', value: 4 }]
const monthOpts = [{ label: 'Все', value: null }, ...Array.from({ length: 12 }, (_, i) => ({ label: new Date(2000, i).toLocaleDateString('ru-RU', { month: 'short' }), value: i + 1 }))]

const ROLE_TABS = {
  all: [{ code: 'sdp', label: 'СДП' }, { code: 'gap', label: 'ГАП' }, { code: 'manager', label: 'Менеджер' }, { code: 'senior_manager', label: 'Ст. менеджер' }, { code: 'designer', label: 'Дизайнер' }, { code: 'draftsman', label: 'Чертёжник' }, { code: 'dan', label: 'ДАН' }],
  individual: [{ code: 'sdp', label: 'СДП' }, { code: 'gap', label: 'ГАП' }, { code: 'manager', label: 'Менеджер' }, { code: 'senior_manager', label: 'Ст. менеджер' }, { code: 'designer', label: 'Дизайнер' }, { code: 'draftsman', label: 'Чертёжник' }],
  template: [{ code: 'gap', label: 'ГАП' }, { code: 'manager', label: 'Менеджер' }, { code: 'senior_manager', label: 'Ст. менеджер' }, { code: 'draftsman', label: 'Чертёжник' }, { code: 'designer', label: 'Дизайнер' }],
  supervision: [{ code: 'dan', label: 'ДАН' }, { code: 'manager', label: 'Менеджер' }],
}

const roleTabs = computed(() => ROLE_TABS[projectTab.value] || ROLE_TABS.all)

// Быстрый lookup просрочек по имени сотрудника
const overdueByName = computed(() => {
  const m = {}
  for (const o of overdueList.value) m[o.employee_name] = o
  return m
})

// Просрочки выбранного сотрудника, отфильтрованные по текущей роли (только договора из empProjects)
const empFilteredOverdue = computed(() => {
  if (!selectedEmp.value) return null
  const empName = selectedEmp.value.full_name || selectedEmp.value.name || ''
  const ovd = overdueByName.value[empName]
  if (!ovd || !ovd.stages) return ovd || null
  const items = empProjects.value?.items
  if (items == null) return ovd  // проекты ещё не загружены — возвращаем всё
  const projectContracts = new Set(items.map(p => p.contract_number))
  const filteredStages = ovd.stages.filter(s => projectContracts.has(s.contract_number))
  return {
    ...ovd,
    stages: filteredStages,
    total_overdue_days: filteredStages.reduce((sum, s) => sum + (s.overdue_days || 0), 0),
    total_overdue_count: filteredStages.length,
  }
})

function empProjectOverdueDays(item) {
  if (!selectedEmp.value || !item.contract_number) return null
  const ovd = empFilteredOverdue.value
  if (!ovd || !ovd.stages) return null
  const total = ovd.stages
    .filter(s => s.contract_number === item.contract_number)
    .reduce((sum, s) => sum + (s.overdue_days || 0), 0)
  return total > 0 ? total : null
}

const dashboardKpi = computed(() => {
  const d = dashboard.value || {}
  const emps = roleEmployees.value
  const avgCompletion = emps.length
    ? Math.round(emps.reduce((s, e) => s + (e.completion_rate || 0), 0) / emps.length)
    : null
  const projectCount = projectTab.value === 'supervision'
    ? (d.supervision_cards ?? '—')
    : projectTab.value === 'all'
    ? ((d.active_crm_cards ?? 0) + (d.supervision_cards ?? 0)) || '—'
    : (d.active_crm_cards ?? '—')
  return [
    { label: 'Сотрудников', value: emps.length || '—' },
    { label: 'Выполнение', value: avgCompletion !== null ? `${avgCompletion}%` : '—' },
    { label: 'Проектов', value: projectCount },
  ]
})

// Рейтинг сотрудников по роли: KPI + объём + пунктуальность + оценка клиента
const roleRating = computed(() => {
  const emps = roleEmployees.value
  if (!emps.length) return []
  const maxCompleted = Math.max(1, ...emps.map(e => e.completed_stages || e.completed || 0))
  return emps
    .map(emp => {
      const name = emp.full_name || emp.name || ''
      const kpi = emp.completion_rate || 0
      const completed = emp.completed_stages || emp.completed || 0
      const total = emp.total_stages || emp.total || 0

      // Объём: нормализован внутри роли (0-100)
      const volume = maxCompleted > 0 ? (completed / maxCompleted * 100) : 0

      // Пунктуальность: штраф за просрочки
      const ovd = overdueByName.value[name]
      const overdueDays = ovd ? ovd.total_overdue_days : 0
      const avgOverduePerStage = overdueDays / Math.max(1, completed)
      const punctuality = Math.max(0, 1 - avgOverduePerStage / 10) * 100

      // Оценка клиента: NPS (0-10→0-100), остальные (1-5→0-100)
      const rawScores = []
      if (emp.avg_nps != null) rawScores.push(emp.avg_nps * 10)
      if (emp.avg_csat != null) rawScores.push((emp.avg_csat - 1) / 4 * 100)
      if (emp.avg_design != null) rawScores.push((emp.avg_design - 1) / 4 * 100)
      if (emp.avg_deadline != null) rawScores.push((emp.avg_deadline - 1) / 4 * 100)
      if (emp.avg_communication != null) rawScores.push((emp.avg_communication - 1) / 4 * 100)
      if (emp.avg_expectations != null) rawScores.push((emp.avg_expectations - 1) / 4 * 100)
      const clientScore = rawScores.length > 0
        ? rawScores.reduce((a, b) => a + b, 0) / rawScores.length
        : null

      const base = kpi * 0.50 + volume * 0.25 + punctuality * 0.25
      const modifier = clientScore !== null ? (0.9 + 0.1 * clientScore / 100) : 1
      const score = Math.round(base * modifier)

      return {
        name, position: emp.position,
        kpi: Math.round(kpi), volume: Math.round(volume),
        punctuality: Math.round(punctuality),
        clientScore: clientScore !== null ? Math.round(clientScore) : null,
        score, overdueDays, completed, total, _emp: emp,
      }
    })
    .sort((a, b) => b.score - a.score)
})

// Нагрузка отфильтрованная по сотрудникам текущей роли
const roleExecutorLoad = computed(() => {
  const names = new Set(roleEmployees.value.map(e => e.full_name || e.name || ''))
  return executorLoad.value.filter(e => names.has(e.name))
})

// Данные для графика пунктуальности: сотрудники текущей роли у которых были просрочки
const roleOverdueChartData = computed(() => {
  const emps = roleEmployees.value
  const items = emps
    .map(e => {
      const ovd = overdueByName.value[e.full_name || e.name]
      return { name: (e.full_name || e.name || '').split(' ').slice(0, 2).join(' '), days: ovd ? ovd.total_overdue_days : 0 }
    })
    .filter(x => x.days > 0)
    .sort((a, b) => b.days - a.days)
  return { labels: items.map(x => x.name), data: items.map(x => x.days) }
})

async function loadData() {
  loading.value = true
  const params = { year: filters.value.year }
  if (filters.value.quarter) params.quarter = filters.value.quarter
  if (filters.value.month) params.month = filters.value.month

  const isAll = projectTab.value === 'all'
  const pt = projectTab.value === 'template' ? 'Шаблонный' : projectTab.value === 'supervision' ? 'Авторский надзор' : isAll ? null : 'Индивидуальный'
  const PT_ENG = { 'Индивидуальный': 'individual', 'Шаблонный': 'template', 'Авторский надзор': 'supervision' }

  const periodLabel = filters.value.quarter ? 'За квартал' : filters.value.month ? 'За месяц' : 'За год'

  const empParams = { ...params }
  if (!isAll) empParams.project_type = projectTab.value
  if (projectTab.value !== 'supervision') empParams.role = roleTab.value

  const ovdParams = { ...params, period: periodLabel }
  if (pt) ovdParams.project_type = pt
  if (projectTab.value !== 'supervision') ovdParams.role = roleTab.value

  const [dashR, empR, projR, survR, ovdR] = await Promise.allSettled([
    statisticsApi.getDashboard({ ...params, ...(isAll ? {} : { project_type: projectTab.value }) }),
    statisticsApi.getEmployees(empParams),
    statisticsApi.getProjects({ ...params, ...(pt ? { project_type: pt } : {}) }),
    surveyApi.getStats({ project_type: PT_ENG[pt] || 'individual' }),
    reportsApi.getEmployeeOverdue(ovdParams),
  ])

  if (dashR.status === 'fulfilled') dashboard.value = dashR.value.data
  if (survR.status === 'fulfilled') surveyStats.value = survR.value.data || null
  else surveyStats.value = null
  overdueList.value = ovdR.status === 'fulfilled' && Array.isArray(ovdR.value.data) ? ovdR.value.data : []

  // Сотрудники — фильтрация по roleTab
  if (empR.status === 'fulfilled' && Array.isArray(empR.value.data)) {
    const allEmps = empR.value.data
    // Фильтруем по роли (учитываем position и secondary_position)
    const _pos = (e) => e.position || ''
    const _sec = (e) => e.secondary_position || ''
    const _hasPos = (e, s) => _pos(e).includes(s) || _sec(e).includes(s)
    const _hasPosLc = (e, s) => _pos(e).toLowerCase().includes(s) || _sec(e).toLowerCase().includes(s)
    const rt = roleTab.value
    let filtered = allEmps
    if (rt === 'dan') {
      filtered = allEmps.filter(e => e.is_supervision_dan)
    } else if (rt === 'manager' && projectTab.value === 'supervision') {
      filtered = allEmps.filter(e => e.is_supervision_manager)
    } else if (rt === 'executor') {
      filtered = allEmps.filter(e => {
        const p = _pos(e); const s = _sec(e)
        return ['Дизайнер', 'Чертёжник', 'Чертежник', 'Замерщик'].some(r => p.includes(r) || s.includes(r)) && p !== 'ДАН' && p !== 'Дизайнер авторского надзора'
      })
    } else {
      // sdp / gap / manager(non-supervision) / designer / draftsman / visualization:
      // backend вернул total_stages из role-specific источника → показываем только реально работавших
      filtered = allEmps.filter(e => e.total_stages > 0)
    }

    roleEmployees.value = filtered.sort((a, b) => b.completion_rate - a.completion_rate)

    // Нагрузка — сотрудники текущей роли с назначенными стадиями
    executorLoad.value = filtered.filter(e => e.total_stages > 0)
      .sort((a, b) => (b.total_stages - b.completed_stages) - (a.total_stages - a.completed_stages))
      .slice(0, 10)
      .map(e => ({ name: e.full_name, active_stages: e.total_stages - e.completed_stages }))
  }

  loading.value = false
}

const surveyKpis = computed(() => {
  const s = surveyStats.value || {}
  return [
    { label: 'NPS', value: s.avg_nps, scale: 10 },
    { label: 'CSAT', value: s.avg_csat, scale: 5 },
    { label: 'Дизайн', value: s.avg_design, scale: 5 },
    { label: 'Сроки', value: s.avg_deadline, scale: 5 },
    { label: 'Общение', value: s.avg_communication, scale: 5 },
    { label: 'Ожидания', value: s.avg_expectations, scale: 5 },
    { label: 'Надзор', value: s.avg_supervision, scale: 5 },
  ]
})

function empSurveyScores(emp) {
  if (!emp) return []
  const pos = emp.position || ''
  const sec = emp.secondary_position || ''
  const _h = (v) => pos.includes(v) || sec.includes(v)
  const isDan = _h('ДАН') || _h('Дизайнер авторского надзора')
  const isDesigner = pos === 'Дизайнер' || sec === 'Дизайнер'
  const isDraftsman = _h('Чертёжник') || _h('Чертежник')
  const isSdp = _h('СДП')
  const isGap = _h('ГАП')
  const isManager = pos.toLowerCase().includes('менеджер') || sec.toLowerCase().includes('менеджер')
  const scores = []
  // NPS и CSAT — для всех ролей
  scores.push({ label: 'NPS', value: emp.avg_nps ?? null, scale: 10 })
  scores.push({ label: 'CSAT', value: emp.avg_csat ?? null, scale: 5 })
  // Дизайн: Дизайнер, СДП, ДАН
  if (isDesigner || isSdp || isDan) scores.push({ label: 'Дизайн', value: emp.avg_design ?? null, scale: 5 })
  // Сроки: Менеджер, СДП, ДАН
  if (isManager || isSdp || isDan) scores.push({ label: 'Сроки', value: emp.avg_deadline ?? null, scale: 5 })
  // Общение: только Менеджер
  if (isManager) scores.push({ label: 'Общение', value: emp.avg_communication ?? null, scale: 5 })
  // Ожидания: ГАП, Менеджер, Чертёжник, ДАН
  if (isGap || isManager || isDraftsman || isDan) scores.push({ label: 'Ожидания', value: emp.avg_expectations ?? null, scale: 5 })
  // Надзор: только ДАН
  if (isDan) scores.push({ label: 'Надзор', value: emp.avg_supervision ?? null, scale: 5 })
  return scores
}

function kpiColor(v) {
  if (v == null) return 'var(--fc-text-light)'
  if (v >= 8) return '#27AE60'
  if (v >= 6) return '#F39C12'
  return '#E74C3C'
}

function showVisitStats(emp) {
  if (!emp || projectTab.value !== 'supervision') return false
  const pos = emp.position || ''
  const isDan = pos === 'ДАН' || pos === 'Дизайнер авторского надзора'
  const isManager = pos.toLowerCase().includes('менеджер')
  return isDan || isManager
}

async function exportPDF() {
  pdfLoading.value = true
  const popup = window.open('', '_blank', 'width=1200,height=800')
  if (!popup) { pdfLoading.value = false; return }
  try { popup.moveTo(0, 0); popup.resizeTo(screen.width, screen.height) } catch(_e) {}
  popup.document.write('<!DOCTYPE html><html><head><meta charset="utf-8"><title>Загрузка...</title></head><body style="font-family:Arial;padding:40px;color:var(--fc-text-medium);text-align:center"><p style="font-size:18px">&#8987; Формирование отчёта...</p></body></html>')
  popup.document.close()

  try {
    const params = { year: filters.value.year }
    if (filters.value.quarter) params.quarter = filters.value.quarter
    if (filters.value.month) params.month = filters.value.month

    const [indR, tmplR, supR, survIndR, survTmplR, survSupR] = await Promise.allSettled([
      statisticsApi.getEmployees({ ...params, project_type: 'individual' }),
      statisticsApi.getEmployees({ ...params, project_type: 'template' }),
      statisticsApi.getEmployees({ ...params, project_type: 'supervision' }),
      surveyApi.getStats({ project_type: 'individual' }),
      surveyApi.getStats({ project_type: 'template' }),
      surveyApi.getStats({ project_type: 'supervision' }),
    ])

    const indEmps  = indR.status   === 'fulfilled' ? (indR.value.data   || []) : []
    const tmplEmps = tmplR.status  === 'fulfilled' ? (tmplR.value.data  || []) : []
    const supEmps  = supR.status   === 'fulfilled' ? (supR.value.data   || []) : []
    const survInd  = survIndR.status  === 'fulfilled' ? survIndR.value.data  : null
    const survTmpl = survTmplR.status === 'fulfilled' ? survTmplR.value.data : null
    const survSup  = survSupR.status  === 'fulfilled' ? survSupR.value.data  : null

    const _MONTHS = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек']
    let periodLabel = String(filters.value.year)
    if (filters.value.month) periodLabel += ' · ' + _MONTHS[filters.value.month - 1]
    else if (filters.value.quarter) periodLabel += ' · Q' + filters.value.quarter

    function shortN(n) { if (!n) return '?'; const p = n.split(' '); return p.length >= 2 ? p[0] + ' ' + p[1] : n }
    function kHex(v) { if (v === null || v === undefined) return 'var(--fc-text-light)'; if (v >= 8) return '#27AE60'; if (v >= 6) return '#F39C12'; return '#E74C3C' }

    function filterRole(emps, rt) {
      const _p = (e) => e.position || ''; const _s = (e) => e.secondary_position || ''
      const _h = (e, v) => _p(e).includes(v) || _s(e).includes(v)
      const _hl = (e, v) => _p(e).toLowerCase().includes(v) || _s(e).toLowerCase().includes(v)
      if (rt === 'sdp') return emps.filter(e => _h(e, 'СДП'))
      if (rt === 'gap') return emps.filter(e => _h(e, 'ГАП'))
      if (rt === 'manager') return emps.filter(e => _hl(e, 'менеджер'))
      if (rt === 'dan') return emps.filter(e => _h(e, 'ДАН') || _h(e, 'Дизайнер авторского надзора'))
      if (rt === 'designer' || rt === 'visualization') return emps.filter(e => _p(e) === 'Дизайнер' || _s(e) === 'Дизайнер')
      if (rt === 'draftsman') return emps.filter(e => _h(e, 'Чертёжник') || _h(e, 'Чертежник'))
      if (rt === 'executor') return emps.filter(e => {
        const p = _p(e); const s = _s(e)
        return ['Дизайнер','Чертёжник','Чертежник','Замерщик'].some(r => p.includes(r) || s.includes(r)) && p !== 'ДАН' && p !== 'Дизайнер авторского надзора'
      })
      return []
    }

    const cd = {}
    const sections = [
      { title: 'Индивидуальные',  key: 'ind',  emps: indEmps,  survey: survInd,  roles: ROLE_TABS.individual },
      { title: 'Шаблонные',       key: 'tmpl', emps: tmplEmps, survey: survTmpl, roles: ROLE_TABS.template },
      { title: 'Авторский надзор', key: 'sup',  emps: supEmps,  survey: survSup,  roles: ROLE_TABS.supervision },
    ]

    let body = ''
    let secIndex = 0
    for (const sec of sections) {
      const { title, key, emps, survey, roles } = sec
      if (!emps.length) continue
      const pageBreak = secIndex > 0 ? 'page-break-before:always;' : ''
      secIndex++

      const loadData = emps.filter(e => e.total_stages > 0)
        .sort((a, b) => (b.total_stages - b.completed_stages) - (a.total_stages - a.completed_stages))
        .slice(0, 12)
      if (loadData.length) {
        cd[`load_${key}`] = {
          labels: loadData.map(e => shortN(e.full_name)),
          data:   loadData.map(e => e.total_stages - e.completed_stages),
        }
      }

      const totalEmps = emps.length
      const avgKpi = totalEmps ? (emps.reduce((s, e) => s + (e.completion_rate || 0), 0) / totalEmps).toFixed(0) : '—'
      const activeEmps = emps.filter(e => e.total_stages > 0).length
      const kpiRowHtml = [
        { label: 'Сотрудников', value: totalEmps },
        { label: 'Ср. KPI', value: totalEmps ? `${avgKpi}%` : '—' },
        { label: 'С активными этапами', value: activeEmps },
      ].map(k =>
        '<td style="text-align:center;padding:8px 14px;border:1px solid var(--fc-border-light)">' +
        `<div style="font-size:20px;font-weight:700;color:var(--fc-text)">${k.value}</div>` +
        `<div style="font-size:9px;color:var(--fc-text-light);margin-top:2px">${k.label}</div></td>`,
      ).join('')

      let roleHtml = ''
      let roleIndex = 0
      for (const role of roles) {
        const rEmps = filterRole(emps, role.code).sort((a, b) => b.completion_rate - a.completion_rate)
        if (!rEmps.length) continue
        const roleDivider = roleIndex > 0 ? '<hr style="border:none;border-top:2px solid var(--fc-border);margin:18px 0 14px">' : ''
        roleIndex++

        const kpiKey = `kpi_${key}_${role.code}`
        cd[kpiKey] = {
          labels: rEmps.map(e => shortN(e.full_name || e.name)),
          data:   rEmps.map(e => Math.round(e.completion_rate || 0)),
        }

        const hasVisits = key === 'sup' && rEmps.some(e => {
          const p = e.position || ''
          return p === 'ДАН' || p === 'Дизайнер авторского надзора' || p.toLowerCase().includes('менеджер')
        })

        const empRows = rEmps.map((e, i) => {
          const kpi = e.completion_rate || 0
          const clr = kHex(kpi / 10)
          const scoreItems = empSurveyScores(e)
          const scoresCells = scoreItems.map(s => {
            if (s.value === null || s.value === undefined) {
              return `<span style="color:var(--fc-border-card);font-size:9px;white-space:nowrap">${s.label}: —</span>`
            }
            return `<span style="color:${kHex(s.value)};font-size:9px;font-weight:600;white-space:nowrap">${s.label}: ${s.value.toFixed(1)}<span style="color:var(--fc-text-disabled);font-weight:400">/${s.scale}</span></span>`
          }).join(' &nbsp;')
          let visitsTd = ''
          if (hasVisits) {
            const isDanPos = e.position === 'ДАН' || e.position === 'Дизайнер авторского надзора'
            const isMgrPos = e.position?.toLowerCase().includes('менеджер')
            if (isDanPos || isMgrPos) {
              const ov = e.visits_overdue ?? 0
              visitsTd = '<td style="padding:5px 8px;font-size:9px;text-align:right;white-space:nowrap">' +
                `${e.visits_object ?? 0} / ${e.visits_supplier ?? 0}` +
                (ov > 0 ? ` <span style="color:#E74C3C">(!${ov})</span>` : '') + '</td>'
            } else {
              visitsTd = '<td style="padding:5px 8px"></td>'
            }
          }
          return `<tr style="background:${i % 2 ? '#fff' : 'var(--fc-bg-hover)'}">` +
            `<td style="padding:5px 8px">${e.full_name || e.name || ''}</td>` +
            `<td style="padding:5px 8px;color:var(--fc-text-light);font-size:10px">${e.position || ''}</td>` +
            `<td style="padding:5px 8px;text-align:right;font-weight:700;color:${clr}">${kpi.toFixed(0)}%</td>` +
            `<td style="padding:5px 8px;text-align:right">${e.completed_stages || 0}/${e.total_stages || 0}</td>` +
            `<td style="padding:5px 8px">${scoresCells}</td>` +
            `${visitsTd}</tr>`
        }).join('')

        const canvH = Math.max(60, rEmps.length * 24)
        const visitsTh = hasVisits ? '<th style="padding:5px 8px;text-align:right;white-space:nowrap">Выезды (об/пост)</th>' : ''
        roleHtml += `${roleDivider}<div class="ct">${role.label} — сравнение KPI</div>
        <canvas id="${kpiKey}" width="700" height="${canvH}" style="break-inside:avoid;margin-bottom:6px"></canvas>
        <table style="width:100%;border-collapse:collapse;font-size:11px;margin-bottom:14px">
          <thead><tr style="background:var(--fc-bg-alt)">
            <th style="padding:5px 8px;text-align:left">Сотрудник</th>
            <th style="padding:5px 8px;text-align:left">Должность</th>
            <th style="padding:5px 8px;text-align:right">KPI%</th>
            <th style="padding:5px 8px;text-align:right">Этапы</th>
            <th style="padding:5px 8px;text-align:left">Оценки клиентов</th>
            ${visitsTh}
          </tr></thead><tbody>${empRows}</tbody></table>`
      }

      let survHtml = ''
      if (survey) {
        const kpis = [
          { label: 'NPS', value: survey.avg_nps, scale: 10 },
          { label: 'CSAT', value: survey.avg_csat, scale: 5 },
          { label: 'Дизайн', value: survey.avg_design, scale: 5 },
          { label: 'Сроки', value: survey.avg_deadline, scale: 5 },
          { label: 'Общение', value: survey.avg_communication, scale: 5 },
          { label: 'Ожидания', value: survey.avg_expectations, scale: 5 },
          { label: 'Надзор', value: survey.avg_supervision, scale: 5 },
        ].filter(k => k.value !== null && k.value !== undefined)
        if (kpis.length) {
          const cells = kpis.map(k =>
            '<td style="text-align:center;padding:6px 10px;border:1px solid var(--fc-border-light)">' +
            `<div style="font-size:15px;font-weight:700;color:${kHex(k.value)}">${k.value.toFixed(1)}</div>` +
            `<div style="font-size:9px;color:var(--fc-text-light)">${k.label} / ${k.scale}</div></td>`,
          ).join('')
          survHtml = `<div class="ct">Опросы клиентов (${survey.completed}/${survey.total} завершено)</div>
          <table style="border-collapse:collapse;margin-bottom:14px"><tr>${cells}</tr></table>`
        }
      }

      const loadCanvH = Math.max(60, loadData.length * 24)
      body += `<h2 style="margin:24px 0 8px;font-size:15px;color:var(--fc-text);border-bottom:2px solid var(--fc-border-light);padding-bottom:4px;${pageBreak}">${title}</h2>
      <table style="border-collapse:collapse;margin-bottom:10px"><tr>${kpiRowHtml}</tr></table>
      ${loadData.length ? `<div class="ct">Нагрузка исполнителей (активных стадий)</div>
      <canvas id="load_${key}" width="700" height="${loadCanvH}" style="break-inside:avoid;margin-bottom:12px"></canvas>` : ''}
      ${roleHtml}${survHtml}`
    }

    let chartCalls = ''
    for (const sec of sections) {
      if (cd[`load_${sec.key}`]) {
        chartCalls += `try{hBar('load_${sec.key}',cd.load_${sec.key}.labels,cd.load_${sec.key}.data,'Стадий','var(--fc-accent)');}catch(e){}\n`
      }
      for (const role of sec.roles) {
        const k = `kpi_${sec.key}_${role.code}`
        if (cd[k]) {
          chartCalls += `try{hBar('${k}',cd.${k.replace(/-/g,'_')}.labels,cd.${k.replace(/-/g,'_')}.data,'KPI%','#27AE60');}catch(e){}\n`
        }
      }
    }
    // cd keys don't have dashes, use bracket access
    chartCalls = ''
    for (const sec of sections) {
      if (cd[`load_${sec.key}`]) {
        chartCalls += `try{hBar('load_${sec.key}',cd['load_${sec.key}'].labels,cd['load_${sec.key}'].data,'Стадий','var(--fc-accent)');}catch(e){}\n`
      }
      for (const role of sec.roles) {
        const k = `kpi_${sec.key}_${role.code}`
        if (cd[k]) {
          chartCalls += `try{hBar('${k}',cd['${k}'].labels,cd['${k}'].data,'KPI%','#27AE60');}catch(e){}\n`
        }
      }
    }

    const now = new Date().toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
    const cdJson = JSON.stringify(cd)

    const html = `<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
    <title>Отчёты по сотрудникам</title>
    <style>
      body { font-family: Arial, sans-serif; padding: 16px; color: var(--fc-text); font-size: 12px; }
      h1 { font-size: 18px; margin: 0 0 3px; }
      .sub { color: var(--fc-text-light); font-size: 11px; margin-bottom: 14px; }
      .ct { font-size: 11px; color: var(--fc-text-medium); font-weight: bold; margin: 10px 0 4px; }
      canvas { display: block; max-width: 100%; break-inside: avoid; }
      @page { size: A4 portrait; margin: 10mm; }
      @media print { body { padding: 0; } }
    </style></head><body>
    <h1>Отчёты по сотрудникам</h1>
    <div class="sub">${periodLabel} &nbsp;·&nbsp; Сформирован: ${now}</div>
    ${body}
    <` + 'script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"><' + `/script>
    <` + `script>
    var __cd = ${cdJson};
    var ROPTS = { animation: false, responsive: false, maintainAspectRatio: false };
    function mkScales() { return { x: { beginAtZero: true, ticks: { font: { size: 8 } } }, y: { ticks: { font: { size: 8 } } } }; }
    function hBar(id, labels, data, label, color) {
      var el = document.getElementById(id); if (!el) return;
      new Chart(el, { type: 'bar', data: { labels: labels, datasets: [{ label: label, data: data, backgroundColor: color || '#3498DB' }] },
        options: Object.assign({}, ROPTS, { indexAxis: 'y', plugins: { legend: { display: false } }, scales: mkScales() }) });
    }
    window.addEventListener('load', function() {
      var cd = __cd;
      ${chartCalls}
      setTimeout(function() { try { window.focus(); window.print(); } catch(e2) {} }, 900);
    });
    <` + `/script>
    </body></html>`

    popup.document.open()
    popup.document.write(html)
    popup.document.close()
  } catch (err) {
    try { popup.document.body.innerHTML = '<p style="padding:20px;color:#c00">Ошибка: ' + (err.message || err) + '</p>' } catch(_e2) {}
  }
  pdfLoading.value = false
}

function resetFilters() {
  filters.value = { year: currentYear, quarter: null, month: null }
  loadData()
}

watch(selectedEmp, async (emp) => {
  showOverdueDetail.value = false
  showEmpProjects.value = false
  empProjects.value = null
  if (!emp) return
  empProjectsLoading.value = true
  try {
    const params = {}
    if (projectTab.value !== 'all') params.project_type = projectTab.value
    if (filters.value.year) params.year = filters.value.year
    if (filters.value.quarter) params.quarter = filters.value.quarter
    if (filters.value.month) params.month = filters.value.month
    if (projectTab.value !== 'supervision') params.role = roleTab.value
    const res = await statisticsApi.getEmployeeProjects(emp.id, params)
    empProjects.value = res.data
  } catch (e) {
    empProjects.value = { items: [] }
  } finally {
    empProjectsLoading.value = false
  }
})
watch(projectTab, (newTab) => {
  const tabs = ROLE_TABS[newTab] || ROLE_TABS.individual
  if (!tabs.find(t => t.code === roleTab.value)) {
    roleTab.value = tabs[0].code
  }
  loadData()
})
watch(roleTab, async () => {
  loadData()
  if (selectedEmp.value && projectTab.value !== 'supervision') {
    empProjects.value = null
    empProjectsLoading.value = true
    try {
      const params = { role: roleTab.value }
      if (projectTab.value !== 'all') params.project_type = projectTab.value
      if (filters.value.year) params.year = filters.value.year
      if (filters.value.quarter) params.quarter = filters.value.quarter
      if (filters.value.month) params.month = filters.value.month
      const res = await statisticsApi.getEmployeeProjects(selectedEmp.value.id, params)
      empProjects.value = res.data
    } catch (e) {
      empProjects.value = { items: [] }
    } finally {
      empProjectsLoading.value = false
    }
  }
})
function onRefresh(done) { loadData().finally(done) }
onMounted(() => loadData())
</script>

<style scoped>
.filter-action-btn {
  width: 100%;
}

.reset-btn {
  height: 40px;
  padding: 0 12px;
  background: var(--fc-accent);
  color: #000;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 13px;
  font-family: inherit;
  outline: none;
}

.reset-btn:hover {
  background: #f0c800;
}

.emp-pdf-btn {
  height: 40px;
  padding: 0 14px;
  border: 1px solid var(--fc-link);
  border-radius: 4px;
  background: var(--fc-bg);
  color: var(--fc-link);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  outline: none;
  white-space: nowrap;
}

.emp-pdf-btn:hover { background: var(--fc-selected-bg); }
.emp-pdf-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
