<template>
  <q-page padding>
    <div v-if="crmStore.cardLoading" class="q-pa-md">
      <q-skeleton type="rect" height="120px" class="q-mb-md" />
      <q-skeleton type="text" width="80%" />
    </div>

    <template v-else-if="card">
      <!-- Шапка -->
      <q-card class="is-card q-mb-md" style="position: relative">
        <!-- Кнопка назад — в углу карточки -->
        <q-btn
          round
          flat
          dense
          icon="arrow_back"
          style="position: absolute; top: -14px; left: -14px; z-index: 10; width: 27px; height: 32px; min-height: 32px; min-width: 27px; max-width: 27px; max-height: 32px; padding: 0; overflow: hidden; background: white; border: 1.5px solid #E0E0E0; box-shadow: 0 2px 8px rgba(0,0,0,0.13); color: #555"
          @click="$router.back()"
        >
          <q-tooltip>Назад</q-tooltip>
        </q-btn>
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
              <q-badge :color="statusColor(card.column_name)" :label="card.column_name" style="min-width: 100px; justify-content: center; padding: 5px 8px; font-size: 11px" />
              <q-badge v-if="card.agent_type" text-color="white" :style="{ background: agentColor, minWidth: '100px', justifyContent: 'center', padding: '5px 8px', fontSize: '11px' }" :label="card.agent_type" />
            </div>
          </div>
          <div class="row items-center text-caption q-mt-xs" style="color: #888; gap: 0">
            <span v-if="card.project_type">{{ card.project_type }}</span>
            <span v-if="card.project_subtype" style="color: #ccc; margin: 0 6px">|</span>
            <span v-if="card.project_subtype">{{ card.project_subtype }}</span>
            <span v-if="card.area" style="color: #ccc; margin: 0 6px">|</span>
            <span v-if="card.area">{{ card.area }} м²</span>
            <span v-if="card.city" style="color: #ccc; margin: 0 6px">|</span>
            <span v-if="card.city">{{ card.city }}</span>
            <span v-if="contractData?.yandex_folder_path && canSeeYdFolder" style="color: #ccc; margin: 0 6px">|</span>
            <q-btn
              v-if="contractData?.yandex_folder_path && canSeeYdFolder"
              flat
              dense
              round
              size="xs"
              icon="folder_open"
              no-caps
              style="color: #F39C12"
              @click="openYdFolder"
            >
              <q-tooltip>Яндекс.Диск</q-tooltip>
            </q-btn>
          </div>
          <div v-if="card.current_substep_name || card.revision_count > 0" class="row items-center q-gutter-xs q-mt-xs" style="flex-wrap: wrap; align-items: center">
            <q-chip
              v-if="card.current_substep_name"
              dense
              size="sm"
              :color="substepColor(card.workflow_status)"
              text-color="white"
              style="height: 22px; border-radius: 12px; font-size: 11px; margin: 0; padding: 0 8px; flex: 1; justify-content: center"
            >
              {{ workflowLabel(card.workflow_status) }}: {{ card.current_substep_name }}
            </q-chip>
            <q-badge v-if="card.revision_count > 0" color="negative" :label="`Правки: ${card.revision_count}`" style="height: 22px; border-radius: 12px; font-size: 11px; padding: 0 8px; display: inline-flex; align-items: center; margin: 0" />
          </div>
          <div v-if="card.tags" class="row q-gutter-xs q-mt-xs">
            <span
              v-for="(tag, tidx) in parseCrmTags(card.tags)"
              :key="tidx"
              :style="{ display: 'inline-block', background: tag.color, color: 'white', borderRadius: '4px', padding: '2px 10px', fontSize: '11px', fontWeight: '600' }"
            >{{ tag.text }}</span>
          </div>
        </q-card-section>
      </q-card>

      <!-- Прогресс подэтапов — grid, минимум 55px на блок, перенос на 2 строки -->
      <div v-if="substepProgress.length > 1" class="stage-progress-bar">
        <div
          v-for="(step, idx) in substepProgress"
          :key="idx"
          class="stage-step"
          :class="{ 'step-active': step.active, 'step-done': step.done && !step.active }"
        >
          {{ step.label }}
        </div>
      </div>

      <!-- Вкладки — sticky чтобы оставались видны при скролле и не перекрывались FAB -->
      <q-tabs
        v-model="activeTab"
        dense
        active-color="dark"
        indicator-color="accent"
        no-caps
        class="q-mb-md tabs-sticky"
        style="color: #666; position: sticky; top: 0; z-index: 5; background: white; margin-left: -16px; margin-right: -16px; padding: 0 16px"
        align="center"
        :breakpoint="0"
      >
        <q-tab name="executors" label="Исполнители" />
        <q-tab v-if="!isExecutor" name="timeline" label="Сроки" />
        <q-tab name="data" label="Данные" />
        <q-tab name="history" label="История" />
        <q-tab v-if="can('crm_cards.payments')" name="payments" label="Оплаты" />
        <q-tab v-if="can('chat.client.view')" name="chat">
          <span>Чат с клиентом</span>
          <q-badge
            v-if="card && chatUnreadStore.unreadByCardAndType(card.id, 'client') > 0"
            color="negative"
            floating
            style="font-size: 9px; top: 2px; right: 0"
          >
            {{ chatUnreadStore.unreadByCardAndType(card.id, 'client') }}
          </q-badge>
        </q-tab>
        <q-tab v-if="can('chat.employee.view')" name="notes">
          <span>Чат сотрудников</span>
          <q-badge
            v-if="card && chatUnreadStore.unreadByCardAndType(card.id, 'employee') > 0"
            color="negative"
            floating
            style="font-size: 9px; top: 2px; right: 0"
          >
            {{ chatUnreadStore.unreadByCardAndType(card.id, 'employee') }}
          </q-badge>
        </q-tab>
      </q-tabs>

      <q-tab-panels v-model="activeTab" animated class="bg-transparent" :style="isChatTab ? {} : { paddingBottom: '80px' }">
        <!-- ====== ВКЛАДКА 1: Исполнители и дедлайн ====== -->
        <q-tab-panel name="executors" class="q-pa-none">
          <!-- Информация -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">
                Информация
              </div>
            </q-card-section>
            <q-card-section>
              <div class="row">
                <div class="col-6" style="padding-right: 12px; border-right: 1px solid #E0E0E0">
                  <div class="q-mb-sm">
                    <div class="text-caption" style="color: #999">
                      Договор
                    </div>
                    <div style="font-size: 13px; color: #333">
                      {{ card.contract_number || '-' }}
                    </div>
                  </div>
                  <div class="q-mb-sm">
                    <div class="text-caption" style="color: #999">
                      Тип проекта
                    </div>
                    <div style="font-size: 13px; color: #333">
                      {{ card.project_type || '-' }}
                    </div>
                  </div>
                  <div v-if="card.project_subtype" class="q-mb-sm">
                    <div class="text-caption" style="color: #999">
                      Подтип проекта
                    </div>
                    <div style="font-size: 13px; color: #333">
                      {{ card.project_subtype }}
                    </div>
                  </div>
                </div>
                <div class="col-6" style="padding-left: 12px">
                  <div class="q-mb-sm">
                    <div class="text-caption" style="color: #999">
                      Срок договора
                    </div>
                    <div style="font-size: 13px; color: #333">
                      {{ contractData?.contract_period ? contractData.contract_period + ' раб.дн.' : '-' }}
                    </div>
                  </div>
                  <div class="q-mb-sm">
                    <div class="text-caption" style="color: #999">
                      Дата начала
                    </div>
                    <div style="font-size: 13px; color: #333">
                      {{ fmtDateShort(projectStartDate) || '-' }}
                    </div>
                  </div>
                  <div>
                    <div class="text-caption" style="color: #999">
                      Дедлайн проекта
                    </div>
                    <div
                      style="font-size: 13px; display: flex; align-items: center; gap: 4px"
                      :style="{ color: effectiveDeadline ? dlHex(effectiveDeadline) : '#333', cursor: (deadlineDeviations.length || aheadDeviations.length) ? 'pointer' : 'default' }"
                      @click="(deadlineDeviations.length || aheadDeviations.length) ? (showDeadlineStatsDialog = true) : undefined"
                    >
                      {{ fmtDateShort(effectiveDeadline) || '-' }}
                      <q-icon v-if="deadlineDeviations.length || aheadDeviations.length" name="info_outline" size="14px" />
                    </div>
                  </div>
                </div>
              </div>
            </q-card-section>
          </q-card>

          <!-- Команда проекта с кнопками управления -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">
                Команда проекта
              </div>
            </q-card-section>
            <q-list dense separator>
              <q-item v-for="m in allTeamMembers" :key="m.roleKey">
                <q-item-section avatar>
                  <q-avatar size="28px" :color="m.name ? 'grey-3' : 'red-1'" :text-color="m.name ? 'grey-8' : 'red-3'" style="overflow:hidden">
                    <img v-if="m.name && getAvatarByName(m.name)" :src="getAvatarByName(m.name)" style="width:100%;height:100%;object-fit:cover;border-radius:50%">
                    <template v-else>
                      {{ m.name ? m.name[0] : '?' }}
                    </template>
                  </q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label style="font-size: 12px" :style="{ color: m.name ? '#333' : '#bbb' }">
                    {{ m.name || 'Не назначен' }}
                  </q-item-label>
                  <q-item-label caption>
                    {{ m.role }}
                  </q-item-label>
                </q-item-section>
                <q-item-section v-if="!isArchived" side>
                  <div class="row q-gutter-xs">
                    <q-btn
                      v-if="m.name && m.canManage"
                      flat
                      round
                      dense
                      size="xs"
                      icon="edit"
                      color="grey-7"
                      @click="showAssignDialog(m, 'change')"
                    >
                      <q-tooltip>Изменить</q-tooltip>
                    </q-btn>
                    <q-btn
                      v-if="m.name && m.canManage"
                      flat
                      round
                      dense
                      size="xs"
                      icon="person_remove"
                      color="negative"
                      @click="removeTeamMember(m)"
                    >
                      <q-tooltip>Удалить</q-tooltip>
                    </q-btn>
                    <q-btn
                      v-if="!m.name && m.canManage"
                      flat
                      round
                      dense
                      size="xs"
                      icon="person_add"
                      color="positive"
                      @click="showAssignDialog(m, 'assign')"
                    >
                      <q-tooltip>Назначить</q-tooltip>
                    </q-btn>
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Workflow действия -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">
                Действия
              </div>
            </q-card-section>
            <q-card-section v-if="!isArchived">
              <!-- Сдать работу — только для исполнителя текущей стадии -->
              <q-btn
                v-if="isCurrentStageExecutor && (card.workflow_status === 'in_progress' || card.workflow_status === 'revision')"
                unelevated
                dense
                no-caps
                icon="check"
                label="Сдать работу"
                class="full-width q-mb-sm"
                style="background: #58D68D; color: white; font-size: 12px; font-weight: bold; height: 36px; border-radius: 4px"
                :loading="actionLoading"
                @click="doAction('submit')"
              />

              <!-- Проверяющий: Клиенту + На исправление -->
              <div v-if="can('crm_cards.complete_approval') && card.workflow_status === 'pending_review'" class="row q-gutter-sm q-mb-sm">
                <q-btn
                  unelevated
                  dense
                  no-caps
                  icon="forward_to_inbox"
                  label="Отправить клиенту"
                  style="background: #58D68D; color: white; font-size: 11px; font-weight: bold; height: 36px; border-radius: 4px; flex: 1"
                  :loading="actionLoading"
                  @click="doAction('client-send')"
                />
                <q-btn
                  unelevated
                  dense
                  no-caps
                  icon="replay"
                  label="На исправление"
                  style="background: #F1948A; color: white; font-size: 11px; font-weight: bold; height: 36px; border-radius: 4px; flex: 1"
                  @click="openRejectDialog()"
                />
              </div>

              <!-- Клиент согласовал -->
              <q-btn
                v-if="can('crm_cards.complete_approval') && card.workflow_status === 'client_approval'"
                unelevated
                dense
                no-caps
                icon="thumb_up"
                label="Клиент согласовал"
                class="full-width q-mb-sm"
                style="background: #27AE60; color: white; font-size: 12px; font-weight: bold; height: 36px; border-radius: 4px"
                :loading="actionLoading"
                @click="doAction('client-approved')"
              />

              <!-- Решение после согласования клиента (pending_decision) -->
              <div v-if="can('crm_cards.complete_approval') && card.workflow_status === 'pending_decision'" class="q-mb-sm">
                <div class="text-caption q-mb-xs" style="color: #888; text-align: center">
                  Клиент согласовал. Выберите действие:
                </div>
                <div class="row q-gutter-sm q-mb-xs">
                  <q-btn
                    unelevated
                    dense
                    no-caps
                    icon="skip_next"
                    label="Следующий подэтап"
                    style="background: #5DADE2; color: white; font-size: 11px; font-weight: bold; height: 36px; border-radius: 4px; flex: 1"
                    :loading="actionLoading"
                    @click="doAdvanceRound"
                  />
                  <q-btn
                    unelevated
                    dense
                    no-caps
                    icon="done_all"
                    label="Закрыть этап"
                    style="background: #27AE60; color: white; font-size: 11px; font-weight: bold; height: 36px; border-radius: 4px; flex: 1"
                    :loading="actionLoading"
                    @click="doCloseStage"
                  />
                </div>
              </div>

              <!-- Доп. круг -->
              <q-btn
                v-if="can('crm_cards.complete_approval') && card.workflow_status === 'pending_decision'"
                unelevated
                dense
                no-caps
                icon="add_circle_outline"
                label="Доп. круг"
                class="full-width q-mb-sm"
                style="background: #D5D8DC; color: #333; font-size: 11px; font-weight: bold; height: 32px; border-radius: 4px"
                :loading="actionLoading"
                @click="doAddExtraRound"
              />

              <!-- Акт -->
              <div v-if="can('crm_cards.complete_approval') && card.workflow_status === 'act_signing'" class="row q-gutter-sm q-mb-sm">
                <q-btn
                  unelevated
                  dense
                  no-caps
                  label="Отправить акт"
                  style="background: #58D68D; color: white; font-size: 11px; font-weight: bold; height: 36px; border-radius: 4px; flex: 1"
                  :loading="actionLoading"
                  @click="doAction('client-send')"
                />
                <q-btn
                  unelevated
                  dense
                  no-caps
                  icon="draw"
                  label="Акт подписан"
                  style="background: #85C1E9; color: white; font-size: 11px; font-weight: bold; height: 36px; border-radius: 4px; flex: 1"
                  :loading="actionLoading"
                  @click="doAction('sign-act')"
                />
              </div>

              <!-- Принятие менеджером -->
              <q-btn
                v-if="can('crm_cards.move') && card.workflow_status === 'stage_completed'"
                unelevated
                dense
                no-caps
                icon="verified"
                label="Принять (менеджер)"
                class="full-width q-mb-sm"
                style="background: #AED6F1; color: #333; font-size: 12px; font-weight: bold; height: 36px; border-radius: 4px"
                :loading="actionLoading"
                @click="doManagerAcceptance"
              />

              <div v-if="!card.workflow_status" class="text-center" style="color: #999; font-size: 12px; padding: 8px 0">
                Нет активного рабочего процесса
              </div>
            </q-card-section>

            <!-- Архивные действия -->
            <q-card-section v-else>
              <q-btn
                v-if="canRestore"
                unelevated
                dense
                no-caps
                icon="replay"
                label="Вернуть в активные"
                class="full-width q-mb-sm"
                style="background: #5DADE2; color: white; font-size: 12px; font-weight: bold; height: 36px; border-radius: 4px"
                :loading="actionLoading"
                @click="showRestoreDialog = true"
              />
              <q-btn
                v-if="canRestore && card.column_name !== 'АВТОРСКИЙ НАДЗОР' && contractData?.status !== 'АВТОРСКИЙ НАДЗОР'"
                unelevated
                dense
                no-caps
                icon="engineering"
                label="В авторский надзор"
                class="full-width q-mb-sm"
                style="background: #5DADE2; color: white; font-size: 12px; font-weight: bold; height: 36px; border-radius: 4px"
                :loading="actionLoading"
                @click="transferToSupervision"
              />
              <div class="text-center" style="color: #999; font-size: 12px; padding: 4px 0">
                Карточка в архиве
              </div>
            </q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 2: Таблица сроков (из timeline API) ====== -->
        <q-tab-panel name="timeline" class="q-pa-none">
          <q-card class="is-card">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">
                Таблица сроков
              </div>
            </q-card-section>
            <q-list v-if="timelineEntries.length > 0" dense separator>
              <q-item
                v-for="e in timelineEntries"
                :key="e.id"
                :style="timelineRowStyle(e)"
                :clickable="e.executor_role !== 'header' && can('crm_cards.deadlines') && !isArchived"
                @click="editNormDays(e)"
              >
                <q-item-section v-if="e.executor_role !== 'header'" avatar style="min-width: 24px">
                  <q-icon :name="timelineIcon(e)" :color="timelineIconColor(e)" size="18px" />
                </q-item-section>
                <q-item-section :style="e.executor_role === 'header' ? 'padding-left: 4px' : ''">
                  <q-item-label :style="{ fontSize: e.executor_role === 'header' ? '12px' : '11px', color: '#333', fontWeight: e.executor_role === 'header' || isActiveSubstep(e) ? 'bold' : 'normal' }">
                    {{ e.stage_name }}
                  </q-item-label>
                  <q-item-label v-if="e.executor_role !== 'header'" caption :style="{ color: isOverdue(e) ? '#E74C3C' : '#888' }">
                    <template v-if="e.norm_days">
                      Норма:
                      <template v-if="e.custom_norm_days && e.custom_norm_days !== e.norm_days">
                        <s style="color:#999">{{ e.norm_days }}</s>
                        <b style="color:#C62828"> {{ e.custom_norm_days }}</b> дн.
                      </template>
                      <template v-else>
                        {{ e.norm_days }} дн.
                      </template>
                    </template>
                    <span v-if="e.actual_days"> | Факт: {{ e.actual_days }} дн.</span>
                    <span v-if="e.executor_role"> | {{ e.executor_role }}</span>
                    <span v-if="isOverdue(e)" style="color: #E74C3C; font-weight: bold"> | Просрочен</span>
                    <span v-else-if="e.actual_date && !isOverdue(e)" style="color: #27AE60"> | В срок</span>
                  </q-item-label>
                </q-item-section>
                <q-item-section v-if="e.stage_code === 'START'" side style="min-width: auto; padding-right: 0">
                  <q-icon name="info_outline" size="16px" color="grey-6" class="cursor-pointer">
                    <q-tooltip style="font-size: 12px; white-space: pre-line">
                      {{ startTooltip }}
                    </q-tooltip>
                  </q-icon>
                </q-item-section>
                <q-item-section v-if="e.status === 'skipped'" side>
                  <div class="text-caption" style="color: #999; font-style: italic">
                    Пропущено
                  </div>
                </q-item-section>
                <q-item-section v-else-if="e.actual_date" side>
                  <div class="text-caption" :style="{ color: isOverdue(e) ? '#E74C3C' : '#27AE60' }">
                    {{ fmtDateShort(e.actual_date) }}
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
            <!-- Итого -->
            <div
              v-if="timelineTotals.normTotal > 0"
              class="q-pa-sm"
              :style="hasCustomNormDays ? 'background: #FFF3F3; border-top: 2px solid #E53935; border: 2px solid #E53935; border-radius: 0 0 8px 8px' : 'background: #F5F5F5; border-top: 2px solid #E0E0E0'"
            >
              <div class="row items-center justify-between">
                <span class="text-caption text-weight-bold" style="color: #555">Итого</span>
                <span class="text-caption" style="color: #555">
                  Норма: {{ timelineTotals.normTotal }} дн.
                  <span v-if="timelineTotals.actualTotal > 0"> | Факт: {{ timelineTotals.actualTotal }} дн.</span>
                </span>
              </div>
              <div v-if="timelineTotals.overdueTotal > 0 || timelineTotals.aheadTotal > 0" class="row items-center justify-end q-mt-xs" style="gap: 8px">
                <span v-if="timelineTotals.overdueTotal > 0" class="text-caption text-weight-bold" style="color: #E53935">
                  Просрочка: +{{ timelineTotals.overdueTotal }} дн.
                </span>
                <span v-if="timelineTotals.aheadTotal > 0" class="text-caption text-weight-bold" style="color: #27AE60">
                  Раньше срока: -{{ timelineTotals.aheadTotal }} дн.
                </span>
              </div>
              <div v-if="card.total_pause_days > 0" class="row items-center justify-between q-mt-xs">
                <span class="text-caption" style="color: #888">
                  <q-icon name="pause_circle_outline" size="12px" class="q-mr-xs" />Дни ожидания (учтены в дедлайне)
                </span>
                <span class="text-caption text-weight-bold" style="color: #888">+{{ card.total_pause_days }} дн.</span>
              </div>
              <div v-if="hasCustomNormDays" style="color: #E53935; font-size: 11px; margin-top: 4px">
                ⚠ Норма-дни изменены. Требуется учёт в расчёте последующих стадий.
              </div>
            </div>
            <q-card-section v-else class="text-center" style="color: #999; padding: 24px">
              <q-icon name="timeline" size="32px" color="grey-4" class="q-mb-sm" /><div>Таблица сроков не инициализирована</div>
            </q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 3: Данные по проекту (блоки) ====== -->
        <q-tab-panel name="data" class="q-pa-none">
          <div class="data-blocks-grid">
            <!-- ТЗ -->
            <q-card class="is-card q-mb-md">
              <q-card-section class="q-pb-xs">
                <div class="row items-center justify-between" style="flex-wrap: wrap; gap: 4px">
                  <div class="text-subtitle2 text-weight-bold" style="color: #333">
                    Техническое задание
                  </div>
                  <div class="row q-gutter-xs">
                    <q-btn
                      v-if="can('crm_cards.files_upload') && !isArchived"
                      outline
                      dense
                      size="xs"
                      icon="upload"
                      label="Загрузить"
                      no-caps
                      color="grey-7"
                      style="border-radius: 4px; padding: 2px 8px; min-width: 88px"
                      @click="uploadCrmFile('tech_task')"
                    />
                    <q-btn
                      v-if="contractData?.tech_task_link"
                      outline
                      dense
                      size="xs"
                      icon="open_in_new"
                      no-caps
                      color="grey-7"
                      style="border-radius: 4px; padding: 2px 6px"
                      @click="openLink(contractData.tech_task_link)"
                    >
                      <q-tooltip>Открыть в ЯД</q-tooltip>
                    </q-btn>
                  </div>
                </div>
              </q-card-section>
              <q-list v-if="filesByStage('tech_task').length > 0" dense class="q-pb-xs">
                <q-item v-for="f in filesByStage('tech_task')" :key="f.id">
                  <q-item-section avatar>
                    <q-icon :name="fileIcon(f)" :color="fileColor(f)" />
                  </q-item-section>
                  <q-item-section style="min-width: 0">
                    <q-item-label style="font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
                      <a href="#" style="color: #1677FF; text-decoration: none" @click.prevent="openFile(f)">{{ f.file_name }}</a>
                    </q-item-label>
                  </q-item-section>
                  <q-item-section v-if="!isArchived" side style="flex-shrink: 0">
                    <div class="row q-gutter-xs no-wrap">
                      <q-btn
                        outline
                        dense
                        size="xs"
                        icon="open_in_new"
                        label="Открыть"
                        no-caps
                        color="grey-7"
                        style="border-radius: 4px; padding: 2px 8px; min-width: 88px"
                        @click.stop="openFile(f)"
                      /><q-btn
                        v-if="can('crm_cards.files_delete')"
                        outline
                        dense
                        size="xs"
                        icon="delete_outline"
                        no-caps
                        color="negative"
                        style="padding: 2px 6px; border-radius: 4px"
                        @click.stop="deleteFile(f)"
                      />
                    </div>
                  </q-item-section>
                </q-item>
              </q-list>
              <q-card-section v-else class="q-py-sm text-center" style="color: #bbb; font-size: 11px">
                Нет файлов
              </q-card-section>
            </q-card>

            <!-- Замер (как десктоп: ссылка на папку + дата + загрузка множества файлов) -->
            <q-card class="is-card q-mb-md">
              <q-card-section class="q-pb-xs">
                <div class="row items-center justify-between" style="flex-wrap: wrap; gap: 4px">
                  <div class="text-subtitle2 text-weight-bold" style="color: #333">
                    Замер
                  </div>
                  <div class="row q-gutter-xs">
                    <q-btn
                      v-if="can('crm_cards.files_upload') && !isArchived"
                      outline
                      dense
                      size="xs"
                      icon="upload"
                      label="Загрузить"
                      no-caps
                      color="grey-7"
                      style="border-radius: 4px; padding: 2px 8px; min-width: 88px"
                      @click="showMeasurementDlg = true"
                    />
                    <q-btn
                      v-if="contractData?.measurement_image_link && can('crm_cards.files_delete') && !isArchived"
                      outline
                      dense
                      size="xs"
                      icon="delete_outline"
                      no-caps
                      color="negative"
                      style="border-radius: 4px; padding: 2px 6px"
                      @click="deleteFolderSection('measurement')"
                    >
                      <q-tooltip>Удалить замер</q-tooltip>
                    </q-btn>
                  </div>
                </div>
              </q-card-section>
              <q-card-section class="q-pt-xs">
                <div v-if="contractData?.measurement_image_link" class="q-mb-xs">
                  <a :href="contractData.measurement_image_link" target="_blank" style="color: #1677FF; font-size: 12px">Открыть папку с замером</a>
                </div>
                <div v-else style="color: #999; font-size: 12px" class="q-mb-xs">
                  Не загружен
                </div>
                <div class="text-caption" style="color: #888">
                  Дата: {{ contractData?.measurement_date ? fmtDate(contractData.measurement_date) : 'Не установлена' }}
                </div>
              </q-card-section>
            </q-card>

            <!-- Фотофиксация (как десктоп: ссылка на папку) -->
            <q-card class="is-card q-mb-md">
              <q-card-section class="q-pb-xs">
                <div class="row items-center justify-between" style="flex-wrap: wrap; gap: 4px">
                  <div class="text-subtitle2 text-weight-bold" style="color: #333">
                    Фотофиксация
                  </div>
                  <div class="row q-gutter-xs">
                    <q-btn
                      v-if="can('crm_cards.files_upload') && !isArchived"
                      outline
                      dense
                      size="xs"
                      icon="upload"
                      label="Загрузить"
                      no-caps
                      color="grey-7"
                      style="border-radius: 4px; padding: 2px 8px; min-width: 88px"
                      @click="uploadCrmFile('photo_documentation')"
                    />
                    <q-btn
                      v-if="(contractData?.photo_folder_public_link || contractData?.photo_documentation_yandex_path) && can('crm_cards.files_delete') && !isArchived"
                      outline
                      dense
                      size="xs"
                      icon="delete_outline"
                      no-caps
                      color="negative"
                      style="border-radius: 4px; padding: 2px 6px"
                      @click="deleteFolderSection('photo_documentation')"
                    >
                      <q-tooltip>Удалить папку</q-tooltip>
                    </q-btn>
                  </div>
                </div>
              </q-card-section>
              <q-card-section class="q-pt-xs">
                <div v-if="contractData?.photo_folder_public_link || contractData?.photo_documentation_yandex_path" class="q-mb-xs">
                  <a :href="contractData.photo_folder_public_link || contractData.photo_documentation_yandex_path" target="_blank" style="color: #1677FF; font-size: 12px">Открыть папку с фотофиксацией</a>
                </div>
                <div v-else style="color: #999; font-size: 12px">
                  Не загружена
                </div>
              </q-card-section>
            </q-card>

            <!-- Референсы / Шаблоны (как десктоп: ссылка на папку) -->
            <q-card class="is-card q-mb-md">
              <q-card-section class="q-pb-xs">
                <div class="row items-center justify-between" style="flex-wrap: wrap; gap: 4px">
                  <div class="text-subtitle2 text-weight-bold" style="color: #333">
                    {{ card.project_type === 'Шаблонный' ? 'Шаблоны проекта' : 'Референсы' }}
                  </div>
                  <div class="row q-gutter-xs">
                    <q-btn
                      v-if="can('crm_cards.files_upload') && !isArchived"
                      outline
                      dense
                      size="xs"
                      icon="upload"
                      label="Загрузить"
                      no-caps
                      color="grey-7"
                      style="border-radius: 4px; padding: 2px 8px; min-width: 88px"
                      @click="uploadCrmFile('references')"
                    />
                    <q-btn
                      v-if="contractData?.references_yandex_path && can('crm_cards.files_delete') && !isArchived"
                      outline
                      dense
                      size="xs"
                      icon="delete_outline"
                      no-caps
                      color="negative"
                      style="border-radius: 4px; padding: 2px 6px"
                      @click="deleteFolderSection('references')"
                    >
                      <q-tooltip>Удалить папку</q-tooltip>
                    </q-btn>
                  </div>
                </div>
              </q-card-section>
              <q-card-section class="q-pt-xs">
                <div v-if="contractData?.references_yandex_path" class="q-mb-xs">
                  <a :href="contractData.references_yandex_path" target="_blank" style="color: #1677FF; font-size: 12px">{{ card.project_type === 'Шаблонный' ? 'Открыть папку с шаблонами' : 'Открыть папку с референсами' }}</a>
                </div>
                <div v-else style="color: #999; font-size: 12px">
                  Не загружена
                </div>
              </q-card-section>
            </q-card>
          </div><!-- /data-blocks-grid -->

          <!-- Стадии проекта с вкладками вариаций (как в десктопе) -->
          <q-card v-for="stage in projectStages" :key="stage.code" class="is-card q-mb-md" :style="isCurrentStage(stage.code) ? 'border: 2px solid #27AE60' : ''">
            <q-card-section class="q-pb-xs">
              <div class="row items-center justify-between" style="flex-wrap: wrap; gap: 4px">
                <div class="text-subtitle2 text-weight-bold" style="color: #333">
                  {{ stage.label }}
                </div>
                <!-- Кнопки только для стадий без подстадий -->
                <div v-if="!stage.substages" class="row q-gutter-xs">
                  <q-btn
                    v-if="revisionPathForStage(stage.code)"
                    outline
                    dense
                    size="xs"
                    label="Правки"
                    no-caps
                    color="negative"
                    style="border-radius: 4px; padding: 2px 8px; font-weight: bold"
                    @click="openRevisionFolder(stage.code)"
                  >
                    <q-tooltip>Открыть папку с правками</q-tooltip>
                  </q-btn>
                  <q-btn
                    v-if="canUploadForProjectStage(stage.code) && !isArchived"
                    outline
                    dense
                    size="xs"
                    icon="upload"
                    label="Загрузить"
                    no-caps
                    color="grey-7"
                    style="border-radius: 4px; padding: 2px 8px; min-width: 88px"
                    @click="uploadToVariation(stage.code)"
                  />
                  <q-btn
                    v-if="canUploadForProjectStage(stage.code) && !isArchived"
                    outline
                    dense
                    size="xs"
                    icon="create_new_folder"
                    no-caps
                    color="grey-7"
                    style="border-radius: 4px; padding: 2px 6px"
                    @click="addVariationTab(stage.code)"
                  >
                    <q-tooltip>Добавить вариацию</q-tooltip>
                  </q-btn>
                  <q-btn
                    v-if="getVariations(stage.code).length > 1 && !isArchived"
                    outline
                    dense
                    size="xs"
                    icon="delete_outline"
                    no-caps
                    color="negative"
                    style="border-radius: 4px; padding: 2px 6px"
                    @click="deleteVariationTab(stage.code)"
                  >
                    <q-tooltip>Удалить текущую вариацию</q-tooltip>
                  </q-btn>
                </div>
              </div>
            </q-card-section>

            <!-- Подстадии (напр. Стадия 2: Мудборды + Визуализация) -->
            <template v-if="stage.substages">
              <div
                v-for="sub in stage.substages"
                :key="sub.code"
                style="border-top: 1px solid #F0F0F0; padding: 8px 16px 4px"
              >
                <div class="row items-center justify-between q-mb-xs" style="flex-wrap: wrap; gap: 4px">
                  <div class="text-caption text-weight-bold" style="color: #555">
                    {{ sub.label }}
                  </div>
                  <div class="row q-gutter-xs">
                    <q-btn
                      v-if="revisionPathForStage(sub.code)"
                      outline
                      dense
                      size="xs"
                      label="Правки"
                      no-caps
                      color="negative"
                      style="border-radius: 4px; padding: 2px 8px; font-weight: bold"
                      @click="openRevisionFolder(sub.code)"
                    >
                      <q-tooltip>Открыть папку с правками</q-tooltip>
                    </q-btn>
                    <q-btn
                      v-if="canUploadForProjectStage(sub.code) && !isArchived"
                      outline
                      dense
                      size="xs"
                      icon="upload"
                      label="Загрузить"
                      no-caps
                      color="grey-7"
                      style="border-radius: 4px; padding: 2px 8px; min-width: 88px"
                      @click="uploadToVariation(sub.code)"
                    />
                    <q-btn
                      v-if="canUploadForProjectStage(sub.code) && !isArchived"
                      outline
                      dense
                      size="xs"
                      icon="create_new_folder"
                      no-caps
                      color="grey-7"
                      style="border-radius: 4px; padding: 2px 6px"
                      @click="addVariationTab(sub.code)"
                    >
                      <q-tooltip>Добавить вариацию</q-tooltip>
                    </q-btn>
                    <q-btn
                      v-if="getVariations(sub.code).length > 1 && !isArchived"
                      outline
                      dense
                      size="xs"
                      icon="delete_outline"
                      no-caps
                      color="negative"
                      style="border-radius: 4px; padding: 2px 6px"
                      @click="deleteVariationTab(sub.code)"
                    >
                      <q-tooltip>Удалить текущую вариацию</q-tooltip>
                    </q-btn>
                  </div>
                </div>

                <!-- Вкладки вариаций подстадии -->
                <q-tabs
                  v-if="getVariations(sub.code).length >= 1"
                  v-model="activeVariation[sub.code]"
                  dense
                  active-color="dark"
                  indicator-color="accent"
                  no-caps
                  style="font-size: 11px"
                  align="left"
                >
                  <q-tab v-for="v in getVariations(sub.code)" :key="v" :name="v" :label="`Вариация ${v}`" />
                </q-tabs>

                <!-- Файлы подстадии -->
                <q-list v-if="filesForVariation(sub.code).length > 0" dense>
                  <q-item v-for="f in filesForVariation(sub.code)" :key="f.id">
                    <q-item-section avatar>
                      <q-img
                        v-if="isImageFile(f)"
                        :src="imgStreamUrl(f)"
                        style="width: 48px; height: 48px; border-radius: 4px; cursor: pointer"
                        @click="openStageFile(f, sub.code)"
                      />
                      <q-icon v-else :name="fileIcon(f)" :color="fileColor(f)" />
                    </q-item-section>
                    <q-item-section v-if="!isImageFile(f)" style="min-width: 0">
                      <q-item-label style="font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
                        <a href="#" style="color: #1677FF; text-decoration: none" @click.prevent="openStageFile(f, sub.code)">{{ f.file_name }}</a>
                      </q-item-label>
                    </q-item-section>
                    <q-item-section v-if="!isArchived" side style="flex-shrink: 0">
                      <div class="row q-gutter-xs no-wrap">
                        <q-btn
                          outline
                          dense
                          size="xs"
                          icon="open_in_new"
                          label="Открыть"
                          no-caps
                          color="grey-7"
                          style="border-radius: 4px; padding: 2px 8px; min-width: 88px"
                          @click.stop="openStageFile(f, sub.code)"
                        />
                        <q-btn
                          v-if="canUploadForProjectStage(sub.code) && can('crm_cards.files_delete')"
                          outline
                          dense
                          size="xs"
                          icon="delete_outline"
                          no-caps
                          color="negative"
                          style="padding: 2px 6px; border-radius: 4px"
                          @click.stop="deleteFile(f)"
                        />
                      </div>
                    </q-item-section>
                  </q-item>
                </q-list>
                <div v-else class="q-py-sm text-center" style="color: #bbb; font-size: 11px">
                  Нет файлов
                </div>
              </div>
              <div class="q-pb-sm" />
            </template>

            <!-- Одиночная стадия без подстадий -->
            <template v-else>
              <!-- Вкладки вариаций -->
              <q-tabs
                v-if="getVariations(stage.code).length > 1"
                v-model="activeVariation[stage.code]"
                dense
                active-color="dark"
                indicator-color="accent"
                no-caps
                style="font-size: 11px"
                align="left"
              >
                <q-tab v-for="v in getVariations(stage.code)" :key="v" :name="v" :label="`Вариация ${v}`" />
              </q-tabs>

              <!-- Файлы текущей вариации -->
              <q-list v-if="filesForVariation(stage.code).length > 0" dense>
                <q-item v-for="f in filesForVariation(stage.code)" :key="f.id">
                  <q-item-section avatar>
                    <q-img
                      v-if="isImageFile(f)"
                      :src="imgStreamUrl(f)"
                      style="width: 48px; height: 48px; border-radius: 4px; cursor: pointer"
                      @click="openStageFile(f, stage.code)"
                    />
                    <q-icon v-else :name="fileIcon(f)" :color="fileColor(f)" />
                  </q-item-section>
                  <q-item-section v-if="!isImageFile(f)" style="min-width: 0">
                    <q-item-label style="font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
                      <a href="#" style="color: #1677FF; text-decoration: none" @click.prevent="openStageFile(f, stage.code)">{{ f.file_name }}</a>
                    </q-item-label>
                  </q-item-section>
                  <q-item-section v-if="!isArchived" side style="flex-shrink: 0">
                    <div class="row q-gutter-xs no-wrap">
                      <q-btn
                        outline
                        dense
                        size="xs"
                        icon="open_in_new"
                        label="Открыть"
                        no-caps
                        color="grey-7"
                        style="border-radius: 4px; padding: 2px 8px; min-width: 88px"
                        @click.stop="openStageFile(f, stage.code)"
                      />
                      <q-btn
                        v-if="canUploadForProjectStage(stage.code) && can('crm_cards.files_delete')"
                        outline
                        dense
                        size="xs"
                        icon="delete_outline"
                        no-caps
                        color="negative"
                        style="padding: 2px 6px; border-radius: 4px"
                        @click.stop="deleteFile(f)"
                      />
                    </div>
                  </q-item-section>
                </q-item>
              </q-list>
              <q-card-section v-else class="q-py-sm text-center" style="color: #bbb; font-size: 11px">
                Нет файлов
              </q-card-section>
              <div class="q-pb-sm" />
            </template>
          </q-card>

          <div class="q-mb-xl" />
          <input
            ref="crmFileInput"
            type="file"
            style="position: absolute; left: -9999px; opacity: 0"
            multiple
            accept=".pdf,.jpg,.jpeg,.png,.webp,.heic,.bmp,.doc,.docx,.xls,.xlsx,.dwg,.mp4,.mov,.avi,.mkv"
            @change="handleCrmFileUpload"
          >
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 4: История ====== -->
        <q-tab-panel name="history" class="q-pa-none">
          <div class="row items-center q-mb-md q-gutter-sm">
            <q-select
              v-model="historyFilter"
              :options="historyFilterOptions"
              outlined
              dense
              style="font-size: 12px; flex: 1"
              emit-value
              map-options
            />
          </div>
          <q-card v-if="completedStages.length > 0" class="is-card q-mb-md" style="border-left: 3px solid #27AE60">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #27AE60">
                Выполненные стадии
              </div>
            </q-card-section>
            <q-list dense>
              <q-item v-for="se in completedStages" :key="'c-'+se.id">
                <q-item-section avatar>
                  <q-icon name="check_circle" color="positive" size="18px" />
                </q-item-section><q-item-section>
                  <q-item-label style="font-size: 12px">
                    {{ se.stage_name }}
                  </q-item-label><q-item-label caption>
                    {{ se.executor_name }} | {{ fmtDateShort(se.completed_date) }}
                  </q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>
          <q-card class="is-card">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">
                Лог действий
              </div>
            </q-card-section>
            <q-list v-if="filteredHistory.length > 0" dense separator>
              <q-item v-for="h in filteredHistory" :key="h.id">
                <q-item-section avatar>
                  <q-icon :name="actionIcon(h.action_type)" :color="actionColor(h.action_type)" size="18px" />
                </q-item-section><q-item-section>
                  <q-item-label style="font-size: 11px; color: #333">
                    {{ (h.description || h.action_type || '').replace(/\[voice:[^\]]*\]\s*/, '') }}
                  </q-item-label><q-item-label caption style="color: #888">
                    {{ h.user_name }}
                  </q-item-label>
                </q-item-section><q-item-section side>
                  <div class="text-caption" style="color: #888">
                    {{ fmtDateTime(h.action_date) }}
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="text-center" style="color: #999; padding: 24px">
              <q-icon name="history" size="32px" color="grey-4" class="q-mb-sm" /><div>Нет записей</div>
            </q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 5: Оплаты исполнителям ====== -->
        <q-tab-panel name="payments" class="q-pa-none">
          <q-card v-for="group in paymentGroups" :key="group.role" class="is-card q-mb-md">
            <q-card-section class="q-pb-xs">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">
                {{ group.role }}
              </div>
            </q-card-section>
            <q-list dense separator>
              <q-item v-for="p in group.items" :key="p.id" :style="paymentRowStyle(p)">
                <q-item-section>
                  <q-item-label style="font-size: 12px; color: #333" class="text-weight-medium">
                    {{ p.employee_name || 'Не указан' }}
                  </q-item-label>
                  <q-item-label caption style="color: #888">
                    {{ p.stage_name || '' }}
                  </q-item-label>
                  <q-item-label v-if="p.is_paid || p.payment_status === 'paid'" caption style="color: #27AE60; font-size: 10px">
                    оплачено
                  </q-item-label>
                  <q-item-label v-else-if="p.payment_status === 'to_pay'" caption style="color: #F39C12; font-size: 10px">
                    к оплате
                  </q-item-label>
                  <q-item-label v-else caption style="color: #bbb; font-size: 10px">
                    в работе
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <div class="text-right">
                    <div class="row items-center justify-end no-wrap">
                      <span class="text-caption" style="color: #888">{{ p.payment_subtype || '' }}</span>
                      <div style="width: 1px; height: 14px; background: #ddd; margin: 0 6px" />
                      <div class="text-caption" :style="{ color: p.report_month ? '#333' : '#bbb' }">
                        {{ formatReportMonth(p.report_month) }}
                      </div>
                      <div style="width: 1px; height: 14px; background: #ddd; margin: 0 6px" />
                      <div class="text-weight-bold" style="font-size: 13px" :style="{ color: p.is_paid ? '#27AE60' : '#333' }">
                        {{ fmtMoney(p.final_amount || p.amount) }}
                      </div>
                    </div>
                    <div v-if="!isArchived" class="row items-center justify-end q-gutter-xs q-mt-xs">
                      <q-btn
                        flat
                        round
                        dense
                        size="xs"
                        icon="edit"
                        color="grey-7"
                        @click.stop="editPaymentAmount(p)"
                      />
                      <q-btn
                        flat
                        round
                        dense
                        size="xs"
                        icon="delete_outline"
                        color="negative"
                        @click.stop="deletePayment(p)"
                      />
                    </div>
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Итого -->
          <q-card v-if="paymentGroups.length > 0" class="is-card" style="border-left: 3px solid #ffd93c">
            <q-card-section class="q-pa-md">
              <div class="row items-center justify-between" style="flex-wrap: wrap; gap: 4px">
                <div class="text-subtitle2 text-weight-bold" style="color: #333">
                  Итого по карточке
                </div>
                <div class="text-h6 text-weight-bold" style="color: #333">
                  {{ fmtMoney(paymentTotal) }}
                </div>
              </div>
            </q-card-section>
          </q-card>

          <!-- Кнопка создания нового платежа (П1) -->
          <q-card v-if="!isArchived && can('crm_cards.payments')" class="is-card q-mb-md">
            <q-card-section class="q-pa-sm text-center">
              <q-btn
                unelevated
                no-caps
                icon="add"
                label="Создать платёж"
                color="primary"
                size="sm"
                class="full-width"
                @click="showCreatePayment = true"
              />
            </q-card-section>
          </q-card>

          <q-card-section v-if="paymentGroups.length === 0" class="text-center" style="color: #999; padding: 24px">
            <q-icon name="payments" size="32px" color="grey-4" class="q-mb-sm" /><div>Нет платежей</div>
          </q-card-section>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА: Чат сотрудников ====== -->
        <q-tab-panel name="notes" class="q-pa-sm">
          <div style="border: 1px solid #E0E0E0; border-radius: 8px; overflow: hidden">
            <InlineChatRoom
              v-if="notesTabVisited && card?.id"
              chat-type="employee"
              :card-id="card.id"
            />
          </div>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА: Чат с клиентом ====== -->
        <q-tab-panel name="chat" class="q-pa-sm">
          <div class="row q-mb-xs">
            <q-btn
              flat
              dense
              no-caps
              icon="smart_toy"
              label="Отправить скрипт"
              color="green-7"
              style="font-size: 12px"
              @click="loadScriptsAndShow"
            />
          </div>
          <div style="border: 1px solid #E0E0E0; border-radius: 8px; overflow: hidden">
            <InlineChatRoom
              v-if="chatTabVisited && card?.id"
              chat-type="client"
              :card-id="card.id"
            />
          </div>
        </q-tab-panel>
      </q-tab-panels>

      <!-- Галерея изображений файлов стадий -->
      <q-dialog v-model="crmGalleryVisible" maximized transition-show="fade" transition-hide="fade">
        <div class="column" style="background: rgba(0,0,0,0.95); height: 100dvh; min-height: 100dvh">
          <div class="row items-center q-pa-sm no-wrap">
            <q-btn
              flat
              round
              dense
              icon="close"
              color="white"
              @click="crmGalleryVisible = false"
            />
            <div class="col text-center text-white q-px-sm" style="font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
              {{ crmCurrentGalleryFile?.file_name }}
            </div>
            <div class="text-white text-caption" style="min-width: 44px; text-align: right">
              {{ crmGalleryIdx + 1 }}/{{ crmGalleryFiles.length }}
            </div>
          </div>
          <div v-touch-swipe.mouse="handleCrmGallerySwipe" class="col flex flex-center" style="position: relative; overflow: hidden">
            <q-btn
              v-if="crmGalleryIdx > 0"
              flat
              round
              icon="chevron_left"
              color="white"
              style="position: absolute; left: 4px; z-index: 2; opacity: 0.8; background: rgba(0,0,0,0.3)"
              @click="crmPrevImage"
            />
            <img
              v-if="crmCurrentGalleryFile"
              :src="imgStreamUrl(crmCurrentGalleryFile)"
              style="max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 4px; padding: 8px"
            >
            <q-btn
              v-if="crmGalleryIdx < crmGalleryFiles.length - 1"
              flat
              round
              icon="chevron_right"
              color="white"
              style="position: absolute; right: 4px; z-index: 2; opacity: 0.8; background: rgba(0,0,0,0.3)"
              @click="crmNextImage"
            />
          </div>
          <div class="row justify-center q-pa-sm">
            <q-btn
              flat
              no-caps
              icon="open_in_new"
              label="Открыть в браузере"
              color="white"
              size="sm"
              @click="openLink(crmCurrentGalleryFile?.public_link)"
            />
          </div>
        </div>
      </q-dialog>

      <!-- Диалог создания Telegram-чата -->
      <q-dialog v-model="showCreateChatDlg" persistent>
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
              @click="showCreateChatDlg = false"
            />
          </q-toolbar>
          <q-card-section>
            <q-banner
              dense
              rounded
              class="q-mb-sm text-body2"
              style="background: #FFF3E0; color: #E65100; font-size: 12px"
            >
              <template #avatar>
                <q-icon name="warning" color="orange-8" />
              </template>
              Внутренний чат с клиентом уже создан. При создании Telegram-чата у клиента будет два канала связи — информацию нужно будет синхронизировать вручную.
            </q-banner>
            <q-input
              v-model="newChatTitle"
              label="Название чата"
              outlined
              dense
              class="q-mb-xs"
              hint="ИН-Город-Адрес или ШП-Город-Адрес"
            />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn v-close-popup flat label="Отмена" no-caps />
            <q-btn
              unelevated
              label="Создать"
              style="background: #ffd93c; color: #333; border-radius: 4px"
              no-caps
              :loading="chatCreating"
              :disable="!newChatTitle.trim()"
              @click="createProjectChat"
            />
          </q-card-actions>
        </q-card>
      </q-dialog>

      <!-- Диалог отправки сообщения в чат -->
      <q-dialog v-model="showSendMessageDlg">
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
              v-model="chatMessageText"
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
              :loading="chatActionLoading"
              :disable="!chatMessageText?.trim()"
              @click="doSendMessage"
            />
          </q-card-actions>
        </q-card>
      </q-dialog>

      <!-- Диалог выбора скрипта -->
      <!-- Диалог добавления участника в чат -->
      <q-dialog v-model="showAddMemberDlg">
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
              v-model="addMemberEmployeeId"
              :options="cardTeamOptions"
              option-value="id"
              option-label="label"
              label="Участник проекта"
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
              :loading="addMemberLoading"
              :disable="!addMemberEmployeeId"
              @click="doAddChatMember"
            />
          </q-card-actions>
        </q-card>
      </q-dialog>

      <q-dialog v-model="showScriptsDlg">
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
          <q-list v-if="chatScripts.length > 0" dense separator>
            <q-item
              v-for="script in chatScripts"
              :key="script.id"
              v-ripple
              clickable
              @click="doTriggerScript(script)"
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

      <!-- Диалог ревизии -->
      <q-dialog v-model="showRejectDialog">
        <q-card style="min-width: 320px; border-radius: 10px">
          <q-toolbar style="background: #E74C3C; color: white">
            <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
              На исправление
            </q-toolbar-title><q-btn
              flat
              round
              dense
              icon="close"
              color="white"
              @click="showRejectDialog = false"
            />
          </q-toolbar>
          <q-card-section>
            <q-input
              v-model="rejectReason"
              label="Причина *"
              outlined
              dense
              type="textarea"
              autogrow
              class="q-mb-sm"
            />
            <!-- Показываем выбранный подэтап (предзаполнен из кнопки) -->
            <div v-if="rejectSubstage" class="q-mb-sm row items-center q-gutter-xs">
              <q-icon name="subdirectory_arrow_right" color="grey-6" size="16px" />
              <span style="font-size: 12px; color: #666">Папка правок:</span>
              <q-chip dense color="orange-2" text-color="orange-9" style="font-size: 11px">
                {{ rejectSubstage === 'concept' ? 'Концепция-коллажи / Правки' : '3D визуализация / Правки' }}
              </q-chip>
            </div>
            <div class="q-mb-sm">
              <q-btn
                outline
                no-caps
                icon="attach_file"
                label="Прикрепить файл с правками"
                style="width: 100%; justify-content: flex-start"
                @click="$refs.rejectFileInput.click()"
              />
              <input
                ref="rejectFileInput"
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.heic,.doc,.docx,.mp4,.mov,.avi,.mkv"
                style="display: none"
                @change="e => { rejectFile = e.target.files[0] || null }"
              >
              <div v-if="rejectFile" class="q-mt-sm row items-center no-wrap" style="background: #f5f5f5; border-radius: 8px; padding: 8px 10px; gap: 8px">
                <img
                  v-if="rejectFilePreviewUrl"
                  :src="rejectFilePreviewUrl"
                  style="width: 56px; height: 56px; object-fit: cover; border-radius: 6px; flex-shrink: 0"
                >
                <q-icon
                  v-else
                  :name="rejectFile.type === 'application/pdf' ? 'picture_as_pdf' : 'description'"
                  :color="rejectFile.type === 'application/pdf' ? 'red-7' : 'blue-7'"
                  size="36px"
                  style="flex-shrink: 0"
                />
                <div class="col-grow" style="min-width: 0">
                  <div style="font-size: 12px; font-weight: 500; color: #333; word-break: break-all; line-height: 1.3">
                    {{ rejectFile.name }}
                  </div>
                  <div style="font-size: 11px; color: #999">
                    {{ (rejectFile.size / 1024).toFixed(0) }} КБ
                  </div>
                </div>
                <q-btn
                  flat
                  dense
                  round
                  icon="close"
                  size="sm"
                  color="grey-7"
                  style="flex-shrink: 0"
                  @click="rejectFile = null"
                />
              </div>
            </div>
          </q-card-section>
          <q-card-actions align="right">
            <q-btn v-close-popup flat label="Отмена" no-caps /><q-btn
              unelevated
              label="Отправить"
              style="background: #E74C3C; color: white; border-radius: 4px"
              no-caps
              :loading="actionLoading"
              @click="submitReject"
            />
          </q-card-actions>
        </q-card>
      </q-dialog>

      <!-- Диалог редактирования записи таймлайна -->
      <q-dialog v-model="timelineEditVisible">
        <q-card style="min-width: 300px; border-radius: 10px">
          <q-toolbar style="background: #ffd93c; color: #333">
            <q-toolbar-title class="text-weight-bold" style="font-size: 13px">
              {{ timelineEditEntry?.stage_name }}
            </q-toolbar-title>
            <q-btn
              flat
              round
              dense
              icon="close"
              @click="timelineEditVisible = false"
            />
          </q-toolbar>
          <q-card-section class="q-pb-sm">
            <q-input
              v-model="timelineEditNormDays"
              label="Норма-дни (польз.)"
              outlined
              dense
              type="number"
              class="q-mb-sm"
              :hint="`Стандарт: ${timelineEditEntry?.norm_days || 0} дн.`"
            />
            <q-input
              v-model="timelineEditActualDate"
              label="Дата выполнения"
              outlined
              dense
              type="date"
              clearable
              class="q-mb-xs"
            />
            <div style="font-size: 11px; color: #888">
              Заполните дату выполнения подэтапа
            </div>
          </q-card-section>
          <q-card-actions align="right">
            <q-btn flat label="Отмена" no-caps @click="timelineEditVisible = false" />
            <q-btn
              unelevated
              label="Сохранить"
              no-caps
              style="background: #4CAF50; color: white; border-radius: 4px"
              @click="saveTimelineEntry"
            />
          </q-card-actions>
        </q-card>
      </q-dialog>

      <!-- Диалог назначения исполнителя -->
      <q-dialog v-model="assignDialogVisible">
        <q-card style="min-width: 320px; border-radius: 10px">
          <q-toolbar style="background: #ffd93c; color: #333">
            <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
              {{ assignDialogTitle }}
            </q-toolbar-title><q-btn
              flat
              round
              dense
              icon="close"
              @click="assignDialogVisible = false"
            />
          </q-toolbar>
          <q-card-section>
            <div class="text-caption q-mb-sm" style="color: #888">
              Роль: {{ assignRole }}
            </div>
            <q-select
              v-model="assignEmployeeId"
              :options="employeeOptions"
              option-value="id"
              option-label="label"
              label="Сотрудник"
              outlined
              dense
              emit-value
              map-options
              use-input
              input-debounce="200"
              class="q-mb-sm"
              @filter="filterAssignEmployees"
            />
          </q-card-section>
          <q-card-section v-if="otherStageExecutors.length > 0" class="q-pt-none">
            <div class="text-caption text-grey-7 q-mb-xs">
              Исполнители на других стадиях:
            </div>
            <q-list dense>
              <q-item
                v-for="(ex, idx) in otherStageExecutors"
                :key="idx"
                dense
                class="q-pa-none"
                style="min-height: 28px"
              >
                <q-item-section>
                  <q-item-label style="font-size: 11px; color: #666">
                    {{ ex.stage_name }}: <span style="color: #333; font-weight: 500">{{ ex.executor_name || 'Не назначен' }}</span>
                  </q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
          <q-card-section v-if="assignHistory.length > 0" class="q-pt-none">
            <div class="text-caption text-grey-7 q-mb-xs">
              История назначений:
            </div>
            <q-list dense>
              <q-item
                v-for="(h, idx) in assignHistory"
                :key="idx"
                dense
                class="q-pa-none"
                style="min-height: 28px"
              >
                <q-item-section>
                  <q-item-label style="font-size: 11px; color: #666">
                    {{ h.executor_name || '?' }} — {{ formatHistoryDate(h.assigned_date) }}
                    <span v-if="h.assigned_by_name" style="color: #999"> ({{ h.assigned_by_name }})</span>
                  </q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
          <q-card-actions align="right">
            <q-btn v-close-popup flat label="Отмена" no-caps /><q-btn
              unelevated
              label="Назначить"
              style="background: #ffd93c; color: #333; border-radius: 4px"
              no-caps
              :loading="actionLoading"
              @click="doAssign"
            />
          </q-card-actions>
        </q-card>
      </q-dialog>

      <!-- Диалог замера -->
      <MeasurementDialog
        v-model="showMeasurementDlg"
        :card-id="card?.id"
        :contract-id="card?.contract_id"
        :contract-data="contractData"
        :card-surveyor-id="card?.surveyor_id ?? null"
        @saved="onMeasurementSaved"
      />

      <ContractFormDialog
        v-model="showContractEdit"
        :contract="contractData"
        @saved="() => reloadCard()"
      />

      <!-- FAB кнопки (скрыты в архиве и на вкладках чата) -->
      <q-page-sticky v-if="!isArchived && !isChatTab" position="bottom-right" :offset="[18, 72]">
        <q-fab icon="more_vert" direction="up" style="background: #ffd93c; color: #333" vertical-actions-align="right">
          <q-fab-action
            v-if="canRestore"
            icon="build"
            style="background: #F39C12; color: white"
            :loading="actionLoading"
            label="Ремонт"
            external-label
            label-position="left"
            @click="repairWorkflow"
          />
          <q-fab-action
            v-if="can('crm_cards.reset_approval') && isArchived"
            icon="restart_alt"
            style="background: #E67E22; color: white"
            :loading="actionLoading"
            label="Сброс согласования"
            external-label
            label-position="left"
            @click="doResetApproval"
          />
          <q-fab-action
            v-if="can('crm_cards.reset_designer')"
            icon="person_off"
            style="background: #E67E22; color: white"
            :loading="actionLoading"
            label="Сброс дизайнера"
            external-label
            label-position="left"
            @click="doResetDesigner"
          />
          <q-fab-action
            v-if="can('crm_cards.reset_draftsman')"
            icon="person_off"
            style="background: #E67E22; color: white"
            :loading="actionLoading"
            label="Сброс чертёжника"
            external-label
            label-position="left"
            @click="doResetDraftsman"
          />
          <q-fab-action
            icon="sync"
            style="background: #5DADE2; color: white"
            :loading="crmSyncing"
            label="Синхронизация ЯД"
            external-label
            label-position="left"
            @click="syncCrmWithYd"
          />
          <q-fab-action
            v-if="can('contracts.update')"
            icon="edit"
            style="background: #ffd93c; color: #333"
            label="Редактировать договор"
            external-label
            label-position="left"
            @click="openContractEdit"
          />
          <q-fab-action
            icon="label"
            style="background: #ffd93c; color: #333"
            label="Теги"
            external-label
            label-position="left"
            @click="openTagDialog"
          />
          <q-fab-action
            v-if="can('access.contracts')"
            icon="description"
            style="background: #5DADE2; color: white"
            label="Посмотреть договор"
            external-label
            label-position="left"
            @click="editCard"
          />
        </q-fab>
      </q-page-sticky>

      <!-- Диалог тегов -->
      <q-dialog v-model="showTagDialog" persistent>
        <q-card style="min-width: 320px; max-width: 420px; width: 93vw; border-radius: 10px">
          <q-toolbar style="background: #ffd93c; color: #333; border-radius: 10px 10px 0 0">
            <q-icon name="label" class="q-mr-sm" />
            <q-toolbar-title style="font-size: 15px; font-weight: 600">
              Теги карточки
            </q-toolbar-title>
            <q-btn
              flat
              round
              dense
              icon="close"
              @click="showTagDialog = false"
            />
          </q-toolbar>
          <q-card-section class="q-pt-md q-pb-sm">
            <!-- Текущие теги в виде чипов -->
            <div v-if="tagList.length > 0" class="row q-gutter-xs q-mb-md" style="flex-wrap: wrap">
              <q-chip
                v-for="(tag, idx) in tagList"
                :key="idx"
                removable
                dense
                :style="{ background: tag.color, color: 'white', fontWeight: '600', fontSize: '12px' }"
                @remove="removeTag(idx)"
              >
                {{ tag.text }}
              </q-chip>
            </div>
            <div v-else class="text-caption q-mb-md" style="color: #999">
              Нет тегов
            </div>

            <!-- Добавить новый тег -->
            <div class="text-caption q-mb-xs" style="color: #666; font-weight: 600">
              Новый тег
            </div>
            <q-input
              v-model="newTagText"
              placeholder="Срочный, VIP, Проблемный..."
              dense
              outlined
              class="q-mb-sm"
              clearable
              @keyup.enter="addTag"
            />
            <div class="row q-gutter-xs q-mb-sm">
              <div
                v-for="c in tagPresetColors"
                :key="c"
                :style="{ width: '26px', height: '26px', borderRadius: '4px', background: c, cursor: 'pointer', border: newTagColor === c ? '2px solid #333' : '2px solid transparent', boxSizing: 'border-box' }"
                @click="newTagColor = c"
              />
            </div>
            <div class="row items-center q-gutter-sm q-mb-sm">
              <div :style="{ width: '26px', height: '26px', borderRadius: '4px', background: newTagColor, border: '1px solid #ccc', flexShrink: 0 }" />
              <div style="flex: 1">
                <input
                  type="color"
                  :value="newTagColor"
                  style="width: 100%; height: 30px; border: 1px solid #ccc; border-radius: 4px; cursor: pointer; padding: 2px"
                  @input="newTagColor = $event.target.value"
                >
              </div>
            </div>
            <q-btn
              unelevated
              label="+ Добавить"
              style="background: #ffd93c; color: #333; font-size: 12px; height: 32px"
              :disable="!newTagText.trim()"
              @click="addTag"
            />
          </q-card-section>
          <q-card-actions align="between" class="q-px-md q-pb-md">
            <q-btn
              flat
              label="Удалить все"
              color="negative"
              :loading="tagLoading"
              @click="clearTag"
            />
            <div class="row q-gutter-xs">
              <q-btn flat label="Отмена" @click="showTagDialog = false" />
              <q-btn
                unelevated
                label="Сохранить"
                style="background: #ffd93c; color: #333"
                :loading="tagLoading"
                @click="saveTag"
              />
            </div>
          </q-card-actions>
        </q-card>
      </q-dialog>

      <!-- Диалог возврата в активные -->
      <q-dialog v-model="showRestoreDialog">
        <q-card style="min-width: 320px; border-radius: 10px">
          <q-toolbar style="background: #5DADE2; color: white">
            <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
              Возврат в активные
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
            <div class="text-caption q-mb-sm" style="color: #888">
              Выберите стадию, в которую нужно вернуть проект. Будет сброшена выбранная стадия и все последующие.
            </div>
            <q-select
              v-model="restoreStage"
              :options="restoreStageOptions"
              label="Стадия"
              outlined
              dense
              emit-value
              map-options
              class="q-mb-sm"
            />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn v-close-popup flat label="Отмена" no-caps />
            <q-btn
              unelevated
              label="Вернуть"
              no-caps
              style="background: #5DADE2; color: white; border-radius: 4px"
              :loading="actionLoading"
              :disable="!restoreStage"
              @click="doRestore"
            />
          </q-card-actions>
        </q-card>
      </q-dialog>

      <!-- Диалог просрочек по подэтапам (открывается по клику на дедлайн) -->
      <q-dialog v-model="showDeadlineStatsDialog">
        <q-card style="min-width: 320px; max-width: 420px; border-radius: 12px">
          <q-card-section class="row items-center q-pb-sm">
            <div>
              <div class="text-subtitle2 text-weight-bold">
                Просрочки по проекту
              </div>
              <div class="text-caption" style="color: #888">
                Дедлайн: {{ fmtDateShort(effectiveDeadline) }}
              </div>
            </div>
            <q-space />
            <q-btn
              flat
              round
              dense
              icon="close"
              @click="showDeadlineStatsDialog = false"
            />
          </q-card-section>
          <q-separator />
          <q-card-section class="q-pt-sm q-pb-md">
            <!-- Нетто итог (общий результат) -->
            <div
              class="q-mb-sm q-pa-sm rounded-borders text-body2 text-weight-bold"
              :style="{ background: netDeadlineDiff > 0 ? '#FFEBEE' : netDeadlineDiff < 0 ? '#E8F5E9' : '#F5F5F5', color: netDeadlineDiff > 0 ? '#E53935' : netDeadlineDiff < 0 ? '#27AE60' : '#555' }"
            >
              <template v-if="netDeadlineDiff > 0">
                Итого просрочка: +{{ netDeadlineDiff }} дн.
              </template>
              <template v-else-if="netDeadlineDiff < 0">
                Итого раньше срока: {{ -netDeadlineDiff }} дн.
              </template>
              <template v-else>
                В срок
              </template>
            </div>
            <div v-if="card.total_pause_days > 0" class="text-caption q-mb-sm" style="color: #888">
              <q-icon name="pause_circle" size="12px" class="q-mr-xs" />Дни ожидания (добавлены к дедлайну): {{ card.total_pause_days }} дн.
            </div>
            <q-separator v-if="deadlineDeviations.length || aheadDeviations.length" class="q-mb-sm" />
            <template v-if="deadlineDeviations.length">
              <div class="text-caption text-weight-bold q-mb-xs" style="color: #E53935">
                Просрочка по подэтапам
              </div>
              <div v-for="d in deadlineDeviations" :key="'o'+d.name" class="q-mb-xs">
                <div class="row items-center">
                  <span class="text-caption" style="flex: 1; color: #333">{{ d.name }}</span>
                  <q-chip
                    dense
                    color="red-1"
                    text-color="red-8"
                    size="xs"
                    icon="trending_up"
                  >
                    +{{ d.diff }} дн.
                  </q-chip>
                </div>
              </div>
              <div class="row q-mt-xs q-mb-sm" style="font-size: 12px; color: #333">
                Итого задержка: <b style="color: #E53935; margin-left: 4px">{{ deadlineDeviations.reduce((s, d) => s + d.diff, 0) }} дн.</b>
              </div>
            </template>
            <q-separator v-if="deadlineDeviations.length && aheadDeviations.length" class="q-my-sm" />
            <template v-if="aheadDeviations.length">
              <div class="text-caption text-weight-bold q-mb-xs" style="color: #27AE60">
                Раньше срока
              </div>
              <div v-for="d in aheadDeviations" :key="'a'+d.name" class="q-mb-xs">
                <div class="row items-center">
                  <span class="text-caption" style="flex: 1; color: #333">{{ d.name }}</span>
                  <q-chip
                    dense
                    color="green-1"
                    text-color="green-8"
                    size="xs"
                    icon="trending_down"
                  >
                    -{{ d.diff }} дн.
                  </q-chip>
                </div>
              </div>
              <div class="row q-mt-xs" style="font-size: 12px; color: #333">
                Итого раньше: <b style="color: #27AE60; margin-left: 4px">{{ aheadDeviations.reduce((s, d) => s + d.diff, 0) }} дн.</b>
              </div>
            </template>
          </q-card-section>
        </q-card>
      </q-dialog>
    </template>

    <div v-else class="text-center q-pa-xl" style="color: #999">
      <q-icon name="search_off" size="48px" class="q-mb-sm" /><div>Карточка не найдена</div>
      <q-btn
        flat
        label="Назад"
        class="q-mt-md"
        no-caps
        style="color: #333"
        @click="$router.back()"
      />
    </div>
  </q-page>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useCrmStore } from 'src/stores/crm'
import { useAuthStore } from 'src/stores/auth'
import { useReferencesStore } from 'src/stores/references'
import { useChatUnreadStore } from 'src/stores/chatUnread'
import { usePermission } from 'src/composables/usePermission'
import { addWorkingDays, calcDeadlineFromTimeline } from 'src/composables/useDeadline'
import { crmApi, employeesApi, filesApi, contractsApi, paymentsApi, locksApi, messengerApi } from 'src/services/api'
import MeasurementDialog from 'src/components/MeasurementDialog.vue'
import InlineChatRoom from 'src/components/InlineChatRoom.vue'
import ContractFormDialog from 'src/components/ContractFormDialog.vue'
import { addToCalendar } from 'src/composables/useCalendar'
import { useEmployeeAvatars } from 'src/composables/useEmployeeAvatars'

const { can, isSuperuser } = usePermission()
const { ensureLoaded: loadAvatars, getAvatarByName } = useEmployeeAvatars()
const authStore = useAuthStore()

// Текущий пользователь — исполнитель (дизайнер/чертёжник) без управленческих прав
const isExecutor = computed(() => {
  const pos = authStore.user?.position || ''
  const secPos = authStore.user?.secondary_position || ''
  const executorPositions = ['Дизайнер', 'Чертёжник', 'Замерщик']
  return executorPositions.some(p => pos === p || secPos === p) && !can('crm_cards.deadlines')
})

/**
 * Может ли текущий пользователь загружать файлы для данной стадии проекта?
 * Управление (есть crm_cards.deadlines) — всё.
 * Исполнитель — только та стадия, в которой он назначен исполнителем.
 */
function canUploadForProjectStage(stageCode) {
  if (!can('crm_cards.files_upload')) return false
  if (!isExecutor.value) return true  // руководство/менеджеры могут всё
  if (!card.value) return false

  const empId = authStore.user?.id
  const se = card.value.stage_executors || []

  // Подэтапы Индивидуального stage2 — оба доступны исполнителям Stage 2 (концепция)
  if ((stageCode === 'stage2_concept' || stageCode === 'stage2_3d') && card.value.project_type === 'Индивидуальный') {
    return se.some(e => e.executor_id === empId && (e.stage_name || '').toLowerCase().includes('концепция'))
  }

  // Для остальных: ищем label в top-level stages и substages
  let stageLabel = ''
  for (const s of projectStages.value) {
    if (s.code === stageCode) { stageLabel = s.label; break }
    for (const sub of (s.substages || [])) {
      if (sub.code === stageCode) { stageLabel = sub.label; break }
    }
  }
  const stageLower = stageLabel.toLowerCase()

  const isAssigned = se.some(e => {
    const eStageLower = (e.stage_name || '').toLowerCase()
    if (stageLower.includes('планировочн') && eStageLower.includes('планировочн') && e.executor_id === empId) return true
    if (stageLower.includes('концепция') && eStageLower.includes('концепция') && e.executor_id === empId) return true
    if (stageLower.includes('чертёж') && eStageLower.includes('чертеж') && e.executor_id === empId) return true
    if (stageLower.includes('чертежная') && eStageLower.includes('чертеж') && e.executor_id === empId) return true
    if (stageLower.includes('3d') || stageLower.includes('визуализ')) {
      if ((eStageLower.includes('визуализ') || eStageLower.includes('3д')) && e.executor_id === empId) return true
    }
    return false
  })
  return isAssigned
}

const route = useRoute()
const router = useRouter()
const $q = useQuasar()
const crmStore = useCrmStore()
const refs = useReferencesStore()
const chatUnreadStore = useChatUnreadStore()

const card = computed(() => crmStore.selectedCard)
const ARCHIVE_COLUMNS = ['Выполненный проект', 'СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР']
const isArchived = computed(() => {
  if (!card.value) return false
  if (ARCHIVE_COLUMNS.includes(card.value.column_name)) return true
  // Также проверяем статус договора
  const cs = contractData.value?.status || ''
  return ['СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР', 'Выполненный проект'].includes(cs)
})
const canRestore = computed(() => {
  const pos = authStore.user?.position || ''
  return pos === 'Руководитель студии' || pos === 'Старший менеджер проектов' || isSuperuser.value
})
const restoreStageOptions = computed(() => {
  const isTemplate = card.value?.project_type === 'Шаблонный'
  return isTemplate ? [
    { label: 'Стадия 1: планировочные решения', value: 'Стадия 1: планировочные решения' },
    { label: 'Стадия 2: рабочие чертежи', value: 'Стадия 2: рабочие чертежи' },
    { label: 'Стадия 3: 3д визуализация (Дополнительная)', value: 'Стадия 3: 3д визуализация (Дополнительная)' },
  ] : [
    { label: 'Стадия 1: планировочные решения', value: 'Стадия 1: планировочные решения' },
    { label: 'Стадия 2: концепция дизайна', value: 'Стадия 2: концепция дизайна' },
    { label: 'Стадия 3: рабочие чертежи', value: 'Стадия 3: рабочие чертежи' },
  ]
})
const activeTab = ref('executors')
const chatTabVisited = ref(false)
const notesTabVisited = ref(false)
const actionLoading = ref(false)
const employeeOptions = ref([])
const cardPayments = ref([])
const showCreatePayment = ref(false)
const actionHistory = ref([])
const contractData = ref(null)
const showContractEdit = ref(false)
const projectFiles = ref([])
const timelineEntries = ref([])
const hasCustomNormDays = computed(() =>
  timelineEntries.value.some(e =>
    e.executor_role !== 'header' && e.custom_norm_days && e.custom_norm_days !== e.norm_days,
  ),
)
const timelineTotals = computed(() => {
  let normTotal = 0, actualTotal = 0, overdueTotal = 0, aheadTotal = 0
  const contractPeriod = contractData.value?.contract_period || 0
  for (const e of timelineEntries.value) {
    if (e.executor_role === 'header') continue
    if (e.is_in_contract_scope !== false) {
      normTotal += (e.norm_days || 0)
    }
    const ad = e.actual_days || 0
    actualTotal += ad
    if (ad > 0) {
      const norm = e.custom_norm_days || e.norm_days || 0
      if (norm > 0) {
        const diff = ad - norm
        if (diff > 0) overdueTotal += diff
        else if (diff < 0) aheadTotal += -diff
      }
    }
  }
  if (contractPeriod > 0) normTotal = contractPeriod
  return { normTotal, actualTotal, overdueTotal, aheadTotal }
})
const workflowStates = ref([])
const showRejectDialog = ref(false)
const rejectSubstage = ref('') // 'concept' | '3d' | '' (для не-stage2)
const showMeasurementDlg = ref(false)
const showRestoreDialog = ref(false)
const showDeadlineStatsDialog = ref(false)
const restoreStage = ref(null)
const rejectReason = ref('')
const rejectFile = ref(null)
// Stage 2 Индивидуальный — нужен выбор подэтапа в диалоге правок
const isRejectStage2Individual = computed(() =>
  (card.value?.column_name || '').toLowerCase().includes('концепция') &&
  card.value?.project_type !== 'Шаблонный',
)
const rejectFilePreviewUrl = ref(null)
watch(rejectFile, (newFile, oldFile) => {
  if (oldFile && rejectFilePreviewUrl.value) URL.revokeObjectURL(rejectFilePreviewUrl.value)
  rejectFilePreviewUrl.value = newFile?.type?.startsWith('image/') ? URL.createObjectURL(newFile) : null
})

// === Telegram-чат ===
const chatData = ref(null)
const chatMembers = ref([])
const chatLoading = ref(false)
const chatCreating = ref(false)
const chatActionLoading = ref(false)
const showSendMessageDlg = ref(false)
const showScriptsDlg = ref(false)
const chatMessageText = ref('')
const chatScripts = ref([])
const showCreateChatDlg = ref(false)
const newChatTitle = ref('')
const showAddMemberDlg = ref(false)
const addMemberEmployeeId = ref(null)
const addMemberLoading = ref(false)

const crmFileInput = ref(null)
const crmUploadStage = ref('')
const crmSyncing = ref(false)
const crmUploadVariation = ref(1)
const historyFilter = ref('all')

const showTagDialog = ref(false)
const tagLoading = ref(false)
const tagList = ref([])
const newTagText = ref('')
const newTagColor = ref('#FF6B6B')
const tagPresetColors = ['#FF6B6B', '#FF9F43', '#F9CA24', '#6AB04C', '#22A6B3', '#4834D4', '#BE2EDD', '#E84393', '#576574', '#2C3E50']

const isChatTab = computed(() => ['chat', 'notes'].includes(activeTab.value))

function _setChatScrollLock(lock) {
  const el = document.querySelector('.q-page-container')
  if (el) el.style.overflowY = lock ? 'hidden' : ''
}

// Загрузка чата при переключении на вкладку + сохранение вкладки в URL
watch(activeTab, (tab) => {
  router.replace({ query: { ...route.query, tab } })
  if (tab === 'chat') chatTabVisited.value = true
  if (tab === 'notes') notesTabVisited.value = true
  _setChatScrollLock(['chat', 'notes'].includes(tab))
})

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
const assignHistory = ref([])
const assignNormDays = ref(0)
const assignSubstepName = ref('')

const otherStageExecutors = computed(() => {
  if (!card.value || !assignStageName.value) return []
  return (card.value.stage_executors || [])
    .filter(se => se.stage_name !== assignStageName.value)
    .reduce((acc, se) => {
      const existing = acc.find(a => a.stage_name === se.stage_name)
      if (!existing || se.id > existing.id) {
        return [...acc.filter(a => a.stage_name !== se.stage_name), se]
      }
      return acc
    }, [])
})

function formatHistoryDate(d) {
  if (!d) return ''
  try { return new Date(d).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' }) }
  catch { return d }
}

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
  draftsman: ['Чертёжник', 'Чертежник'],
}

function filterAssignEmployees(val, update) {
  let list = allEmployeesList.value
  // Фильтр по роли назначения
  const posFilters = ROLE_POSITION_FILTER[assignRoleKey.value]
  if (posFilters) {
    const filtered = list.filter(e =>
      posFilters.some(pf =>
        (e.position || '').toLowerCase().includes(pf.toLowerCase()) ||
        (e.secondary_position || '').toLowerCase().includes(pf.toLowerCase()),
      ),
    )
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
      executorId: executor?.id || null,
    })
  }

  return members
})

const stageExecutors = computed(() => card.value?.stage_executors || [])
const completedStages = computed(() => stageExecutors.value.filter(se => se.completed))

// Команда карточки для добавления в чат (только назначенные сотрудники)
const cardTeamOptions = computed(() => {
  if (!card.value) return []
  const opts = []
  const addOpt = (id, name, role) => { if (id && name) opts.push({ id, label: `${name} (${role})` }) }
  addOpt(card.value.senior_manager_id, card.value.senior_manager_name, 'Ст. менеджер')
  addOpt(card.value.sdp_id, card.value.sdp_name, 'СДП')
  addOpt(card.value.gap_id, card.value.gap_name, 'ГАП')
  addOpt(card.value.manager_id, card.value.manager_name, 'Менеджер')
  addOpt(card.value.surveyor_id, card.value.surveyor_name, 'Замерщик')
  const seenIds = new Set(opts.map(o => o.id))
  for (const se of (card.value.stage_executors || [])) {
    if (se.executor_id && se.executor_name && !seenIds.has(se.executor_id)) {
      seenIds.add(se.executor_id)
      opts.push({ id: se.executor_id, label: `${se.executor_name} (${se.stage_name || 'Исполнитель'})` })
    }
  }
  return opts
})

function filesByStage(stage) { return projectFiles.value.filter(f => f.stage === stage) }

// Путь к файлу правок для стадии (из workflow state)
// Использует label из projectStages для определения префикса (напр. "Стадия 2")
function revisionPathForStage(stageCode) {
  let prefix, substageFilter
  if (stageCode === 'stage2_concept') {
    prefix = 'Стадия 2'
    // Папка Мудбордов: "Концепция-коллажи" в пути
    substageFilter = p => p.toLowerCase().includes('коллаж')
  } else if (stageCode === 'stage2_3d') {
    prefix = 'Стадия 2'
    // Папка Визуализации: "визуализ" в пути (3D визуализация)
    substageFilter = p => p.toLowerCase().includes('визуализ')
  } else {
    const stage = projectStages.value.find(s => s.code === stageCode)
    if (!stage) return ''
    const m = (stage.label || '').match(/^(Стадия \d+)/)
    prefix = m ? m[1] : ''
  }
  if (!prefix) return ''
  const colName = card.value?.column_name || ''
  if (!colName.startsWith(prefix)) return ''
  const candidates = workflowStates.value.filter(w =>
    w.stage_name && w.stage_name.startsWith(prefix) && w.revision_file_path,
  )
  if (substageFilter) {
    // Для подэтапов: только путь, специфичный для данной подпапки
    return candidates.find(w => substageFilter(w.revision_file_path))?.revision_file_path || ''
  }
  return candidates[0]?.revision_file_path || ''
}

// Вариации — вкладки как в десктопе
const activeVariation = ref({}) // { stage_code: active_variation_number }
const createdVariations = ref({}) // { stage_code: [variation_numbers] }

function getVariations(stageCode) {
  const files = filesByStage(stageCode)
  const varsSet = new Set(files.map(f => f.variation || 1))
  const created = createdVariations.value[stageCode] || []
  for (const v of created) varsSet.add(v)
  varsSet.add(1) // Вариация 1 всегда существует по умолчанию
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
    ok: { label: 'Да, удалить', noCaps: true, color: 'negative' },
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
  if ((stageCode === 'stage2_group' || stageCode === 'stage2_concept') && col.includes('концепция')) return true
  if (stageCode === 'stage2_3d') {
    if (col.includes('визуализац')) return true
    // В Индивидуальном Визуализация — подэтап Концепции
    if (card.value?.project_type === 'Индивидуальный' && col.includes('концепция')) return true
  }
  if (stageCode === 'stage3' && (col.includes('чертеж') || col.includes('чертёж'))) return true
  return false
}

const hasWorkflowActions = computed(() => {
  const s = card.value?.workflow_status
  return s && ['in_progress', 'pending_review', 'client_approval', 'act_signing'].includes(s)
})

// Проверка: текущий пользователь — исполнитель текущей стадии
const isCurrentStageExecutor = computed(() => {
  if (!card.value || !authStore.user) return false
  const userId = authStore.user.id
  const columnName = card.value.column_name || ''
  const executors = card.value.stage_executors || []
  // Ищем исполнителя текущей стадии (по column_name)
  const currentStageExecs = executors.filter(se =>
    se.stage_name && columnName.toLowerCase().includes(se.stage_name.toLowerCase().split(':')[1]?.trim().substring(0, 10) || ''),
  )
  if (currentStageExecs.length === 0) return false
  // Берём последнего назначенного (max id)
  const latest = currentStageExecs.reduce((a, b) => a.id > b.id ? a : b)
  return latest.executor_id === userId
})

// Подсказка для START (как десктоп timeline_widget.py:862-877)
const startTooltip = computed(() => {
  const fmt = (d) => {
    if (!d) return 'не установлена'
    try { const [y, m, dd] = d.split('-'); return `${dd}.${m}.${y}` } catch { return d }
  }
  const cd = contractData.value
  const c = card.value
  return `Дата договора: ${fmt(cd?.contract_date)}\nДата замера: ${fmt(c?.survey_date || cd?.measurement_date)}\nДата тех. задания: ${fmt(c?.tech_task_date || cd?.tech_task_date)}\nДата аванса: ${fmt(cd?.advance_payment_paid_date)}`
})

// Оплаты группами по роли (исполнитель видит только свои)
const paymentGroups = computed(() => {
  const list = isExecutor.value
    ? cardPayments.value.filter(p => Number(p.employee_id) === Number(authStore.user?.id))
    : cardPayments.value
  const map = {}
  for (const p of list) {
    const role = p.role || p.stage_name || 'Прочее'
    if (!map[role]) map[role] = { role, items: [] }
    map[role].items.push(p)
  }
  return Object.values(map)
})
const paymentTotal = computed(() => {
  const list = isExecutor.value
    ? cardPayments.value.filter(p => Number(p.employee_id) === Number(authStore.user?.id))
    : cardPayments.value
  return list.reduce((sum, p) => sum + (p.final_amount || p.amount || 0), 0)
})

function paymentRowStyle(p) {
  if (p.is_paid || p.payment_status === 'paid') return { background: '#E8F5E9' }
  if (p.payment_status === 'to_pay') return { background: '#FFF8E1' }
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
  { label: 'Файлы', value: 'file' }, { label: 'Прочее', value: 'other' },
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
// Дата начала = actual_date записи START в timeline (устанавливается автоматически как max дат)
const projectStartDate = computed(() =>
  timelineEntries.value.find(e => e.stage_code === 'START')?.actual_date || null,
)
// Дедлайн проекта = START + срок договора в рабочих днях (как в desktop timeline_widget.py:642-643)
const effectiveDeadline = computed(() => {
  const startDate = projectStartDate.value
  if (!startDate) return null
  const period = contractData.value?.contract_period || card.value?.contract_period
  if (!period || period <= 0) return null
  return addWorkingDays(startDate, period)
})
// Просрочки по завершённым подэтапам (как в desktop _recalculate_days deviation_reasons)
const deadlineDeviations = computed(() => {
  const result = []
  for (const e of timelineEntries.value) {
    if (e.executor_role === 'header') continue
    const ad = e.actual_days || 0
    if (ad <= 0) continue
    const effectiveNorm = e.custom_norm_days || e.norm_days || 0
    if (effectiveNorm <= 0) continue
    const diff = ad - effectiveNorm
    if (diff > 0) result.push({ name: e.stage_name, diff })
  }
  return result
})
const aheadDeviations = computed(() => {
  const result = []
  for (const e of timelineEntries.value) {
    if (e.executor_role === 'header') continue
    const ad = e.actual_days || 0
    if (ad <= 0) continue
    const effectiveNorm = e.custom_norm_days || e.norm_days || 0
    if (effectiveNorm <= 0) continue
    const diff = effectiveNorm - ad
    if (diff > 0) result.push({ name: e.stage_name, diff })
  }
  return result
})
const netDeadlineDiff = computed(() => {
  const overdue = deadlineDeviations.value.reduce((s, d) => s + d.diff, 0)
  const ahead = aheadDeviations.value.reduce((s, d) => s + d.diff, 0)
  return overdue - ahead
})
const isProjectOverdue = computed(() => {
  if (!effectiveDeadline.value) return false
  return new Date(effectiveDeadline.value) < new Date()
})
const deadlineTooltip = computed(() => {
  if (!deadlineDeviations.value.length) return ''
  const lines = deadlineDeviations.value.map(d => `• ${d.name}: +${d.diff} дн.`)
  const total = deadlineDeviations.value.reduce((sum, d) => sum + d.diff, 0)
  return `Просрочки по подэтапам:\n${lines.join('\n')}\nИтого задержка: ${total} дн.`
})

// Авто-расчёт и сохранение даты START (как в desktop timeline_widget._auto_set_start_date)
// Вызывается после загрузки timeline и после обновления данных карточки/договора
async function autoSetStartDate() {
  const cd = contractData.value
  const c = card.value
  if (!cd || !c || !timelineEntries.value.length) return
  const dates = []
  if (cd.contract_date) dates.push(cd.contract_date)
  if (c.survey_date || cd.measurement_date) dates.push(c.survey_date || cd.measurement_date)
  if (c.tech_task_date || cd.tech_task_date) dates.push(c.tech_task_date || cd.tech_task_date)
  if (cd.advance_payment_paid_date) dates.push(cd.advance_payment_paid_date)
  if (!dates.length) return
  const maxDate = [...dates].sort().at(-1)
  const startEntry = timelineEntries.value.find(e => e.stage_code === 'START')
  if (!startEntry) return
  if (startEntry.actual_date === maxDate) return
  try {
    const { api: ax } = await import('src/boot/axios')
    await ax.put(`/api/v1/timeline/${c.contract_id}/entry/${encodeURIComponent('START')}`, { actual_date: maxDate })
    startEntry.actual_date = maxDate
  } catch { /* ignore — не блокируем загрузку */ }
}

function dlHex(d) { if (!d) return '#888'; const days = Math.ceil((new Date(d)-new Date())/86400000); if (days<0) return '#E74C3C'; if (days<=2) return '#F39C12'; return '#888' }
function dlBadgeColor(d) { if (!d) return 'grey'; const days = Math.ceil((new Date(d)-new Date())/86400000); if (days<0) return 'negative'; if (days<=2) return 'warning'; return 'positive' }
function daysLeft(d) { if (!d) return ''; const days = Math.ceil((new Date(d)-new Date())/86400000); if (days<0) return `${Math.abs(days)} дн. просрочено`; if (days===0) return 'сегодня'; return `${days} дн.` }
function fmtDate(d) { if (!d) return '—'; return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' }) }
function fmtDateShort(d) { if (!d) return ''; return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }) }

// Удаление папки секции (замер/фото/референсы) — как десктоп
async function deleteFolderSection(section) {
  const SECTION_FIELDS = {
    measurement: { fields: ['measurement_image_link', 'measurement_yandex_path', 'measurement_file_name'], label: 'замера' },
    photo_documentation: { fields: ['photo_documentation_yandex_path', 'photo_folder_public_link'], label: 'фотофиксации' },
    references: { fields: ['references_yandex_path'], label: 'референсов' },
  }
  const cfg = SECTION_FIELDS[section]
  if (!cfg) return
  $q.dialog({
    title: `Удалить папку ${cfg.label}?`,
    message: 'Файлы будут удалены с Яндекс.Диска',
    cancel: { label: 'Нет', flat: true, noCaps: true },
    ok: { label: 'Удалить', noCaps: true, color: 'negative' },
  }).onOk(async () => {
    try {
      // Очищаем поля в contracts
      const update = {}
      for (const f of cfg.fields) update[f] = ''
      if (contractData.value?.id) await contractsApi.update(contractData.value.id, update)
      // Удаляем файлы из project_files
      const stageFiles = projectFiles.value.filter(f => f.stage === section)
      const { api: ax } = await import('src/boot/axios')
      for (const f of stageFiles) { try { await ax.delete(`/api/v1/files/${f.id}`) } catch {} }
      projectFiles.value = projectFiles.value.filter(f => f.stage !== section)
      // Перезагружаем контракт
      if (contractData.value?.id) {
        const { data: fresh } = await contractsApi.getById(contractData.value.id)
        contractData.value = fresh
      }
      // Если замер — очищаем survey_date в crm_card
      if (section === 'measurement' && card.value?.id) {
        try { await crmApi.updateCard(card.value.id, { survey_date: null }) } catch {}
      }
      $q.notify({ type: 'positive', message: `Папка ${cfg.label} удалена` })
      await reloadCard()
    } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  })
}

// Таймлайн: просрочен если actual_days > norm_days (как десктоп timeline_widget.py:828-834)
function isOverdue(e) {
  if (!e.actual_date || e.executor_role === 'header') return false
  const norm = e.custom_norm_days || e.norm_days || 0
  return norm > 0 && (e.actual_days || 0) > norm
}
// Текущий активный подэтап (из workflow state, не из card)
function isActiveSubstep(e) {
  if (!e.stage_code || e.actual_date) return false
  // Сначала проверяем workflow state (более точный источник)
  const wf = workflowStates.value.find(w => w.stage_name === card.value?.column_name)
  if (wf?.current_substep_code) return wf.current_substep_code === e.stage_code
  // Fallback на card
  return card.value?.current_substep_code === e.stage_code
}
function timelineRowStyle(e) {
  if (e.executor_role === 'header') return 'background: #F5F5F5'
  if (e.is_in_contract_scope === false) return 'background: #E0E0E0'  // вне объёма договора — серый
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
// Редактирование нормо-дней в timeline
const timelineEditEntry = ref(null)
const timelineEditNormDays = ref('')
const timelineEditActualDate = ref('')
const timelineEditVisible = ref(false)

function editNormDays(entry) {
  if (!can('crm_cards.deadlines') || entry.executor_role === 'header') return
  timelineEditEntry.value = entry
  timelineEditNormDays.value = String(entry.custom_norm_days || entry.norm_days || '')
  timelineEditActualDate.value = entry.actual_date || ''
  timelineEditVisible.value = true
}

async function saveTimelineEntry() {
  const entry = timelineEditEntry.value
  if (!entry) return
  try {
    const { api: ax } = await import('src/boot/axios')
    const update = {}
    const days = parseInt(timelineEditNormDays.value)
    if (!isNaN(days) && days >= 0) update.custom_norm_days = days
    const ad = timelineEditActualDate.value
    update.actual_date = ad || null
    await ax.put(`/api/v1/timeline/${card.value.contract_id}/entry/${encodeURIComponent(entry.stage_code)}`, update)
    if ('custom_norm_days' in update) entry.custom_norm_days = update.custom_norm_days
    entry.actual_date = update.actual_date || null
    timelineEditVisible.value = false
    $q.notify({ type: 'positive', message: 'Сохранено' })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}
// Прогресс подэтапов всех стадий (1.x → 2.x → 3.x)
const substepProgress = computed(() => {
  if (!timelineEntries.value.length || !card.value) return []
  const currentStage = card.value.column_name
  if (!currentStage || currentStage === 'Новый заказ' || currentStage === 'В ожидании' || currentStage === 'Выполненный проект') return []

  // Собираем все подэтапы (не заголовки), со всех стадий проекта
  const stageEntries = timelineEntries.value.filter(e =>
    e.executor_role !== 'header' && e.stage_code,
  )

  // Если какой-либо stage_group имеет substage_group записи — плоские записи того же
  // stage_group пропускаем (иначе появляется лишний шаг, напр. "2" перед "2.1" у Эскизного)
  const stageGroupsWithSubstages = new Set(
    stageEntries.filter(e => e.substage_group).map(e => e.stage_group).filter(Boolean),
  )

  // Группируем: substage_group для иерархических стадий (1.x, 2.x),
  // stage_group для плоских (STAGE3 инд., STAGE2/3 шабл. где substage_group = null)
  const groups = []
  const seen = new Set()
  const groupDone = {}

  for (const e of stageEntries) {
    // Пропускаем плоскую запись если её stage_group уже представлен подэтапами
    if (!e.substage_group && stageGroupsWithSubstages.has(e.stage_group)) continue
    const group = e.substage_group || e.stage_group
    if (!group) continue
    if (groupDone[group] === undefined) groupDone[group] = true
    if (!e.actual_date && e.status !== 'skipped') groupDone[group] = false  // пропущенные = завершённые
    if (!seen.has(group)) {
      seen.add(group)
      let label
      if (e.substage_group) {
        // "Подэтап 2.1" → "2.1", "Доп. круг 1" → "+1" (короткий лейбл для бейджа)
        if (e.substage_group.startsWith('Подэтап ')) {
          label = e.substage_group.replace('Подэтап ', '')
        } else if (e.substage_group.startsWith('Доп. круг ')) {
          label = '+' + e.substage_group.replace('Доп. круг ', '')
        } else {
          label = e.substage_group
        }
      } else {
        // Плоская стадия — показываем номер стадии (STAGE3 → "3")
        label = (group || '').replace('STAGE', '')
      }
      groups.push({ label, group })
    }
  }

  // Активная группа — через current_substep_code (как isActiveSubstep в таймлайне)
  const wf = workflowStates.value.find(w => w.stage_name === card.value?.column_name)
  const activeCode = wf?.current_substep_code || card.value?.current_substep_code
  let activeGroup = null
  if (activeCode) {
    const activeEntry = stageEntries.find(e => e.stage_code === activeCode)
    if (activeEntry) activeGroup = activeEntry.substage_group || activeEntry.stage_group
  }

  const result = groups.map(g => ({
    label: g.label,
    active: activeGroup ? activeGroup === g.group : false,
    done: !!groupDone[g.group],
  }))

  // Fallback — если активная группа не определена, берём первый незавершённый
  if (result.length > 0 && !result.some(g => g.active)) {
    const first = result.find(g => !g.done)
    if (first) first.active = true
    else result[result.length - 1].active = true
  }

  return result
})
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
const IMAGE_RE = /\.(jpg|jpeg|png|webp|gif|bmp|heic)$/i
function isImageFile(f) { return IMAGE_RE.test(f.file_name || '') }
function imgStreamUrl(f) {
  const raw = f?.yandex_path || ''
  if (!raw) return f?.public_link || ''
  const path = raw.replace(/^disk:/, '')
  const token = localStorage.getItem('access_token') || ''
  return `/api/v1/files/stream?yandex_path=${encodeURIComponent(path)}&token=${encodeURIComponent(token)}`
}
function fileIcon(f) { const n = (f.file_name||'').toLowerCase(); if (n.endsWith('.pdf')) return 'picture_as_pdf'; if (IMAGE_RE.test(n)) return 'photo_library'; return 'insert_drive_file' }
function fileColor(f) { const n = (f.file_name||'').toLowerCase(); if (n.endsWith('.pdf')) return 'red'; if (IMAGE_RE.test(n)) return 'green'; return 'grey-7' }

// === Галерея изображений в файлах стадий ===
const crmGalleryVisible = ref(false)
const crmGalleryIdx = ref(0)
const crmGalleryFiles = ref([])
const crmCurrentGalleryFile = computed(() => crmGalleryFiles.value[crmGalleryIdx.value] || null)

function openFile(f) {
  if (!f.public_link) return
  if (isImageFile(f)) {
    const imgs = projectFiles.value.filter(pf => isImageFile(pf) && pf.public_link)
    const idx = imgs.findIndex(pf => pf.id === f.id)
    if (idx >= 0) {
      crmGalleryFiles.value = imgs
      crmGalleryIdx.value = idx
      crmGalleryVisible.value = true
      return
    }
  }
  window.open(f.public_link, '_blank')
}
// Открыть файл стадии: картинки → галерея только из этой стадии/вариации
function openStageFile(f, stageCode) {
  if (isImageFile(f)) {
    const imgs = filesForVariation(stageCode).filter(pf => isImageFile(pf))
    const idx = imgs.findIndex(pf => pf.id === f.id)
    if (idx >= 0) {
      crmGalleryFiles.value = imgs
      crmGalleryIdx.value = idx
      crmGalleryVisible.value = true
      return
    }
  }
  if (f.public_link) window.open(f.public_link, '_blank')
}
function crmPrevImage() { if (crmGalleryIdx.value > 0) crmGalleryIdx.value-- }
function crmNextImage() { if (crmGalleryIdx.value < crmGalleryFiles.value.length - 1) crmGalleryIdx.value++ }
function handleCrmGallerySwipe({ direction }) {
  if (direction === 'right') crmPrevImage()
  else if (direction === 'left') crmNextImage()
}
function actionIcon(t) { if (!t) return 'history'; const l=t.toLowerCase(); if (l.includes('move')||l.includes('column')) return 'swap_horiz'; if (l.includes('assign')) return 'person_add'; if (l.includes('submit')) return 'send'; if (l.includes('accept')) return 'check_circle'; if (l.includes('reject')) return 'replay'; if (l.includes('payment')) return 'payments'; if (l.includes('deadline')) return 'event'; if (l.includes('file')) return 'attach_file'; return 'history' }
function actionColor(t) { if (!t) return 'grey-5'; const l=t.toLowerCase(); if (l.includes('accept')||l.includes('complete')) return 'positive'; if (l.includes('reject')) return 'negative'; if (l.includes('submit')) return 'info'; return 'grey-7' }

// === Заметки (текстовые + голосовые) ===
const noteText = ref('')
const noteSending = ref(false)

// Список заметок — фильтр из actionHistory по типам note/voice_note
const notesList = computed(() => {
  return actionHistory.value.filter(h =>
    h.action_type === 'note' || h.action_type === 'voice_note',
  ).sort((a, b) => new Date(b.action_date) - new Date(a.action_date))
})

// Открыть голосовую заметку — получить публичную ссылку с ЯД
// URL для стриминга аудио через сервер
function voiceStreamUrl(path) {
  const cleanPath = path.replace(/^disk:/, '')
  const token = localStorage.getItem('access_token') || ''
  return `https://crm.festivalcolor.ru/api/v1/files/stream?yandex_path=${encodeURIComponent(cleanPath)}&token=${encodeURIComponent(token)}`
}

// Извлечь путь голосовой записи из description [voice:/path/file.webm]
function noteVoiceUrl(n) {
  const desc = n.description || ''
  const match = desc.match(/\[voice:([^\]]+)\]/)
  return match ? match[1] : ''
}

// Отправить текстовую заметку
async function submitNote() {
  if (!noteText.value?.trim() || !card.value?.id) return
  noteSending.value = true
  try {
    const { api: ax } = await import('src/boot/axios')
    await ax.post('/api/v1/action-history', {
      action_type: 'note',
      entity_type: 'crm_card',
      entity_id: card.value.id,
      description: noteText.value.trim(),
    })
    noteText.value = ''
    $q.notify({ type: 'positive', message: 'Заметка добавлена' })
    await reloadCard()
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Ошибка сохранения заметки' })
  } finally { noteSending.value = false }
}

// === Голосовая заметка — добавление в историю CRM карточки ===
async function onVoiceRecorded({ url, duration, path }) {
  try {
    const { api: ax } = await import('src/boot/axios')
    const durationStr = `${Math.floor(duration / 60)}:${String(duration % 60).padStart(2, '0')}`
    const voicePath = url || path || ''
    await ax.post('/api/v1/action-history', {
      action_type: 'voice_note',
      entity_type: 'crm_card',
      entity_id: card.value.id,
      description: `[voice:${voicePath}] Голосовая заметка (${durationStr})`,
    })
    $q.notify({ type: 'positive', message: 'Голосовая заметка сохранена' })
    await reloadCard()
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Ошибка сохранения записи в историю' })
  }
}

// === Добавить дедлайн проекта в календарь ===
function addDeadlineToCalendar() {
  if (!effectiveDeadline.value) return
  addToCalendar({
    title: `CRM: ${card.value.address || card.value.contract_number} — ${card.value.column_name || 'проект'}`,
    description: `Дедлайн проекта ${card.value.contract_number}. Стадия: ${card.value.column_name || ''}`,
    startDate: effectiveDeadline.value,
    location: card.value.address || '',
    reminder: 1440, // за 1 день
  }, $q)
}

// === ACTIONS ===
function editCard() {
  if (card.value?.contract_id) {
    router.push(`/contracts/${card.value.contract_id}`)
  }
}

function openContractEdit() {
  if (!contractData.value && card.value?.contract_id) {
    contractsApi.getById(card.value.contract_id).then(({ data }) => {
      contractData.value = data
      showContractEdit.value = true
    })
  } else {
    showContractEdit.value = true
  }
}

async function doAction(action) {
  if (action === 'submit') {
    const confirmed = await new Promise((resolve) => {
      $q.dialog({
        title: 'Сдать работу',
        message: 'Перед сдачей убедитесь, что загрузили результат работы в данные карточки. Продолжить?',
        ok: { label: 'Сдать работу', color: 'positive', noCaps: true, unelevated: true },
        cancel: { label: 'Отмена', flat: true, noCaps: true },
        persistent: true,
      }).onOk(() => resolve(true)).onCancel(() => resolve(false))
    })
    if (!confirmed) return
  }
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

function openRejectDialog() {
  rejectReason.value = ''
  rejectFile.value = null
  // S2_1_* = Мудборды (Концепция-коллажи), S2_2_+ = Визуализация (3D)
  if (isRejectStage2Individual.value) {
    const activeCode = card.value?.current_substep_code
    rejectSubstage.value = activeCode?.startsWith('S2_1_') ? 'concept' : activeCode ? '3d' : ''
  } else {
    rejectSubstage.value = ''
  }
  showRejectDialog.value = true
}

async function submitReject() {
  if (!rejectReason.value) { $q.notify({ type: 'warning', message: 'Укажите причину' }); return }
  actionLoading.value = true
  try {
    let filePath = null
    if (rejectFile.value) {
      const contractFolder = (contractData.value?.yandex_folder_path || '').replace(/^disk:/, '')
      let corrPath
      // Для Стадии 2 Индивидуального — раздельные папки по подэтапам
      if (rejectSubstage.value === 'concept') {
        corrPath = `${contractFolder}/2 стадия - Концепция дизайна/Концепция-коллажи/Правки`
      } else if (rejectSubstage.value === '3d') {
        corrPath = `${contractFolder}/2 стадия - Концепция дизайна/3D визуализация/Правки`
      } else {
        // Остальные стадии — маппинг по column_name
        const STAGE_YD_FOLDERS = {
          'Стадия 1: планировочные решения': '1 стадия - Планировочное решение',
          'Стадия 2: концепция дизайна': '2 стадия - Концепция дизайна',
          'Стадия 3: рабочие чертежи': '3 стадия - Чертежный проект',
          'Стадия 2: рабочие чертежи': '2 стадия - Чертежный проект',
          'Стадия 3: 3д визуализация (Дополнительная)': '3D визуализация',
        }
        const ydStageName = STAGE_YD_FOLDERS[card.value.column_name] || (card.value.column_name || 'Стадия').replace(/:/g, ' -')
        corrPath = contractFolder ? `${contractFolder}/${ydStageName}/Правки` : `/CRM/Правки/${card.value.contract_number || card.value.id}`
      }
      const yp = `${corrPath}/${rejectFile.value.name}`
      await filesApi.upload(rejectFile.value, yp)
      filePath = corrPath
    }
    await crmApi.rejectWork(card.value.id, { reason: rejectReason.value, revision_file_path: filePath })
    $q.notify({ type: 'positive', message: 'Отправлено на исправление' })
    showRejectDialog.value = false; rejectReason.value = ''; rejectFile.value = null; rejectSubstage.value = ''
    await reloadCard()
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  finally { actionLoading.value = false }
}

// Назначение / изменение члена команды
async function showAssignDialog(member, mode) {
  assignRole.value = member.role
  assignRoleKey.value = member.roleKey
  assignStageName.value = member.stageName || ''
  assignMode.value = mode
  // Для исполнителей стадий (дизайнер/чертёжник) — запрашиваем дедлайн с авторасчётом из норма-дней
  assignNeedsDeadline.value = !!member.isStageExecutor
  assignDialogTitle.value = mode === 'assign' ? `Назначить ${member.role}` : `Изменить ${member.role}`
  assignEmployeeId.value = null
  assignDeadline.value = ''

  // Авторасчёт дедлайна + норма-дней из таймлайна (как десктоп crm_dialogs.py:719-734)
  assignNormDays.value = 0
  assignSubstepName.value = ''
  if (member.isStageExecutor && timelineEntries.value.length) {
    const stageNumMatch = (member.stageName || '').match(/Стадия\s+(\d+)/i)
    const stageNum = stageNumMatch ? stageNumMatch[1] : null
    if (stageNum) {
      const { getStageDeadlineInfo } = await import('src/composables/useDeadline')
      const info = getStageDeadlineInfo(timelineEntries.value, member.stageName || '')
      if (info.deadline) assignDeadline.value = info.deadline
      assignNormDays.value = info.normDays || 0
      assignSubstepName.value = info.substepName || ''
    }
  }

  // Загрузить историю назначений для этой стадии
  if (member.stageName) {
    const history = (card.value.stage_executors || [])
      .filter(se => se.stage_name === member.stageName)
      .sort((a, b) => new Date(b.assigned_date || 0) - new Date(a.assigned_date || 0))
    assignHistory.value = history
  } else {
    assignHistory.value = []
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
        completed: false,
      })

      // 2. Двойная запись оплат (как десктоп _reassign_payments_via_api)
      if (oldExecutorId && oldExecutorId !== assignEmployeeId.value) {
        // Помечаем старые оплаты как reassigned
        const oldPayments = cardPayments.value.filter(p =>
          p.employee_id === oldExecutorId && p.role === roleName && !p.reassigned,
        )
        for (const op of oldPayments) {
          try {
            const month = `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`
            await paymentsApi.update(op.id, { reassigned: true, report_month: op.report_month || month })
          } catch {}
        }

        // Создаём новые оплаты для нового исполнителя
        try {
          const calcRes = await paymentsApi.calculate({ contract_id: card.value.contract_id, employee_id: assignEmployeeId.value, role: roleName, stage_name: stageName || undefined, project_subtype: card.value.project_subtype || undefined })
          const fullAmount = typeof calcRes.data === 'number' ? calcRes.data : (calcRes.data?.amount || 0)
          if (fullAmount > 0) {
            const month = `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`
            if (isTemplate) {
              await paymentsApi.create({ contract_id: card.value.contract_id, employee_id: assignEmployeeId.value, role: roleName, stage_name: stageName || undefined, payment_type: 'Полная оплата', crm_card_id: card.value.id, calculated_amount: fullAmount, final_amount: fullAmount, report_month: null })
            } else {
              const advance = Math.round(fullAmount / 2)
              const balance = fullAmount - advance
              await paymentsApi.create({ contract_id: card.value.contract_id, employee_id: assignEmployeeId.value, role: roleName, stage_name: stageName || undefined, payment_type: 'Аванс', crm_card_id: card.value.id, calculated_amount: advance, final_amount: advance, report_month: month })
              await paymentsApi.create({ contract_id: card.value.contract_id, employee_id: assignEmployeeId.value, role: roleName, stage_name: stageName || undefined, payment_type: 'Доплата', crm_card_id: card.value.id, calculated_amount: balance, final_amount: balance, report_month: null })
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
        // Создаём оплаты при первом назначении (аналогично переназначению)
        try {
          const calcRes = await paymentsApi.calculate({ contract_id: card.value.contract_id, employee_id: assignEmployeeId.value, role: roleName, stage_name: stageName, project_subtype: card.value.project_subtype || undefined })
          const fullAmount = typeof calcRes.data === 'number' ? calcRes.data : (calcRes.data?.amount || 0)
          if (fullAmount > 0) {
            if (isTemplate) {
              await paymentsApi.create({ contract_id: card.value.contract_id, employee_id: assignEmployeeId.value, role: roleName, stage_name: stageName, payment_type: 'Полная оплата', crm_card_id: card.value.id, calculated_amount: fullAmount, final_amount: fullAmount, report_month: null })
            } else {
              const month = `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`
              const advance = Math.round(fullAmount / 2)
              const balance = fullAmount - advance
              await paymentsApi.create({ contract_id: card.value.contract_id, employee_id: assignEmployeeId.value, role: roleName, stage_name: stageName, payment_type: 'Аванс', crm_card_id: card.value.id, calculated_amount: advance, final_amount: advance, report_month: month })
              await paymentsApi.create({ contract_id: card.value.contract_id, employee_id: assignEmployeeId.value, role: roleName, stage_name: stageName, payment_type: 'Доплата', crm_card_id: card.value.id, calculated_amount: balance, final_amount: balance, report_month: null })
            }
          }
        } catch (e) { console.warn('Ошибка создания оплаты при назначении:', e) }
      } else if (roleKey === 'surveyor') {
        // Замерщик — сервер auto_create_employee_payment создаёт платёж автоматически
        await crmApi.updateCard(card.value.id, { surveyor_id: assignEmployeeId.value })
      } else {
        // Руководство (СМ, СДП, ГАП, Менеджер) — сервер auto_create_employee_payment
        // создаёт платежи автоматически при updateCard, дублировать не нужно
        const update = {}; update[`${roleKey}_id`] = assignEmployeeId.value
        await crmApi.updateCard(card.value.id, update)
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
      const { api: ax } = await import('src/boot/axios')
      // 1. Удаляем оплаты для этой роли
      const roleName = ROLE_NAMES[member.roleKey] || member.role
      const rolePayments = cardPayments.value.filter(p => p.role === roleName && !p.reassigned)
      for (const rp of rolePayments) {
        try { await paymentsApi.delete(rp.id) } catch {}
      }
      // 2. Убираем исполнителя
      const cardFields = ['senior_manager', 'sdp', 'gap', 'manager', 'surveyor']
      if (cardFields.includes(member.roleKey)) {
        // Роли хранящиеся как поля crm_cards
        const update = {}; update[`${member.roleKey}_id`] = null
        await crmApi.updateCard(card.value.id, update)
      } else if (member.executorId) {
        // Стадийные роли (designer, draftsman) — удаляем из stage_executors по ID
        await ax.delete(`/api/v1/crm/stage-executors/${member.executorId}`)
      }
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

// П1: создание платежа вручную
function openCreatePaymentDialog() {
  const se = stageExecutors.value.filter(s => s.executor_id)
  const empOptions = se.map(s => ({ label: `${s.executor_name} (${s.stage_name})`, value: s.executor_id, role: s.stage_name }))
  if (empOptions.length === 0) {
    $q.notify({ type: 'warning', message: 'Нет назначенных сотрудников' })
    return
  }
  // Шаг 1: выбор сотрудника
  $q.dialog({
    title: 'Создать платёж',
    message: 'Выберите сотрудника:',
    options: { model: empOptions[0]?.value, items: empOptions.map(e => ({ label: e.label, value: e.value })) },
    cancel: { label: 'Отмена', flat: true, noCaps: true },
    ok: { label: 'Далее', noCaps: true, color: 'primary' },
  }).onOk(empId => {
    const emp = empOptions.find(e => e.value === empId)
    // Шаг 2: ввод суммы
    $q.dialog({
      title: `Сумма платежа: ${emp?.label}`,
      prompt: { model: '0', type: 'number', label: 'Сумма (руб.)' },
      cancel: { label: 'Отмена', flat: true, noCaps: true },
      ok: { label: 'Создать', noCaps: true, color: 'positive' },
    }).onOk(async (amount) => {
      try {
        const data = {
          contract_id: card.value.contract_id,
          employee_id: empId,
          role: emp?.role || '',
          payment_type: 'Полная оплата',
          crm_card_id: card.value.id,
          calculated_amount: parseFloat(amount),
          final_amount: parseFloat(amount),
          report_month: null,
        }
        const { data: created } = await paymentsApi.create(data)
        if (created) cardPayments.value.push(created)
        $q.notify({ type: 'positive', message: 'Платёж создан' })
      } catch (err) {
        $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка создания платежа' })
      }
    })
  })
}

// Следим за showCreatePayment
watch(showCreatePayment, (val) => { if (val) { openCreatePaymentDialog(); showCreatePayment.value = false } })

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
      } catch { $q.notify({ type: 'warning', message: 'Не удалось создать папку на ЯД' }) }
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
      stage3: '3 стадия - Чертежный проект',                            // Стадия 3
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

      // Шаг 1: получить upload URL от сервера и загрузить файл напрямую на ЯД из браузера
      // (сервер→ЯД медленный ~120 KB/s, браузер→ЯД использует скорость домашнего интернета)
      let publicLink = ''
      let actualYpClean = ypClean
      let actualFileName = file.name
      try {
        const urlRes = await filesApi.getUploadUrl(ypClean)
        const uploadUrl = urlRes.data?.upload_url
        if (urlRes.data?.yandex_path) actualYpClean = urlRes.data.yandex_path
        if (urlRes.data?.file_name) actualFileName = urlRes.data.file_name

        if (!uploadUrl) throw new Error('Нет URL загрузки')

        // PUT напрямую на ЯД из браузера — без ограничений по скорости сервера
        const putRes = await fetch(uploadUrl, {
          method: 'PUT',
          body: file,
          headers: { 'Content-Type': file.type || 'application/octet-stream' },
        })
        if (!putRes.ok && putRes.status !== 201) {
          throw new Error(`ЯД PUT: ${putRes.status}`)
        }

        // Получить публичную ссылку после загрузки
        try {
          const linkRes = await filesApi.getPublicLink(actualYpClean)
          publicLink = linkRes.data?.public_link || ''
        } catch { /* ссылку получим при сканировании */ }
      } catch (uploadErr) {
        const msg = uploadErr.message || (uploadErr.response?.status ? `HTTP ${uploadErr.response.status}` : 'ошибка')
        $q.notify({ type: 'warning', message: `ЯД: ${msg}` })
      }

      // Шаг 2: создание записи в БД
      try {
        const { api: ax } = await import('src/boot/axios')
        await ax.post('/api/v1/files/', {
          contract_id: contractId, stage, file_name: actualFileName,
          file_type: file.type?.includes('image') ? 'image' : actualFileName.endsWith('.pdf') ? 'pdf' : 'other',
          public_link: publicLink, yandex_path: actualYpClean,
          file_order: projectFiles.value.length + i + 1, variation,
        })
      } catch (dbErr) {
        const d = dbErr.response?.data?.detail
        $q.notify({ type: 'negative', message: `Запись в БД: ${typeof d === 'string' ? d : JSON.stringify(d || dbErr.message)}` })
      }
    }
    $q.notify({ type: 'positive', message: `Загружено: ${fileList.length}` })

    // Обновляем публичные ссылки на папки (как десктоп — ВСЕ стадии включая stage1/2/3)
    const FOLDER_LINK_FIELDS = {
      measurement: 'measurement_image_link',
      photo_documentation: 'photo_documentation_yandex_path',
      references: 'references_yandex_path',
      stage1: 'act_planning_link',
      stage2_concept: 'act_concept_link',
      stage2_3d: 'act_concept_link',
      stage3: 'act_final_link',
      tech_task: 'tech_task_link',
    }
    const linkField = FOLDER_LINK_FIELDS[stage]
    if (linkField && contractFolder) {
      try {
        const folderPath = `${contractFolder}/${STAGE_FOLDERS[stage] || stage}`
        const { data: linkData } = await filesApi.getPublicLink(folderPath)
        if (linkData.public_link && can('contracts.update')) {
          const upd = {}; upd[linkField] = linkData.public_link
          await contractsApi.update(card.value.contract_id, upd)
        }
      } catch {}
    }

    // Scan + перезагрузить файлы и контракт
    try { const { api: ax } = await import('src/boot/axios'); await ax.post(`/api/v1/files/scan/${card.value.contract_id}`) } catch {}
    try { const { data } = await filesApi.getContractFiles(card.value.contract_id); projectFiles.value = data || [] } catch {}
    try { const { data: fresh } = await contractsApi.getById(card.value.contract_id); contractData.value = fresh } catch {}
  } catch (err) {
    $q.notify({ type: 'negative', message: err.message || 'Ошибка' })
  } finally { $q.loading.hide(); event.target.value = '' }
}

// === ЗАГРУЗКА ===
async function reloadCard() { const id = route.params.id; await crmStore.loadCard(id); await loadAdditionalData(id) }

async function loadAdditionalData(cardId) {
  // Оплаты — загружаем по contract_id через правильный endpoint
  try {
    const contractId = card.value?.contract_id
    if (contractId) {
      const { data } = await crmApi.getPayments(contractId)
      const cid = Number(cardId)
      // Фильтр: только этой карточки, исключая оклады
      cardPayments.value = (data || []).filter(p => Number(p.crm_card_id) === cid && p.source !== 'Оклад')
    }
  } catch { cardPayments.value = [] }

  // История действий
  try {
    const { api: ax } = await import('src/boot/axios')
    const resp = await ax.get(`/api/v1/crm/cards/${cardId}/action-history?_t=${Date.now()}`)
    actionHistory.value = resp.data || []
  } catch {
    actionHistory.value = []
  }

  // Сотрудники
  try {
    const { data } = await employeesApi.getList()
    const all = (data || []).filter(e => e.status === 'активный')
    allEmployeesList.value = all
    employeeOptions.value = all.map(e => ({ id: e.id, label: `${e.full_name} (${e.position})` }))
  } catch { /* ignore */ }

  // Данные контракта + файлы + timeline
  const cid = card.value?.contract_id
  if (!cid) {
    $q.notify({ type: 'warning', message: `contract_id не найден (card loaded: ${!!card.value})`, timeout: 5000 })
    return
  }

  try { const { data } = await contractsApi.getById(cid); contractData.value = data } catch { /* ignore */ }
  try { const { data } = await crmApi.getWorkflowState(card.value.id); workflowStates.value = Array.isArray(data) ? data : data ? [data] : [] } catch { workflowStates.value = [] }
  try { const { data } = await filesApi.getContractFiles(cid); projectFiles.value = data || [] } catch { projectFiles.value = [] }
  // Фоновый скан ЯД — восстанавливает записи в БД для файлов которые там есть но не в БД
  import('src/boot/axios').then(({ api: ax }) => {
    ax.post(`/api/v1/files/scan/${cid}`).then(async (resp) => {
      if ((resp.data?.new_files_added || 0) > 0) {
        filesApi.getContractFiles(cid).then(({ data }) => { projectFiles.value = data || [] }).catch(() => {})
      }
    }).catch(() => {})
  })
  try {
    const { api: ax } = await import('src/boot/axios')
    const resp = await ax.get(`/api/v1/timeline/${cid}?_t=${Date.now()}`)
    timelineEntries.value = Array.isArray(resp.data) ? resp.data : []
  } catch {
    timelineEntries.value = []
  }

  // Авто-пересчёт даты START (запускаем фоново, не блокируем загрузку)
  autoSetStartDate()

  // Чат — грузим всегда, чтобы данные были готовы при открытии вкладки
  loadChat()
}

// Кнопка «Синхронизировать с ЯД» — обратная синхронизация
// === Архивные действия ===
async function doRestore() {
  if (!restoreStage.value) return
  actionLoading.value = true
  try {
    const { api: ax } = await import('src/boot/axios')
    // 1. Обновляем статус договора → В работе
    if (card.value.contract_id) {
      await contractsApi.update(card.value.contract_id, { status: 'В работе', termination_reason: null })
    }
    // 2. Перемещаем карточку на выбранную стадию
    await crmApi.moveCard(card.value.id, restoreStage.value)
    // 3. Сбрасываем стадии (выбранную и все последующие)
    try { await ax.post(`/api/v1/crm/cards/${card.value.id}/reset-stages`, { stage_name: restoreStage.value }) } catch {}
    $q.notify({ type: 'positive', message: 'Карточка возвращена в активные' })
    showRestoreDialog.value = false
    restoreStage.value = null
    await reloadCard()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка возврата' })
  } finally { actionLoading.value = false }
}

async function transferToSupervision() {
  $q.dialog({ title: 'Подтверждение', message: 'Перевести карточку в авторский надзор?', cancel: { label: 'Нет', flat: true, noCaps: true }, ok: { label: 'Да', noCaps: true, color: 'warning' } }).onOk(async () => {
    actionLoading.value = true
    try {
      const { api: ax } = await import('src/boot/axios')
      // 1. Обновляем статус договора → АВТОРСКИЙ НАДЗОР
      if (card.value.contract_id) {
        await contractsApi.update(card.value.contract_id, { status: 'АВТОРСКИЙ НАДЗОР' })
      }
      // 2. Создаём карточку надзора (если нет)
      try {
        await ax.post('/api/v1/supervision/cards', {
          contract_id: card.value.contract_id,
          column_name: 'Новый заказ',
          start_date: new Date().toISOString().slice(0, 10),
          deadline: card.value.deadline || '',
        })
      } catch {}
      $q.notify({ type: 'positive', message: 'Переведено в авторский надзор' })
      await reloadCard()
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
    } finally { actionLoading.value = false }
  })
}

async function doAdvanceRound() {
  actionLoading.value = true
  try {
    await crmApi.advanceRound(card.value.id)
    $q.notify({ type: 'positive', message: 'Переход к следующему подэтапу' })
    await reloadCard()
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  finally { actionLoading.value = false }
}

async function doCloseStage() {
  actionLoading.value = true
  try {
    await crmApi.closeStage(card.value.id)
    $q.notify({ type: 'positive', message: 'Этап закрыт, переход к подписанию акта' })
    await reloadCard()
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  finally { actionLoading.value = false }
}

async function doAddExtraRound() {
  actionLoading.value = true
  try {
    const colLower = (card.value.column_name || '').toLowerCase()
    const isDesign = colLower.includes('концепция') || colLower.includes('визуализац') || colLower.includes('3д')
    const executorRole = isDesign ? 'Дизайнер' : 'Чертёжник'
    await crmApi.addExtraRound(card.value.id, { executor_role: executorRole })
    $q.notify({ type: 'positive', message: 'Добавлен дополнительный круг' })
    await reloadCard()
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  finally { actionLoading.value = false }
}

async function doManagerAcceptance() {
  actionLoading.value = true
  try {
    const stageName = card.value.column_name || ''
    const stageExec = (card.value.stage_executors || []).find(se => se.stage_name === stageName)
    const executorName = stageExec?.executor_name || 'Исполнитель'
    const managerId = authStore.user?.id || 0
    await crmApi.managerAcceptance(card.value.id, { stage_name: stageName, executor_name: executorName, manager_id: managerId })
    $q.notify({ type: 'positive', message: 'Принято менеджером' })
    await reloadCard()
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  finally { actionLoading.value = false }
}

async function doResetApproval() {
  actionLoading.value = true
  try {
    await crmApi.resetApproval(card.value.id)
    $q.notify({ type: 'positive', message: 'Согласование сброшено' })
    await reloadCard()
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  finally { actionLoading.value = false }
}

async function doResetDesigner() {
  actionLoading.value = true
  try {
    await crmApi.resetDesigner(card.value.id)
    $q.notify({ type: 'positive', message: 'Отметка дизайнера сброшена' })
    await reloadCard()
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  finally { actionLoading.value = false }
}

async function doResetDraftsman() {
  actionLoading.value = true
  try {
    await crmApi.resetDraftsman(card.value.id)
    $q.notify({ type: 'positive', message: 'Отметка чертёжника сброшена' })
    await reloadCard()
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  finally { actionLoading.value = false }
}

function parseCrmTags(tagsStr) {
  if (!tagsStr) return []
  try {
    const parsed = JSON.parse(tagsStr)
    if (Array.isArray(parsed)) return parsed.map(t => ({ text: String(t.text || ''), color: String(t.color || '#FF6B6B') }))
    return [{ text: String(tagsStr), color: '#FF6B6B' }]
  } catch { return [{ text: String(tagsStr), color: '#FF6B6B' }] }
}

function openTagDialog() {
  tagList.value = parseCrmTags(card.value?.tags)
  newTagText.value = ''
  newTagColor.value = '#FF6B6B'
  showTagDialog.value = true
}

function addTag() {
  const text = newTagText.value.trim()
  if (!text) return
  tagList.value.push({ text, color: newTagColor.value })
  newTagText.value = ''
}

function removeTag(idx) {
  tagList.value.splice(idx, 1)
}

async function saveTag() {
  tagLoading.value = true
  try {
    const tagsJson = tagList.value.length > 0 ? JSON.stringify(tagList.value) : null
    await crmApi.updateCard(card.value.id, { tags: tagsJson, tag_color: null })
    $q.notify({ type: 'positive', message: 'Теги сохранены' })
    showTagDialog.value = false
    await reloadCard()
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка сохранения тегов' }) }
  finally { tagLoading.value = false }
}

async function clearTag() {
  tagLoading.value = true
  try {
    await crmApi.updateCard(card.value.id, { tags: null, tag_color: null })
    $q.notify({ type: 'positive', message: 'Теги удалены' })
    showTagDialog.value = false
    await reloadCard()
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  finally { tagLoading.value = false }
}

function openRevisionFolder(stageCode) {
  const path = revisionPathForStage(stageCode)
  if (!path) return
  const clean = path.replace(/^disk:\/?/, '').replace(/^\//, '')
  const encoded = encodeURIComponent(clean).replace(/%2F/g, '/')
  window.open(`https://disk.yandex.ru/client/disk/${encoded}`, '_blank')
}

async function repairWorkflow() {
  actionLoading.value = true
  try {
    const { api: ax } = await import('src/boot/axios')
    const { data } = await ax.post(`/api/v1/crm/cards/${card.value.id}/workflow/repair`)
    if (data.old_substep === data.new_substep && data.old_status === data.new_status) {
      $q.notify({ type: 'info', message: 'Карточка в порядке — восстановление не требуется' })
    } else {
      $q.notify({ type: 'positive', message: `Восстановлено: ${data.old_substep || '?'} → ${data.new_substep || '?'}` })
      await reloadCard()
    }
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка ремонта' })
  } finally { actionLoading.value = false }
}

async function onMeasurementSaved() {
  // Перезагружаем данные карточки и файлы после сохранения замера
  await crmStore.loadCard(card.value.id)
  if (card.value?.contract_id) {
    try { const { data } = await contractsApi.getById(card.value.contract_id); contractData.value = data } catch {}
    try { const { data } = await filesApi.getContractFiles(card.value.contract_id); projectFiles.value = data } catch {}
  }
  autoSetStartDate()
}

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

// === Telegram-чат — загрузка и действия ===

function _tgDeepLink(link) {
  if (!link) return '#'
  // t.me/joinchat/HASH или t.me/+HASH → tg://join?invite=HASH
  const m = link.match(/t\.me\/(?:joinchat\/|\+)([A-Za-z0-9_-]+)/)
  if (m) return `tg://join?invite=${m[1]}`
  return link
}

async function loadChat() {
  if (!card.value?.id) return
  chatLoading.value = true
  try {
    const { api: ax } = await import('src/boot/axios')
    const resp = await ax.get(`/api/v1/messenger/chats/by-card/${card.value.id}`, { validateStatus: s => s < 500 })
    if (resp.data && resp.data.chat) {
      chatData.value = resp.data.chat
      chatMembers.value = resp.data.members || []
    } else {
      chatData.value = null
      chatMembers.value = []
    }
  } catch { chatData.value = null }
  chatLoading.value = false
}

function _openCreateChatDlg() {
  const prefix = card.value?.project_type === 'Шаблонный' ? 'ШП' : 'ИН'
  const city = (card.value?.city || '').replace(/_/g, '-')
  const address = (card.value?.address || '').replace(/_/g, '-')
  newChatTitle.value = [prefix, city, address].filter(Boolean).join('-')
  showCreateChatDlg.value = true
}

async function createProjectChat() {
  if (!card.value?.id) return
  chatCreating.value = true
  showCreateChatDlg.value = false
  try {
    // Автоматически добавляем всех назначенных членов команды
    const c = card.value
    const memberFields = [
      { key: 'senior_manager_id', role: 'Старший менеджер' },
      { key: 'sdp_id', role: 'СДП' },
      { key: 'gap_id', role: 'ГАП' },
      { key: 'manager_id', role: 'Менеджер' },
      { key: 'surveyor_id', role: 'Замерщик' },
    ]
    const members = memberFields
      .filter(m => c[m.key])
      .map(m => ({ member_type: 'employee', member_id: c[m.key], role_in_project: m.role }))

    const payload = {
      crm_card_id: c.id,
      chat_title: newChatTitle.value.trim() || undefined,
      members,
    }
    const { data } = await messengerApi.createChat(payload)
    if (data && data.chat) {
      chatData.value = data.chat
      chatMembers.value = data.members || []
    }
    $q.notify({ type: 'positive', message: 'Чат создан' })
    await loadChat()
  } catch (e) {
    const msg = e?.response?.data?.detail || 'Ошибка создания чата'
    $q.notify({ type: 'negative', message: msg })
  }
  chatCreating.value = false
}

async function doAddChatMember() {
  if (!chatData.value?.id || !addMemberEmployeeId.value) return
  addMemberLoading.value = true
  try {
    const { api: ax } = await import('src/boot/axios')
    await ax.post(`/api/v1/messenger/chats/${chatData.value.id}/add-member`, {
      employee_id: addMemberEmployeeId.value,
    })
    $q.notify({ type: 'positive', message: 'Участник добавлен' })
    showAddMemberDlg.value = false
    addMemberEmployeeId.value = null
    await loadChat()
  } catch (e) {
    const detail = e?.response?.data?.detail
    const msg = Array.isArray(detail) ? detail.map(d => d.msg || d).join('; ') : (detail || 'Ошибка добавления')
    $q.notify({ type: 'negative', message: msg })
  }
  addMemberLoading.value = false
}

async function _confirmDeleteChat() {
  if (!chatData.value?.id) return
  $q.dialog({ title: 'Удалить чат?', message: 'Telegram-группа будет удалена', cancel: true, persistent: false })
    .onOk(async () => {
      try {
        await messengerApi.deleteChat(chatData.value.id)
        chatData.value = null
        chatMembers.value = []
        $q.notify({ type: 'positive', message: 'Чат удалён' })
      } catch { $q.notify({ type: 'negative', message: 'Ошибка удаления' }) }
    })
}

async function doSendMessage() {
  if (!chatData.value?.id || !chatMessageText.value?.trim()) return
  chatActionLoading.value = true
  try {
    await messengerApi.sendMessage(chatData.value.id, { text: chatMessageText.value.trim() })
    $q.notify({ type: 'positive', message: 'Сообщение отправлено' })
    chatMessageText.value = ''
    showSendMessageDlg.value = false
  } catch { $q.notify({ type: 'negative', message: 'Ошибка отправки' }) }
  chatActionLoading.value = false
}

async function loadScriptsAndShow() {
  try {
    const { data } = await messengerApi.getScripts({ crm_card_id: card.value?.id })
    // Показываем только стартовый/финальный скрипты под тип проекта (инд/шабл)
    const pt = card.value?.project_type || ''
    chatScripts.value = (data || []).filter(s =>
      (s.script_type === 'project_start' || s.script_type === 'project_end') &&
      s.project_type === pt,
    )
  } catch { chatScripts.value = [] }
  showScriptsDlg.value = true
}

async function doTriggerScript(script) {
  if (!chatData.value?.id) return
  try {
    await messengerApi.triggerScript(script.id, chatData.value.id)
    $q.notify({ type: 'positive', message: `Скрипт «${script.name || script.code}» запущен` })
    showScriptsDlg.value = false
  } catch { $q.notify({ type: 'negative', message: 'Ошибка запуска скрипта' }) }
}

// === Блокировки (locks) — защита от одновременного редактирования ===
const currentLockId = ref(null)
const lockedByUser = ref(null)

async function acquireLock(cardId) {
  try {
    // Проверяем, не заблокирована ли уже
    const { data: existing } = await locksApi.check('crm_card', cardId)
    // is_own_lock = true → это наша блокировка, предупреждение не нужно
    if (existing && existing.is_locked && !existing.is_own_lock) {
      lockedByUser.value = existing.locked_by || 'другой пользователь'
      $q.notify({ type: 'warning', message: `Карточка редактируется: ${lockedByUser.value}`, timeout: 5000 })
      return
    }
    // Захватываем блокировку (entity_type+id — сервер вернёт created/renewed)
    await locksApi.lock('crm_card', cardId)
    currentLockId.value = cardId
  } catch { /* блокировки опциональны — не блокируем работу */ }
}

async function releaseLock() {
  if (!currentLockId.value) return
  try { await locksApi.unlock('crm_card', currentLockId.value) } catch {}
  currentLockId.value = null
}

onMounted(async () => {
  loadAvatars()
  try {
    const id = route.params.id
    if (route.query.tab) {
      activeTab.value = route.query.tab
      if (route.query.tab === 'chat') chatTabVisited.value = true
      if (route.query.tab === 'notes') notesTabVisited.value = true
    }
    await crmStore.loadCard(id)
    await loadAdditionalData(id)
    await acquireLock(id)
    // Блокируем внешний скролл если стартуем на вкладке чата
    if (['chat', 'notes'].includes(activeTab.value)) {
      _setChatScrollLock(true)
    }
  } catch (e) { console.error('Ошибка загрузки карточки:', e) }
})

onBeforeUnmount(() => {
  releaseLock()
  _setChatScrollLock(false) // Восстанавливаем скролл при уходе со страницы
})
</script>

<style scoped>
/* Отступ справа в прокручиваемом контейнере вкладок — чтобы не скрывался под FAB */
.tabs-sticky :deep(.q-tabs__content) {
  padding-right: 68px;
}

/* Прогресс-бар подэтапов — grid, auto-fit минимум 55px */
.stage-progress-bar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(55px, 1fr));
  gap: 3px;
  padding: 4px 16px 8px;
  width: 100%;
  box-sizing: border-box;
}
.stage-step {
  text-align: center;
  font-size: 9px;
  padding: 3px 4px;
  border-radius: 4px;
  background: #EEEEEE;
  color: #999;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.step-done {
  background: #9E9E9E;
  color: white;
}
.step-active {
  background: #4CAF50;
  color: white;
  font-weight: bold;
}

/* Ландшафт: вкладка Данные — ровно 2 колонки, равная высота блоков в строке */
@media (orientation: landscape) {
  .data-blocks-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 12px;
  }
  .data-blocks-grid > .is-card {
    margin-bottom: 0 !important;
  }
}
</style>
