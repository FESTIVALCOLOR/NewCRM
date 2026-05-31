<template>
  <q-page padding>
    <q-tabs
      v-model="tab"
      dense
      active-color="dark"
      indicator-color="accent"
      no-caps
      class="q-mb-md"
      style="color: #666"
      align="left"
    >
      <q-tab name="rates" label="Тарифы" />
      <q-tab name="agents" label="Агенты" />
      <q-tab name="cities" label="Города" />
      <q-tab name="roles" label="Роли" />
      <q-tab name="normdays" label="Нормодни" />
      <q-tab name="telegram" label="Telegram/Email" />
      <q-tab name="trash" label="Корзина" />
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
          style="color: #888"
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
                <div class="text-weight-bold" style="font-size: 12px; color: #333">
                  {{ rate.role }}
                </div>
                <div class="text-caption" style="color: #888">
                  <span v-if="rateTab === 'individual'" style="color: #2F5496; font-weight: 600">{{ rate.project_subtype || 'все подтипы' }}</span>
                  <span v-if="rate.stage_name"> | {{ rate.stage_name }}</span>
                  <span v-if="rate.city"> | {{ rate.city }}</span>
                  <span v-if="rate.area_from"> | {{ rate.area_from }}-{{ rate.area_to }} м²</span>
                </div>
              </div>
              <div class="text-weight-bold q-mr-sm" style="color: #333">
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
        <div v-if="filteredRates.length === 0" class="text-center q-pa-md" style="color: #999">
          Нет тарифов
        </div>

        <!-- =================== ВЫЕЗДЫ НАДЗОРА =================== -->
        <div v-if="rateTab === 'supervision'" class="q-mt-md q-mb-xs">
          <div class="text-caption text-weight-bold q-px-sm q-mb-xs" style="color: #888; text-transform: uppercase; font-size: 11px">
            Тарифы за выезды
          </div>
          <q-card v-for="vr in visitRates" :key="'v_' + vr.id" class="is-card q-mb-xs">
            <q-card-section class="q-pa-sm">
              <div class="row items-center justify-between">
                <div style="flex: 1">
                  <div class="text-weight-bold" style="font-size: 12px; color: #333">
                    {{ vr.role }}
                  </div>
                  <div class="text-caption" style="color: #888">
                    {{ vr.city }}
                  </div>
                </div>
                <div class="text-weight-bold q-mr-sm" style="color: #333">
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
            style="background: #f5f5f5; color: #555; border-radius: 8px; width: 100%; margin-top: 4px"
            @click="addVisitRate"
          />
        </div>

        <!-- =================== ЕЖЕМЕСЯЧНЫЕ ТАРИФЫ НАДЗОРА =================== -->
        <div v-if="rateTab === 'supervision_monthly'" class="q-mt-md q-mb-xs">
          <div class="text-caption text-weight-bold q-px-sm q-mb-xs" style="color: #888; text-transform: uppercase; font-size: 11px">
            Ежемесячные тарифы надзора
          </div>
          <div class="text-caption q-px-sm q-mb-sm" style="color: #aaa; font-size: 11px">
            Фиксированная ставка назначается сотруднику в карточке надзора. Если город не указан — действует для всех городов.
          </div>
          <q-card v-for="mr in monthlyRates" :key="'m_' + mr.id" class="is-card q-mb-xs">
            <q-card-section class="q-pa-sm">
              <div class="row items-center justify-between">
                <div style="flex: 1">
                  <div class="text-weight-bold" style="font-size: 12px; color: #333">
                    {{ mr.role }}
                  </div>
                  <div class="text-caption" style="color: #888">
                    {{ mr.city || 'Все города' }}
                  </div>
                </div>
                <div class="text-weight-bold q-mr-sm" style="color: #333">
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
            style="background: #f5f5f5; color: #555; border-radius: 8px; width: 100%; margin-top: 4px"
            @click="addMonthlyRate"
          />
        </div>

        <q-page-sticky position="bottom-right" :offset="[18, 18]">
          <q-btn
            v-if="rateTab !== 'supervision_monthly'"
            fab
            icon="add"
            style="background: #ffd93c; color: #333"
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
              <q-item-section style="color: #333">
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
          <q-btn fab icon="add" style="background: #ffd93c; color: #333" @click="addAgent" />
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
              <q-item-section style="color: #333">
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
          <q-btn fab icon="add" style="background: #ffd93c; color: #333" @click="addCity" />
        </q-page-sticky>
      </q-tab-panel>

      <!-- РОЛИ — права по блокам -->
      <q-tab-panel name="roles" class="q-pa-none">
        <q-card class="is-card q-mb-md">
          <q-card-section class="q-pb-none">
            <div class="text-subtitle2 text-weight-bold" style="color: #333">
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
              <q-item-section style="color: #333">
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
              <div class="col-auto text-caption" style="color: #555; line-height: 1.8">
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
                    <q-item-label class="text-weight-bold" style="font-size: 11px; color: #555">
                      {{ nd.stage_name }}
                    </q-item-label>
                  </q-item-section>
                </q-item>
                <!-- Запись нормодней -->
                <q-item v-else :class="{ 'nd-out-of-scope': !nd.is_in_contract_scope }">
                  <q-item-section>
                    <q-item-label style="font-size: 11px; color: #333">
                      {{ nd.stage_name }}
                    </q-item-label>
                    <q-item-label caption style="color: #888">
                      {{ nd.executor_role }}<span v-if="!nd.is_in_contract_scope" style="color: #e74c3c"> · вне объёма</span>
                    </q-item-label>
                  </q-item-section>
                  <!-- Просмотр -->
                  <q-item-section v-if="!ndEditMode" side style="text-align: right; min-width: 72px">
                    <div class="text-weight-bold" style="font-size: 12px; color: #333">
                      {{ ndPreviewMap[nd.stage_code] !== undefined ? ndPreviewMap[nd.stage_code] : (nd.base_norm_days ?? '—') }} дн.
                    </div>
                    <div v-if="ndProjectType === 'Индивидуальный' && nd.k_multiplier > 0" class="text-caption" style="color: #aaa; font-size: 9px">
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
                <div class="text-weight-bold" style="font-size: 12px; color: #333">
                  Итого по договору
                </div>
                <div class="text-weight-bold" style="font-size: 14px; color: #333">
                  {{ ndContractTerm }} дн.
                </div>
              </div>
              <div class="row items-center justify-between">
                <div class="text-caption" style="color: #777">
                  Итого с учётом вне объёма
                </div>
                <div class="text-caption text-weight-bold" style="color: #777">
                  {{ ndTotalAll }} дн.
                </div>
              </div>
            </q-card-section>
          </q-card>
        </template>
        <q-card v-else class="is-card">
          <q-card-section class="text-center" style="color: #999">
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
            style="border-bottom: 2px solid #e0e0e0"
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
                  <div class="text-subtitle2 text-weight-bold q-mb-md" style="color: #333">
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
                  <div class="text-caption text-weight-bold q-mb-sm" style="color: #555">
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
                  <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: #333">
                    Тестовое уведомление
                  </div>
                  <q-btn
                    unelevated
                    no-caps
                    label="Отправить тестовое уведомление"
                    icon="send"
                    style="background: #ffd93c; color: #333; border-radius: 4px"
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
                  style="background: #ffd93c; color: #333; border-radius: 4px"
                  :loading="settingsSaving"
                  @click="saveMessengerSettings"
                />
              </div>
            </q-tab-panel>

            <!-- ─── Email SMTP ─── -->
            <q-tab-panel name="smtp" class="q-pa-none">
              <q-card class="is-card q-mb-md">
                <q-card-section>
                  <div class="text-subtitle2 text-weight-bold q-mb-md" style="color: #333">
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
                  style="background: #ffd93c; color: #333; border-radius: 4px"
                  :loading="settingsSaving"
                  @click="saveMessengerSettings"
                />
              </div>
            </q-tab-panel>

            <!-- ─── Welcome письма ─── -->
            <q-tab-panel name="welcome" class="q-pa-none">
              <q-card class="is-card q-mb-md">
                <q-card-section>
                  <div class="text-subtitle2 text-weight-bold q-mb-md" style="color: #333">
                    Welcome письма
                  </div>

                  <!-- Письмо сотруднику -->
                  <div class="text-caption text-weight-bold q-mb-xs" style="color: #555">
                    Письмо сотруднику
                  </div>
                  <div class="text-caption q-mb-sm" style="color: #888">
                    Отправляется новому сотруднику при добавлении в систему. Содержит логин, пароль и ссылку на Telegram-бот.
                  </div>
                  <div class="row q-gutter-sm q-mb-lg">
                    <q-btn
                      unelevated
                      no-caps
                      label="Просмотр"
                      icon="visibility"
                      style="background: #f5f5f5; color: #333; border: 1px solid #ddd; border-radius: 4px"
                      @click="previewEmail('employee')"
                    />
                    <q-btn
                      unelevated
                      no-caps
                      label="Редактировать"
                      icon="edit"
                      style="background: #ffd93c; color: #333; border-radius: 4px"
                      @click="editEmail('employee')"
                    />
                  </div>

                  <!-- Письмо клиенту -->
                  <div class="text-caption text-weight-bold q-mb-xs" style="color: #555">
                    Приглашение клиенту
                  </div>
                  <div class="text-caption q-mb-sm" style="color: #888">
                    Отправляется клиенту при создании проектного Telegram-чата. Содержит ссылку-приглашение и данные проекта.
                  </div>
                  <div class="row q-gutter-sm">
                    <q-btn
                      unelevated
                      no-caps
                      label="Просмотр"
                      icon="visibility"
                      style="background: #f5f5f5; color: #333; border: 1px solid #ddd; border-radius: 4px"
                      @click="previewEmail('client')"
                    />
                    <q-btn
                      unelevated
                      no-caps
                      label="Редактировать"
                      icon="edit"
                      style="background: #ffd93c; color: #333; border-radius: 4px"
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
                  <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: #333">
                    Приглашения сотрудникам
                  </div>
                  <div class="text-caption q-mb-md" style="color: #888">
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
                  <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: #333">
                    Telegram-токены сотрудников
                  </div>
                  <div class="text-caption q-mb-md" style="color: #888">
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
                        <span style="font-size: 12px; color: #333">{{ tgInfo.telegram_connected ? 'Telegram подключён' : 'Не подключён' }}</span>
                      </div>
                      <template v-if="tgInfo.token_command">
                        <div class="text-caption q-mb-xs" style="color: #888">
                          Инструкция для сотрудника:
                        </div>
                        <div style="background: #F5F5F5; border-radius: 6px; padding: 8px; font-family: monospace; font-size: 11px; color: #333; word-break: break-all">
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
                      <div v-else class="text-caption" style="color: #999">
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
          <div class="text-subtitle2 text-weight-bold" style="color: #333">
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

        <div v-else-if="deletedContracts.length === 0" class="text-center q-pa-xl" style="color: #aaa">
          <q-icon name="delete_outline" size="48px" class="q-mb-sm" />
          <div>Корзина пуста</div>
        </div>

        <template v-else>
          <q-card v-for="item in deletedContracts" :key="item.id" class="is-card q-mb-xs">
            <q-card-section class="q-pa-sm">
              <div class="row items-start justify-between no-wrap" style="gap: 8px">
                <div class="col-grow" style="min-width: 0">
                  <div class="text-weight-bold" style="font-size: 13px; color: #333">
                    № {{ item.contract_number || '—' }} · {{ item.client_name }}
                  </div>
                  <div class="text-caption" style="color: #888">
                    {{ item.address }} · {{ item.project_type }}
                    <span v-if="item.project_subtype"> ({{ item.project_subtype }})</span>
                  </div>
                  <div class="text-caption" style="color: #aaa; font-size: 10px; margin-top: 2px">
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
    </q-tab-panels>

    <!-- Диалог прав роли — ПО БЛОКАМ -->
    <q-dialog v-model="showRoleDialog" maximized transition-show="slide-up" transition-hide="slide-down">
      <q-card>
        <q-toolbar style="background: #ffd93c; color: #333">
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
            style="border: 1px solid #333; border-radius: 8px; color: #333"
            @click="saveRolePermissions"
          />
        </q-toolbar>
        <q-card-section style="max-height: calc(100vh - 50px); overflow-y: auto">
          <div v-for="(perms, group) in permissionsByGroup" :key="group" class="q-mb-md">
            <div class="text-subtitle2 text-weight-bold q-mb-xs" style="color: #333; border-bottom: 1px solid #E0E0E0; padding-bottom: 4px">
              {{ group }}
            </div>
            <q-list dense>
              <q-item v-for="perm in perms" :key="perm.name" tag="label" dense>
                <q-item-section>
                  <q-item-label style="font-size: 11px; color: #333">
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
        <q-toolbar style="background: #ffd93c; color: #333">
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
            style="background: #ffd93c; color: #333; border-radius: 8px"
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
            style="background: #ffd93c; color: #333"
            :disable="!editingMonthlyRate.role || !editingMonthlyRate.fixed_price"
            @click="saveMonthlyRate"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог превью email письма -->
    <q-dialog v-model="emailPreviewDialog" maximized>
      <q-card style="display:flex; flex-direction:column; height:100%">
        <q-bar style="background: #333; color: white">
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
        <q-bar style="background: #333; color: white">
          <q-icon name="edit" />
          <div class="q-ml-sm">
            Редактор: {{ emailEditorType === 'employee' ? 'Письмо сотруднику' : 'Приглашение клиенту' }}
          </div>
          <q-space />
          <q-btn v-close-popup dense flat icon="close" />
        </q-bar>
        <div class="q-pa-sm" style="flex:1; display:flex; flex-direction:column; overflow:hidden">
          <div class="text-caption q-mb-xs" style="color: #888">
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
          <div class="text-caption q-mb-sm" style="color: #aaa">
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
        <q-card-actions align="right" style="border-top: 1px solid #e0e0e0">
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
            style="background: #ffd93c; color: #333"
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
import { deletedContractsApi, messengerApi } from 'src/services/api'

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
  'Договоры': ['contracts.create', 'contracts.view', 'contracts.update', 'contracts.delete'],
  'CRM': ['crm_cards.update', 'crm_cards.view_archive', 'crm_cards.move', 'crm_cards.delete', 'crm_cards.assign_executor', 'crm_cards.delete_executor', 'crm_cards.reset_stages', 'crm_cards.reset_approval', 'crm_cards.complete_approval', 'crm_cards.reset_designer', 'crm_cards.reset_draftsman', 'crm_cards.files_upload', 'crm_cards.files_delete', 'crm_cards.deadlines', 'crm_cards.payments'],
  'Надзор': ['supervision.view_archive', 'supervision.update', 'supervision.move', 'supervision.pause_resume', 'supervision.complete_stage', 'supervision.delete_order', 'supervision.assign_executor', 'supervision.files_upload', 'supervision.files_delete', 'supervision.deadlines', 'supervision.payments'],
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
  supervision: ['Разработка КД', 'Авторский надзор', 'Согласование проекта'],
  surveyor: [],
}

const stageOptions = computed(() => STAGES_BY_TAB[rateTab.value] || [])

const filteredRates = computed(() => {
  if (rateTab.value === 'surveyor') return rates.value.filter(r => r.role === 'Замерщик')
  if (rateTab.value === 'supervision') return rates.value.filter(r => r.project_type === 'Авторский надзор' && !r.fixed_price)
  return rates.value.filter(r => r.project_type === rateTypeMap[rateTab.value])
})

const visitRates = computed(() =>
  rates.value.filter(r => r.project_type === 'Авторский надзор' && r.fixed_price != null && r.city && r.project_subtype !== 'monthly'),
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
    .sub { color: #666; margin-bottom: 14px; font-size: 11px; }
    table { border-collapse: collapse; width: 100%; }
    th { background: #ffd93c; color: #333; font-weight: bold; padding: 5px 8px; text-align: left; border: 1px solid #ddd; }
    td { padding: 4px 8px; border: 1px solid #eee; vertical-align: middle; }
    .grp { color: #555; font-size: 10px; width: 22%; }
    .num { text-align: right; width: 10%; white-space: nowrap; }
    .sub-hdr td { background: #f0f0f0; font-weight: bold; font-size: 10px; color: #444; }
    .out td { color: #aaa; }
    .total-row td { border-top: 2px solid #333; font-size: 12px; }
    .total-sub td { color: #888; }
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

watch(tab, (val) => {
  if (val === 'trash') loadTrash()
  if (val === 'normdays') loadNormDays()
  if (val === 'telegram') loadMessengerSettings()
})

onMounted(async () => {
  loadRates()
  loadCitiesFull()
  try {
    const { data } = await api.get('/api/v1/employees')
    inviteEmployeeOpts.value = data.filter(e => e.status === 'активный').map(e => ({ label: `${e.full_name} (${e.email || 'нет email'})`, value: e.id }))
  } catch {}
})
</script>

<style scoped>
.nd-group-header {
  background: #ffd93c;
  color: #333;
  font-size: 12px;
  font-weight: 700;
  padding: 5px 12px;
}

.nd-subheader {
  background: #f5f5f5 !important;
}

.nd-btn {
  height: 30px;
  padding: 0 10px;
  border: 1px solid #bbb;
  border-radius: 4px;
  background: white;
  color: #333;
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
  background: #f5f5f5;
  border-color: #ccc;
}

.nd-btn-export {
  border-color: #2196f3;
  color: #2196f3;
}

.nd-out-of-scope {
  background: #f5f5f5 !important;
}

.nd-formula-hint {
  color: #888;
  line-height: 1.7;
}

.nd-formula-hint div {
  margin-bottom: 1px;
}
</style>
