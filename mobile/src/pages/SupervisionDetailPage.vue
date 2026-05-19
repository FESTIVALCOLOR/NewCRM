<template>
  <q-page padding>
    <div v-if="loading" class="q-pa-md">
      <q-skeleton type="rect" height="120px" class="q-mb-md" />
      <q-skeleton type="text" width="80%" />
      <q-skeleton type="text" width="50%" />
    </div>

    <template v-else-if="card">
      <!-- Шапка (как CrmCardPage) -->
      <q-card class="is-card q-mb-md">
        <q-card-section style="background: #F8F9FA; border-radius: 8px 8px 0 0">
          <div class="row items-start justify-between q-mb-xs">
            <div style="flex: 1">
              <div class="text-subtitle1 text-weight-bold" style="color: #333">
                {{ card.contract_number }}
              </div>
              <div class="text-body2 q-mt-xs" style="color: #333">
                <a v-if="card.address" :href="'https://yandex.ru/maps/?text=' + encodeURIComponent(card.address)" target="_blank" style="color: #333; text-decoration: none"><q-icon name="location_on" size="14px" color="red" class="q-mr-xs" />{{ card.address }}</a>
              </div>
            </div>
            <div class="column items-end q-gutter-xs q-ml-sm" style="flex-shrink: 0">
              <q-badge
                :color="card.is_paused ? 'warning' : 'positive'"
                :label="card.is_paused ? 'Приостановлено' : card.column_name"
                style="min-width: 100px; justify-content: center; padding: 5px 8px; font-size: 11px"
              />
              <q-badge v-if="card.agent_type" text-color="white" :style="{ background: agentColor, minWidth: '100px', justifyContent: 'center', padding: '5px 8px', fontSize: '11px' }" :label="card.agent_type" />
            </div>
          </div>
          <div class="row items-center q-gutter-xs text-caption q-mt-xs" style="color: #888">
            <span v-if="card.project_type">{{ card.project_type }}</span>
            <span v-if="card.project_subtype" style="color: #ccc; margin: 0 4px">|</span><span v-if="card.project_subtype">{{ card.project_subtype }}</span>
            <span v-if="card.area" style="color: #ccc; margin: 0 4px">|</span><span v-if="card.area">{{ card.area }} м²</span>
            <span v-if="card.city" style="color: #ccc; margin: 0 4px">|</span><span v-if="card.city"><q-icon name="location_on" size="12px" /> {{ card.city }}</span>
          </div>
          <div class="row q-gutter-md text-caption q-mt-xs" style="color: #888">
            <span v-if="card.start_date"><q-icon name="play_arrow" size="14px" /> Начало: {{ formatDate(card.start_date) }}</span>
            <span v-if="card.deadline"><q-icon name="flag" size="14px" :style="{ color: dlColor(card.deadline) }" /> Дедлайн: {{ formatDate(card.deadline) }}</span>
          </div>
          <!-- Статус ДАН убран — функционал завершения через кнопку "Завершить стадию" -->
        </q-card-section>
      </q-card>

      <!-- Вкладки (как CrmCardPage) -->
      <q-tabs
        v-model="activeTab"
        dense
        active-color="dark"
        indicator-color="accent"
        no-caps
        class="q-mb-md"
        style="color: #666"
        align="left"
        :breakpoint="0"
      >
        <q-tab name="executors" label="Исполнители" />
        <q-tab name="timeline" label="Закупки" />
        <q-tab name="data" label="Выезды" />
        <q-tab name="history" label="История" />
        <q-tab name="payments" label="Оплаты" />
        <q-tab name="notes" label="Заметки" />
        <q-tab name="chat" label="Чат" />
        <q-tab name="sv-chat" icon="chat" label="Чат надзора" />
      </q-tabs>

      <q-tab-panels v-model="activeTab" animated class="bg-transparent">
        <!-- ====== ВКЛАДКА 1: Исполнители ====== -->
        <q-tab-panel name="executors" class="q-pa-none">
          <!-- Информация о проекте -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">
                Информация
              </div>
            </q-card-section>
            <q-list dense>
              <q-item>
                <q-item-section avatar>
                  <q-icon name="description" color="grey-7" />
                </q-item-section><q-item-section>
                  <q-item-label caption>
                    Договор
                  </q-item-label><q-item-label>{{ card.contract_number }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item v-if="card.project_type">
                <q-item-section avatar>
                  <q-icon name="category" color="grey-7" />
                </q-item-section><q-item-section>
                  <q-item-label caption>
                    Тип проекта
                  </q-item-label><q-item-label>{{ card.project_type }}<span v-if="card.project_subtype"> / {{ card.project_subtype }}</span></q-item-label>
                </q-item-section>
              </q-item>
              <q-item v-if="card.area">
                <q-item-section avatar>
                  <q-icon name="square_foot" color="grey-7" />
                </q-item-section><q-item-section>
                  <q-item-label caption>
                    Площадь
                  </q-item-label><q-item-label>{{ card.area }} м²</q-item-label>
                </q-item-section>
              </q-item>
              <q-item v-if="card.deadline">
                <q-item-section avatar>
                  <q-icon name="flag" color="grey-7" />
                </q-item-section><q-item-section>
                  <q-item-label caption>
                    Дедлайн проекта
                  </q-item-label><q-item-label :style="{ color: dlColor(card.deadline) }">
                    {{ formatDate(card.deadline) }} ({{ daysLeft(card.deadline) }})
                  </q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Команда -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">
                Команда
              </div>
            </q-card-section>
            <q-list dense separator>
              <q-item v-if="card.dan_name || can('supervision.assign_executor')">
                <q-item-section avatar>
                  <q-avatar size="32px" color="orange-2" text-color="orange-8">
                    {{ card.dan_name ? card.dan_name[0] : '?' }}
                  </q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ card.dan_name || 'Не назначен' }}</q-item-label>
                  <q-item-label caption>
                    ДАН
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <div class="row q-gutter-xs">
                    <q-icon v-if="card.dan_completed" name="check_circle" color="positive" />
                    <q-btn
                      v-if="can('supervision.assign_executor')"
                      flat
                      round
                      dense
                      size="xs"
                      icon="edit"
                      color="grey-7"
                      @click="showReassignDan = true"
                    >
                      <q-tooltip>Переназначить</q-tooltip>
                    </q-btn>
                  </div>
                </q-item-section>
              </q-item>
              <q-item v-if="card.senior_manager_name || can('supervision.assign_executor')">
                <q-item-section avatar>
                  <q-avatar size="32px" color="blue-2" text-color="blue-8">
                    {{ card.senior_manager_name ? card.senior_manager_name[0] : '?' }}
                  </q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ card.senior_manager_name || 'Не назначен' }}</q-item-label>
                  <q-item-label caption>
                    Ст. менеджер
                  </q-item-label>
                </q-item-section>
                <q-item-section v-if="can('supervision.assign_executor')" side>
                  <q-btn
                    flat
                    round
                    dense
                    size="xs"
                    icon="edit"
                    color="grey-7"
                    @click="showReassignSM = true"
                  >
                    <q-tooltip>Переназначить</q-tooltip>
                  </q-btn>
                </q-item-section>
              </q-item>
              <q-item v-if="card.studio_director_name">
                <q-item-section avatar>
                  <q-avatar size="32px" color="purple-2" text-color="purple-8">
                    {{ card.studio_director_name[0] }}
                  </q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ card.studio_director_name }}</q-item-label>
                  <q-item-label caption>
                    Руководитель студии
                  </q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Действия -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">
                Действия
              </div>
            </q-card-section>
            <q-card-section>
              <q-btn
                v-if="can('supervision.pause_resume') && !card.is_paused"
                unelevated
                dense
                no-caps
                icon="pause_circle"
                label="Приостановить"
                class="full-width q-mb-sm"
                style="background: #F39C12; color: white; font-size: 12px; font-weight: bold; height: 36px; border-radius: 4px"
                @click="handlePause"
              />
              <q-btn
                v-else-if="can('supervision.pause_resume') && card.is_paused"
                unelevated
                dense
                no-caps
                icon="play_circle"
                label="Возобновить"
                class="full-width q-mb-sm"
                style="background: #27AE60; color: white; font-size: 12px; font-weight: bold; height: 36px; border-radius: 4px"
                @click="handleResume"
              />
              <q-btn
                v-if="can('supervision.complete_stage')"
                unelevated
                dense
                no-caps
                icon="check_circle"
                label="Завершить стадию"
                class="full-width q-mb-sm"
                style="background: #5DADE2; color: white; font-size: 12px; font-weight: bold; height: 36px; border-radius: 4px"
                @click="handleCompleteStage"
              />
              <q-btn
                v-if="can('supervision.move')"
                unelevated
                dense
                no-caps
                icon="swap_horiz"
                label="Переместить"
                class="full-width q-mb-sm"
                style="background: #95A5A6; color: white; font-size: 12px; font-weight: bold; height: 36px; border-radius: 4px"
                @click="showMoveDialog = true"
              />
              <q-btn
                v-if="isDan && !card.dan_completed"
                unelevated
                dense
                no-caps
                icon="check"
                label="Сдать работу"
                class="full-width q-mb-sm"
                style="background: #58D68D; color: white; font-size: 12px; font-weight: bold; height: 36px; border-radius: 4px"
                @click="submitDanWork"
              />
            </q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 2: Сроки (стадии закупок + бюджет) ====== -->
        <q-tab-panel name="timeline" class="q-pa-none">
          <!-- Экспорт + счётчик выездов -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="row items-center justify-between">
                <div class="text-subtitle2 text-weight-bold" style="color: #333">
                  Стадии закупок
                </div>
                <div class="row q-gutter-xs items-center">
                  <q-btn
                    flat
                    dense
                    size="xs"
                    icon="picture_as_pdf"
                    color="grey-7"
                    @click="exportTimelinePDF"
                  >
                    <q-tooltip>Экспорт PDF</q-tooltip>
                  </q-btn>
                  <q-btn
                    flat
                    dense
                    size="xs"
                    icon="table_chart"
                    color="grey-7"
                    @click="exportTimelineExcel"
                  >
                    <q-tooltip>Экспорт Excel</q-tooltip>
                  </q-btn>
                  <div v-if="summary" class="text-caption text-grey-7">
                    {{ supplierVisitsCount }} выездов к поставщикам
                  </div>
                </div>
              </div>
            </q-card-section>

            <!-- Стадии из timeline -->
            <q-list v-if="timeline.length > 0" dense separator>
              <q-item
                v-for="entry in timeline"
                :key="entry.id"
                v-ripple
                clickable
                :style="purchaseRowStyle(entry.status)"
                @click="editTimelineEntry(entry)"
              >
                <q-item-section avatar>
                  <q-icon :name="stageIcon(entry.status)" :color="stageColor(entry.status)" size="20px" />
                </q-item-section>
                <q-item-section>
                  <q-item-label class="text-weight-medium">
                    {{ entry.stage_name.replace(/^Стадия \d+: /, '') }}
                  </q-item-label>
                  <q-item-label caption>
                    <span v-if="entry.plan_date">План: {{ formatDate(entry.plan_date) }}</span>
                    <span v-if="entry.actual_date"> | Факт: {{ formatDate(entry.actual_date) }}</span>
                  </q-item-label>
                  <q-item-label v-if="entry.supplier" caption style="color: #888">
                    {{ entry.supplier }}
                  </q-item-label>
                  <q-item-label v-if="entry.budget_planned > 0" caption style="color: #888">
                    Факт. {{ formatMoney(entry.budget_actual || 0) }} / План {{ formatMoney(entry.budget_planned) }}
                  </q-item-label>
                  <!-- Файлы стадии — кнопка папки ЯД -->
                  <div v-if="stageFiles(entry.stage_code).length > 0" class="q-mt-xs">
                    <q-btn
                      flat
                      dense
                      size="xs"
                      icon="folder_open"
                      :label="`${stageFiles(entry.stage_code).length} файл(ов)`"
                      color="blue"
                      no-caps
                      style="font-size: 10px"
                      @click.stop="openStageFolder(entry)"
                    />
                  </div>
                </q-item-section>
                <q-item-section side>
                  <div class="column items-end q-gutter-xs">
                    <q-badge :color="stageColor(entry.status)" :label="entry.status" dense />
                    <!-- Кнопка загрузки файлов для этой стадии -->
                    <q-btn
                      v-if="can('supervision.files_upload')"
                      flat
                      round
                      dense
                      size="xs"
                      icon="attach_file"
                      color="blue"
                      @click.stop="uploadStageFile(entry.stage_code)"
                    >
                      <q-tooltip>Загрузить файл для стадии</q-tooltip>
                    </q-btn>
                  </div>
                </q-item-section>
              </q-item>
            </q-list>

            <!-- Стадии по умолчанию (если timeline пуст) -->
            <q-list v-else dense separator>
              <q-item
                v-for="s in defaultStages"
                :key="s.code"
                v-ripple
                clickable
                @click="initAndEditStage(s)"
              >
                <q-item-section avatar>
                  <q-icon name="radio_button_unchecked" color="grey-4" size="20px" />
                </q-item-section>
                <q-item-section>
                  <q-item-label class="text-weight-medium">
                    {{ s.name }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <div class="row q-gutter-xs items-center">
                    <q-badge color="grey-4" label="Не начато" dense />
                    <q-btn
                      v-if="can('supervision.files_upload')"
                      flat
                      round
                      dense
                      size="xs"
                      icon="attach_file"
                      color="blue"
                      @click.stop="uploadStageFile(s.code)"
                    >
                      <q-tooltip>Загрузить файл</q-tooltip>
                    </q-btn>
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Бюджет -->
          <q-card v-if="summary && summary.total_budget_planned > 0" class="is-card q-mb-md">
            <q-card-section>
              <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: #333">
                Бюджет
              </div>
              <div class="row q-col-gutter-sm">
                <div class="col-6" style="text-align: center">
                  <div class="text-caption text-grey-7">
                    Запланировано
                  </div>
                  <div class="text-weight-bold">
                    {{ formatMoney(summary.total_budget_planned) }}
                  </div>
                </div>
                <div class="col-6" style="text-align: center">
                  <div class="text-caption text-grey-7">
                    Фактически
                  </div>
                  <div class="text-weight-bold">
                    {{ formatMoney(summary.total_budget_actual) }}
                  </div>
                </div>
                <div class="col-6" style="text-align: center">
                  <div class="text-caption text-grey-7">
                    Экономия
                  </div>
                  <div class="text-weight-bold text-positive">
                    {{ formatMoney(summary.total_savings) }}
                  </div>
                </div>
                <div class="col-6" style="text-align: center">
                  <div class="text-caption text-grey-7">
                    Комиссия
                  </div>
                  <div class="text-weight-bold text-positive">
                    {{ formatMoney(totalCommission) }}
                  </div>
                </div>
              </div>
            </q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 3: Данные (отчёты, фотофиксация, файлы) ====== -->
        <q-tab-panel name="data" class="q-pa-none">
          <!-- Таблица выездов -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-xs">
              <div class="row items-center justify-between">
                <div class="text-subtitle2 text-weight-bold" style="color: #333">
                  Выезды
                </div>
                <q-btn
                  unelevated
                  dense
                  no-caps
                  icon="add"
                  label="Новый выезд"
                  style="background: #ffd93c; color: #333; font-size: 11px; height: 32px; border-radius: 4px"
                  @click="showAddVisit = true"
                />
              </div>
            </q-card-section>

            <!-- Список выездов -->
            <div v-if="visits.length > 0" class="q-pa-sm">
              <q-card
                v-for="visit in visits"
                :key="'data-visit-' + visit.id"
                flat
                bordered
                class="q-mb-sm"
                :style="Object.assign({ borderRadius: '6px' }, visit.actual_date ? { background: '#E8F5E9', borderColor: '#A5D6A7' } : {})"
              >
                <q-card-section class="q-pa-sm">
                  <div class="row items-center q-mb-xs">
                    <q-badge :color="visit.visit_type === 'К поставщику' ? 'blue' : 'green'" :label="visit.visit_type || 'На объект'" dense class="q-mr-xs" />
                    <span class="text-caption text-weight-bold" style="color: #333">{{ formatDate(visit.visit_date) }}</span>
                    <span v-if="visit.actual_date" class="text-caption q-ml-sm" style="color: #27AE60">Факт: {{ formatDate(visit.actual_date) }}</span>
                  </div>
                  <div v-if="visit.stage_name" class="text-caption" style="color: #888">
                    {{ visit.stage_name }}
                  </div>
                  <div v-if="visit.notes" class="text-caption q-mt-xs" style="color: #666">
                    {{ visit.notes }}
                  </div>

                  <!-- Файлы отчёта -->
                  <div v-if="visit.report_files && visit.report_files.length > 0" class="q-mt-xs">
                    <div class="text-caption text-weight-bold" style="color: #555">
                      Отчёт:
                    </div>
                    <div v-for="f in visit.report_files" :key="f.id" class="row items-center q-gutter-xs">
                      <q-icon name="description" size="14px" color="orange" />
                      <a :href="f.public_link || '#'" target="_blank" style="color: #1677FF; text-decoration: none; font-size: 11px">{{ f.file_name }}</a>
                      <q-btn
                        flat
                        round
                        dense
                        size="xs"
                        icon="delete_outline"
                        color="negative"
                        @click.stop="deleteVisitFile(visit, f)"
                      />
                    </div>
                  </div>

                  <!-- Фото -->
                  <div v-if="visit.photo_files && visit.photo_files.length > 0" class="q-mt-xs">
                    <div class="text-caption text-weight-bold" style="color: #555">
                      Фото:
                    </div>
                    <div v-for="f in visit.photo_files" :key="f.id" class="row items-center q-gutter-xs">
                      <q-icon name="image" size="14px" color="blue" />
                      <a :href="f.public_link || '#'" target="_blank" style="color: #1677FF; text-decoration: none; font-size: 11px">{{ f.file_name }}</a>
                      <q-btn
                        flat
                        round
                        dense
                        size="xs"
                        icon="delete_outline"
                        color="negative"
                        @click.stop="deleteVisitFile(visit, f)"
                      />
                    </div>
                  </div>

                  <!-- Кнопки действий + ЯД папка в одной строке -->
                  <div class="row q-gutter-xs q-mt-sm items-center">
                    <q-btn
                      v-if="visit.actual_date || visit.visit_date"
                      flat
                      dense
                      size="xs"
                      icon="folder_open"
                      label="ЯД"
                      color="blue"
                      no-caps
                      style="font-size: 10px; padding: 2px 8px; border-radius: 4px"
                      @click.stop="openVisitFolder(visit)"
                    />
                    <q-space />
                    <q-btn
                      outline
                      dense
                      size="xs"
                      icon="description"
                      label="Отчёт"
                      no-caps
                      color="orange"
                      style="font-size: 10px; padding: 2px 8px; border-radius: 4px"
                      @click="uploadVisitReport(visit)"
                    />
                    <q-btn
                      outline
                      dense
                      size="xs"
                      icon="photo_camera"
                      label="Фото"
                      no-caps
                      color="blue"
                      style="font-size: 10px; padding: 2px 8px; border-radius: 4px"
                      @click="uploadVisitPhoto(visit)"
                    />
                    <q-btn
                      v-if="!visit.actual_date"
                      outline
                      dense
                      size="xs"
                      icon="event_available"
                      label="Факт. выезд"
                      no-caps
                      color="positive"
                      style="font-size: 10px; padding: 2px 8px; border-radius: 4px"
                      @click="setActualDate(visit)"
                    />
                    <q-btn
                      outline
                      dense
                      size="xs"
                      icon="edit"
                      no-caps
                      color="grey-7"
                      style="font-size: 10px; padding: 2px 6px; border-radius: 4px"
                      @click="editVisit(visit)"
                    />
                    <q-btn
                      outline
                      dense
                      size="xs"
                      icon="delete"
                      no-caps
                      color="negative"
                      style="font-size: 10px; padding: 2px 6px; border-radius: 4px"
                      @click="deleteVisit(visit)"
                    />
                  </div>
                </q-card-section>
              </q-card>
            </div>

            <q-card-section v-else class="text-center text-grey-5 q-py-md">
              Нет выездов
            </q-card-section>
          </q-card>

          <!-- Отчёты и фотофиксация (общие) -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-xs">
              <div class="row items-center justify-between">
                <div class="text-subtitle2 text-weight-bold" style="color: #333">
                  Общие отчёты
                </div>
                <div class="row q-gutter-xs">
                  <q-btn
                    v-if="can('supervision.files_upload')"
                    outline
                    dense
                    size="xs"
                    icon="description"
                    label="Отчёт"
                    no-caps
                    color="grey-7"
                    style="border-radius: 4px; padding: 2px 6px"
                    @click="uploadReport"
                  />
                  <q-btn
                    v-if="can('supervision.files_upload')"
                    outline
                    dense
                    size="xs"
                    icon="photo_camera"
                    label="Фото"
                    no-caps
                    color="grey-7"
                    style="border-radius: 4px; padding: 2px 6px"
                    @click="takePhoto"
                  />
                </div>
              </div>
            </q-card-section>
            <q-list v-if="svFilesReports.length > 0" dense>
              <q-item v-for="f in svFilesReports" :key="f.id">
                <q-item-section avatar>
                  <q-icon :name="f.file_type === 'image' ? 'image' : 'description'" :color="f.file_type === 'image' ? 'blue' : 'orange'" size="18px" />
                </q-item-section>
                <q-item-section style="min-width: 0">
                  <q-item-label style="font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
                    <a :href="f.public_link || '#'" target="_blank" style="color: #1677FF; text-decoration: none">{{ f.file_name }}</a>
                  </q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="q-py-sm text-center" style="color: #bbb; font-size: 11px">
              Нет файлов
            </q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 4: История ====== -->
        <q-tab-panel name="history" class="q-pa-none">
          <!-- История надзора -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="row items-center justify-between">
                <div class="text-subtitle2 text-weight-bold" style="color: #333">
                  История проекта
                </div>
                <q-btn
                  unelevated
                  dense
                  no-caps
                  icon="add"
                  label="Добавить запись"
                  style="background: #ffd93c; color: #333; font-size: 11px; height: 32px; border-radius: 4px"
                  @click="showAddHistoryDlg = true"
                />
              </div>
              <q-btn-toggle
                v-model="historyFilter"
                no-caps
                dense
                unelevated
                rounded
                toggle-color="grey-7"
                text-color="grey-7"
                size="xs"
                class="q-mb-sm q-mt-sm"
                :options="[
                  { label: 'Все', value: 'all' },
                  { label: 'Записи', value: 'note' },
                  { label: 'Выезды', value: 'site_visit' },
                  { label: 'Назначения', value: 'assignment_change' },
                ]"
              />
            </q-card-section>
            <q-list v-if="filteredSvHistory.length > 0" dense separator>
              <q-item v-for="h in filteredSvHistory" :key="h.id">
                <q-item-section avatar>
                  <q-icon :name="historyIcon(h.entry_type)" :color="historyColor(h.entry_type)" size="18px" />
                </q-item-section>
                <q-item-section>
                  <q-item-label style="font-size: 12px; color: #333">
                    {{ cleanNoteText(h) }}
                  </q-item-label>
                  <q-item-label caption style="color: #888">
                    <span v-if="h.entry_type" style="font-weight: bold">{{ historyLabel(h.entry_type) }}</span>
                    <span v-if="h.created_by_name"> · {{ h.created_by_name }}</span>
                    <span> · {{ formatDate(h.created_at) }}</span>
                  </q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="text-center" style="color: #999; font-size: 12px">
              Нет записей
            </q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 5: Оплаты надзора ====== -->
        <q-tab-panel name="payments" class="q-pa-none">
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">
                Оплаты надзора
              </div>
            </q-card-section>
            <q-list v-if="svPayments.length > 0" dense separator>
              <q-item v-for="p in svPayments" :key="p.id" :style="p.is_paid ? { background: '#E8F5E9' } : {}">
                <q-item-section>
                  <q-item-label style="font-size: 12px">
                    {{ p.employee_name || 'Не указан' }}
                  </q-item-label>
                  <q-item-label caption>
                    {{ p.role || '' }} {{ p.stage_name ? `· ${p.stage_name}` : '' }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <div class="text-weight-bold" :style="{ color: p.is_paid ? '#27AE60' : '#333' }">
                    {{ formatMoney(p.final_amount || p.amount || 0) }}
                  </div>
                  <div class="text-caption" style="color: #888">
                    {{ p.is_paid ? 'оплачено' : p.payment_status === 'to_pay' ? 'к оплате' : 'в работе' }}
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
            <div v-if="svPayments.length > 0" class="row items-center q-px-md q-py-xs" style="background: #F5F5F5; border-top: 1px solid #E0E0E0">
              <span style="font-size: 12px; font-weight: bold; color: #333; flex: 1">Итого</span>
              <span style="font-size: 13px; font-weight: bold; color: #333">{{ formatMoney(svPayments.reduce((s, p) => s + (p.final_amount || p.amount || 0), 0)) }}</span>
            </div>
            <q-card-section v-if="svPayments.length === 0" class="text-center" style="color: #999; font-size: 12px">
              Нет оплат
            </q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 6: Заметки (текстовые + голосовые) ====== -->
        <q-tab-panel name="notes" class="q-pa-none">
          <!-- Добавить текстовую заметку -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="row items-center justify-between">
                <div class="text-subtitle2 text-weight-bold" style="color: #333">
                  Новая заметка
                </div>
                <VoiceRecorder :yandex-folder-path="svContractYdPath ? svContractYdPath + '/Авторский надзор' : ''" @recorded="onVoiceRecorded" />
              </div>
            </q-card-section>
            <q-card-section>
              <q-input
                v-model="noteText"
                outlined
                dense
                type="textarea"
                autogrow
                placeholder="Введите текст заметки..."
                class="q-mb-sm"
              />
              <q-btn
                unelevated
                dense
                no-caps
                icon="add"
                label="Добавить заметку"
                style="background: #ffd93c; color: #333; font-size: 12px; height: 36px; border-radius: 4px"
                :disable="!noteText?.trim()"
                @click="addTextNote"
              />
            </q-card-section>
          </q-card>

          <!-- Список заметок -->
          <q-card class="is-card">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">
                Все заметки
              </div>
            </q-card-section>
            <q-list v-if="voiceNotes.length > 0" dense separator>
              <q-item v-for="h in voiceNotes" :key="h.id">
                <q-item-section avatar>
                  <q-icon :name="h.entry_type === 'voice_note' ? 'mic' : 'comment'" :color="h.entry_type === 'voice_note' ? 'purple' : 'blue-grey'" size="18px" />
                </q-item-section>
                <q-item-section>
                  <q-item-label style="font-size: 12px; color: #333">
                    {{ cleanNoteText(h) }}
                  </q-item-label>
                  <q-item-label caption style="color: #888">
                    {{ h.created_by_name || 'Неизвестный' }}
                  </q-item-label>
                </q-item-section>
                <q-item-section v-if="h.entry_type === 'voice_note' && extractVoiceUrl(h)" side>
                  <audio :src="voiceStreamUrl(extractVoiceUrl(h))" controls preload="none" style="height: 36px; width: 120px" />
                </q-item-section>
                <q-item-section side>
                  <div class="text-caption" style="color: #888">
                    {{ formatDate(h.created_at) }}
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="text-center" style="color: #999; padding: 24px">
              <q-icon name="speaker_notes_off" size="32px" color="grey-4" class="q-mb-sm" /><div>Нет заметок</div>
            </q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 7: Telegram-чат ====== -->
        <q-tab-panel name="chat" class="q-pa-none">
          <div v-if="svChatLoading" class="q-pa-md text-center">
            <q-spinner color="grey-5" size="24px" />
          </div>

          <template v-else-if="svChatData">
            <q-card class="is-card q-mb-md">
              <q-card-section>
                <div class="text-subtitle2 text-weight-bold q-mb-xs" style="color: #333">
                  {{ svChatData.chat_title || 'Проектный чат' }}
                </div>
                <div v-if="svChatData.invite_link" class="q-mb-sm">
                  <a :href="tgDeepLink(svChatData.invite_link)" style="color: #1677FF; text-decoration: none; font-size: 13px">
                    <q-icon name="open_in_new" size="14px" class="q-mr-xs" />Открыть в Telegram
                  </a>
                </div>
                <div class="text-caption" style="color: #888">
                  {{ svChatMembers.length }} участник(ов)
                </div>
              </q-card-section>
            </q-card>

            <!-- Участники -->
            <q-card class="is-card q-mb-md">
              <q-card-section class="q-pb-none">
                <div class="text-subtitle2 text-weight-bold" style="color: #333">
                  Участники
                </div>
              </q-card-section>
              <q-list v-if="svChatMembers.length > 0" dense separator>
                <q-item v-for="member in svChatMembers" :key="member.id || member.user_id">
                  <q-item-section avatar>
                    <q-avatar size="24px" color="grey-3" text-color="grey-8">
                      {{ (member.name || member.username || '?')[0] }}
                    </q-avatar>
                  </q-item-section>
                  <q-item-section>
                    <q-item-label style="font-size: 11px">
                      {{ member.name || member.username || 'Неизвестный' }}
                    </q-item-label>
                    <q-item-label caption style="font-size: 10px">
                      {{ member.role || 'участник' }}
                    </q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </q-card>

            <!-- Действия с чатом -->
            <q-card class="is-card q-mb-md">
              <q-card-section class="q-pb-none">
                <div class="text-subtitle2 text-weight-bold" style="color: #333">
                  Действия
                </div>
              </q-card-section>
              <q-card-section>
                <q-btn
                  unelevated
                  dense
                  no-caps
                  icon="send"
                  label="Отправить сообщение"
                  class="full-width q-mb-sm"
                  style="background: #5DADE2; color: white; font-size: 12px; height: 36px; border-radius: 4px"
                  @click="showSvSendMsgDlg = true"
                />
                <q-btn
                  unelevated
                  dense
                  no-caps
                  icon="smart_toy"
                  label="Запустить скрипт"
                  class="full-width q-mb-sm"
                  style="background: #58D68D; color: white; font-size: 12px; height: 36px; border-radius: 4px"
                  @click="loadSvScriptsAndShow"
                />
                <q-btn
                  unelevated
                  dense
                  no-caps
                  icon="person_add"
                  label="Добавить участника"
                  class="full-width q-mb-sm"
                  style="background: #AAB7B8; color: white; font-size: 12px; height: 36px; border-radius: 4px"
                  @click="showAddSvMemberDlg = true"
                />
                <q-btn
                  outline
                  dense
                  no-caps
                  icon="delete"
                  label="Удалить чат"
                  class="full-width"
                  color="negative"
                  style="font-size: 12px; height: 36px; border-radius: 4px"
                  @click="confirmDeleteSvChat"
                />
              </q-card-section>
            </q-card>
          </template>

          <!-- Чат не создан -->
          <template v-else>
            <q-card class="is-card q-mb-md">
              <q-card-section class="text-center q-pa-lg">
                <q-icon name="chat_bubble_outline" size="48px" color="grey-4" class="q-mb-sm" />
                <div style="color: #999; font-size: 13px" class="q-mb-md">
                  Telegram-чат не создан
                </div>
                <q-btn
                  unelevated
                  dense
                  no-caps
                  icon="add"
                  label="Создать чат"
                  style="background: #ffd93c; color: #333; font-size: 12px; font-weight: bold; height: 36px; border-radius: 4px; padding: 0 24px"
                  :loading="svChatCreating"
                  @click="openCreateSvChatDlg"
                />
              </q-card-section>
            </q-card>
          </template>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 8: Чат надзора (InlineChatRoom) ====== -->
        <q-tab-panel name="sv-chat" class="q-pa-none">
          <InlineChatRoom
            v-if="svChatTabVisited && card?.id"
            chat-type="supervision"
            :supervision-card-id="card.id"
          />
        </q-tab-panel>
      </q-tab-panels>
    </template>

    <div v-else class="text-center q-pa-xl text-grey-5">
      <q-icon name="search_off" size="48px" class="q-mb-sm" />
      <div>Карточка не найдена</div>
      <q-btn
        flat
        color="primary"
        label="Назад"
        class="q-mt-md"
        no-caps
        @click="$router.back()"
      />
    </div>

    <!-- Диалог добавления выезда -->
    <q-dialog v-model="showAddVisit" @hide="editingVisitId = null">
      <q-card style="min-width: 320px">
        <q-card-section>
          <div class="text-subtitle1 text-weight-bold">
            {{ editingVisitId ? 'Редактировать выезд' : 'Новый выезд' }}
          </div>
        </q-card-section>
        <q-card-section>
          <q-input
            v-model="visitForm.visit_date"
            label="Дата выезда"
            outlined
            dense
            type="date"
            class="q-mb-sm"
          />
          <q-select
            v-model="visitForm.visit_type"
            :options="['На объект', 'К поставщику']"
            label="Тип выезда"
            outlined
            dense
            class="q-mb-sm"
          />
          <q-select
            v-model="visitForm.stage_code"
            :options="stageCodesForVisit"
            label="Стадия"
            outlined
            dense
            emit-value
            map-options
            class="q-mb-sm"
          />
          <q-select
            v-model="visitForm.executor_name"
            :options="executorNameOptions"
            label="Исполнитель (ДАН)"
            outlined
            dense
            emit-value
            class="q-mb-sm"
          />
          <q-input
            v-model="visitForm.notes"
            label="Заметки"
            outlined
            dense
            type="textarea"
            autogrow
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" no-caps />
          <q-btn
            unelevated
            color="positive"
            label="Сохранить"
            no-caps
            @click="saveVisit"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог редактирования стадии -->
    <q-dialog v-model="showEditEntry">
      <q-card style="min-width: 320px">
        <q-card-section>
          <div class="text-subtitle1 text-weight-bold">
            {{ editEntry?.stage_name }}
          </div>
        </q-card-section>
        <q-card-section v-if="editEntry" class="q-pt-none">
          <q-input
            v-model="editEntry.plan_date"
            label="Плановая дата"
            outlined
            dense
            type="date"
            class="q-mb-sm"
          />
          <q-input
            v-model="editEntry.actual_date"
            label="Фактическая дата"
            outlined
            dense
            type="date"
            class="q-mb-sm"
          />
          <q-input
            v-model.number="editEntry.budget_planned"
            label="Бюджет план"
            outlined
            dense
            type="number"
            prefix="₽"
            class="q-mb-sm"
          />
          <q-input
            v-model.number="editEntry.budget_actual"
            label="Бюджет факт"
            outlined
            dense
            type="number"
            prefix="₽"
            class="q-mb-sm"
          />
          <q-input
            v-model="editEntry.supplier"
            label="Поставщик"
            outlined
            dense
            class="q-mb-sm"
          />
          <q-input
            v-model="editEntry.commission"
            label="Комиссия (доход студии)"
            outlined
            dense
            type="number"
            prefix="₽"
            class="q-mb-sm"
          />
          <q-select
            v-model="editEntry.status"
            :options="['Не начато','В работе','Закуплено','Доставлено','Просрочено']"
            label="Статус"
            outlined
            dense
            class="q-mb-sm"
          />
          <q-input
            v-model="editEntry.notes"
            label="Заметки"
            outlined
            dense
            type="textarea"
            autogrow
            class="q-mb-sm"
          />
          <q-select
            v-model="editEntry.executor"
            :options="executorNameOptions"
            label="Исполнитель"
            outlined
            dense
            emit-value
            class="q-mb-sm"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" no-caps />
          <q-btn
            unelevated
            color="accent"
            text-color="dark"
            label="Сохранить"
            no-caps
            @click="saveTimelineEntry"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог переназначения ДАН -->
    <q-dialog v-model="showReassignDan" @show="loadReassignOptions">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #F39C12; color: white">
          <q-toolbar-title style="font-size: 14px">
            Переназначить ДАН
          </q-toolbar-title><q-btn
            v-close-popup
            flat
            round
            dense
            icon="close"
            color="white"
          />
        </q-toolbar>
        <q-card-section>
          <div v-if="card.dan_name" class="q-mb-sm" style="background: #FFF3CD; padding: 8px; border-radius: 4px; font-size: 12px">
            Текущий: <b>{{ card.dan_name }}</b>
          </div>
          <q-select
            v-model="newDanId"
            :options="danOptions"
            option-value="id"
            option-label="label"
            label="Новый ДАН"
            outlined
            dense
            emit-value
            map-options
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" no-caps /><q-btn
            unelevated
            label="Переназначить"
            no-caps
            style="background: #F39C12; color: white; border-radius: 4px"
            @click="reassignDan"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог переназначения Ст. менеджера -->
    <q-dialog v-model="showReassignSM" @show="loadReassignOptions">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #3498DB; color: white">
          <q-toolbar-title style="font-size: 14px">
            Переназначить Ст. менеджера
          </q-toolbar-title><q-btn
            v-close-popup
            flat
            round
            dense
            icon="close"
            color="white"
          />
        </q-toolbar>
        <q-card-section>
          <div v-if="card.senior_manager_name" class="q-mb-sm" style="background: #D6EAF8; padding: 8px; border-radius: 4px; font-size: 12px">
            Текущий: <b>{{ card.senior_manager_name }}</b>
          </div>
          <q-select
            v-model="newSMId"
            :options="smOptions"
            option-value="id"
            option-label="label"
            label="Новый Ст. менеджер"
            outlined
            dense
            emit-value
            map-options
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" no-caps /><q-btn
            unelevated
            label="Переназначить"
            no-caps
            style="background: #3498DB; color: white; border-radius: 4px"
            @click="reassignSM"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог перемещения на стадию -->
    <q-dialog v-model="showMoveDialog">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #5DADE2; color: white">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
            Переместить на стадию
          </q-toolbar-title>
          <q-btn
            v-close-popup
            flat
            round
            dense
            icon="close"
            color="white"
          />
        </q-toolbar>
        <q-card-section>
          <q-select
            v-model="moveTargetColumn"
            :options="supervisionColumns"
            label="Стадия"
            outlined
            dense
            emit-value
            map-options
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" no-caps />
          <q-btn
            unelevated
            label="Переместить"
            no-caps
            style="background: #5DADE2; color: white; border-radius: 4px"
            :disable="!moveTargetColumn"
            @click="doMoveSupervision"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог добавления записи -->
    <q-dialog v-model="showAddHistoryDlg">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #ffd93c; color: #333">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
            Добавить запись
          </q-toolbar-title>
          <q-btn
            v-close-popup
            flat
            round
            dense
            icon="close"
          />
        </q-toolbar>
        <q-card-section>
          <q-input
            v-model="historyNote"
            label="Описание"
            outlined
            dense
            type="textarea"
            autogrow
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" no-caps />
          <q-btn
            unelevated
            label="Добавить"
            no-caps
            style="background: #ffd93c; color: #333; border-radius: 4px"
            :disable="!historyNote"
            @click="doAddHistory"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог создания Telegram-чата надзора -->
    <q-dialog v-model="showCreateSvChatDlg" persistent>
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #ffd93c; color: #333">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
            Создать Telegram-чат
          </q-toolbar-title>
          <q-btn
            flat
            round
            dense
            icon="close"
            @click="showCreateSvChatDlg = false"
          />
        </q-toolbar>
        <q-card-section>
          <q-input
            v-model="newSvChatTitle"
            label="Название чата"
            outlined
            dense
            class="q-mb-xs"
            hint="АН-Город-Адрес"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" no-caps />
          <q-btn
            unelevated
            label="Создать"
            style="background: #ffd93c; color: #333; border-radius: 4px"
            no-caps
            :loading="svChatCreating"
            :disable="!newSvChatTitle.trim()"
            @click="createSvChat"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог отправки сообщения в чат надзора -->
    <q-dialog v-model="showSvSendMsgDlg">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #5DADE2; color: white">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
            Отправить сообщение
          </q-toolbar-title><q-btn
            v-close-popup
            flat
            round
            dense
            icon="close"
            color="white"
          />
        </q-toolbar>
        <q-card-section>
          <q-input
            v-model="svChatMsgText"
            label="Текст сообщения"
            outlined
            dense
            type="textarea"
            autogrow
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" no-caps /><q-btn
            unelevated
            label="Отправить"
            style="background: #5DADE2; color: white; border-radius: 4px"
            no-caps
            :loading="svChatActionLoading"
            :disable="!svChatMsgText?.trim()"
            @click="doSendSvMessage"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог добавления участника в чат надзора -->
    <q-dialog v-model="showAddSvMemberDlg">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #AAB7B8; color: white">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
            Добавить участника
          </q-toolbar-title>
          <q-btn
            v-close-popup
            flat
            round
            dense
            icon="close"
            color="white"
          />
        </q-toolbar>
        <q-card-section>
          <q-select
            v-model="addSvMemberEmployeeId"
            :options="executorOptions"
            option-value="value"
            option-label="label"
            label="Сотрудник"
            outlined
            dense
            emit-value
            map-options
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" no-caps />
          <q-btn
            unelevated
            label="Добавить"
            style="background: #AAB7B8; color: white; border-radius: 4px"
            no-caps
            :loading="addSvMemberLoading"
            :disable="!addSvMemberEmployeeId"
            @click="doAddSvMember"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог выбора скрипта надзора -->
    <q-dialog v-model="showSvScriptsDlg">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #58D68D; color: white">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
            Запустить скрипт
          </q-toolbar-title><q-btn
            v-close-popup
            flat
            round
            dense
            icon="close"
            color="white"
          />
        </q-toolbar>
        <q-list v-if="svChatScripts.length > 0" dense separator>
          <q-item
            v-for="script in svChatScripts"
            :key="script.id"
            v-ripple
            clickable
            @click="doTriggerSvScript(script)"
          >
            <q-item-section avatar>
              <q-icon name="smart_toy" color="grey-7" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ script.name || script.code }}</q-item-label>
              <q-item-label caption>
                {{ script.description || '' }}
              </q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
        <q-card-section v-else class="text-center" style="color: #999">
          Нет доступных скриптов
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Диалог загрузки файлов для стадии -->
    <q-dialog v-model="showStageFileUpload">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #5DADE2; color: white">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
            Загрузить файлы — {{ uploadStageLabel }}
          </q-toolbar-title>
          <q-btn
            v-close-popup
            flat
            round
            dense
            icon="close"
            color="white"
          />
        </q-toolbar>
        <q-card-section>
          <q-file
            v-model="stageUploadFiles"
            label="Выберите файлы"
            outlined
            dense
            multiple
            accept=".pdf,.jpg,.jpeg,.png,.xls,.xlsx,.doc,.docx"
            counter
          >
            <template #prepend>
              <q-icon name="attach_file" />
            </template>
          </q-file>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" no-caps />
          <q-btn
            unelevated
            label="Загрузить"
            no-caps
            style="background: #5DADE2; color: white; border-radius: 4px"
            :loading="stageUploading"
            :disable="!stageUploadFiles?.length"
            @click="doUploadStageFiles"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Скрытые file inputs -->
    <input
      ref="reportFileInput"
      type="file"
      accept=".pdf,.doc,.docx,.xls,.xlsx"
      style="display:none"
      @change="handleReportUpload"
    >
    <input
      ref="cameraInput"
      type="file"
      accept="image/*"
      capture="environment"
      style="display:none"
      @change="handlePhotoCapture"
    >
    <input
      ref="fileInput"
      type="file"
      accept="image/*,.pdf"
      style="display:none"
      @change="handleFileUpload"
    >
    <input
      ref="nadzorFileInput"
      type="file"
      accept=".pdf,.jpg,.jpeg,.png,.xls,.xlsx"
      style="display:none"
      @change="handleNadzorFileUpload"
    >
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { supervisionApi, filesApi, employeesApi, paymentsApi, locksApi, messengerApi } from 'src/services/api'
import VoiceRecorder from 'src/components/VoiceRecorder.vue'
import InlineChatRoom from 'src/components/InlineChatRoom.vue'
import { addToCalendar } from 'src/composables/useCalendar'
import { usePermission } from 'src/composables/usePermission'
import { useAuthStore } from 'src/stores/auth'
import { useReferencesStore } from 'src/stores/references'

const { can } = usePermission()
const refs = useReferencesStore()
const authStore = useAuthStore()
const agentColor = computed(() => refs.agentByName(card.value?.agent_type)?.color || '#95A5A6')

const route = useRoute()
const router = useRouter()
const $q = useQuasar()
const loading = ref(true)
const card = ref(null)
const timeline = ref([])
const summary = ref(null)
const visits = ref([])
// Комиссия считается из timeline entries (серверный summary может не содержать)
const totalCommission = computed(() => {
  const fromSummary = summary.value?.total_commission
  if (fromSummary && fromSummary > 0) return fromSummary
  // Fallback: сумма commission из timeline
  return timeline.value.reduce((sum, e) => sum + (parseFloat(e.commission) || 0), 0)
})
const activeTab = ref('executors')
const svChatTabVisited = ref(false)
if (route.query.tab) activeTab.value = route.query.tab
const svContractYdPath = ref('')
const showAddVisit = ref(false)
const editingVisitId = ref(null)
const showReassignDan = ref(false)
const showReassignSM = ref(false)
const newDanId = ref(null)
const newSMId = ref(null)
const danOptions = ref([])
const smOptions = ref([])
const showEditEntry = ref(false)
const editEntry = ref(null)
const cameraInput = ref(null)
const fileInput = ref(null)
const nadzorFileInput = ref(null)
const visitForm = ref({ visit_date: new Date().toISOString().split('T')[0], stage_code: '', notes: '', executor_name: '', visit_type: 'На объект' })
const executorOptions = ref([])
const executorNameOptions = ref([])
const svPayments = ref([])
const svHistory = ref([])
const svFilesSupervision = ref([])
const svFilesReports = ref([])
const reportFileInput = ref(null)
const showMoveDialog = ref(false)
const moveTargetColumn = ref(null)
const showAddHistoryDlg = ref(false)
const historyNote = ref('')
const noteText = ref('')

const historyFilter = ref('all')
const filteredSvHistory = computed(() => {
  if (historyFilter.value === 'all') return svHistory.value
  return svHistory.value.filter(h => h.entry_type === historyFilter.value)
})

// === Файлы по стадиям ===
const svFilesStages = ref({}) // { stage_code: [файлы] }
const showStageFileUpload = ref(false)
const stageUploadFiles = ref(null)
const stageUploading = ref(false)
const uploadStageCode = ref('')

// === Telegram-чат надзора ===
const svChatData = ref(null)
const svChatMembers = ref([])
const svChatLoading = ref(false)
const svChatCreating = ref(false)
const svChatActionLoading = ref(false)
const showSvSendMsgDlg = ref(false)
const showSvScriptsDlg = ref(false)
const svChatMsgText = ref('')
const svChatScripts = ref([])
const showCreateSvChatDlg = ref(false)
const newSvChatTitle = ref('')
const showAddSvMemberDlg = ref(false)
const addSvMemberEmployeeId = ref(null)
const addSvMemberLoading = ref(false)

// ДАН ли текущий пользователь
const isDan = computed(() => {
  return card.value && card.value.dan_id === authStore.user?.id
})

// Голосовые заметки — фильтрация из истории
const voiceNotes = computed(() => {
  return svHistory.value.filter(h =>
    h.description?.includes('Голосовая заметка') ||
    h.description?.includes('Текстовая заметка') ||
    h.entry_type === 'note' ||
    h.entry_type === 'voice_note',
  )
})

const supplierVisitsCount = computed(() => {
  return visits.value.filter(v => v.visit_type === 'К поставщику').length
})

// Имя стадии для диалога загрузки файлов
const uploadStageLabel = computed(() => {
  const ds = defaultStages.find(s => s.code === uploadStageCode.value)
  if (ds) return ds.name
  const tl = timeline.value.find(e => e.stage_code === uploadStageCode.value)
  return tl?.stage_name?.replace(/^Стадия \d+: /, '') || uploadStageCode.value
})

// Файлы конкретной стадии (основной источник + fallback по supervision файлам)
function stageFiles(stageCode) {
  const fromStages = svFilesStages.value[stageCode] || []
  if (fromStages.length > 0) return fromStages
  // Fallback: ищем в общих supervision файлах по stage_code
  return svFilesSupervision.value.filter(f => f.stage_code === stageCode)
}

function openStageFolder(entry) {
  const files = stageFiles(entry.stage_code)
  if (files.length > 0 && files[0].yandex_path) {
    const filePath = files[0].yandex_path.replace(/^disk:/, '').replace(/\/[^/]+$/, '')
    const encoded = encodeURIComponent(filePath).replace(/%2F/g, '/')
    window.open(`https://disk.yandex.ru/client/disk${encoded}`, '_blank')
  } else if (files.length > 0 && files[0].public_link) {
    window.open(files[0].public_link, '_blank')
  }
}

function openVisitFolder(visit) {
  // Формируем путь к папке выезда на ЯД
  const contractFolder = svContractYdPath.value || ''
  const visitDate = visit.visit_date || 'unknown'
  const subfolder = `Авторский надзор/Выезды/${visitDate}`
  const folderPath = contractFolder ? `${contractFolder}/${subfolder}` : `/CRM/Надзор/Выезды/${visitDate}`
  const clean = folderPath.replace(/^disk:/, '')
  const encoded = encodeURIComponent(clean).replace(/%2F/g, '/')
  window.open(`https://disk.yandex.ru/client/disk${encoded}`, '_blank')
}

const defaultStages = [
  { code: 'STAGE_1_CERAMIC', name: 'Закупка керамогранита' },
  { code: 'STAGE_2_PLUMBING', name: 'Закупка сантехники' },
  { code: 'STAGE_3_EQUIPMENT', name: 'Закупка оборудования' },
  { code: 'STAGE_4_DOORS', name: 'Закупка дверей и окон' },
  { code: 'STAGE_5_WALLS', name: 'Закупка настенных материалов' },
  { code: 'STAGE_6_FLOORS', name: 'Закупка напольных материалов' },
  { code: 'STAGE_7_STUCCO', name: 'Лепной декор' },
  { code: 'STAGE_8_LIGHTING', name: 'Освещение' },
  { code: 'STAGE_9_APPLIANCES', name: 'Бытовая техника' },
  { code: 'STAGE_10_CUSTOM_FURNITURE', name: 'Закупка заказной мебели' },
  { code: 'STAGE_11_FACTORY_FURNITURE', name: 'Закупка фабричной мебели' },
  { code: 'STAGE_12_DECOR', name: 'Закупка декора' },
]

function initAndEditStage(s) {
  editEntry.value = {
    stage_code: s.code,
    stage_name: `Стадия: ${s.name}`,
    plan_date: '', actual_date: '', budget_planned: 0, budget_actual: 0,
    supplier: '', status: 'Не начато', notes: '', executor: '',
  }
  showEditEntry.value = true
}

const supervisionColumns = [
  { label: 'Новый заказ', value: 'Новый заказ' },
  { label: 'Стадия 1: Закупка керамогранита', value: 'Стадия 1: Закупка керамогранита' },
  { label: 'Стадия 2: Закупка сантехники', value: 'Стадия 2: Закупка сантехники' },
  { label: 'Стадия 3: Закупка оборудования', value: 'Стадия 3: Закупка оборудования' },
  { label: 'Стадия 4: Двери и окна', value: 'Стадия 4: Двери и окна' },
  { label: 'Стадия 5: Настенные материалы', value: 'Стадия 5: Настенные материалы' },
  { label: 'Стадия 6: Напольные материалы', value: 'Стадия 6: Напольные материалы' },
  { label: 'Стадия 7: Лепной декор', value: 'Стадия 7: Лепной декор' },
  { label: 'Стадия 8: Освещение', value: 'Стадия 8: Освещение' },
  { label: 'Стадия 9: Бытовая техника', value: 'Стадия 9: Бытовая техника' },
  { label: 'Стадия 10: Закупка заказной мебели', value: 'Стадия 10: Закупка заказной мебели' },
  { label: 'Стадия 11: Закупка фабричной мебели', value: 'Стадия 11: Закупка фабричной мебели' },
  { label: 'Стадия 12: Закупка декора', value: 'Стадия 12: Закупка декора' },
  { label: 'Выполненный проект', value: 'Выполненный проект' },
]

const stageCodesForVisit = [
  { label: 'Ст. 1: Закупка керамогранита', value: 'STAGE_1_CERAMIC' },
  { label: 'Ст. 2: Закупка сантехники', value: 'STAGE_2_PLUMBING' },
  { label: 'Ст. 3: Закупка оборудования', value: 'STAGE_3_EQUIPMENT' },
  { label: 'Ст. 4: Двери и окна', value: 'STAGE_4_DOORS' },
  { label: 'Ст. 5: Настенные материалы', value: 'STAGE_5_WALLS' },
  { label: 'Ст. 6: Напольные материалы', value: 'STAGE_6_FLOORS' },
  { label: 'Ст. 7: Лепной декор', value: 'STAGE_7_STUCCO' },
  { label: 'Ст. 8: Освещение', value: 'STAGE_8_LIGHTING' },
  { label: 'Ст. 9: Бытовая техника', value: 'STAGE_9_APPLIANCES' },
  { label: 'Ст. 10: Заказная мебель', value: 'STAGE_10_CUSTOM_FURNITURE' },
  { label: 'Ст. 11: Фабричная мебель', value: 'STAGE_11_FACTORY_FURNITURE' },
  { label: 'Ст. 12: Декор', value: 'STAGE_12_DECOR' },
]

function stageIcon(status) {
  const icons = {
    'Не начато': 'radio_button_unchecked',
    'В работе': 'pending',
    'Закуплено': 'shopping_cart',
    'Доставлено': 'check_circle',
    'Просрочено': 'error',
  }
  return icons[status] || 'radio_button_unchecked'
}

function stageColor(status) {
  const colors = {
    'Не начато': 'grey-5',
    'В работе': 'orange',
    'Закуплено': 'blue',
    'Доставлено': 'positive',
    'Просрочено': 'negative',
  }
  return colors[status] || 'grey'
}

function purchaseRowStyle(status) {
  if (status === 'Закуплено' || status === 'Доставлено') return { background: '#E8F5E9' }
  if (status === 'Просрочено') return { background: '#FFEBEE' }
  return {}
}

function voiceStreamUrl(path) {
  const cleanPath = path.replace(/^disk:/, '')
  const token = localStorage.getItem('access_token') || ''
  return `https://crm.festivalcolor.ru/api/v1/files/stream?yandex_path=${encodeURIComponent(cleanPath)}&token=${encodeURIComponent(token)}`
}

function cleanNoteText(h) {
  const msg = h.message || h.description || 'Заметка'
  // Убрать путь ЯД из текста: "Голосовая заметка (0:03) — /CRM/.../file.webm" → "Голосовая заметка (0:03)"
  return msg.replace(/\s*—\s*\/CRM\/.+$/, '').replace(/\[voice:[^\]]*\]\s*/, '')
}

function extractVoiceUrl(h) {
  // Извлечь путь голосовой из message — формат: "Голосовая заметка (0:02) — /CRM/.../file.webm"
  // Путь может содержать пробелы (названия городов, адреса)
  const msg = h.message || h.description || ''
  const match = msg.match(/— (\/CRM\/.+\.webm)/)
  return match ? match[1] : ''
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('ru-RU', {
    day: 'numeric', month: 'short',
  })
}

function formatMoney(amount) {
  if (!amount) return '0 ₽'
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency', currency: 'RUB', maximumFractionDigits: 0,
  }).format(amount)
}

// Цвет дедлайна
function dlColor(deadline) {
  if (!deadline) return '#888'
  const d = new Date(deadline)
  const now = new Date()
  const diff = Math.ceil((d - now) / (1000 * 60 * 60 * 24))
  if (diff < 0) return '#E74C3C'
  if (diff <= 7) return '#F39C12'
  return '#27AE60'
}

// Дней до дедлайна
function daysLeft(deadline) {
  if (!deadline) return ''
  const d = new Date(deadline)
  const now = new Date()
  const diff = Math.ceil((d - now) / (1000 * 60 * 60 * 24))
  if (diff < 0) return `просрочен на ${Math.abs(diff)} дн.`
  if (diff === 0) return 'сегодня'
  return `${diff} дн.`
}

async function reloadData() {
  const cardId = route.params.id
  if (!cardId) return
  const [cardRes, timelineRes, summaryRes, visitsRes] = await Promise.allSettled([
    supervisionApi.getCard(cardId),
    supervisionApi.getTimeline(cardId),
    supervisionApi.getTimelineSummary(cardId),
    supervisionApi.getVisits(cardId),
  ])
  if (cardRes.status === 'fulfilled') card.value = cardRes.value.data
  if (timelineRes.status === 'fulfilled') timeline.value = timelineRes.value.data?.entries || timelineRes.value.data || []
  if (summaryRes.status === 'fulfilled') summary.value = summaryRes.value.data
  if (visitsRes.status === 'fulfilled') visits.value = visitsRes.value.data || []
  console.log('[Supervision] Visits loaded:', visits.value.length, visits.value.map(v => v.visit_type))

  // Оплаты надзора
  try {
    const { api: ax } = await import('src/boot/axios')
    const { data } = await ax.get(`/api/v1/payments/by-supervision-card/${cardId}`)
    svPayments.value = data || []
  } catch { svPayments.value = [] }

  // История надзора
  try { const { data } = await supervisionApi.getHistory(cardId); svHistory.value = data || [] } catch { svHistory.value = [] }

  // Файлы: закупки (stage=supervision) и отчёты выездов (stage=supervision_reports)
  const cid = card.value?.contract_id
  if (cid) {
    try { const { data } = await filesApi.getContractFiles(cid, 'supervision'); svFilesSupervision.value = data || [] } catch { svFilesSupervision.value = [] }
    try { const { data } = await filesApi.getContractFiles(cid, 'supervision_reports'); svFilesReports.value = data || [] } catch { svFilesReports.value = [] }

    // Файлы по стадиям закупок — загружаем для каждого stage_code
    await loadStageFiles(cid)
  }

  // Исполнители
  const names = []
  if (card.value?.dan_name) names.push({ label: `${card.value.dan_name} (ДАН)`, value: card.value.dan_id })
  if (card.value?.senior_manager_name) names.push({ label: `${card.value.senior_manager_name} (Ст. менеджер)`, value: card.value.senior_manager_id })
  if (card.value?.studio_director_name) names.push({ label: `${card.value.studio_director_name} (Руководитель)`, value: card.value.studio_director_id })
  executorOptions.value = names
  executorNameOptions.value = names.map(n => n.label.split(' (')[0])
}

// Загрузка файлов по стадиям закупок
async function loadStageFiles(contractId) {
  const stages = {}
  try {
    const { data: allFiles } = await filesApi.getContractFiles(contractId, 'supervision_stage')
    if (allFiles && allFiles.length > 0) {
      for (const f of allFiles) {
        const code = f.stage_code || f.stage || 'unknown'
        if (!stages[code]) stages[code] = []
        stages[code].push(f)
      }
    }
  } catch { /* нет файлов по стадиям */ }
  svFilesStages.value = stages
}

// Загрузка файлов для конкретной стадии закупки
function uploadStageFile(stageCode) {
  uploadStageCode.value = stageCode
  stageUploadFiles.value = null
  showStageFileUpload.value = true
}

async function doUploadStageFiles() {
  if (!stageUploadFiles.value?.length || !card.value) return
  stageUploading.value = true
  try {
    const { api: ax } = await import('src/boot/axios')
    const cid = card.value.contract_id
    let contractFolder = ''
    if (cid) {
      try {
        const { data: c } = await import('src/services/api').then(m => m.contractsApi.getById(cid))
        contractFolder = (c?.yandex_folder_path || '').replace(/^disk:/, '')
      } catch {}
    }

    const stageLabel = uploadStageLabel.value || uploadStageCode.value
    const subFolder = `Авторский надзор/Закупки/${stageLabel}`
    const folder = contractFolder ? `${contractFolder}/${subFolder}` : `/CRM/Надзор/${card.value.contract_number || card.value.id}/${subFolder}`

    for (const file of stageUploadFiles.value) {
      const yp = `${folder}/${file.name}`
      const uploadRes = await filesApi.upload(file, yp)
      let publicLink = uploadRes.data?.public_link || ''

      // Получаем публичную ссылку если нет
      if (!publicLink) {
        try {
          const { data: linkData } = await filesApi.getPublicLink(yp)
          publicLink = linkData.public_link || ''
        } catch {}
      }

      if (cid) {
        await ax.post('/api/v1/files/', {
          contract_id: cid,
          stage: 'supervision_stage',
          stage_code: uploadStageCode.value,
          file_type: file.type?.includes('image') ? 'image' : 'pdf',
          public_link: publicLink,
          yandex_path: yp,
          file_name: file.name,
          file_order: 0,
          variation: 1,
        })
      }
    }

    $q.notify({ type: 'positive', message: `Загружено ${stageUploadFiles.value.length} файл(ов)` })
    showStageFileUpload.value = false
    stageUploadFiles.value = null
    // Принудительное обновление файлов стадий
    if (card.value?.contract_id) await loadStageFiles(card.value.contract_id)
    await reloadData()
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка загрузки файлов' })
  } finally {
    stageUploading.value = false
  }
}

async function handlePause() {
  $q.dialog({
    title: 'Приостановить',
    message: 'Укажите причину приостановки',
    prompt: { model: '', type: 'text' },
    cancel: true,
  }).onOk(async (reason) => {
    try {
      await supervisionApi.pause(card.value.id, reason || 'Без причины')
      $q.notify({ type: 'positive', message: 'Карточка приостановлена' })
      await reloadData()
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
    }
  })
}

async function handleResume() {
  try {
    await supervisionApi.resume(card.value.id)
    $q.notify({ type: 'positive', message: 'Карточка возобновлена' })
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

function exportTimelinePDF() {
  if (!card.value) return
  const url = `https://crm.festivalcolor.ru/api/v1/supervision-timeline/${card.value.id}/export/pdf`
  window.open(url, '_blank')
}

function exportTimelineExcel() {
  if (!card.value) return
  const url = `https://crm.festivalcolor.ru/api/v1/supervision-timeline/${card.value.id}/export/excel`
  window.open(url, '_blank')
}

function editTimelineEntry(entry) {
  editEntry.value = { ...entry }
  showEditEntry.value = true
}

async function saveTimelineEntry() {
  if (!editEntry.value || !card.value) return
  try {
    await supervisionApi.updateTimelineEntry(card.value.id, editEntry.value.stage_code, {
      plan_date: editEntry.value.plan_date,
      actual_date: editEntry.value.actual_date,
      budget_planned: editEntry.value.budget_planned,
      budget_actual: editEntry.value.budget_actual,
      supplier: editEntry.value.supplier,
      commission: editEntry.value.commission || null,
      status: editEntry.value.status,
      notes: editEntry.value.notes,
      executor: editEntry.value.executor,
    })
    $q.notify({ type: 'positive', message: 'Стадия обновлена' })
    showEditEntry.value = false
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

async function saveVisit() {
  if (!visitForm.value.visit_date) {
    $q.notify({ type: 'warning', message: 'Заполните дату выезда' })
    return
  }
  if (visitForm.value.visit_type === 'К поставщику' && !visitForm.value.stage_code) {
    $q.notify({ type: 'warning', message: 'Для выезда к поставщику укажите стадию' })
    return
  }
  try {
    const stageLabel = stageCodesForVisit.find(s => s.value === visitForm.value.stage_code)?.label || ''
    const isEditing = !!editingVisitId.value
    const payload = {
      stage_code: visitForm.value.stage_code,
      stage_name: stageLabel,
      visit_date: visitForm.value.visit_date,
      visit_type: visitForm.value.visit_type || 'На объект',
      executor_name: visitForm.value.executor_name || '',
      notes: visitForm.value.notes,
    }
    if (isEditing) {
      const { api: ax } = await import('src/boot/axios')
      await ax.patch(`/api/v1/supervision-visits/${editingVisitId.value}`, payload)
      editingVisitId.value = null
    } else {
      await supervisionApi.createVisit(card.value.id, payload)
    }
    $q.notify({ type: 'positive', message: isEditing ? 'Выезд обновлён' : 'Выезд добавлен' })
    showAddVisit.value = false
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

async function setActualDate(visit) {
  const today = new Date().toISOString().split('T')[0]
  $q.dialog({
    title: 'Фактическая дата выезда',
    prompt: { model: today, type: 'date' },
    cancel: { label: 'Отмена', flat: true, noCaps: true },
    ok: { label: 'Сохранить', noCaps: true, color: 'positive' },
  }).onOk(async (val) => {
    try {
      const { api: ax } = await import('src/boot/axios')
      await ax.patch(`/api/v1/supervision-visits/${visit.id}`, { actual_date: val })
      visit.actual_date = val
      $q.notify({ type: 'positive', message: 'Факт. дата установлена' })
      await reloadData()
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
    }
  })
}

function editVisit(visit) {
  visitForm.value = {
    visit_date: visit.visit_date || '',
    stage_code: visit.stage_code || '',
    notes: visit.notes || '',
    executor_name: visit.executor_name || '',
    visit_type: visit.visit_type || 'На объект',
  }
  editingVisitId.value = visit.id
  showAddVisit.value = true
}

async function uploadVisitReport(visit) {
  const input = document.createElement('input')
  input.type = 'file'
  input.multiple = true
  input.accept = '.pdf,.doc,.docx,.xls,.xlsx'
  input.onchange = async (e) => {
    for (const file of e.target.files) {
      try {
        const fd = new FormData()
        fd.append('file', file)
        fd.append('visit_id', visit.id)
        fd.append('file_type', 'report')
        const { api: ax } = await import('src/boot/axios')
        await ax.post('/api/v1/supervision-visits/upload-file', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      } catch (err) { $q.notify({ type: 'negative', message: 'Ошибка загрузки: ' + (err.response?.data?.detail || err.message) }) }
    }
    $q.notify({ type: 'positive', message: 'Файлы загружены' })
    await reloadData()
  }
  input.click()
}

async function uploadVisitPhoto(visit) {
  const input = document.createElement('input')
  input.type = 'file'
  input.multiple = true
  input.accept = 'image/*'
  input.onchange = async (e) => {
    for (const file of e.target.files) {
      try {
        const fd = new FormData()
        fd.append('file', file)
        fd.append('visit_id', visit.id)
        fd.append('file_type', 'photo')
        const { api: ax } = await import('src/boot/axios')
        await ax.post('/api/v1/supervision-visits/upload-file', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      } catch (err) { $q.notify({ type: 'negative', message: 'Ошибка загрузки: ' + (err.response?.data?.detail || err.message) }) }
    }
    $q.notify({ type: 'positive', message: 'Фото загружены' })
    await reloadData()
  }
  input.click()
}

async function deleteVisitFile(visit, file) {
  try {
    const { api: ax } = await import('src/boot/axios')
    await ax.delete(`/api/v1/files/${file.id}`)
    $q.notify({ type: 'positive', message: 'Файл удалён' })
    await reloadData()
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
}

async function deleteVisit(visit) {
  $q.dialog({
    title: 'Удалить выезд?',
    message: `${formatDate(visit.visit_date)} — ${visit.stage_name || ''}`,
    cancel: { label: 'Нет', flat: true, noCaps: true },
    ok: { label: 'Да', noCaps: true, color: 'negative' },
  }).onOk(async () => {
    try {
      const { api: ax } = await import('src/boot/axios')
      await ax.delete(`/api/v1/supervision-visits/${visit.id}`)
      $q.notify({ type: 'positive', message: 'Выезд удалён' })
      await reloadData()
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
    }
  })
}

function takePhoto() { cameraInput.value?.click() }
function uploadPhoto() { fileInput.value?.click() }

async function handlePhotoCapture(event) {
  const file = event.target.files?.[0]
  if (file) await uploadFileWithStage(file, 'supervision_reports')
  event.target.value = ''
}

async function handleFileUpload(event) {
  const file = event.target.files?.[0]
  if (file) await uploadFileWithStage(file, 'supervision_reports')
  event.target.value = ''
}

async function uploadFile(file) {
  if (!file) return
  try {
    $q.loading.show({ message: 'Загрузка...' })
    const { api: ax } = await import('src/boot/axios')
    const cid = card.value.contract_id
    let contractFolder = ''
    if (cid) {
      try {
        const { data: c } = await import('src/services/api').then(m => m.contractsApi.getById(cid))
        contractFolder = (c?.yandex_folder_path || '').replace(/^disk:/, '')
      } catch {}
    }
    const supervisionFolder = contractFolder ? `${contractFolder}/Авторский надзор` : `/CRM/Надзор/${card.value.contract_number || card.value.id}`
    const yandexPath = `${supervisionFolder}/${file.name}`
    const uploadRes = await filesApi.upload(file, yandexPath)
    const publicLink = uploadRes.data?.public_link || ''
    if (cid) {
      await ax.post('/api/v1/files/', {
        contract_id: cid, stage: 'supervision',
        file_type: file.type?.includes('image') ? 'image' : 'pdf',
        public_link: publicLink, yandex_path: yandexPath,
        file_name: file.name, file_order: 0, variation: 1,
      })
      try {
        const { data: folderLink } = await filesApi.getPublicLink(supervisionFolder)
        if (folderLink.public_link) {
          const { contractsApi: cApi } = await import('src/services/api')
          await cApi.update(cid, { additional_agreement_link: folderLink.public_link })
        }
      } catch {}
      try { await ax.post(`/api/v1/files/scan/${cid}?scope=supervision`) } catch {}
    }
    $q.notify({ type: 'positive', message: 'Файл загружен' })
    await reloadData()
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка загрузки' })
  } finally {
    $q.loading.hide()
  }
}

function historyIcon(type) {
  const m = { pause: 'pause_circle', resume: 'play_circle', card_moved: 'swap_horiz', assignment_change: 'person', stage_completed: 'check_circle', payment_created: 'payments', auto_resume: 'refresh', note: 'note', voice_note: 'mic' }
  return m[type] || 'history'
}
function historyColor(type) {
  const m = { pause: 'warning', resume: 'positive', card_moved: 'primary', stage_completed: 'positive', payment_created: 'info', note: 'grey-7', voice_note: 'orange' }
  return m[type] || 'grey-6'
}
function historyLabel(type) {
  const m = { pause: 'Пауза', resume: 'Возобновление', card_moved: 'Перемещение', assignment_change: 'Назначение', stage_completed: 'Стадия завершена', payment_created: 'Оплата', auto_resume: 'Авто-возобновление', note: 'Заметка', voice_note: 'Голос. заметка' }
  return m[type] || type || ''
}

function uploadNadzorFile() { nadzorFileInput.value?.click() }
async function handleNadzorFileUpload(event) {
  const file = event.target.files?.[0]
  if (file) await uploadFileWithStage(file, 'supervision')
  event.target.value = ''
}

function uploadReport() { reportFileInput.value?.click() }
async function handleReportUpload(event) {
  const file = event.target.files?.[0]
  if (file) await uploadFileWithStage(file, 'supervision_reports')
  event.target.value = ''
}

async function uploadFileWithStage(file, stage) {
  if (!file) return
  try {
    $q.loading.show({ message: 'Загрузка...' })
    const { api: ax } = await import('src/boot/axios')
    const cid = card.value.contract_id
    let contractFolder = ''
    if (cid) {
      try { const { data: c } = await import('src/services/api').then(m => m.contractsApi.getById(cid)); contractFolder = (c?.yandex_folder_path || '').replace(/^disk:/, '') } catch {}
    }
    const subFolder = stage === 'supervision_reports' ? 'Авторский надзор/Отчёты' : 'Авторский надзор'
    const folder = contractFolder ? `${contractFolder}/${subFolder}` : `/CRM/Надзор/${card.value.contract_number || card.value.id}`
    const yp = `${folder}/${file.name}`
    const uploadRes = await filesApi.upload(file, yp)
    const publicLink = uploadRes.data?.public_link || ''
    if (cid) {
      await ax.post('/api/v1/files/', { contract_id: cid, stage, file_type: file.type?.includes('image') ? 'image' : 'pdf', public_link: publicLink, yandex_path: yp, file_name: file.name, file_order: 0, variation: 1 })
      try { await ax.post(`/api/v1/files/scan/${cid}?scope=supervision`) } catch {}
    }
    $q.notify({ type: 'positive', message: 'Файл загружен' })
    await reloadData()
  } catch { $q.notify({ type: 'negative', message: 'Ошибка загрузки' }) }
  finally { $q.loading.hide() }
}

async function loadReassignOptions() {
  try {
    const { data } = await employeesApi.getList()
    const active = (data || []).filter(e => e.status === 'активный')
    danOptions.value = active.filter(e => e.position === 'ДАН' || e.position === 'Руководитель студии').map(e => ({ id: e.id, label: e.full_name }))
    smOptions.value = active.filter(e => e.position === 'Старший менеджер проектов' || e.position === 'Руководитель студии').map(e => ({ id: e.id, label: e.full_name }))
  } catch {}
}

async function reassignDan() {
  if (!newDanId.value || !card.value?.id) return
  try {
    const oldDanId = card.value.dan_id
    await supervisionApi.updateCard(card.value.id, { dan_id: newDanId.value })
    // Двойная запись оплат ДАН
    if (oldDanId && oldDanId !== newDanId.value && card.value.contract_id) {
      try {
        const { data: payments } = await paymentsApi.getList({ contract_id: card.value.contract_id })
        const oldPayments = (payments || []).filter(p => p.employee_id === oldDanId && p.role === 'ДАН' && !p.reassigned)
        for (const op of oldPayments) {
          await paymentsApi.update(op.id, { reassigned: true })
          await paymentsApi.create({ contract_id: card.value.contract_id, employee_id: newDanId.value, role: 'ДАН', payment_type: op.payment_type, calculated_amount: op.final_amount, final_amount: op.final_amount, report_month: op.report_month })
        }
      } catch (e) { console.warn('Ошибка переназначения оплат ДАН:', e) }
    }
    $q.notify({ type: 'positive', message: 'ДАН переназначен' })
    showReassignDan.value = false
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

async function reassignSM() {
  if (!newSMId.value || !card.value?.id) return
  try {
    await supervisionApi.updateCard(card.value.id, { senior_manager_id: newSMId.value })
    $q.notify({ type: 'positive', message: 'Ст. менеджер переназначен' })
    showReassignSM.value = false
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

async function handleCompleteStage() {
  try {
    await supervisionApi.completeStage(card.value.id)
    // Автоперемещение на следующую стадию
    const columns = ['Чертежи', 'Комплектация', 'Черновые работы', 'Чистовые работы', 'Декор', 'Выполненный проект']
    const currentIdx = columns.indexOf(card.value.column_name)
    if (currentIdx >= 0 && currentIdx < columns.length - 1) {
      await supervisionApi.moveCard(card.value.id, columns[currentIdx + 1])
    }
    $q.notify({ type: 'positive', message: 'Стадия завершена, карточка перемещена' })
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

async function doMoveSupervision() {
  if (!moveTargetColumn.value) return
  try {
    await supervisionApi.moveCard(card.value.id, moveTargetColumn.value)
    $q.notify({ type: 'positive', message: `Перемещено: ${moveTargetColumn.value}` })
    showMoveDialog.value = false
    moveTargetColumn.value = null
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка перемещения' })
  }
}

async function submitDanWork() {
  try {
    await supervisionApi.updateCard(card.value.id, { dan_completed: true })
    $q.notify({ type: 'positive', message: 'Работа сдана' })
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

async function acceptDanWork() {
  try {
    await supervisionApi.updateCard(card.value.id, { dan_completed: false })
    await supervisionApi.completeStage(card.value.id)
    $q.notify({ type: 'positive', message: 'Работа принята, стадия завершена' })
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

// Голосовая заметка
async function onVoiceRecorded({ url, duration, path }) {
  try {
    const durationStr = `${Math.floor(duration / 60)}:${String(duration % 60).padStart(2, '0')}`
    await supervisionApi.addHistory(card.value.id, {
      entry_type: 'voice_note',
      message: `Голосовая заметка (${durationStr}) — ${path}`,
    })
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Ошибка сохранения записи в историю' })
  }
}

// Текстовая заметка
async function addTextNote() {
  if (!noteText.value?.trim()) return
  try {
    await supervisionApi.addHistory(card.value.id, {
      entry_type: 'note',
      message: noteText.value.trim(),
    })
    $q.notify({ type: 'positive', message: 'Заметка добавлена' })
    noteText.value = ''
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Ошибка сохранения заметки' })
  }
}

function addVisitToCalendar(visit) {
  if (!visit?.visit_date) return
  const stageName = visit.stage_name?.replace(/^Стадия \d+: /, '') || ''
  addToCalendar({
    title: `Надзор: ${card.value?.address || ''} — выезд`,
    description: `Выезд на объект${stageName ? '. Стадия: ' + stageName : ''}${visit.notes ? '. ' + visit.notes : ''}`,
    startDate: visit.visit_date,
    location: card.value?.address || '',
    reminder: 1440,
  }, $q)
}

async function doAddHistory() {
  if (!historyNote.value) return
  try {
    await supervisionApi.addHistory(card.value.id, { entry_type: 'note', message: historyNote.value })
    $q.notify({ type: 'positive', message: 'Запись добавлена' })
    showAddHistoryDlg.value = false
    historyNote.value = ''
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

// === Telegram-чат надзора ===

// Ленивая загрузка чата при переключении на вкладку
watch(activeTab, (val) => {
  router.replace({ query: { ...route.query, tab: val } })
  if (val === 'chat' && !svChatData.value && !svChatLoading.value) loadSvChat()
  if (val === 'sv-chat') svChatTabVisited.value = true
})

function tgDeepLink(link) {
  if (!link) return '#'
  const m = link.match(/t\.me\/(?:joinchat\/|\+)([A-Za-z0-9_-]+)/)
  if (m) return `tg://join?invite=${m[1]}`
  return link
}

async function loadSvChat() {
  if (!card.value?.id) return
  svChatLoading.value = true
  try {
    const { api: ax } = await import('src/boot/axios')
    const resp = await ax.get(`/api/v1/messenger/chats/by-supervision/${card.value.id}`, { validateStatus: s => s < 500 })
    if (resp.data && resp.data.chat) {
      svChatData.value = resp.data.chat
      svChatMembers.value = resp.data.members || []
    } else {
      svChatData.value = null
      svChatMembers.value = []
    }
  } catch { svChatData.value = null }
  svChatLoading.value = false
}

function openCreateSvChatDlg() {
  const city = (card.value?.city || '').replace(/_/g, '-')
  const address = (card.value?.address || '').replace(/_/g, '-')
  newSvChatTitle.value = ['АН', city, address].filter(Boolean).join('-')
  showCreateSvChatDlg.value = true
}

async function createSvChat() {
  if (!card.value?.id) return
  svChatCreating.value = true
  showCreateSvChatDlg.value = false
  try {
    const c = card.value
    const memberFields = [
      { key: 'dan_id', role: 'ДАН' },
      { key: 'senior_manager_id', role: 'Старший менеджер' },
      { key: 'studio_director_id', role: 'Руководитель студии' },
    ]
    const members = memberFields
      .filter(m => c[m.key])
      .map(m => ({ member_type: 'employee', member_id: c[m.key], role_in_project: m.role }))

    const payload = {
      supervision_card_id: c.id,
      chat_title: newSvChatTitle.value.trim() || undefined,
      members,
    }
    const { data } = await messengerApi.createSupervisionChat(payload)
    if (data && data.chat) {
      svChatData.value = data.chat
      svChatMembers.value = data.members || []
    }
    $q.notify({ type: 'positive', message: 'Чат создан' })
    await loadSvChat()
  } catch (e) {
    const msg = e?.response?.data?.detail || 'Ошибка создания чата'
    $q.notify({ type: 'negative', message: msg })
  }
  svChatCreating.value = false
}

async function doAddSvMember() {
  if (!svChatData.value?.id || !addSvMemberEmployeeId.value) return
  addSvMemberLoading.value = true
  try {
    const { api: ax } = await import('src/boot/axios')
    await ax.post(`/api/v1/messenger/chats/${svChatData.value.id}/add-member`, {
      member_type: 'employee',
      member_id: addSvMemberEmployeeId.value,
    })
    $q.notify({ type: 'positive', message: 'Участник добавлен' })
    showAddSvMemberDlg.value = false
    addSvMemberEmployeeId.value = null
    await loadSvChat()
  } catch (e) {
    $q.notify({ type: 'negative', message: e?.response?.data?.detail || 'Ошибка добавления' })
  }
  addSvMemberLoading.value = false
}

async function confirmDeleteSvChat() {
  if (!svChatData.value?.id) return
  $q.dialog({ title: 'Удалить чат?', message: 'Telegram-группа будет удалена', cancel: true, persistent: false })
    .onOk(async () => {
      try {
        await messengerApi.deleteChat(svChatData.value.id)
        svChatData.value = null
        svChatMembers.value = []
        $q.notify({ type: 'positive', message: 'Чат удалён' })
      } catch { $q.notify({ type: 'negative', message: 'Ошибка удаления' }) }
    })
}

async function doSendSvMessage() {
  if (!svChatData.value?.id || !svChatMsgText.value?.trim()) return
  svChatActionLoading.value = true
  try {
    await messengerApi.sendMessage(svChatData.value.id, { text: svChatMsgText.value.trim() })
    $q.notify({ type: 'positive', message: 'Сообщение отправлено' })
    svChatMsgText.value = ''
    showSvSendMsgDlg.value = false
  } catch { $q.notify({ type: 'negative', message: 'Ошибка отправки' }) }
  svChatActionLoading.value = false
}

async function loadSvScriptsAndShow() {
  try {
    const { data } = await messengerApi.getScripts({ supervision_card_id: card.value?.id })
    svChatScripts.value = data || []
  } catch { svChatScripts.value = [] }
  showSvScriptsDlg.value = true
}

async function doTriggerSvScript(script) {
  if (!svChatData.value?.id) return
  try {
    await messengerApi.triggerScript(script.id, svChatData.value.id)
    $q.notify({ type: 'positive', message: `Скрипт «${script.name || script.code}» запущен` })
    showSvScriptsDlg.value = false
  } catch { $q.notify({ type: 'negative', message: 'Ошибка запуска скрипта' }) }
}

onMounted(async () => {
  const cardId = route.params.id
  if (!cardId) return

  try {
    const [cardRes, timelineRes, summaryRes, visitsRes] = await Promise.allSettled([
      supervisionApi.getCard(cardId),
      supervisionApi.getTimeline(cardId),
      supervisionApi.getTimelineSummary(cardId),
      supervisionApi.getVisits(cardId),
    ])

    if (cardRes.status === 'fulfilled') {
      card.value = cardRes.value.data
      // Загружаем yandex_folder_path из контракта для голосовых заметок
      if (card.value?.contract_id) {
        try {
          const { contractsApi } = await import('src/services/api')
          const { data: ct } = await contractsApi.getById(card.value.contract_id)
          svContractYdPath.value = (ct?.yandex_folder_path || '').replace(/^disk:/, '')
        } catch {}
      }
    }
    if (timelineRes.status === 'fulfilled') {
      timeline.value = timelineRes.value.data?.entries || timelineRes.value.data || []
    }
    if (summaryRes.status === 'fulfilled') summary.value = summaryRes.value.data
    if (visitsRes.status === 'fulfilled') visits.value = visitsRes.value.data || []
  } finally {
    loading.value = false
  }

  // Дополнительные данные (не блокируют основную загрузку)
  reloadData()
  // Чат — грузим сразу, чтобы данные были готовы при открытии вкладки
  loadSvChat()

  // Блокировка карточки при редактировании
  try {
    const { data: existing } = await locksApi.check('supervision_card', cardId)
    if (existing?.locked_by && existing.locked_by !== authStore.user?.id) {
      $q.notify({ type: 'warning', message: `Карточка редактируется: ${existing.locked_by_name || 'другой пользователь'}`, timeout: 5000 })
    } else {
      const { data } = await locksApi.lock('supervision_card', cardId)
      if (data?.lock_id || data?.id) svLockId.value = data.lock_id || data.id
    }
  } catch { /* блокировки опциональны */ }
})

const svLockId = ref(null)
onBeforeUnmount(async () => {
  if (svLockId.value) {
    try { await locksApi.unlock(svLockId.value) } catch {}
  }
})
</script>
