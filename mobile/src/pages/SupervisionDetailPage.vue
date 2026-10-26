<template>
  <q-page padding>
    <div v-if="loading" class="q-pa-md">
      <q-skeleton type="rect" height="120px" class="q-mb-md" />
      <q-skeleton type="text" width="80%" />
      <q-skeleton type="text" width="50%" />
    </div>

    <template v-else-if="card">
      <!-- Шапка (как CrmCardPage) -->
      <q-card class="is-card q-mb-md" style="position: relative">
        <q-btn
          round
          flat
          dense
          icon="arrow_back"
          style="position: absolute; top: -8px; left: -8px; z-index: 10; width: 27px; height: 32px; min-height: 32px; min-width: 27px; max-width: 27px; max-height: 32px; padding: 0; overflow: hidden; background: var(--fc-bg); border: 1.5px solid var(--fc-border-light); box-shadow: 0 2px 8px var(--fc-shadow-md); color: var(--fc-text-medium)"
          @click="$router.back()"
        >
          <q-tooltip>Назад</q-tooltip>
        </q-btn>
        <q-card-section style="background: var(--fc-bg-info); border-radius: 8px 8px 0 0">
          <div class="row items-start justify-between q-mb-xs" style="gap: 8px">
            <!-- Левый столбец: номер договора, адрес, тип, площадь, город -->
            <div style="flex: 1; min-width: 0">
              <div class="text-subtitle1 text-weight-bold" style="color: var(--fc-text)">
                {{ card.contract_number }}
              </div>
              <div class="text-body2 q-mt-xs" style="color: var(--fc-text)">
                <a v-if="card.address" :href="'https://yandex.ru/maps/?text=' + encodeURIComponent(card.address)" target="_blank" style="color: var(--fc-text); text-decoration: none"><q-icon name="location_on" size="14px" color="red" class="q-mr-xs" />{{ card.address }}</a>
              </div>
              <div class="text-caption q-mt-xs" style="color: var(--fc-text-light)">
                <span v-if="card.project_type">{{ card.project_type }}</span>
                <span v-if="card.project_subtype" style="color: var(--fc-border-card); margin: 0 4px">|</span><span v-if="card.project_subtype">{{ card.project_subtype }}</span>
                <span v-if="card.area" style="color: var(--fc-border-card); margin: 0 4px">|</span><span v-if="card.area">{{ card.area }} м²</span>
                <span v-if="card.city" style="color: var(--fc-border-card); margin: 0 4px">|</span><span v-if="card.city"><q-icon name="location_on" size="12px" /> {{ card.city }}</span>
              </div>
            </div>
            <!-- Правый столбец: статус стадии (с переносом) + тип агента -->
            <div class="column items-end q-gutter-xs" style="flex-shrink: 0; max-width: 44%">
              <q-badge
                :color="card.is_paused ? 'warning' : 'positive'"
                :label="card.is_paused ? 'Приостановлено' : card.column_name"
                style="text-align: center; padding: 5px 8px; font-size: 11px; white-space: normal; word-break: break-word; max-width: 100%"
                multi-line
              />
              <q-badge
                v-if="card.agent_type"
                text-color="white"
                :style="{ background: agentColor, textAlign: 'center', padding: '5px 8px', fontSize: '11px', whiteSpace: 'normal', wordBreak: 'break-word', maxWidth: '100%' }"
                :label="card.agent_type"
                multi-line
              />
            </div>
          </div>
          <div class="row q-gutter-md text-caption q-mt-xs" style="color: var(--fc-text-light)">
            <span v-if="card.start_date"><q-icon name="play_arrow" size="14px" /> Начало: {{ formatDate(card.start_date) }}</span>
            <span v-if="card.deadline"><q-icon name="flag" size="14px" :style="{ color: dlColor(card.deadline) }" /> Дедлайн: {{ formatDate(card.deadline) }}</span>
          </div>
          <div v-if="card.tags" class="row q-gutter-xs q-mt-xs">
            <span
              v-for="(tag, tidx) in parseSvTags(card.tags)"
              :key="tidx"
              :style="{ display: 'inline-block', background: tag.color, color: 'white', borderRadius: '4px', padding: '2px 10px', fontSize: '11px', fontWeight: '600' }"
            >{{ tag.text }}</span>
          </div>
          <!-- Статус ДАН убран — функционал завершения через кнопку "Завершить стадию" -->
        </q-card-section>
        <!-- Таймлайн стадий надзора -->
        <q-card-section class="q-pt-none q-pb-sm">
          <div class="row items-center q-mb-xs">
            <span class="text-caption" style="color: var(--fc-text-light)">
              Стадия {{ currentStageIndex + 1 }}/{{ SUPERVISION_STAGES.length }}
            </span>
            <q-space />
            <span class="text-caption text-weight-medium" style="color: var(--fc-text-medium); max-width: 180px; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
              {{ card?.column_name }}
            </span>
          </div>
          <div
            class="row"
            style="gap: 2px; cursor: pointer"
            @click="showStagesDialog = true"
          >
            <div
              v-for="(stage, idx) in SUPERVISION_STAGES"
              :key="stage"
              :style="{
                flex: '1',
                height: '8px',
                borderRadius: '4px',
                minWidth: '6px',
                background: idx < currentStageIndex ? '#4CAF50' : idx === currentStageIndex ? '#1976D2' : 'var(--fc-border-light)',
              }"
            />
          </div>
          <div class="text-caption q-mt-xs" style="color: var(--fc-text-disabled)">
            Нажмите для просмотра стадий
          </div>
        </q-card-section>

        <!-- Прогресс закупок -->
        <q-card-section v-if="timeline.length > 0" class="q-pt-none q-pb-sm">
          <div class="row items-center q-mb-xs">
            <span class="text-caption" style="color: var(--fc-text-light)">Закупки: {{ svStageProgress.done }}/{{ svStageProgress.total }} завершено</span>
            <q-space />
            <span class="text-caption text-weight-bold" style="color: var(--fc-text)">{{ svStageProgress.percent }}%</span>
          </div>
          <q-linear-progress
            :value="svStageProgress.percent / 100"
            color="positive"
            track-color="grey-3"
            size="8px"
            style="border-radius: 4px"
          />
        </q-card-section>
        <!-- Прогресс выездов текущего месяца -->
        <q-card-section v-if="visitProgress" class="q-pt-none q-pb-sm">
          <div class="row items-center q-mb-xs">
            <span class="text-caption" style="color: var(--fc-text-light)">
              Выезды (месяц): {{ visitProgress.regular }}/{{ visitProgress.minVisits }}
              <span v-if="visitProgress.additional > 0" style="color: #e65100"> + {{ visitProgress.additional }} доп.</span>
            </span>
            <q-space />
            <span
              class="text-caption text-weight-bold"
              :style="{ color: visitProgress.isOver ? '#e65100' : '#2e7d32' }"
            >
              {{ visitProgress.isOver ? '+' + visitProgress.overflow + ' сверх нормы' : Math.round(visitProgress.percent * 100) + '%' }}
            </span>
          </div>
          <q-linear-progress
            :value="visitProgress.percent"
            :color="visitProgress.isOver ? 'orange' : 'positive'"
            track-color="grey-3"
            size="8px"
            style="border-radius: 4px; cursor: pointer"
            @click="showVisitStatsDialog = true"
          />
          <div class="text-caption q-mt-xs" style="color: var(--fc-text-disabled)">
            Нажмите для статистики по месяцам
          </div>
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
        style="color: var(--fc-text-secondary)"
        align="left"
        :breakpoint="0"
      >
        <q-tab name="executors" label="Исполнители" />
        <q-tab name="timeline" label="Закупки" />
        <q-tab name="data" label="Выезды" />
        <q-tab name="history" label="История" />
        <q-tab name="payments" label="Оплаты" />
        <q-tab name="notes" label="Заметки" />
        <q-tab name="sv-chat" label="Чат надзора" />
      </q-tabs>

      <q-tab-panels v-model="activeTab" animated class="bg-transparent">
        <!-- ====== ВКЛАДКА 1: Исполнители ====== -->
        <q-tab-panel name="executors" class="q-pa-none">
          <!-- Информация о проекте -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: var(--fc-text)">
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

          <!-- Вводные данные проекта -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-xs">
              <div class="row items-center justify-between">
                <div class="text-subtitle2 text-weight-bold" style="color: var(--fc-text)">
                  Вводные данные проекта
                </div>
                <div v-if="hasCrmCard" class="text-caption" style="color: var(--fc-text-muted)">
                  из основного CRM
                </div>
              </div>
            </q-card-section>

            <!-- Замер -->
            <q-separator spaced="xs" />
            <q-card-section class="q-py-xs">
              <div class="row items-center justify-between q-mb-xs">
                <div class="text-weight-medium" style="font-size: 13px; color: var(--fc-text)">
                  Замер
                </div>
                <div v-if="!hasCrmCard && !isArchived" class="row q-gutter-xs">
                  <q-btn
                    outline
                    dense
                    size="xs"
                    icon="upload"
                    label="Загрузить"
                    no-caps
                    color="grey-7"
                    style="border-radius: 4px; padding: 2px 8px"
                    @click="showIntroMeasurementDlg = true"
                  />
                  <q-btn
                    v-if="introContractData?.measurement_image_link"
                    outline
                    dense
                    size="xs"
                    icon="delete_outline"
                    no-caps
                    color="negative"
                    style="border-radius: 4px; padding: 2px 6px"
                    @click="deleteIntroMeasurement"
                  >
                    <q-tooltip>Удалить замер</q-tooltip>
                  </q-btn>
                </div>
              </div>
              <div v-if="introContractData?.measurement_image_link" class="q-mb-xs">
                <a :href="introContractData.measurement_image_link" target="_blank" style="color: var(--fc-link); font-size: 12px">Открыть папку с замером</a>
              </div>
              <div v-else style="color: var(--fc-text-muted); font-size: 12px" class="q-mb-xs">
                Не загружен
              </div>
              <div v-if="introContractData?.measurement_date" class="text-caption" style="color: var(--fc-text-light)">
                Дата: {{ formatDate(introContractData.measurement_date) }}
              </div>
            </q-card-section>

            <!-- Фотофиксация -->
            <q-separator spaced="xs" />
            <q-card-section class="q-py-xs">
              <div class="row items-center justify-between q-mb-xs">
                <div class="text-weight-medium" style="font-size: 13px; color: var(--fc-text)">
                  Фотофиксация
                </div>
                <div v-if="!hasCrmCard && !isArchived" class="row q-gutter-xs">
                  <q-btn
                    v-if="!introContractData?.photo_folder_public_link"
                    outline
                    dense
                    size="xs"
                    icon="upload"
                    label="Загрузить"
                    no-caps
                    color="grey-7"
                    style="border-radius: 4px; padding: 2px 8px"
                    @click="uploadIntroFile('photo_documentation', 'Фотофиксация')"
                  />
                  <q-btn
                    v-if="introContractData?.photo_folder_public_link"
                    outline
                    dense
                    size="xs"
                    icon="delete_outline"
                    no-caps
                    color="negative"
                    style="border-radius: 4px; padding: 2px 6px"
                    @click="deleteIntroPhotoFolder"
                  >
                    <q-tooltip>Удалить папку</q-tooltip>
                  </q-btn>
                </div>
              </div>
              <div v-if="introContractData?.photo_folder_public_link || introContractData?.photo_documentation_yandex_path">
                <a :href="introContractData.photo_folder_public_link || introContractData.photo_documentation_yandex_path" target="_blank" style="color: var(--fc-link); font-size: 12px">Открыть папку с фотофиксацией</a>
              </div>
              <div v-else style="color: var(--fc-text-muted); font-size: 12px">
                Не загружена
              </div>
            </q-card-section>

            <!-- Стадии проекта -->
            <template v-for="stage in introStageCodes" :key="stage.code">
              <q-separator spaced="xs" />
              <q-card-section class="q-py-xs">
                <div class="row items-center justify-between q-mb-xs">
                  <div class="text-weight-medium" style="font-size: 13px; color: var(--fc-text)">
                    {{ stage.label }}
                  </div>
                  <div v-if="!hasCrmCard && !isArchived" class="row q-gutter-xs">
                    <q-btn
                      outline
                      dense
                      size="xs"
                      icon="upload"
                      label="Загрузить"
                      no-caps
                      color="grey-7"
                      style="border-radius: 4px; padding: 2px 8px"
                      @click="uploadIntroFile(stage.code, stage.label)"
                    />
                  </div>
                </div>
                <div v-if="introFilesMap[stage.code]?.length">
                  <q-list dense>
                    <q-item v-for="f in introFilesMap[stage.code]" :key="f.id">
                      <q-item-section avatar style="min-width: 28px">
                        <q-icon :name="introFileIcon(f)" color="blue-7" size="16px" />
                      </q-item-section>
                      <q-item-section style="min-width: 0">
                        <q-item-label style="font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
                          <a href="#" style="color: var(--fc-link); text-decoration: none" @click.prevent="openIntroFile(f)">{{ f.file_name }}</a>
                        </q-item-label>
                      </q-item-section>
                      <q-item-section side style="flex-shrink: 0">
                        <div class="row q-gutter-xs no-wrap">
                          <q-btn
                            outline
                            dense
                            size="xs"
                            icon="open_in_new"
                            no-caps
                            color="grey-7"
                            style="padding: 2px 6px; border-radius: 4px"
                            @click.stop="openIntroFile(f)"
                          />
                          <q-btn
                            v-if="!hasCrmCard && !isArchived"
                            outline
                            dense
                            size="xs"
                            icon="delete_outline"
                            no-caps
                            color="negative"
                            style="padding: 2px 6px; border-radius: 4px"
                            @click.stop="deleteIntroFile(f)"
                          />
                        </div>
                      </q-item-section>
                    </q-item>
                  </q-list>
                </div>
                <div v-else class="text-caption" style="color: var(--fc-text-disabled)">
                  Нет файлов
                </div>
              </q-card-section>
            </template>
          </q-card>

          <!-- Команда -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: var(--fc-text)">
                Команда
              </div>
            </q-card-section>
            <q-list dense separator>
              <q-item v-if="card.dan_name || can('supervision.assign_executor')">
                <q-item-section avatar>
                  <q-avatar size="32px" color="orange-2" text-color="orange-8" style="overflow:hidden">
                    <img v-if="card.dan_name && getAvatarByName(card.dan_name)" :src="getAvatarByName(card.dan_name)" style="width:100%;height:100%;object-fit:cover;border-radius:50%">
                    <template v-else>
                      {{ card.dan_name ? card.dan_name[0] : '?' }}
                    </template>
                  </q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ card.dan_name || 'Не назначен' }}</q-item-label>
                  <q-item-label caption>
                    ДАН
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <div class="row q-gutter-xs items-center">
                    <q-icon v-if="card.dan_completed" name="check_circle" color="positive" />
                    <q-btn
                      v-if="can('supervision.assign_executor') && card.dan_id && !isArchived"
                      flat
                      round
                      dense
                      size="xs"
                      icon="payments"
                      :color="monthlyAssignments.some(a => a.role === 'ДАН') ? 'positive' : 'grey-7'"
                      @click="openMonthlyRateDialog('ДАН', card.dan_id, card.dan_name)"
                    >
                      <q-tooltip>Ежемесячная ставка</q-tooltip>
                    </q-btn>
                    <q-btn
                      v-if="can('supervision.assign_executor') && !isArchived"
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
              <q-item v-if="card.senior_manager_name || (can('supervision.assign_executor') && !isArchived)">
                <q-item-section avatar>
                  <q-avatar size="32px" color="blue-2" text-color="blue-8" style="overflow:hidden">
                    <img v-if="card.senior_manager_name && getAvatarByName(card.senior_manager_name)" :src="getAvatarByName(card.senior_manager_name)" style="width:100%;height:100%;object-fit:cover;border-radius:50%">
                    <template v-else>
                      {{ card.senior_manager_name ? card.senior_manager_name[0] : '?' }}
                    </template>
                  </q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ card.senior_manager_name || 'Не назначен' }}</q-item-label>
                  <q-item-label caption>
                    Ст. менеджер
                  </q-item-label>
                </q-item-section>
                <q-item-section v-if="can('supervision.assign_executor') && !isArchived" side>
                  <div class="row q-gutter-xs items-center">
                    <q-btn
                      v-if="card.senior_manager_id"
                      flat
                      round
                      dense
                      size="xs"
                      icon="payments"
                      :color="monthlyAssignments.some(a => a.role === 'Старший менеджер проектов') ? 'positive' : 'grey-7'"
                      @click="openMonthlyRateDialog('Старший менеджер проектов', card.senior_manager_id, card.senior_manager_name)"
                    >
                      <q-tooltip>Ежемесячная ставка</q-tooltip>
                    </q-btn>
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
                  </div>
                </q-item-section>
              </q-item>
              <q-item v-if="card.studio_director_name">
                <q-item-section avatar>
                  <q-avatar size="32px" color="purple-2" text-color="purple-8" style="overflow:hidden">
                    <img v-if="getAvatarByName(card.studio_director_name)" :src="getAvatarByName(card.studio_director_name)" style="width:100%;height:100%;object-fit:cover;border-radius:50%">
                    <template v-else>
                      {{ card.studio_director_name[0] }}
                    </template>
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
              <div class="text-subtitle2 text-weight-bold" style="color: var(--fc-text)">
                Действия
              </div>
            </q-card-section>
            <q-card-section>
              <q-btn
                v-if="can('supervision.pause_resume') && !card.is_paused && !isArchived"
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
                v-else-if="can('supervision.pause_resume') && card.is_paused && !isArchived"
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
                v-if="can('supervision.complete_stage') && !isArchived"
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
                v-if="can('supervision.move') && !isArchived"
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
                v-if="isDan && !card.dan_completed && !isArchived"
                unelevated
                dense
                no-caps
                icon="check"
                label="Сдать работу"
                class="full-width q-mb-sm"
                style="background: #58D68D; color: white; font-size: 12px; font-weight: bold; height: 36px; border-radius: 4px"
                @click="submitDanWork"
              />
              <!-- В архив: карточка в "Выполненный проект", но договор ещё активен -->
              <q-btn
                v-if="isArchived && card.contract_status !== 'СДАН' && card.contract_status !== 'РАСТОРГНУТ'"
                unelevated
                dense
                no-caps
                icon="archive"
                label="В архив"
                class="full-width q-mb-sm"
                style="background: #27AE60; color: white; font-size: 12px; font-weight: bold; height: 36px; border-radius: 4px"
                :loading="archiveLoading"
                @click="archiveSupervisionWithValidation"
              />
              <!-- Вернуть в активные: карточка в архиве (СДАН/РАСТОРГНУТ) -->
              <q-btn
                v-if="isArchived && (card.contract_status === 'СДАН' || card.contract_status === 'РАСТОРГНУТ') && canRestoreSupervision"
                unelevated
                dense
                no-caps
                icon="replay"
                label="Вернуть в активные"
                class="full-width q-mb-sm"
                style="background: #5DADE2; color: white; font-size: 12px; font-weight: bold; height: 36px; border-radius: 4px"
                :loading="archiveLoading"
                @click="restoreSupervision"
              />
              <div
                v-if="isArchived && (card.contract_status === 'СДАН' || card.contract_status === 'РАСТОРГНУТ')"
                class="text-center"
                style="color: var(--fc-text-muted); font-size: 12px; padding: 4px 0"
              >
                Карточка в архиве
              </div>
            </q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 2: Сроки (стадии закупок + бюджет) ====== -->
        <q-tab-panel name="timeline" class="q-pa-none">
          <!-- Экспорт + счётчик выездов -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="row items-center justify-between">
                <div class="text-subtitle2 text-weight-bold" style="color: var(--fc-text)">
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
                :clickable="!isArchived"
                :style="purchaseRowStyle(entry.status)"
                @click="!isArchived && editTimelineEntry(entry)"
              >
                <q-item-section avatar>
                  <q-btn
                    flat
                    dense
                    round
                    size="sm"
                    :icon="entry.status === 'Закуплено' || entry.status === 'Доставлено' ? 'check_circle' : 'radio_button_unchecked'"
                    :color="entry.status === 'Закуплено' || entry.status === 'Доставлено' ? 'positive' : 'grey-4'"
                    :disable="isArchived"
                    @click.stop="!isArchived && toggleStageComplete(entry)"
                  >
                    <q-tooltip>{{ entry.status === 'Закуплено' || entry.status === 'Доставлено' ? 'Снять отметку' : 'Отметить закупленным' }}</q-tooltip>
                  </q-btn>
                </q-item-section>
                <q-item-section>
                  <q-item-label class="text-weight-medium">
                    {{ entry.stage_name.replace(/^Стадия \d+: /, '') }}
                  </q-item-label>
                  <template v-if="hasPurchaseData(entry)">
                    <q-item-label caption>
                      План: {{ entry.plan_date ? formatDate(entry.plan_date) : '—' }} | Факт: {{ entry.actual_date ? formatDate(entry.actual_date) : '—' }}
                    </q-item-label>
                    <q-item-label caption style="color: var(--fc-text-light)">
                      {{ entry.supplier || '—' }}
                    </q-item-label>
                    <q-item-label caption style="color: var(--fc-text-light)">
                      Факт. {{ formatMoney(entry.budget_actual || 0) }} / План {{ entry.budget_planned > 0 ? formatMoney(entry.budget_planned) : '—' }}
                    </q-item-label>
                    <q-item-label caption style="color: var(--fc-text-medium)">
                      Исполнитель: {{ entry.executor || '—' }}
                    </q-item-label>
                    <q-item-label caption :style="entry.commission > 0 ? 'color: #2e7d32; font-weight: 500' : 'color: var(--fc-text-muted)'">
                      Комиссия: {{ entry.commission > 0 ? formatMoney(entry.commission) : '—' }}
                    </q-item-label>
                  </template>
                </q-item-section>
                <q-item-section side>
                  <div class="column q-gutter-xs" style="align-items: stretch; min-width: 76px">
                    <q-badge :color="stageColor(entry.status)" :label="entry.status" dense />
                    <q-btn
                      v-if="stageFiles(entry.stage_code).length > 0"
                      unelevated
                      dense
                      no-caps
                      size="xs"
                      icon="folder_open"
                      :label="`${stageFiles(entry.stage_code).length} файл(ов)`"
                      color="blue-1"
                      text-color="blue-8"
                      style="font-size: 10px; border-radius: 4px; padding: 0 5px; width: 100%"
                      @click.stop="openStageFolder(entry)"
                    />
                    <q-btn
                      v-if="can('supervision.files_upload') && !isArchived"
                      unelevated
                      dense
                      no-caps
                      size="xs"
                      icon="attach_file"
                      label="Файл"
                      color="blue-1"
                      text-color="blue-8"
                      style="font-size: 10px; border-radius: 4px; padding: 0 5px; width: 100%"
                      @click.stop="uploadStageFile(entry.stage_code)"
                    />
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
                :clickable="!isArchived"
                @click="!isArchived && initAndEditStage(s)"
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
                      v-if="can('supervision.files_upload') && !isArchived"
                      unelevated
                      dense
                      no-caps
                      size="xs"
                      icon="attach_file"
                      label="Файл"
                      color="blue-1"
                      text-color="blue-8"
                      style="font-size: 10px; border-radius: 4px; padding: 0 5px"
                      @click.stop="uploadStageFile(s.code)"
                    />
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Бюджет -->
          <q-card v-if="summary && summary.total_budget_planned > 0" class="is-card q-mb-md">
            <q-card-section>
              <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: var(--fc-text)">
                Бюджет (итого)
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
                    Остаток средств
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

          <!-- Строительные работы -->
          <q-card class="is-card q-mb-md">
            <q-card-section>
              <div class="row items-center justify-between q-mb-sm">
                <div class="text-subtitle2 text-weight-bold" style="color: var(--fc-text)">
                  Строительные работы
                </div>
                <q-btn
                  v-if="!isArchived"
                  flat
                  dense
                  round
                  icon="edit"
                  size="sm"
                  color="grey-6"
                  @click="openConstructionDialog"
                />
              </div>
              <template v-if="budgetExtra.construction_planned || budgetExtra.construction_contractor || budgetExtra.construction_payments?.length">
                <div class="row q-col-gutter-sm q-mb-xs">
                  <div class="col-6" style="text-align: center">
                    <div class="text-caption text-grey-7">
                      Стоимость план
                    </div>
                    <div class="text-weight-bold">
                      {{ formatMoney(budgetExtra.construction_planned || 0) }}
                    </div>
                  </div>
                  <div class="col-6" style="text-align: center">
                    <div class="text-caption text-grey-7">
                      Фактические оплаты
                    </div>
                    <div class="text-weight-bold">
                      {{ formatMoney(constructionActualTotal) }}
                    </div>
                  </div>
                </div>
                <div v-if="budgetExtra.construction_contractor" class="text-caption q-mb-xs">
                  Подрядчик: <span style="color: var(--fc-text); font-weight: 500">{{ budgetExtra.construction_contractor }}</span>
                </div>
                <div v-if="budgetExtra.construction_payments?.length" class="q-mt-xs">
                  <div class="text-caption text-grey-7 q-mb-xs">
                    Оплаты:
                  </div>
                  <div v-for="(p, idx) in budgetExtra.construction_payments" :key="idx" class="text-caption q-mb-xs" style="color: var(--fc-text-medium)">
                    {{ fmtDMY(p.date) }} — {{ formatMoney(p.amount) }}<span v-if="p.commission > 0" style="color: #2e7d32"> (ком. {{ formatMoney(p.commission) }})</span>
                  </div>
                </div>
              </template>
              <div v-else class="text-caption text-grey-5">
                Нет данных.
                <span v-if="!isArchived" class="text-primary cursor-pointer" @click="openConstructionDialog">Добавить</span>
              </div>
            </q-card-section>
          </q-card>

          <!-- Черновые материалы -->
          <q-card class="is-card q-mb-md">
            <q-card-section>
              <div class="row items-center justify-between q-mb-sm">
                <div class="text-subtitle2 text-weight-bold" style="color: var(--fc-text)">
                  Черновые материалы
                </div>
                <q-btn
                  v-if="!isArchived"
                  flat
                  dense
                  round
                  icon="edit"
                  size="sm"
                  color="grey-6"
                  @click="openMaterialsDialog"
                />
              </div>
              <template v-if="budgetExtra.materials_planned || budgetExtra.materials_supplier || budgetExtra.materials_payments?.length">
                <div class="row q-col-gutter-sm q-mb-xs">
                  <div class="col-6" style="text-align: center">
                    <div class="text-caption text-grey-7">
                      Стоимость план
                    </div>
                    <div class="text-weight-bold">
                      {{ formatMoney(budgetExtra.materials_planned || 0) }}
                    </div>
                  </div>
                  <div class="col-6" style="text-align: center">
                    <div class="text-caption text-grey-7">
                      Фактические заказы
                    </div>
                    <div class="text-weight-bold">
                      {{ formatMoney(materialsActualTotal) }}
                    </div>
                  </div>
                </div>
                <div v-if="budgetExtra.materials_supplier" class="text-caption q-mb-xs">
                  Поставщик: <span style="color: var(--fc-text); font-weight: 500">{{ budgetExtra.materials_supplier }}</span>
                </div>
                <div v-if="budgetExtra.materials_payments?.length" class="q-mt-xs">
                  <div class="text-caption text-grey-7 q-mb-xs">
                    Заказы:
                  </div>
                  <div v-for="(p, idx) in budgetExtra.materials_payments" :key="idx" class="text-caption q-mb-xs" style="color: var(--fc-text-medium)">
                    {{ fmtDMY(p.date) }} — {{ formatMoney(p.amount) }}<span v-if="p.supplier" style="color: var(--fc-text-light)"> ({{ p.supplier }})</span><span v-if="p.commission > 0" style="color: #2e7d32"> ком. {{ formatMoney(p.commission) }}</span>
                  </div>
                </div>
              </template>
              <div v-else class="text-caption text-grey-5">
                Нет данных.
                <span v-if="!isArchived" class="text-primary cursor-pointer" @click="openMaterialsDialog">Добавить</span>
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
                <div class="text-subtitle2 text-weight-bold" style="color: var(--fc-text)">
                  Выезды
                </div>
                <q-btn
                  v-if="!isArchived"
                  unelevated
                  dense
                  no-caps
                  icon="add"
                  label="Новый выезд"
                  style="background: var(--fc-accent); color: var(--fc-text); font-size: 11px; height: 32px; border-radius: 4px"
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
                :style="Object.assign({ borderRadius: '6px' }, visit.actual_date ? { background: 'var(--fc-state-success-bg)', borderColor: '#A5D6A7' } : {})"
              >
                <q-card-section class="q-pa-sm">
                  <!-- Строка: бейджи слева, даты справа в столбик -->
                  <div class="row items-start justify-between q-mb-xs">
                    <div class="column q-gutter-xs" style="flex: 1">
                      <div class="row items-center q-gutter-xs">
                        <q-badge :color="visit.visit_type === 'К поставщику' ? 'blue' : 'green'" :label="visit.visit_type || 'На объект'" dense />
                        <q-badge
                          v-if="visit.is_additional"
                          color="orange"
                          label="доп."
                          dense
                        />
                      </div>
                    </div>
                    <div class="column items-end" style="flex-shrink: 0; text-align: right">
                      <span class="text-caption text-weight-bold" style="color: var(--fc-text)">План: {{ formatDate(visit.visit_date) }}</span>
                      <span v-if="visit.actual_date" class="text-caption" style="color: #27AE60">Факт: {{ formatDate(visit.actual_date) }}</span>
                    </div>
                  </div>

                  <div v-if="visit.stage_name" class="text-caption" style="color: var(--fc-text-light)">
                    {{ visit.stage_name }}
                  </div>
                  <div v-if="visit.notes" class="text-caption q-mt-xs" style="color: var(--fc-text-secondary)">
                    {{ visit.notes }}
                  </div>

                  <!-- Файлы отчёта -->
                  <div v-if="visit.report_files && visit.report_files.length > 0" class="q-mt-xs">
                    <div class="text-caption text-weight-bold" style="color: var(--fc-text-medium)">
                      Отчёт:
                    </div>
                    <div v-for="f in visit.report_files" :key="f.id" class="row items-center q-gutter-xs">
                      <q-icon name="description" size="14px" color="orange" />
                      <a :href="f.public_link || '#'" target="_blank" style="color: var(--fc-link); text-decoration: none; font-size: 11px">{{ f.file_name }}</a>
                      <q-btn
                        v-if="!isArchived"
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
                    <div class="text-caption text-weight-bold" style="color: var(--fc-text-medium)">
                      Фото:
                    </div>
                    <div v-for="f in visit.photo_files" :key="f.id" class="row items-center q-gutter-xs">
                      <q-icon name="image" size="14px" color="blue" />
                      <a :href="f.public_link || '#'" target="_blank" style="color: var(--fc-link); text-decoration: none; font-size: 11px">{{ f.file_name }}</a>
                      <q-btn
                        v-if="!isArchived"
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

                  <!-- ЯД папка -->
                  <div v-if="visit.actual_date || visit.visit_date" class="row q-mt-xs">
                    <q-btn
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
                  </div>

                  <!-- Строка 1: кнопка Факт. выезд (если не проставлена) -->
                  <div v-if="!isArchived && !visit.actual_date" class="row q-mt-xs">
                    <q-btn
                      outline
                      dense
                      size="xs"
                      icon="event_available"
                      label="Факт. выезд"
                      no-caps
                      color="positive"
                      class="full-width"
                      style="font-size: 10px; padding: 2px 8px; border-radius: 4px"
                      @click="setActualDate(visit)"
                    />
                  </div>

                  <!-- Строка 2: Отчёт + Фото (растягиваются) + edit + delete в одну строку -->
                  <div v-if="!isArchived" class="row q-gutter-xs q-mt-xs items-center">
                    <q-btn
                      outline
                      dense
                      size="xs"
                      icon="description"
                      label="Отчёт"
                      no-caps
                      color="orange"
                      class="col"
                      style="font-size: 10px; padding: 2px 4px; border-radius: 4px"
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
                      class="col"
                      style="font-size: 10px; padding: 2px 4px; border-radius: 4px"
                      @click="uploadVisitPhoto(visit)"
                    />
                    <q-btn
                      outline
                      dense
                      size="xs"
                      icon="edit"
                      no-caps
                      color="grey-7"
                      style="font-size: 10px; padding: 2px 6px; border-radius: 4px; flex-shrink: 0"
                      @click="editVisit(visit)"
                    />
                    <q-btn
                      outline
                      dense
                      size="xs"
                      icon="delete"
                      no-caps
                      color="negative"
                      style="font-size: 10px; padding: 2px 6px; border-radius: 4px; flex-shrink: 0"
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
                <div class="text-subtitle2 text-weight-bold" style="color: var(--fc-text)">
                  Общие отчёты
                </div>
                <div class="row q-gutter-xs">
                  <q-btn
                    v-if="can('supervision.files_upload') && !isArchived"
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
                    v-if="can('supervision.files_upload') && !isArchived"
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
                    <a :href="f.public_link || '#'" target="_blank" style="color: var(--fc-link); text-decoration: none">{{ f.file_name }}</a>
                  </q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="q-py-sm text-center" style="color: var(--fc-text-disabled); font-size: 11px">
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
                <div class="text-subtitle2 text-weight-bold" style="color: var(--fc-text)">
                  История проекта
                </div>
                <q-btn
                  v-if="!isArchived"
                  unelevated
                  dense
                  no-caps
                  icon="add"
                  label="Добавить запись"
                  style="background: var(--fc-accent); color: var(--fc-text); font-size: 11px; height: 32px; border-radius: 4px"
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
                  <q-item-label style="font-size: 12px; color: var(--fc-text)">
                    {{ cleanNoteText(h) }}
                  </q-item-label>
                  <q-item-label caption style="color: var(--fc-text-light)">
                    <span v-if="h.entry_type" style="font-weight: bold">{{ historyLabel(h.entry_type) }}</span>
                    <span v-if="h.created_by_name"> · {{ h.created_by_name }}</span>
                    <span> · {{ formatDate(h.created_at) }}</span>
                  </q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="text-center" style="color: var(--fc-text-muted); font-size: 12px">
              Нет записей
            </q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 5: Оплаты надзора ====== -->
        <q-tab-panel name="payments" class="q-pa-none">
          <!-- Блок: Оплата надзора клиентом (ежемесячная) -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-xs">
              <div class="row items-center">
                <div class="text-subtitle2 text-weight-bold col" style="color: var(--fc-text)">
                  Оплата надзора клиентом
                </div>
                <q-btn
                  flat
                  round
                  dense
                  size="sm"
                  :icon="clientPaymentSettings.notification_enabled ? 'notifications' : 'notifications_off'"
                  :color="clientPaymentSettings.notification_enabled ? 'primary' : 'grey-5'"
                  @click="toggleClientPaymentNotif"
                >
                  <q-tooltip>{{ clientPaymentSettings.notification_enabled ? 'Уведомления включены' : 'Уведомления отключены' }}</q-tooltip>
                </q-btn>
              </div>
              <div v-if="clientPaymentSettings.notification_enabled" class="text-caption" style="color: var(--fc-text-light)">
                Напоминание {{ clientPaymentSettings.notification_day }}-го числа каждого месяца
              </div>
            </q-card-section>

            <q-list v-if="clientPayments.length > 0" dense separator>
              <q-item v-for="cp in clientPayments" :key="cp.id" :style="cp.payment_date ? { background: 'var(--fc-state-success-bg)' } : {}">
                <q-item-section>
                  <q-item-label class="text-weight-medium" style="font-size: 13px">
                    {{ formatReportMonth(cp.payment_month) }}
                  </q-item-label>
                  <q-item-label caption :style="{ color: cp.payment_date ? '#27AE60' : 'var(--fc-text-light)' }">
                    {{ cp.payment_date ? `Оплачено ${fmtDMY(cp.payment_date)}` : 'Не оплачено' }}
                  </q-item-label>
                  <div v-if="!isArchived" class="row items-center q-gutter-xs q-mt-xs">
                    <q-btn
                      flat
                      round
                      dense
                      size="xs"
                      icon="delete_outline"
                      color="negative"
                      @click.stop="deleteClientPayment(cp)"
                    />
                  </div>
                </q-item-section>
                <q-item-section side>
                  <div class="text-weight-bold" :style="{ color: cp.payment_date ? '#27AE60' : 'var(--fc-text)' }">
                    {{ formatMoney(cp.amount) }}
                  </div>
                  <div class="column q-gutter-xs items-stretch q-mt-xs">
                    <q-btn
                      v-if="!cp.payment_date && !isArchived"
                      outline
                      dense
                      size="sm"
                      icon="check_circle"
                      label="Оплатить"
                      color="positive"
                      no-caps
                      style="border-radius: 4px; min-width: 100px; height: 28px"
                      @click="markClientPaymentPaid(cp)"
                    />
                    <q-badge v-else-if="cp.payment_date" color="positive" style="padding: 4px 10px; font-size: 11px; border-radius: 4px; min-width: 100px; justify-content: center; height: 28px; display: flex; align-items: center">
                      Оплачено
                      <q-btn
                        v-if="!isArchived"
                        flat
                        round
                        dense
                        size="xs"
                        icon="close"
                        color="white"
                        class="q-ml-xs"
                        style="margin: -4px -4px -4px 0"
                        @click.stop="cancelClientPaymentPaid(cp)"
                      />
                    </q-badge>
                    <q-btn
                      v-if="!isArchived"
                      outline
                      dense
                      size="sm"
                      icon="upload_file"
                      label="Чек"
                      no-caps
                      :color="cp.receipt_path ? 'positive' : 'grey-7'"
                      style="border-radius: 4px; min-width: 100px; height: 28px"
                      @click="triggerClientPayReceiptUpload(cp.id)"
                    >
                      <q-tooltip v-if="cp.receipt_path">
                        Чек загружен
                      </q-tooltip>
                    </q-btn>
                  </div>
                </q-item-section>
              </q-item>
            </q-list>

            <q-card-section v-if="clientPayments.length === 0" class="text-center" style="color: var(--fc-text-muted); font-size: 12px">
              Нет платежей клиента
            </q-card-section>

            <q-card-section v-if="!isArchived" class="q-pt-xs q-pb-sm">
              <q-btn
                outline
                dense
                no-caps
                icon="add"
                label="Добавить платёж клиента"
                color="primary"
                size="sm"
                class="full-width"
                @click="showClientPayDialog = true"
              />
            </q-card-section>
          </q-card>
          <!-- /Блок оплата надзора клиентом -->

          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: var(--fc-text)">
                Оплаты надзора
              </div>
            </q-card-section>
            <q-list v-if="filteredSvPayments.length > 0" dense separator>
              <q-item v-for="p in filteredSvPayments" :key="p.id" :style="p.is_paid ? { background: 'var(--fc-state-success-bg)' } : {}">
                <q-item-section>
                  <q-item-label style="font-size: 12px">
                    {{ p.employee_name || 'Не указан' }}
                  </q-item-label>
                  <q-item-label caption>
                    {{ p.role || '' }} {{ p.stage_name ? `· ${p.stage_name}` : '' }}
                  </q-item-label>
                  <q-item-label v-if="p.report_month" caption style="color: #5DADE2">
                    {{ formatReportMonth(p.report_month) }}
                  </q-item-label>
                  <div v-if="!isArchived" class="row items-center q-gutter-xs q-mt-xs">
                    <q-btn
                      flat
                      round
                      dense
                      size="xs"
                      icon="edit"
                      color="grey-7"
                      @click.stop="editSvPayment(p)"
                    />
                    <q-btn
                      flat
                      round
                      dense
                      size="xs"
                      icon="delete_outline"
                      color="negative"
                      @click.stop="deleteSvPayment(p)"
                    />
                  </div>
                </q-item-section>
                <q-item-section side>
                  <div class="text-weight-bold" :style="{ color: p.is_paid ? '#27AE60' : 'var(--fc-text)' }">
                    {{ formatMoney(p.final_amount || p.amount || 0) }}
                  </div>
                  <div class="text-caption" style="color: var(--fc-text-light)">
                    {{ p.is_paid ? 'оплачено' : p.payment_status === 'to_pay' ? 'к оплате' : 'в работе' }}
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
            <div v-if="filteredSvPayments.length > 0" class="row items-center q-px-md q-py-xs" style="background: var(--fc-bg-alt); border-top: 1px solid var(--fc-border-light)">
              <span style="font-size: 12px; font-weight: bold; color: var(--fc-text); flex: 1">Итого</span>
              <span style="font-size: 13px; font-weight: bold; color: var(--fc-text)">{{ formatMoney(filteredSvPayments.reduce((s, p) => s + (p.final_amount || p.amount || 0), 0)) }}</span>
            </div>
            <q-card-section v-if="filteredSvPayments.length === 0" class="text-center" style="color: var(--fc-text-muted); font-size: 12px">
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
                <div class="text-subtitle2 text-weight-bold" style="color: var(--fc-text)">
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
                class="full-width"
                style="background: var(--fc-accent); color: var(--fc-text); font-size: 12px; height: 36px; border-radius: 4px"
                :disable="!noteText?.trim()"
                @click="addTextNote"
              />
            </q-card-section>
          </q-card>

          <!-- Список заметок -->
          <q-card class="is-card">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: var(--fc-text)">
                Все заметки
              </div>
            </q-card-section>
            <q-list v-if="voiceNotes.length > 0" dense separator>
              <q-item v-for="h in voiceNotes" :key="h.id">
                <q-item-section avatar>
                  <q-icon :name="h.entry_type === 'voice_note' ? 'mic' : 'comment'" :color="h.entry_type === 'voice_note' ? 'purple' : 'blue-grey'" size="18px" />
                </q-item-section>
                <q-item-section>
                  <q-item-label style="font-size: 12px; color: var(--fc-text)">
                    {{ cleanNoteText(h) }}
                  </q-item-label>
                  <q-item-label caption style="color: var(--fc-text-light)">
                    {{ h.created_by_name || 'Неизвестный' }}
                  </q-item-label>
                </q-item-section>
                <q-item-section v-if="h.entry_type === 'voice_note' && extractVoiceUrl(h)" side>
                  <audio :src="voiceStreamUrl(extractVoiceUrl(h))" controls preload="none" style="height: 36px; width: 120px" />
                </q-item-section>
                <q-item-section side>
                  <div class="text-caption" style="color: var(--fc-text-light)">
                    {{ formatDate(h.created_at) }}
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="text-center" style="color: var(--fc-text-muted); padding: 24px">
              <q-icon name="speaker_notes_off" size="32px" color="grey-4" class="q-mb-sm" /><div>Нет заметок</div>
            </q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ====== ВКЛАДКА 7: Чат надзора (InlineChatRoom) ====== -->
        <q-tab-panel name="sv-chat" class="q-pa-sm">
          <div style="border: 1px solid var(--fc-border-light); border-radius: 8px; overflow: hidden">
            <InlineChatRoom
              v-if="svChatTabVisited && card?.id"
              chat-type="supervision"
              :supervision-card-id="card.id"
              :can-script="true"
              @script-click="loadSvScriptsAndShow"
            />
          </div>
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
    <q-dialog v-model="showAddVisit" @hide="editingVisitId = null; visitExecutorPick = visitExecutorOptions[0] || null">
      <q-card style="min-width: 320px">
        <q-card-section>
          <div class="text-subtitle1 text-weight-bold">
            {{ editingVisitId ? 'Редактировать выезд' : 'Новый выезд' }}
          </div>
        </q-card-section>
        <q-card-section>
          <div class="text-caption text-grey-7 q-mb-xs">
            Дата выезда
          </div>
          <q-input
            v-model="visitForm.visit_date"
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
            v-model="visitExecutorPick"
            :options="visitExecutorOptions"
            option-label="label"
            label="Исполнитель"
            outlined
            dense
            class="q-mb-sm"
          />
          <q-input
            v-model="visitForm.notes"
            label="Заметки"
            outlined
            dense
            type="textarea"
            autogrow
            class="q-mb-sm"
          />
          <q-item tag="label" class="q-px-none q-pt-xs">
            <q-item-section avatar>
              <q-checkbox v-model="visitForm.extra_visit" color="positive" />
            </q-item-section>
            <q-item-section>
              <q-item-label>Доп. выезд</q-item-label>
              <q-item-label caption>
                Оплата за выезд начисляется только для доп. выездов
              </q-item-label>
            </q-item-section>
          </q-item>
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
          <div class="text-caption text-grey-7 q-mb-xs">
            Плановая дата
          </div>
          <q-input
            v-model="editEntry.plan_date"
            outlined
            dense
            type="date"
            class="q-mb-sm"
          />
          <div class="text-caption text-grey-7 q-mb-xs">
            Фактическая дата
          </div>
          <q-input
            v-model="editEntry.actual_date"
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
    <!-- Диалог ежемесячной ставки -->
    <q-dialog v-model="showMonthlyRateDialog">
      <q-card style="min-width: 320px; border-radius: 12px">
        <q-card-section class="q-pb-sm">
          <div class="text-subtitle2 text-weight-bold">
            Ежемесячная ставка
          </div>
          <div class="text-caption" style="color: var(--fc-text-light)">
            {{ monthlyRateTarget.employee_name }} ({{ monthlyRateTarget.role }})
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none q-gutter-y-sm">
          <div v-if="activeMonthlyAssignment" class="q-pa-sm" style="background: var(--fc-state-success-bg); border-radius: 8px; font-size: 12px">
            Текущая ставка: <b>{{ activeMonthlyAssignment.monthly_amount }} ₽/мес.</b>
            (с {{ fmtDMY(activeMonthlyAssignment.start_date) }})
          </div>
          <div class="text-caption" style="color: var(--fc-text-disabled)">
            Ставка будет начислена за текущий месяц немедленно, затем 1-го числа каждого следующего месяца, пока карточка не переведена в «Выполненный проект».
          </div>
          <q-input
            v-model.number="monthlyRateAmount"
            label="Ставка в месяц (₽)"
            type="number"
            outlined
            dense
          />
          <q-input
            v-model.number="minVisitsInput"
            label="Мин. выездов в месяц"
            type="number"
            outlined
            dense
            clearable
            hint="Для ДАН и ст. менеджера вместе"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn
            v-if="activeMonthlyAssignment"
            flat
            no-caps
            label="Деактивировать"
            color="negative"
            @click="deactivateMonthlyRate"
          />
          <q-btn flat no-caps label="Отмена" @click="showMonthlyRateDialog = false" />
          <q-btn
            unelevated
            no-caps
            label="Установить"
            style="background: var(--fc-accent); color: var(--fc-text)"
            :disable="!monthlyRateAmount || monthlyRateAmount <= 0"
            @click="saveMonthlyRate"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог статистики выездов по месяцам -->
    <!-- Диалог стадий надзора -->
    <q-dialog v-model="showStagesDialog">
      <q-card style="min-width: 320px; max-width: 480px; border-radius: 12px">
        <q-card-section class="row items-center q-pb-xs">
          <div class="text-subtitle2 text-weight-bold">
            Стадии надзора
          </div>
          <q-space />
          <q-btn
            flat
            round
            dense
            icon="close"
            @click="showStagesDialog = false"
          />
        </q-card-section>
        <q-list dense class="q-pb-sm">
          <q-item v-for="(stage, idx) in SUPERVISION_STAGES" :key="stage" dense>
            <q-item-section avatar style="min-width: 32px">
              <q-icon
                :name="idx < currentStageIndex ? 'check_circle' : idx === currentStageIndex ? 'radio_button_checked' : 'radio_button_unchecked'"
                :color="idx < currentStageIndex ? 'positive' : idx === currentStageIndex ? 'primary' : 'grey-4'"
                size="20px"
              />
            </q-item-section>
            <q-item-section>
              <q-item-label
                :style="{
                  fontSize: '12px',
                  color: idx < currentStageIndex ? '#2e7d32' : idx === currentStageIndex ? '#1565C0' : 'var(--fc-text-muted)',
                  fontWeight: idx === currentStageIndex ? '600' : '400',
                }"
              >
                {{ stage }}
              </q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>
    </q-dialog>

    <q-dialog v-model="showVisitStatsDialog">
      <q-card style="min-width: 340px; max-width: 480px; border-radius: 12px">
        <q-card-section class="row items-center q-pb-sm">
          <div>
            <div class="text-subtitle2 text-weight-bold">
              Статистика выездов
            </div>
            <div class="text-caption" style="color: var(--fc-text-light)">
              Норма: {{ card?.min_visits_per_month ?? '—' }} выездов/мес.
            </div>
          </div>
          <q-space />
          <q-btn
            flat
            round
            dense
            icon="close"
            @click="showVisitStatsDialog = false"
          />
        </q-card-section>
        <q-separator />
        <q-card-section class="q-pt-sm q-pb-md">
          <div v-if="visitStatsByMonth.length === 0" class="text-caption text-center" style="color: var(--fc-text-disabled); padding: 16px 0">
            Выездов пока нет
          </div>
          <div v-for="row in visitStatsByMonth" :key="row.ym" class="q-mb-sm">
            <div class="row items-center q-mb-xs">
              <span class="text-caption text-weight-medium" style="flex: 1">{{ row.label }}</span>
              <q-chip
                v-if="row.minVisits && row.isOver"
                dense
                color="orange-1"
                text-color="orange-9"
                size="xs"
                icon="trending_up"
              >
                +{{ row.regular - row.minVisits }} сверх
              </q-chip>
              <q-chip
                v-else-if="row.minVisits && row.isUnder"
                dense
                color="red-1"
                text-color="red-8"
                size="xs"
                icon="trending_down"
              >
                {{ row.regular }}/{{ row.minVisits }}
              </q-chip>
              <q-chip
                v-else-if="row.minVisits"
                dense
                color="green-1"
                text-color="green-8"
                size="xs"
                icon="check"
              >
                в норме
              </q-chip>
            </div>
            <div class="row q-gutter-x-sm" style="font-size: 12px; color: var(--fc-text-medium)">
              <span>Плановых: <b>{{ row.regular }}</b></span>
              <span v-if="row.additional > 0">Доп.: <b style="color: #e65100">{{ row.additional }}</b></span>
              <span>Итого: <b>{{ row.total }}</b></span>
            </div>
          </div>
          <q-separator v-if="visitStatsByMonth.length > 0" class="q-my-sm" />
          <div v-if="visitStatsByMonth.length > 0" class="row q-gutter-x-md" style="font-size: 12px; color: var(--fc-text)">
            <span>Всего плановых: <b>{{ visitStatsByMonth.reduce((s, r) => s + r.regular, 0) }}</b></span>
            <span>Всего доп.: <b style="color: #e65100">{{ visitStatsByMonth.reduce((s, r) => s + r.additional, 0) }}</b></span>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

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
        <q-toolbar style="background: var(--fc-accent); color: var(--fc-text)">
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
            style="background: var(--fc-accent); color: var(--fc-text); border-radius: 4px"
            :disable="!historyNote"
            @click="doAddHistory"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог создания Telegram-чата надзора -->
    <q-dialog v-model="showCreateSvChatDlg" persistent>
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: var(--fc-accent); color: var(--fc-text)">
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
            style="background: var(--fc-accent); color: var(--fc-text); border-radius: 4px"
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
        <q-card-section v-else class="text-center" style="color: var(--fc-text-muted)">
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

    <!-- FAB меню (скрыт на вкладке чата, чтобы не перекрывать кнопку отправки) -->
    <q-page-sticky v-if="activeTab !== 'sv-chat'" position="bottom-right" :offset="[18, 18]">
      <q-fab
        v-model="fabOpen"
        direction="up"
        style="background: var(--fc-accent); color: var(--fc-text)"
        icon="more_horiz"
        active-icon="close"
      >
        <q-fab-action
          icon="label"
          style="background: var(--fc-accent); color: var(--fc-text)"
          label="Теги"
          external-label
          label-position="left"
          @click="openTagDialog"
        />
      </q-fab>
    </q-page-sticky>

    <!-- Диалог тегов — мульти -->
    <q-dialog v-model="showTagDialog" persistent>
      <q-card style="min-width: 320px; max-width: 420px; width: 95vw; border-radius: 12px">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">
            Теги карточки
          </div>
          <q-space />
          <q-btn
            v-close-popup
            icon="close"
            flat
            round
            dense
            :disable="tagLoading"
          />
        </q-card-section>
        <q-card-section class="q-pt-sm">
          <!-- Текущие теги -->
          <div class="text-caption text-grey q-mb-xs">
            Текущие теги:
          </div>
          <div v-if="tagList.length > 0" class="row q-gutter-xs q-mb-sm">
            <q-chip
              v-for="(tag, tidx) in tagList"
              :key="tidx"
              removable
              dense
              :style="{ background: tag.color, color: 'white', fontWeight: '600', fontSize: '12px' }"
              @remove="removeTag(tidx)"
            >
              {{ tag.text }}
            </q-chip>
          </div>
          <div v-else class="text-caption text-grey-6 q-mb-sm">
            Нет тегов
          </div>

          <q-separator class="q-mb-sm" />

          <!-- Добавить тег -->
          <div class="text-caption text-grey q-mb-xs">
            Добавить тег:
          </div>
          <q-input
            v-model="newTagText"
            label="Текст тега"
            outlined
            dense
            maxlength="30"
            class="q-mb-sm"
            placeholder="Например: Срочно"
            @keyup.enter="addTag"
          />
          <div class="text-caption text-grey q-mb-xs">
            Цвет:
          </div>
          <div class="row q-gutter-xs q-mb-xs">
            <div
              v-for="c in tagPresetColors"
              :key="c"
              :style="{ width: '26px', height: '26px', borderRadius: '6px', background: c, cursor: 'pointer', border: newTagColor === c ? '3px solid var(--fc-text)' : '2px solid transparent', boxSizing: 'border-box' }"
              @click="newTagColor = c"
            />
            <div style="position: relative; width: 26px; height: 26px; flex-shrink: 0">
              <input
                type="color"
                :value="newTagColor"
                style="position: absolute; top: 0; left: 0; width: 26px; height: 26px; border: none; padding: 0; cursor: pointer; opacity: 0"
                @change="newTagColor = $event.target.value"
              >
              <div :style="{ width: '26px', height: '26px', borderRadius: '6px', background: newTagColor, border: '2px dashed var(--fc-text-muted)', boxSizing: 'border-box', pointerEvents: 'none' }" />
            </div>
          </div>
          <div v-if="newTagText" class="q-mt-xs">
            <span :style="{ display: 'inline-block', background: newTagColor, color: 'white', borderRadius: '4px', padding: '2px 10px', fontSize: '12px', fontWeight: '600' }">{{ newTagText }}</span>
          </div>
        </q-card-section>
        <q-card-actions align="right" class="q-pt-none">
          <q-btn
            flat
            no-caps
            label="+ Добавить"
            color="primary"
            :disable="!newTagText.trim()"
            @click="addTag"
          />
          <q-btn
            flat
            no-caps
            label="Отмена"
            :disable="tagLoading"
            @click="showTagDialog = false"
          />
          <q-btn
            flat
            no-caps
            label="Сохранить"
            color="primary"
            :loading="tagLoading"
            @click="saveTag"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог: Добавить платёж клиента -->
    <q-dialog v-model="showClientPayDialog" persistent>
      <q-card style="min-width: 300px; max-width: 420px; border-radius: 10px">
        <q-card-section style="background: var(--fc-bg-info); border-radius: 10px 10px 0 0">
          <div class="text-subtitle1 text-weight-bold">
            Ежемесячный платёж клиента
          </div>
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-input
            v-model.number="clientPayForm.amount"
            label="Сумма, ₽"
            type="number"
            outlined
            dense
            input-style="font-size: 14px"
          />
          <q-input
            v-model="clientPayForm.payment_month"
            label="Месяц (ГГГГ-ММ)"
            type="month"
            outlined
            dense
            input-style="font-size: 14px"
          />
          <q-input
            v-model="clientPayForm.payment_date"
            label="Дата оплаты"
            type="date"
            outlined
            dense
            input-style="font-size: 14px"
            hint="Первая дата задаёт день напоминания каждого месяца"
          />
        </q-card-section>
        <q-card-actions align="right" class="q-px-md q-pb-md">
          <q-btn
            flat
            label="Отмена"
            color="grey-7"
            no-caps
            @click="showClientPayDialog = false"
          />
          <q-btn
            unelevated
            label="Добавить"
            color="primary"
            no-caps
            @click="addClientPayment"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Скрытый input для загрузки чека платежа клиента -->
    <input
      ref="clientPayReceiptInput"
      type="file"
      accept="image/*,application/pdf"
      style="display:none"
      @change="handleClientPayReceiptUpload"
    >

    <!-- Диалог: Строительные работы -->
    <q-dialog v-model="showConstructionDialog" persistent>
      <q-card style="min-width: 320px; max-width: 480px; border-radius: 10px">
        <q-card-section style="background: var(--fc-bg-info); border-radius: 10px 10px 0 0">
          <div class="text-subtitle1 text-weight-bold">
            Строительные работы
          </div>
        </q-card-section>
        <q-card-section>
          <q-input
            v-model.number="constructionForm.planned"
            label="Итого стоимость план (₽)"
            outlined
            dense
            type="number"
            prefix="₽"
            class="q-mb-sm"
          />
          <q-input
            v-model="constructionForm.contractor"
            label="Подрядчик"
            outlined
            dense
            class="q-mb-sm"
          />
          <q-separator class="q-my-sm" />
          <div class="text-caption text-weight-bold q-mb-xs" style="color: var(--fc-text)">
            Фактические оплаты
          </div>
          <div v-for="(p, idx) in constructionForm.payments" :key="idx" class="row items-center q-mb-xs">
            <div class="col text-caption" style="color: var(--fc-text-medium)">
              {{ p.date }} — {{ formatMoney(p.amount) }}<span v-if="p.commission > 0"> (ком. {{ formatMoney(p.commission) }})</span>
            </div>
            <q-btn
              flat
              dense
              round
              icon="delete"
              size="xs"
              color="negative"
              @click="constructionForm.payments.splice(idx, 1)"
            />
          </div>
          <div class="row q-col-gutter-xs q-mb-xs">
            <div class="col-4">
              <q-input
                v-model="newConstructionPayment.date"
                label="Дата"
                stack-label
                outlined
                dense
                type="date"
              />
            </div>
            <div class="col-4">
              <q-input
                v-model.number="newConstructionPayment.amount"
                label="Сумма"
                stack-label
                outlined
                dense
                type="number"
                prefix="₽"
              />
            </div>
            <div class="col-4">
              <q-input
                v-model.number="newConstructionPayment.commission"
                label="Комиссия"
                stack-label
                outlined
                dense
                type="number"
                prefix="₽"
              />
            </div>
          </div>
          <q-btn
            unelevated
            dense
            no-caps
            label="+ Добавить оплату"
            style="background: var(--fc-accent); color: var(--fc-text); font-size: 11px"
            @click="addConstructionPayment"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat no-caps label="Отмена" @click="showConstructionDialog = false" />
          <q-btn
            unelevated
            no-caps
            label="Сохранить"
            color="primary"
            @click="saveConstructionBudget"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог: Черновые материалы -->
    <q-dialog v-model="showMaterialsDialog" persistent>
      <q-card style="min-width: 320px; max-width: 480px; border-radius: 10px">
        <q-card-section style="background: var(--fc-bg-info); border-radius: 10px 10px 0 0">
          <div class="text-subtitle1 text-weight-bold">
            Черновые материалы
          </div>
        </q-card-section>
        <q-card-section>
          <q-input
            v-model.number="materialsForm.planned"
            label="Итого план черновых материалов (₽)"
            outlined
            dense
            type="number"
            prefix="₽"
            class="q-mb-sm"
          />
          <q-input
            v-model="materialsForm.supplier"
            label="Поставщик"
            outlined
            dense
            class="q-mb-sm"
          />
          <q-separator class="q-my-sm" />
          <div class="text-caption text-weight-bold q-mb-xs" style="color: var(--fc-text)">
            Фактические заказы
          </div>
          <div v-for="(p, idx) in materialsForm.payments" :key="idx" class="row items-center q-mb-xs">
            <div class="col text-caption" style="color: var(--fc-text-medium)">
              {{ p.date }} — {{ formatMoney(p.amount) }}<span v-if="p.supplier" style="color: var(--fc-text-light)"> ({{ p.supplier }})</span><span v-if="p.commission > 0"> ком. {{ formatMoney(p.commission) }}</span>
            </div>
            <q-btn
              flat
              dense
              round
              icon="delete"
              size="xs"
              color="negative"
              @click="materialsForm.payments.splice(idx, 1)"
            />
          </div>
          <div class="row q-col-gutter-xs q-mb-xs">
            <div class="col-3">
              <q-input
                v-model="newMaterialsPayment.date"
                label="Дата"
                stack-label
                outlined
                dense
                type="date"
              />
            </div>
            <div class="col-3">
              <q-input
                v-model.number="newMaterialsPayment.amount"
                label="Сумма"
                stack-label
                outlined
                dense
                type="number"
                prefix="₽"
              />
            </div>
            <div class="col-3">
              <q-input
                v-model="newMaterialsPayment.supplier"
                label="Поставщик"
                stack-label
                outlined
                dense
              />
            </div>
            <div class="col-3">
              <q-input
                v-model.number="newMaterialsPayment.commission"
                label="Комиссия"
                stack-label
                outlined
                dense
                type="number"
                prefix="₽"
              />
            </div>
          </div>
          <q-btn
            unelevated
            dense
            no-caps
            label="+ Добавить заказ"
            style="background: var(--fc-accent); color: var(--fc-text); font-size: 11px"
            @click="addMaterialsPayment"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat no-caps label="Отмена" @click="showMaterialsDialog = false" />
          <q-btn
            unelevated
            no-caps
            label="Сохранить"
            color="primary"
            @click="saveMaterialsBudget"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог замера (вводные данные, scratch режим) -->
    <MeasurementDialog
      v-model="showIntroMeasurementDlg"
      :card-id="null"
      :contract-id="card?.contract_id"
      :contract-data="introContractData"
      :card-surveyor-id="null"
      @saved="loadIntroData"
    />

    <!-- Диалог загрузки файлов вводных данных (стадии и фото) -->
    <q-dialog v-model="showIntroUpload">
      <q-card style="min-width: 320px; max-width: 480px; width: 100%; border-radius: 10px">
        <q-toolbar style="background: var(--fc-accent); color: var(--fc-text)">
          <q-toolbar-title style="font-size: 14px; font-weight: 600">
            Загрузить — {{ introUploadLabel || introUploadStage }}
          </q-toolbar-title>
          <q-btn
            flat
            round
            dense
            icon="close"
            @click="showIntroUpload = false"
          />
        </q-toolbar>
        <q-card-section>
          <q-file
            v-model="introUploadFiles"
            label="Выберите файлы"
            multiple
            outlined
            dense
            accept="*/*"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat no-caps label="Отмена" @click="showIntroUpload = false" />
          <q-btn
            unelevated
            no-caps
            label="Загрузить"
            color="primary"
            :loading="introUploading"
            :disable="!introUploadFiles?.length"
            @click="doUploadIntroFile"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { supervisionApi, supervisionBudgetApi, supervisionClientPaymentsApi, filesApi, employeesApi, paymentsApi, locksApi, messengerApi } from 'src/services/api'
import VoiceRecorder from 'src/components/VoiceRecorder.vue'
import InlineChatRoom from 'src/components/InlineChatRoom.vue'
import MeasurementDialog from 'src/components/MeasurementDialog.vue'
import { addToCalendar } from 'src/composables/useCalendar'
import { usePermission } from 'src/composables/usePermission'
import { useEmployeeAvatars } from 'src/composables/useEmployeeAvatars'
import { useYdUpload } from 'src/composables/useYdUpload'
import { useAuthStore } from 'src/stores/auth'
import { useReferencesStore } from 'src/stores/references'

const { can } = usePermission()
const refs = useReferencesStore()
const authStore = useAuthStore()
const { ensureLoaded: loadAvatars, getAvatarByName } = useEmployeeAvatars()
const { uploadToYd } = useYdUpload()
const agentColor = computed(() => refs.agentByName(card.value?.agent_type)?.color || '#95A5A6')
const isArchived = computed(() => {
  if (!card.value) return false
  if (card.value.column_name === 'Выполненный проект') return true
  const cs = card.value.contract_status || ''
  return cs === 'СДАН' || cs === 'РАСТОРГНУТ'
})
const archiveLoading = ref(false)

const route = useRoute()
const router = useRouter()
const $q = useQuasar()
const loading = ref(true)
const card = ref(null)
const timeline = ref([])
const summary = ref(null)
const visits = ref([])
const budgetExtra = ref({
  construction_planned: null, construction_contractor: null, construction_notes: null, construction_payments: [],
  materials_planned: null, materials_supplier: null, materials_notes: null, materials_payments: [],
})

// Диалоги строительных работ и черновых материалов
const showConstructionDialog = ref(false)
const showMaterialsDialog = ref(false)
const constructionForm = ref({ planned: null, contractor: '', notes: '', payments: [] })
const materialsForm = ref({ planned: null, supplier: '', notes: '', payments: [] })
const newConstructionPayment = ref({ date: '', amount: null, commission: null })
const newMaterialsPayment = ref({ date: '', amount: null, supplier: '', commission: null })

// Ежемесячные платежи клиента по надзору
const clientPayments = ref([])
const clientPaymentSettings = ref({ notification_enabled: true, notification_day: 1 })
const showClientPayDialog = ref(false)
const clientPayForm = ref({ amount: null, payment_month: '', payment_date: '' })
const clientPayReceiptInput = ref(null)
const clientPayReceiptId = ref(null)

const constructionActualTotal = computed(() =>
  (budgetExtra.value.construction_payments || []).reduce((s, p) => s + (Number(p.amount) || 0), 0),
)
const materialsActualTotal = computed(() =>
  (budgetExtra.value.materials_payments || []).reduce((s, p) => s + (Number(p.amount) || 0), 0),
)

const totalCommission = computed(() => {
  const fromSummary = summary.value?.total_commission
  if (fromSummary && fromSummary > 0) return fromSummary
  return timeline.value.reduce((s, e) => s + (parseFloat(e.commission) || 0), 0)
})
const activeTab = ref('executors')
const svChatTabVisited = ref(false)
if (route.query.tab) activeTab.value = route.query.tab
const svContractYdPath = ref('')
const showAddVisit = ref(false)
const editingVisitId = ref(null)
const showReassignDan = ref(false)
const showReassignSM = ref(false)
const showMonthlyRateDialog = ref(false)
const monthlyRateTarget = ref({ role: '', employee_id: null, employee_name: '' })
const monthlyRateAmount = ref(null)
const minVisitsInput = ref(null)
const monthlyAssignments = ref([])
const showVisitStatsDialog = ref(false)
const activeMonthlyAssignment = computed(() =>
  monthlyAssignments.value.find(a => a.role === monthlyRateTarget.value.role) || null,
)
const newDanId = ref(null)
const newSMId = ref(null)
const danOptions = ref([])
const smOptions = ref([])
const showEditEntry = ref(false)
const editEntry = ref(null)
const cameraInput = ref(null)
const fileInput = ref(null)
const nadzorFileInput = ref(null)
const visitForm = ref({ visit_date: new Date().toISOString().split('T')[0], stage_code: '', notes: '', executor_name: '', visit_type: 'На объект', executor_role: 'ДАН', extra_visit: false })
// Сбрасываем стадию при смене типа выезда — опции меняются
watch(() => visitForm.value.visit_type, () => { visitForm.value.stage_code = '' })
const visitExecutorPick = ref(null)
const executorOptions = ref([])
const executorNameOptions = ref([])
const visitExecutorOptions = computed(() => {
  const opts = []
  if (card.value?.dan_name) opts.push({ label: `${card.value.dan_name} (ДАН)`, name: card.value.dan_name, role: 'ДАН' })
  if (card.value?.senior_manager_name) opts.push({ label: `${card.value.senior_manager_name} (Ст. менеджер)`, name: card.value.senior_manager_name, role: 'Старший менеджер проектов' })
  return opts
})
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

// === Теги ===
const fabOpen = ref(false)
const showTagDialog = ref(false)
const tagLoading = ref(false)
const tagPresetColors = ['#FF6B6B', '#FF9F43', '#F9CA24', '#6AB04C', '#22A6B3', '#4834D4', '#BE2EDD', '#E84393', '#576574', '#2C3E50']
const tagList = ref([])
const newTagText = ref('')
const newTagColor = ref('#FF6B6B')

function parseSvTags(tagsStr) {
  if (!tagsStr) return []
  try {
    const parsed = JSON.parse(tagsStr)
    if (Array.isArray(parsed)) return parsed.map(t => ({ text: String(t.text || ''), color: String(t.color || '#FF6B6B') }))
    return [{ text: String(tagsStr), color: '#FF6B6B' }]
  } catch {
    return [{ text: String(tagsStr), color: '#FF6B6B' }]
  }
}

function openTagDialog() {
  tagList.value = parseSvTags(card.value?.tags)
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
    await supervisionApi.updateCard(card.value.id, { tags: tagsJson, tag_color: null })
    $q.notify({ type: 'positive', message: 'Теги сохранены' })
    showTagDialog.value = false
    await reloadData()
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка сохранения тегов' })
  } finally {
    tagLoading.value = false
  }
}

async function clearTag() {
  tagLoading.value = true
  try {
    await supervisionApi.updateCard(card.value.id, { tags: null, tag_color: null })
    $q.notify({ type: 'positive', message: 'Теги удалены' })
    showTagDialog.value = false
    await reloadData()
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка удаления тегов' })
  } finally {
    tagLoading.value = false
  }
}

const filteredSvHistory = computed(() => {
  if (historyFilter.value === 'all') return svHistory.value
  if (historyFilter.value === 'site_visit') return svHistory.value.filter(h => h.entry_type === 'site_visit' || h.entry_type === 'site_visit_deleted')
  return svHistory.value.filter(h => h.entry_type === historyFilter.value)
})

// === Файлы по стадиям ===
const svFilesStages = ref({}) // { stage_code: [файлы] }
const showStageFileUpload = ref(false)
const stageUploadFiles = ref(null)
const stageUploading = ref(false)
const uploadStageCode = ref('')

// === Вводные данные проекта ===
const introContractData = ref(null)
const introFilesMap = ref({})
const showIntroMeasurementDlg = ref(false)
const showIntroUpload = ref(false)
const introUploadStage = ref('')
const introUploadLabel = ref('')
const introUploadFiles = ref(null)
const introUploading = ref(false)

const hasCrmCard = computed(() => !!card.value?.source_crm_card_id)

const introStageCodes = computed(() => {
  const pt = card.value?.project_type
  if (pt === 'Шаблонный') {
    return [
      { code: 'stage1', label: 'Стадия 1: Планировочное решение' },
      { code: 'stage3', label: 'Стадия 2: Чертёжная документация' },
      { code: 'stage2_3d', label: 'Стадия 3: 3D визуализация (Доп.)' },
    ]
  }
  return [
    { code: 'stage1', label: 'Стадия 1: Планировочное решение' },
    { code: 'stage2_concept', label: 'Стадия 2: Мудборды (концепция)' },
    { code: 'stage2_3d', label: 'Стадия 2: 3D визуализация' },
    { code: 'stage3', label: 'Стадия 3: Чертёжная документация' },
  ]
})

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

const canRestoreSupervision = computed(() => {
  const pos = authStore.user?.position || ''
  const role = authStore.user?.role || ''
  return pos === 'Руководитель студии' || pos === 'Старший менеджер проектов' || role === 'admin' || role === 'director'
})

// Исполнитель надзора — видит только свои выплаты (нет supervision.payments)
const svIsExecutor = computed(() => {
  const pos = authStore.user?.position || ''
  const secPos = authStore.user?.secondary_position || ''
  const execPositions = ['Дизайнер', 'Чертёжник', 'Замерщик', 'Дизайнер авторского надзора']
  return execPositions.some(p => pos === p || secPos === p) && !can('supervision.payments')
})

// Выплаты, видимые текущему пользователю
const filteredSvPayments = computed(() => {
  if (!svIsExecutor.value) return svPayments.value
  return svPayments.value.filter(p => Number(p.employee_id) === Number(authStore.user?.id))
})

// Стадии надзора (колонки доски) — строительные работы
const SUPERVISION_STAGES = [
  'Новый заказ',
  'В ожидании',
  'Стадия 1: Демонтаж/Монтаж/Штукатурные работы',
  'Стадия 2: Электрика/Сантехника/Звукоизоляция',
  'Стадия 3: Монтаж Пола/Потолков/Шпатлевание стен',
  'Стадия 4: Плиточные работы',
  'Стадия 5: Финишные отделочные работы',
  'Стадия 6: Чистовая электрика/сантехника',
  'Стадия 7: Монтаж Заказной мебели',
  'Стадия 8: Монтаж фабричной мебели/зеркал и стекл',
  'Стадия 9: Финишные доп. работы/декорирование',
  'Выполненный проект',
]

const currentStageIndex = computed(() => {
  if (!card.value) return -1
  return SUPERVISION_STAGES.indexOf(card.value.column_name)
})

const showStagesDialog = ref(false)

// Прогресс закупок (Закуплено / Доставлено = завершённые)
const svStageProgress = computed(() => {
  const entries = timeline.value
  if (!entries.length) return { done: 0, total: defaultStages.length, percent: 0 }
  const done = entries.filter(e => e.status === 'Закуплено' || e.status === 'Доставлено').length
  const total = entries.length
  return { done, total, percent: Math.round(done / total * 100) }
})

// Прогресс выездов текущего месяца
const visitProgress = computed(() => {
  const minVisits = card.value?.min_visits_per_month || null
  if (!minVisits) return null
  const now = new Date()
  const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  const current = visits.value.filter(v => v.visit_date?.startsWith(currentMonth))
  const regular = current.filter(v => !v.is_additional).length
  const additional = current.filter(v => v.is_additional).length
  const isOver = regular > minVisits
  const percent = Math.min(regular / minVisits, 1)
  const overflow = regular - minVisits
  return { minVisits, regular, additional, total: regular + additional, isOver, percent, overflow }
})

// Статистика выездов по месяцам для диалога
const visitStatsByMonth = computed(() => {
  const minVisits = card.value?.min_visits_per_month || null
  const byMonth = {}
  for (const v of visits.value) {
    const m = v.visit_date?.slice(0, 7) || 'Без даты'
    if (!byMonth[m]) byMonth[m] = { regular: 0, additional: 0 }
    if (v.is_additional) byMonth[m].additional++
    else byMonth[m].regular++
  }
  const monthNames = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']
  return Object.entries(byMonth)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([ym, c]) => {
      const label = ym === 'Без даты' ? ym : (() => {
        const [y, m] = ym.split('-')
        return `${monthNames[parseInt(m) - 1]} ${y}`
      })()
      const isOver = minVisits ? c.regular > minVisits : false
      const isUnder = minVisits ? c.regular < minVisits : false
      return { ym, label, regular: c.regular, additional: c.additional, total: c.regular + c.additional, minVisits, isOver, isUnder }
    })
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
  { code: 'STAGE_5_WALL', name: 'Закупка настенных материалов' },
  { code: 'STAGE_6_FLOOR', name: 'Закупка напольных материалов' },
  { code: 'STAGE_7_STUCCO', name: 'Лепной декор' },
  { code: 'STAGE_8_LIGHTING', name: 'Освещение' },
  { code: 'STAGE_CEILING', name: 'Закупка потолочных материалов' },
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
  { label: 'В ожидании', value: 'В ожидании' },
  { label: 'Стадия 1: Закупка керамогранита', value: 'Стадия 1: Закупка керамогранита' },
  { label: 'Стадия 2: Закупка сантехники', value: 'Стадия 2: Закупка сантехники' },
  { label: 'Стадия 3: Закупка оборудования', value: 'Стадия 3: Закупка оборудования' },
  { label: 'Стадия 4: Закупка дверей и окон', value: 'Стадия 4: Закупка дверей и окон' },
  { label: 'Стадия 5: Закупка настенных материалов', value: 'Стадия 5: Закупка настенных материалов' },
  { label: 'Стадия 6: Закупка напольных материалов', value: 'Стадия 6: Закупка напольных материалов' },
  { label: 'Стадия 7: Лепной декор', value: 'Стадия 7: Лепной декор' },
  { label: 'Стадия 8: Освещение', value: 'Стадия 8: Освещение' },
  { label: 'Стадия 9: Закупка потолочных материалов', value: 'Стадия 9: Закупка потолочных материалов' },
  { label: 'Стадия 10: Бытовая техника', value: 'Стадия 10: Бытовая техника' },
  { label: 'Стадия 11: Закупка заказной мебели', value: 'Стадия 11: Закупка заказной мебели' },
  { label: 'Стадия 12: Закупка фабричной мебели', value: 'Стадия 12: Закупка фабричной мебели' },
  { label: 'Стадия 13: Закупка декора', value: 'Стадия 13: Закупка декора' },
  { label: 'Выполненный проект', value: 'Выполненный проект' },
]

// Стадии закупок (для выездов "К поставщику" и таймлайна закупок)
const PURCHASE_STAGE_CODES = [
  { label: 'Ст. 1: Закупка керамогранита', value: 'STAGE_1_CERAMIC' },
  { label: 'Ст. 2: Закупка сантехники', value: 'STAGE_2_PLUMBING' },
  { label: 'Ст. 3: Закупка оборудования', value: 'STAGE_3_EQUIPMENT' },
  { label: 'Ст. 4: Двери и окна', value: 'STAGE_4_DOORS' },
  { label: 'Ст. 5: Настенные материалы', value: 'STAGE_5_WALL' },
  { label: 'Ст. 6: Напольные материалы', value: 'STAGE_6_FLOOR' },
  { label: 'Ст. 7: Лепной декор', value: 'STAGE_7_STUCCO' },
  { label: 'Ст. 8: Освещение', value: 'STAGE_8_LIGHTING' },
  { label: 'Ст. 9: Потолочные материалы', value: 'STAGE_CEILING' },
  { label: 'Ст. 10: Бытовая техника', value: 'STAGE_9_APPLIANCES' },
  { label: 'Ст. 11: Заказная мебель', value: 'STAGE_10_CUSTOM_FURNITURE' },
  { label: 'Ст. 12: Фабричная мебель', value: 'STAGE_11_FACTORY_FURNITURE' },
  { label: 'Ст. 13: Декор', value: 'STAGE_12_DECOR' },
]

// Стадии строительных работ (для выездов "На объект")
const WORK_STAGE_CODES = [
  { label: 'Ст. 1: Демонтаж/Монтаж/Штукатурные работы', value: 'WORK_1' },
  { label: 'Ст. 2: Электрика/Сантехника/Звукоизоляция', value: 'WORK_2' },
  { label: 'Ст. 3: Монтаж Пола/Потолков/Шпатлевание стен', value: 'WORK_3' },
  { label: 'Ст. 4: Плиточные работы', value: 'WORK_4' },
  { label: 'Ст. 5: Финишные отделочные работы', value: 'WORK_5' },
  { label: 'Ст. 6: Чистовая электрика/сантехника', value: 'WORK_6' },
  { label: 'Ст. 7: Монтаж Заказной мебели', value: 'WORK_7' },
  { label: 'Ст. 8: Монтаж фабричной мебели/зеркал и стекл', value: 'WORK_8' },
  { label: 'Ст. 9: Финишные доп. работы/декорирование', value: 'WORK_9' },
]

// Опции стадий для формы выезда — зависят от типа выезда
const stageCodesForVisit = computed(() =>
  visitForm.value.visit_type === 'К поставщику' ? PURCHASE_STAGE_CODES : WORK_STAGE_CODES,
)

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
  if (status === 'Закуплено' || status === 'Доставлено') return { background: 'var(--fc-state-success-bg)' }
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

function fmtDMY(dateStr) {
  if (!dateStr) return '—'
  const p = String(dateStr).slice(0, 10).split('-')
  return p.length === 3 ? `${p[2]}.${p[1]}.${p[0]}` : dateStr
}

function formatMoney(amount) {
  if (!amount) return '0 ₽'
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency', currency: 'RUB', maximumFractionDigits: 0,
  }).format(amount)
}

function formatReportMonth(m) {
  if (!m) return null
  try {
    const [y, mo] = m.split('-')
    const months = ['январь','февраль','март','апрель','май','июнь','июль','август','сентябрь','октябрь','ноябрь','декабрь']
    return `${months[parseInt(mo) - 1]} ${y}`
  } catch { return m }
}

// Цвет дедлайна
function dlColor(deadline) {
  if (!deadline) return 'var(--fc-text-light)'
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

async function archiveSupervisionWithValidation() {
  const warnings = []
  // Проверка платежей по договору (оплата от клиента)
  try {
    const { contractsApi: cApi } = await import('src/services/api')
    const { data: cd } = await cApi.getById(card.value.contract_id)
    if (!cd?.advance_payment_paid_date) {
      warnings.push('Не получен аванс по договору')
    }
  } catch {}

  if (warnings.length === 0) {
    await doArchiveSupervision()
    return
  }

  $q.dialog({
    title: 'Данные не заполнены',
    message: `<b>Обнаружены незавершённые данные:</b><ul style="margin:8px 0 0 0;padding-left:16px">${warnings.map(w => `<li>${w}</li>`).join('')}</ul><br>Переместить в архив?`,
    html: true,
    ok: { label: 'В архив', color: 'green', unelevated: true },
    cancel: { label: 'Отмена', flat: true },
    persistent: true,
  }).onOk(() => { doArchiveSupervision() })
}

async function restoreSupervision() {
  archiveLoading.value = true
  try {
    const { contractsApi: cApi } = await import('src/services/api')
    await cApi.update(card.value.contract_id, { status: 'АВТОРСКИЙ НАДЗОР' })
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка восстановления' })
  } finally { archiveLoading.value = false }
}

async function doArchiveSupervision() {
  archiveLoading.value = true
  try {
    const { contractsApi: cApi } = await import('src/services/api')
    await cApi.update(card.value.contract_id, { status: 'СДАН' })
    $q.notify({ type: 'positive', message: 'Проект завершён и перемещён в архив' })
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка архивации' })
  } finally { archiveLoading.value = false }
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

  // Авто-миграция: если таймлайн есть, но STAGE_CEILING отсутствует — запускаем init (добавит стадию)
  const hasCeiling = timeline.value.some((e) => e.stage_code === 'STAGE_CEILING')
  if (timeline.value.length > 0 && !hasCeiling) {
    try {
      const { api: ax } = await import('src/boot/axios')
      await ax.post(`/api/v1/supervision-timeline/${cardId}/init`)
      const { data: tl } = await supervisionApi.getTimeline(cardId)
      timeline.value = tl?.entries || tl || []
      const { data: s } = await supervisionApi.getTimelineSummary(cardId)
      summary.value = s
    } catch { /* ok */ }
  }

  // Оплаты надзора
  try {
    const { api: ax } = await import('src/boot/axios')
    const { data } = await ax.get(`/api/v1/payments/by-supervision-card/${cardId}`)
    svPayments.value = data || []
  } catch { svPayments.value = [] }

  // Платежи клиента по надзору
  try {
    const { data } = await supervisionClientPaymentsApi.getByCard(cardId)
    clientPayments.value = data.payments || []
    clientPaymentSettings.value = data.settings || { notification_enabled: true, notification_day: 1 }
  } catch { clientPayments.value = [] }

  // Бюджет (строительные работы + черновые материалы)
  try { const { data } = await supervisionBudgetApi.get(cardId); budgetExtra.value = data } catch { /* ok */ }

  // История надзора
  try { const { data } = await supervisionApi.getHistory(cardId); svHistory.value = data || [] } catch { svHistory.value = [] }

  // Ежемесячные назначения
  try { const { data } = await supervisionApi.getMonthlyAssignments(cardId); monthlyAssignments.value = data || [] } catch { monthlyAssignments.value = [] }

  // Файлы: закупки (stage=supervision) и отчёты выездов (stage=supervision_reports)
  const cid = card.value?.contract_id
  if (cid) {
    try { const { data } = await filesApi.getContractFiles(cid, 'supervision'); svFilesSupervision.value = data || [] } catch { svFilesSupervision.value = [] }
    try { const { data } = await filesApi.getContractFiles(cid, 'supervision_reports'); svFilesReports.value = data || [] } catch { svFilesReports.value = [] }

    // Файлы по стадиям закупок — загружаем для каждого stage_code
    await loadStageFiles(cid)
  }

  // Вводные данные проекта (Замер, Фотофиксация, Стадии)
  await loadIntroData()

  // Исполнители
  const names = []
  if (card.value?.dan_name) names.push({ label: `${card.value.dan_name} (ДАН)`, value: card.value.dan_id })
  if (card.value?.senior_manager_name) names.push({ label: `${card.value.senior_manager_name} (Ст. менеджер)`, value: card.value.senior_manager_id })
  if (card.value?.studio_director_name) names.push({ label: `${card.value.studio_director_name} (Руководитель)`, value: card.value.studio_director_id })
  executorOptions.value = names
  executorNameOptions.value = names.map(n => n.label)
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

// === Вводные данные проекта — загрузка ===
async function loadIntroData() {
  if (!card.value) return
  try {
    const cid = card.value.contract_id
    const { contractsApi: cApi } = await import('src/services/api')
    const { data } = await cApi.getById(cid)
    introContractData.value = data
    // Файлы CRM стадий
    const stageCodes = ['stage1', 'stage2_concept', 'stage2_3d', 'stage3']
    const fm = {}
    for (const code of stageCodes) {
      try {
        const { data: files } = await filesApi.getContractFiles(cid, code)
        if (files?.length) fm[code] = files
      } catch {}
    }
    introFilesMap.value = fm
  } catch {}
}

function uploadIntroFile(stageCode, stageLabel) {
  introUploadStage.value = stageCode
  introUploadLabel.value = stageLabel
  introUploadFiles.value = null
  showIntroUpload.value = true
}

async function doUploadIntroFile() {
  if (!introUploadFiles.value?.length || !card.value) return
  introUploading.value = true
  try {
    const { api: ax } = await import('src/boot/axios')
    const cid = card.value.contract_id
    const contractFolder = (introContractData.value?.yandex_folder_path || '').replace(/^disk:/, '')
    const STAGE_FOLDERS = {
      stage1: '1 стадия - Планировочное решение',
      stage2_concept: '2 стадия - Концепция дизайна/Концепция-коллажи',
      stage2_3d: '2 стадия - Концепция дизайна/3D визуализация',
      stage3: '3 стадия - Чертежный проект',
    }
    const stageFolder = STAGE_FOLDERS[introUploadStage.value] || introUploadStage.value
    for (const file of introUploadFiles.value) {
      if (!contractFolder) { $q.notify({ type: 'negative', message: 'Папка проекта на ЯД не создана' }); break }
      const yp = `disk:${contractFolder}/Вводные данные/${stageFolder}/${file.name}`
      try {
        const { public_link: publicLink, yandex_path: actualYp } = await uploadToYd(file, yp)
        await ax.post('/api/v1/files/', {
          contract_id: cid, stage: introUploadStage.value,
          file_type: file.type?.includes('image') ? 'image' : 'pdf',
          public_link: publicLink, yandex_path: actualYp, file_name: file.name, file_order: 0, variation: 1,
        })
      } catch (e) { console.warn('[IntroUpload]:', e) }
    }
    $q.notify({ type: 'positive', message: `Загружено ${introUploadFiles.value.length} файл(ов)` })
    showIntroUpload.value = false
    await loadIntroData()
  } catch { $q.notify({ type: 'negative', message: 'Ошибка загрузки' }) }
  finally { introUploading.value = false }
}

async function deleteIntroFile(file) {
  try {
    const { api: ax } = await import('src/boot/axios')
    await ax.delete(`/api/v1/files/${file.id}`)
    await loadIntroData()
    $q.notify({ type: 'positive', message: 'Файл удалён' })
  } catch { $q.notify({ type: 'negative', message: 'Ошибка удаления' }) }
}

function openIntroFile(f) {
  const link = f.public_link || (f.yandex_path ? `https://disk.yandex.ru/client/disk/${encodeURIComponent((f.yandex_path || '').replace(/^disk:/, ''))}` : null)
  if (link) window.open(link, '_blank')
}

function introFileIcon(f) {
  const name = (f.file_name || '').toLowerCase()
  if (name.endsWith('.pdf')) return 'picture_as_pdf'
  if (/\.(jpg|jpeg|png|gif|bmp|heic|heif|webp)$/.test(name)) return 'image'
  if (/\.(mp4|mov|avi|mkv)$/.test(name)) return 'videocam'
  return 'description'
}

async function deleteIntroMeasurement() {
  try {
    const { contractsApi: cApi } = await import('src/services/api')
    await cApi.update(card.value.contract_id, {
      measurement_image_link: null, measurement_yandex_path: null, measurement_file_name: null,
    })
    await loadIntroData()
    $q.notify({ type: 'positive', message: 'Замер удалён' })
  } catch { $q.notify({ type: 'negative', message: 'Ошибка удаления' }) }
}

async function deleteIntroPhotoFolder() {
  try {
    const { contractsApi: cApi } = await import('src/services/api')
    await cApi.update(card.value.contract_id, {
      photo_folder_public_link: null, photo_documentation_yandex_path: null,
    })
    await loadIntroData()
    $q.notify({ type: 'positive', message: 'Фотофиксация удалена' })
  } catch { $q.notify({ type: 'negative', message: 'Ошибка удаления' }) }
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
      const { public_link: publicLink, yandex_path: actualYp } = await uploadToYd(file, yp)
      if (cid) {
        await ax.post('/api/v1/files/', {
          contract_id: cid,
          stage: 'supervision_stage',
          stage_code: uploadStageCode.value,
          file_type: file.type?.includes('image') ? 'image' : 'pdf',
          public_link: publicLink,
          yandex_path: actualYp,
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

function hasPurchaseData(entry) {
  return !!(
    entry.executor ||
    entry.commission > 0 ||
    entry.actual_date ||
    entry.plan_date ||
    entry.supplier ||
    entry.budget_planned > 0
  )
}

async function toggleStageComplete(entry) {
  const isDone = entry.status === 'Закуплено' || entry.status === 'Доставлено'
  const newStatus = isDone ? 'Не начато' : 'Закуплено'
  try {
    await supervisionApi.updateTimelineEntry(card.value.id, entry.stage_code, {
      status: newStatus,
      actual_date: newStatus === 'Закуплено' ? (entry.actual_date || new Date().toISOString().slice(0, 10)) : null,
    })
    entry.status = newStatus
    $q.notify({ type: 'positive', message: newStatus === 'Закуплено' ? 'Стадия отмечена закупленной' : 'Отметка снята', timeout: 1500 })
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

function openConstructionDialog() {
  constructionForm.value = {
    planned: budgetExtra.value.construction_planned,
    contractor: budgetExtra.value.construction_contractor || '',
    notes: budgetExtra.value.construction_notes || '',
    payments: JSON.parse(JSON.stringify(budgetExtra.value.construction_payments || [])),
  }
  newConstructionPayment.value = { date: '', amount: null, commission: null }
  showConstructionDialog.value = true
}

function openMaterialsDialog() {
  materialsForm.value = {
    planned: budgetExtra.value.materials_planned,
    supplier: budgetExtra.value.materials_supplier || '',
    notes: budgetExtra.value.materials_notes || '',
    payments: JSON.parse(JSON.stringify(budgetExtra.value.materials_payments || [])),
  }
  newMaterialsPayment.value = { date: '', amount: null, supplier: '', commission: null }
  showMaterialsDialog.value = true
}

function addConstructionPayment() {
  const p = newConstructionPayment.value
  if (!p.date || !p.amount) { $q.notify({ type: 'warning', message: 'Укажите дату и сумму' }); return }
  constructionForm.value.payments.push({ date: p.date, amount: Number(p.amount), commission: Number(p.commission) || 0 })
  newConstructionPayment.value = { date: '', amount: null, commission: null }
}

function addMaterialsPayment() {
  const p = newMaterialsPayment.value
  if (!p.date || !p.amount) { $q.notify({ type: 'warning', message: 'Укажите дату и сумму' }); return }
  materialsForm.value.payments.push({ date: p.date, amount: Number(p.amount), supplier: p.supplier || '', commission: Number(p.commission) || 0 })
  newMaterialsPayment.value = { date: '', amount: null, supplier: '', commission: null }
}

async function saveConstructionBudget() {
  const toNum = (v) => (v !== '' && v !== null && v !== undefined ? Number(v) : null)
  try {
    const { data } = await supervisionBudgetApi.update(card.value.id, {
      construction_planned: toNum(constructionForm.value.planned),
      construction_contractor: constructionForm.value.contractor || null,
      construction_notes: constructionForm.value.notes || null,
      construction_payments: constructionForm.value.payments,
    })
    budgetExtra.value = data
    showConstructionDialog.value = false
    const { data: s } = await supervisionApi.getTimelineSummary(card.value.id)
    summary.value = s
    $q.notify({ type: 'positive', message: 'Строительные работы сохранены' })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка сохранения' })
  }
}

async function saveMaterialsBudget() {
  const toNum = (v) => (v !== '' && v !== null && v !== undefined ? Number(v) : null)
  try {
    const { data } = await supervisionBudgetApi.update(card.value.id, {
      materials_planned: toNum(materialsForm.value.planned),
      materials_supplier: materialsForm.value.supplier || null,
      materials_notes: materialsForm.value.notes || null,
      materials_payments: materialsForm.value.payments,
    })
    budgetExtra.value = data
    showMaterialsDialog.value = false
    const { data: s } = await supervisionApi.getTimelineSummary(card.value.id)
    summary.value = s
    $q.notify({ type: 'positive', message: 'Черновые материалы сохранены' })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка сохранения' })
  }
}

async function saveTimelineEntry() {
  if (!editEntry.value || !card.value) return
  const PURCHASE_PAID_STATUSES = ['Закуплено', 'Доставлено']
  if (PURCHASE_PAID_STATUSES.includes(editEntry.value.status) && !editEntry.value.executor) {
    $q.notify({ type: 'warning', message: `Укажите исполнителя перед установкой статуса «${editEntry.value.status}» — оплата начисляется только указанному исполнителю` })
    return
  }
  try {
    // Если таймлайн ещё не инициализирован — инициализируем
    if (timeline.value.length === 0) {
      const { api: ax } = await import('src/boot/axios')
      await ax.post(`/api/v1/supervision-timeline/${card.value.id}/init`)
      const { data } = await supervisionApi.getTimeline(card.value.id)
      timeline.value = data?.entries || data || []
      // Берём реальный stage_code из БД (defaultStages может не совпадать)
      const dbEntry = timeline.value.find(
        (e) => e.stage_code === editEntry.value.stage_code || e.stage_name === editEntry.value.stage_name,
      )
      if (dbEntry) editEntry.value.stage_code = dbEntry.stage_code
    }
    const toNum = (v) => (v !== '' && v !== null && v !== undefined ? Number(v) : null)
    await supervisionApi.updateTimelineEntry(card.value.id, editEntry.value.stage_code, {
      plan_date: editEntry.value.plan_date || null,
      actual_date: editEntry.value.actual_date || null,
      budget_planned: toNum(editEntry.value.budget_planned),
      budget_actual: toNum(editEntry.value.budget_actual),
      supplier: editEntry.value.supplier,
      commission: toNum(editEntry.value.commission),
      status: editEntry.value.status,
      notes: editEntry.value.notes,
      executor: editEntry.value.executor,
    })
    $q.notify({ type: 'positive', message: 'Стадия обновлена' })
    showEditEntry.value = false
    await reloadData()
  } catch (err) {
    const detail = err.response?.data?.detail
    const msg = Array.isArray(detail)
      ? detail.map((d) => d.msg || d.message || JSON.stringify(d)).join('; ')
      : detail || 'Ошибка'
    $q.notify({ type: 'negative', message: msg })
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
  // Применяем выбранного исполнителя
  const pickedExecutor = visitExecutorPick.value
  const executorName = pickedExecutor?.name || visitForm.value.executor_name || ''
  const executorRole = pickedExecutor?.role || visitForm.value.executor_role || 'ДАН'

  // Предупреждение: доп. выезд не отмечен, а ежемесячная ставка для роли не активна
  if (!editingVisitId.value && !visitForm.value.extra_visit) {
    const hasMonthly = monthlyAssignments.value.some(a => a.role === executorRole)
    if (!hasMonthly) {
      $q.notify({ type: 'warning', message: `Ежемесячная ставка для «${executorRole}» не включена. Оплата за выезд не будет начислена.` })
    }
  }
  try {
    const stageLabel = stageCodesForVisit.value.find(s => s.value === visitForm.value.stage_code)?.label || ''
    const isEditing = !!editingVisitId.value
    const payload = {
      stage_code: visitForm.value.stage_code,
      stage_name: stageLabel,
      visit_date: visitForm.value.visit_date,
      visit_type: visitForm.value.visit_type || 'На объект',
      executor_name: executorName,
      notes: visitForm.value.notes,
      executor_role: executorRole,
      extra_visit: visitForm.value.extra_visit || false,
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
    executor_role: visit.executor_role || 'ДАН',
    extra_visit: visit.is_additional || false,
  }
  visitExecutorPick.value = visitExecutorOptions.value.find(
    o => o.name === visit.executor_name,
  ) || visitExecutorOptions.value[0] || null
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
      await ax.delete(`/api/v1/supervision-visits/${card.value.id}/visits/${visit.id}`)
      $q.notify({ type: 'positive', message: 'Выезд удалён' })
      await reloadData()
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
    }
  })
}

function editSvPayment(p) {
  $q.dialog({
    title: 'Изменить сумму',
    prompt: { model: String(p.final_amount || p.amount || 0), type: 'number' },
    cancel: { label: 'Отмена', flat: true, noCaps: true },
    ok: { label: 'Сохранить', noCaps: true, color: 'positive' },
  }).onOk(async (val) => {
    try {
      await paymentsApi.update(p.id, { final_amount: parseFloat(val) })
      p.final_amount = parseFloat(val)
      $q.notify({ type: 'positive', message: 'Сумма обновлена' })
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
    }
  })
}

async function deleteSvPayment(p) {
  $q.dialog({
    title: 'Удалить оплату?',
    message: `${p.employee_name} — ${formatMoney(p.final_amount || p.amount)}`,
    cancel: { label: 'Нет', flat: true, noCaps: true },
    ok: { label: 'Да', noCaps: true, color: 'negative' },
  }).onOk(async () => {
    try {
      await paymentsApi.delete(p.id)
      svPayments.value = svPayments.value.filter(x => x.id !== p.id)
      $q.notify({ type: 'positive', message: 'Оплата удалена' })
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
    const { public_link: publicLink, yandex_path: actualYandexPath } = await uploadToYd(file, yandexPath)
    if (cid) {
      await ax.post('/api/v1/files/', {
        contract_id: cid, stage: 'supervision',
        file_type: file.type?.includes('image') ? 'image' : 'pdf',
        public_link: publicLink, yandex_path: actualYandexPath,
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

// === Платежи клиента по надзору ===

async function addClientPayment() {
  if (!clientPayForm.value.amount || !clientPayForm.value.payment_month) {
    $q.notify({ type: 'warning', message: 'Укажите сумму и месяц' })
    return
  }
  try {
    const cardId = card.value.id
    const contractId = card.value.contract_id
    await supervisionClientPaymentsApi.create({
      supervision_card_id: cardId,
      contract_id: contractId,
      amount: Number(clientPayForm.value.amount),
      payment_month: clientPayForm.value.payment_month,
      payment_date: clientPayForm.value.payment_date || null,
    })
    showClientPayDialog.value = false
    clientPayForm.value = { amount: null, payment_month: '', payment_date: '' }
    const { data } = await supervisionClientPaymentsApi.getByCard(cardId)
    clientPayments.value = data.payments || []
    $q.notify({ type: 'positive', message: 'Платёж добавлен' })
  } catch { $q.notify({ type: 'negative', message: 'Ошибка сохранения' }) }
}

async function markClientPaymentPaid(p) {
  const today = new Date().toISOString().slice(0, 10)
  try {
    await supervisionClientPaymentsApi.update(p.id, { payment_date: today })
    p.payment_date = today
    $q.notify({ type: 'positive', message: 'Отмечено как оплачено' })
  } catch { $q.notify({ type: 'negative', message: 'Ошибка' }) }
}

async function cancelClientPaymentPaid(p) {
  try {
    await supervisionClientPaymentsApi.update(p.id, { payment_date: '' })
    p.payment_date = null
    $q.notify({ type: 'info', message: 'Отметка об оплате снята' })
  } catch { $q.notify({ type: 'negative', message: 'Ошибка' }) }
}

async function deleteClientPayment(p) {
  $q.dialog({ title: 'Удалить платёж?', message: `${formatReportMonth(p.payment_month)} — ${formatMoney(p.amount)}`, cancel: true }).onOk(async () => {
    try {
      await supervisionClientPaymentsApi.delete(p.id)
      clientPayments.value = clientPayments.value.filter(x => x.id !== p.id)
      $q.notify({ type: 'positive', message: 'Платёж удалён' })
    } catch { $q.notify({ type: 'negative', message: 'Ошибка' }) }
  })
}

async function toggleClientPaymentNotif() {
  const newVal = !clientPaymentSettings.value.notification_enabled
  try {
    const { data } = await supervisionClientPaymentsApi.updateSettings(card.value.id, { notification_enabled: newVal })
    clientPaymentSettings.value = data
    $q.notify({ type: 'info', message: newVal ? 'Уведомления включены' : 'Уведомления отключены' })
  } catch { $q.notify({ type: 'negative', message: 'Ошибка' }) }
}

function triggerClientPayReceiptUpload(paymentId) {
  clientPayReceiptId.value = paymentId
  clientPayReceiptInput.value?.click()
}

async function handleClientPayReceiptUpload(event) {
  const file = event.target.files?.[0]
  if (!file || !card.value) return
  try {
    $q.loading.show({ message: 'Загрузка чека...' })
    const contractNum = card.value.contract_number || card.value.contract_id || card.value.id
    const yandexPath = `/CRM/Чеки/${contractNum}/надзор_клиент_${clientPayReceiptId.value}_${file.name}`
    const { yandex_path: actualPath } = await uploadToYd(file, yandexPath)
    await supervisionClientPaymentsApi.update(clientPayReceiptId.value, { receipt_path: actualPath })
    const idx = clientPayments.value.findIndex(p => p.id === clientPayReceiptId.value)
    if (idx !== -1) clientPayments.value[idx].receipt_path = actualPath
    $q.notify({ type: 'positive', message: 'Чек загружен' })
  } catch { $q.notify({ type: 'negative', message: 'Ошибка загрузки чека' }) }
  finally { $q.loading.hide(); event.target.value = '' }
}

function historyIcon(type) {
  const m = { pause: 'pause_circle', resume: 'play_circle', card_moved: 'swap_horiz', assignment_change: 'person', stage_completed: 'check_circle', payment_created: 'payments', auto_resume: 'refresh', note: 'note', voice_note: 'mic', site_visit: 'directions_walk', site_visit_deleted: 'remove_circle_outline' }
  return m[type] || 'history'
}
function historyColor(type) {
  const m = { pause: 'warning', resume: 'positive', card_moved: 'primary', stage_completed: 'positive', payment_created: 'info', note: 'grey-7', voice_note: 'orange', site_visit: 'blue-7', site_visit_deleted: 'red-4' }
  return m[type] || 'grey-6'
}
function historyLabel(type) {
  const m = { pause: 'Пауза', resume: 'Возобновление', card_moved: 'Перемещение', assignment_change: 'Назначение', stage_completed: 'Стадия завершена', payment_created: 'Оплата', auto_resume: 'Авто-возобновление', note: 'Заметка', voice_note: 'Голос. заметка', site_visit: 'Выезд', site_visit_deleted: 'Удалён выезд' }
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
    const { public_link: publicLink, yandex_path: actualYp } = await uploadToYd(file, yp)
    if (cid) {
      await ax.post('/api/v1/files/', { contract_id: cid, stage, file_type: file.type?.includes('image') ? 'image' : 'pdf', public_link: publicLink, yandex_path: actualYp, file_name: file.name, file_order: 0, variation: 1 })
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
    const currentIdx = currentStageIndex.value
    if (currentIdx >= 0 && currentIdx < SUPERVISION_STAGES.length - 1) {
      await supervisionApi.moveCard(card.value.id, SUPERVISION_STAGES[currentIdx + 1])
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

async function openMonthlyRateDialog(role, employeeId, employeeName) {
  monthlyRateTarget.value = { role, employee_id: employeeId, employee_name: employeeName }
  minVisitsInput.value = card.value?.min_visits_per_month || null
  const existing = monthlyAssignments.value.find(a => a.role === role)
  if (existing) {
    monthlyRateAmount.value = existing.monthly_amount
  } else {
    // Автозаполнение из таблицы тарифов
    monthlyRateAmount.value = null
    try {
      const { api: ax } = await import('src/boot/axios')
      const { data: ratesList } = await ax.get('/api/v1/rates')
      const found = (ratesList || []).find(r => r.project_type === 'Надзор ежемесячный' && r.role === role)
      if (found?.fixed_price) monthlyRateAmount.value = found.fixed_price
    } catch {}
  }
  showMonthlyRateDialog.value = true
}

async function saveMonthlyRate() {
  if (!monthlyRateAmount.value || monthlyRateAmount.value <= 0) return
  const cardId = route.params.id
  try {
    const today = new Date().toISOString().split('T')[0]
    await supervisionApi.createMonthlyAssignment(cardId, {
      employee_id: monthlyRateTarget.value.employee_id,
      employee_name: monthlyRateTarget.value.employee_name,
      role: monthlyRateTarget.value.role,
      monthly_amount: monthlyRateAmount.value,
      city: null,
      start_date: today,
    })
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка установки ставки' })
    return
  }
  // Сохраняем мин. выездов в месяц на карточке — в отдельном try, чтобы не блокировать ставку
  const newMinVisits = minVisitsInput.value ? parseInt(minVisitsInput.value) : null
  if (newMinVisits !== (card.value?.min_visits_per_month ?? null)) {
    try {
      await supervisionApi.updateCard(cardId, { min_visits_per_month: newMinVisits })
      card.value = { ...card.value, min_visits_per_month: newMinVisits }
    } catch {
      // Не критично — ставка уже сохранена
    }
  }
  $q.notify({ type: 'positive', message: `Ежемесячная ставка ${monthlyRateAmount.value} ₽ установлена` })
  showMonthlyRateDialog.value = false
  const { data } = await supervisionApi.getMonthlyAssignments(cardId)
  monthlyAssignments.value = data || []
  // Перезагружаем выплаты чтобы сразу отобразить новую
  try {
    const { api: ax } = await import('src/boot/axios')
    const { data: payments } = await ax.get(`/api/v1/payments/by-supervision-card/${cardId}`)
    svPayments.value = payments || []
  } catch {}
}

async function deactivateMonthlyRate() {
  const cardId = route.params.id
  const a = activeMonthlyAssignment.value
  if (!a) return
  try {
    await supervisionApi.deleteMonthlyAssignment(cardId, a.id)
    $q.notify({ type: 'positive', message: 'Ежемесячная ставка деактивирована' })
    showMonthlyRateDialog.value = false
    const { data } = await supervisionApi.getMonthlyAssignments(cardId)
    monthlyAssignments.value = data || []
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка деактивации ставки' })
  }
}

onMounted(async () => {
  loadAvatars()
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
    if (existing?.is_locked && !existing.is_own_lock) {
      $q.notify({ type: 'warning', message: `Карточка редактируется: ${existing.locked_by || 'другой пользователь'}`, timeout: 5000 })
    } else {
      await locksApi.lock('supervision_card', cardId)
      svLockId.value = cardId
    }
  } catch { /* блокировки опциональны */ }
})

const svLockId = ref(null)
onBeforeUnmount(async () => {
  if (svLockId.value) {
    try { await locksApi.unlock('supervision_card', svLockId.value) } catch {}
  }
})
</script>
