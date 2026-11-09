<template>
  <q-page padding>
    <q-tabs
      v-model="tab"
      dense
      active-color="dark"
      indicator-color="accent"
      no-caps
      class="q-mb-md"
      style="color: var(--fc-text-secondary)"
      align="left"
    >
      <q-tab name="rates" label="Тарифы" />
      <q-tab name="agents" label="Агенты" />
      <q-tab name="cities" label="Города" />
      <q-tab name="roles" label="Роли" />
      <q-tab name="normdays" label="Нормодни" />
      <q-tab name="telegram" label="Telegram/Email" />
      <q-tab name="trash" label="Корзина" />
      <q-tab name="backup" label="Бекап" />

      <q-tab name="doctemplates" label="Шаблоны" />
      <q-tab name="tz-survey" label="Анкета ТЗ" />
    </q-tabs>

    <q-tab-panels v-model="tab" animated class="bg-transparent">
      <!-- ТАРИФЫ -->
      <q-tab-panel name="rates" class="q-pa-none">
        <q-tabs
          v-model="rateTab"
          dense
          active-color="dark"
          indicator-color="accent"
          no-caps
          class="q-mb-sm"
          style="color: var(--fc-text-light)"
          align="left"
        >
          <q-tab name="individual" label="Индивид." />
          <q-tab name="template" label="Шаблон." />
          <q-tab name="supervision" label="Надзор" />
          <q-tab name="supervision_monthly" label="Надзор (мес.)" />
          <q-tab name="surveyor" label="Замерщик" />
        </q-tabs>

        <q-card v-for="rate in filteredRates" :key="rate.id" class="is-card q-mb-xs">
          <q-card-section class="q-pa-sm">
            <div class="row items-center justify-between">
              <div style="flex: 1">
                <div class="text-weight-bold" style="font-size: 12px; color: var(--fc-text)">
                  {{ rate.role }}
                </div>
                <div class="text-caption" style="color: var(--fc-text-light)">
                  <span v-if="rateTab === 'individual'" style="color: #2F5496; font-weight: 600">{{ rate.project_subtype || 'все подтипы' }}</span>
                  <span v-if="rate.stage_name"> | {{ rate.stage_name }}</span>
                  <span v-if="rate.city"> | {{ rate.city }}</span>
                  <span v-if="rate.area_from"> | {{ rate.area_from }}-{{ rate.area_to }} м²</span>
                </div>
              </div>
              <div class="text-weight-bold q-mr-sm" style="color: var(--fc-text)">
                <span v-if="rate.rate_per_m2">{{ rate.rate_per_m2 }} ₽/м²</span>
                <span v-else-if="rate.fixed_price">{{ rate.fixed_price }} ₽</span>
                <span v-else-if="rate.surveyor_price">{{ rate.surveyor_price }} ₽</span>
              </div>
              <div>
                <q-btn
                  flat
                  dense
                  size="xs"
                  icon="edit"
                  color="grey-7"
                  @click="editRate(rate)"
                />
                <q-btn
                  flat
                  dense
                  size="xs"
                  icon="delete"
                  color="negative"
                  @click="deleteRate(rate)"
                />
              </div>
            </div>
          </q-card-section>
        </q-card>
        <div v-if="filteredRates.length === 0 && rateTab !== 'supervision'" class="text-center q-pa-md" style="color: var(--fc-text-muted)">
          Нет тарифов
        </div>

        <!-- =================== ВЫЕЗДЫ НАДЗОРА =================== -->
        <div v-if="rateTab === 'supervision'" class="q-mt-md q-mb-xs">
          <div class="text-caption text-weight-bold q-px-sm q-mb-xs" style="color: var(--fc-text-light); text-transform: uppercase; font-size: 11px">
            Тарифы за выезды
          </div>
          <q-card v-for="vr in visitRates" :key="'v_' + vr.id" class="is-card q-mb-xs">
            <q-card-section class="q-pa-sm">
              <div class="row items-center justify-between">
                <div style="flex: 1">
                  <div class="text-weight-bold" style="font-size: 12px; color: var(--fc-text)">
                    {{ vr.role }}
                  </div>
                  <div class="text-caption" style="color: var(--fc-text-light)">
                    {{ vr.city }}
                  </div>
                </div>
                <div class="text-weight-bold q-mr-sm" style="color: var(--fc-text)">
                  {{ vr.fixed_price }} ₽
                </div>
                <div>
                  <q-btn
                    flat
                    dense
                    size="xs"
                    icon="edit"
                    color="grey-7"
                    @click="editVisitRate(vr)"
                  />
                  <q-btn
                    flat
                    dense
                    size="xs"
                    icon="delete"
                    color="negative"
                    @click="deleteRate(vr)"
                  />
                </div>
              </div>
            </q-card-section>
          </q-card>
          <q-btn
            unelevated
            no-caps
            label="+ Добавить тариф выезда"
            style="background: var(--fc-bg-alt); color: var(--fc-text-medium); border-radius: 8px; width: 100%; margin-top: 4px"
            @click="addVisitRate"
          />
        </div>

        <!-- =================== ТАРИФЫ ПО ЗАКУПКАМ =================== -->
        <div v-if="rateTab === 'supervision'" class="q-mt-md q-mb-xs">
          <div class="text-caption text-weight-bold q-px-sm q-mb-xs" style="color: var(--fc-text-light); text-transform: uppercase; font-size: 11px">
            Тарифы исполнителя по закупкам
          </div>
          <q-card v-for="pr in purchaseRates" :key="'p_' + pr.id" class="is-card q-mb-xs">
            <q-card-section class="q-pa-sm">
              <div class="row items-center justify-between">
                <div style="flex: 1">
                  <div class="text-weight-bold" style="font-size: 12px; color: var(--fc-text)">
                    {{ pr.role }}
                  </div>
                  <div class="text-caption" style="color: var(--fc-text-light)">
                    {{ pr.stage_name || 'Все закупки' }}
                  </div>
                </div>
                <div class="text-weight-bold q-mr-sm" style="color: var(--fc-text)">
                  {{ pr.fixed_price }} ₽
                </div>
                <div>
                  <q-btn
                    flat
                    dense
                    size="xs"
                    icon="edit"
                    color="grey-7"
                    @click="editPurchaseRate(pr)"
                  />
                  <q-btn
                    flat
                    dense
                    size="xs"
                    icon="delete"
                    color="negative"
                    @click="deleteRate(pr)"
                  />
                </div>
              </div>
            </q-card-section>
          </q-card>
          <q-btn
            unelevated
            no-caps
            label="+ Добавить тариф закупки"
            style="background: var(--fc-bg-alt); color: var(--fc-text-medium); border-radius: 8px; width: 100%; margin-top: 4px"
            @click="addPurchaseRate"
          />
        </div>

        <!-- =================== ЕЖЕМЕСЯЧНЫЕ ТАРИФЫ НАДЗОРА =================== -->
        <div v-if="rateTab === 'supervision_monthly'" class="q-mt-md q-mb-xs">
          <div class="text-caption text-weight-bold q-px-sm q-mb-xs" style="color: var(--fc-text-light); text-transform: uppercase; font-size: 11px">
            Ежемесячные тарифы надзора
          </div>
          <div class="text-caption q-px-sm q-mb-sm" style="color: var(--fc-text-disabled); font-size: 11px">
            Фиксированная ставка назначается сотруднику в карточке надзора. Если город не указан — действует для всех городов.
          </div>
          <q-card v-for="mr in monthlyRates" :key="'m_' + mr.id" class="is-card q-mb-xs">
            <q-card-section class="q-pa-sm">
              <div class="row items-center justify-between">
                <div style="flex: 1">
                  <div class="text-weight-bold" style="font-size: 12px; color: var(--fc-text)">
                    {{ mr.role }}
                  </div>
                  <div class="text-caption" style="color: var(--fc-text-light)">
                    {{ mr.city || 'Все города' }}
                  </div>
                </div>
                <div class="text-weight-bold q-mr-sm" style="color: var(--fc-text)">
                  {{ mr.fixed_price }} ₽/мес.
                </div>
                <div>
                  <q-btn
                    flat
                    dense
                    size="xs"
                    icon="edit"
                    color="grey-7"
                    @click="editMonthlyRate(mr)"
                  />
                  <q-btn
                    flat
                    dense
                    size="xs"
                    icon="delete"
                    color="negative"
                    @click="deleteRate(mr)"
                  />
                </div>
              </div>
            </q-card-section>
          </q-card>
          <q-btn
            unelevated
            no-caps
            label="+ Добавить ежемесячный тариф"
            style="background: var(--fc-bg-alt); color: var(--fc-text-medium); border-radius: 8px; width: 100%; margin-top: 4px"
            @click="addMonthlyRate"
          />
        </div>

        <q-page-sticky position="bottom-right" :offset="[18, 18]">
          <q-btn
            v-if="rateTab !== 'supervision_monthly' && rateTab !== 'supervision'"
            fab
            icon="add"
            style="background: var(--fc-accent); color: var(--fc-text)"
            @click="addRate"
          />
        </q-page-sticky>
      </q-tab-panel>

      <!-- АГЕНТЫ -->
      <q-tab-panel name="agents" class="q-pa-none">
        <q-card class="is-card">
          <q-list separator>
            <q-item v-for="agent in refs.agents" :key="agent.id">
              <q-item-section avatar>
                <q-avatar size="32px" :style="{ background: agent.color || '#95A5A6' }" text-color="white">
                  {{ agent.name?.[0] }}
                </q-avatar>
              </q-item-section>
              <q-item-section style="color: var(--fc-text)">
                {{ agent.name }}
              </q-item-section>
              <q-item-section side>
                <div class="row items-center q-gutter-xs">
                  <input type="color" :value="agent.color || '#95A5A6'" style="width: 28px; height: 28px; border: none; cursor: pointer; border-radius: 4px" @change="updateAgentColor(agent, $event.target.value)">
                  <q-btn
                    flat
                    dense
                    size="xs"
                    icon="delete"
                    color="negative"
                    @click="deleteAgent(agent)"
                  />
                </div>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
        <q-page-sticky position="bottom-right" :offset="[18, 18]">
          <q-btn fab icon="add" style="background: var(--fc-accent); color: var(--fc-text)" @click="addAgent" />
        </q-page-sticky>
      </q-tab-panel>

      <!-- ГОРОДА -->
      <q-tab-panel name="cities" class="q-pa-none">
        <q-card class="is-card">
          <q-list separator>
            <q-item v-for="city in citiesFull" :key="city.id">
              <q-item-section avatar>
                <q-icon name="location_on" color="grey-7" />
              </q-item-section>
              <q-item-section style="color: var(--fc-text)">
                {{ city.name }}
              </q-item-section>
              <q-item-section side>
                <div class="row items-center q-gutter-xs">
                  <q-btn
                    flat
                    dense
                    size="xs"
                    icon="edit"
                    color="grey-7"
                    @click="editCity(city)"
                  />
                  <q-btn
                    flat
                    dense
                    size="xs"
                    icon="delete"
                    color="negative"
                    @click="deleteCity(city)"
                  />
                </div>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
        <q-page-sticky position="bottom-right" :offset="[18, 18]">
          <q-btn fab icon="add" style="background: var(--fc-accent); color: var(--fc-text)" @click="addCity" />
        </q-page-sticky>
      </q-tab-panel>

      <!-- РОЛИ — права по блокам -->
      <q-tab-panel name="roles" class="q-pa-none">
        <q-card class="is-card q-mb-md">
          <q-card-section class="q-pb-none">
            <div class="text-subtitle2 text-weight-bold" style="color: var(--fc-text)">
              Матрица ролей
            </div>
          </q-card-section>
          <q-list separator>
            <q-item
              v-for="role in rolesList"
              :key="role"
              v-ripple
              clickable
              @click="viewRolePermissions(role)"
            >
              <q-item-section avatar>
                <q-icon name="security" color="grey-7" />
              </q-item-section>
              <q-item-section style="color: var(--fc-text)">
                {{ role }}
              </q-item-section>
              <q-item-section side>
                <q-icon name="chevron_right" color="grey-5" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
      </q-tab-panel>

      <!-- НОРМОДНИ -->
      <q-tab-panel name="normdays" class="q-pa-none">
        <!-- Фильтры: тип и подтип -->
        <div class="row q-col-gutter-sm q-mb-sm">
          <div class="col-6">
            <q-select
              v-model="ndProjectType"
              :options="['Индивидуальный', 'Шаблонный']"
              label="Тип"
              outlined
              dense
              @update:model-value="onNdTypeChange"
            />
          </div>
          <div class="col-6">
            <q-select
              v-model="ndSubtype"
              :options="ndSubtypeOptions"
              label="Подтип"
              outlined
              dense
              @update:model-value="onNdSubtypeChange"
            />
          </div>
        </div>

        <!-- Блок расчёта -->
        <q-card v-if="normDays.length > 0" class="is-card q-mb-sm" flat bordered>
          <q-card-section class="q-pa-sm">
            <div class="row items-center q-gutter-sm">
              <div class="col">
                <q-input
                  v-model.number="ndArea"
                  label="Площадь, м²"
                  outlined
                  dense
                  type="number"
                  min="1"
                  @update:model-value="previewNormDays"
                />
              </div>
              <div class="col-auto text-caption" style="color: var(--fc-text-medium); line-height: 1.8">
                <div v-if="ndProjectType === 'Индивидуальный'">
                  K = <b>{{ ndK }}</b>
                </div>
                <div>Срок = <b>{{ ndContractTerm }}</b> дн.</div>
              </div>
            </div>
            <div class="text-caption q-mt-xs nd-formula-hint">
              <template v-if="ndProjectType === 'Индивидуальный'">
                <div><b>Норм-дни = base + K × mult</b></div>
                <div>· <b>base</b> — базовые дни этапа, не зависят от площади</div>
                <div>· <b>mult</b> — прибавка за каждые 100 м² сверх первых 100 м²</div>
                <div>· <b>K</b> = ⌊(площадь − 1) ÷ 100⌋ → ≤100 м²: K=0 · 101–200: K=1 · 201–300: K=2</div>
                <div>Итоговые дни распределяются пропорционально в рамках срока договора</div>
              </template>
              <template v-else>
                <template v-if="ndSubtype && ndSubtype.toLowerCase().includes('ванн')">
                  <div><b>Ванная комната — фиксированный срок:</b></div>
                  <div>· Без визуализации: 10 рабочих дней</div>
                  <div>· С визуализацией: 20 рабочих дней</div>
                  <div>Нормодни распределяются пропорционально в рамках этого срока</div>
                </template>
                <template v-else>
                  <div><b>Стандарт — срок нарастает с площадью:</b></div>
                  <div>· до 90 м²: 20 рабочих дней</div>
                  <div>· за каждые 50 м² сверх 90 → +10 дней (91–140: 30 дн., 141–190: 40 дн., …)</div>
                  <template v-if="ndSubtype && ndSubtype.toLowerCase().includes('визуализ')">
                    <div>· визуализация: +25 дней базово; за каждые 50 м² сверх 90 → ещё +15 дней</div>
                  </template>
                  <div>· этажность: +10 дн. за каждый доп. этаж (с визуализацией +20 дн.)</div>
                  <div>Нормодни каждого этапа пропорциональны общему сроку</div>
                </template>
              </template>
            </div>
          </q-card-section>
        </q-card>

        <!-- Кнопки действий -->
        <div v-if="normDays.length > 0" class="row q-gutter-xs q-mb-sm">
          <template v-if="!ndEditMode">
            <button type="button" class="nd-btn" @click="enterEditMode">
              <q-icon name="edit" size="14px" /> Редактировать
            </button>
            <button type="button" class="nd-btn nd-btn-reset" @click="resetNormDays">
              <q-icon name="restore" size="14px" /> Сбросить к формулам
            </button>
          </template>
          <template v-else>
            <button type="button" class="nd-btn nd-btn-save" :disabled="ndSaving" @click="saveNormDays">
              <q-spinner v-if="ndSaving" size="14px" /><q-icon v-else name="save" size="14px" /> Сохранить
            </button>
            <button type="button" class="nd-btn nd-btn-cancel" @click="cancelEdit">
              Отмена
            </button>
          </template>
          <!-- Экспорт -->
          <div style="flex: 1" />
          <button type="button" class="nd-btn nd-btn-export" title="Скачать Excel" @click="exportNormDaysExcel">
            <q-icon name="table_view" size="14px" /> Excel
          </button>
          <button type="button" class="nd-btn nd-btn-export" title="Скачать PDF" @click="exportNormDaysPdf">
            <q-icon name="picture_as_pdf" size="14px" /> PDF
          </button>
        </div>

        <!-- Таблица нормодней, сгруппированная по стадиям -->
        <div v-if="ndLoading" class="text-center q-pa-md">
          <q-spinner size="30px" color="accent" />
        </div>
        <template v-else-if="normDays.length > 0">
          <q-card v-for="group in normDaysGrouped" :key="group.key" class="is-card q-mb-sm">
            <div class="nd-group-header">
              {{ group.name }}
            </div>
            <q-list dense separator>
              <template v-for="nd in group.items" :key="nd.stage_code">
                <!-- Заголовок подэтапа -->
                <q-item v-if="nd.executor_role === 'header'" class="nd-subheader">
                  <q-item-section>
                    <q-item-label class="text-weight-bold" style="font-size: 11px; color: var(--fc-text-medium)">
                      {{ nd.stage_name }}
                    </q-item-label>
                  </q-item-section>
                </q-item>
                <!-- Запись нормодней -->
                <q-item v-else :class="{ 'nd-out-of-scope': !nd.is_in_contract_scope }">
                  <q-item-section>
                    <q-item-label style="font-size: 11px; color: var(--fc-text)">
                      {{ nd.stage_name }}
                    </q-item-label>
                    <q-item-label caption style="color: var(--fc-text-light)">
                      {{ nd.executor_role }}<span v-if="!nd.is_in_contract_scope" style="color: #e74c3c"> · вне объёма</span>
                    </q-item-label>
                  </q-item-section>
                  <!-- Просмотр -->
                  <q-item-section v-if="!ndEditMode" side style="text-align: right; min-width: 72px">
                    <div class="text-weight-bold" style="font-size: 12px; color: var(--fc-text)">
                      {{ ndPreviewMap[nd.stage_code] !== undefined ? ndPreviewMap[nd.stage_code] : (nd.base_norm_days ?? '—') }} дн.
                    </div>
                    <div v-if="ndProjectType === 'Индивидуальный' && nd.k_multiplier > 0" class="text-caption" style="color: var(--fc-text-disabled); font-size: 9px">
                      {{ nd.base_norm_days }} + {{ nd.k_multiplier }}×K
                    </div>
                  </q-item-section>
                  <!-- Редактирование -->
                  <q-item-section v-else side style="min-width: 130px">
                    <div class="row q-gutter-xs no-wrap items-center">
                      <q-input
                        v-model.number="ndEditMap[nd.stage_code].base_norm_days"
                        dense
                        outlined
                        type="number"
                        label="Дни"
                        style="width: 58px"
                      />
                      <q-input
                        v-if="ndProjectType === 'Индивидуальный'"
                        v-model.number="ndEditMap[nd.stage_code].k_multiplier"
                        dense
                        outlined
                        type="number"
                        label="×K"
                        style="width: 48px"
                      />
                    </div>
                  </q-item-section>
                </q-item>
              </template>
            </q-list>
          </q-card>
          <!-- ИТОГО -->
          <q-card class="is-card q-mt-xs">
            <q-card-section class="q-pa-sm">
              <div class="row items-center justify-between q-mb-xs">
                <div class="text-weight-bold" style="font-size: 12px; color: var(--fc-text)">
                  Итого по договору
                </div>
                <div class="text-weight-bold" style="font-size: 14px; color: var(--fc-text)">
                  {{ ndContractTerm }} дн.
                </div>
              </div>
              <div class="row items-center justify-between">
                <div class="text-caption" style="color: var(--fc-text-light)">
                  Итого с учётом вне объёма
                </div>
                <div class="text-caption text-weight-bold" style="color: var(--fc-text-light)">
                  {{ ndTotalAll }} дн.
                </div>
              </div>
            </q-card-section>
          </q-card>
        </template>
        <q-card v-else class="is-card">
          <q-card-section class="text-center" style="color: var(--fc-text-muted)">
            Выберите тип и подтип проекта
          </q-card-section>
        </q-card>
      </q-tab-panel>

      <!-- TELEGRAM / EMAIL -->
      <q-tab-panel name="telegram" class="q-pa-none">
        <!-- Индикатор загрузки -->
        <div v-if="settingsLoading" class="row justify-center q-py-lg">
          <q-spinner color="yellow-8" size="32px" />
        </div>

        <template v-else>
          <!-- Статус сервисов -->
          <q-card v-if="messengerStatus" class="is-card q-mb-md">
            <q-card-section class="q-py-sm">
              <div class="row q-gutter-md">
                <div class="row items-center q-gutter-xs">
                  <q-icon
                    :name="messengerStatus.telegram_bot_available ? 'check_circle' : 'cancel'"
                    :color="messengerStatus.telegram_bot_available ? 'positive' : 'negative'"
                    size="18px"
                  />
                  <span style="font-size: 12px">Бот</span>
                </div>
                <div class="row items-center q-gutter-xs">
                  <q-icon
                    :name="messengerStatus.telegram_mtproto_available ? 'check_circle' : 'cancel'"
                    :color="messengerStatus.telegram_mtproto_available ? 'positive' : 'negative'"
                    size="18px"
                  />
                  <span style="font-size: 12px">MTProto</span>
                </div>
                <div class="row items-center q-gutter-xs">
                  <q-icon
                    :name="messengerStatus.email_available ? 'check_circle' : 'cancel'"
                    :color="messengerStatus.email_available ? 'positive' : 'negative'"
                    size="18px"
                  />
                  <span style="font-size: 12px">Email</span>
                </div>
              </div>
            </q-card-section>
          </q-card>

          <!-- Внутренние вкладки -->
          <q-tabs
            v-model="settingsSubTab"
            dense
            no-caps
            align="left"
            class="q-mb-md"
            style="border-bottom: 2px solid var(--fc-border-light)"
            active-color="yellow-9"
            indicator-color="yellow-8"
          >
            <q-tab name="telegram" label="Telegram" />
            <q-tab name="smtp" label="Email (SMTP)" />
            <q-tab name="welcome" label="Welcome письма" />
            <q-tab name="invites" label="Приглашения" />
          </q-tabs>

          <q-tab-panels v-model="settingsSubTab" animated>
            <!-- ─── Telegram бот ─── -->
            <q-tab-panel name="telegram" class="q-pa-none">
              <q-card class="is-card q-mb-md">
                <q-card-section>
                  <div class="text-subtitle2 text-weight-bold q-mb-md" style="color: var(--fc-text)">
                    Настройки Telegram бота
                  </div>

                  <q-input
                    v-model="messengerSettings.telegram_bot_token"
                    :type="showBotToken ? 'text' : 'password'"
                    label="Bot Token"
                    outlined
                    dense
                    class="q-mb-sm"
                  >
                    <template #append>
                      <q-icon
                        :name="showBotToken ? 'visibility_off' : 'visibility'"
                        class="cursor-pointer"
                        @click="showBotToken = !showBotToken"
                      />
                    </template>
                  </q-input>

                  <q-input
                    v-model="messengerSettings.telegram_api_id"
                    label="API ID"
                    outlined
                    dense
                    class="q-mb-sm"
                  />

                  <q-input
                    v-model="messengerSettings.telegram_api_hash"
                    :type="showApiHash ? 'text' : 'password'"
                    label="API Hash"
                    outlined
                    dense
                    class="q-mb-sm"
                  >
                    <template #append>
                      <q-icon
                        :name="showApiHash ? 'visibility_off' : 'visibility'"
                        class="cursor-pointer"
                        @click="showApiHash = !showApiHash"
                      />
                    </template>
                  </q-input>

                  <q-input
                    v-model="messengerSettings.telegram_phone"
                    label="Номер телефона (+7...)"
                    outlined
                    dense
                    class="q-mb-md"
                  />

                  <!-- MTProto авторизация -->
                  <div class="text-caption text-weight-bold q-mb-sm" style="color: var(--fc-text-medium)">
                    MTProto авторизация
                  </div>
                  <div v-if="!mtprotoCodeSent">
                    <q-btn
                      unelevated
                      no-caps
                      label="Отправить код подтверждения"
                      icon="sms"
                      style="background: #2AABEE; color: white; border-radius: 4px"
                      class="full-width"
                      @click="mtprotoSendCode"
                    />
                  </div>
                  <div v-else>
                    <q-input
                      v-model="mtprotoCode"
                      label="Код из Telegram"
                      outlined
                      dense
                      class="q-mb-sm"
                      @keyup.enter="mtprotoVerifyCode"
                    />
                    <div class="row q-gutter-sm">
                      <q-btn
                        unelevated
                        no-caps
                        flex-1
                        label="Подтвердить"
                        icon="check"
                        style="background: #27AE60; color: white; border-radius: 4px"
                        :loading="mtprotoVerifying"
                        @click="mtprotoVerifyCode"
                      />
                      <q-btn
                        flat
                        no-caps
                        label="Получить SMS"
                        style="border-radius: 4px"
                        @click="mtprotoResendSms"
                      />
                    </div>
                  </div>
                </q-card-section>
              </q-card>

              <q-card class="is-card q-mb-md">
                <q-card-section>
                  <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: var(--fc-text)">
                    Тестовое уведомление
                  </div>
                  <q-btn
                    unelevated
                    no-caps
                    label="Отправить тестовое уведомление"
                    icon="send"
                    style="background: var(--fc-accent); color: var(--fc-text); border-radius: 4px"
                    class="full-width"
                    @click="sendTestNotification"
                  />
                </q-card-section>
              </q-card>

              <div class="row justify-end q-mt-md">
                <q-btn
                  unelevated
                  no-caps
                  label="Сохранить настройки Telegram"
                  icon="save"
                  style="background: var(--fc-accent); color: var(--fc-text); border-radius: 4px"
                  :loading="settingsSaving"
                  @click="saveMessengerSettings"
                />
              </div>
            </q-tab-panel>

            <!-- ─── Email SMTP ─── -->
            <q-tab-panel name="smtp" class="q-pa-none">
              <q-card class="is-card q-mb-md">
                <q-card-section>
                  <div class="text-subtitle2 text-weight-bold q-mb-md" style="color: var(--fc-text)">
                    Настройки SMTP
                  </div>

                  <q-input
                    v-model="messengerSettings.smtp_host"
                    label="SMTP Host"
                    outlined
                    dense
                    class="q-mb-sm"
                  />
                  <q-input
                    v-model="messengerSettings.smtp_port"
                    label="SMTP Port"
                    outlined
                    dense
                    class="q-mb-sm"
                    type="number"
                  />
                  <q-input
                    v-model="messengerSettings.smtp_username"
                    label="Логин (email)"
                    outlined
                    dense
                    class="q-mb-sm"
                  />

                  <q-input
                    v-model="messengerSettings.smtp_password"
                    :type="showSmtpPassword ? 'text' : 'password'"
                    label="Пароль"
                    outlined
                    dense
                    class="q-mb-sm"
                  >
                    <template #append>
                      <q-icon
                        :name="showSmtpPassword ? 'visibility_off' : 'visibility'"
                        class="cursor-pointer"
                        @click="showSmtpPassword = !showSmtpPassword"
                      />
                    </template>
                  </q-input>

                  <q-toggle
                    v-model="messengerSettings.smtp_use_tls"
                    :true-value="'true'"
                    :false-value="'false'"
                    label="Использовать TLS"
                    class="q-mb-sm"
                    color="yellow-8"
                  />

                  <q-input
                    v-model="messengerSettings.smtp_from_name"
                    label="Имя отправителя"
                    outlined
                    dense
                    class="q-mb-sm"
                  />
                  <q-input
                    v-model="messengerSettings.app_download_url"
                    label="Ссылка на мобильную версию CRM"
                    outlined
                    dense
                    class="q-mb-sm"
                  />
                  <q-input v-model="messengerSettings.review_link" label="Ссылка для отзыва" outlined dense />
                </q-card-section>
              </q-card>

              <div class="row justify-end q-mt-md">
                <q-btn
                  unelevated
                  no-caps
                  label="Сохранить настройки Email"
                  icon="save"
                  style="background: var(--fc-accent); color: var(--fc-text); border-radius: 4px"
                  :loading="settingsSaving"
                  @click="saveMessengerSettings"
                />
              </div>
            </q-tab-panel>

            <!-- ─── Welcome письма ─── -->
            <q-tab-panel name="welcome" class="q-pa-none">
              <q-card class="is-card q-mb-md">
                <q-card-section>
                  <div class="text-subtitle2 text-weight-bold q-mb-md" style="color: var(--fc-text)">
                    Welcome письма
                  </div>

                  <!-- Письмо сотруднику -->
                  <div class="text-caption text-weight-bold q-mb-xs" style="color: var(--fc-text-medium)">
                    Письмо сотруднику
                  </div>
                  <div class="text-caption q-mb-sm" style="color: var(--fc-text-light)">
                    Отправляется новому сотруднику при добавлении в систему. Содержит логин, пароль и ссылку на Telegram-бот.
                  </div>
                  <div class="row q-gutter-sm q-mb-lg">
                    <q-btn
                      unelevated
                      no-caps
                      label="Просмотр"
                      icon="visibility"
                      style="background: var(--fc-bg-alt); color: var(--fc-text); border: 1px solid var(--fc-border); border-radius: 4px"
                      @click="previewEmail('employee')"
                    />
                    <q-btn
                      unelevated
                      no-caps
                      label="Редактировать"
                      icon="edit"
                      style="background: var(--fc-accent); color: var(--fc-text); border-radius: 4px"
                      @click="editEmail('employee')"
                    />
                  </div>

                  <!-- Письмо клиенту -->
                  <div class="text-caption text-weight-bold q-mb-xs" style="color: var(--fc-text-medium)">
                    Приглашение клиенту
                  </div>
                  <div class="text-caption q-mb-sm" style="color: var(--fc-text-light)">
                    Отправляется клиенту при создании проектного Telegram-чата. Содержит ссылку-приглашение и данные проекта.
                  </div>
                  <div class="row q-gutter-sm">
                    <q-btn
                      unelevated
                      no-caps
                      label="Просмотр"
                      icon="visibility"
                      style="background: var(--fc-bg-alt); color: var(--fc-text); border: 1px solid var(--fc-border); border-radius: 4px"
                      @click="previewEmail('client')"
                    />
                    <q-btn
                      unelevated
                      no-caps
                      label="Редактировать"
                      icon="edit"
                      style="background: var(--fc-accent); color: var(--fc-text); border-radius: 4px"
                      @click="editEmail('client')"
                    />
                  </div>
                </q-card-section>
              </q-card>
            </q-tab-panel>

            <!-- ─── Приглашения ─── -->
            <q-tab-panel name="invites" class="q-pa-none">
              <q-card class="is-card q-mb-md">
                <q-card-section>
                  <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: var(--fc-text)">
                    Приглашения сотрудникам
                  </div>
                  <div class="text-caption q-mb-md" style="color: var(--fc-text-light)">
                    Отправить welcome-email с ссылкой на Telegram бот и временным паролем
                  </div>
                  <q-select
                    v-model="inviteEmployeeId"
                    :options="inviteEmployeeOpts"
                    label="Сотрудник"
                    outlined
                    dense
                    emit-value
                    map-options
                    class="q-mb-sm"
                  />
                  <q-btn
                    unelevated
                    no-caps
                    label="Отправить приглашение"
                    icon="mail"
                    style="background: #27AE60; color: white; border-radius: 4px"
                    class="full-width"
                    :disable="!inviteEmployeeId"
                    @click="sendInvite"
                  />
                </q-card-section>
              </q-card>

              <!-- Токены сотрудников для ручного подключения -->
              <q-card class="is-card q-mb-md">
                <q-card-section>
                  <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: var(--fc-text)">
                    Telegram-токены сотрудников
                  </div>
                  <div class="text-caption q-mb-md" style="color: var(--fc-text-light)">
                    Если сотрудник не может открыть ссылку — отправьте ему инструкцию вручную
                  </div>
                  <q-select
                    v-model="tgInfoEmployeeId"
                    :options="inviteEmployeeOpts"
                    label="Выберите сотрудника"
                    outlined
                    dense
                    emit-value
                    map-options
                    class="q-mb-sm"
                    @update:model-value="loadTgInfo"
                  />
                  <template v-if="tgInfo">
                    <q-card flat bordered class="q-pa-sm q-mb-sm" style="border-radius: 8px">
                      <div class="row items-center q-mb-xs">
                        <q-icon
                          :name="tgInfo.telegram_connected ? 'check_circle' : 'radio_button_unchecked'"
                          :color="tgInfo.telegram_connected ? 'positive' : 'warning'"
                          size="20px"
                          class="q-mr-xs"
                        />
                        <span style="font-size: 12px; color: var(--fc-text)">{{ tgInfo.telegram_connected ? 'Telegram подключён' : 'Не подключён' }}</span>
                      </div>
                      <template v-if="tgInfo.token_command">
                        <div class="text-caption q-mb-xs" style="color: var(--fc-text-light)">
                          Инструкция для сотрудника:
                        </div>
                        <div style="background: var(--fc-bg-alt); border-radius: 6px; padding: 8px; font-family: monospace; font-size: 11px; color: var(--fc-text); word-break: break-all">
                          Откройте Telegram → найдите бота @festival_color_crm_bot → отправьте:<br>
                          <strong>{{ tgInfo.token_command }}</strong>
                        </div>
                        <div class="row q-gutter-xs q-mt-sm">
                          <q-btn
                            flat
                            dense
                            size="sm"
                            icon="content_copy"
                            label="Копировать команду"
                            no-caps
                            color="grey-7"
                            @click="copyToClipboard(tgInfo.token_command)"
                          />
                          <q-btn
                            flat
                            dense
                            size="sm"
                            icon="link"
                            label="Копировать tg://"
                            no-caps
                            color="grey-7"
                            @click="copyToClipboard(tgInfo.tg_link)"
                          />
                        </div>
                      </template>
                      <div v-else class="text-caption" style="color: var(--fc-text-muted)">
                        {{ tgInfo.telegram_connected ? 'Уже подключён, токен не нужен' : 'Токен не создан — отправьте приглашение' }}
                      </div>
                    </q-card>
                  </template>
                </q-card-section>
              </q-card>
            </q-tab-panel>
          </q-tab-panels>
        </template>
      </q-tab-panel>

      <!-- КОРЗИНА ДОГОВОРОВ -->
      <q-tab-panel name="trash" class="q-pa-none">
        <div class="row items-center justify-between q-mb-sm">
          <div class="text-subtitle2 text-weight-bold" style="color: var(--fc-text)">
            Удалённые договоры
          </div>
          <q-btn
            flat
            dense
            no-caps
            size="sm"
            icon="refresh"
            label="Обновить"
            color="grey-7"
            :loading="trashLoading"
            @click="loadTrash"
          />
        </div>

        <div v-if="trashLoading" class="text-center q-pa-lg">
          <q-spinner size="32px" color="grey-5" />
        </div>

        <div v-else-if="deletedContracts.length === 0" class="text-center q-pa-xl" style="color: var(--fc-text-disabled)">
          <q-icon name="delete_outline" size="48px" class="q-mb-sm" />
          <div>Корзина пуста</div>
        </div>

        <template v-else>
          <q-card v-for="item in deletedContracts" :key="item.id" class="is-card q-mb-xs">
            <q-card-section class="q-pa-sm">
              <div class="row items-start justify-between no-wrap" style="gap: 8px">
                <div class="col-grow" style="min-width: 0">
                  <div class="text-weight-bold" style="font-size: 13px; color: var(--fc-text)">
                    № {{ item.contract_number || '—' }} · {{ item.client_name }}
                  </div>
                  <div class="text-caption" style="color: var(--fc-text-light)">
                    {{ item.address }} · {{ item.project_type }}
                    <span v-if="item.project_subtype"> ({{ item.project_subtype }})</span>
                  </div>
                  <div class="text-caption" style="color: var(--fc-text-disabled); font-size: 10px; margin-top: 2px">
                    Удалён: {{ formatTrashDate(item.deleted_at) }}
                  </div>
                </div>
                <div class="column" style="gap: 4px; flex-shrink: 0">
                  <q-btn
                    dense
                    unelevated
                    no-caps
                    size="sm"
                    color="positive"
                    label="Восстановить"
                    style="min-width: 110px"
                    :loading="item._loading"
                    @click="restoreContract(item)"
                  />
                  <q-btn
                    dense
                    unelevated
                    no-caps
                    size="sm"
                    color="negative"
                    label="Удалить навсегда"
                    style="min-width: 110px"
                    @click="permanentDeleteContract(item)"
                  />
                </div>
              </div>
            </q-card-section>
          </q-card>
        </template>
      </q-tab-panel>

      <!-- БЕКАП -->
      <q-tab-panel name="backup" class="q-pa-none">
        <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: var(--fc-text)">
          Резервное копирование БД
        </div>

        <!-- Статус / кнопка запуска -->
        <q-card class="is-card q-mb-md">
          <q-card-section class="q-pa-sm">
            <div class="row items-center justify-between q-mb-sm">
              <div>
                <div style="font-size: 13px; font-weight: 600; color: var(--fc-text)">
                  PostgreSQL → Яндекс.Диск
                </div>
                <div class="text-caption" style="color: var(--fc-text-light)">
                  disk:/CRM/Бэкапы/PostgreSQL/
                </div>
              </div>
              <q-btn
                unelevated
                no-caps
                icon="backup"
                label="Создать бекап"
                color="primary"
                size="sm"
                :loading="backupInProgress"
                :disable="backupInProgress"
                @click="startBackup"
              />
            </div>

            <!-- Результат последнего бекапа -->
            <div v-if="lastBackup" class="q-mt-xs">
              <div
                v-if="lastBackup.status === 'success'"
                class="rounded-borders q-pa-xs"
                style="background: var(--fc-state-success-bg); color: #2E7D32; font-size: 12px"
              >
                <q-icon name="check_circle" size="14px" class="q-mr-xs" />
                {{ lastBackup.filename }} · {{ lastBackup.size_mb }} МБ
              </div>
              <div
                v-else-if="lastBackup.status === 'error'"
                class="rounded-borders q-pa-xs"
                style="background: #FFEBEE; color: #C62828; font-size: 12px"
              >
                <q-icon name="error" size="14px" class="q-mr-xs" />
                Ошибка: {{ lastBackup.error }}
              </div>
              <div v-if="backupInProgress" class="text-caption q-mt-xs" style="color: var(--fc-text-light)">
                <q-spinner size="12px" class="q-mr-xs" />Бекап выполняется...
              </div>
            </div>
          </q-card-section>
        </q-card>

        <!-- Список существующих бекапов -->
        <div class="row items-center justify-between q-mb-xs">
          <div class="text-caption text-weight-bold" style="color: var(--fc-text-light); text-transform: uppercase">
            Бекапы на Яндекс.Диске
          </div>
          <q-btn
            flat
            dense
            no-caps
            size="xs"
            icon="refresh"
            color="grey-7"
            :loading="backupsLoading"
            @click="loadBackupList"
          />
        </div>

        <div v-if="backupsLoading" class="text-center q-pa-md">
          <q-spinner size="24px" color="grey-5" />
        </div>
        <div v-else-if="backupList.length === 0" class="text-center q-pa-md" style="color: var(--fc-text-disabled); font-size: 13px">
          Бекапов нет
        </div>
        <q-card v-else class="is-card">
          <q-list dense separator>
            <q-item v-for="b in backupList" :key="b.name">
              <q-item-section avatar>
                <q-icon name="storage" color="blue-7" size="20px" />
              </q-item-section>
              <q-item-section>
                <q-item-label style="font-size: 12px; color: var(--fc-text)">
                  {{ b.name }}
                </q-item-label>
                <q-item-label caption>
                  {{ formatBackupSize(b.size) }} · {{ formatBackupDate(b.modified) }}
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-btn
                  flat
                  round
                  icon="restore"
                  color="orange-7"
                  size="sm"
                  :disable="restoreInProgress || backupInProgress"
                  :loading="restoreInProgress && restoreTarget === b.name"
                  @click="confirmRestore(b.name)"
                >
                  <q-tooltip>Восстановить из этого бекапа</q-tooltip>
                </q-btn>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>

        <!-- Статус восстановления -->
        <div v-if="restoreInProgress" class="q-mt-sm q-pa-sm" style="background: #fff3e0; border-radius: 8px; border: 1px solid #ffcc80">
          <div class="row items-center no-wrap q-gutter-xs">
            <q-spinner size="16px" color="orange-7" />
            <span style="font-size: 13px; color: #e65100">Восстановление БД... не закрывайте страницу</span>
          </div>
        </div>
        <div v-if="lastRestore" class="q-mt-sm q-pa-sm" style="border-radius: 8px; border: 1px solid" :style="lastRestore.status === 'success' ? 'background:var(--fc-state-success-bg);border-color:#a5d6a7' : 'background:#ffebee;border-color:#ef9a9a'">
          <div v-if="lastRestore.status === 'success'" style="font-size: 13px; color: #2e7d32">
            ✓ Восстановление завершено: {{ lastRestore.filename }}
          </div>
          <div v-else style="font-size: 13px; color: #c62828">
            ✗ Ошибка восстановления: {{ lastRestore.error }}
          </div>
        </div>
      </q-tab-panel>


      <!-- Вкладка Шаблоны договоров -->
      <q-tab-panel name="doctemplates" class="q-pa-sm">
        <!-- Памятка по шаблонам -->
        <q-expansion-item
          dense
          icon="help_outline"
          label="Как подготовить шаблон"
          header-style="font-size:13px; font-weight:600; color: var(--fc-primary); padding: 4px 8px"
          class="q-mb-md"
          style="border: 1px solid var(--fc-border); border-radius: 8px; background: var(--fc-surface)"
        >
          <div class="q-pa-sm" style="font-size: 12px; color: var(--fc-text-light); line-height: 1.6">
            <div style="font-weight:600; color: var(--fc-text); margin-bottom: 4px">
              Форматы файлов
            </div>
            <div class="q-mb-sm">
              Поддерживаются <b>.docx</b>, <b>.dotx</b>, <b>.doc</b>
              (Word 2007 и новее). Рекомендуется <b>.docx</b>.
              Для реквизитов (подпись, печать) — <b>.png</b>, <b>.jpg</b>, <b>.webp</b>.
            </div>

            <div style="font-weight:600; color: var(--fc-text); margin-bottom: 4px">
              Текстовые теги
            </div>
            <div class="q-mb-xs">
              Вставляйте в текст шаблона двойными фигурными скобками: <code style="background:#f5f5f5;padding:1px 4px;border-radius:3px">&#123;&#123;ТЕГ&#125;&#125;</code>
            </div>
            <table style="width:100%; border-collapse:collapse; font-size:11px" class="q-mb-sm">
              <thead>
                <tr style="background: var(--fc-bg-alt)">
                  <th style="text-align:left; padding:3px 6px; border-bottom:1px solid var(--fc-border)">
                    Тег
                  </th>
                  <th style="text-align:left; padding:3px 6px; border-bottom:1px solid var(--fc-border)">
                    Подставляется
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="tag in templateTags"
                  :key="tag.tag"
                  style="border-bottom:1px solid var(--fc-border-light)"
                >
                  <td style="padding:2px 6px; white-space:nowrap">
                    <code style="background:#e8f5e9;color:#2e7d32;padding:1px 4px;border-radius:3px">
                      &#123;&#123;{{ tag.tag }}&#125;&#125;
                    </code>
                  </td>
                  <td style="padding:2px 6px; color: var(--fc-text)">
                    {{ tag.desc }}
                  </td>
                </tr>
              </tbody>
            </table>

            <div style="font-weight:600; color: var(--fc-text); margin-bottom: 4px">
              Теги изображений
            </div>
            <div class="q-mb-xs">
              Строка в шаблоне должна содержать <b>только</b> тег — изображение вставится на его место.
            </div>
            <table style="width:100%; border-collapse:collapse; font-size:11px">
              <thead>
                <tr style="background: var(--fc-bg-alt)">
                  <th style="text-align:left; padding:3px 6px; border-bottom:1px solid var(--fc-border)">
                    Тег
                  </th>
                  <th style="text-align:left; padding:3px 6px; border-bottom:1px solid var(--fc-border)">
                    Вставляется
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr style="border-bottom:1px solid var(--fc-border-light)">
                  <td style="padding:2px 6px">
                    <code style="background:#e3f2fd;color:#1565c0;padding:1px 4px;border-radius:3px">&#123;&#123;ПОДПИСЬ&#125;&#125;</code>
                  </td>
                  <td style="padding:2px 6px">
                    Подпись директора (без расшифровки)
                  </td>
                </tr>
                <tr style="border-bottom:1px solid var(--fc-border-light)">
                  <td style="padding:2px 6px">
                    <code style="background:#e3f2fd;color:#1565c0;padding:1px 4px;border-radius:3px">&#123;&#123;ПОДПИСЬ_РАСШ&#125;&#125;</code>
                  </td>
                  <td style="padding:2px 6px">
                    Подпись с расшифровкой ФИО
                  </td>
                </tr>
                <tr style="border-bottom:1px solid var(--fc-border-light)">
                  <td style="padding:2px 6px">
                    <code style="background:#e3f2fd;color:#1565c0;padding:1px 4px;border-radius:3px">&#123;&#123;ПЕЧАТЬ&#125;&#125;</code>
                  </td>
                  <td style="padding:2px 6px">
                    Печать организации
                  </td>
                </tr>
                <tr>
                  <td style="padding:2px 6px">
                    <code style="background:#e3f2fd;color:#1565c0;padding:1px 4px;border-radius:3px">&#123;&#123;ЛОГО_АГЕНТА&#125;&#125;</code>
                  </td>
                  <td style="padding:2px 6px">
                    Логотип агента (подставляется автоматически по агенту договора)
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </q-expansion-item>

        <!-- Реквизиты компании -->
        <div style="font-size: 14px; font-weight: 600; color: var(--fc-text); margin-bottom: 8px">
          Реквизиты компании
        </div>
        <q-card flat bordered class="q-mb-md" style="border-radius: 8px; overflow: hidden">
          <div
            v-for="(req, idx) in requisiteSlots"
            :key="req.type"
            class="tmpl-row"
            :style="idx < requisiteSlots.length - 1 ? 'border-bottom: 1px solid var(--fc-border-light)' : ''"
          >
            <span class="tmpl-label">{{ req.label }}</span>
            <span class="tmpl-dots" />
            <div class="tmpl-right">
              <template v-if="requisites[req.type]">
                <q-icon name="check_circle" color="positive" size="16px" />
                <span class="tmpl-filename">{{ requisites[req.type].file_name }}</span>
                <q-btn
                  flat
                  round
                  dense
                  icon="delete"
                  color="negative"
                  size="xs"
                  @click="deleteRequisite(req.type)"
                />
              </template>
              <span v-else class="tmpl-empty">Не загружено</span>
              <q-btn
                outline
                size="sm"
                :label="requisites[req.type] ? 'Заменить' : 'Загрузить'"
                color="primary"
                class="tmpl-btn"
                @click="triggerRequisiteUpload(req.type)"
              />
              <input
                :ref="el => requisiteInputs[req.type] = el"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                style="display:none"
                @change="e => onRequisiteFileSelected(req.type, e)"
              >
            </div>
          </div>
        </q-card>

        <!-- Логотипы агентов -->
        <div style="font-size: 14px; font-weight: 600; color: var(--fc-text); margin-bottom: 8px">
          Логотипы агентов
        </div>
        <div class="q-mb-xs" style="font-size:12px; color:var(--fc-text-secondary)">
          Используйте тег
          <code style="background:#e3f2fd;color:#1565c0;padding:1px 4px;border-radius:3px">&#123;&#123;ЛОГО_АГЕНТА&#125;&#125;</code>
          в шаблоне — логотип подставится автоматически по агенту договора.
        </div>
        <q-card flat bordered class="q-mb-md" style="border-radius: 8px; overflow: hidden">
          <div
            v-for="(logo, idx) in agentLogoSlots"
            :key="logo.type"
            class="tmpl-row"
            :style="idx < agentLogoSlots.length - 1 ? 'border-bottom: 1px solid var(--fc-border-light)' : ''"
          >
            <span class="tmpl-label">{{ logo.label }}</span>
            <span class="tmpl-dots" />
            <div class="tmpl-right">
              <template v-if="requisites[logo.type]">
                <q-icon name="check_circle" color="positive" size="16px" />
                <span class="tmpl-filename">{{ requisites[logo.type].file_name }}</span>
                <q-btn
                  flat
                  round
                  dense
                  icon="delete"
                  color="negative"
                  size="xs"
                  @click="deleteRequisite(logo.type)"
                />
              </template>
              <span v-else class="tmpl-empty">Не загружено</span>
              <q-btn
                outline
                size="sm"
                :label="requisites[logo.type] ? 'Заменить' : 'Загрузить'"
                color="primary"
                class="tmpl-btn"
                @click="triggerRequisiteUpload(logo.type)"
              />
              <input
                :ref="el => requisiteInputs[logo.type] = el"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                style="display:none"
                @change="e => onRequisiteFileSelected(logo.type, e)"
              >
            </div>
          </div>
          <div v-if="agentLogoSlots.length === 0" class="q-pa-md text-caption text-grey">
            Агенты не найдены — добавьте агентов на вкладке «Агенты»
          </div>
        </q-card>

        <!-- Шаблоны по типам проектов — вкладки Физ. лица / Юр. лица -->
        <div class="q-mb-sm">
          <q-tabs
            v-model="activeClientType"
            dense
            align="left"
            active-color="primary"
            indicator-color="primary"
            class="q-mb-md"
            style="border-bottom: 1px solid var(--fc-border-light)"
          >
            <q-tab name="физ" label="Физ. лица" />
            <q-tab name="юр" label="Юр. лица" />
          </q-tabs>
        </div>
        <div v-for="pt in projectTypeSlots" :key="pt.type" class="q-mb-md">
          <div style="font-size: 14px; font-weight: 600; color: var(--fc-text); margin-bottom: 6px">
            {{ pt.label }}
          </div>
          <q-card flat bordered style="border-radius: 8px; overflow: hidden">
            <div
              v-for="(dt, idx) in pt.docTypes"
              :key="dt.type"
              class="tmpl-row"
              :style="idx < pt.docTypes.length - 1 ? 'border-bottom: 1px solid var(--fc-border-light)' : ''"
            >
              <span class="tmpl-label">{{ dt.label }}</span>
              <span class="tmpl-dots" />
              <div class="tmpl-right">
                <template v-if="getTemplate(pt.type, dt.type, activeClientType)">
                  <q-icon name="check_circle" color="positive" size="16px" />
                  <span class="tmpl-filename">{{ getTemplate(pt.type, dt.type, activeClientType).file_name }}</span>
                  <q-btn
                    flat
                    round
                    dense
                    icon="delete"
                    color="negative"
                    size="xs"
                    @click="deleteTemplate(pt.type, dt.type, activeClientType)"
                  />
                </template>
                <span v-else class="tmpl-empty">Не загружено</span>
                <q-btn
                  outline
                  size="sm"
                  :label="getTemplate(pt.type, dt.type, activeClientType) ? 'Заменить' : 'Загрузить'"
                  color="primary"
                  class="tmpl-btn"
                  @click="triggerTemplateUpload(pt.type, dt.type, activeClientType)"
                />
                <input
                  :ref="el => setTemplateInput(pt.type, dt.type, activeClientType, el)"
                  type="file"
                  accept=".docx,.dotx,.doc"
                  style="display:none"
                  @change="e => onTemplateFileSelected(pt.type, dt.type, activeClientType, e)"
                >
              </div>
            </div>
          </q-card>
        </div>

        <!-- Шаблоны состава проекта -->
        <div style="font-size: 14px; font-weight: 600; color: var(--fc-text); margin: 16px 0 8px">
          Шаблоны состава проекта
        </div>
        <div class="q-mb-xs" style="font-size:12px; color:var(--fc-text-secondary)">
          Вставьте тег
          <code style="background:#e8f5e9;color:#2e7d32;padding:1px 4px;border-radius:3px">&#123;&#123;СОСТАВ_ПРОЕКТА&#125;&#125;</code>
          в шаблон договора — на его место подставится состав по подтипу.
        </div>
        <div>
          <q-tabs
            v-model="activeCompositionClientType"
            dense
            align="left"
            active-color="primary"
            indicator-color="primary"
            class="q-mb-md"
            style="border-bottom: 1px solid var(--fc-border-light)"
          >
            <q-tab name="физ" label="Физ. лица" />
            <q-tab name="юр" label="Юр. лица" />
          </q-tabs>
        </div>
        <div v-for="pt in compositionSlots" :key="pt.type" class="q-mb-md">
          <div style="font-size: 13px; font-weight: 600; color: var(--fc-text); margin-bottom: 6px">
            {{ pt.label }}
          </div>
          <q-card flat bordered style="border-radius: 8px; overflow: hidden">
            <div
              v-for="(sub, idx) in pt.subtypes"
              :key="sub"
              class="tmpl-row"
              :style="idx < pt.subtypes.length - 1 ? 'border-bottom: 1px solid var(--fc-border-light)' : ''"
            >
              <span class="tmpl-label">{{ sub }}</span>
              <span class="tmpl-dots" />
              <div class="tmpl-right">
                <template v-if="getCompositionTemplate(pt.type, sub, activeCompositionClientType)">
                  <q-icon name="check_circle" color="positive" size="16px" />
                  <span class="tmpl-filename">{{ getCompositionTemplate(pt.type, sub, activeCompositionClientType).file_name }}</span>
                  <q-btn
                    flat
                    round
                    dense
                    icon="delete"
                    color="negative"
                    size="xs"
                    @click="deleteCompositionTemplate(pt.type, sub, activeCompositionClientType)"
                  />
                </template>
                <span v-else class="tmpl-empty">Не загружено</span>
                <q-btn
                  outline
                  size="sm"
                  :label="getCompositionTemplate(pt.type, sub, activeCompositionClientType) ? 'Заменить' : 'Загрузить'"
                  color="primary"
                  class="tmpl-btn"
                  @click="triggerCompositionUpload(pt.type, sub, activeCompositionClientType)"
                />
                <input
                  :ref="el => setCompositionInput(pt.type, sub, activeCompositionClientType, el)"
                  type="file"
                  accept=".docx,.dotx,.doc"
                  style="display:none"
                  @change="e => onCompositionFileSelected(pt.type, sub, activeCompositionClientType, e)"
                >
              </div>
            </div>
          </q-card>
        </div>
      </q-tab-panel>

      <!-- === Анкеты ТЗ === -->
      <q-tab-panel name="tz-survey" class="q-pa-sm">
        <div class="text-subtitle1 text-weight-bold q-mb-sm" style="color: var(--fc-text)">
          Шаблоны анкет технического задания
        </div>

        <div class="row q-gutter-sm q-mb-md items-center">
          <q-btn-toggle
            v-model="tzSurveyProjectType"
            toggle-color="purple"
            :options="[
              { label: 'Индивидуальный', value: 'Индивидуальный' },
              { label: 'Шаблонный', value: 'Шаблонный' },
            ]"
            dense
            unelevated
            size="sm"
            @update:model-value="loadTzSurveyTemplate"
          />
          <q-btn
            outline
            dense
            size="sm"
            icon="download"
            label="Загрузить"
            color="purple"
            :loading="tzSurveyTemplateLoading"
            @click="loadTzSurveyTemplate"
          />
        </div>

        <div v-if="tzSurveyTemplate">
          <div class="row q-gutter-xs q-mb-sm items-center">
            <div class="text-caption" style="color: var(--fc-text-light)">
              Последнее обновление: {{ tzSurveyTemplate.updated_at ? new Date(tzSurveyTemplate.updated_at).toLocaleString('ru') : 'никогда' }}
            </div>
            <q-space />
            <q-btn-toggle
              v-model="tzEditorMode"
              toggle-color="purple"
              dense
              size="sm"
              :options="[{ label: 'Визуальный', value: 'visual' }, { label: 'JSON', value: 'json' }]"
              class="q-mr-sm"
            />
            <q-btn
              outline
              dense
              size="sm"
              icon="restart_alt"
              label="Сбросить"
              color="negative"
              :loading="tzSurveyTemplateResetting"
              @click="resetTzSurveyTemplate"
            />
            <q-btn
              unelevated
              dense
              size="sm"
              icon="save"
              label="Сохранить"
              color="purple"
              :loading="tzSurveyTemplateSaving"
              @click="saveTzSurveyTemplate"
            />
          </div>

          <!-- Визуальный редактор -->
          <TzTemplateEditor
            v-if="tzEditorMode === 'visual' && tzSurveyTemplateData"
            v-model="tzSurveyTemplateData"
            class="q-mb-md"
          />

          <!-- JSON редактор -->
          <template v-if="tzEditorMode === 'json'">
            <div
              v-if="tzSurveyTemplateJsonError"
              class="text-negative q-mb-xs"
              style="font-size: 12px"
            >
              {{ tzSurveyTemplateJsonError }}
            </div>

            <q-input
              v-model="tzSurveyTemplateJson"
              type="textarea"
              outlined
              dense
              :rows="30"
              :error="!!tzSurveyTemplateJsonError"
              style="font-family: monospace; font-size: 12px; line-height: 1.4"
              @update:model-value="onJsonEdit"
            />
          </template>
        </div>

        <div v-else class="text-center q-pa-xl" style="color: var(--fc-text-disabled)">
          Выберите тип проекта и нажмите «Загрузить»
        </div>
      </q-tab-panel>
    </q-tab-panels>

    <!-- Диалог подтверждения восстановления -->
    <q-dialog v-model="showRestoreDialog" persistent>
      <q-card style="min-width: 320px; max-width: 480px; border-radius: 12px">
        <q-card-section class="row items-center q-pb-none">
          <q-icon name="warning" color="orange-8" size="28px" class="q-mr-sm" />
          <span style="font-size: 16px; font-weight: 600; color: #bf360c">Восстановление БД</span>
        </q-card-section>
        <q-card-section style="font-size: 14px; color: var(--fc-text)">
          <p class="q-mb-sm">
            Вы собираетесь восстановить базу данных из бекапа:
          </p>
          <div class="q-pa-sm" style="background: var(--fc-bg-alt); border-radius: 6px; font-size: 12px; color: var(--fc-text-medium); word-break: break-all">
            {{ restoreTarget }}
          </div>
          <p class="q-mt-md" style="color: #b71c1c; font-weight: 500">
            ⚠ ВНИМАНИЕ: Все текущие данные будут удалены и заменены данными из бекапа. Это действие необратимо!
          </p>
          <p style="color: var(--fc-text-secondary); font-size: 13px">
            После восстановления рекомендуется перезагрузить приложение.
          </p>
        </q-card-section>
        <q-card-actions align="right" class="q-pb-md q-px-md">
          <q-btn v-close-popup flat label="Отмена" color="grey-7" />
          <q-btn
            label="Восстановить"
            color="orange-8"
            icon="restore"
            :loading="restoreInProgress"
            @click="doRestore"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог прав роли — ПО БЛОКАМ -->
    <q-dialog v-model="showRoleDialog" maximized transition-show="slide-up" transition-hide="slide-down">
      <q-card>
        <q-toolbar style="background: var(--fc-accent); color: var(--fc-text)">
          <q-btn
            flat
            round
            dense
            icon="close"
            @click="showRoleDialog = false"
          />
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
            {{ selectedRole }}
          </q-toolbar-title>
          <q-btn
            label="Сохранить"
            no-caps
            outline
            style="border: 1px solid var(--fc-text); border-radius: 8px; color: var(--fc-text)"
            @click="saveRolePermissions"
          />
        </q-toolbar>
        <q-card-section style="max-height: calc(100vh - 50px); overflow-y: auto">
          <div v-for="(perms, group) in permissionsByGroup" :key="group" class="q-mb-md">
            <div class="text-subtitle2 text-weight-bold q-mb-xs" style="color: var(--fc-text); border-bottom: 1px solid var(--fc-border-light); padding-bottom: 4px">
              {{ group }}
            </div>
            <q-list dense>
              <q-item v-for="perm in perms" :key="perm.name" tag="label" dense>
                <q-item-section>
                  <q-item-label style="font-size: 11px; color: var(--fc-text)">
                    {{ perm.description || perm.name }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-toggle v-model="perm.granted" color="accent" dense />
                </q-item-section>
              </q-item>
            </q-list>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Диалог редактирования тарифа -->
    <q-dialog v-model="showRateDialog">
      <q-card style="min-width: 320px">
        <q-toolbar style="background: var(--fc-accent); color: var(--fc-text)">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
            {{ editingRate?.id ? 'Редактировать' : 'Новый' }} тариф
          </q-toolbar-title>
        </q-toolbar>
        <q-card-section v-if="editingRate">
          <!-- Тариф выезда надзора -->
          <template v-if="editingRate._isVisit">
            <q-select
              v-model="editingRate.role"
              :options="['ДАН', 'Старший менеджер проектов']"
              label="Роль"
              outlined
              dense
              class="q-mb-sm"
            />
            <q-select
              v-model="editingRate.city"
              :options="refs.cities"
              label="Город"
              outlined
              dense
              class="q-mb-sm"
            />
            <q-input
              v-model.number="editingRate.fixed_price"
              label="Цена за выезд (₽)"
              outlined
              dense
              type="number"
              class="q-mb-sm"
            />
          </template>
          <!-- Тариф исполнителя по закупкам -->
          <template v-else-if="editingRate._isPurchase">
            <q-select
              v-model="editingRate.role"
              :options="['ДАН', 'Старший менеджер проектов']"
              label="Роль"
              outlined
              dense
              class="q-mb-sm"
            />
            <q-select
              v-model="editingRate.stage_name"
              :options="PURCHASE_STAGE_OPTIONS"
              label="Стадия закупки (пусто = все)"
              outlined
              dense
              clearable
              class="q-mb-sm"
            />
            <q-input
              v-model.number="editingRate.fixed_price"
              label="Тариф за закупку (₽)"
              outlined
              dense
              type="number"
              class="q-mb-sm"
            />
          </template>
          <!-- Тариф замерщика: только цена и город -->
          <template v-else-if="rateTab === 'surveyor' || editingRate.surveyor_price">
            <q-input
              v-model.number="editingRate.surveyor_price"
              label="Цена замера (₽)"
              outlined
              dense
              type="number"
              class="q-mb-sm"
            />
            <q-select
              v-model="editingRate.city"
              :options="refs.cities"
              label="Город"
              outlined
              dense
              clearable
              class="q-mb-sm"
            />
          </template>
          <!-- Остальные тарифы -->
          <template v-else>
            <q-select
              v-model="editingRate.role"
              :options="refs.positions"
              label="Роль"
              outlined
              dense
              class="q-mb-sm"
            />
            <!-- Диапазон площади — только для Шаблонных тарифов -->
            <div v-if="rateTab === 'template'" class="row q-gutter-xs q-mb-sm">
              <q-input
                v-model.number="editingRate.area_from"
                label="Площадь от (м²)"
                outlined
                dense
                type="number"
                style="flex: 1"
              />
              <q-input
                v-model.number="editingRate.area_to"
                label="Площадь до (м²)"
                outlined
                dense
                type="number"
                style="flex: 1"
              />
            </div>
            <!-- Подтип проекта — только для Индивидуальных тарифов, первым чтобы влиял на стадии -->
            <q-select
              v-if="rateTab === 'individual'"
              v-model="editingRate.project_subtype"
              :options="['Полный', 'Эскизный', 'Планировочный']"
              label="Подтип проекта"
              outlined
              dense
              clearable
              class="q-mb-sm"
              hint="Пусто = тариф для всех подтипов"
            />
            <!-- Стадия: выпадающий список в зависимости от вкладки -->
            <q-select
              v-if="stageOptions.length > 0"
              v-model="editingRate.stage_name"
              :options="stageOptions"
              label="Стадия"
              outlined
              dense
              clearable
              class="q-mb-sm"
              hint="Пусто = тариф без привязки к стадии"
            />
            <q-input
              v-model.number="editingRate.rate_per_m2"
              label="₽/м²"
              outlined
              dense
              type="number"
              class="q-mb-sm"
            />
            <q-input
              v-model.number="editingRate.fixed_price"
              label="Фикс. цена"
              outlined
              dense
              type="number"
              class="q-mb-sm"
            />
            <q-select
              v-model="editingRate.city"
              :options="refs.cities"
              label="Город"
              outlined
              dense
              clearable
              class="q-mb-sm"
            />
          </template>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" no-caps />
          <q-btn
            unelevated
            label="Сохранить"
            style="background: var(--fc-accent); color: var(--fc-text); border-radius: 8px"
            no-caps
            @click="saveRate"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог ежемесячного тарифа надзора -->
    <q-dialog v-model="showMonthlyRateDialog">
      <q-card style="min-width: 320px; border-radius: 12px">
        <q-card-section class="q-pb-sm">
          <div class="text-subtitle2 text-weight-bold">
            {{ editingMonthlyRate.id ? 'Редактировать' : 'Новый' }} ежемесячный тариф надзора
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none q-gutter-y-sm">
          <q-select
            v-model="editingMonthlyRate.role"
            :options="['ДАН', 'Старший менеджер проектов']"
            label="Роль"
            outlined
            dense
          />
          <q-select
            v-model="editingMonthlyRate.city"
            :options="['МСК', 'СПБ', 'ЕКТ', 'ВН']"
            label="Город (пусто = все города)"
            outlined
            dense
            clearable
          />
          <q-input
            v-model.number="editingMonthlyRate.fixed_price"
            label="Ставка в месяц (₽)"
            type="number"
            outlined
            dense
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat no-caps label="Отмена" @click="showMonthlyRateDialog = false" />
          <q-btn
            unelevated
            no-caps
            label="Сохранить"
            style="background: var(--fc-accent); color: var(--fc-text)"
            :disable="!editingMonthlyRate.role || !editingMonthlyRate.fixed_price"
            @click="saveMonthlyRate"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог превью email письма -->
    <q-dialog v-model="emailPreviewDialog" maximized>
      <q-card style="display:flex; flex-direction:column; height:100%">
        <q-bar style="background: var(--fc-text); color: white">
          <q-icon name="visibility" />
          <div class="q-ml-sm">
            Превью: {{ emailEditorType === 'employee' ? 'Письмо сотруднику' : 'Приглашение клиенту' }}
          </div>
          <q-space />
          <q-btn v-close-popup dense flat icon="close" />
        </q-bar>
        <div style="flex:1; overflow:auto">
          <iframe
            v-if="emailPreviewHtml"
            :srcdoc="emailPreviewHtml"
            style="width:100%; height:100%; border:none; min-height:600px"
            sandbox="allow-same-origin"
          />
        </div>
      </q-card>
    </q-dialog>

    <!-- Диалог редактора HTML шаблона -->
    <q-dialog v-model="emailEditorDialog" maximized>
      <q-card style="display:flex; flex-direction:column; height:100%">
        <q-bar style="background: var(--fc-text); color: white">
          <q-icon name="edit" />
          <div class="q-ml-sm">
            Редактор: {{ emailEditorType === 'employee' ? 'Письмо сотруднику' : 'Приглашение клиенту' }}
          </div>
          <q-space />
          <q-btn v-close-popup dense flat icon="close" />
        </q-bar>
        <div class="q-pa-sm" style="flex:1; display:flex; flex-direction:column; overflow:hidden">
          <div class="text-caption q-mb-xs" style="color: var(--fc-text-light)">
            Доступные переменные:
            <template v-if="emailEditorType === 'employee'">
              <code>&#123;&#123;first_name&#125;&#125;</code> <code>&#123;&#123;login&#125;&#125;</code> <code>&#123;&#123;password&#125;&#125;</code>
              <code>&#123;&#123;telegram_link&#125;&#125;</code> <code>&#123;&#123;telegram_link_tg&#125;&#125;</code> <code>&#123;&#123;download_link&#125;&#125;</code>
            </template>
            <template v-else>
              <code>&#123;&#123;first_name&#125;&#125;</code> <code>&#123;&#123;project_address&#125;&#125;</code> <code>&#123;&#123;project_type&#125;&#125;</code>
              <code>&#123;&#123;manager_name&#125;&#125;</code> <code>&#123;&#123;invite_link&#125;&#125;</code> <code>&#123;&#123;telegram_link_tg&#125;&#125;</code>
            </template>
          </div>
          <div class="text-caption q-mb-sm" style="color: var(--fc-text-disabled)">
            Пустой шаблон = использовать стандартный дизайн.
          </div>
          <q-input
            v-model="emailEditorHtml"
            type="textarea"
            outlined
            dense
            style="flex:1; font-family: monospace; font-size: 12px"
            input-style="height:100%; resize:none; min-height:300px"
            placeholder="Введите HTML шаблон или оставьте пустым для стандартного..."
          />
        </div>
        <q-card-actions align="right" style="border-top: 1px solid var(--fc-border-light)">
          <q-btn
            flat
            no-caps
            label="Сбросить до стандартного"
            color="negative"
            @click="resetEmailTemplate"
          />
          <q-btn v-close-popup flat no-caps label="Отмена" />
          <q-btn
            unelevated
            no-caps
            label="Сохранить"
            icon="save"
            style="background: var(--fc-accent); color: var(--fc-text)"
            :loading="emailEditorSaving"
            @click="saveEmailTemplate"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'src/boot/axios'
import { useReferencesStore } from 'src/stores/references'
import { deletedContractsApi, messengerApi, adminApi, contractDocsApi, tzApi } from 'src/services/api'
import TzTemplateEditor from 'src/components/survey/TzTemplateEditor.vue'

const $q = useQuasar()
const refs = useReferencesStore()
const tab = ref('rates')
const deletedContracts = ref([])
const trashLoading = ref(false)
const rateTab = ref('individual')
const rates = ref([])
const normDays = ref([])
const ndLoading = ref(false)
const ndProjectType = ref('Индивидуальный')
const ND_SUBTYPES_INDIVIDUAL = ['Полный (с 3д визуализацией)', 'Эскизный (с коллажами)', 'Планировочный']
const ND_SUBTYPES_TEMPLATE = ['Стандарт', 'Стандарт с визуализацией', 'Проект ванной комнаты', 'Проект ванной комнаты с визуализацией']
const ndSubtypeOptions = computed(() => ndProjectType.value === 'Шаблонный' ? ND_SUBTYPES_TEMPLATE : ND_SUBTYPES_INDIVIDUAL)
const ndSubtype = ref('Полный (с 3д визуализацией)')
const ndArea = ref(100)
const ndK = ref(0)
const ndContractTerm = ref(0)
const ndPreview = ref([])
const ndEditMode = ref(false)
const ndEditMap = ref({})
const ndSaving = ref(false)
const showRoleDialog = ref(false)
const selectedRole = ref('')
const rolePermissions = ref([])
const showRateDialog = ref(false)
const editingRate = ref(null)

const citiesFull = ref([])
const rolesList = refs.positions
const inviteEmployeeId = ref(null)
const inviteEmployeeOpts = ref([])
const tgInfoEmployeeId = ref(null)
const tgInfo = ref(null)

// Messenger settings (Telegram / Email / MTProto)
const settingsSubTab = ref('telegram')
const messengerSettings = ref({})
const settingsLoading = ref(false)
const settingsSaving = ref(false)
const messengerStatus = ref(null)
const mtprotoCodeSent = ref(false)
const mtprotoCode = ref('')
const mtprotoVerifying = ref(false)
const showBotToken = ref(false)
const showApiHash = ref(false)
const showSmtpPassword = ref(false)
// Email template editor/preview
const emailEditorDialog = ref(false)
const emailEditorType = ref('employee')
const emailEditorHtml = ref('')
const emailEditorSaving = ref(false)
const emailPreviewDialog = ref(false)
const emailPreviewHtml = ref('')

// Блоки прав как в десктопе
const PERMISSION_GROUPS = {
  'Доступ к страницам': ['access.clients', 'access.contracts', 'access.crm', 'access.supervision', 'access.reports', 'access.employees', 'access.salaries', 'access.employee_reports', 'access.admin', 'access.dashboards'],
  'Сотрудники': ['employees.create', 'employees.update', 'employees.delete'],
  'Клиенты': ['clients.create', 'clients.view', 'clients.update', 'clients.delete'],
  'Договоры': ['contracts.create', 'contracts.view', 'contracts.update', 'contracts.delete', 'contracts.generate_contract', 'contracts.generate_acts'],
  'CRM': ['crm_cards.view_all', 'crm_cards.update', 'crm_cards.view_archive', 'crm_cards.move', 'crm_cards.delete', 'crm_cards.assign_executor', 'crm_cards.delete_executor', 'crm_cards.reset_stages', 'crm_cards.reset_approval', 'crm_cards.complete_approval', 'crm_cards.reset_designer', 'crm_cards.reset_draftsman', 'crm_cards.files_upload', 'crm_cards.files_delete', 'crm_cards.deadlines', 'crm_cards.payments'],
  'Надзор': ['supervision.view_all', 'supervision.view_archive', 'supervision.update', 'supervision.move', 'supervision.pause_resume', 'supervision.complete_stage', 'supervision.delete_order', 'supervision.assign_executor', 'supervision.files_upload', 'supervision.files_delete', 'supervision.deadlines', 'supervision.payments'],
  'Платежи': ['payments.create', 'payments.update', 'payments.delete'],
  'Зарплаты': ['salaries.create', 'salaries.update', 'salaries.delete', 'salaries.mark_to_pay', 'salaries.mark_paid'],
  'Тарифы': ['rates.create', 'rates.delete'],
  'Чат сотрудников': ['chat.employee.view', 'chat.employee.send', 'chat.employee.manage', 'chat.employee.upload_to_data'],
  'Чат с клиентами': ['chat.client.view', 'chat.client.send', 'chat.client.manage', 'chat.client.send_script'],
  'Мессенджер (Telegram)': ['messenger.create_chat', 'messenger.delete_chat', 'messenger.view_chat', 'messenger.manage_scripts'],
  'Уведомления': ['notifications.settings_projects', 'notifications.settings_duplication', 'notifications.settings_supervision', 'notifications.settings_payment'],
}

const rateTypeMap = { individual: 'Индивидуальный', template: 'Шаблонный', supervision: 'Авторский надзор', surveyor: 'Замерщик' }

const STAGES_BY_TAB = {
  individual: ['Стадия 1: планировочные решения', 'Стадия 2: концепция дизайна', 'Стадия 3: рабочие чертежи'],
  template: ['Стадия 1: планировочные решения', 'Стадия 2: рабочие чертежи', 'Стадия 3: 3д визуализация (Дополнительная)'],
  surveyor: [],
}

const PURCHASE_STAGE_OPTIONS = [
  'Закупка керамогранита', 'Закупка сантехники', 'Закупка оборудования',
  'Закупка дверей и окон', 'Закупка настенных материалов', 'Закупка напольных материалов',
  'Лепной декор', 'Освещение', 'Закупка потолочных материалов',
  'Бытовая техника', 'Закупка заказной мебели', 'Закупка фабричной мебели', 'Закупка декора',
]

const stageOptions = computed(() => STAGES_BY_TAB[rateTab.value] || [])

const filteredRates = computed(() => {
  if (rateTab.value === 'surveyor') return rates.value.filter(r => r.role === 'Замерщик')
  // Для надзора — только устаревшие записи без fixed_price и не закупки (не показываем в основном списке)
  if (rateTab.value === 'supervision') return []
  return rates.value.filter(r => r.project_type === rateTypeMap[rateTab.value])
})

const visitRates = computed(() =>
  rates.value.filter(r => r.project_type === 'Авторский надзор' && r.fixed_price != null && r.city && r.project_subtype !== 'monthly' && r.project_subtype !== 'purchase'),
)

const purchaseRates = computed(() =>
  rates.value.filter(r => r.project_type === 'Авторский надзор' && r.project_subtype === 'purchase'),
)

const monthlyRates = computed(() =>
  rates.value.filter(r => r.project_type === 'Надзор ежемесячный'),
)

const showMonthlyRateDialog = ref(false)
const editingMonthlyRate = ref({ id: null, role: null, city: null, fixed_price: null })

const permissionsByGroup = computed(() => {
  const result = {}
  for (const [group, permNames] of Object.entries(PERMISSION_GROUPS)) {
    const perms = permNames.map(name => {
      const existing = rolePermissions.value.find(p => p.name === name)
      return existing || { name, description: name, granted: false }
    })
    result[group] = perms
  }
  return result
})

async function loadRates() {
  try { const { data } = await api.get('/api/v1/rates'); rates.value = data } catch { rates.value = [] }
}

const STAGE_GROUP_LABELS = { START: 'Начало проекта', STAGE1: 'Стадия 1', STAGE2: 'Стадия 2', STAGE3: 'Стадия 3', FINISH: 'Завершение проекта' }

const normDaysGrouped = computed(() => {
  const order = []
  const map = {}
  normDays.value.forEach(nd => {
    const k = nd.stage_group || 'OTHER'
    if (!map[k]) { map[k] = { key: k, name: STAGE_GROUP_LABELS[k] || k, items: [] }; order.push(k) }
    map[k].items.push(nd)
  })
  return order.map(k => map[k])
})

const ndPreviewMap = computed(() => {
  const m = {}
  ndPreview.value.forEach(e => { if (e.stage_code) m[e.stage_code] = e.norm_days })
  return m
})

const ndTotalAll = computed(() => {
  if (ndPreview.value.length > 0) {
    return ndPreview.value
      .filter(e => e.executor_role !== 'header')
      .reduce((sum, e) => sum + (e.norm_days || 0), 0)
  }
  return normDays.value
    .filter(nd => nd.executor_role !== 'header')
    .reduce((sum, nd) => sum + (nd.base_norm_days || 0), 0)
})

async function previewNormDays() {
  if (!ndProjectType.value || !ndSubtype.value) return
  try {
    const { data } = await api.post('/api/v1/norm-days/templates/preview', {
      area: ndArea.value || 100,
      project_type: ndProjectType.value,
      project_subtype: ndSubtype.value,
    })
    ndPreview.value = data.entries || []
    ndContractTerm.value = data.contract_term || 0
    ndK.value = data.k_coefficient || 0
  } catch { ndPreview.value = [] }
}

async function loadNormDays() {
  if (!ndProjectType.value || !ndSubtype.value) return
  ndLoading.value = true
  try {
    const { data } = await api.get('/api/v1/norm-days/templates', { params: { project_type: ndProjectType.value, project_subtype: ndSubtype.value } })
    normDays.value = data.entries || data || []
    await previewNormDays()
  } catch { normDays.value = [] }
  finally { ndLoading.value = false }
}

function onNdTypeChange() {
  ndSubtype.value = ndSubtypeOptions.value[0]
  ndEditMode.value = false
  ndEditMap.value = {}
  loadNormDays()
}

function onNdSubtypeChange() {
  ndEditMode.value = false
  ndEditMap.value = {}
  loadNormDays()
}

function enterEditMode() {
  const m = {}
  normDays.value.forEach(nd => { m[nd.stage_code] = { base_norm_days: nd.base_norm_days, k_multiplier: nd.k_multiplier || 0 } })
  ndEditMap.value = m
  ndEditMode.value = true
}

function cancelEdit() {
  ndEditMode.value = false
  ndEditMap.value = {}
}

async function saveNormDays() {
  ndSaving.value = true
  try {
    const entries = normDays.value
      .filter(nd => nd.executor_role !== 'header')
      .map(nd => {
        const edited = ndEditMap.value[nd.stage_code] || {}
        return {
          stage_code: nd.stage_code,
          stage_name: nd.stage_name,
          stage_group: nd.stage_group,
          substage_group: nd.substage_group,
          base_norm_days: Number(edited.base_norm_days ?? nd.base_norm_days),
          k_multiplier: Number(edited.k_multiplier ?? nd.k_multiplier ?? 0),
          executor_role: nd.executor_role,
          is_in_contract_scope: nd.is_in_contract_scope,
          sort_order: nd.sort_order,
        }
      })
    await api.put('/api/v1/norm-days/templates', { project_type: ndProjectType.value, project_subtype: ndSubtype.value, entries })
    $q.notify({ type: 'positive', message: 'Нормодни сохранены' })
    ndEditMode.value = false
    ndEditMap.value = {}
    await loadNormDays()
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка сохранения' })
  } finally { ndSaving.value = false }
}

async function resetNormDays() {
  $q.dialog({
    title: 'Сбросить нормодни?',
    message: 'Вернуть стандартные формулы из кода для этого типа и подтипа? Все кастомные изменения будут удалены.',
    cancel: { label: 'Отмена', flat: true },
    ok: { label: 'Сбросить', color: 'negative' },
    persistent: true,
  }).onOk(async () => {
    try {
      await api.post('/api/v1/norm-days/templates/reset', { project_type: ndProjectType.value, project_subtype: ndSubtype.value })
      $q.notify({ type: 'positive', message: 'Нормодни сброшены к стандартным' })
      ndEditMode.value = false
      await loadNormDays()
    } catch {
      $q.notify({ type: 'negative', message: 'Ошибка сброса' })
    }
  })
}

function buildNdRows() {
  const rows = []
  normDaysGrouped.value.forEach(group => {
    group.items.forEach(nd => {
      if (nd.executor_role === 'header') {
        rows.push({ group: group.name, name: nd.stage_name, role: '', days: '', outOfScope: false, isHeader: true })
      } else {
        const days = ndPreviewMap.value[nd.stage_code] !== undefined ? ndPreviewMap.value[nd.stage_code] : (nd.base_norm_days ?? 0)
        rows.push({ group: group.name, name: nd.stage_name, role: nd.executor_role, days, outOfScope: !nd.is_in_contract_scope, isHeader: false })
      }
    })
  })
  return rows
}

async function exportNormDaysExcel() {
  const { utils, writeFile } = await import('xlsx')
  const rows = buildNdRows()
  const title = `${ndProjectType.value} — ${ndSubtype.value} (${ndArea.value} м²)`

  const wsData = [
    [title],
    [],
    ['Стадия', 'Этап', 'Роль', 'Норма, дн.', 'Вне объёма'],
  ]
  let lastGroup = ''
  rows.forEach(r => {
    if (r.isHeader) {
      wsData.push([r.group, r.name, '', '', ''])
    } else {
      wsData.push([r.group !== lastGroup ? r.group : '', r.name, r.role, r.days, r.outOfScope ? 'вне объёма' : ''])
    }
    lastGroup = r.group
  })
  wsData.push([])
  wsData.push(['', 'Итого по договору', '', ndContractTerm.value, ''])
  wsData.push(['', 'Итого с учётом вне объёма', '', ndTotalAll.value, ''])

  const ws = utils.aoa_to_sheet(wsData)
  ws['!cols'] = [{ wch: 22 }, { wch: 38 }, { wch: 22 }, { wch: 12 }, { wch: 12 }]
  const wb = utils.book_new()
  utils.book_append_sheet(wb, ws, 'Нормодни')
  const fileName = `normdays_${ndProjectType.value}_${ndSubtype.value}_${ndArea.value}m2.xlsx`
    .replace(/[^\wа-яёА-ЯЁ._-]/gi, '_')
  writeFile(wb, fileName)
}

function exportNormDaysPdf() {
  const rows = buildNdRows()
  const title = `Нормодни: ${ndProjectType.value} — ${ndSubtype.value}`
  const subtitle = `Площадь: ${ndArea.value} м²&nbsp;&nbsp;|&nbsp;&nbsp;Срок: ${ndContractTerm.value} дн.`

  let tableRows = ''
  let lastGroup = ''
  rows.forEach(r => {
    if (r.isHeader) {
      tableRows += `<tr class="sub-hdr"><td colspan="4">${r.name}</td></tr>`
    } else {
      const grpCell = r.group !== lastGroup ? `<td class="grp">${r.group}</td>` : '<td class="grp"></td>'
      const outCls = r.outOfScope ? ' class="out"' : ''
      tableRows += `<tr${outCls}>${grpCell}<td>${r.name}</td><td>${r.role}</td><td class="num">${r.days} дн.</td></tr>`
      lastGroup = r.group
    }
  })
  tableRows += `
    <tr class="total-row"><td></td><td colspan="2"><b>ИТОГО по договору</b></td><td class="num"><b>${ndContractTerm.value} дн.</b></td></tr>
    <tr class="total-sub"><td></td><td colspan="2">ИТОГО с учётом вне объёма</td><td class="num">${ndTotalAll.value} дн.</td></tr>`

  const html = `<!DOCTYPE html><html><head><meta charset="utf-8">
  <title>${title}</title>
  <style>
    body { font-family: Arial, sans-serif; font-size: 11px; color: #222; margin: 20px; }
    h2 { font-size: 14px; margin: 0 0 4px; }
    .sub { color: var(--fc-text-secondary); margin-bottom: 14px; font-size: 11px; }
    table { border-collapse: collapse; width: 100%; }
    th { background: var(--fc-accent); color: var(--fc-text); font-weight: bold; padding: 5px 8px; text-align: left; border: 1px solid var(--fc-border); }
    td { padding: 4px 8px; border: 1px solid var(--fc-border-light); vertical-align: middle; }
    .grp { color: var(--fc-text-medium); font-size: 10px; width: 22%; }
    .num { text-align: right; width: 10%; white-space: nowrap; }
    .sub-hdr td { background: var(--fc-tab-hover); font-weight: bold; font-size: 10px; color: var(--fc-text-medium); }
    .out td { color: var(--fc-text-disabled); }
    .total-row td { border-top: 2px solid var(--fc-text); font-size: 12px; }
    .total-sub td { color: var(--fc-text-light); }
    @media print { @page { margin: 15mm; } }
  </style></head><body>
  <h2>${title}</h2>
  <div class="sub">${subtitle}</div>
  <table><thead><tr><th>Стадия</th><th>Этап</th><th>Роль</th><th>Дни</th></tr></thead>
  <tbody>${tableRows}</tbody></table>
  <script>window.onload = () => { window.print() }<\/script>
  </body></html>`

  const w = window.open('', '_blank')
  w.document.write(html)
  w.document.close()
}

function editRate(rate) {
  editingRate.value = { ...rate }
  showRateDialog.value = true
}

function addRate() {
  if (rateTab.value === 'surveyor') {
    editingRate.value = { role: 'Замерщик', surveyor_price: null, city: null }
  } else {
    editingRate.value = { project_type: rateTypeMap[rateTab.value] || null, role: null, rate_per_m2: null, fixed_price: null, stage_name: null, city: null, project_subtype: null, area_from: null, area_to: null }
  }
  showRateDialog.value = true
}

function addVisitRate() {
  editingRate.value = { project_type: 'Авторский надзор', role: null, fixed_price: null, city: null, _isVisit: true }
  showRateDialog.value = true
}

function editVisitRate(rate) {
  editingRate.value = { ...rate, _isVisit: true }
  showRateDialog.value = true
}

function addPurchaseRate() {
  editingRate.value = { project_type: 'Авторский надзор', project_subtype: 'purchase', role: null, stage_name: null, fixed_price: null, _isPurchase: true }
  showRateDialog.value = true
}

function editPurchaseRate(rate) {
  editingRate.value = { ...rate, _isPurchase: true }
  showRateDialog.value = true
}

function addMonthlyRate() {
  editingMonthlyRate.value = { id: null, role: null, city: null, fixed_price: null }
  showMonthlyRateDialog.value = true
}

function editMonthlyRate(rate) {
  editingMonthlyRate.value = { id: rate.id, role: rate.role, city: rate.city, fixed_price: rate.fixed_price }
  showMonthlyRateDialog.value = true
}

async function saveMonthlyRate() {
  if (!editingMonthlyRate.value.role || !editingMonthlyRate.value.fixed_price) return
  try {
    const payload = {
      project_type: 'Надзор ежемесячный',
      role: editingMonthlyRate.value.role,
      city: editingMonthlyRate.value.city || null,
      fixed_price: editingMonthlyRate.value.fixed_price,
    }
    if (editingMonthlyRate.value.id) {
      await api.put(`/api/v1/rates/${editingMonthlyRate.value.id}`, payload)
    } else {
      await api.post('/api/v1/rates', payload)
    }
    $q.notify({ type: 'positive', message: 'Ежемесячный тариф сохранён' })
    showMonthlyRateDialog.value = false
    loadRates()
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка сохранения тарифа' })
  }
}

async function saveRate() {
  if (!editingRate.value) return
  try {
    if (editingRate.value._isVisit) {
      const payload = {
        project_type: 'Авторский надзор',
        role: editingRate.value.role,
        city: editingRate.value.city,
        fixed_price: editingRate.value.fixed_price,
      }
      if (editingRate.value.id) {
        await api.put(`/api/v1/rates/${editingRate.value.id}`, payload)
      } else {
        await api.post('/api/v1/rates', payload)
      }
      $q.notify({ type: 'positive', message: 'Тариф выезда сохранён' })
      showRateDialog.value = false
      loadRates()
      return
    }
    if (editingRate.value._isPurchase) {
      const payload = {
        project_type: 'Авторский надзор',
        project_subtype: 'purchase',
        role: editingRate.value.role,
        stage_name: editingRate.value.stage_name || null,
        fixed_price: editingRate.value.fixed_price,
      }
      if (editingRate.value.id) {
        await api.put(`/api/v1/rates/${editingRate.value.id}`, payload)
      } else {
        await api.post('/api/v1/rates', payload)
      }
      $q.notify({ type: 'positive', message: 'Тариф закупки сохранён' })
      showRateDialog.value = false
      loadRates()
      return
    }
    const isSurveyor = rateTab.value === 'surveyor' || !!editingRate.value.surveyor_price
    if (isSurveyor) {
      // Замерщик: upsert по городу через специальный endpoint
      await api.post('/api/v1/rates/surveyor', { city: editingRate.value.city, price: editingRate.value.surveyor_price })
    } else if (editingRate.value.id) {
      await api.put(`/api/v1/rates/${editingRate.value.id}`, editingRate.value)
    } else {
      await api.post('/api/v1/rates', editingRate.value)
    }
    $q.notify({ type: 'positive', message: 'Тариф сохранён' })
    showRateDialog.value = false
    loadRates()
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
}

async function deleteRate(rate) {
  $q.dialog({ title: 'Удалить тариф?', message: `${rate.role} — ${rate.rate_per_m2 || rate.fixed_price || rate.surveyor_price} ₽`, cancel: true }).onOk(async () => {
    try {
      await api.delete(`/api/v1/rates/${rate.id}`)
      $q.notify({ type: 'positive', message: 'Удалено' })
      loadRates()
    } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  })
}

async function viewRolePermissions(role) {
  selectedRole.value = role
  try {
    const [defsRes, matrixRes] = await Promise.allSettled([
      api.get('/api/v1/permissions/definitions'),
      api.get('/api/v1/permissions/role-matrix'),
    ])
    const defs = defsRes.status === 'fulfilled' ? defsRes.value.data : []
    const matrix = matrixRes.status === 'fulfilled' ? matrixRes.value.data?.roles || {} : {}
    const rolePerms = matrix[role] || []
    rolePermissions.value = defs.map(d => ({ name: d.name, description: d.description, granted: rolePerms.includes(d.name) }))
    // Добавляем права из PERMISSION_GROUPS которых нет в definitions API (новые права до rebuild)
    const LOCAL_PERM_DESCRIPTIONS = {
      'crm_cards.view_all': 'Показывать все карточки СРМ (не только свои)',
      'supervision.view_all': 'Показывать все карточки надзора (не только свои)',
    }
    const knownNames = new Set(rolePermissions.value.map(p => p.name))
    for (const permNames of Object.values(PERMISSION_GROUPS)) {
      for (const name of permNames) {
        if (!knownNames.has(name)) {
          rolePermissions.value.push({ name, description: LOCAL_PERM_DESCRIPTIONS[name] || name, granted: rolePerms.includes(name) })
          knownNames.add(name)
        }
      }
    }
    showRoleDialog.value = true
  } catch {}
}

async function saveRolePermissions() {
  const granted = rolePermissions.value.filter(p => p.granted).map(p => p.name)
  try {
    // Загружаем полную текущую матрицу, чтобы не затереть другие роли
    const { data: currentData } = await api.get('/api/v1/permissions/role-matrix')
    const fullMatrix = currentData.roles || {}
    fullMatrix[selectedRole.value] = granted
    await api.put('/api/v1/permissions/role-matrix', {
      roles: fullMatrix,
      apply_to_employees: true,
    })
    $q.notify({ type: 'positive', message: 'Права сохранены и применены к сотрудникам' })
    showRoleDialog.value = false
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
}

function addAgent() {
  $q.dialog({ title: 'Новый агент', prompt: { model: '', type: 'text', label: 'Название' }, cancel: true }).onOk(async (name) => {
    try { await api.post('/api/v1/agents', { name, color: '#95A5A6' }); $q.notify({ type: 'positive', message: 'Добавлен' }); refs.loaded = false; refs.loadAll() }
    catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  })
}

function deleteAgent(agent) {
  $q.dialog({ title: 'Удалить агента?', message: agent.name, cancel: true }).onOk(async () => {
    try { await api.delete(`/api/v1/agents/${agent.id}`); $q.notify({ type: 'positive', message: 'Удалён' }); refs.loaded = false; refs.loadAll() }
    catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  })
}

async function updateAgentColor(agent, color) {
  try { await api.patch(`/api/v1/agents/${encodeURIComponent(agent.name)}/color`, { color }); refs.loaded = false; refs.loadAll() }
  catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
}

async function loadCitiesFull() {
  try { const { data } = await api.get('/api/v1/cities'); citiesFull.value = data.filter(c => c.status === 'активный') } catch { citiesFull.value = [] }
}

function addCity() {
  $q.dialog({ title: 'Новый город', prompt: { model: '', type: 'text', label: 'Название' }, cancel: true }).onOk(async (name) => {
    try { await api.post('/api/v1/cities', { name }); $q.notify({ type: 'positive', message: 'Добавлен' }); refs.loaded = false; await Promise.all([refs.loadAll(), loadCitiesFull()]) }
    catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  })
}

function deleteCity(city) {
  $q.dialog({ title: 'Удалить город?', message: city.name, cancel: true }).onOk(async () => {
    try { await api.delete(`/api/v1/cities/${city.id}`); $q.notify({ type: 'positive', message: 'Удалён' }); refs.loaded = false; await Promise.all([refs.loadAll(), loadCitiesFull()]) }
    catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  })
}

function editCity(city) {
  $q.dialog({ title: 'Переименовать город', prompt: { model: city.name, type: 'text', label: 'Название' }, cancel: true })
    .onOk(async (name) => {
      if (!name || name.trim() === city.name) return
      try {
        await api.patch(`/api/v1/cities/${city.id}`, { name: name.trim() })
        $q.notify({ type: 'positive', message: 'Город переименован' })
        refs.loaded = false
        await Promise.all([refs.loadAll(), loadCitiesFull()])
      } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
    })
}

async function loadMessengerSettings() {
  settingsLoading.value = true
  try {
    const { data } = await messengerApi.getSettings()
    const obj = {}
    for (const item of data) {
      obj[item.setting_key] = item.setting_value ?? ''
    }
    messengerSettings.value = obj
    const statusRes = await messengerApi.getStatus()
    messengerStatus.value = statusRes.data
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Ошибка загрузки настроек' })
  } finally {
    settingsLoading.value = false
  }
}

async function saveMessengerSettings() {
  settingsSaving.value = true
  try {
    await messengerApi.updateSettings(messengerSettings.value)
    $q.notify({ type: 'positive', message: 'Настройки сохранены' })
    await loadMessengerSettings()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка сохранения' })
  } finally {
    settingsSaving.value = false
  }
}

async function mtprotoSendCode() {
  try {
    await messengerApi.mtprotoSendCode()
    mtprotoCodeSent.value = true
    $q.notify({ type: 'positive', message: 'Код отправлен в Telegram' })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка отправки кода' })
  }
}

async function mtprotoVerifyCode() {
  if (!mtprotoCode.value) return
  mtprotoVerifying.value = true
  try {
    await messengerApi.mtprotoVerifyCode(mtprotoCode.value)
    $q.notify({ type: 'positive', message: 'MTProto авторизован успешно' })
    mtprotoCodeSent.value = false
    mtprotoCode.value = ''
    await loadMessengerSettings()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Неверный код' })
  } finally {
    mtprotoVerifying.value = false
  }
}

async function mtprotoResendSms() {
  try {
    await messengerApi.mtprotoResendSms()
    $q.notify({ type: 'positive', message: 'SMS отправлено' })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

async function previewEmail(type) {
  try {
    const res = await messengerApi.previewEmail(type)
    emailPreviewHtml.value = res.data
    emailPreviewDialog.value = true
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Ошибка загрузки превью' })
  }
}

async function editEmail(type) {
  emailEditorType.value = type
  try {
    const { data } = await messengerApi.getEmailTemplate(type)
    emailEditorHtml.value = data.html || ''
    emailEditorDialog.value = true
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Ошибка загрузки шаблона' })
  }
}

async function saveEmailTemplate() {
  emailEditorSaving.value = true
  try {
    await messengerApi.saveEmailTemplate(emailEditorType.value, emailEditorHtml.value)
    $q.notify({ type: 'positive', message: 'Шаблон сохранён' })
    emailEditorDialog.value = false
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Ошибка сохранения шаблона' })
  } finally {
    emailEditorSaving.value = false
  }
}

function resetEmailTemplate() {
  $q.dialog({
    title: 'Сбросить шаблон?',
    message: 'Вернуть стандартный шаблон письма? Ваши изменения будут удалены.',
    cancel: true,
  }).onOk(async () => {
    try {
      await messengerApi.resetEmailTemplate(emailEditorType.value)
      $q.notify({ type: 'positive', message: 'Шаблон сброшен до стандартного' })
      emailEditorDialog.value = false
    } catch (err) {
      $q.notify({ type: 'negative', message: 'Ошибка' })
    }
  })
}

async function loadTgInfo() {
  if (!tgInfoEmployeeId.value) { tgInfo.value = null; return }
  try {
    const { data } = await api.get(`/api/v1/employees/${tgInfoEmployeeId.value}/telegram-info`)
    tgInfo.value = data
  } catch { tgInfo.value = null }
}

function copyToClipboard(text) {
  if (!text) return
  navigator.clipboard.writeText(text).then(() => {
    $q.notify({ type: 'positive', message: 'Скопировано' })
  })
}

async function sendTestNotification() {
  try {
    await api.post('/api/v1/notifications/test')
    $q.notify({ type: 'positive', message: 'Тестовое уведомление отправлено' })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

async function sendInvite() {
  if (!inviteEmployeeId.value) return
  try {
    await api.post(`/api/v1/employees/${inviteEmployeeId.value}/send-invite`)
    $q.notify({ type: 'positive', message: 'Приглашение отправлено' })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

function formatTrashDate(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch { return iso }
}

async function loadTrash() {
  trashLoading.value = true
  try {
    const { data } = await deletedContractsApi.getList()
    deletedContracts.value = (data || []).map(item => ({ ...item, _loading: false }))
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка загрузки корзины' })
  } finally {
    trashLoading.value = false
  }
}

async function restoreContract(item) {
  item._loading = true
  try {
    const { data } = await deletedContractsApi.restore(item.id)
    $q.notify({ type: 'positive', message: data.message || 'Договор восстановлен' })
    await loadTrash()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка восстановления' })
    item._loading = false
  }
}

function permanentDeleteContract(item) {
  $q.dialog({
    title: 'Удалить навсегда?',
    message: `Договор №${item.contract_number || '—'} (${item.client_name}) будет удалён безвозвратно вместе с папкой на Яндекс.Диске.`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await deletedContractsApi.permanentDelete(item.id)
      $q.notify({ type: 'positive', message: 'Удалено безвозвратно' })
      await loadTrash()
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка удаления' })
    }
  })
}

// === БЕКАП ===
const backupInProgress = ref(false)
const lastBackup = ref(null)
const backupList = ref([])
const backupsLoading = ref(false)

let _backupPollTimer = null

// ─── VPN ─────────────────────────────────────────────────────────────────────

async function startBackup() {
  try {
    await adminApi.triggerBackup()
    backupInProgress.value = true
    lastBackup.value = null
    _pollBackupStatus()
    $q.notify({ type: 'info', message: 'Бекап запущен — ожидайте...' })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Не удалось запустить бекап' })
  }
}

function _pollBackupStatus() {
  if (_backupPollTimer) clearTimeout(_backupPollTimer)
  _backupPollTimer = setTimeout(async () => {
    try {
      const { data } = await adminApi.getBackupStatus()
      backupInProgress.value = data.in_progress
      if (data.last) lastBackup.value = data.last
      if (data.in_progress) {
        _pollBackupStatus()
      } else if (data.last?.status === 'success') {
        loadBackupList()
      }
    } catch {}
  }, 3000)
}

async function loadBackupList() {
  backupsLoading.value = true
  try {
    const { data } = await adminApi.listBackups()
    backupList.value = data.backups || []
  } catch {
    backupList.value = []
  } finally {
    backupsLoading.value = false
  }
}

function formatBackupSize(bytes) {
  if (!bytes) return '?'
  const mb = bytes / 1024 / 1024
  return mb >= 1 ? `${mb.toFixed(1)} МБ` : `${(bytes / 1024).toFixed(0)} КБ`
}

function formatBackupDate(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch { return iso }
}

// === ВОССТАНОВЛЕНИЕ ===
const restoreInProgress = ref(false)
const lastRestore = ref(null)
const restoreTarget = ref(null)
const showRestoreDialog = ref(false)

let _restorePollTimer = null

function confirmRestore(filename) {
  restoreTarget.value = filename
  showRestoreDialog.value = true
}

async function doRestore() {
  showRestoreDialog.value = false
  restoreInProgress.value = true
  lastRestore.value = null
  try {
    await adminApi.restoreBackup(restoreTarget.value)
    _pollRestoreStatus()
    $q.notify({ type: 'warning', message: 'Восстановление БД запущено — не закрывайте страницу', timeout: 10000 })
  } catch (err) {
    restoreInProgress.value = false
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка запуска восстановления' })
  }
}

function _pollRestoreStatus() {
  if (_restorePollTimer) clearTimeout(_restorePollTimer)
  _restorePollTimer = setTimeout(async () => {
    try {
      const { data } = await adminApi.getRestoreStatus()
      restoreInProgress.value = data.in_progress
      if (data.last) lastRestore.value = data.last
      if (data.in_progress) {
        _pollRestoreStatus()
      } else if (data.last?.status === 'success') {
        $q.notify({ type: 'positive', message: 'Восстановление завершено успешно!', timeout: 8000 })
      }
    } catch {
      _pollRestoreStatus()
    }
  }, 3000)
}


watch(tab, (val) => {
  if (val === 'trash') loadTrash()
  if (val === 'normdays') loadNormDays()
  if (val === 'telegram') loadMessengerSettings()
  if (val === 'backup') {
    loadBackupList()
    adminApi.getBackupStatus().then(r => {
      lastBackup.value = r.data.last
      backupInProgress.value = r.data.in_progress
      if (r.data.in_progress) _pollBackupStatus()
    }).catch(() => {})
    adminApi.getRestoreStatus().then(r => {
      lastRestore.value = r.data.last
      restoreInProgress.value = r.data.in_progress
      if (r.data.in_progress) _pollRestoreStatus()
    }).catch(() => {})
  }
})

// ─── Шаблоны договоров ───────────────────────────────────────────────────────

const templateTags = [
  { tag: 'НОМЕР_ДОГОВОРА', desc: 'Номер договора (напр. «ФЦ-2025-001»)' },
  { tag: 'ДАТА_ДОГОВОРА', desc: 'Дата договора прописью (напр. «01 января 2025 г.»)' },
  { tag: 'АДРЕС', desc: 'Адрес объекта' },
  { tag: 'ПЛОЩАДЬ', desc: 'Площадь объекта (число)' },
  { tag: 'СРОК', desc: 'Срок выполнения работ (дней)' },
  { tag: 'СУММА', desc: 'Сумма договора цифрами' },
  { tag: 'СУММА_ПРОПИСЬЮ', desc: 'Сумма договора прописью (рубли)' },
  { tag: 'АВАНС', desc: 'Авансовый платёж цифрами' },
  { tag: 'АВАНС_ПРОПИСЬЮ', desc: 'Авансовый платёж прописью (рубли)' },
  { tag: 'ДОПЛАТА', desc: 'Второй платёж цифрами' },
  { tag: 'ДОПЛАТА_ПРОПИСЬЮ', desc: 'Второй платёж прописью (рубли)' },
  { tag: 'ТРЕТИЙ_ПЛАТЕЖ', desc: 'Третий платёж цифрами' },
  { tag: 'ТРЕТИЙ_ПЛАТЕЖ_ПРОПИСЬЮ', desc: 'Третий платёж прописью (рубли)' },
  { tag: 'ЭТАП_ПР_СТОИМОСТЬ', desc: 'Стоимость план. решений (Инд: 20%, Шабл: 30% от суммы)' },
  { tag: 'ЭТАП_ПР_СРОК', desc: 'Срок план. решений в днях (Инд: 16%, Шабл: 24% от срока, целое)' },
  { tag: 'ЭТАП_КД_СТОИМОСТЬ', desc: 'Стоимость концепции дизайна (Инд: 50%; Шабл: пусто)' },
  { tag: 'ЭТАП_КД_СРОК', desc: 'Срок концепции дизайна в днях (Инд: 50%; Шабл: пусто)' },
  { tag: 'ЭТАП_РЧ_СТОИМОСТЬ', desc: 'Стоимость комплекта чертежей (Инд: 25%, Шабл: 70% от суммы)' },
  { tag: 'ЭТАП_РЧ_СРОК', desc: 'Срок комплекта чертежей в днях (Инд: 24%, Шабл: 76% от срока, целое)' },
  { tag: 'ЭТАП_СМ_СТОИМОСТЬ', desc: 'Стоимость ведомости/сметы (Инд: 5%; Шабл: пусто)' },
  { tag: 'ЭТАП_СМ_СРОК', desc: 'Срок ведомости/сметы в днях (Инд: 10%; Шабл: пусто)' },
  { tag: 'ТИП_ПРОЕКТА', desc: 'Тип проекта (Индивидуальный / Шаблонный / Авторский надзор)' },
  { tag: 'ПОДТИП_ПРОЕКТА', desc: 'Подтип проекта (Полный, Эскизный, Стандарт…)' },
  { tag: 'ТИП_ОРГАНИЗАЦИИ', desc: 'Тип организации юр. лица: ООО / ИП / АО / ПАО / ЗАО' },
  { tag: 'СЕГОДНЯ', desc: 'Текущая дата прописью' },
  { tag: 'КЛИЕНТ', desc: 'ФИО клиента' },
  { tag: 'ТЕЛЕФОН', desc: 'Телефон клиента' },
  { tag: 'EMAIL', desc: 'Email клиента' },
  { tag: 'ПАСПОРТ_СЕРИЯ', desc: 'Серия паспорта' },
  { tag: 'ПАСПОРТ_НОМЕР', desc: 'Номер паспорта' },
  { tag: 'ПАСПОРТ_КЕМ_ВЫДАН', desc: 'Кем выдан паспорт' },
  { tag: 'ПАСПОРТ_ДАТА', desc: 'Дата выдачи паспорта' },
  { tag: 'АДРЕС_РЕГИСТРАЦИИ', desc: 'Адрес регистрации клиента' },
  { tag: 'ИНН', desc: 'ИНН (для организаций)' },
  { tag: 'ОГРН', desc: 'ОГРН (для организаций)' },
  { tag: 'ОРГАНИЗАЦИЯ', desc: 'Название организации' },
  { tag: 'РЕКВИЗИТЫ', desc: 'Банковские реквизиты' },
  { tag: 'ОТВЕТСТВЕННЫЙ', desc: 'Ответственное лицо организации' },
]

const requisiteSlots = [
  { type: 'signature', label: 'Подпись' },
  { type: 'signature_name', label: 'Подпись с расшифровкой' },
  { type: 'seal', label: 'Печать' },
]

// Динамические слоты лого агентов: logo_<agent_name_lower> для каждого агента
const agentLogoSlots = computed(() =>
  (refs.agents || []).map((a) => ({
    type: `logo_${(a.name || '').trim().toLowerCase()}`,
    label: `Лого ${a.name}`,
  })),
)

const projectTypeSlots = [
  {
    type: 'Индивидуальный',
    label: 'Индивидуальный проект',
    docTypes: [
      { type: 'contract', label: 'Договор' },
      { type: 'act_pr', label: 'Акт планировочных решений' },
      { type: 'act_kd', label: 'Акт концепции дизайна' },
      { type: 'act_info', label: 'Информационное письмо о готовности' },
      { type: 'act_final', label: 'Акт финальной стадии/приёмки работ' },
    ],
  },
  {
    type: 'Шаблонный',
    label: 'Шаблонный проект',
    docTypes: [
      { type: 'contract', label: 'Договор' },
      { type: 'act_pr', label: 'Акт планировочного решения' },
      { type: 'act_final', label: 'Акт финальной сдачи/приёмки работ' },
    ],
  },
  {
    type: 'Авторский надзор',
    label: 'Авторский надзор',
    docTypes: [
      { type: 'contract', label: 'Договор' },
      { type: 'act_final', label: 'Акт финальной сдачи/приёмки работ' },
    ],
  },
]

const requisites = ref({})        // { signature: {...}, seal: {...}, signature_name: {...} }
const templates = ref([])         // ContractTemplateResponse[]
const requisiteInputs = ref({})   // { signature: <input el>, ... }
const templateInputs = ref({})    // { 'Индивидуальный::contract::физ': <input el>, ... }
const activeClientType = ref('физ')  // 'физ' | 'юр'

function getTemplate(projectType, docType, clientType = 'физ') {
  return templates.value.find(
    t => t.project_type === projectType && t.doc_type === docType && (t.client_type || 'физ') === clientType,
  ) || null
}

function setTemplateInput(projectType, docType, clientType, el) {
  templateInputs.value[`${projectType}::${docType}::${clientType}`] = el
}

async function loadDocTemplates() {
  try {
    const [rRes, tRes] = await Promise.all([
      contractDocsApi.getRequisites(),
      contractDocsApi.getTemplates(),
    ])
    const map = {}
    for (const r of rRes.data) map[r.requisite_type] = r
    requisites.value = map
    templates.value = tRes.data
  } catch {}
}

function triggerRequisiteUpload(type) {
  requisiteInputs.value[type]?.click()
}

async function onRequisiteFileSelected(type, e) {
  const file = e.target.files?.[0]
  if (!file) return
  try {
    await contractDocsApi.uploadRequisite(type, file)
    await loadDocTemplates()
    $q.notify({ type: 'positive', message: 'Реквизит загружен', timeout: 2000 })
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка загрузки', timeout: 2000 })
  } finally {
    e.target.value = ''
  }
}

async function deleteRequisite(type) {
  try {
    await contractDocsApi.deleteRequisite(type)
    await loadDocTemplates()
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка удаления', timeout: 2000 })
  }
}

function triggerTemplateUpload(projectType, docType, clientType) {
  templateInputs.value[`${projectType}::${docType}::${clientType}`]?.click()
}

async function onTemplateFileSelected(projectType, docType, clientType, e) {
  const file = e.target.files?.[0]
  if (!file) return
  try {
    await contractDocsApi.uploadTemplate(projectType, docType, clientType, file)
    await loadDocTemplates()
    $q.notify({ type: 'positive', message: 'Шаблон загружен', timeout: 2000 })
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка загрузки', timeout: 2000 })
  } finally {
    e.target.value = ''
  }
}

async function deleteTemplate(projectType, docType, clientType) {
  try {
    await contractDocsApi.deleteTemplate(projectType, docType, clientType)
    await loadDocTemplates()
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка удаления', timeout: 2000 })
  }
}

// ─────────────────────────────────────────────────────────────────────────────

// === Шаблоны состава проекта ===

const compositionSlots = [
  {
    type: 'Индивидуальный',
    label: 'Индивидуальный проект',
    subtypes: ['Полный (с 3д визуализацией)', 'Эскизный (с коллажами)', 'Планировочный'],
  },
  {
    type: 'Шаблонный',
    label: 'Шаблонный проект',
    subtypes: ['Стандарт', 'Стандарт с визуализацией', 'Проект ванной комнаты', 'Проект ванной комнаты с визуализацией'],
  },
]

const compositionTemplates = ref([])
const compositionInputs = ref({})
const activeCompositionClientType = ref('физ')

function getCompositionTemplate(projectType, subtype, clientType = 'физ') {
  return compositionTemplates.value.find(
    t => t.project_type === projectType && t.project_subtype === subtype && (t.client_type || 'физ') === clientType,
  ) || null
}

function setCompositionInput(projectType, subtype, clientType, el) {
  compositionInputs.value[`${projectType}::${subtype}::${clientType}`] = el
}

function triggerCompositionUpload(projectType, subtype, clientType) {
  compositionInputs.value[`${projectType}::${subtype}::${clientType}`]?.click()
}

async function loadCompositionTemplates() {
  try {
    const { data } = await contractDocsApi.getCompositionTemplates()
    compositionTemplates.value = data
  } catch {}
}

async function onCompositionFileSelected(projectType, subtype, clientType, e) {
  const file = e.target.files?.[0]
  if (!file) return
  try {
    await contractDocsApi.uploadCompositionTemplate(projectType, subtype, clientType, file)
    await loadCompositionTemplates()
    $q.notify({ type: 'positive', message: 'Шаблон состава загружен', timeout: 2000 })
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка загрузки', timeout: 2000 })
  } finally {
    e.target.value = ''
  }
}

async function deleteCompositionTemplate(projectType, subtype, clientType) {
  try {
    await contractDocsApi.deleteCompositionTemplate(projectType, subtype, clientType)
    await loadCompositionTemplates()
    $q.notify({ type: 'info', message: 'Шаблон состава удалён', timeout: 2000 })
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка удаления', timeout: 2000 })
  }
}

// ─────────────────────────────────────────────────────────────────────────────

// === Шаблоны анкет ТЗ ===
const tzSurveyProjectType = ref('Индивидуальный')
const tzSurveyTemplate = ref(null)
const tzSurveyTemplateData = ref(null)
const tzSurveyTemplateLoading = ref(false)
const tzSurveyTemplateSaving = ref(false)
const tzSurveyTemplateResetting = ref(false)
const tzSurveyTemplateJson = ref('')
const tzSurveyTemplateJsonError = ref('')
const tzEditorMode = ref('visual')

function onJsonEdit(val) {
  tzSurveyTemplateJsonError.value = ''
  try {
    tzSurveyTemplateData.value = JSON.parse(val)
  } catch {
    // ошибку покажем при сохранении
  }
}

watch(tzSurveyTemplateData, (val) => {
  if (tzEditorMode.value === 'visual' && val) {
    tzSurveyTemplateJson.value = JSON.stringify(val, null, 2)
  }
}, { deep: true })

watch(tzEditorMode, (mode) => {
  if (mode === 'json' && tzSurveyTemplateData.value) {
    tzSurveyTemplateJson.value = JSON.stringify(tzSurveyTemplateData.value, null, 2)
  }
  if (mode === 'visual') {
    try {
      if (tzSurveyTemplateJson.value) {
        tzSurveyTemplateData.value = JSON.parse(tzSurveyTemplateJson.value)
      }
    } catch {
      $q.notify({ type: 'warning', message: 'JSON содержит ошибки, визуальный режим недоступен' })
      tzEditorMode.value = 'json'
    }
  }
})

async function loadTzSurveyTemplate() {
  if (tzSurveyTemplateLoading.value) return
  try {
    tzSurveyTemplateLoading.value = true
    tzSurveyTemplateJsonError.value = ''
    const { data } = await tzApi.getTemplate(tzSurveyProjectType.value)
    tzSurveyTemplate.value = data
    tzSurveyTemplateData.value = data.template_data
    tzSurveyTemplateJson.value = JSON.stringify(data.template_data, null, 2)
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка загрузки шаблона анкеты' })
  } finally {
    tzSurveyTemplateLoading.value = false
  }
}

async function saveTzSurveyTemplate() {
  let dataToSave = tzSurveyTemplateData.value
  if (tzEditorMode.value === 'json') {
    try {
      dataToSave = JSON.parse(tzSurveyTemplateJson.value)
    } catch {
      tzSurveyTemplateJsonError.value = 'Невалидный JSON'
      return
    }
  }
  tzSurveyTemplateJsonError.value = ''
  try {
    tzSurveyTemplateSaving.value = true
    await tzApi.updateTemplate(tzSurveyProjectType.value, dataToSave)
    $q.notify({ type: 'positive', message: 'Шаблон сохранён' })
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка сохранения шаблона' })
  } finally {
    tzSurveyTemplateSaving.value = false
  }
}

async function resetTzSurveyTemplate() {
  try {
    tzSurveyTemplateResetting.value = true
    const { data } = await tzApi.resetTemplate(tzSurveyProjectType.value)
    tzSurveyTemplate.value = data
    tzSurveyTemplateData.value = data.template_data
    tzSurveyTemplateJson.value = JSON.stringify(data.template_data, null, 2)
    tzSurveyTemplateJsonError.value = ''
    $q.notify({ type: 'positive', message: 'Шаблон сброшен к начальному' })
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка сброса шаблона' })
  } finally {
    tzSurveyTemplateResetting.value = false
  }
}

onMounted(async () => {
  loadRates()
  loadCitiesFull()
  loadDocTemplates()
  loadCompositionTemplates()
  try {
    const { data } = await api.get('/api/v1/employees')
    inviteEmployeeOpts.value = data.filter(e => e.status === 'активный').map(e => ({ label: `${e.full_name} (${e.email || 'нет email'})`, value: e.id }))
  } catch {}
})
</script>

<style scoped>
/* ─── Строки шаблонов / реквизитов ─── */
.tmpl-row {
  display: flex;
  align-items: center;
  padding: 10px 14px;
  min-height: 44px;
}

.tmpl-label {
  font-size: 13px;
  color: var(--fc-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 1;
  min-width: 0;
  max-width: 42%;
}

.tmpl-dots {
  flex: 1;
  min-width: 4px;
  border-bottom: 1px dotted var(--fc-border);
  margin: 0 8px;
  margin-bottom: 2px;
  align-self: flex-end;
}

.tmpl-right {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.tmpl-filename {
  font-size: 12px;
  color: var(--fc-text-light);
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tmpl-empty {
  font-size: 12px;
  color: var(--fc-text-muted);
  white-space: nowrap;
}

.tmpl-btn {
  min-width: 82px;
}

.nd-group-header {
  background: var(--fc-accent);
  color: var(--fc-text);
  font-size: 12px;
  font-weight: 700;
  padding: 5px 12px;
}

.nd-subheader {
  background: var(--fc-bg-alt) !important;
}

.nd-btn {
  height: 30px;
  padding: 0 10px;
  border: 1px solid var(--fc-text-disabled);
  border-radius: 4px;
  background: var(--fc-bg);
  color: var(--fc-text);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  outline: none;
}

.nd-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.nd-btn-save {
  background: #4caf50;
  border-color: #4caf50;
  color: white;
}

.nd-btn-reset {
  border-color: #e74c3c;
  color: #e74c3c;
}

.nd-btn-cancel {
  background: var(--fc-bg-alt);
  border-color: var(--fc-border-card);
}

.nd-btn-export {
  border-color: var(--fc-link);
  color: var(--fc-link);
}

.nd-out-of-scope {
  background: var(--fc-bg-alt) !important;
}

.nd-formula-hint {
  color: var(--fc-text-light);
  line-height: 1.7;
}

.nd-formula-hint div {
  margin-bottom: 1px;
}
</style>
