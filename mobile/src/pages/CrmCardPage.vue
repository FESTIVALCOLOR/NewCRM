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
          <div class="row items-center q-gutter-sm text-caption q-mt-xs" style="color: #888">
            <span v-if="card.project_type">{{ card.project_type }}</span>
            <span v-if="card.project_subtype"> · {{ card.project_subtype }}</span>
            <span v-if="card.area">{{ card.area }} м²</span>
            <span v-if="card.city">{{ card.city }}</span>
            <q-btn v-if="contractData?.yandex_folder_path && canSeeYdFolder" flat dense size="xs" icon="folder_open" label="ЯД" no-caps style="color: #F39C12; font-size: 10px" @click="openYdFolder" />
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
        <q-tab v-if="can('crm_cards.payments')" name="payments" label="Оплаты" />
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

          <!-- Workflow действия (всегда видимы) -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold" style="color: #333">Действия</div></q-card-section>
            <q-card-section>
              <!-- Сдать работу -->
              <q-btn v-if="card.workflow_status === 'in_progress'" unelevated dense no-caps icon="check" label="Сдать работу" class="full-width q-mb-sm" style="background: #58D68D; color: white; font-size: 12px; font-weight: bold; height: 36px; border-radius: 4px" @click="doAction('submit')" :loading="actionLoading" />

              <!-- Проверяющий: Клиенту + На исправление -->
              <div v-if="can('crm_cards.complete_approval') && card.workflow_status === 'pending_review'" class="row q-gutter-sm q-mb-sm">
                <q-btn unelevated dense no-caps icon="forward_to_inbox" label="Отправить клиенту" style="background: #58D68D; color: white; font-size: 11px; font-weight: bold; height: 36px; border-radius: 4px; flex: 1" @click="doAction('client-send')" :loading="actionLoading" />
                <q-btn unelevated dense no-caps icon="replay" label="На исправление" style="background: #F1948A; color: white; font-size: 11px; font-weight: bold; height: 36px; border-radius: 4px; flex: 1" @click="showRejectDialog = true" />
              </div>

              <!-- Клиент согласовал -->
              <q-btn v-if="can('crm_cards.complete_approval') && card.workflow_status === 'client_approval'" unelevated dense no-caps icon="thumb_up" label="Клиент согласовал" class="full-width q-mb-sm" style="background: #27AE60; color: white; font-size: 12px; font-weight: bold; height: 36px; border-radius: 4px" @click="doAction('client-approved')" :loading="actionLoading" />

              <!-- Акт -->
              <div v-if="can('crm_cards.complete_approval') && card.workflow_status === 'act_signing'" class="row q-gutter-sm q-mb-sm">
                <q-btn unelevated dense no-caps label="Отправить акт" style="background: #58D68D; color: white; font-size: 11px; font-weight: bold; height: 36px; border-radius: 4px; flex: 1" @click="doAction('client-send')" :loading="actionLoading" />
                <q-btn unelevated dense no-caps icon="draw" label="Акт подписан" style="background: #85C1E9; color: white; font-size: 11px; font-weight: bold; height: 36px; border-radius: 4px; flex: 1" @click="doAction('sign-act')" :loading="actionLoading" />
              </div>

              <div v-if="!card.workflow_status" class="text-center" style="color: #999; font-size: 12px; padding: 8px 0">Нет активного рабочего процесса</div>
            </q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 2: Таблица сроков (из timeline API) ====== -->
        <q-tab-panel name="timeline" class="q-pa-none">
          <q-card class="is-card">
            <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold" style="color: #333">Таблица сроков</div></q-card-section>
            <q-list dense separator v-if="timelineEntries.length > 0">
              <q-item v-for="e in timelineEntries" :key="e.id" :style="timelineRowStyle(e)">
                <q-item-section avatar v-if="e.executor_role !== 'header'" style="min-width: 24px">
                  <q-icon :name="timelineIcon(e)" :color="timelineIconColor(e)" size="18px" />
                </q-item-section>
                <q-item-section :style="e.executor_role === 'header' ? 'padding-left: 4px' : ''">
                  <q-item-label :style="{ fontSize: e.executor_role === 'header' ? '12px' : '11px', color: '#333', fontWeight: e.executor_role === 'header' || isActiveSubstep(e) ? 'bold' : 'normal' }">{{ e.stage_name }}</q-item-label>
                  <q-item-label v-if="e.executor_role !== 'header'" caption :style="{ color: isOverdue(e) ? '#E74C3C' : '#888' }">
                    <span v-if="e.norm_days">Норма: {{ e.custom_norm_days || e.norm_days }} дн.</span>
                    <span v-if="e.actual_days"> | Факт: {{ e.actual_days }} дн.</span>
                    <span v-if="e.executor_role"> | {{ e.executor_role }}</span>
                    <span v-if="isOverdue(e)" style="color: #E74C3C; font-weight: bold"> | Просрочен</span>
                    <span v-else-if="e.actual_date && !isOverdue(e)" style="color: #27AE60"> | В срок</span>
                  </q-item-label>
                </q-item-section>
                <q-item-section side v-if="e.actual_date">
                  <div class="text-caption" :style="{ color: isOverdue(e) ? '#E74C3C' : '#27AE60' }">{{ fmtDateShort(e.actual_date) }}</div>
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
              <q-item v-for="f in filesByStage('tech_task')" :key="f.id" >
                <q-item-section avatar><q-icon :name="fileIcon(f)" :color="fileColor(f)" /></q-item-section>
                <q-item-section><q-item-label style="font-size: 12px">{{ f.file_name }}</q-item-label></q-item-section>
                <q-item-section side><div class="row q-gutter-xs"><q-btn outline dense size="xs" icon="open_in_new" no-caps color="grey-7" style="padding: 2px 6px; border-radius: 4px" @click.stop="openFile(f)" /><q-btn v-if="can('crm_cards.files_delete')" outline dense size="xs" icon="delete_outline" no-caps color="negative" style="padding: 2px 6px; border-radius: 4px" @click.stop="deleteFile(f)" /></div></q-item-section>
              </q-item>
            </q-list>
            <q-card-section class="q-pt-xs"><div class="row q-gutter-xs"><q-btn v-if="can('crm_cards.files_upload')" outline color="grey-7" icon="upload" label="Загрузить" no-caps dense @click="uploadCrmFile('tech_task')" /><q-btn v-if="contractData?.tech_task_link" flat color="grey-7" icon="open_in_new" label="ЯД" no-caps dense @click="openLink(contractData.tech_task_link)" /></div></q-card-section>
          </q-card>

          <!-- Замер -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-xs"><div class="text-subtitle2 text-weight-bold" style="color: #333">Замер</div></q-card-section>
            <q-list dense v-if="filesByStage('measurement').length > 0">
              <q-item v-for="f in filesByStage('measurement')" :key="f.id" >
                <q-item-section avatar><q-icon :name="fileIcon(f)" :color="fileColor(f)" /></q-item-section>
                <q-item-section><q-item-label style="font-size: 12px">{{ f.file_name }}</q-item-label></q-item-section>
                <q-item-section side><div class="row q-gutter-xs"><q-btn outline dense size="xs" icon="open_in_new" no-caps color="grey-7" style="padding: 2px 6px; border-radius: 4px" @click.stop="openFile(f)" /><q-btn v-if="can('crm_cards.files_delete')" outline dense size="xs" icon="delete_outline" no-caps color="negative" style="padding: 2px 6px; border-radius: 4px" @click.stop="deleteFile(f)" /></div></q-item-section>
              </q-item>
            </q-list>
            <q-card-section class="q-pt-xs"><q-btn v-if="can('crm_cards.files_upload')" outline color="grey-7" icon="upload" label="Загрузить" no-caps dense @click="uploadCrmFile('measurement')" /></q-card-section>
          </q-card>

          <!-- Фотофиксация -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-xs"><div class="text-subtitle2 text-weight-bold" style="color: #333">Фотофиксация</div></q-card-section>
            <q-list dense v-if="filesByStage('photo_documentation').length > 0">
              <q-item v-for="f in filesByStage('photo_documentation')" :key="f.id"><q-item-section avatar><q-icon :name="fileIcon(f)" :color="fileColor(f)" /></q-item-section><q-item-section><q-item-label style="font-size: 12px">{{ f.file_name }}</q-item-label></q-item-section><q-item-section side><div class="row q-gutter-xs"><q-btn outline dense size="xs" icon="open_in_new" no-caps color="grey-7" style="padding: 2px 6px; border-radius: 4px" @click.stop="openFile(f)" /><q-btn v-if="can('crm_cards.files_delete')" outline dense size="xs" icon="delete_outline" no-caps color="negative" style="padding: 2px 6px; border-radius: 4px" @click.stop="deleteFile(f)" /></div></q-item-section></q-item>
            </q-list>
            <q-card-section class="q-pt-xs"><q-btn v-if="can('crm_cards.files_upload')" outline color="grey-7" icon="upload" label="Загрузить" no-caps dense @click="uploadCrmFile('photo_documentation')" /></q-card-section>
          </q-card>

          <!-- Референсы -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-xs"><div class="text-subtitle2 text-weight-bold" style="color: #333">{{ card.project_type === 'Шаблонный' ? 'Шаблоны' : 'Референсы' }}</div></q-card-section>
            <q-list dense v-if="filesByStage('references').length > 0">
              <q-item v-for="f in filesByStage('references')" :key="f.id"><q-item-section avatar><q-icon :name="fileIcon(f)" :color="fileColor(f)" /></q-item-section><q-item-section><q-item-label style="font-size: 12px">{{ f.file_name }}</q-item-label></q-item-section><q-item-section side><div class="row q-gutter-xs"><q-btn outline dense size="xs" icon="open_in_new" no-caps color="grey-7" style="padding: 2px 6px; border-radius: 4px" @click.stop="openFile(f)" /><q-btn v-if="can('crm_cards.files_delete')" outline dense size="xs" icon="delete_outline" no-caps color="negative" style="padding: 2px 6px; border-radius: 4px" @click.stop="deleteFile(f)" /></div></q-item-section></q-item>
            </q-list>
            <q-card-section class="q-pt-xs"><q-btn v-if="can('crm_cards.files_upload')" outline color="grey-7" icon="upload" label="Загрузить" no-caps dense @click="uploadCrmFile('references')" /></q-card-section>
          </q-card>

          <!-- Стадии проекта с вкладками вариаций (как в десктопе) -->
          <q-card v-for="stage in projectStages" :key="stage.code" class="is-card q-mb-md" :style="isCurrentStage(stage.code) ? 'border: 2px solid #27AE60' : ''">
            <q-card-section class="q-pb-xs">
              <div class="row items-center justify-between">
                <div class="text-subtitle2 text-weight-bold" style="color: #333">{{ stage.label }}</div>
                <div class="row q-gutter-xs">
                  <q-btn v-if="can('crm_cards.files_upload')" outline dense size="xs" icon="upload" label="Загрузить" no-caps color="grey-7" style="border-radius: 4px; padding: 2px 8px" @click="uploadToVariation(stage.code)" />
                  <q-btn v-if="can('crm_cards.files_upload')" outline dense size="xs" icon="create_new_folder" no-caps color="grey-7" style="border-radius: 4px; padding: 2px 6px" @click="addVariationTab(stage.code)"><q-tooltip>Добавить вариацию</q-tooltip></q-btn>
                  <q-btn v-if="getVariations(stage.code).length > 1" outline dense size="xs" icon="delete_outline" no-caps color="negative" style="border-radius: 4px; padding: 2px 6px" @click="deleteVariationTab(stage.code)"><q-tooltip>Удалить текущую вариацию</q-tooltip></q-btn>
                </div>
              </div>
            </q-card-section>

            <!-- Вкладки вариаций -->
            <q-tabs v-if="getVariations(stage.code).length > 1" v-model="activeVariation[stage.code]" dense active-color="dark" indicator-color="accent" no-caps style="font-size: 11px" align="left">
              <q-tab v-for="v in getVariations(stage.code)" :key="v" :name="v" :label="`Вариация ${v}`" />
            </q-tabs>

            <!-- Файлы текущей вариации -->
            <q-list dense v-if="filesForVariation(stage.code).length > 0">
              <q-item v-for="f in filesForVariation(stage.code)" :key="f.id">
                <q-item-section avatar><q-icon :name="fileIcon(f)" :color="fileColor(f)" /></q-item-section>
                <q-item-section><q-item-label style="font-size: 12px">{{ f.file_name }}</q-item-label></q-item-section>
                <q-item-section side>
                  <div class="row q-gutter-xs">
                    <q-btn outline dense size="xs" icon="open_in_new" no-caps color="grey-7" style="padding: 2px 6px; border-radius: 4px" @click.stop="openFile(f)" />
                    <q-btn v-if="can('crm_cards.files_delete')" outline dense size="xs" icon="delete_outline" no-caps color="negative" style="padding: 2px 6px; border-radius: 4px" @click.stop="deleteFile(f)" />
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="q-py-sm text-center" style="color: #bbb; font-size: 11px">Нет файлов</q-card-section>
            <div class="q-pb-sm" />
          </q-card>

          <div class="q-mb-xl" />
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
                  <q-item-label style="font-size: 12px; color: #333" class="text-weight-medium">{{ p.employee_name || 'Не указан' }}</q-item-label>
                  <q-item-label caption style="color: #888">{{ p.stage_name || '' }}</q-item-label>
                  <q-item-label v-if="p.is_paid || p.payment_status === 'paid'" caption style="color: #aaa; font-size: 10px">оплачено</q-item-label>
                  <q-item-label v-else-if="p.report_month || p.payment_status === 'to_pay'" caption style="color: #aaa; font-size: 10px">к оплате</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <div class="text-right">
                    <div class="row items-center justify-end no-wrap">
                      <div class="text-weight-bold" style="font-size: 13px" :style="{ color: p.is_paid ? '#27AE60' : '#333' }">{{ fmtMoney(p.final_amount || p.amount) }}</div>
                      <span class="text-caption q-ml-xs" style="color: #888">{{ p.payment_subtype || '' }}</span>
                      <div style="width: 1px; height: 14px; background: #ddd; margin: 0 6px"></div>
                      <div class="text-caption" :style="{ color: p.report_month ? '#333' : '#bbb' }">{{ formatReportMonth(p.report_month) }}</div>
                    </div>
                    <div class="row items-center justify-end q-gutter-xs q-mt-xs">
                      <q-btn flat round dense size="xs" icon="edit" color="grey-7" @click.stop="editPaymentAmount(p)" />
                      <q-btn flat round dense size="xs" icon="delete_outline" color="negative" @click.stop="deletePayment(p)" />
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
            <q-select v-model="assignEmployeeId" :options="employeeOptions" option-value="id" option-label="label" label="Сотрудник" outlined dense emit-value map-options use-input input-debounce="200" @filter="filterAssignEmployees" class="q-mb-sm" />
            <q-input v-if="assignNeedsDeadline" v-model="assignDeadline" label="Дедлайн" outlined dense type="date" class="q-mb-sm" />
          </q-card-section>
          <q-card-actions align="right"><q-btn flat label="Отмена" v-close-popup no-caps /><q-btn unelevated label="Назначить" style="background: #ffd93c; color: #333; border-radius: 4px" no-caps @click="doAssign" :loading="actionLoading" /></q-card-actions>
        </q-card>
      </q-dialog>

      <!-- FAB кнопки -->
      <q-page-sticky position="bottom-right" :offset="[18, 18]">
        <div class="column q-gutter-sm items-end">
          <q-btn round icon="sync" size="md" style="background: #5DADE2; color: white" @click="syncCrmWithYd" :loading="crmSyncing">
            <q-tooltip>Синхронизировать с ЯД</q-tooltip>
          </q-btn>
          <q-btn fab icon="edit" style="background: #ffd93c; color: #333" @click="editCard" />
        </div>
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
import { useAuthStore } from 'src/stores/auth'
import { useReferencesStore } from 'src/stores/references'
import { usePermission } from 'src/composables/usePermission'
import { calcDeadlineFromTimeline } from 'src/composables/useDeadline'
import { crmApi, employeesApi, filesApi, contractsApi, paymentsApi } from 'src/services/api'

const { can, isSuperuser } = usePermission()

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
const crmSyncing = ref(false)
const crmUploadVariation = ref(1)
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
const assignMode = ref('assign') // 'assign' или 'change'

const agentColor = computed(() => refs.agentByName(card.value?.agent_type)?.color || '#95A5A6')

// Папка ЯД видна только руководителю, СДП, ГАП, менеджерам
const canSeeYdFolder = computed(() => {
  if (isSuperuser.value) return true
  const auth = useAuthStore()
  const pos = auth.user?.position || ''
  const secPos = auth.user?.secondary_position || ''
  const allowed = ['Руководитель студии', 'Старший менеджер проектов', 'СДП', 'ГАП', 'Менеджер']
  return allowed.includes(pos) || allowed.includes(secPos)
})
const allEmployeesList = ref([])

// Маппинг roleKey → фильтр по должности
const ROLE_POSITION_FILTER = {
  senior_manager: ['Старший менеджер', 'Руководитель'],
  sdp: ['Руководитель студии', 'СДП'],
  gap: ['ГАП', 'руководитель'],
  manager: ['Менеджер', 'Старший менеджер'],
  surveyor: ['Замерщик'],
  designer: ['Дизайнер'],
  draftsman: ['Чертёжник', 'Чертежник']
}

function filterAssignEmployees(val, update) {
  let list = allEmployeesList.value
  // Фильтр по роли назначения
  const posFilters = ROLE_POSITION_FILTER[assignRoleKey.value]
  if (posFilters) {
    const filtered = list.filter(e => posFilters.some(pf => (e.position || '').toLowerCase().includes(pf.toLowerCase())))
    if (filtered.length > 0) list = filtered // fallback на всех если никто не подходит
  }
  const makeOpts = (emps) => {
    const byPos = {}
    for (const e of emps) { const pos = e.position || 'Прочие'; if (!byPos[pos]) byPos[pos] = []; byPos[pos].push(e) }
    const opts = []
    for (const [pos, items] of Object.entries(byPos).sort((a, b) => a[0].localeCompare(b[0]))) {
      opts.push({ id: null, label: `── ${pos} ──`, disable: true })
      for (const e of items) opts.push({ id: e.id, label: e.full_name })
    }
    return opts
  }
  if (!val) { update(() => { employeeOptions.value = makeOpts(list) }); return }
  const q = val.toLowerCase()
  update(() => { employeeOptions.value = makeOpts(list.filter(e => (e.full_name || '').toLowerCase().includes(q))) })
}

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

// Команда — руководство + исполнители ПО СТАДИЯМ из stage_executors
const allTeamMembers = computed(() => {
  if (!card.value) return []
  const canAssign = can('crm_cards.assign_executor')
  const canRemove = can('crm_cards.delete_executor')
  const canManageTeam = canAssign || canRemove

  // Руководство проекта (единые для всего проекта)
  const members = [
    { roleKey: 'senior_manager', role: 'Ст. менеджер', name: card.value.senior_manager_name, canManage: canManageTeam },
  ]
  if (card.value.project_type === 'Индивидуальный') {
    members.push({ roleKey: 'sdp', role: 'СДП', name: card.value.sdp_name, canManage: canManageTeam })
  }
  members.push(
    { roleKey: 'gap', role: 'ГАП', name: card.value.gap_name, canManage: canManageTeam },
    { roleKey: 'manager', role: 'Менеджер', name: card.value.manager_name, canManage: canManageTeam },
    { roleKey: 'surveyor', role: 'Замерщик', name: card.value.surveyor_name, canManage: canManageTeam },
  )

  // Исполнители ПО СТАДИЯМ — определяем все стадии проекта и показываем назначенных
  const se = card.value.stage_executors || []
  const isTemplate = card.value.project_type === 'Шаблонный'

  // Все стадии проекта с ролями (порядок как в десктопе)
  const allStages = isTemplate ? [
    { stageName: 'Стадия 1: планировочные решения', roleKey: 'draftsman', role: 'Чертёжник' },
    { stageName: 'Стадия 2: рабочие чертежи', roleKey: 'draftsman', role: 'Чертёжник' },
    { stageName: 'Стадия 3: 3д визуализация (Дополнительная)', roleKey: 'designer', role: 'Дизайнер' },
  ] : [
    { stageName: 'Стадия 1: планировочные решения', roleKey: 'draftsman', role: 'Чертёжник' },
    { stageName: 'Стадия 2: концепция дизайна', roleKey: 'designer', role: 'Дизайнер' },
    { stageName: 'Стадия 3: рабочие чертежи', roleKey: 'draftsman', role: 'Чертёжник' },
  ]

  for (const stage of allStages) {
    // Ищем последнего назначенного на эту стадию (max id)
    const candidates = se.filter(s => s.stage_name === stage.stageName)
    const executor = candidates.length ? candidates.reduce((a, b) => a.id > b.id ? a : b) : null

    members.push({
      roleKey: stage.roleKey,
      role: `${stage.role} — ${stage.stageName}`,
      name: executor?.executor_name || null,
      deadline: executor?.deadline,
      canManage: canManageTeam,
      stageName: stage.stageName,
      isStageExecutor: true,
    })
  }

  return members
})

const stageExecutors = computed(() => card.value?.stage_executors || [])
const completedStages = computed(() => stageExecutors.value.filter(se => se.completed))

function filesByStage(stage) { return projectFiles.value.filter(f => f.stage === stage) }

// Вариации — вкладки как в десктопе
const activeVariation = ref({}) // { stage_code: active_variation_number }
const createdVariations = ref({}) // { stage_code: [variation_numbers] }

function getVariations(stageCode) {
  const files = filesByStage(stageCode)
  const varsSet = new Set(files.map(f => f.variation || 1))
  // Добавляем вручную созданные вариации (которые ещё без файлов)
  const created = createdVariations.value[stageCode] || []
  for (const v of created) varsSet.add(v)
  if (varsSet.size === 0) varsSet.add(1)
  if (!activeVariation.value[stageCode]) activeVariation.value[stageCode] = Math.min(...varsSet)
  return [...varsSet].sort((a, b) => a - b)
}

function filesForVariation(stageCode) {
  const v = activeVariation.value[stageCode] || 1
  return projectFiles.value.filter(f => f.stage === stageCode && (f.variation || 1) === v)
}

function uploadToVariation(stageCode) {
  const v = activeVariation.value[stageCode] || 1
  crmUploadStage.value = stageCode
  crmUploadVariation.value = v
  crmFileInput.value?.click()
}

function addVariationTab(stageCode) {
  const vars = getVariations(stageCode)
  const nextVar = vars.length > 0 ? Math.max(...vars) + 1 : 2
  // Регистрируем вариацию (массив для реактивности Vue) + переключаемся
  const existing = createdVariations.value[stageCode] || []
  createdVariations.value = { ...createdVariations.value, [stageCode]: [...existing, nextVar] }
  activeVariation.value = { ...activeVariation.value, [stageCode]: nextVar }
  $q.notify({ type: 'positive', message: `Вариация ${nextVar} создана. Загрузите в неё файлы.` })
}

function deleteVariationTab(stageCode) {
  const v = activeVariation.value[stageCode] || 1
  const varFiles = projectFiles.value.filter(f => f.stage === stageCode && (f.variation || 1) === v)
  $q.dialog({
    title: `Удалить Вариацию ${v}?`,
    message: `${varFiles.length} файлов будет удалено`,
    cancel: { label: 'Нет', flat: true, noCaps: true },
    ok: { label: 'Да, удалить', noCaps: true, color: 'negative' }
  }).onOk(async () => {
    for (const f of varFiles) {
      try {
        const { api: ax } = await import('src/boot/axios')
        await ax.delete(`/api/v1/files/${f.id}`)
      } catch {}
    }
    projectFiles.value = projectFiles.value.filter(f => !(f.stage === stageCode && (f.variation || 1) === v))
    // Переключиться на Вариацию 1
    activeVariation.value[stageCode] = 1
    $q.notify({ type: 'positive', message: `Вариация ${v} удалена` })
  })
}

// Текущая стадия карточки (по column_name)
function isCurrentStage(stageCode) {
  const col = (card.value?.column_name || '').toLowerCase()
  if (stageCode === 'stage1' && col.includes('планировочн')) return true
  if (stageCode === 'stage2_concept' && col.includes('концепция')) return true
  if (stageCode === 'stage2_3d' && col.includes('визуализац')) return true
  if (stageCode === 'stage3' && col.includes('чертеж')) return true
  return false
}

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

// Таймлайн: просрочен если actual_days > norm_days (как десктоп timeline_widget.py:828-834)
function isOverdue(e) {
  if (!e.actual_date || e.executor_role === 'header') return false
  const norm = e.custom_norm_days || e.norm_days || 0
  return norm > 0 && (e.actual_days || 0) > norm
}
// Текущий активный подэтап (current_substep_code)
function isActiveSubstep(e) {
  return e.stage_code && card.value?.current_substep_code === e.stage_code && !e.actual_date
}
function timelineRowStyle(e) {
  if (e.executor_role === 'header') return 'background: #F5F5F5'
  if (isActiveSubstep(e)) return 'border: 2px solid #4CAF50; border-radius: 4px'
  if (e.actual_date && isOverdue(e)) return 'background: #FFEBEE'
  if (e.actual_date && !isOverdue(e)) return 'background: #E8F5E9'
  if (e.status === 'skipped') return 'background: #F5F5F5; opacity: 0.6'
  return ''
}
function timelineIcon(e) {
  if (e.executor_role === 'header') return ''
  if (isActiveSubstep(e)) return 'play_circle'
  if (e.actual_date) return 'check_circle'
  if (e.status === 'skipped') return 'skip_next'
  return 'radio_button_unchecked'
}
function timelineIconColor(e) {
  if (isActiveSubstep(e)) return 'positive'
  if (e.actual_date && isOverdue(e)) return 'negative'
  if (e.actual_date) return 'positive'
  if (e.status === 'skipped') return 'grey-4'
  return 'grey-5'
}
function fmtDateTime(d) { if (!d) return ''; return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) }
function fmtMoney(v) { if (!v) return '0 ₽'; return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(v) }
function openLink(url) { if (url) window.open(url, '_blank') }
async function openYdFolder() {
  const rawPath = contractData.value?.yandex_folder_path
  if (!rawPath) return
  // Убираем disk: prefix если есть — API ожидает путь без него
  const path = rawPath.replace(/^disk:/, '')
  try {
    const { data } = await filesApi.getPublicLink(path)
    const url = data.public_link || data.public_url || data.href
    if (url) window.open(url, '_blank')
    else $q.notify({ type: 'warning', message: 'Не удалось получить ссылку на папку' })
  } catch {
    // Fallback: открываем ЯД web-клиент напрямую (требует логина в ЯД)
    const encoded = path.split('/').map(s => encodeURIComponent(s)).join('/')
    window.open(`https://disk.yandex.ru/client/disk${encoded}`, '_blank')
  }
}
function openFile(f) { if (f.public_link) window.open(f.public_link, '_blank') }
function fileIcon(f) { const n = (f.file_name||'').toLowerCase(); if (n.endsWith('.pdf')) return 'picture_as_pdf'; if (n.match(/\.(jpg|jpeg|png|webp)$/)) return 'image'; return 'insert_drive_file' }
function fileColor(f) { const n = (f.file_name||'').toLowerCase(); if (n.endsWith('.pdf')) return 'red'; if (n.match(/\.(jpg|jpeg|png|webp)$/)) return 'green'; return 'grey-7' }
function actionIcon(t) { if (!t) return 'history'; const l=t.toLowerCase(); if (l.includes('move')||l.includes('column')) return 'swap_horiz'; if (l.includes('assign')) return 'person_add'; if (l.includes('submit')) return 'send'; if (l.includes('accept')) return 'check_circle'; if (l.includes('reject')) return 'replay'; if (l.includes('payment')) return 'payments'; if (l.includes('deadline')) return 'event'; if (l.includes('file')) return 'attach_file'; return 'history' }
function actionColor(t) { if (!t) return 'grey-5'; const l=t.toLowerCase(); if (l.includes('accept')||l.includes('complete')) return 'positive'; if (l.includes('reject')) return 'negative'; if (l.includes('submit')) return 'info'; return 'grey-7' }

// === ACTIONS ===
function editCard() {
  if (card.value?.contract_id) {
    $q.notify({ type: 'info', message: 'Переход к карточке договора', icon: 'open_in_new', timeout: 1500 })
    setTimeout(() => router.push(`/contracts/${card.value.contract_id}`), 300)
  }
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
  assignMode.value = mode
  assignNeedsDeadline.value = ['designer', 'draftsman'].includes(member.roleKey)
  assignDialogTitle.value = mode === 'assign' ? `Назначить ${member.role}` : `Изменить ${member.role}`
  assignEmployeeId.value = null
  assignDeadline.value = ''

  // Автоподстановка дедлайна из timeline (как в десктопе)
  if (assignNeedsDeadline.value && timelineEntries.value.length > 0) {
    // Определяем стадию: из stageName, или по roleKey (как в doAssign)
    let stageName = member.stageName || ''
    if (!stageName) {
      const isTemplate = card.value?.project_type === 'Шаблонный'
      if (member.roleKey === 'designer') stageName = isTemplate ? 'Стадия 3: 3д визуализация (Дополнительная)' : 'Стадия 2: концепция дизайна'
      else if (member.roleKey === 'draftsman') stageName = isTemplate ? 'Стадия 2: рабочие чертежи' : 'Стадия 3: рабочие чертежи'
    }
    const autoDeadline = calcDeadlineFromTimeline(timelineEntries.value, stageName)
    if (autoDeadline) assignDeadline.value = autoDeadline
  }
  // Fallback: today + 7 дней
  if (assignNeedsDeadline.value && !assignDeadline.value) {
    const d = new Date(); d.setDate(d.getDate() + 7)
    assignDeadline.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  }

  filterAssignEmployees('', (fn) => fn())
  assignDialogVisible.value = true
}

// Маппинг roleKey → ТОЧНЫЕ названия ролей как в десктопе (crm_card_edit_dialog.py line 1091-1106)
const ROLE_NAMES = { senior_manager: 'Старший менеджер проектов', sdp: 'СДП', gap: 'ГАП', manager: 'Менеджер', surveyor: 'Замерщик', designer: 'Дизайнер', draftsman: 'Чертёжник' }

async function doAssign() {
  if (!assignEmployeeId.value) return
  actionLoading.value = true
  try {
    const roleKey = assignRoleKey.value
    const roleName = ROLE_NAMES[roleKey] || assignRole.value
    const isReassign = assignMode.value === 'change'
    const isTemplate = card.value?.project_type === 'Шаблонный'

    // Определяем stageName для дизайнера/чертёжника
    let stageName = assignStageName.value
    if (['designer', 'draftsman'].includes(roleKey) && !stageName) {
      if (roleKey === 'designer') stageName = isTemplate ? 'Стадия 3: 3д визуализация (Дополнительная)' : 'Стадия 2: концепция дизайна'
      else stageName = isTemplate ? 'Стадия 2: рабочие чертежи' : 'Стадия 3: рабочие чертежи'
    }

    // === ПЕРЕНАЗНАЧЕНИЕ (как десктоп ReassignExecutorDialog) ===
    if (isReassign && ['designer', 'draftsman'].includes(roleKey) && stageName) {
      // Находим старого исполнителя
      const se = card.value.stage_executors || []
      const oldSe = se.filter(s => (s.stage_name || '').toLowerCase().includes(stageName.toLowerCase().split(':')[1]?.trim().substring(0, 10) || ''))
        .sort((a, b) => b.id - a.id)[0]
      const oldExecutorId = oldSe?.executor_id

      // 1. PATCH stage_executor — обновляем исполнителя, сбрасываем completed
      await crmApi.reassignExecutor(card.value.id, stageName, {
        executor_id: assignEmployeeId.value,
        deadline: assignDeadline.value || null,
        completed: false
      })

      // 2. Двойная запись оплат (как десктоп _reassign_payments_via_api)
      if (oldExecutorId && oldExecutorId !== assignEmployeeId.value) {
        // Помечаем старые оплаты как reassigned
        const oldPayments = cardPayments.value.filter(p =>
          p.employee_id === oldExecutorId && p.role === roleName && !p.reassigned
        )
        for (const op of oldPayments) {
          try {
            const month = `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`
            await paymentsApi.update(op.id, { reassigned: true, report_month: op.report_month || month })
          } catch {}
        }

        // Создаём новые оплаты для нового исполнителя
        try {
          const calcRes = await paymentsApi.calculate({ contract_id: card.value.contract_id, employee_id: assignEmployeeId.value, role: roleName })
          const fullAmount = typeof calcRes.data === 'number' ? calcRes.data : (calcRes.data?.amount || 0)
          if (fullAmount > 0) {
            const month = `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`
            if (isTemplate) {
              await paymentsApi.create({ contract_id: card.value.contract_id, employee_id: assignEmployeeId.value, role: roleName, payment_type: 'Полная оплата', crm_card_id: card.value.id, calculated_amount: fullAmount, final_amount: fullAmount, report_month: null })
            } else {
              const advance = Math.round(fullAmount / 2)
              const balance = fullAmount - advance
              await paymentsApi.create({ contract_id: card.value.contract_id, employee_id: assignEmployeeId.value, role: roleName, payment_type: 'Аванс', crm_card_id: card.value.id, calculated_amount: advance, final_amount: advance, report_month: month })
              await paymentsApi.create({ contract_id: card.value.contract_id, employee_id: assignEmployeeId.value, role: roleName, payment_type: 'Доплата', crm_card_id: card.value.id, calculated_amount: balance, final_amount: balance, report_month: null })
            }
          }
        } catch (e) { console.warn('Ошибка создания оплат при переназначении:', e) }

        // История
        try {
          const oldName = allEmployeesList.value.find(e => e.id === oldExecutorId)?.full_name || ''
          const newName = allEmployeesList.value.find(e => e.id === assignEmployeeId.value)?.full_name || ''
          const { api: ax } = await import('src/boot/axios')
          await ax.post('/api/v1/action-history', { action_type: 'reassign', entity_type: 'crm_card', entity_id: card.value.id, description: `Переназначен ${roleName}: ${oldName} → ${newName} (${stageName})` })
        } catch {}
      }

      $q.notify({ type: 'positive', message: 'Исполнитель переназначен' })

    // === НОВОЕ НАЗНАЧЕНИЕ ===
    } else {
      // Назначаем
      if (['designer', 'draftsman'].includes(roleKey) && stageName) {
        // Дизайнер/Чертёжник — upsert в stage_executors (сервер сам обновит если есть)
        await crmApi.assignExecutor(card.value.id, { stage_name: stageName, executor_id: assignEmployeeId.value, deadline: assignDeadline.value || null })
        // Оплата НЕ создаётся здесь — только при ПЕРЕМЕЩЕНИИ на стадию
      } else if (roleKey === 'surveyor') {
        // Замерщик — назначаем без оплаты (оплата при загрузке замера)
        await crmApi.updateCard(card.value.id, { surveyor_id: assignEmployeeId.value })
        // Создаём запись оплаты БЕЗ report_month (будет заполнен при загрузке замера)
        try {
          const calcRes = await paymentsApi.calculate({ contract_id: card.value.contract_id, employee_id: assignEmployeeId.value, role: roleName })
          const fullAmount = typeof calcRes.data === 'number' ? calcRes.data : (calcRes.data?.amount || 0)
          if (fullAmount > 0) {
            await paymentsApi.create({ contract_id: card.value.contract_id, employee_id: assignEmployeeId.value, role: roleName, payment_type: 'Полная оплата', crm_card_id: card.value.id, calculated_amount: fullAmount, final_amount: fullAmount, report_month: null })
          }
        } catch {}
      } else {
        // Руководство (СМ, СДП, ГАП, Менеджер) — назначение + оплата сразу
        const update = {}; update[`${roleKey}_id`] = assignEmployeeId.value
        await crmApi.updateCard(card.value.id, update)

        // Удаляем старые оплаты для этой роли
        const oldPayments = cardPayments.value.filter(p => p.role === roleName)
        for (const op of oldPayments) { try { await paymentsApi.delete(op.id) } catch {} }

        // Создаём оплату (шаблонные: СМ и Менеджер без оплаты)
        const skipPayment = isTemplate && ['senior_manager', 'manager'].includes(roleKey)
        if (!skipPayment) {
          try {
            const calcRes = await paymentsApi.calculate({ contract_id: card.value.contract_id, employee_id: assignEmployeeId.value, role: roleName })
            const fullAmount = typeof calcRes.data === 'number' ? calcRes.data : (calcRes.data?.amount || 0)
            if (fullAmount > 0) {
              if (roleKey === 'sdp') {
                // СДП: Аванс 50% + Доплата 50%
                const advance = Math.round(fullAmount / 2)
                const balance = fullAmount - advance
                const month = `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`
                await paymentsApi.create({ contract_id: card.value.contract_id, employee_id: assignEmployeeId.value, role: roleName, payment_type: 'Аванс', crm_card_id: card.value.id, calculated_amount: advance, final_amount: advance, report_month: month })
                await paymentsApi.create({ contract_id: card.value.contract_id, employee_id: assignEmployeeId.value, role: roleName, payment_type: 'Доплата', crm_card_id: card.value.id, calculated_amount: balance, final_amount: balance, report_month: null })
              } else {
                await paymentsApi.create({ contract_id: card.value.contract_id, employee_id: assignEmployeeId.value, role: roleName, payment_type: 'Полная оплата', crm_card_id: card.value.id, calculated_amount: fullAmount, final_amount: fullAmount, report_month: null })
              }
            }
          } catch (e) { console.warn('Ошибка оплаты:', e) }
        }
      }

      // История
      try {
        const empName = allEmployeesList.value.find(e => e.id === assignEmployeeId.value)?.full_name || ''
        const { api: ax } = await import('src/boot/axios')
        await ax.post('/api/v1/action-history', { action_type: 'executor_assigned', entity_type: 'crm_card', entity_id: card.value.id, description: `Назначен ${roleName}: ${empName}` })
      } catch {}

      $q.notify({ type: 'positive', message: 'Назначен' })
    }

    assignDialogVisible.value = false
    await reloadCard()
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  finally { actionLoading.value = false }
}

async function removeTeamMember(member) {
  $q.dialog({ title: 'Убрать исполнителя?', message: `${member.role}: ${member.name}`, cancel: { label: 'Нет', flat: true, noCaps: true }, ok: { label: 'Да', noCaps: true, color: 'negative' } }).onOk(async () => {
    try {
      // 1. Удаляем оплаты для этой роли
      const roleName = ROLE_NAMES[member.roleKey] || member.role
      const rolePayments = cardPayments.value.filter(p => p.role === roleName)
      for (const rp of rolePayments) {
        try { await paymentsApi.delete(rp.id) } catch {}
      }
      // 2. Убираем исполнителя
      const update = {}; update[`${member.roleKey}_id`] = null
      await crmApi.updateCard(card.value.id, update)
      $q.notify({ type: 'positive', message: 'Убран + оплаты удалены' }); await reloadCard()
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

function uploadCrmFile(stage) {
  crmUploadStage.value = stage
  crmUploadVariation.value = 1
  crmFileInput.value?.click()
}

async function handleCrmFileUpload(event) {
  const fileList = event.target.files
  if (!fileList?.length || !card.value) return
  try {
    $q.loading.show({ message: 'Загрузка...' })
    const stage = crmUploadStage.value
    const variation = crmUploadVariation.value
    const contractNum = card.value.contract_number || card.value.id
    const contractId = card.value.contract_id

    // Если yandex_folder_path отсутствует — генерируем правильный путь на клиенте
    let contractFolder = (contractData.value?.yandex_folder_path || '').replace(/^disk:/, '')
    if (!contractFolder && contractId) {
      try {
        const { api: ax } = await import('src/boot/axios')
        const { data: c } = await contractsApi.getById(contractId)
        const agent = c.agent_type || 'ФЕСТИВАЛЬ'
        const ptype = c.project_type || 'Индивидуальный'
        const city = c.city || 'МСК'
        const address = (c.address || 'Без адреса').replace(/[/\\<>:"|?*]/g, '-')
        const rawArea = c.area || 0
        const area = Number.isInteger(Number(rawArea)) ? Number(rawArea).toFixed(1) : rawArea
        const typeFolder = ptype.includes('ндивид') ? 'Индивидуальные' : 'Шаблонные'
        const folderName = `${city}-${address}-${area}м2`
        const path = `disk:/CRM/Проекты/${agent}/${typeFolder}/${city}/${folderName}`
        contractFolder = path.replace(/^disk:/, '')
        // Создаём папку на ЯД + обновляем yandex_folder_path в БД
        await ax.post('/api/v1/files/folder', null, { params: { folder_path: path } })
        await contractsApi.update(contractId, { yandex_folder_path: path })
        contractData.value = { ...contractData.value, yandex_folder_path: path }
      } catch (e) { $q.notify({ type: 'warning', message: 'Не удалось создать папку на ЯД' }) }
    }

    // Маппинг stage → подпапка на ЯД (как в десктопе contract_dialogs.py + yandex_disk.py)
    const STAGE_FOLDERS = {
      tech_task: 'Анкета',                                            // ТЗ
      measurement: 'Замер',                                           // Замер
      photo_documentation: 'Фотофиксация',                           // Фото
      references: 'Референсы',                                        // Референсы
      stage1: '1 стадия - Планировочное решение',                     // Стадия 1
      stage2_concept: '2 стадия - Концепция дизайна/Концепция-коллажи', // Стадия 2 концепция
      stage2_3d: '2 стадия - Концепция дизайна/3D визуализация',        // Стадия 2 визуализация
      stage3: '3 стадия - Чертежный проект'                            // Стадия 3
    }

    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i]
      const stageFolder = STAGE_FOLDERS[stage] || stage
      // Вариации только для stage2_concept и stage2_3d (как в десктопе)
      const stagesWithVariation = ['stage2_concept', 'stage2_3d']
      const varSuffix = stagesWithVariation.includes(stage) ? `/Вариация ${variation}` : ''
      if (!contractFolder) {
        $q.notify({ type: 'negative', message: 'Папка проекта на ЯД не создана. Обратитесь к администратору.' })
        break
      }
      const yp = `${contractFolder}/${stageFolder}${varSuffix}/${file.name}`

      // Путь без disk: для upload API И для записи в БД (как десктоп)
      const ypClean = yp.replace(/^disk:/, '')

      // Шаг 1: загрузка на ЯД
      let publicLink = ''
      try {
        const uploadRes = await filesApi.upload(file, ypClean)
        publicLink = uploadRes.data?.public_link || ''
      } catch (uploadErr) {
        $q.notify({ type: 'warning', message: `ЯД: ${uploadErr.response?.status || 'ошибка'}` })
      }

      // Шаг 2: создание записи в БД (как десктоп — с disk: в yandex_path)
      try {
        const { api: ax } = await import('src/boot/axios')
        await ax.post('/api/v1/files/', {
          contract_id: contractId, stage, file_name: file.name,
          file_type: file.type?.includes('image') ? 'image' : file.name.endsWith('.pdf') ? 'pdf' : 'other',
          public_link: publicLink, yandex_path: ypClean,
          file_order: projectFiles.value.length + i + 1, variation
        })
      } catch (dbErr) {
        const d = dbErr.response?.data?.detail
        $q.notify({ type: 'negative', message: `Запись в БД: ${typeof d === 'string' ? d : JSON.stringify(d || dbErr.message)}` })
      }
    }
    $q.notify({ type: 'positive', message: `Загружено: ${fileList.length}` })
    // Перезагрузить файлы
    try { const { data } = await filesApi.getContractFiles(card.value.contract_id); projectFiles.value = data || [] } catch {}
  } catch (err) {
    $q.notify({ type: 'negative', message: err.message || 'Ошибка' })
  } finally { $q.loading.hide(); event.target.value = '' }
}

// === ЗАГРУЗКА ===
async function reloadCard() { const id = route.params.id; await crmStore.loadCard(id); await loadAdditionalData(id) }

async function loadAdditionalData(cardId) {
  // Оплаты — загружаем ВСЕ и фильтруем по crm_card_id
  try {
    const { data } = await crmApi.getPayments(cardId)
    const cid = Number(cardId)
    // Фильтр: только этой карточки, исключая оклады
    cardPayments.value = (data || []).filter(p => Number(p.crm_card_id) === cid && p.source !== 'Оклад')
  } catch (e) { cardPayments.value = [] }

  // История действий
  try {
    const { api: ax } = await import('src/boot/axios')
    const resp = await ax.get(`/api/v1/crm/cards/${cardId}/action-history?_t=${Date.now()}`)
    actionHistory.value = resp.data || []
  } catch (e) {
    actionHistory.value = []
  }

  // Сотрудники
  try {
    const { data } = await employeesApi.getList()
    const all = (data || []).filter(e => e.status === 'активный')
    allEmployeesList.value = all
    employeeOptions.value = all.map(e => ({ id: e.id, label: `${e.full_name} (${e.position})` }))
  } catch (e) { /* ignore */ }

  // Данные контракта + файлы + timeline
  const cid = card.value?.contract_id
  if (!cid) {
    $q.notify({ type: 'warning', message: `contract_id не найден (card loaded: ${!!card.value})`, timeout: 5000 })
    return
  }

  try { const { data } = await contractsApi.getById(cid); contractData.value = data } catch (e) { /* ignore */ }
  try { const { data } = await filesApi.getContractFiles(cid); projectFiles.value = data || [] } catch (e) { projectFiles.value = [] }
  try {
    const { api: ax } = await import('src/boot/axios')
    const resp = await ax.get(`/api/v1/timeline/${cid}?_t=${Date.now()}`)
    timelineEntries.value = Array.isArray(resp.data) ? resp.data : []
  } catch (e) {
    timelineEntries.value = []
  }

  // Фоновая синхронизация файлов с ЯД — убираем записи удалённых файлов
  syncCrmFilesWithYd()
}

// Кнопка «Синхронизировать с ЯД» — обратная синхронизация
async function syncCrmWithYd() {
  const cid = card.value?.contract_id
  if (!cid) return
  crmSyncing.value = true
  try {
    const { api: ax } = await import('src/boot/axios')
    // 1. Свежие данные + создание папки если нет
    const { data: c } = await contractsApi.getById(cid)
    contractData.value = c
    if (!c.yandex_folder_path) {
      const agent = c.agent_type || 'ФЕСТИВАЛЬ'
      const ptype = c.project_type || 'Индивидуальный'
      const city = c.city || 'МСК'
      const address = (c.address || 'Без адреса').replace(/[/\\<>:"|?*]/g, '-')
      const rawArea = c.area || 0
      const area = Number.isInteger(Number(rawArea)) ? Number(rawArea).toFixed(1) : rawArea
      const typeFolder = ptype.includes('ндивид') ? 'Индивидуальные' : 'Шаблонные'
      const path = `disk:/CRM/Проекты/${agent}/${typeFolder}/${city}/${city}-${address}-${area}м2`
      try { await ax.post('/api/v1/files/folder', null, { params: { folder_path: path } }) } catch {}
      await contractsApi.update(cid, { yandex_folder_path: path })
      contractData.value.yandex_folder_path = path
    }
    // 2. Скан
    const { data } = await ax.post(`/api/v1/files/scan/${cid}`)
    const added = data.new_files_added || 0
    if (added > 0) {
      const { data: freshFiles } = await filesApi.getContractFiles(cid)
      projectFiles.value = freshFiles || []
      $q.notify({ type: 'positive', message: `Синхронизация: +${added} файл(ов) с ЯД` })
    } else {
      $q.notify({ type: 'info', message: 'Файлы синхронизированы — новых нет' })
    }
    await syncCrmFilesWithYd()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка синхронизации' })
  } finally { crmSyncing.value = false }
}

async function syncCrmFilesWithYd() {
  if (!projectFiles.value.length) return
  const { api: ax } = await import('src/boot/axios')
  const toRemove = []
  for (const f of projectFiles.value) {
    const path = (f.yandex_path || '').replace(/^disk:/, '')
    if (!path) continue
    try {
      await filesApi.getPublicLink(path)
    } catch {
      try { await ax.delete(`/api/v1/files/${f.id}`) } catch {}
      toRemove.push(f.id)
    }
  }
  if (toRemove.length > 0) {
    projectFiles.value = projectFiles.value.filter(f => !toRemove.includes(f.id))
    $q.notify({ type: 'info', message: `Удалено ${toRemove.length} файл(ов) — отсутствуют на ЯД` })
  }
}

onMounted(async () => {
  try {
    const id = route.params.id
    await crmStore.loadCard(id)
    await loadAdditionalData(id)
  } catch (e) { console.error('Ошибка загрузки карточки:', e) }
})
</script>
