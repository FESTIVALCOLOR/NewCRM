<template>
  <q-page padding>
    <div v-if="crmStore.cardLoading" class="q-pa-md">
      <q-skeleton type="rect" height="120px" class="q-mb-md" />
      <q-skeleton type="text" width="80%" />
      <q-skeleton type="text" width="60%" />
    </div>

    <template v-else-if="card">
      <!-- Шапка — как в десктопе -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="row items-center justify-between q-mb-xs">
            <div class="text-subtitle1 text-weight-bold" style="color: #333">{{ card.contract_number }}</div>
            <q-badge :color="statusColor(card.column_name)" :label="card.column_name" />
          </div>
          <div class="row items-start justify-between">
            <div class="text-body2" style="color: #333; flex: 1">{{ card.address }}</div>
            <span v-if="card.agent_type" class="agent-badge q-ml-xs" :style="{ background: agentColor }">{{ card.agent_type }}</span>
          </div>
          <div class="row q-gutter-sm text-caption q-mt-xs" style="color: #888">
            <span v-if="card.project_type">{{ card.project_type }}</span>
            <span v-if="card.area">{{ card.area }} м²</span>
            <span v-if="card.city">{{ card.city }}</span>
          </div>
          <div v-if="card.current_substep_name" class="q-mt-xs">
            <q-chip dense size="sm" :color="substepColor(card.workflow_status)" text-color="white">
              {{ workflowLabel(card.workflow_status) }}: {{ card.current_substep_name }}
            </q-chip>
          </div>
          <q-badge v-if="card.revision_count > 0" color="negative" :label="`Правки: ${card.revision_count}`" class="q-mt-xs" />
        </q-card-section>
      </q-card>

      <!-- Вкладки — 5 как в десктопе -->
      <q-tabs v-model="activeTab" dense active-color="dark" indicator-color="accent" no-caps class="q-mb-md" style="color: #666" align="left" :breakpoint="0">
        <q-tab name="executors" label="Исполнители" />
        <q-tab name="timeline" label="Сроки" />
        <q-tab name="data" label="Данные" />
        <q-tab name="history" label="История" />
        <q-tab name="payments" label="Оплаты" />
      </q-tabs>

      <q-tab-panels v-model="activeTab" animated class="bg-transparent">

        <!-- ====== ВКЛАДКА 1: Исполнители и дедлайн ====== -->
        <q-tab-panel name="executors" class="q-pa-none">
          <!-- Информация проекта -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">Информация</div>
            </q-card-section>
            <q-list dense>
              <q-item>
                <q-item-section avatar><q-icon name="description" color="grey-7" /></q-item-section>
                <q-item-section>
                  <q-item-label caption>Договор</q-item-label>
                  <q-item-label>{{ card.contract_number }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item v-if="card.project_type">
                <q-item-section avatar><q-icon name="category" color="grey-7" /></q-item-section>
                <q-item-section>
                  <q-item-label caption>Тип проекта</q-item-label>
                  <q-item-label>{{ card.project_type }}<span v-if="card.project_subtype"> / {{ card.project_subtype }}</span></q-item-label>
                </q-item-section>
              </q-item>
              <q-item v-if="card.deadline">
                <q-item-section avatar><q-icon name="event" color="grey-7" /></q-item-section>
                <q-item-section>
                  <q-item-label caption>Дедлайн проекта</q-item-label>
                  <q-item-label :style="{ color: dlHex(card.deadline) }">{{ fmtDate(card.deadline) }} ({{ daysLeft(card.deadline) }})</q-item-label>
                </q-item-section>
              </q-item>
              <q-item v-if="card.contract_period">
                <q-item-section avatar><q-icon name="schedule" color="grey-7" /></q-item-section>
                <q-item-section>
                  <q-item-label caption>Срок выполнения</q-item-label>
                  <q-item-label>{{ card.contract_period }} раб. дней</q-item-label>
                </q-item-section>
              </q-item>
              <q-item v-if="card.tags">
                <q-item-section avatar><q-icon name="label" color="grey-7" /></q-item-section>
                <q-item-section>
                  <q-item-label caption>Теги</q-item-label>
                  <q-item-label>{{ card.tags }}</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Команда проекта — все 7 ролей как в десктопе -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">Команда проекта</div>
            </q-card-section>
            <q-list dense separator>
              <q-item v-for="m in allTeamMembers" :key="m.roleKey">
                <q-item-section avatar>
                  <q-avatar size="28px" :color="m.name ? 'grey-3' : 'red-1'" :text-color="m.name ? 'grey-8' : 'red-3'">
                    {{ m.name ? m.name[0] : '?' }}
                  </q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label style="font-size: 12px" :style="{ color: m.name ? '#333' : '#bbb' }">{{ m.name || 'Не назначен' }}</q-item-label>
                  <q-item-label caption>{{ m.role }}</q-item-label>
                </q-item-section>
                <q-item-section side v-if="m.deadline">
                  <q-badge :color="dlBadgeColor(m.deadline)" :label="fmtDateShort(m.deadline)" dense />
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Workflow действия -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">Действия</div>
            </q-card-section>
            <q-list dense v-if="hasWorkflowActions">
              <q-item v-if="card.workflow_status === 'in_progress'" clickable v-ripple @click="doAction('submit')">
                <q-item-section avatar><q-icon name="send" color="positive" /></q-item-section>
                <q-item-section>Сдать работу</q-item-section>
              </q-item>
              <q-item v-if="card.workflow_status === 'pending_review'" clickable v-ripple @click="doAction('accept')">
                <q-item-section avatar><q-icon name="check_circle" color="positive" /></q-item-section>
                <q-item-section>Принять</q-item-section>
              </q-item>
              <q-item v-if="card.workflow_status === 'pending_review'" clickable v-ripple @click="showRejectDialog = true">
                <q-item-section avatar><q-icon name="replay" color="negative" /></q-item-section>
                <q-item-section>На исправление</q-item-section>
              </q-item>
              <q-item v-if="card.workflow_status === 'pending_review'" clickable v-ripple @click="doAction('client-send')">
                <q-item-section avatar><q-icon name="forward_to_inbox" style="color: #3498DB" /></q-item-section>
                <q-item-section>Отправить клиенту</q-item-section>
              </q-item>
              <q-item v-if="card.workflow_status === 'client_approval'" clickable v-ripple @click="doAction('client-approved')">
                <q-item-section avatar><q-icon name="thumb_up" color="positive" /></q-item-section>
                <q-item-section>Клиент согласовал</q-item-section>
              </q-item>
              <q-item v-if="card.workflow_status === 'act_signing'" clickable v-ripple @click="doAction('sign-act')">
                <q-item-section avatar><q-icon name="draw" style="color: #333" /></q-item-section>
                <q-item-section>Акт подписан</q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="q-pt-sm">
              <div class="text-caption" style="color: #999">
                {{ card.workflow_status ? workflowLabel(card.workflow_status) : 'Нет активного рабочего процесса' }}
              </div>
            </q-card-section>
          </q-card>

          <!-- Назначить исполнителя -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">Назначить исполнителя</div>
            </q-card-section>
            <q-card-section>
              <q-select v-model="assignForm.stage_name" :options="stageOptions" label="Стадия" outlined dense class="q-mb-sm" />
              <q-select v-model="assignForm.executor_id" :options="employeeOptions" option-value="id" option-label="label" label="Исполнитель" outlined dense emit-value map-options class="q-mb-sm" />
              <q-input v-model="assignForm.deadline" label="Дедлайн" outlined dense type="date" class="q-mb-sm" />
              <q-btn unelevated label="Назначить" no-caps class="full-width" style="background: #ffd93c; color: #333; border-radius: 4px" @click="assignExecutor" :loading="actionLoading" />
            </q-card-section>
          </q-card>

          <!-- Переместить -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">Переместить в колонку</div>
            </q-card-section>
            <q-list dense>
              <q-item v-for="col in crmStore.columnOrder" :key="col" clickable @click="moveToColumn(col)" :disable="col === card.column_name">
                <q-item-section>
                  <q-item-label :style="{ color: col === card.column_name ? '#ccc' : '#333', fontSize: '12px' }">{{ col }}</q-item-label>
                </q-item-section>
                <q-item-section side v-if="col === card.column_name">
                  <q-icon name="check" color="positive" size="16px" />
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 2: Таблица сроков ====== -->
        <q-tab-panel name="timeline" class="q-pa-none">
          <q-card class="is-card">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">Таблица сроков проекта</div>
            </q-card-section>
            <q-list dense separator v-if="stageExecutors.length > 0">
              <q-item v-for="se in stageExecutors" :key="se.id" :class="{ 'bg-green-1': se.completed }">
                <q-item-section avatar>
                  <q-icon
                    :name="se.completed ? 'check_circle' : se.submitted_date ? 'hourglass_top' : 'radio_button_unchecked'"
                    :color="se.completed ? 'positive' : se.submitted_date ? 'warning' : 'grey-5'"
                    size="20px"
                  />
                </q-item-section>
                <q-item-section>
                  <q-item-label style="font-size: 12px; color: #333" class="text-weight-medium">{{ se.stage_name }}</q-item-label>
                  <q-item-label caption style="color: #888">
                    {{ se.executor_name || 'Не назначен' }}
                    <span v-if="se.deadline"> | до {{ fmtDateShort(se.deadline) }}</span>
                  </q-item-label>
                  <q-item-label caption v-if="se.assigned_date" style="color: #aaa">
                    Назначен: {{ fmtDateShort(se.assigned_date) }}
                    <span v-if="se.submitted_date"> | Сдано: {{ fmtDateShort(se.submitted_date) }}</span>
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <div v-if="se.completed_date" class="text-caption" style="color: #27AE60">
                    {{ fmtDateShort(se.completed_date) }}
                  </div>
                  <q-badge v-else-if="se.deadline" :color="dlBadgeColor(se.deadline)" dense>
                    {{ daysLeftShort(se.deadline) }}
                  </q-badge>
                </q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="text-center" style="color: #999; padding: 24px">
              <q-icon name="timeline" size="32px" color="grey-4" class="q-mb-sm" />
              <div>Исполнители ещё не назначены</div>
            </q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 3: Данные по проекту ====== -->
        <q-tab-panel name="data" class="q-pa-none">
          <!-- ТЗ и Замер -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">ТЗ и Замер</div>
            </q-card-section>
            <q-list dense>
              <!-- Техническое задание -->
              <q-item :clickable="!!contractData?.tech_task_link" @click="openLink(contractData?.tech_task_link)">
                <q-item-section avatar><q-icon name="description" color="orange" /></q-item-section>
                <q-item-section>
                  <q-item-label>Техническое задание</q-item-label>
                  <q-item-label caption v-if="card.tech_task_date">{{ fmtDateShort(card.tech_task_date) }}</q-item-label>
                  <q-item-label caption v-else style="color: #bbb">Не загружено</q-item-label>
                </q-item-section>
                <q-item-section side v-if="contractData?.tech_task_link"><q-icon name="open_in_new" color="grey-5" /></q-item-section>
              </q-item>
              <!-- Замер -->
              <q-item :clickable="!!contractData?.measurement_image_link" @click="openLink(contractData?.measurement_image_link)">
                <q-item-section avatar><q-icon name="straighten" color="blue" /></q-item-section>
                <q-item-section>
                  <q-item-label>Замер</q-item-label>
                  <q-item-label caption v-if="card.survey_date">{{ fmtDateShort(card.survey_date) }}</q-item-label>
                  <q-item-label caption v-else style="color: #bbb">Не загружен</q-item-label>
                </q-item-section>
                <q-item-section side v-if="contractData?.measurement_image_link"><q-icon name="open_in_new" color="grey-5" /></q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Референсы / Шаблоны + Фотофиксация -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">
                {{ card.project_type === 'Шаблонный' ? 'Шаблоны и Фотофиксация' : 'Референсы и Фотофиксация' }}
              </div>
            </q-card-section>
            <q-list dense>
              <q-item :clickable="!!referencesLink" @click="openLink(referencesLink)">
                <q-item-section avatar><q-icon name="collections" color="purple" /></q-item-section>
                <q-item-section>
                  <q-item-label>{{ card.project_type === 'Шаблонный' ? 'Шаблоны проекта' : 'Референсы' }}</q-item-label>
                </q-item-section>
                <q-item-section side v-if="referencesLink"><q-icon name="open_in_new" color="grey-5" /></q-item-section>
              </q-item>
              <q-item :clickable="!!photoDocLink" @click="openLink(photoDocLink)">
                <q-item-section avatar><q-icon name="photo_camera" color="teal" /></q-item-section>
                <q-item-section><q-item-label>Фотофиксация</q-item-label></q-item-section>
                <q-item-section side v-if="photoDocLink"><q-icon name="open_in_new" color="grey-5" /></q-item-section>
              </q-item>
              <q-item v-if="card.project_data_link" clickable @click="openLink(card.project_data_link)">
                <q-item-section avatar><q-icon name="folder_open" color="amber-8" /></q-item-section>
                <q-item-section><q-item-label>Папка проекта на ЯД</q-item-label></q-item-section>
                <q-item-section side><q-icon name="open_in_new" color="grey-5" /></q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Файлы стадий проекта -->
          <q-card class="is-card q-mb-md" v-if="stageFiles.length > 0">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">Файлы проекта</div>
            </q-card-section>
            <q-list dense separator>
              <q-item v-for="file in stageFiles" :key="file.id" clickable @click="openFile(file)">
                <q-item-section avatar>
                  <q-icon :name="fileIcon(file)" :color="fileColor(file)" />
                </q-item-section>
                <q-item-section>
                  <q-item-label style="font-size: 12px">{{ file.file_name }}</q-item-label>
                  <q-item-label caption>{{ stageLabel(file.stage) }}<span v-if="file.variation > 1"> — вариант {{ file.variation }}</span></q-item-label>
                </q-item-section>
                <q-item-section side><q-icon name="open_in_new" color="grey-5" /></q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Кнопки загрузки файлов -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">Загрузить файлы</div>
            </q-card-section>
            <q-card-section>
              <div class="row q-col-gutter-xs">
                <div class="col-6"><q-btn outline color="grey-7" icon="description" label="ТЗ" no-caps class="full-width" dense @click="uploadCrmFile('tech_task')" /></div>
                <div class="col-6"><q-btn outline color="grey-7" icon="straighten" label="Замер" no-caps class="full-width" dense @click="uploadCrmFile('measurement')" /></div>
                <div class="col-6"><q-btn outline color="grey-7" icon="collections" label="Референсы" no-caps class="full-width q-mt-xs" dense @click="uploadCrmFile('references')" /></div>
                <div class="col-6"><q-btn outline color="grey-7" icon="photo_camera" label="Фотофикс." no-caps class="full-width q-mt-xs" dense @click="uploadCrmFile('photo_documentation')" /></div>
                <div class="col-6"><q-btn outline color="grey-7" icon="architecture" label="Стадия 1" no-caps class="full-width q-mt-xs" dense @click="uploadCrmFile('stage1')" /></div>
                <div class="col-6"><q-btn outline color="grey-7" icon="palette" label="Стадия 2" no-caps class="full-width q-mt-xs" dense @click="uploadCrmFile('stage2_concept')" /></div>
                <div class="col-6"><q-btn outline color="grey-7" icon="engineering" label="Чертежи" no-caps class="full-width q-mt-xs" dense @click="uploadCrmFile('stage3')" /></div>
              </div>
              <input ref="crmFileInput" type="file" style="position: absolute; left: -9999px; opacity: 0" multiple @change="handleCrmFileUpload" accept=".pdf,.jpg,.jpeg,.png,.webp,.heic,.bmp,.doc,.docx,.xls,.xlsx,.dwg" />
            </q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 4: История ====== -->
        <q-tab-panel name="history" class="q-pa-none">
          <!-- Фильтр по типу действия -->
          <q-select
            v-model="historyFilter"
            :options="historyFilterOptions"
            outlined dense
            class="q-mb-md"
            style="font-size: 12px"
            emit-value map-options
          />

          <!-- Выполненные стадии (зелёные) -->
          <q-card v-if="completedStages.length > 0" class="is-card q-mb-md" style="border-left: 3px solid #27AE60">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #27AE60">Выполненные стадии</div>
            </q-card-section>
            <q-list dense>
              <q-item v-for="se in completedStages" :key="'c-'+se.id">
                <q-item-section avatar><q-icon name="check_circle" color="positive" size="18px" /></q-item-section>
                <q-item-section>
                  <q-item-label style="font-size: 12px">{{ se.stage_name }}</q-item-label>
                  <q-item-label caption>{{ se.executor_name }} | {{ fmtDateShort(se.completed_date) }}</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- История действий -->
          <q-card class="is-card">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">Лог действий</div>
            </q-card-section>
            <q-list dense separator v-if="filteredHistory.length > 0">
              <q-item v-for="h in filteredHistory" :key="h.id">
                <q-item-section avatar>
                  <q-icon :name="actionIcon(h.action_type)" :color="actionColor(h.action_type)" size="18px" />
                </q-item-section>
                <q-item-section>
                  <q-item-label style="font-size: 11px; color: #333">{{ h.description || h.action_type }}</q-item-label>
                  <q-item-label caption style="color: #888">{{ h.user_name }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <div class="text-caption" style="color: #888">{{ fmtDateTime(h.action_date) }}</div>
                </q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="text-center" style="color: #999; padding: 24px">
              <q-icon name="history" size="32px" color="grey-4" class="q-mb-sm" />
              <div>Нет записей</div>
            </q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 5: Оплаты исполнителям ====== -->
        <q-tab-panel name="payments" class="q-pa-none">
          <q-card class="is-card">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">Оплаты исполнителям</div>
              <div v-if="paymentTotal > 0" class="text-caption" style="color: #888">
                Итого: {{ fmtMoney(paymentTotal) }}
              </div>
            </q-card-section>
            <q-list dense separator v-if="cardPayments.length > 0">
              <q-item v-for="p in cardPayments" :key="p.id">
                <q-item-section avatar>
                  <q-avatar size="28px" :color="p.is_paid ? 'green-1' : 'orange-1'" :text-color="p.is_paid ? 'green-8' : 'orange-8'">
                    {{ p.employee_name ? p.employee_name[0] : '?' }}
                  </q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label style="font-size: 12px; color: #333" class="text-weight-medium">{{ p.employee_name || 'Не указан' }}</q-item-label>
                  <q-item-label caption style="color: #888">
                    {{ p.role || '' }}
                    <span v-if="p.stage_name || p.payment_subtype"> | {{ p.stage_name || p.payment_subtype }}</span>
                  </q-item-label>
                  <q-item-label caption v-if="p.report_month" style="color: #aaa">{{ p.report_month }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <div class="text-right">
                    <div class="text-weight-bold" style="font-size: 13px" :style="{ color: p.is_paid ? '#27AE60' : '#333' }">{{ fmtMoney(p.final_amount || p.amount) }}</div>
                    <div class="row items-center q-gutter-xs justify-end">
                      <q-badge :color="p.is_paid ? 'positive' : 'warning'" :label="p.is_paid ? 'Оплачено' : 'К оплате'" dense />
                      <q-btn v-if="!p.is_paid" flat dense round size="xs" icon="check" color="positive" @click.stop="markPaymentPaid(p)">
                        <q-tooltip>Отметить как оплачено</q-tooltip>
                      </q-btn>
                    </div>
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="text-center" style="color: #999; padding: 24px">
              <q-icon name="payments" size="32px" color="grey-4" class="q-mb-sm" />
              <div>Нет платежей</div>
            </q-card-section>
          </q-card>
        </q-tab-panel>
      </q-tab-panels>

      <!-- Диалог ревизии -->
      <q-dialog v-model="showRejectDialog">
        <q-card style="min-width: 320px; border-radius: 10px">
          <q-toolbar style="background: #E74C3C; color: white">
            <q-toolbar-title class="text-weight-bold" style="font-size: 14px">На исправление</q-toolbar-title>
            <q-btn flat round dense icon="close" color="white" @click="showRejectDialog = false" />
          </q-toolbar>
          <q-card-section>
            <q-input v-model="rejectReason" label="Причина *" outlined dense type="textarea" autogrow class="q-mb-sm" />
            <q-file v-model="rejectFile" label="Файл с правками" outlined dense accept=".pdf,.jpg,.png,.doc" class="q-mb-sm">
              <template v-slot:prepend><q-icon name="attach_file" /></template>
            </q-file>
          </q-card-section>
          <q-card-actions align="right">
            <q-btn flat label="Отмена" v-close-popup no-caps />
            <q-btn unelevated label="Отправить" style="background: #E74C3C; color: white; border-radius: 4px" no-caps @click="submitReject" :loading="actionLoading" />
          </q-card-actions>
        </q-card>
      </q-dialog>

      <!-- FAB редактирования -->
      <q-page-sticky position="bottom-right" :offset="[18, 18]">
        <q-btn fab icon="edit" style="background: #ffd93c; color: #333" />
      </q-page-sticky>
    </template>

    <div v-else class="text-center q-pa-xl" style="color: #999">
      <q-icon name="search_off" size="48px" class="q-mb-sm" />
      <div>Карточка не найдена</div>
      <q-btn flat label="Назад" @click="$router.back()" class="q-mt-md" no-caps style="color: #333" />
    </div>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { useCrmStore } from 'src/stores/crm'
import { useReferencesStore } from 'src/stores/references'
import { crmApi, employeesApi, filesApi, contractsApi, paymentsApi } from 'src/services/api'

const route = useRoute()
const $q = useQuasar()
const crmStore = useCrmStore()
const refs = useReferencesStore()

const card = computed(() => crmStore.selectedCard)
const activeTab = ref('executors')
const actionLoading = ref(false)
const employeeOptions = ref([])
const assignForm = ref({ stage_name: '', executor_id: null, deadline: '' })
const cardPayments = ref([])
const actionHistory = ref([])
const stageHistory = ref([])
const contractData = ref(null)
const projectFiles = ref([])
const showRejectDialog = ref(false)
const rejectReason = ref('')
const rejectFile = ref(null)
const crmFileInput = ref(null)
const crmUploadStage = ref('')
const historyFilter = ref('all')

// Цвет агента
const agentColor = computed(() => refs.agentByName(card.value?.agent_type)?.color || '#95A5A6')

// Стадии для назначения (зависят от типа проекта)
const stageOptions = computed(() => {
  if (card.value?.project_type === 'Шаблонный') {
    return [
      'Стадия 1: планировочные решения',
      'Стадия 2: рабочие чертежи',
      'Стадия 3: 3д визуализация'
    ]
  }
  return [
    'Стадия 1: планировочные решения',
    'Стадия 2: концепция дизайна',
    'Стадия 2: 3д визуализация',
    'Стадия 3: рабочие чертежи'
  ]
})

// Команда проекта — все 7 ролей (как в десктопе), включая незаполненные
const allTeamMembers = computed(() => {
  if (!card.value) return []
  // Дизайнер и чертёжник из stage_executors
  const se = card.value.stage_executors || []
  const designerSe = se.find(s => s.stage_name?.includes('концепция') || s.stage_name?.includes('дизайн'))
  const draftsmanSe = se.find(s => s.stage_name?.includes('чертеж') || s.stage_name?.includes('чертёж'))

  const members = [
    { roleKey: 'senior_manager', role: 'Ст. менеджер', name: card.value.senior_manager_name },
    { roleKey: 'gap', role: 'ГАП', name: card.value.gap_name },
    { roleKey: 'manager', role: 'Менеджер', name: card.value.manager_name },
    { roleKey: 'surveyor', role: 'Замерщик', name: card.value.surveyor_name },
    { roleKey: 'designer', role: 'Дизайнер', name: designerSe?.executor_name || null, deadline: designerSe?.deadline },
    { roleKey: 'draftsman', role: 'Чертёжник', name: draftsmanSe?.executor_name || null, deadline: draftsmanSe?.deadline }
  ]
  // СДП только для индивидуальных
  if (card.value.project_type === 'Индивидуальный') {
    members.splice(1, 0, { roleKey: 'sdp', role: 'СДП', name: card.value.sdp_name })
  }
  return members
})

// Stage executors (вкладка 2)
const stageExecutors = computed(() => card.value?.stage_executors || [])

// Выполненные стадии (вкладка 4)
const completedStages = computed(() => stageExecutors.value.filter(se => se.completed))

// Файлы проекта по стадиям (вкладка 3)
const stageFiles = computed(() => projectFiles.value.filter(f =>
  ['stage1', 'stage2_concept', 'stage2_3d', 'stage3', 'tech_task', 'measurement', 'references', 'photo_documentation'].includes(f.stage)
))

// Ссылки на ЯД из контракта
const referencesLink = computed(() => {
  if (!contractData.value) return null
  return ydLink(contractData.value.references_yandex_path)
})
const photoDocLink = computed(() => {
  if (!contractData.value) return null
  return ydLink(contractData.value.photo_documentation_yandex_path)
})

// Есть ли workflow действия
const hasWorkflowActions = computed(() => {
  const s = card.value?.workflow_status
  return s && ['in_progress', 'pending_review', 'client_approval', 'act_signing'].includes(s)
})

// Фильтр истории
const historyFilterOptions = [
  { label: 'Все действия', value: 'all' },
  { label: 'Перемещение карточки', value: 'move' },
  { label: 'Назначение исполнителей', value: 'assign' },
  { label: 'Сдача / приёмка работы', value: 'workflow' },
  { label: 'Оплаты', value: 'payment' },
  { label: 'Изменение дедлайна', value: 'deadline' },
  { label: 'Загрузка файлов', value: 'file' },
  { label: 'Прочее', value: 'other' }
]

const filteredHistory = computed(() => {
  if (historyFilter.value === 'all') return actionHistory.value
  const filterMap = {
    move: ['card_moved', 'column_change'],
    assign: ['executor_assigned', 'executor_changed', 'assign'],
    workflow: ['submit', 'accept', 'reject', 'client_send', 'client_ok', 'sign_act', 'stage_completed'],
    payment: ['payment'],
    deadline: ['deadline'],
    file: ['file_upload', 'file_delete'],
    other: []
  }
  const types = filterMap[historyFilter.value] || []
  if (types.length === 0 && historyFilter.value === 'other') {
    const allTypes = Object.values(filterMap).flat()
    return actionHistory.value.filter(h => !allTypes.some(t => (h.action_type || '').toLowerCase().includes(t)))
  }
  return actionHistory.value.filter(h => types.some(t => (h.action_type || '').toLowerCase().includes(t)))
})

// Итого по оплатам
const paymentTotal = computed(() => cardPayments.value.reduce((sum, p) => sum + (p.final_amount || p.amount || 0), 0))

// Ссылки YD → URL
function ydLink(ydPath) {
  if (!ydPath) return null
  let path = ydPath.replace(/^disk:/, '')
  return 'https://disk.yandex.ru/client/disk' + encodeURI(path)
}

// Стили
function statusColor(col) {
  if (!col) return 'grey'
  if (col.includes('Новый')) return 'info'
  if (col.includes('ожидании')) return 'warning'
  if (col.includes('Стадия')) return 'accent'
  if (col.includes('Выполненный')) return 'positive'
  return 'grey'
}
function substepColor(s) {
  return { pending_review: 'purple', revision: 'negative', client_approval: 'info', act_signing: 'purple', stage_completed: 'positive' }[s] || 'orange'
}
function workflowLabel(s) {
  return { in_progress: 'В работе', pending_review: 'На проверке', revision: 'Исправление', client_approval: 'У клиента', pending_decision: 'Решение', act_signing: 'Подписание акта', stage_completed: 'Завершено' }[s] || s || ''
}
function dlHex(d) {
  if (!d) return '#888'
  const days = Math.ceil((new Date(d) - new Date()) / 86400000)
  if (days < 0) return '#E74C3C'
  if (days <= 2) return '#F39C12'
  return '#888'
}
function dlBadgeColor(d) {
  if (!d) return 'grey'
  const days = Math.ceil((new Date(d) - new Date()) / 86400000)
  if (days < 0) return 'negative'
  if (days <= 2) return 'warning'
  return 'positive'
}
function daysLeft(d) {
  if (!d) return ''
  const days = Math.ceil((new Date(d) - new Date()) / 86400000)
  if (days < 0) return `${Math.abs(days)} дн. просрочено`
  if (days === 0) return 'сегодня'
  return `${days} дн.`
}
function daysLeftShort(d) {
  if (!d) return ''
  const days = Math.ceil((new Date(d) - new Date()) / 86400000)
  if (days < 0) return `−${Math.abs(days)}`
  if (days === 0) return '0'
  return `${days}`
}
function fmtDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' })
}
function fmtDateShort(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
}
function fmtDateTime(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}
function fmtMoney(v) {
  if (!v) return '0 ₽'
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(v)
}
function openLink(url) {
  if (url) window.open(url, '_blank')
}
function openFile(f) {
  if (f.public_link) window.open(f.public_link, '_blank')
}

// Иконки файлов
function fileIcon(f) {
  const name = (f.file_name || '').toLowerCase()
  if (name.endsWith('.pdf')) return 'picture_as_pdf'
  if (name.match(/\.(jpg|jpeg|png|webp|heic|bmp)$/)) return 'image'
  if (name.match(/\.(doc|docx)$/)) return 'article'
  if (name.match(/\.(xls|xlsx)$/)) return 'table_chart'
  if (name.endsWith('.dwg')) return 'architecture'
  return 'insert_drive_file'
}
function fileColor(f) {
  const name = (f.file_name || '').toLowerCase()
  if (name.endsWith('.pdf')) return 'red'
  if (name.match(/\.(jpg|jpeg|png|webp|heic|bmp)$/)) return 'green'
  if (name.match(/\.(doc|docx)$/)) return 'blue'
  if (name.match(/\.(xls|xlsx)$/)) return 'teal'
  if (name.endsWith('.dwg')) return 'purple'
  return 'grey-7'
}

const STAGE_LABELS = {
  stage1: 'Планировочное решение',
  stage2_concept: 'Концепция дизайна',
  stage2_3d: '3D визуализация',
  stage3: 'Рабочие чертежи',
  references: 'Референсы',
  photo_documentation: 'Фотофиксация',
  tech_task: 'Тех. задание',
  measurement: 'Замер'
}
function stageLabel(s) { return STAGE_LABELS[s] || s || '' }

// Иконки для типов действий
function actionIcon(type) {
  if (!type) return 'history'
  const t = type.toLowerCase()
  if (t.includes('move') || t.includes('column')) return 'swap_horiz'
  if (t.includes('assign')) return 'person_add'
  if (t.includes('submit')) return 'send'
  if (t.includes('accept')) return 'check_circle'
  if (t.includes('reject')) return 'replay'
  if (t.includes('client')) return 'person'
  if (t.includes('payment')) return 'payments'
  if (t.includes('deadline')) return 'event'
  if (t.includes('file')) return 'attach_file'
  return 'history'
}
function actionColor(type) {
  if (!type) return 'grey-5'
  const t = type.toLowerCase()
  if (t.includes('accept') || t.includes('complete')) return 'positive'
  if (t.includes('reject')) return 'negative'
  if (t.includes('submit')) return 'info'
  if (t.includes('payment')) return 'warning'
  return 'grey-7'
}

// === ACTIONS ===

async function doAction(action) {
  actionLoading.value = true
  try {
    const id = card.value.id
    const actions = {
      submit: () => crmApi.submitWork(id),
      accept: () => crmApi.acceptWork(id),
      'client-send': () => crmApi.sendToClient(id),
      'client-approved': () => crmApi.clientApproved(id),
      'sign-act': () => crmApi.signAct(id)
    }
    await actions[action]()
    $q.notify({ type: 'positive', message: 'Выполнено' })
    await reloadCard()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  } finally {
    actionLoading.value = false
  }
}

async function submitReject() {
  if (!rejectReason.value) {
    $q.notify({ type: 'warning', message: 'Укажите причину' })
    return
  }
  actionLoading.value = true
  try {
    let filePath = null
    if (rejectFile.value) {
      const yp = `/CRM/Правки/${card.value.contract_number || card.value.id}/${rejectFile.value.name}`
      await filesApi.upload(rejectFile.value, yp)
      filePath = yp
    }
    await crmApi.rejectWork(card.value.id, { reason: rejectReason.value, revision_file_path: filePath })
    $q.notify({ type: 'positive', message: 'Отправлено на исправление' })
    showRejectDialog.value = false
    rejectReason.value = ''
    rejectFile.value = null
    await reloadCard()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  } finally {
    actionLoading.value = false
  }
}

async function moveToColumn(col) {
  actionLoading.value = true
  try {
    await crmApi.moveCard(card.value.id, col)
    $q.notify({ type: 'positive', message: `Перемещено: ${col}` })
    await reloadCard()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  } finally {
    actionLoading.value = false
  }
}

async function assignExecutor() {
  if (!assignForm.value.stage_name || !assignForm.value.executor_id) return
  actionLoading.value = true
  try {
    await crmApi.assignExecutor(card.value.id, assignForm.value)
    $q.notify({ type: 'positive', message: 'Исполнитель назначен' })
    await reloadCard()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  } finally {
    actionLoading.value = false
  }
}

async function markPaymentPaid(payment) {
  try {
    await paymentsApi.markPaid(payment.id)
    payment.is_paid = true
    $q.notify({ type: 'positive', message: 'Оплата проведена' })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

function uploadCrmFile(stage) {
  crmUploadStage.value = stage
  crmFileInput.value?.click()
}

async function handleCrmFileUpload(event) {
  const files = event.target.files
  if (!files?.length || !card.value) return
  try {
    $q.loading.show({ message: 'Загрузка...' })
    for (const file of files) {
      const yp = `/CRM/Проекты/${card.value.contract_number}/${crmUploadStage.value}/${file.name}`
      const uploadRes = await filesApi.upload(file, yp)
      const publicLink = uploadRes.data?.public_link || ''
      // Сохраняем в БД ProjectFile
      const { api: apiInst } = await import('src/boot/axios')
      await apiInst.post('/api/v1/files/', {
        contract_id: card.value.contract_id,
        stage: crmUploadStage.value,
        file_type: file.type?.includes('image') ? 'image' : file.name.endsWith('.pdf') ? 'pdf' : 'other',
        public_link: publicLink,
        yandex_path: yp,
        file_name: file.name,
        file_order: projectFiles.value.length + 1,
        variation: 1
      })
    }
    $q.notify({ type: 'positive', message: `Загружено файлов: ${files.length}` })
    // Обновляем список файлов
    if (card.value.contract_id) {
      const { data } = await filesApi.getContractFiles(card.value.contract_id)
      projectFiles.value = data || []
    }
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Ошибка загрузки' })
  } finally {
    $q.loading.hide()
    event.target.value = ''
  }
}

// === ЗАГРУЗКА ДАННЫХ ===

async function reloadCard() {
  const cardId = route.params.id
  await crmStore.loadCard(cardId)
  await loadAdditionalData(cardId)
}

async function loadAdditionalData(cardId) {
  // Загружаем всё параллельно: оплаты, историю действий, историю стадий, сотрудников
  const [payRes, actHistRes, empRes] = await Promise.allSettled([
    crmApi.getPayments(cardId),
    crmApi.getActionHistory(cardId),
    employeesApi.getList()
  ])

  if (payRes.status === 'fulfilled') cardPayments.value = payRes.value.data || []
  if (actHistRes.status === 'fulfilled') actionHistory.value = actHistRes.value.data || []
  if (empRes.status === 'fulfilled') {
    employeeOptions.value = empRes.value.data
      .filter(e => e.status === 'активный')
      .map(e => ({ id: e.id, label: `${e.full_name} (${e.position})` }))
  }

  // Данные контракта и файлы проекта (зависят от card.contract_id)
  if (card.value?.contract_id) {
    const [contractRes, filesRes] = await Promise.allSettled([
      contractsApi.getById(card.value.contract_id),
      filesApi.getContractFiles(card.value.contract_id)
    ])
    if (contractRes.status === 'fulfilled') contractData.value = contractRes.value.data
    if (filesRes.status === 'fulfilled') projectFiles.value = filesRes.value.data || []
  }
}

onMounted(async () => {
  const cardId = route.params.id
  await crmStore.loadCard(cardId)
  await loadAdditionalData(cardId)
})
</script>
