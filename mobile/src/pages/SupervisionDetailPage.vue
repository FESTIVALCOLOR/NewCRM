<template>
  <q-page padding>
    <div v-if="loading" class="q-pa-md">
      <q-skeleton type="rect" height="150px" class="q-mb-md" />
      <q-skeleton type="text" width="70%" />
      <q-skeleton type="text" width="50%" />
    </div>

    <template v-else-if="card">
      <!-- Шапка -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="row items-center justify-between q-mb-xs">
            <div class="text-h6 text-weight-bold">{{ card.contract_number }}</div>
            <q-badge
              :color="card.is_paused ? 'warning' : 'positive'"
              :label="card.is_paused ? 'Приостановлено' : card.column_name"
              style="padding: 5px 8px; font-size: 11px"
            />
          </div>
          <div class="text-body1 q-mb-xs">{{ card.address }}</div>
          <div class="row items-center q-gutter-xs text-caption q-mb-xs" style="color: #888">
            <span v-if="card.area">{{ card.area }} м²</span>
            <span v-if="card.city"><q-icon name="location_on" size="12px" /> {{ card.city }}</span>
            <span v-if="card.project_type">{{ card.project_type }}</span>
            <span v-if="card.project_subtype"> · {{ card.project_subtype }}</span>
          </div>
          <div v-if="card.agent_type" class="q-mb-xs">
            <q-badge :style="{ background: agentColor, padding: '4px 8px', fontSize: '11px' }" text-color="white" :label="card.agent_type" />
          </div>
          <div class="row q-gutter-md text-caption" style="color: #888">
            <span v-if="card.start_date"><q-icon name="play_arrow" size="14px" /> Начало: {{ formatDate(card.start_date) }}</span>
            <span v-if="card.deadline"><q-icon name="flag" size="14px" :style="{ color: dlColor(card.deadline) }" /> Дедлайн: {{ formatDate(card.deadline) }}</span>
          </div>
          <div v-if="card.dan_completed" class="q-mt-xs">
            <q-badge color="positive" label="Работа сдана ДАН" style="padding: 4px 8px" />
          </div>
        </q-card-section>
      </q-card>

      <!-- Команда -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold">Команда</div>
        </q-card-section>
        <q-list dense>
          <q-item v-if="card.dan_name || can('supervision.assign_executor')">
            <q-item-section avatar>
              <q-avatar size="32px" color="orange-2" text-color="orange-8">{{ card.dan_name ? card.dan_name[0] : '?' }}</q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ card.dan_name || 'Не назначен' }}</q-item-label>
              <q-item-label caption>ДАН</q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="row q-gutter-xs">
                <q-icon v-if="card.dan_completed" name="check_circle" color="positive" />
                <q-btn v-if="can('supervision.assign_executor')" flat round dense size="xs" icon="edit" color="grey-7" @click="showReassignDan = true"><q-tooltip>Переназначить</q-tooltip></q-btn>
              </div>
            </q-item-section>
          </q-item>
          <q-item v-if="card.senior_manager_name || can('supervision.assign_executor')">
            <q-item-section avatar>
              <q-avatar size="32px" color="blue-2" text-color="blue-8">{{ card.senior_manager_name ? card.senior_manager_name[0] : '?' }}</q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ card.senior_manager_name || 'Не назначен' }}</q-item-label>
              <q-item-label caption>Ст. менеджер</q-item-label>
            </q-item-section>
            <q-item-section side v-if="can('supervision.assign_executor')">
              <q-btn flat round dense size="xs" icon="edit" color="grey-7" @click="showReassignSM = true"><q-tooltip>Переназначить</q-tooltip></q-btn>
            </q-item-section>
          </q-item>
          <q-item v-if="card.studio_director_name">
            <q-item-section avatar>
              <q-avatar size="32px" color="purple-2" text-color="purple-8">{{ card.studio_director_name[0] }}</q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ card.studio_director_name }}</q-item-label>
              <q-item-label caption>Руководитель студии</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Таблица сроков (стадии) -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="row items-center justify-between">
            <div class="text-subtitle2 text-weight-bold">Стадии закупок</div>
            <div class="row q-gutter-xs">
              <q-btn flat dense size="xs" icon="picture_as_pdf" color="grey-7" @click="exportTimelinePDF">
                <q-tooltip>Экспорт PDF</q-tooltip>
              </q-btn>
              <q-btn flat dense size="xs" icon="table_chart" color="grey-7" @click="exportTimelineExcel">
                <q-tooltip>Экспорт Excel</q-tooltip>
              </q-btn>
              <div class="text-caption text-grey-7" v-if="summary">{{ summary.total_site_visits }} выездов</div>
            </div>
          </div>
        </q-card-section>

        <q-list v-if="timeline.length > 0" dense separator>
          <q-item v-for="entry in timeline" :key="entry.id" clickable v-ripple @click="editTimelineEntry(entry)">
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
              <q-item-label caption v-if="entry.supplier" style="color: #888">{{ entry.supplier }}</q-item-label>
              <q-item-label caption v-if="entry.budget_planned > 0" style="color: #888">
                Бюджет: {{ formatMoney(entry.budget_actual || 0) }} / {{ formatMoney(entry.budget_planned) }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-badge :color="stageColor(entry.status)" :label="entry.status" dense />
            </q-item-section>
          </q-item>
        </q-list>

        <q-list v-else dense separator>
          <q-item v-for="s in defaultStages" :key="s.code" clickable v-ripple @click="initAndEditStage(s)">
            <q-item-section avatar><q-icon name="radio_button_unchecked" color="grey-4" size="20px" /></q-item-section>
            <q-item-section><q-item-label class="text-weight-medium">{{ s.name }}</q-item-label></q-item-section>
            <q-item-section side><q-badge color="grey-4" label="Не начато" dense /></q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Бюджет -->
      <q-card class="is-card q-mb-md" v-if="summary && summary.total_budget_planned > 0">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm">Бюджет</div>
          <div class="row q-col-gutter-sm">
            <div class="col-6">
              <div class="text-caption text-grey-7">Запланировано</div>
              <div class="text-weight-bold">{{ formatMoney(summary.total_budget_planned) }}</div>
            </div>
            <div class="col-6">
              <div class="text-caption text-grey-7">Фактически</div>
              <div class="text-weight-bold">{{ formatMoney(summary.total_budget_actual) }}</div>
            </div>
            <div class="col-6">
              <div class="text-caption text-grey-7">Экономия</div>
              <div class="text-weight-bold text-positive">{{ formatMoney(summary.total_savings) }}</div>
            </div>
            <div class="col-6">
              <div class="text-caption text-grey-7">Дефекты</div>
              <div class="text-weight-bold">
                {{ summary.total_defects_resolved }}/{{ summary.total_defects_found }}
              </div>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Выезды -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold">Выезды на объект</div>
        </q-card-section>

        <q-list v-if="visits.length > 0" dense separator>
          <q-item v-for="visit in visits" :key="visit.id">
            <q-item-section avatar>
              <q-icon name="place" color="blue" size="20px" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ formatDate(visit.visit_date) }}</q-item-label>
              <q-item-label caption>
                {{ visit.stage_name?.replace(/^Стадия \d+: /, '') }}
              </q-item-label>
              <q-item-label caption v-if="visit.notes" class="text-grey-7">
                {{ visit.notes }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="column items-end q-gutter-xs">
                <span class="text-caption text-grey-7">{{ visit.executor_name }}</span>
                <q-btn flat round dense size="xs" icon="event" color="grey-6" @click.stop="addVisitToCalendar(visit)"><q-tooltip>В календарь</q-tooltip></q-btn>
              </div>
            </q-item-section>
          </q-item>
        </q-list>

        <q-card-section v-else class="text-center text-grey-5 q-py-md">
          Нет выездов
        </q-card-section>
        <q-card-actions>
          <q-btn flat color="positive" icon="add" label="Добавить выезд" no-caps @click="showAddVisit = true" />
        </q-card-actions>

        <!-- Файлы отчётов выездов -->
        <q-separator />
        <q-card-section class="q-pb-xs q-pt-sm">
          <div class="row items-center justify-between" style="flex-wrap: wrap; gap: 4px">
            <div class="text-caption text-weight-bold" style="color: #555">Отчёты и фотофиксация</div>
            <div class="row q-gutter-xs">
              <q-btn v-if="can('supervision.files_upload')" outline dense size="xs" icon="description" label="Отчёт" no-caps color="grey-7" style="border-radius: 4px; padding: 2px 6px" @click="uploadReport" />
              <q-btn v-if="can('supervision.files_upload')" outline dense size="xs" icon="photo_camera" label="Фото" no-caps color="grey-7" style="border-radius: 4px; padding: 2px 6px" @click="takePhoto" />
            </div>
          </div>
        </q-card-section>
        <q-list v-if="svFilesReports.length > 0" dense>
          <q-item v-for="f in svFilesReports" :key="f.id">
            <q-item-section avatar><q-icon :name="f.file_type === 'image' ? 'image' : 'description'" :color="f.file_type === 'image' ? 'blue' : 'orange'" size="18px" /></q-item-section>
            <q-item-section style="min-width: 0"><q-item-label style="font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap"><a :href="f.public_link || '#'" target="_blank" style="color: #1677FF; text-decoration: none">{{ f.file_name }}</a></q-item-label></q-item-section>
          </q-item>
        </q-list>
        <input ref="reportFileInput" type="file" accept=".pdf,.doc,.docx,.xls,.xlsx" style="display:none" @change="handleReportUpload" />
        <input ref="cameraInput" type="file" accept="image/*" capture="environment" style="display:none" @change="handlePhotoCapture" />
        <input ref="fileInput" type="file" accept="image/*,.pdf" style="display:none" @change="handleFileUpload" />
      </q-card>

      <!-- Файлы закупок (счета) — рядом с таблицей закупок -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-xs">
          <div class="row items-center justify-between" style="flex-wrap: wrap; gap: 4px">
            <div class="text-subtitle2 text-weight-bold">Файлы закупок</div>
            <q-btn v-if="can('supervision.files_upload')" outline dense size="xs" icon="upload" label="Загрузить счёт" no-caps color="grey-7" style="border-radius: 4px; padding: 2px 8px" @click="uploadNadzorFile" />
          </div>
        </q-card-section>
        <q-list v-if="svFilesSupervision.length > 0" dense separator>
          <q-item v-for="f in svFilesSupervision" :key="f.id">
            <q-item-section avatar><q-icon name="receipt" color="blue" /></q-item-section>
            <q-item-section style="min-width: 0"><q-item-label style="font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap"><a :href="f.public_link || '#'" target="_blank" style="color: #1677FF; text-decoration: none">{{ f.file_name }}</a></q-item-label></q-item-section>
          </q-item>
        </q-list>
        <q-card-section v-else class="q-py-sm text-center" style="color: #bbb; font-size: 11px">Нет файлов</q-card-section>
        <input ref="nadzorFileInput" type="file" accept=".pdf,.jpg,.jpeg,.png,.xls,.xlsx" style="display:none" @change="handleNadzorFileUpload" />
      </q-card>

      <!-- Диалог добавления выезда -->
      <q-dialog v-model="showAddVisit">
        <q-card style="min-width: 320px">
          <q-card-section><div class="text-subtitle1 text-weight-bold">Новый выезд</div></q-card-section>
          <q-card-section>
            <q-input v-model="visitForm.visit_date" label="Дата выезда" outlined dense type="date" class="q-mb-sm" />
            <q-select v-model="visitForm.stage_code" :options="stageCodesForVisit" label="Стадия" outlined dense emit-value map-options class="q-mb-sm" />
            <q-select v-model="visitForm.executor_name" :options="executorNameOptions" label="Исполнитель (ДАН)" outlined dense emit-value class="q-mb-sm" />
            <q-input v-model="visitForm.notes" label="Заметки" outlined dense type="textarea" autogrow />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn flat label="Отмена" v-close-popup no-caps />
            <q-btn unelevated color="positive" label="Сохранить" no-caps @click="saveVisit" />
          </q-card-actions>
        </q-card>
      </q-dialog>

      <!-- Диалог редактирования стадии -->
      <q-dialog v-model="showEditEntry">
        <q-card style="min-width: 320px">
          <q-card-section><div class="text-subtitle1 text-weight-bold">{{ editEntry?.stage_name }}</div></q-card-section>
          <q-card-section class="q-pt-none" v-if="editEntry">
            <q-input v-model="editEntry.plan_date" label="Плановая дата" outlined dense type="date" class="q-mb-sm" />
            <q-input v-model="editEntry.actual_date" label="Фактическая дата" outlined dense type="date" class="q-mb-sm" />
            <q-input v-model.number="editEntry.budget_planned" label="Бюджет план" outlined dense type="number" prefix="₽" class="q-mb-sm" />
            <q-input v-model.number="editEntry.budget_actual" label="Бюджет факт" outlined dense type="number" prefix="₽" class="q-mb-sm" />
            <q-input v-model="editEntry.supplier" label="Поставщик" outlined dense class="q-mb-sm" />
            <q-select v-model="editEntry.status" :options="['Не начато','В работе','Закуплено','Доставлено','Просрочено']" label="Статус" outlined dense class="q-mb-sm" />
            <q-input v-model="editEntry.notes" label="Заметки" outlined dense type="textarea" autogrow class="q-mb-sm" />
            <q-select v-model="editEntry.executor" :options="executorNameOptions" label="Исполнитель" outlined dense emit-value class="q-mb-sm" />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn flat label="Отмена" v-close-popup no-caps />
            <q-btn unelevated color="accent" text-color="dark" label="Сохранить" no-caps @click="saveTimelineEntry" />
          </q-card-actions>
        </q-card>
      </q-dialog>

      <!-- Диалог переназначения ДАН -->
      <q-dialog v-model="showReassignDan" @show="loadReassignOptions">
        <q-card style="min-width: 320px; border-radius: 10px">
          <q-toolbar style="background: #F39C12; color: white"><q-toolbar-title style="font-size: 14px">Переназначить ДАН</q-toolbar-title><q-btn flat round dense icon="close" color="white" v-close-popup /></q-toolbar>
          <q-card-section>
            <div v-if="card.dan_name" class="q-mb-sm" style="background: #FFF3CD; padding: 8px; border-radius: 4px; font-size: 12px">Текущий: <b>{{ card.dan_name }}</b></div>
            <q-select v-model="newDanId" :options="danOptions" option-value="id" option-label="label" label="Новый ДАН" outlined dense emit-value map-options />
          </q-card-section>
          <q-card-actions align="right"><q-btn flat label="Отмена" v-close-popup no-caps /><q-btn unelevated label="Переназначить" no-caps style="background: #F39C12; color: white; border-radius: 4px" @click="reassignDan" /></q-card-actions>
        </q-card>
      </q-dialog>

      <!-- Диалог переназначения Ст. менеджера -->
      <q-dialog v-model="showReassignSM" @show="loadReassignOptions">
        <q-card style="min-width: 320px; border-radius: 10px">
          <q-toolbar style="background: #3498DB; color: white"><q-toolbar-title style="font-size: 14px">Переназначить Ст. менеджера</q-toolbar-title><q-btn flat round dense icon="close" color="white" v-close-popup /></q-toolbar>
          <q-card-section>
            <div v-if="card.senior_manager_name" class="q-mb-sm" style="background: #D6EAF8; padding: 8px; border-radius: 4px; font-size: 12px">Текущий: <b>{{ card.senior_manager_name }}</b></div>
            <q-select v-model="newSMId" :options="smOptions" option-value="id" option-label="label" label="Новый Ст. менеджер" outlined dense emit-value map-options />
          </q-card-section>
          <q-card-actions align="right"><q-btn flat label="Отмена" v-close-popup no-caps /><q-btn unelevated label="Переназначить" no-caps style="background: #3498DB; color: white; border-radius: 4px" @click="reassignSM" /></q-card-actions>
        </q-card>
      </q-dialog>

      <!-- Telegram-чат -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="row items-center justify-between">
            <div class="text-subtitle2 text-weight-bold">Telegram-чат</div>
            <q-btn v-if="!svChatLoading && !svChatData" flat dense size="xs" icon="add" color="grey-7" @click="createSvChat" :loading="svChatCreating"><q-tooltip>Создать чат</q-tooltip></q-btn>
          </div>
        </q-card-section>

        <div v-if="svChatLoading" class="q-pa-sm text-center"><q-spinner color="grey-5" size="20px" /></div>

        <template v-else-if="svChatData">
          <q-list dense>
            <q-item>
              <q-item-section avatar><q-icon name="chat" color="blue" /></q-item-section>
              <q-item-section>
                <q-item-label style="font-size: 12px; color: #333">{{ svChatData.title || 'Проектный чат' }}</q-item-label>
                <q-item-label caption v-if="svChatData.invite_link">
                  <a :href="svChatData.invite_link" target="_blank" style="color: #1677FF; text-decoration: none; font-size: 11px">Открыть в Telegram</a>
                </q-item-label>
              </q-item-section>
              <q-item-section side><q-badge color="blue-2" text-color="blue-8" :label="`${svChatMembers.length} уч.`" dense /></q-item-section>
            </q-item>
          </q-list>

          <!-- Участники чата -->
          <q-list v-if="svChatMembers.length > 0" dense separator>
            <q-item v-for="member in svChatMembers" :key="member.id || member.user_id">
              <q-item-section avatar>
                <q-avatar size="24px" color="grey-3" text-color="grey-8">{{ (member.name || member.username || '?')[0] }}</q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label style="font-size: 11px">{{ member.name || member.username || 'Неизвестный' }}</q-item-label>
                <q-item-label caption style="font-size: 10px">{{ member.role || 'участник' }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>

          <q-card-section class="q-pt-sm">
            <div class="row q-gutter-sm">
              <q-btn outline dense no-caps icon="send" label="Сообщение" size="xs" color="primary" style="border-radius: 4px; flex: 1" @click="showSvSendMsgDlg = true" />
              <q-btn outline dense no-caps icon="smart_toy" label="Скрипт" size="xs" color="positive" style="border-radius: 4px; flex: 1" @click="loadSvScriptsAndShow" />
              <q-btn outline dense no-caps icon="delete" size="xs" color="negative" style="border-radius: 4px" @click="confirmDeleteSvChat" />
            </div>
          </q-card-section>
        </template>

        <q-card-section v-else class="text-center q-py-sm" style="color: #bbb; font-size: 11px">
          Чат не создан
        </q-card-section>
      </q-card>

      <!-- Действия -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold">Действия</div>
        </q-card-section>
        <q-list>
          <q-item v-if="can('supervision.pause_resume') && !card.is_paused" clickable v-ripple @click="handlePause">
            <q-item-section avatar><q-icon name="pause_circle" color="warning" /></q-item-section>
            <q-item-section>Приостановить</q-item-section>
          </q-item>
          <q-item v-else-if="can('supervision.pause_resume') && card.is_paused" clickable v-ripple @click="handleResume">
            <q-item-section avatar><q-icon name="play_circle" color="positive" /></q-item-section>
            <q-item-section>Возобновить</q-item-section>
          </q-item>
          <q-item v-if="can('supervision.complete_stage')" clickable v-ripple @click="handleCompleteStage">
            <q-item-section avatar><q-icon name="check_circle" color="primary" /></q-item-section>
            <q-item-section>Завершить текущую стадию</q-item-section>
          </q-item>
          <!-- Переместить на стадию -->
          <q-item v-if="can('supervision.move')" clickable v-ripple @click="showMoveDialog = true">
            <q-item-section avatar><q-icon name="swap_horiz" color="grey-7" /></q-item-section>
            <q-item-section>Переместить на стадию</q-item-section>
          </q-item>
          <!-- Сдать работу (ДАН) -->
          <q-item v-if="isDan && !card.dan_completed" clickable v-ripple @click="submitDanWork">
            <q-item-section avatar><q-icon name="check" color="positive" /></q-item-section>
            <q-item-section>Сдать работу</q-item-section>
          </q-item>
          <!-- Принять работу (менеджер) -->
          <q-item v-if="can('supervision.complete_stage') && card.dan_completed" clickable v-ripple @click="acceptDanWork">
            <q-item-section avatar><q-icon name="thumb_up" color="positive" /></q-item-section>
            <q-item-section>Принять работу ДАН</q-item-section>
          </q-item>
          <!-- Добавить запись в историю -->
          <q-item clickable v-ripple @click="showAddHistoryDlg = true">
            <q-item-section avatar><q-icon name="note_add" color="grey-7" /></q-item-section>
            <q-item-section>Добавить запись</q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Оплаты надзора -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold">Оплаты надзора</div></q-card-section>
        <q-list v-if="svPayments.length > 0" dense separator>
          <q-item v-for="p in svPayments" :key="p.id" :style="p.is_paid ? { background: '#E8F5E9' } : {}">
            <q-item-section>
              <q-item-label style="font-size: 12px">{{ p.employee_name || 'Не указан' }}</q-item-label>
              <q-item-label caption>{{ p.role || '' }} {{ p.stage_name ? `· ${p.stage_name}` : '' }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="text-weight-bold" :style="{ color: p.is_paid ? '#27AE60' : '#333' }">{{ formatMoney(p.final_amount || p.amount || 0) }}</div>
              <div class="text-caption" style="color: #888">{{ p.is_paid ? 'оплачено' : p.payment_status === 'to_pay' ? 'к оплате' : 'в работе' }}</div>
            </q-item-section>
          </q-item>
        </q-list>
        <q-card-section v-else class="text-center" style="color: #999; font-size: 12px">Нет оплат</q-card-section>
      </q-card>

      <!-- История надзора -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="row items-center justify-between">
            <div class="text-subtitle2 text-weight-bold">История</div>
            <VoiceRecorder :yandex-folder-path="card?.yandex_folder_path || ''" @recorded="onVoiceRecorded" />
          </div>
        </q-card-section>
        <q-list v-if="svHistory.length > 0" dense separator>
          <q-item v-for="h in svHistory" :key="h.id">
            <q-item-section avatar><q-icon :name="historyIcon(h.entry_type)" :color="historyColor(h.entry_type)" size="18px" /></q-item-section>
            <q-item-section>
              <q-item-label style="font-size: 12px; color: #333">{{ h.message || h.description || '' }}</q-item-label>
              <q-item-label caption style="color: #888">
                <span v-if="h.entry_type" style="font-weight: bold">{{ historyLabel(h.entry_type) }}</span>
                <span v-if="h.created_by_name"> · {{ h.created_by_name }}</span>
                <span> · {{ formatDate(h.created_at) }}</span>
              </q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
        <q-card-section v-else class="text-center" style="color: #999; font-size: 12px">Нет записей</q-card-section>
      </q-card>

      <div class="q-mb-xl" />
    </template>

    <div v-else class="text-center q-pa-xl text-grey-5">
      <q-icon name="search_off" size="48px" class="q-mb-sm" />
      <div>Карточка не найдена</div>
      <q-btn flat color="primary" label="Назад" @click="$router.back()" class="q-mt-md" no-caps />
    </div>

    <!-- Диалог перемещения на стадию -->
    <q-dialog v-model="showMoveDialog">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #5DADE2; color: white">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">Переместить на стадию</q-toolbar-title>
          <q-btn flat round dense icon="close" color="white" v-close-popup />
        </q-toolbar>
        <q-card-section>
          <q-select v-model="moveTargetColumn" :options="supervisionColumns" label="Стадия" outlined dense emit-value map-options />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Отмена" no-caps v-close-popup />
          <q-btn unelevated label="Переместить" no-caps style="background: #5DADE2; color: white; border-radius: 4px" @click="doMoveSupervision" :disable="!moveTargetColumn" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог добавления записи -->
    <q-dialog v-model="showAddHistoryDlg">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #ffd93c; color: #333">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">Добавить запись</q-toolbar-title>
          <q-btn flat round dense icon="close" v-close-popup />
        </q-toolbar>
        <q-card-section>
          <q-input v-model="historyNote" label="Описание" outlined dense type="textarea" autogrow />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Отмена" no-caps v-close-popup />
          <q-btn unelevated label="Добавить" no-caps style="background: #ffd93c; color: #333; border-radius: 4px" @click="doAddHistory" :disable="!historyNote" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог отправки сообщения в чат надзора -->
    <q-dialog v-model="showSvSendMsgDlg">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #5DADE2; color: white"><q-toolbar-title class="text-weight-bold" style="font-size: 14px">Отправить сообщение</q-toolbar-title><q-btn flat round dense icon="close" color="white" v-close-popup /></q-toolbar>
        <q-card-section>
          <q-input v-model="svChatMsgText" label="Текст сообщения" outlined dense type="textarea" autogrow />
        </q-card-section>
        <q-card-actions align="right"><q-btn flat label="Отмена" v-close-popup no-caps /><q-btn unelevated label="Отправить" style="background: #5DADE2; color: white; border-radius: 4px" no-caps @click="doSendSvMessage" :loading="svChatActionLoading" :disable="!svChatMsgText?.trim()" /></q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог выбора скрипта надзора -->
    <q-dialog v-model="showSvScriptsDlg">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #58D68D; color: white"><q-toolbar-title class="text-weight-bold" style="font-size: 14px">Запустить скрипт</q-toolbar-title><q-btn flat round dense icon="close" color="white" v-close-popup /></q-toolbar>
        <q-list v-if="svChatScripts.length > 0" dense separator>
          <q-item v-for="script in svChatScripts" :key="script.id" clickable v-ripple @click="doTriggerSvScript(script)">
            <q-item-section avatar><q-icon name="smart_toy" color="grey-7" /></q-item-section>
            <q-item-section>
              <q-item-label>{{ script.name || script.code }}</q-item-label>
              <q-item-label caption>{{ script.description || '' }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
        <q-card-section v-else class="text-center" style="color: #999">Нет доступных скриптов</q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { supervisionApi, filesApi, employeesApi, paymentsApi, locksApi, messengerApi } from 'src/services/api'
import VoiceRecorder from 'src/components/VoiceRecorder.vue'
import { addToCalendar } from 'src/composables/useCalendar'
import { usePermission } from 'src/composables/usePermission'
import { useAuthStore } from 'src/stores/auth'
import { useReferencesStore } from 'src/stores/references'

const { can } = usePermission()
const refs = useReferencesStore()
const agentColor = computed(() => refs.agentByName(card.value?.agent_type)?.color || '#95A5A6')

const route = useRoute()
const $q = useQuasar()
const loading = ref(true)
const card = ref(null)
const timeline = ref([])
const summary = ref(null)
const visits = ref([])
const showAddVisit = ref(false)
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
const visitForm = ref({ visit_date: new Date().toISOString().split('T')[0], stage_code: '', notes: '', executor_name: '' })
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

// ДАН ли текущий пользователь
const isDan = computed(() => {
  const auth = useAuthStore()
  return card.value && card.value.dan_id === auth.user?.id
})

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
  // Создаём запись в timeline и открываем на редактирование
  editEntry.value = {
    stage_code: s.code,
    stage_name: `Стадия: ${s.name}`,
    plan_date: '', actual_date: '', budget_planned: 0, budget_actual: 0,
    supplier: '', status: 'Не начато', notes: '', executor: ''
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
  { label: 'Ст. 12: Декор', value: 'STAGE_12_DECOR' }
]

function stageIcon(status) {
  const icons = {
    'Не начато': 'radio_button_unchecked',
    'В работе': 'pending',
    'Закуплено': 'shopping_cart',
    'Доставлено': 'check_circle',
    'Просрочено': 'error'
  }
  return icons[status] || 'radio_button_unchecked'
}

function stageColor(status) {
  const colors = {
    'Не начато': 'grey-5',
    'В работе': 'orange',
    'Закуплено': 'blue',
    'Доставлено': 'positive',
    'Просрочено': 'negative'
  }
  return colors[status] || 'grey'
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('ru-RU', {
    day: 'numeric', month: 'short'
  })
}

function formatMoney(amount) {
  if (!amount) return '0 ₽'
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency', currency: 'RUB', maximumFractionDigits: 0
  }).format(amount)
}

async function reloadData() {
  const cardId = route.params.id
  if (!cardId) return
  const [cardRes, timelineRes, summaryRes, visitsRes] = await Promise.allSettled([
    supervisionApi.getCard(cardId),
    supervisionApi.getTimeline(cardId),
    supervisionApi.getTimelineSummary(cardId),
    supervisionApi.getVisits(cardId)
  ])
  if (cardRes.status === 'fulfilled') card.value = cardRes.value.data
  if (timelineRes.status === 'fulfilled') timeline.value = timelineRes.value.data?.entries || timelineRes.value.data || []
  if (summaryRes.status === 'fulfilled') summary.value = summaryRes.value.data
  if (visitsRes.status === 'fulfilled') visits.value = visitsRes.value.data || []

  // Оплаты надзора — endpoint /payments/by-supervision-card/{id}
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
  }

  // Исполнители — только 3 из карточки (ДАН, СМ, Руководитель)
  const names = []
  if (card.value?.dan_name) names.push({ label: `${card.value.dan_name} (ДАН)`, value: card.value.dan_id })
  if (card.value?.senior_manager_name) names.push({ label: `${card.value.senior_manager_name} (Ст. менеджер)`, value: card.value.senior_manager_id })
  if (card.value?.studio_director_name) names.push({ label: `${card.value.studio_director_name} (Руководитель)`, value: card.value.studio_director_id })
  executorOptions.value = names
  executorNameOptions.value = names.map(n => n.label.split(' (')[0])
}

async function handlePause() {
  $q.dialog({
    title: 'Приостановить',
    message: 'Укажите причину приостановки',
    prompt: { model: '', type: 'text' },
    cancel: true
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
      status: editEntry.value.status,
      notes: editEntry.value.notes,
      executor: editEntry.value.executor
    })
    $q.notify({ type: 'positive', message: 'Стадия обновлена' })
    showEditEntry.value = false
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

async function saveVisit() {
  if (!visitForm.value.visit_date || !visitForm.value.stage_code) {
    $q.notify({ type: 'warning', message: 'Заполните дату и стадию' })
    return
  }
  try {
    const stageLabel = stageCodesForVisit.find(s => s.value === visitForm.value.stage_code)?.label || ''
    await supervisionApi.createVisit(card.value.id, {
      stage_code: visitForm.value.stage_code,
      stage_name: stageLabel,
      visit_date: visitForm.value.visit_date,
      executor_name: '',
      notes: visitForm.value.notes
    })
    $q.notify({ type: 'positive', message: 'Выезд добавлен' })
    showAddVisit.value = false
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
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

    // Получаем папку договора
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

    // Создаём запись в project_files
    if (cid) {
      await ax.post('/api/v1/files/', {
        contract_id: cid,
        stage: 'supervision',
        file_type: file.type?.includes('image') ? 'image' : 'pdf',
        public_link: publicLink,
        yandex_path: yandexPath,
        file_name: file.name,
        file_order: 0, variation: 1
      })

      // Обновляем поле contracts (для синхронизации с десктопом)
      try {
        const { data: folderLink } = await filesApi.getPublicLink(supervisionFolder)
        if (folderLink.public_link) {
          const { contractsApi: cApi } = await import('src/services/api')
          await cApi.update(cid, { additional_agreement_link: folderLink.public_link })
        }
      } catch {}

      // Scan для синхронизации
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
  const m = { pause: 'pause_circle', resume: 'play_circle', card_moved: 'swap_horiz', assignment_change: 'person', stage_completed: 'check_circle', payment_created: 'payments', auto_resume: 'refresh' }
  return m[type] || 'history'
}
function historyColor(type) {
  const m = { pause: 'warning', resume: 'positive', card_moved: 'primary', stage_completed: 'positive', payment_created: 'info' }
  return m[type] || 'grey-6'
}
function historyLabel(type) {
  const m = { pause: 'Пауза', resume: 'Возобновление', card_moved: 'Перемещение', assignment_change: 'Назначение', stage_completed: 'Стадия завершена', payment_created: 'Оплата', auto_resume: 'Авто-возобновление' }
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

    // Двойная запись оплат ДАН (как десктоп SupervisionReassignDANDialog)
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
    $q.notify({ type: 'positive', message: 'Стадия завершена' })
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

// Переместить на стадию
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

// Сдать работу ДАН
async function submitDanWork() {
  try {
    await supervisionApi.updateCard(card.value.id, { dan_completed: true })
    $q.notify({ type: 'positive', message: 'Работа сдана' })
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

// Принять работу ДАН (менеджер)
async function acceptDanWork() {
  try {
    await supervisionApi.updateCard(card.value.id, { dan_completed: false })
    // Завершаем стадию
    await supervisionApi.completeStage(card.value.id)
    $q.notify({ type: 'positive', message: 'Работа принята, стадия завершена' })
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

// Голосовая заметка — добавление в историю надзора
async function onVoiceRecorded({ url, duration, path }) {
  try {
    const durationStr = `${Math.floor(duration / 60)}:${String(duration % 60).padStart(2, '0')}`
    await supervisionApi.addHistory(card.value.id, {
      description: `Голосовая заметка (${durationStr}) — ${path}`
    })
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Ошибка сохранения записи в историю' })
  }
}

// Добавить выезд в календарь
function addVisitToCalendar(visit) {
  if (!visit?.visit_date) return
  const stageName = visit.stage_name?.replace(/^Стадия \d+: /, '') || ''
  addToCalendar({
    title: `Надзор: ${card.value?.address || ''} — выезд`,
    description: `Выезд на объект${stageName ? '. Стадия: ' + stageName : ''}${visit.notes ? '. ' + visit.notes : ''}`,
    startDate: visit.visit_date,
    location: card.value?.address || '',
    reminder: 1440 // за 1 день
  }, $q)
}

// Добавить запись в историю
async function doAddHistory() {
  if (!historyNote.value) return
  try {
    await supervisionApi.addHistory(card.value.id, { description: historyNote.value })
    $q.notify({ type: 'positive', message: 'Запись добавлена' })
    showAddHistoryDlg.value = false
    historyNote.value = ''
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

// === Telegram-чат надзора — загрузка и действия ===

async function loadSvChat() {
  if (!card.value?.id) return
  svChatLoading.value = true
  try {
    const { data } = await messengerApi.getChats({ supervision_card_id: card.value.id })
    svChatData.value = data?.[0] || null
    if (svChatData.value) {
      const { data: members } = await messengerApi.getChatMembers(svChatData.value.id)
      svChatMembers.value = members || []
    }
  } catch { svChatData.value = null }
  svChatLoading.value = false
}

async function createSvChat() {
  if (!card.value?.id) return
  svChatCreating.value = true
  try {
    const payload = {
      supervision_card_id: card.value.id,
      title: card.value.contract_number || `Чат надзора #${card.value.id}`
    }
    await messengerApi.createChat(payload)
    $q.notify({ type: 'positive', message: 'Чат создан' })
    await loadSvChat()
  } catch { $q.notify({ type: 'negative', message: 'Ошибка создания чата' }) }
  svChatCreating.value = false
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
      supervisionApi.getVisits(cardId)
    ])

    if (cardRes.status === 'fulfilled') card.value = cardRes.value.data
    if (timelineRes.status === 'fulfilled') {
      timeline.value = timelineRes.value.data?.entries || timelineRes.value.data || []
    }
    if (summaryRes.status === 'fulfilled') summary.value = summaryRes.value.data
    if (visitsRes.status === 'fulfilled') visits.value = visitsRes.value.data || []
  } finally {
    loading.value = false
  }

  // Загружаем чат параллельно (не блокируя основную загрузку)
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
