<template>
  <q-page padding>
    <div v-if="crmStore.cardLoading" class="q-pa-md">
      <q-skeleton type="rect" height="120px" class="q-mb-md" />
      <q-skeleton type="text" width="80%" />
    </div>

    <template v-else-if="card">
      <!-- Шапка -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="row items-start justify-between q-mb-xs">
            <div style="flex: 1">
              <div class="text-subtitle1 text-weight-bold" style="color: #333">{{ card.contract_number }}</div>
              <div class="text-body2 q-mt-xs" style="color: #333">{{ card.address }}</div>
            </div>
            <div class="column items-end q-gutter-xs q-ml-sm" style="flex-shrink: 0">
              <q-badge :color="statusColor(card.column_name)" :label="card.column_name" style="min-width: 100px; justify-content: center; padding: 5px 8px; font-size: 11px" />
              <q-badge v-if="card.agent_type" text-color="white" :style="{ background: agentColor, minWidth: '100px', justifyContent: 'center', padding: '5px 8px', fontSize: '11px' }" :label="card.agent_type" />
            </div>
          </div>
          <div class="row q-gutter-sm text-caption q-mt-xs" style="color: #888">
            <span v-if="card.project_type">{{ card.project_type }}</span>
            <span v-if="card.project_subtype"> · {{ card.project_subtype }}</span>
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

      <!-- Вкладки -->
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
          <!-- Информация -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold" style="color: #333">Информация</div></q-card-section>
            <q-list dense>
              <q-item><q-item-section avatar><q-icon name="description" color="grey-7" /></q-item-section><q-item-section><q-item-label caption>Договор</q-item-label><q-item-label>{{ card.contract_number }}</q-item-label></q-item-section></q-item>
              <q-item v-if="card.project_type"><q-item-section avatar><q-icon name="category" color="grey-7" /></q-item-section><q-item-section><q-item-label caption>Тип проекта</q-item-label><q-item-label>{{ card.project_type }}<span v-if="card.project_subtype"> / {{ card.project_subtype }}</span></q-item-label></q-item-section></q-item>
              <q-item v-if="card.contract_period"><q-item-section avatar><q-icon name="schedule" color="grey-7" /></q-item-section><q-item-section><q-item-label caption>Срок выполнения</q-item-label><q-item-label>{{ card.contract_period }} раб. дней</q-item-label></q-item-section></q-item>
              <q-item v-if="contractData?.contract_date"><q-item-section avatar><q-icon name="play_arrow" color="grey-7" /></q-item-section><q-item-section><q-item-label caption>Дата начала работ</q-item-label><q-item-label>{{ fmtDate(contractData.contract_date) }}</q-item-label></q-item-section></q-item>
              <q-item v-if="card.deadline"><q-item-section avatar><q-icon name="flag" color="grey-7" /></q-item-section><q-item-section><q-item-label caption>Дедлайн проекта</q-item-label><q-item-label :style="{ color: dlHex(card.deadline) }">{{ fmtDate(card.deadline) }} ({{ daysLeft(card.deadline) }})</q-item-label></q-item-section></q-item>
              <q-item v-if="card.tags"><q-item-section avatar><q-icon name="label" color="grey-7" /></q-item-section><q-item-section><q-item-label caption>Теги</q-item-label><q-item-label>{{ card.tags }}</q-item-label></q-item-section></q-item>
            </q-list>
          </q-card>

          <!-- Команда проекта с кнопками управления -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold" style="color: #333">Команда проекта</div></q-card-section>
            <q-list dense separator>
              <q-item v-for="m in allTeamMembers" :key="m.roleKey">
                <q-item-section avatar>
                  <q-avatar size="28px" :color="m.name ? 'grey-3' : 'red-1'" :text-color="m.name ? 'grey-8' : 'red-3'">{{ m.name ? m.name[0] : '?' }}</q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label style="font-size: 12px" :style="{ color: m.name ? '#333' : '#bbb' }">{{ m.name || 'Не назначен' }}</q-item-label>
                  <q-item-label caption>{{ m.role }}</q-item-label>
                </q-item-section>
                <q-item-section side v-if="m.deadline">
                  <q-badge :color="dlBadgeColor(m.deadline)" :label="fmtDateShort(m.deadline)" dense />
                </q-item-section>
                <q-item-section side>
                  <div class="row q-gutter-xs">
                    <q-btn v-if="m.name && m.canManage" flat round dense size="xs" icon="edit" color="grey-7" @click="showAssignDialog(m, 'change')"><q-tooltip>Изменить</q-tooltip></q-btn>
                    <q-btn v-if="m.name && m.canManage" flat round dense size="xs" icon="person_remove" color="negative" @click="removeTeamMember(m)"><q-tooltip>Удалить</q-tooltip></q-btn>
                    <q-btn v-if="!m.name && m.canManage" flat round dense size="xs" icon="person_add" color="positive" @click="showAssignDialog(m, 'assign')"><q-tooltip>Назначить</q-tooltip></q-btn>
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Workflow действия -->
          <q-card class="is-card q-mb-md" v-if="hasWorkflowActions">
            <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold" style="color: #333">Действия</div></q-card-section>
            <q-list dense>
              <q-item v-if="card.workflow_status === 'in_progress'" clickable v-ripple @click="doAction('submit')"><q-item-section avatar><q-icon name="send" color="positive" /></q-item-section><q-item-section>Сдать работу</q-item-section></q-item>
              <q-item v-if="card.workflow_status === 'pending_review'" clickable v-ripple @click="doAction('accept')"><q-item-section avatar><q-icon name="check_circle" color="positive" /></q-item-section><q-item-section>Принять</q-item-section></q-item>
              <q-item v-if="card.workflow_status === 'pending_review'" clickable v-ripple @click="showRejectDialog = true"><q-item-section avatar><q-icon name="replay" color="negative" /></q-item-section><q-item-section>На исправление</q-item-section></q-item>
              <q-item v-if="card.workflow_status === 'pending_review'" clickable v-ripple @click="doAction('client-send')"><q-item-section avatar><q-icon name="forward_to_inbox" style="color: #3498DB" /></q-item-section><q-item-section>Отправить клиенту</q-item-section></q-item>
              <q-item v-if="card.workflow_status === 'client_approval'" clickable v-ripple @click="doAction('client-approved')"><q-item-section avatar><q-icon name="thumb_up" color="positive" /></q-item-section><q-item-section>Клиент согласовал</q-item-section></q-item>
              <q-item v-if="card.workflow_status === 'act_signing'" clickable v-ripple @click="doAction('sign-act')"><q-item-section avatar><q-icon name="draw" style="color: #333" /></q-item-section><q-item-section>Акт подписан</q-item-section></q-item>
            </q-list>
          </q-card>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 2: Таблица сроков (из timeline API) ====== -->
        <q-tab-panel name="timeline" class="q-pa-none">
          <q-card class="is-card">
            <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold" style="color: #333">Таблица сроков</div></q-card-section>
            <q-list dense separator v-if="timelineEntries.length > 0">
              <q-item v-for="e in timelineEntries" :key="e.id" :class="{ 'bg-green-1': e.actual_date }" :style="e.executor_role === 'header' ? 'background: #F5F5F5' : ''">
                <q-item-section avatar v-if="e.executor_role !== 'header'">
                  <q-icon :name="e.actual_date ? 'check_circle' : 'radio_button_unchecked'" :color="e.actual_date ? 'positive' : 'grey-5'" size="18px" />
                </q-item-section>
                <q-item-section :style="e.executor_role === 'header' ? 'padding-left: 4px' : ''">
                  <q-item-label :style="{ fontSize: e.executor_role === 'header' ? '13px' : '11px', color: '#333', fontWeight: e.executor_role === 'header' ? 'bold' : 'normal' }">{{ e.stage_name }}</q-item-label>
                  <q-item-label v-if="e.executor_role !== 'header'" caption style="color: #888">
                    <span v-if="e.norm_days">Норма: {{ e.custom_norm_days || e.norm_days }} дн.</span>
                    <span v-if="e.actual_days"> | Факт: {{ e.actual_days }} дн.</span>
                    <span v-if="e.executor_role"> | {{ e.executor_role }}</span>
                  </q-item-label>
                </q-item-section>
                <q-item-section side v-if="e.actual_date">
                  <div class="text-caption" style="color: #27AE60">{{ fmtDateShort(e.actual_date) }}</div>
                </q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="text-center" style="color: #999; padding: 24px">
              <q-icon name="timeline" size="32px" color="grey-4" class="q-mb-sm" /><div>Таблица сроков не инициализирована</div>
            </q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 3: Данные по проекту (блоки) ====== -->
        <q-tab-panel name="data" class="q-pa-none">
          <!-- ТЗ -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-xs"><div class="text-subtitle2 text-weight-bold" style="color: #333">Техническое задание</div></q-card-section>
            <q-list dense v-if="filesByStage('tech_task').length > 0">
              <q-item v-for="f in filesByStage('tech_task')" :key="f.id" clickable @click="openFile(f)">
                <q-item-section avatar><q-icon :name="fileIcon(f)" :color="fileColor(f)" /></q-item-section>
                <q-item-section><q-item-label style="font-size: 12px">{{ f.file_name }}</q-item-label></q-item-section>
                <q-item-section side><div class="row q-gutter-xs"><q-icon name="open_in_new" color="grey-5" /><q-btn flat round dense size="xs" icon="delete_outline" color="negative" @click.stop="deleteFile(f)" /></div></q-item-section>
              </q-item>
            </q-list>
            <q-card-section class="q-pt-xs"><div class="row q-gutter-xs"><q-btn outline color="grey-7" icon="upload" label="Загрузить" no-caps dense @click="uploadCrmFile('tech_task')" /><q-btn v-if="contractData?.tech_task_link" flat color="grey-7" icon="open_in_new" label="ЯД" no-caps dense @click="openLink(contractData.tech_task_link)" /></div></q-card-section>
          </q-card>

          <!-- Замер -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-xs"><div class="text-subtitle2 text-weight-bold" style="color: #333">Замер</div></q-card-section>
            <q-list dense v-if="filesByStage('measurement').length > 0">
              <q-item v-for="f in filesByStage('measurement')" :key="f.id" clickable @click="openFile(f)">
                <q-item-section avatar><q-icon :name="fileIcon(f)" :color="fileColor(f)" /></q-item-section>
                <q-item-section><q-item-label style="font-size: 12px">{{ f.file_name }}</q-item-label></q-item-section>
                <q-item-section side><div class="row q-gutter-xs"><q-icon name="open_in_new" color="grey-5" /><q-btn flat round dense size="xs" icon="delete_outline" color="negative" @click.stop="deleteFile(f)" /></div></q-item-section>
              </q-item>
            </q-list>
            <q-card-section class="q-pt-xs"><q-btn outline color="grey-7" icon="upload" label="Загрузить" no-caps dense @click="uploadCrmFile('measurement')" /></q-card-section>
          </q-card>

          <!-- Фотофиксация -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-xs"><div class="text-subtitle2 text-weight-bold" style="color: #333">Фотофиксация</div></q-card-section>
            <q-list dense v-if="filesByStage('photo_documentation').length > 0">
              <q-item v-for="f in filesByStage('photo_documentation')" :key="f.id" clickable @click="openFile(f)"><q-item-section avatar><q-icon :name="fileIcon(f)" :color="fileColor(f)" /></q-item-section><q-item-section><q-item-label style="font-size: 12px">{{ f.file_name }}</q-item-label></q-item-section><q-item-section side><div class="row q-gutter-xs"><q-icon name="open_in_new" color="grey-5" /><q-btn flat round dense size="xs" icon="delete_outline" color="negative" @click.stop="deleteFile(f)" /></div></q-item-section></q-item>
            </q-list>
            <q-card-section class="q-pt-xs"><q-btn outline color="grey-7" icon="upload" label="Загрузить" no-caps dense @click="uploadCrmFile('photo_documentation')" /></q-card-section>
          </q-card>

          <!-- Референсы -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-xs"><div class="text-subtitle2 text-weight-bold" style="color: #333">{{ card.project_type === 'Шаблонный' ? 'Шаблоны' : 'Референсы' }}</div></q-card-section>
            <q-list dense v-if="filesByStage('references').length > 0">
              <q-item v-for="f in filesByStage('references')" :key="f.id" clickable @click="openFile(f)"><q-item-section avatar><q-icon :name="fileIcon(f)" :color="fileColor(f)" /></q-item-section><q-item-section><q-item-label style="font-size: 12px">{{ f.file_name }}</q-item-label></q-item-section><q-item-section side><div class="row q-gutter-xs"><q-icon name="open_in_new" color="grey-5" /><q-btn flat round dense size="xs" icon="delete_outline" color="negative" @click.stop="deleteFile(f)" /></div></q-item-section></q-item>
            </q-list>
            <q-card-section class="q-pt-xs"><q-btn outline color="grey-7" icon="upload" label="Загрузить" no-caps dense @click="uploadCrmFile('references')" /></q-card-section>
          </q-card>

          <!-- Стадии проекта (зависят от типа) -->
          <q-card v-for="stage in projectStages" :key="stage.code" class="is-card q-mb-md">
            <q-card-section class="q-pb-xs"><div class="text-subtitle2 text-weight-bold" style="color: #333">{{ stage.label }}</div></q-card-section>
            <q-list dense v-if="filesByStage(stage.code).length > 0">
              <q-item v-for="f in filesByStage(stage.code)" :key="f.id" clickable @click="openFile(f)"><q-item-section avatar><q-icon :name="fileIcon(f)" :color="fileColor(f)" /></q-item-section><q-item-section><q-item-label style="font-size: 12px">{{ f.file_name }}<span v-if="f.variation > 1" class="text-caption q-ml-xs" style="color: #888">вар. {{ f.variation }}</span></q-item-label></q-item-section><q-item-section side><div class="row q-gutter-xs"><q-icon name="open_in_new" color="grey-5" /><q-btn flat round dense size="xs" icon="delete_outline" color="negative" @click.stop="deleteFile(f)" /></div></q-item-section></q-item>
            </q-list>
            <q-card-section class="q-pt-xs">
              <div class="row q-gutter-xs">
                <q-btn outline color="grey-7" icon="upload" label="Загрузить" no-caps dense @click="uploadCrmFile(stage.code)" />
                <q-btn outline color="grey-7" icon="create_new_folder" label="Вариация" no-caps dense @click="uploadCrmFile(stage.code + '_var')" />
              </div>
            </q-card-section>
          </q-card>

          <input ref="crmFileInput" type="file" style="position: absolute; left: -9999px; opacity: 0" multiple @change="handleCrmFileUpload" accept=".pdf,.jpg,.jpeg,.png,.webp,.heic,.bmp,.doc,.docx,.xls,.xlsx,.dwg" />
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 4: История ====== -->
        <q-tab-panel name="history" class="q-pa-none">
          <q-select v-model="historyFilter" :options="historyFilterOptions" outlined dense class="q-mb-md" style="font-size: 12px" emit-value map-options />
          <q-card v-if="completedStages.length > 0" class="is-card q-mb-md" style="border-left: 3px solid #27AE60">
            <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold" style="color: #27AE60">Выполненные стадии</div></q-card-section>
            <q-list dense>
              <q-item v-for="se in completedStages" :key="'c-'+se.id"><q-item-section avatar><q-icon name="check_circle" color="positive" size="18px" /></q-item-section><q-item-section><q-item-label style="font-size: 12px">{{ se.stage_name }}</q-item-label><q-item-label caption>{{ se.executor_name }} | {{ fmtDateShort(se.completed_date) }}</q-item-label></q-item-section></q-item>
            </q-list>
          </q-card>
          <q-card class="is-card">
            <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold" style="color: #333">Лог действий</div></q-card-section>
            <q-list dense separator v-if="filteredHistory.length > 0">
              <q-item v-for="h in filteredHistory" :key="h.id"><q-item-section avatar><q-icon :name="actionIcon(h.action_type)" :color="actionColor(h.action_type)" size="18px" /></q-item-section><q-item-section><q-item-label style="font-size: 11px; color: #333">{{ h.description || h.action_type }}</q-item-label><q-item-label caption style="color: #888">{{ h.user_name }}</q-item-label></q-item-section><q-item-section side><div class="text-caption" style="color: #888">{{ fmtDateTime(h.action_date) }}</div></q-item-section></q-item>
            </q-list>
            <q-card-section v-else class="text-center" style="color: #999; padding: 24px"><q-icon name="history" size="32px" color="grey-4" class="q-mb-sm" /><div>Нет записей</div></q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 5: Оплаты исполнителям ====== -->
        <q-tab-panel name="payments" class="q-pa-none">
          <q-card class="is-card q-mb-md" v-for="group in paymentGroups" :key="group.role">
            <q-card-section class="q-pb-xs">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">{{ group.role }}</div>
            </q-card-section>
            <q-list dense separator>
              <q-item v-for="p in group.items" :key="p.id" :style="paymentRowStyle(p)">
                <q-item-section>
                  <q-item-label style="font-size: 12px; color: #333" class="text-weight-medium">
                    {{ p.employee_name || 'Не указан' }}
                    <span class="text-caption q-ml-xs" style="color: #888">{{ p.payment_subtype || 'Полная оплата' }}</span>
                  </q-item-label>
                  <q-item-label caption style="color: #888">{{ p.stage_name || '' }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <div class="text-right">
                    <div class="row items-center justify-end q-gutter-xs">
                      <div class="text-weight-bold" style="font-size: 13px" :style="{ color: p.is_paid ? '#27AE60' : '#333' }">{{ fmtMoney(p.final_amount || p.amount) }}</div>
                      <div class="text-caption" :style="{ color: p.report_month ? '#333' : '#bbb' }">{{ formatReportMonth(p.report_month) }}</div>
                    </div>
                    <div class="row items-center justify-end q-gutter-xs q-mt-xs">
                      <q-btn flat round dense size="xs" icon="edit" color="grey-7" @click.stop="editPaymentAmount(p)"><q-tooltip>Изменить сумму</q-tooltip></q-btn>
                      <q-btn flat round dense size="xs" icon="delete_outline" color="negative" @click.stop="deletePayment(p)"><q-tooltip>Удалить</q-tooltip></q-btn>
                    </div>
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Итого -->
          <q-card v-if="cardPayments.length > 0" class="is-card" style="border-left: 3px solid #ffd93c">
            <q-card-section class="q-pa-md">
              <div class="row items-center justify-between">
                <div class="text-subtitle2 text-weight-bold" style="color: #333">Итого по карточке</div>
                <div class="text-h6 text-weight-bold" style="color: #333">{{ fmtMoney(paymentTotal) }}</div>
              </div>
            </q-card-section>
          </q-card>

          <q-card-section v-if="cardPayments.length === 0" class="text-center" style="color: #999; padding: 24px">
            <q-icon name="payments" size="32px" color="grey-4" class="q-mb-sm" /><div>Нет платежей</div>
          </q-card-section>
        </q-tab-panel>
      </q-tab-panels>

      <!-- Диалог ревизии -->
      <q-dialog v-model="showRejectDialog">
        <q-card style="min-width: 320px; border-radius: 10px">
          <q-toolbar style="background: #E74C3C; color: white"><q-toolbar-title class="text-weight-bold" style="font-size: 14px">На исправление</q-toolbar-title><q-btn flat round dense icon="close" color="white" @click="showRejectDialog = false" /></q-toolbar>
          <q-card-section>
            <q-input v-model="rejectReason" label="Причина *" outlined dense type="textarea" autogrow class="q-mb-sm" />
            <q-file v-model="rejectFile" label="Файл с правками" outlined dense accept=".pdf,.jpg,.png,.doc" class="q-mb-sm"><template v-slot:prepend><q-icon name="attach_file" /></template></q-file>
          </q-card-section>
          <q-card-actions align="right"><q-btn flat label="Отмена" v-close-popup no-caps /><q-btn unelevated label="Отправить" style="background: #E74C3C; color: white; border-radius: 4px" no-caps @click="submitReject" :loading="actionLoading" /></q-card-actions>
        </q-card>
      </q-dialog>

      <!-- Диалог назначения исполнителя -->
      <q-dialog v-model="assignDialogVisible">
        <q-card style="min-width: 320px; border-radius: 10px">
          <q-toolbar style="background: #ffd93c; color: #333"><q-toolbar-title class="text-weight-bold" style="font-size: 14px">{{ assignDialogTitle }}</q-toolbar-title><q-btn flat round dense icon="close" @click="assignDialogVisible = false" /></q-toolbar>
          <q-card-section>
            <div class="text-caption q-mb-sm" style="color: #888">Роль: {{ assignRole }}</div>
            <q-select v-model="assignEmployeeId" :options="employeeOptions" option-value="id" option-label="label" label="Сотрудник" outlined dense emit-value map-options class="q-mb-sm" />
            <q-input v-if="assignNeedsDeadline" v-model="assignDeadline" label="Дедлайн" outlined dense type="date" class="q-mb-sm" />
          </q-card-section>
          <q-card-actions align="right"><q-btn flat label="Отмена" v-close-popup no-caps /><q-btn unelevated label="Назначить" style="background: #ffd93c; color: #333; border-radius: 4px" no-caps @click="doAssign" :loading="actionLoading" /></q-card-actions>
        </q-card>
      </q-dialog>

      <!-- FAB -->
      <q-page-sticky position="bottom-right" :offset="[18, 18]">
        <q-btn fab icon="edit" style="background: #ffd93c; color: #333" @click="editCard" />
      </q-page-sticky>
    </template>

    <div v-else class="text-center q-pa-xl" style="color: #999">
      <q-icon name="search_off" size="48px" class="q-mb-sm" /><div>Карточка не найдена</div>
      <q-btn flat label="Назад" @click="$router.back()" class="q-mt-md" no-caps style="color: #333" />
    </div>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useCrmStore } from 'src/stores/crm'
import { useReferencesStore } from 'src/stores/references'
import { crmApi, employeesApi, filesApi, contractsApi, paymentsApi } from 'src/services/api'

const route = useRoute()
const router = useRouter()
const $q = useQuasar()
const crmStore = useCrmStore()
const refs = useReferencesStore()

const card = computed(() => crmStore.selectedCard)
const activeTab = ref('executors')
const actionLoading = ref(false)
const employeeOptions = ref([])
const cardPayments = ref([])
const actionHistory = ref([])
const contractData = ref(null)
const projectFiles = ref([])
const timelineEntries = ref([])
const showRejectDialog = ref(false)
const rejectReason = ref('')
const rejectFile = ref(null)
const crmFileInput = ref(null)
const crmUploadStage = ref('')
const historyFilter = ref('all')

// Диалог назначения
const assignDialogVisible = ref(false)
const assignDialogTitle = ref('')
const assignRole = ref('')
const assignRoleKey = ref('')
const assignEmployeeId = ref(null)
const assignDeadline = ref('')
const assignNeedsDeadline = ref(false)
const assignStageName = ref('')

const agentColor = computed(() => refs.agentByName(card.value?.agent_type)?.color || '#95A5A6')

// Стадии файлов (зависят от типа)
const projectStages = computed(() => {
  if (card.value?.project_type === 'Шаблонный') {
    return [
      { code: 'stage1', label: 'Стадия 1: Планировочное решение' },
      { code: 'stage3', label: 'Стадия 2: Чертёжная документация' },
      { code: 'stage2_3d', label: 'Стадия 3: 3D визуализация (Доп.)' }
    ]
  }
  return [
    { code: 'stage1', label: 'Стадия 1: Планировочное решение' },
    { code: 'stage2_concept', label: 'Стадия 2: Концепция дизайна' },
    { code: 'stage3', label: 'Стадия 3: Чертёжная документация' }
  ]
})

// Команда
const allTeamMembers = computed(() => {
  if (!card.value) return []
  const se = card.value.stage_executors || []
  const designerSe = se.find(s => s.stage_name?.includes('концепция') || s.stage_name?.includes('дизайн') || s.stage_name?.includes('визуализац'))
  const draftsmanSe = se.find(s => s.stage_name?.includes('чертеж') || s.stage_name?.includes('чертёж'))

  const members = [
    { roleKey: 'senior_manager', role: 'Ст. менеджер', name: card.value.senior_manager_name, canManage: true },
    { roleKey: 'gap', role: 'ГАП', name: card.value.gap_name, canManage: true },
    { roleKey: 'manager', role: 'Менеджер', name: card.value.manager_name, canManage: true },
    { roleKey: 'surveyor', role: 'Замерщик', name: card.value.surveyor_name, canManage: true },
    { roleKey: 'designer', role: 'Дизайнер', name: designerSe?.executor_name || null, deadline: designerSe?.deadline, canManage: true, stageName: designerSe?.stage_name },
    { roleKey: 'draftsman', role: 'Чертёжник', name: draftsmanSe?.executor_name || null, deadline: draftsmanSe?.deadline, canManage: true, stageName: draftsmanSe?.stage_name }
  ]
  if (card.value.project_type === 'Индивидуальный') {
    members.splice(1, 0, { roleKey: 'sdp', role: 'СДП', name: card.value.sdp_name, canManage: true })
  }
  return members
})

const stageExecutors = computed(() => card.value?.stage_executors || [])
const completedStages = computed(() => stageExecutors.value.filter(se => se.completed))

function filesByStage(stage) { return projectFiles.value.filter(f => f.stage === stage) }

const hasWorkflowActions = computed(() => {
  const s = card.value?.workflow_status
  return s && ['in_progress', 'pending_review', 'client_approval', 'act_signing'].includes(s)
})

// Оплаты группами по роли
const paymentGroups = computed(() => {
  const map = {}
  for (const p of cardPayments.value) {
    const role = p.role || p.stage_name || 'Прочее'
    if (!map[role]) map[role] = { role, items: [] }
    map[role].items.push(p)
  }
  return Object.values(map)
})
const paymentTotal = computed(() => cardPayments.value.reduce((sum, p) => sum + (p.final_amount || p.amount || 0), 0))

function paymentRowStyle(p) {
  if (p.is_paid) return { background: '#E8F5E9' }
  if (p.report_month) return { background: '#FFF8E1' }
  return {}
}

function formatReportMonth(m) {
  if (!m) return 'в работе'
  try {
    const [y, mo] = m.split('-')
    const months = ['январь','февраль','март','апрель','май','июнь','июль','август','сентябрь','октябрь','ноябрь','декабрь']
    return `${months[parseInt(mo) - 1]} ${y}`
  } catch { return m }
}

// Фильтр истории
const historyFilterOptions = [
  { label: 'Все действия', value: 'all' }, { label: 'Перемещение', value: 'move' },
  { label: 'Назначения', value: 'assign' }, { label: 'Workflow', value: 'workflow' },
  { label: 'Оплаты', value: 'payment' }, { label: 'Дедлайны', value: 'deadline' },
  { label: 'Файлы', value: 'file' }, { label: 'Прочее', value: 'other' }
]
const filteredHistory = computed(() => {
  if (historyFilter.value === 'all') return actionHistory.value
  const map = { move: ['card_moved','column'], assign: ['executor_assigned','assign'], workflow: ['submit','accept','reject','client','sign_act','stage_completed'], payment: ['payment'], deadline: ['deadline'], file: ['file'] }
  const types = map[historyFilter.value] || []
  if (types.length === 0) { const all = Object.values(map).flat(); return actionHistory.value.filter(h => !all.some(t => (h.action_type||'').toLowerCase().includes(t))) }
  return actionHistory.value.filter(h => types.some(t => (h.action_type||'').toLowerCase().includes(t)))
})

// Форматирование
function statusColor(col) { if (!col) return 'grey'; if (col.includes('Новый')) return 'info'; if (col.includes('ожидании')) return 'warning'; if (col.includes('Стадия')) return 'accent'; if (col.includes('Выполненный')) return 'positive'; return 'grey' }
function substepColor(s) { return { pending_review: 'purple', revision: 'negative', client_approval: 'info', act_signing: 'purple', stage_completed: 'positive' }[s] || 'orange' }
function workflowLabel(s) { return { in_progress: 'В работе', pending_review: 'На проверке', revision: 'Исправление', client_approval: 'У клиента', act_signing: 'Подписание акта', stage_completed: 'Завершено' }[s] || s || '' }
function dlHex(d) { if (!d) return '#888'; const days = Math.ceil((new Date(d)-new Date())/86400000); if (days<0) return '#E74C3C'; if (days<=2) return '#F39C12'; return '#888' }
function dlBadgeColor(d) { if (!d) return 'grey'; const days = Math.ceil((new Date(d)-new Date())/86400000); if (days<0) return 'negative'; if (days<=2) return 'warning'; return 'positive' }
function daysLeft(d) { if (!d) return ''; const days = Math.ceil((new Date(d)-new Date())/86400000); if (days<0) return `${Math.abs(days)} дн. просрочено`; if (days===0) return 'сегодня'; return `${days} дн.` }
function fmtDate(d) { if (!d) return '—'; return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' }) }
function fmtDateShort(d) { if (!d) return ''; return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }) }
function fmtDateTime(d) { if (!d) return ''; return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) }
function fmtMoney(v) { if (!v) return '0 ₽'; return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(v) }
function openLink(url) { if (url) window.open(url, '_blank') }
function openFile(f) { if (f.public_link) window.open(f.public_link, '_blank') }
function fileIcon(f) { const n = (f.file_name||'').toLowerCase(); if (n.endsWith('.pdf')) return 'picture_as_pdf'; if (n.match(/\.(jpg|jpeg|png|webp)$/)) return 'image'; return 'insert_drive_file' }
function fileColor(f) { const n = (f.file_name||'').toLowerCase(); if (n.endsWith('.pdf')) return 'red'; if (n.match(/\.(jpg|jpeg|png|webp)$/)) return 'green'; return 'grey-7' }
function actionIcon(t) { if (!t) return 'history'; const l=t.toLowerCase(); if (l.includes('move')||l.includes('column')) return 'swap_horiz'; if (l.includes('assign')) return 'person_add'; if (l.includes('submit')) return 'send'; if (l.includes('accept')) return 'check_circle'; if (l.includes('reject')) return 'replay'; if (l.includes('payment')) return 'payments'; if (l.includes('deadline')) return 'event'; if (l.includes('file')) return 'attach_file'; return 'history' }
function actionColor(t) { if (!t) return 'grey-5'; const l=t.toLowerCase(); if (l.includes('accept')||l.includes('complete')) return 'positive'; if (l.includes('reject')) return 'negative'; if (l.includes('submit')) return 'info'; return 'grey-7' }

// === ACTIONS ===
function editCard() {
  // Открыть страницу договора для редактирования (FAB)
  if (card.value?.contract_id) router.push(`/contracts/${card.value.contract_id}`)
}

async function doAction(action) {
  actionLoading.value = true
  try {
    const id = card.value.id
    const actions = { submit: () => crmApi.submitWork(id), accept: () => crmApi.acceptWork(id), 'client-send': () => crmApi.sendToClient(id), 'client-approved': () => crmApi.clientApproved(id), 'sign-act': () => crmApi.signAct(id) }
    await actions[action]()
    $q.notify({ type: 'positive', message: 'Выполнено' })
    await reloadCard()
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  finally { actionLoading.value = false }
}

async function submitReject() {
  if (!rejectReason.value) { $q.notify({ type: 'warning', message: 'Укажите причину' }); return }
  actionLoading.value = true
  try {
    let filePath = null
    if (rejectFile.value) {
      const yp = `/CRM/Правки/${card.value.contract_number||card.value.id}/${rejectFile.value.name}`
      await filesApi.upload(rejectFile.value, yp); filePath = yp
    }
    await crmApi.rejectWork(card.value.id, { reason: rejectReason.value, revision_file_path: filePath })
    $q.notify({ type: 'positive', message: 'Отправлено на исправление' }); showRejectDialog.value = false; rejectReason.value = ''; rejectFile.value = null; await reloadCard()
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  finally { actionLoading.value = false }
}

// Назначение / изменение члена команды
function showAssignDialog(member, mode) {
  assignRole.value = member.role
  assignRoleKey.value = member.roleKey
  assignStageName.value = member.stageName || ''
  assignNeedsDeadline.value = ['designer', 'draftsman'].includes(member.roleKey)
  assignDialogTitle.value = mode === 'assign' ? `Назначить ${member.role}` : `Изменить ${member.role}`
  assignEmployeeId.value = null
  assignDeadline.value = ''
  assignDialogVisible.value = true
}

async function doAssign() {
  if (!assignEmployeeId.value) return
  actionLoading.value = true
  try {
    const roleKey = assignRoleKey.value
    if (['designer', 'draftsman'].includes(roleKey)) {
      // Назначение через stage_executor
      let stageName = assignStageName.value
      if (!stageName) {
        const isTemplate = card.value?.project_type === 'Шаблонный'
        if (roleKey === 'designer') stageName = isTemplate ? 'Стадия 3: 3д визуализация' : 'Стадия 2: концепция дизайна'
        else stageName = isTemplate ? 'Стадия 2: рабочие чертежи' : 'Стадия 3: рабочие чертежи'
      }
      await crmApi.assignExecutor(card.value.id, { stage_name: stageName, executor_id: assignEmployeeId.value, deadline: assignDeadline.value || null })
    } else {
      const update = {}; update[`${roleKey}_id`] = assignEmployeeId.value
      await crmApi.updateCard(card.value.id, update)
    }
    $q.notify({ type: 'positive', message: 'Назначен' }); assignDialogVisible.value = false; await reloadCard()
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  finally { actionLoading.value = false }
}

async function removeTeamMember(member) {
  $q.dialog({ title: 'Убрать исполнителя?', message: `${member.role}: ${member.name}`, cancel: { label: 'Нет', flat: true, noCaps: true }, ok: { label: 'Да', noCaps: true, color: 'negative' } }).onOk(async () => {
    try {
      const update = {}; update[`${member.roleKey}_id`] = null
      await crmApi.updateCard(card.value.id, update)
      $q.notify({ type: 'positive', message: 'Убран' }); await reloadCard()
    } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  })
}

function editPaymentAmount(p) {
  $q.dialog({ title: 'Изменить сумму', prompt: { model: String(p.final_amount || p.amount || 0), type: 'number' }, cancel: { label: 'Отмена', flat: true, noCaps: true }, ok: { label: 'Сохранить', noCaps: true, color: 'positive' } }).onOk(async (val) => {
    try { await paymentsApi.update(p.id, { final_amount: parseFloat(val) }); p.final_amount = parseFloat(val); $q.notify({ type: 'positive', message: 'Сумма обновлена' }) }
    catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  })
}

async function deletePayment(p) {
  $q.dialog({ title: 'Удалить оплату?', message: `${p.employee_name} — ${fmtMoney(p.final_amount || p.amount)}`, cancel: { label: 'Нет', flat: true, noCaps: true }, ok: { label: 'Да', noCaps: true, color: 'negative' } }).onOk(async () => {
    try { await paymentsApi.delete(p.id); cardPayments.value = cardPayments.value.filter(x => x.id !== p.id); $q.notify({ type: 'positive', message: 'Удалено' }) }
    catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  })
}

async function deleteFile(f) {
  $q.dialog({ title: 'Удалить файл?', message: f.file_name, cancel: { label: 'Нет', flat: true, noCaps: true }, ok: { label: 'Да', noCaps: true, color: 'negative' } }).onOk(async () => {
    try {
      const { api: apiInst } = await import('src/boot/axios')
      await apiInst.delete(`/api/v1/files/${f.id}`)
      projectFiles.value = projectFiles.value.filter(x => x.id !== f.id)
      $q.notify({ type: 'positive', message: 'Файл удалён' })
    } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  })
}

function uploadCrmFile(stage) { crmUploadStage.value = stage.replace('_var', ''); crmFileInput.value?.click() }

async function handleCrmFileUpload(event) {
  const files = event.target.files; if (!files?.length || !card.value) return
  try {
    $q.loading.show({ message: 'Загрузка...' })
    const variation = crmUploadStage.value.endsWith('_var') ? (projectFiles.value.filter(f => f.stage === crmUploadStage.value).length + 2) : 1
    for (const file of files) {
      const yp = `/CRM/Проекты/${card.value.contract_number}/${crmUploadStage.value}/${file.name}`
      const res = await filesApi.upload(file, yp)
      const { api: apiInst } = await import('src/boot/axios')
      await apiInst.post('/api/v1/files/', { contract_id: card.value.contract_id, stage: crmUploadStage.value, file_type: file.type?.includes('image') ? 'image' : 'other', public_link: res.data?.public_link || '', yandex_path: yp, file_name: file.name, file_order: projectFiles.value.length + 1, variation })
    }
    $q.notify({ type: 'positive', message: `Загружено: ${files.length}` })
    if (card.value.contract_id) { const { data } = await filesApi.getContractFiles(card.value.contract_id); projectFiles.value = data || [] }
  } catch { $q.notify({ type: 'negative', message: 'Ошибка загрузки' }) }
  finally { $q.loading.hide(); event.target.value = '' }
}

// === ЗАГРУЗКА ===
async function reloadCard() { const id = route.params.id; await crmStore.loadCard(id); await loadAdditionalData(id) }

async function loadAdditionalData(cardId) {
  const [payRes, actRes, empRes] = await Promise.allSettled([crmApi.getPayments(cardId), crmApi.getActionHistory(cardId), employeesApi.getList()])
  if (payRes.status === 'fulfilled') cardPayments.value = payRes.value.data || []
  if (actRes.status === 'fulfilled') actionHistory.value = actRes.value.data || []
  if (empRes.status === 'fulfilled') employeeOptions.value = empRes.value.data.filter(e => e.status === 'активный').map(e => ({ id: e.id, label: `${e.full_name} (${e.position})` }))
  if (card.value?.contract_id) {
    const [cRes, fRes, tRes] = await Promise.allSettled([contractsApi.getById(card.value.contract_id), filesApi.getContractFiles(card.value.contract_id), crmApi.getTimeline(card.value.contract_id)])
    if (cRes.status === 'fulfilled') contractData.value = cRes.value.data
    if (fRes.status === 'fulfilled') projectFiles.value = fRes.value.data || []
    if (tRes.status === 'fulfilled') timelineEntries.value = tRes.value.data || []
  }
}

onMounted(async () => { const id = route.params.id; await crmStore.loadCard(id); await loadAdditionalData(id) })
</script>
