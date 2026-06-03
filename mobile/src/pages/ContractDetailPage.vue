<template>
  <q-page padding>
    <template v-if="contract">
      <!-- Шапка -->
      <q-card class="is-card q-mb-md" style="position: relative">
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
              <div class="text-subtitle1 text-weight-bold" style="color: #555">
                {{ contract.contract_number }}
              </div>
              <div class="row items-center q-mt-xs">
                <q-icon
                  v-if="contract.address"
                  name="location_on"
                  size="16px"
                  color="red"
                  class="q-mr-xs cursor-pointer"
                  @click="openMap(contract.address)"
                />
                <div class="text-body2" style="color: #333; flex: 1">
                  {{ contract.address }}
                </div>
              </div>
            </div>
            <div class="column items-end q-gutter-xs q-ml-sm" style="flex-shrink: 0">
              <q-badge :color="statusColor(contract.status)" :label="contract.status" style="min-width: 100px; justify-content: center; padding: 5px 8px; font-size: 11px" />
              <q-badge v-if="contract.agent_type" text-color="white" :style="{ background: agentColor, minWidth: '100px', justifyContent: 'center', padding: '5px 8px', fontSize: '11px' }" :label="contract.agent_type" />
            </div>
          </div>
          <div class="row items-center text-caption q-mt-xs" style="color: #888; gap: 0">
            <span v-if="contract.project_type">{{ contract.project_type }}</span>
            <span v-if="contract.project_subtype" style="color: #ccc; margin: 0 6px">|</span>
            <span v-if="contract.project_subtype">{{ contract.project_subtype }}</span>
            <span v-if="contract.area" style="color: #ccc; margin: 0 6px">|</span>
            <span v-if="contract.area">{{ contract.area }} м²</span>
            <span v-if="contract.city" style="color: #ccc; margin: 0 6px">|</span>
            <span v-if="contract.city">{{ contract.city }}</span>
            <span v-if="contract.floors" style="color: #ccc; margin: 0 6px">|</span>
            <span v-if="contract.floors">{{ contract.floors }} эт.</span>
          </div>
        </q-card-section>
      </q-card>

      <!-- Сетка: в ландшафте 2 колонки (левая=данные, правая=документы) -->
      <div class="contract-detail-grid">
        <!-- Левая колонка: клиент, данные, платежи, документы, акты, опрос -->
        <div class="contract-left-col">
          <!-- Клиент (ФИО со ссылкой + контакты) -->
          <q-card v-if="contract.client_name || contract.client_id" class="is-card q-mb-md">
            <q-item v-ripple clickable @click="goToClient">
              <q-item-section avatar>
                <q-icon name="person" color="grey-7" />
              </q-item-section>
              <q-item-section>
                <q-item-label caption>
                  Клиент
                </q-item-label>
                <q-item-label class="text-weight-bold" style="color: #333">
                  {{ clientDisplayName }}
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-icon name="chevron_right" color="grey-5" />
              </q-item-section>
            </q-item>
            <!-- Контакты клиента -->
            <div v-if="clientData" class="row q-col-gutter-xs q-px-md q-pb-sm" style="border-top: 1px solid #F5F5F5; padding-top: 8px">
              <div v-if="clientData.phone" class="col-auto">
                <a :href="`tel:${clientData.phone}`" class="contact-chip">
                  <q-icon name="phone" size="12px" />
                  {{ clientData.phone }}
                </a>
              </div>
              <div v-if="clientData.telegram_account" class="col-auto">
                <a :href="clientTelegramLink(clientData.telegram_account)" class="contact-chip contact-chip--tg" target="_blank">
                  <q-icon name="send" size="12px" />
                  {{ clientData.telegram_account }}
                </a>
              </div>
              <div v-if="clientData.email" class="col-auto">
                <a :href="`mailto:${clientData.email}`" class="contact-chip">
                  <q-icon name="email" size="12px" />
                  {{ clientData.email }}
                </a>
              </div>
            </div>
          </q-card>

          <!-- Основные данные -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">
                Основные данные
              </div>
            </q-card-section>
            <q-card-section>
              <div class="row">
                <!-- Колонка 1: Дата, Срок -->
                <div class="col-6" style="padding-right: 12px; border-right: 1px solid #E0E0E0">
                  <div v-if="contract.contract_date" class="q-mb-sm">
                    <div class="text-caption" style="color: #999">
                      Дата договора
                    </div>
                    <div style="font-size: 13px; color: #333">
                      {{ fmtDate(contract.contract_date) }}
                    </div>
                  </div>
                  <div v-if="contract.contract_period" class="q-mb-sm">
                    <div class="text-caption" style="color: #999">
                      Срок договора
                    </div>
                    <div style="font-size: 13px; color: #333">
                      {{ contract.contract_period }} раб. дней
                    </div>
                  </div>
                  <div v-if="contract.deadline || crmDeadline" class="q-mb-sm">
                    <div class="text-caption" style="color: #999">
                      Дедлайн проекта
                    </div>
                    <div style="font-size: 13px; color: #333">
                      {{ fmtDate(contract.deadline || crmDeadline) }}
                    </div>
                  </div>
                </div>
                <!-- Колонка 2: Сумма, Площадь, Город -->
                <div class="col-6" style="padding-left: 12px">
                  <div v-if="contract.total_amount" class="q-mb-sm">
                    <div class="text-caption" style="color: #999">
                      Сумма договора
                    </div>
                    <div style="font-size: 13px; color: #333; font-weight: bold">
                      {{ fmtMoney(contract.total_amount) }}
                    </div>
                  </div>
                  <div v-if="contract.area" class="q-mb-sm">
                    <div class="text-caption" style="color: #999">
                      Площадь
                    </div>
                    <div style="font-size: 13px; color: #333">
                      {{ contract.area }} м²
                    </div>
                  </div>
                  <div v-if="contract.city">
                    <div class="text-caption" style="color: #999">
                      Город
                    </div>
                    <div style="font-size: 13px; color: #333">
                      {{ contract.city }}
                    </div>
                  </div>
                </div>
              </div>
              <!-- Комментарий — на всю ширину -->
              <div v-if="contract.comments" class="q-mt-md" style="border-top: 1px solid #F0F0F0; padding-top: 8px">
                <div class="text-caption" style="color: #999">
                  Комментарий
                </div>
                <div style="font-size: 13px; color: #333">
                  {{ contract.comments }}
                </div>
              </div>
            </q-card-section>
          </q-card>

          <!-- Платежи от клиента (индивидуальный) -->
          <q-card v-if="contract.project_type === 'Индивидуальный'" class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">
                Платежи от клиента
              </div>
            </q-card-section>
            <q-list dense separator>
              <q-item v-for="pay in clientPayments" :key="pay.key">
                <q-item-section>
                  <q-item-label class="text-weight-medium">
                    {{ pay.label }}
                  </q-item-label>
                  <q-item-label class="text-weight-bold" style="color: #333">
                    {{ fmtMoney(pay.amount) }}
                  </q-item-label>
                  <q-item-label caption :style="{ color: pay.paidDate ? '#27AE60' : '#888' }">
                    {{ pay.paidDate ? `Оплачено ${fmtDate(pay.paidDate)}` : 'Не оплачено' }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side style="min-width: 110px">
                  <div class="column q-gutter-xs items-stretch">
                    <q-btn
                      v-if="!pay.paidDate"
                      outline
                      dense
                      size="sm"
                      icon="check_circle"
                      label="Оплатить"
                      color="positive"
                      no-caps
                      style="border-radius: 4px; min-width: 105px; height: 30px"
                      @click="pickPayDate(pay.key)"
                    />
                    <q-badge v-else color="positive" style="padding: 6px 12px; font-size: 11px; border-radius: 4px; min-width: 105px; justify-content: center; height: 30px; display: flex; align-items: center">
                      Оплачено
                      <q-btn
                        flat
                        round
                        dense
                        size="xs"
                        icon="close"
                        color="white"
                        class="q-ml-xs"
                        style="margin: -4px -4px -4px 0"
                        @click.stop="cancelPayment(pay.key)"
                      />
                    </q-badge>
                    <q-btn
                      outline
                      dense
                      size="sm"
                      icon="upload_file"
                      label="Чек"
                      no-caps
                      style="color: #333; border-color: #ffd93c; border-radius: 4px; min-width: 105px; height: 30px"
                      @click="uploadReceipt(pay.key)"
                    />
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Шаблонный — 1 платёж -->
          <q-card v-if="contract.project_type === 'Шаблонный'" class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">
                Оплата
              </div>
            </q-card-section>
            <q-list dense>
              <q-item>
                <q-item-section>
                  <q-item-label class="text-weight-bold" style="color: #333">
                    {{ fmtMoney(contract.advance_payment || contract.total_amount) }}
                  </q-item-label>
                  <q-item-label caption :style="{ color: contract.advance_payment_paid_date ? '#27AE60' : '#888' }">
                    {{ contract.advance_payment_paid_date ? `Оплачено ${fmtDate(contract.advance_payment_paid_date)}` : 'Не оплачено' }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side style="min-width: 110px">
                  <q-btn
                    v-if="!contract.advance_payment_paid_date"
                    outline
                    dense
                    size="sm"
                    icon="check_circle"
                    label="Оплатить"
                    color="positive"
                    no-caps
                    style="border-radius: 4px; min-width: 105px"
                    @click="pickPayDate('advance')"
                  />
                  <q-badge v-else color="positive" style="padding: 5px 12px; font-size: 11px; border-radius: 4px; min-width: 105px; justify-content: center">
                    Оплачено
                    <q-btn
                      flat
                      round
                      dense
                      size="xs"
                      icon="close"
                      color="white"
                      class="q-ml-xs"
                      @click.stop="cancelPayment('advance')"
                    />
                  </q-badge>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Файлы: Договор / ТЗ / Доп.соглашения — в ландшафте 3 колонки -->
          <div class="contract-files-grid">
            <!-- Файлы: Договор -->
            <q-card class="is-card q-mb-md">
              <q-card-section class="q-pb-none">
                <div class="text-subtitle2 text-weight-bold" style="color: #333">
                  Договор
                </div>
              </q-card-section>
              <q-list v-if="filesByGroup.documents.length > 0" dense>
                <q-item v-for="f in filesByGroup.documents" :key="f.id" clickable @click="openFile(f)">
                  <q-item-section avatar>
                    <q-icon :name="fileIconByName(f.file_name)" :color="fileColorByName(f.file_name)" />
                  </q-item-section>
                  <q-item-section style="min-width: 0; overflow: hidden">
                    <q-item-label style="font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
                      {{ f.file_name }}
                    </q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <div class="row q-gutter-xs items-center">
                      <q-btn
                        outline
                        dense
                        size="xs"
                        icon="open_in_new"
                        color="primary"
                        no-caps
                        label="Открыть"
                        style="font-size: 10px; padding: 2px 8px; border-radius: 4px"
                        @click.stop="openFile(f)"
                      />
                      <q-btn
                        v-if="canDeleteFiles"
                        outline
                        dense
                        size="xs"
                        icon="delete_outline"
                        color="negative"
                        no-caps
                        style="font-size: 10px; padding: 2px 6px; border-radius: 4px"
                        @click.stop="deleteContractFile(f)"
                      />
                    </div>
                  </q-item-section>
                </q-item>
              </q-list>
              <q-card-section class="q-pt-xs">
                <q-btn
                  outline
                  color="grey-7"
                  icon="gavel"
                  label="Загрузить договор"
                  no-caps
                  class="full-width"
                  dense
                  @click="uploadFor('documents')"
                />
              </q-card-section>
            </q-card>

            <!-- Файлы: ТЗ -->
            <q-card class="is-card q-mb-md">
              <q-card-section class="q-pb-none">
                <div class="text-subtitle2 text-weight-bold" style="color: #333">
                  Техническое задание
                </div>
              </q-card-section>
              <q-list v-if="filesByGroup.tech_task.length > 0" dense>
                <q-item v-for="f in filesByGroup.tech_task" :key="f.id" clickable @click="openFile(f)">
                  <q-item-section avatar>
                    <q-icon :name="fileIconByName(f.file_name)" :color="fileColorByName(f.file_name)" />
                  </q-item-section>
                  <q-item-section style="min-width: 0; overflow: hidden">
                    <q-item-label style="font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
                      {{ f.file_name }}
                    </q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <div class="row q-gutter-xs items-center">
                      <q-btn
                        outline
                        dense
                        size="xs"
                        icon="open_in_new"
                        color="primary"
                        no-caps
                        label="Открыть"
                        style="font-size: 10px; padding: 2px 8px; border-radius: 4px"
                        @click.stop="openFile(f)"
                      />
                      <q-btn
                        v-if="canDeleteFiles"
                        outline
                        dense
                        size="xs"
                        icon="delete_outline"
                        color="negative"
                        no-caps
                        style="font-size: 10px; padding: 2px 6px; border-radius: 4px"
                        @click.stop="deleteContractFile(f)"
                      />
                    </div>
                  </q-item-section>
                </q-item>
              </q-list>
              <q-card-section class="q-pt-xs">
                <q-btn
                  outline
                  color="grey-7"
                  icon="description"
                  label="Загрузить ТЗ"
                  no-caps
                  class="full-width"
                  dense
                  @click="uploadFor('tech_task')"
                />
              </q-card-section>
            </q-card>

            <!-- Файлы: Доп. соглашения -->
            <q-card class="is-card q-mb-md">
              <q-card-section class="q-pb-none">
                <div class="text-subtitle2 text-weight-bold" style="color: #333">
                  Доп. соглашения
                </div>
              </q-card-section>
              <q-list v-if="filesByGroup.supervision.length > 0" dense>
                <q-item v-for="f in filesByGroup.supervision" :key="f.id" clickable @click="openFile(f)">
                  <q-item-section avatar>
                    <q-icon :name="fileIconByName(f.file_name)" :color="fileColorByName(f.file_name)" />
                  </q-item-section>
                  <q-item-section style="min-width: 0; overflow: hidden">
                    <q-item-label style="font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
                      {{ f.file_name }}
                    </q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <div class="row q-gutter-xs items-center">
                      <q-btn
                        outline
                        dense
                        size="xs"
                        icon="open_in_new"
                        color="primary"
                        no-caps
                        label="Открыть"
                        style="font-size: 10px; padding: 2px 8px; border-radius: 4px"
                        @click.stop="openFile(f)"
                      />
                      <q-btn
                        v-if="canDeleteFiles"
                        outline
                        dense
                        size="xs"
                        icon="delete_outline"
                        color="negative"
                        no-caps
                        style="font-size: 10px; padding: 2px 6px; border-radius: 4px"
                        @click.stop="deleteContractFile(f)"
                      />
                    </div>
                  </q-item-section>
                </q-item>
              </q-list>
              <q-card-section class="q-pt-xs">
                <q-btn
                  outline
                  color="grey-7"
                  icon="handshake"
                  label="Загрузить доп. соглашение"
                  no-caps
                  class="full-width"
                  dense
                  @click="uploadFor('supervision')"
                />
              </q-card-section>
            </q-card>
          </div><!-- /contract-files-grid -->

          <!-- Файлы: Акты без подписи -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">
                Акты (без подписи)
              </div>
            </q-card-section>
            <div v-if="filesByGroup.acts.length > 0" class="row q-col-gutter-sm q-pa-sm">
              <div v-for="f in filesByGroup.acts" :key="f.id" class="col-xs-12 col-sm-4">
                <q-card flat bordered class="q-pa-sm" style="border-radius: 4px">
                  <div style="font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #333">
                    {{ f.file_name }}
                  </div>
                  <div class="text-caption" style="color: #888">
                    {{ stageLabel(f.stage) }}
                  </div>
                  <div class="row q-gutter-xs q-mt-xs">
                    <q-btn
                      outline
                      dense
                      size="xs"
                      icon="open_in_new"
                      color="primary"
                      no-caps
                      style="font-size: 9px; padding: 1px 6px; border-radius: 4px; flex: 1"
                      @click="openFile(f)"
                    />
                    <q-btn
                      v-if="canDeleteFiles"
                      outline
                      dense
                      size="xs"
                      icon="delete"
                      color="negative"
                      no-caps
                      style="font-size: 9px; padding: 1px 6px; border-radius: 4px"
                      @click="deleteContractFile(f)"
                    />
                  </div>
                </q-card>
              </div>
            </div>
            <q-card-section class="q-pt-xs">
              <div class="row q-col-gutter-xs">
                <div class="col-4">
                  <q-btn
                    outline
                    color="grey-7"
                    label="Акт ПР"
                    no-caps
                    class="full-width"
                    dense
                    @click="uploadFor('act_pr')"
                  />
                </div>
                <div class="col-4">
                  <q-btn
                    outline
                    color="grey-7"
                    label="Акт КД"
                    no-caps
                    class="full-width"
                    dense
                    @click="uploadFor('act_kd')"
                  />
                </div>
                <div class="col-4">
                  <q-btn
                    outline
                    color="grey-7"
                    label="Акт РЧ"
                    no-caps
                    class="full-width"
                    dense
                    @click="uploadFor('act_rch')"
                  />
                </div>
              </div>
            </q-card-section>
          </q-card>

          <!-- Файлы: Акты с подписью -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">
                Акты (с подписью)
              </div>
            </q-card-section>
            <div v-if="filesByGroup.actsSigned.length > 0" class="row q-col-gutter-sm q-pa-sm">
              <div v-for="f in filesByGroup.actsSigned" :key="f.id" class="col-xs-12 col-sm-4">
                <q-card flat bordered class="q-pa-sm" style="border-radius: 4px">
                  <div style="font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #333">
                    {{ f.file_name }}
                  </div>
                  <div class="text-caption" style="color: #888">
                    {{ stageLabel(f.stage) }}
                  </div>
                  <div class="row q-gutter-xs q-mt-xs">
                    <q-btn
                      outline
                      dense
                      size="xs"
                      icon="open_in_new"
                      color="primary"
                      no-caps
                      style="font-size: 9px; padding: 1px 6px; border-radius: 4px; flex: 1"
                      @click="openFile(f)"
                    />
                    <q-btn
                      v-if="canDeleteFiles"
                      outline
                      dense
                      size="xs"
                      icon="delete"
                      color="negative"
                      no-caps
                      style="font-size: 9px; padding: 1px 6px; border-radius: 4px"
                      @click="deleteContractFile(f)"
                    />
                  </div>
                </q-card>
              </div>
            </div>
            <q-card-section class="q-pt-xs">
              <div class="row q-col-gutter-xs">
                <div class="col-4">
                  <q-btn
                    outline
                    color="grey-7"
                    label="ПР подп."
                    no-caps
                    class="full-width"
                    dense
                    @click="uploadFor('act_pr_signed')"
                  />
                </div>
                <div class="col-4">
                  <q-btn
                    outline
                    color="grey-7"
                    label="КД подп."
                    no-caps
                    class="full-width"
                    dense
                    @click="uploadFor('act_kd_signed')"
                  />
                </div>
                <div class="col-4">
                  <q-btn
                    outline
                    color="grey-7"
                    label="РЧ подп."
                    no-caps
                    class="full-width"
                    dense
                    @click="uploadFor('act_rch_signed')"
                  />
                </div>
              </div>
            </q-card-section>
          </q-card>

          <!-- Блок опросов клиентов -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="row items-center justify-between">
                <div class="text-subtitle2 text-weight-bold" style="color: #333">
                  Опрос клиента
                </div>
                <q-btn
                  v-if="!surveys.some(s => s.status === 'pending' || s.status === 'sent')"
                  unelevated
                  dense
                  no-caps
                  icon="add_task"
                  label="Создать опрос"
                  style="background: #ffd93c; color: #333; font-size: 11px; height: 32px; border-radius: 4px"
                  :loading="surveysLoading"
                  @click="createSurvey"
                />
              </div>
            </q-card-section>
            <q-card-section v-if="surveysLoading" class="text-center">
              <q-spinner size="24px" color="accent" />
            </q-card-section>
            <template v-else-if="surveys.length > 0">
              <q-list dense separator>
                <q-item v-for="s in surveys" :key="s.id">
                  <q-item-section>
                    <q-item-label style="font-size: 12px; font-weight: bold">
                      {{ { individual: 'Индивидуальный', template: 'Шаблонный', supervision: 'Авторский надзор' }[s.project_type] || contract.project_type }}
                    </q-item-label>
                    <q-item-label caption>
                      <q-badge :color="surveyStatusColor(s.status)" :label="surveyStatusLabel(s.status)" dense />
                      <span v-if="s.completed_at" class="q-ml-xs">{{ new Date(s.completed_at).toLocaleDateString('ru-RU') }}</span>
                    </q-item-label>
                    <!-- Результаты опроса -->
                    <template v-if="s.status === 'completed'">
                      <div class="row q-gutter-xs q-mt-xs" style="flex-wrap: wrap">
                        <div v-if="s.nps_score != null" class="text-caption" style="color: #333">
                          NPS: <b>{{ s.nps_score }}</b>/10
                        </div>
                        <div v-if="s.csat_score != null" class="text-caption" style="color: #888">
                          ·
                        </div>
                        <div v-if="s.csat_score != null" class="text-caption" style="color: #333">
                          CSAT: <b>{{ s.csat_score }}</b>/5
                        </div>
                        <div v-if="s.design_score != null" class="text-caption" style="color: #888">
                          ·
                        </div>
                        <div v-if="s.design_score != null" class="text-caption" style="color: #333">
                          Дизайн: <b>{{ s.design_score }}</b>/5
                        </div>
                        <div v-if="s.deadline_score != null" class="text-caption" style="color: #888">
                          ·
                        </div>
                        <div v-if="s.deadline_score != null" class="text-caption" style="color: #333">
                          Сроки: <b>{{ s.deadline_score }}</b>/5
                        </div>
                        <div v-if="s.communication_score != null" class="text-caption" style="color: #888">
                          ·
                        </div>
                        <div v-if="s.communication_score != null" class="text-caption" style="color: #333">
                          Общение: <b>{{ s.communication_score }}</b>/5
                        </div>
                        <div v-if="s.expectations_score != null" class="text-caption" style="color: #888">
                          ·
                        </div>
                        <div v-if="s.expectations_score != null" class="text-caption" style="color: #333">
                          Ожидания: <b>{{ s.expectations_score }}</b>/5
                        </div>
                      </div>
                      <div v-if="s.comment" class="text-caption q-mt-xs" style="color: #666; font-style: italic">
                        "{{ s.comment }}"
                      </div>
                    </template>
                    <!-- Ссылка на опрос (если не завершён) -->
                    <div v-if="s.survey_link && s.status !== 'completed'" class="q-mt-xs">
                      <a :href="s.survey_link" target="_blank" style="color: #1677FF; font-size: 11px; word-break: break-all">{{ s.survey_link }}</a>
                    </div>
                  </q-item-section>
                  <q-item-section side style="flex-shrink: 0">
                    <q-btn
                      v-if="s.status !== 'completed'"
                      flat
                      round
                      dense
                      size="xs"
                      icon="send"
                      color="positive"
                      @click="resendSurvey(s)"
                    >
                      <q-tooltip>Переотправить</q-tooltip>
                    </q-btn>
                  </q-item-section>
                </q-item>
              </q-list>
            </template>
            <q-card-section v-else class="text-center" style="color: #999; font-size: 12px">
              Опросов нет
            </q-card-section>
          </q-card>
        </div><!-- /contract-left-col -->

        <!-- Правая колонка: только таблица сроков -->
        <div class="contract-right-col">
          <!-- Таблица сроков -->
          <q-card class="is-card">
            <div style="padding: 8px 16px; display: flex; align-items: center; gap: 8px">
              <span style="flex: 1; font-weight: 600; font-size: 14px; color: #333">Таблица сроков</span>
              <template v-if="timeline.length > 0">
                <button type="button" class="tl-export-btn" @click="exportTimelineExcel">
                  Excel
                </button>
                <button type="button" class="tl-export-btn" @click="exportTimelinePdf">
                  PDF
                </button>
              </template>
            </div>
            <q-card-section v-if="timeline.length === 0" class="text-center q-py-lg">
              <q-icon name="schedule" size="36px" color="grey-4" class="q-mb-sm" />
              <div style="color: #999; font-size: 13px">
                Таблица сроков не создана
              </div>
              <div style="color: #bbb; font-size: 11px; margin-top: 4px">
                Создайте её в CRM-карточке проекта
              </div>
            </q-card-section>
            <q-list v-else dense separator>
              <q-item
                v-for="entry in timeline"
                :key="entry.id"
                :class="{
                  'bg-green-1': entry.actual_date && !entry.stage_code?.endsWith('_HDR') && entry.executor_role !== 'header' && !((entry.actual_days || 0) > (entry.norm_days || 0) && (entry.norm_days || 0) > 0),
                  'bg-red-1': entry.actual_date && !entry.stage_code?.endsWith('_HDR') && entry.executor_role !== 'header' && (entry.actual_days || 0) > (entry.norm_days || 0) && (entry.norm_days || 0) > 0
                }"
                :style="entry.executor_role === 'header'
                  ? { background: '#EEEEEE', fontWeight: 'bold' }
                  : (entry.stage_code?.endsWith('_HDR')
                    ? { background: '#F5F5F5', fontWeight: '600' }
                    : (entry.status === 'skipped' ? { background: '#FAFAFA', opacity: 0.7 } : {}))"
              >
                <q-item-section avatar>
                  <q-icon
                    :name="entry.status === 'skipped' ? 'block' : (entry.actual_date ? 'check_circle' : 'radio_button_unchecked')"
                    :color="entry.status === 'skipped' ? 'grey-4' : (entry.actual_date ? ((entry.actual_days || 0) > (entry.norm_days || 0) && (entry.norm_days || 0) > 0 ? 'negative' : 'positive') : 'grey-5')"
                    size="16px"
                  />
                </q-item-section>
                <q-item-section>
                  <q-item-label style="font-size: 11px; color: #333" :class="{ 'text-weight-bold': entry.stage_code?.endsWith('_HDR') || entry.executor_role === 'header' }">
                    {{ entry.stage_name }}
                  </q-item-label>
                  <q-item-label caption style="color: #888">
                    <span v-if="entry.norm_days">Норма: {{ entry.custom_norm_days || entry.norm_days }} дн.</span>
                    <span v-if="entry.actual_days"> | Факт: {{ entry.actual_days }} дн.</span>
                    <span v-if="entry.executor_role && entry.executor_role !== 'header'"> | {{ entry.executor_role }}</span>
                    <span v-if="!entry.is_in_contract_scope && entry.executor_role !== 'header' && !entry.stage_code?.endsWith('_HDR')" style="color: #e74c3c; font-style: italic"> | вне объёма</span>
                    <span v-if="entry.status === 'skipped'" style="color: #bbb; font-style: italic"> | Пропущено</span>
                    <span v-if="entry.actual_date && !entry.stage_code?.endsWith('_HDR') && entry.executor_role !== 'header' && (entry.actual_days || 0) > (entry.norm_days || 0) && (entry.norm_days || 0) > 0" style="color: #E74C3C; font-weight: bold"> | Просрочен</span>
                  </q-item-label>
                </q-item-section>
                <q-item-section v-if="entry.actual_date" side>
                  <div class="text-caption" :style="{ color: (entry.actual_days || 0) > (entry.norm_days || 0) && (entry.norm_days || 0) > 0 ? '#E74C3C' : '#27AE60' }">
                    {{ fmtDateShort(entry.actual_date) }}
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
            <!-- ИТОГО таймлайна -->
            <q-card-section v-if="timeline.length > 0" class="q-pa-sm" style="border-top: 1px solid #eee">
              <div class="row items-center justify-between q-mb-xs">
                <div class="text-weight-bold" style="font-size: 11px; color: #333">
                  Итого по договору
                </div>
                <div class="text-weight-bold" style="font-size: 12px; color: #333">
                  {{ timelineTotalInScope }} дн.
                </div>
              </div>
              <div class="row items-center justify-between">
                <div class="text-caption" style="color: #777">
                  Итого с учётом вне объёма
                </div>
                <div class="text-caption text-weight-bold" style="color: #777">
                  {{ timelineTotalAll }} дн.
                </div>
              </div>
            </q-card-section>
          </q-card>
        </div><!-- /contract-right-col -->
      </div><!-- /contract-detail-grid -->

      <!-- Кнопка удаления -->
      <q-btn
        v-if="can('contracts.delete')"
        flat
        color="negative"
        icon="delete"
        label="Удалить договор"
        no-caps
        class="full-width q-mb-md"
        @click="deleteContract"
      />

      <!-- FAB кнопки -->
      <q-page-sticky position="bottom-right" :offset="[18, 18]">
        <q-fab icon="more_vert" direction="up" style="background: #ffd93c; color: #333" vertical-actions-align="right">
          <q-fab-action
            icon="sync"
            style="background: #5DADE2; color: white"
            :loading="syncing"
            label="Синхронизация ЯД"
            external-label
            label-position="left"
            @click="syncWithYd"
          />
          <q-fab-action
            v-if="can('contracts.update')"
            icon="edit"
            style="background: #ffd93c; color: #333"
            label="Редактировать"
            external-label
            label-position="left"
            @click="showEdit = true"
          />
        </q-fab>
      </q-page-sticky>

      <contract-form-dialog v-model="showEdit" :contract="contract" @saved="reload" />

      <!-- Скрытые инпуты для загрузки -->
      <input
        ref="fileInput"
        type="file"
        style="position: absolute; left: -9999px; opacity: 0"
        accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx,.xls,.xlsx,.dwg"
        @change="handleFileUpload"
      >
      <input
        ref="receiptInput"
        type="file"
        style="position: absolute; left: -9999px; opacity: 0"
        accept=".pdf,.jpg,.jpeg,.png"
        @change="handleReceiptUpload"
      >
    </template>

    <div v-else-if="!loading" class="text-center q-pa-xl" style="color: #999">
      <q-icon name="description" size="48px" class="q-mb-sm" /><div>Договор не найден</div>
    </div>
    <div v-else class="text-center q-pa-xl">
      <q-spinner size="40px" color="accent" />
    </div>

    <!-- Диалог оплаты: сумма + дата -->
    <q-dialog v-model="payDialogOpen" persistent>
      <q-card style="min-width: 300px; border-radius: 12px">
        <q-card-section>
          <div class="text-subtitle1 text-weight-bold" style="color: #333">
            Подтвердить оплату
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-input
            v-model="payDialogAmount"
            label="Сумма оплаты, ₽"
            outlined
            dense
            type="number"
            class="q-mb-sm"
          />
          <q-input
            v-model="payDialogDate"
            label="Дата оплаты"
            outlined
            dense
            type="date"
          />
        </q-card-section>
        <q-card-actions align="right" class="q-pt-none">
          <q-btn flat label="Отмена" no-caps @click="payDialogOpen = false" />
          <q-btn
            unelevated
            label="Подтвердить"
            color="positive"
            no-caps
            @click="confirmPay"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { contractsApi, filesApi, crmApi, clientsApi, timelineApi, surveyApi } from 'src/services/api'
import { useReferencesStore } from 'src/stores/references'
import { useAuthStore } from 'src/stores/auth'
import { usePermission } from 'src/composables/usePermission'
import ContractFormDialog from 'src/components/ContractFormDialog.vue'

const { can, isSuperuser } = usePermission()
const authStore = useAuthStore()

// Удаление файлов видно только руководителю и старшему менеджеру
const canDeleteFiles = computed(() => {
  if (isSuperuser.value) return true
  const pos = authStore.user?.position || ''
  return ['Руководитель студии', 'Старший менеджер проектов'].includes(pos)
})

const route = useRoute()
const router = useRouter()
const $q = useQuasar()
const refs = useReferencesStore()
const contract = ref(null)
const files = ref([])
const timeline = ref([])
const loading = ref(true)
const syncing = ref(false)
const showEdit = ref(false)
const fileInput = ref(null)
const receiptInput = ref(null)
const uploadStage = ref('')
const receiptType = ref('')

const agentColor = computed(() => refs.agentByName(contract.value?.agent_type)?.color || '#95A5A6')
const crmDeadline = computed(() => contract.value?.crm_card_deadline || null)

// Опросы клиента
const surveys = ref([])
const surveysLoading = ref(false)

async function loadSurveys() {
  if (!contract.value?.id) return
  surveysLoading.value = true
  try {
    const { data } = await surveyApi.getByContract(contract.value.id)
    surveys.value = Array.isArray(data) ? data : []
  } catch { surveys.value = [] }
  finally { surveysLoading.value = false }
}

const PT_RU_EN = { 'Индивидуальный': 'individual', 'Шаблонный': 'template', 'Авторский надзор': 'supervision' }

async function createSurvey() {
  if (!contract.value) return
  const pt = PT_RU_EN[contract.value.project_type] || 'individual'
  try {
    await surveyApi.create({ contract_id: contract.value.id, project_type: pt })
    $q.notify({ type: 'positive', message: 'Опрос создан' })
    await loadSurveys()
  } catch (e) { $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Ошибка создания опроса' }) }
}

async function resendSurvey(survey) {
  try {
    await surveyApi.resend(survey.id)
    $q.notify({ type: 'positive', message: 'Ссылка обновлена' })
    await loadSurveys()
  } catch (e) { $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Ошибка' }) }
}

function surveyStatusLabel(s) {
  return { pending: 'Ожидает', sent: 'Отправлен', completed: 'Завершён', expired: 'Истёк' }[s] || s
}
function surveyStatusColor(s) {
  return { pending: 'grey-7', sent: 'warning', completed: 'positive', expired: 'negative' }[s] || 'grey-7'
}
function scoreBar(v) { return v != null ? `${v}/10` : '—' }

// ФИО и контакты клиента — загружаем отдельно
const clientName = ref(null)
const clientData = ref(null)
const clientDisplayName = computed(() => {
  if (contract.value?.client_name) return contract.value.client_name
  if (clientData.value?.full_name) return clientData.value.full_name
  if (clientName.value) return clientName.value
  return contract.value?.client_id ? `Клиент #${contract.value.client_id}` : 'Неизвестен'
})

// Платежи клиента (массив для удобства итерации)
const clientPayments = computed(() => {
  if (!contract.value) return []
  return [
    { key: 'advance', label: '1 платёж (Аванс)', amount: contract.value.advance_payment, paidDate: contract.value.advance_payment_paid_date },
    { key: 'additional', label: '2 платёж (Доплата)', amount: contract.value.additional_payment, paidDate: contract.value.additional_payment_paid_date },
    { key: 'third', label: '3 платёж (Доплата)', amount: contract.value.third_payment, paidDate: contract.value.third_payment_paid_date },
  ]
})

// Файлы, сгруппированные по блокам
const filesByGroup = computed(() => {
  const groups = { documents: [], tech_task: [], supervision: [], acts: [], actsSigned: [] }
  const ACT_STAGES = ['act_pr', 'act_kd', 'act_rch', 'acts']
  const ACT_SIGNED_STAGES = ['act_pr_signed', 'act_kd_signed', 'act_rch_signed']
  for (const f of files.value) {
    if (f.stage === 'documents') groups.documents.push(f)
    else if (f.stage === 'tech_task') groups.tech_task.push(f)
    else if (f.stage === 'supervision') groups.supervision.push(f)
    else if (ACT_SIGNED_STAGES.includes(f.stage)) groups.actsSigned.push(f)
    else if (ACT_STAGES.includes(f.stage)) groups.acts.push(f)
    // Совместимость: старые stage-ID только если файл в папке Документы
    else if (['stage1_signed', 'stage2_signed', 'stage3_signed'].includes(f.stage) && f.yandex_path?.includes('Документы')) groups.actsSigned.push(f)
    else if (['stage1', 'stage2_concept', 'stage3'].includes(f.stage) && f.yandex_path?.includes('Документы')) groups.acts.push(f)
  }
  return groups
})

const STAGE_LABELS = {
  act_pr: 'Акт ПР', act_pr_signed: 'Акт ПР (подписанный)',
  act_kd: 'Акт КД', act_kd_signed: 'Акт КД (подписанный)',
  act_rch: 'Акт РЧ', act_rch_signed: 'Акт РЧ (подписанный)',
  stage1: 'Акт ПР', stage1_signed: 'Акт ПР (подписанный)',
  stage2_concept: 'Акт КД', stage2_signed: 'Акт КД (подписанный)',
  stage3: 'Акт РЧ', stage3_signed: 'Акт РЧ (подписанный)',
  tech_task: 'Тех. задание', documents: 'Договор',
  supervision: 'Доп. соглашение', acts: 'Акт',
}
function stageLabel(s) { return STAGE_LABELS[s] || s || '' }
function statusColor(s) { if (!s) return 'grey'; if (s === 'В работе') return 'orange'; if (s.includes('СДАН')) return 'positive'; if (s.includes('РАСТОРГНУТ')) return 'negative'; if (s.includes('НАДЗОР')) return 'purple'; return 'blue' }
function fmtDate(d) { if (!d) return '—'; return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }) }
function fmtDateShort(d) { if (!d) return ''; return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }) }

const isTimelineEntry = e => e.executor_role !== 'header' && !e.stage_code?.endsWith('_HDR') && e.status !== 'skipped'

const timelineTotalInScope = computed(() =>
  timeline.value.filter(e => isTimelineEntry(e) && e.is_in_contract_scope)
    .reduce((s, e) => s + (e.custom_norm_days || e.norm_days || 0), 0),
)

const timelineTotalAll = computed(() =>
  timeline.value.filter(isTimelineEntry)
    .reduce((s, e) => s + (e.custom_norm_days || e.norm_days || 0), 0),
)

async function exportTimelineExcel() {
  const { utils, writeFile } = await import('xlsx')
  const num = contract.value?.contract_number || ''
  const wsData = [
    [`Таблица сроков — Договор №${num}`],
    [],
    ['Этап', 'Роль', 'Норма, дн.', 'Факт, дн.', 'Дата', 'Статус', 'Примечание'],
  ]
  timeline.value.forEach(e => {
    if (e.executor_role === 'header' || e.stage_code?.endsWith('_HDR')) {
      wsData.push([e.stage_name, '', '', '', '', '', ''])
      return
    }
    const norm = e.custom_norm_days || e.norm_days || ''
    const fact = e.actual_days || ''
    const date = e.actual_date ? new Date(e.actual_date).toLocaleDateString('ru-RU') : ''
    let status = 'Ожидается'
    if (e.status === 'skipped') status = 'Пропущено'
    else if (e.actual_date) status = ((e.actual_days || 0) > (e.norm_days || 0) && (e.norm_days || 0) > 0) ? 'Просрочен' : 'В срок'
    const note = !e.is_in_contract_scope ? 'вне объёма' : ''
    wsData.push([e.stage_name, e.executor_role || '', norm, fact, date, status, note])
  })
  wsData.push([])
  wsData.push(['Итого по договору', '', timelineTotalInScope.value, '', '', '', ''])
  wsData.push(['Итого с учётом вне объёма', '', timelineTotalAll.value, '', '', '', ''])
  const ws = utils.aoa_to_sheet(wsData)
  ws['!cols'] = [{ wch: 42 }, { wch: 20 }, { wch: 12 }, { wch: 12 }, { wch: 12 }, { wch: 12 }, { wch: 14 }]
  const wb = utils.book_new()
  utils.book_append_sheet(wb, ws, 'Таблица сроков')
  writeFile(wb, `timeline_${num || 'contract'}.xlsx`.replace(/[/\\:*?"<>|]/g, '_'))
}

function exportTimelinePdf() {
  const num = contract.value?.contract_number || ''
  const addr = contract.value?.address || ''
  let rows = ''
  timeline.value.forEach(e => {
    if (e.executor_role === 'header') {
      rows += `<tr class="grp-hdr"><td colspan="6">${e.stage_name}</td></tr>`
      return
    }
    if (e.stage_code?.endsWith('_HDR')) {
      rows += `<tr class="sub-hdr"><td colspan="6">${e.stage_name}</td></tr>`
      return
    }
    const norm = e.custom_norm_days || e.norm_days || '—'
    const fact = e.actual_days || '—'
    const date = e.actual_date ? new Date(e.actual_date).toLocaleDateString('ru-RU') : '—'
    const isOverdue = e.actual_date && (e.actual_days || 0) > (e.norm_days || 0) && (e.norm_days || 0) > 0
    const isOnTime = e.actual_date && !isOverdue
    const rowCls = e.status === 'skipped' ? 'skipped' : (isOverdue ? 'overdue' : (isOnTime ? 'ontime' : ''))
    let status = '–'
    if (e.status === 'skipped') status = '<span class="tag-skip">Пропущено</span>'
    else if (isOverdue) status = '<span class="tag-over">Просрочен</span>'
    else if (isOnTime) status = '<span class="tag-ok">В срок</span>'
    const outNote = !e.is_in_contract_scope ? '<br><span class="out-tag">вне объёма</span>' : ''
    rows += `<tr class="${rowCls}">
      <td>${e.stage_name}${outNote}</td>
      <td>${e.executor_role || ''}</td>
      <td class="num">${norm}</td>
      <td class="num">${fact}</td>
      <td class="num">${date}</td>
      <td>${status}</td>
    </tr>`
  })
  rows += `<tr class="total-row">
    <td colspan="2"><b>Итого по договору</b></td>
    <td class="num"><b>${timelineTotalInScope.value} дн.</b></td>
    <td colspan="3"></td>
  </tr>
  <tr class="total-sub">
    <td colspan="2">Итого с учётом вне объёма</td>
    <td class="num">${timelineTotalAll.value} дн.</td>
    <td colspan="3"></td>
  </tr>`
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8">
  <title>Таблица сроков — №${num}</title>
  <style>
    body { font-family: Arial, sans-serif; font-size: 10px; color: #222; margin: 16px; }
    h2 { font-size: 13px; margin: 0 0 2px; }
    .sub { color: #666; margin-bottom: 12px; font-size: 10px; }
    table { border-collapse: collapse; width: 100%; }
    th { background: #ffd93c; color: #333; font-weight: bold; padding: 4px 6px; text-align: left; border: 1px solid #ddd; font-size: 10px; }
    td { padding: 3px 6px; border: 1px solid #eee; vertical-align: middle; }
    .num { text-align: right; white-space: nowrap; }
    .grp-hdr td { background: #e0e0e0; font-weight: bold; font-size: 10px; }
    .sub-hdr td { background: #f5f5f5; font-weight: 600; font-size: 10px; }
    .ontime td { background: #f0fff4; }
    .overdue td { background: #fff5f5; }
    .skipped td { opacity: 0.55; }
    .out-tag { color: #999; font-style: italic; font-size: 9px; }
    .tag-ok { color: #27ae60; font-weight: bold; }
    .tag-over { color: #e74c3c; font-weight: bold; }
    .tag-skip { color: #aaa; }
    .total-row td { border-top: 2px solid #333; font-size: 11px; }
    .total-sub td { color: #888; }
    @media print { @page { margin: 12mm; size: A4; } }
  </style></head><body>
  <h2>Таблица сроков — Договор №${num}</h2>
  <div class="sub">${addr}</div>
  <table>
    <thead><tr><th>Этап</th><th>Роль</th><th>Норма</th><th>Факт</th><th>Дата</th><th>Статус</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>
  <script>window.onload = () => { window.print() }<\/script>
  </body></html>`
  const w = window.open('', '_blank')
  w.document.write(html)
  w.document.close()
}
function fmtMoney(v) { if (!v) return '0 ₽'; return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(v) }

function fileIconByName(name) {
  if (!name) return 'insert_drive_file'
  const n = name.toLowerCase()
  if (n.endsWith('.pdf')) return 'picture_as_pdf'
  if (n.match(/\.(jpg|jpeg|png|webp)$/)) return 'image'
  if (n.match(/\.(doc|docx)$/)) return 'article'
  if (n.match(/\.(xls|xlsx)$/)) return 'table_chart'
  return 'insert_drive_file'
}
function fileColorByName(name) {
  if (!name) return 'grey-7'
  const n = name.toLowerCase()
  if (n.endsWith('.pdf')) return 'red'
  if (n.match(/\.(jpg|jpeg|png|webp)$/)) return 'green'
  if (n.match(/\.(doc|docx)$/)) return 'blue'
  if (n.match(/\.(xls|xlsx)$/)) return 'teal'
  return 'grey-7'
}

async function openFile(f) {
  if (!f.public_link && f.yandex_path) {
    // Нет публичной ссылки — запросим
    try {
      const { data } = await filesApi.getPublicLink(f.yandex_path)
      if (data.public_link) { window.open(data.public_link, '_blank'); return }
    } catch {
      // Файл не найден на ЯД — удалим запись из БД
      try {
        const { api: ax } = await import('src/boot/axios')
        await ax.delete(`/api/v1/files/${f.id}`)
        files.value = files.value.filter(x => x.id !== f.id)
        $q.notify({ type: 'info', message: `Файл "${f.file_name}" удалён с ЯД — запись убрана` })
      } catch {}
      return
    }
  }
  if (f.public_link) window.open(f.public_link, '_blank')
}

async function deleteContractFile(f) {
  $q.dialog({
    title: 'Удалить файл?',
    message: f.file_name,
    cancel: { label: 'Нет', flat: true, noCaps: true },
    ok: { label: 'Удалить', noCaps: true, color: 'negative' },
  }).onOk(async () => {
    try {
      const { api: ax } = await import('src/boot/axios')
      await ax.delete(`/api/v1/files/${f.id}`)
      files.value = files.value.filter(x => x.id !== f.id)
      // Очищаем поля contracts для совместимости с десктопом
      const FIELD_MAP = {
        documents: ['contract_file_link', 'contract_file_yandex_path', 'contract_file_name'],
        tech_task: ['tech_task_link', 'tech_task_yandex_path', 'tech_task_file_name'],
        measurement: ['measurement_image_link', 'measurement_yandex_path', 'measurement_file_name'],
        act_pr: ['act_planning_link', 'act_planning_yandex_path', 'act_planning_file_name'],
        act_kd: ['act_concept_link', 'act_concept_yandex_path', 'act_concept_file_name'],
        act_rch: ['act_final_link', 'act_final_yandex_path', 'act_final_file_name'],
        act_pr_signed: ['act_planning_signed_link', 'act_planning_signed_yandex_path', 'act_planning_signed_file_name'],
        act_kd_signed: ['act_concept_signed_link', 'act_concept_signed_yandex_path', 'act_concept_signed_file_name'],
        act_rch_signed: ['act_final_signed_link', 'act_final_signed_yandex_path', 'act_final_signed_file_name'],
        // Обратная совместимость для старых записей
        stage1: ['act_planning_link', 'act_planning_yandex_path', 'act_planning_file_name'],
        stage2_concept: ['act_concept_link', 'act_concept_yandex_path', 'act_concept_file_name'],
        stage3: ['act_final_link', 'act_final_yandex_path', 'act_final_file_name'],
        stage1_signed: ['act_planning_signed_link', 'act_planning_signed_yandex_path', 'act_planning_signed_file_name'],
        stage2_signed: ['act_concept_signed_link', 'act_concept_signed_yandex_path', 'act_concept_signed_file_name'],
        stage3_signed: ['act_final_signed_link', 'act_final_signed_yandex_path', 'act_final_signed_file_name'],
        supervision: ['additional_agreement_link', 'additional_agreement_yandex_path', 'additional_agreement_file_name'],
      }
      const CLEAR_MAP = {}
      for (const [stage, fields] of Object.entries(FIELD_MAP)) {
        const obj = {}; for (const fld of fields) obj[fld] = ''; CLEAR_MAP[stage] = obj
      }
      const clearFields = CLEAR_MAP[f.stage]
      if (clearFields) { try { await contractsApi.update(contract.value.id, clearFields) } catch {} }
      $q.notify({ type: 'positive', message: 'Файл удалён' })
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка удаления' })
    }
  })
}
function goToClient() { if (contract.value?.client_id) router.push(`/clients/${contract.value.client_id}`) }
function openMap(address) { window.open(`https://yandex.ru/maps/?text=${encodeURIComponent(address)}`, '_blank') }
function clientTelegramLink(account) {
  if (!account) return '#'
  const clean = account.replace('@', '').trim()
  if (!clean) return '#'
  if (/^\+?\d+$/.test(clean.replace(/\s/g, ''))) {
    const phone = clean.replace(/[^\d+]/g, '')
    return `https://t.me/${phone.startsWith('+') ? phone : '+' + phone}`
  }
  return `https://t.me/${clean}`
}

function uploadFor(stage) { uploadStage.value = stage; fileInput.value?.click() }
function uploadReceipt(type) { receiptType.value = type; receiptInput.value?.click() }

// Диалог подтверждения оплаты (сумма + дата)
const payDialogOpen = ref(false)
const payDialogKey = ref('')
const payDialogDate = ref('')
const payDialogAmount = ref('')

function pickPayDate(payKey) {
  payDialogKey.value = payKey
  payDialogDate.value = new Date().toISOString().split('T')[0]
  const currentAmount = contract.value[`${payKey}_payment`]
  payDialogAmount.value = currentAmount ? String(currentAmount) : ''
  payDialogOpen.value = true
}

async function confirmPay() {
  const payKey = payDialogKey.value
  try {
    const update = { [`${payKey}_payment_paid_date`]: payDialogDate.value }
    if (payDialogAmount.value) update[`${payKey}_payment`] = parseFloat(payDialogAmount.value)
    await contractsApi.update(contract.value.id, update)
    contract.value[`${payKey}_payment_paid_date`] = payDialogDate.value
    if (payDialogAmount.value) contract.value[`${payKey}_payment`] = parseFloat(payDialogAmount.value)
    payDialogOpen.value = false
    $q.notify({ type: 'positive', message: 'Оплата проведена' })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

// Снять оплату
async function cancelPayment(payKey) {
  $q.dialog({ title: 'Снять оплату?', message: 'Отменить дату оплаты?', cancel: { label: 'Нет', flat: true, noCaps: true }, ok: { label: 'Да, снять', noCaps: true, color: 'negative' } }).onOk(async () => {
    try {
      const update = {}
      update[`${payKey}_payment_paid_date`] = null
      await contractsApi.update(contract.value.id, update)
      contract.value[`${payKey}_payment_paid_date`] = null
      $q.notify({ type: 'positive', message: 'Оплата снята' })
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
    }
  })
}

// Генерация пути ЯД на клиенте (как в десктопе yandex_disk.py build_contract_folder_path)
function buildYdFolderPath(c) {
  const agent = c.agent_type || 'ФЕСТИВАЛЬ'
  const ptype = c.project_type || 'Индивидуальный'
  const city = c.city || 'МСК'
  const address = (c.address || 'Без адреса').replace(/[/\\<>:"|?*]/g, '-')
  // area как Python float (100 → "100.0", 100.5 → "100.5") — совпадает с серверным fix-folder
  const rawArea = c.area || 0
  const area = Number.isInteger(Number(rawArea)) ? Number(rawArea).toFixed(1) : rawArea
  const typeFolder = ptype.includes('ндивид') ? 'Индивидуальные' : 'Шаблонные'
  const folderName = `${city}-${address}-${area}м2`
  return `disk:/CRM/Проекты/${agent}/${typeFolder}/${city}/${folderName}`
}

// Создание полной структуры подпапок (как десктоп yandex_disk.py create_contract_folder_structure)
async function createYdSubfolders(basePath) {
  const { api: ax } = await import('src/boot/axios')
  const subfolders = [
    'Документы',
    'Документы/Акты',
    'Документы/Информационные письма',
    'Документы/Доп. соглашения',
    'Анкета',
    'Замер',
    'Референсы',
    'Фотофиксация',
    '1 стадия - Планировочное решение',
    '2 стадия - Концепция дизайна',
    '2 стадия - Концепция дизайна/Концепция-коллажи',
    '2 стадия - Концепция дизайна/3D визуализация',
    '3 стадия - Чертежный проект',
  ]
  for (const sub of subfolders) {
    try { await ax.post('/api/v1/files/folder', null, { params: { folder_path: `${basePath}/${sub}` } }) } catch {}
  }
}

async function ensureYdFolder(c) {
  // Всегда загружаем свежие данные из БД (yandex_folder_path мог измениться)
  try {
    const { data: fresh } = await contractsApi.getById(c.id)
    if (fresh.yandex_folder_path) {
      contract.value = fresh
      return fresh.yandex_folder_path.replace(/^disk:/, '')
    }
  } catch {}
  let folder = (c.yandex_folder_path || '').replace(/^disk:/, '')
  if (!folder) {
    // Генерируем правильный путь и обновляем в БД
    const path = buildYdFolderPath(c)
    folder = path.replace(/^disk:/, '')
    try {
      const { api: ax } = await import('src/boot/axios')
      // Создаём папку на ЯД
      await ax.post('/api/v1/files/folder', null, { params: { folder_path: path } })
      // Обновляем yandex_folder_path в БД
      await contractsApi.update(c.id, { yandex_folder_path: path })
      contract.value.yandex_folder_path = path
    } catch {}
  }
  return folder
}

async function handleFileUpload(event) {
  const file = event.target.files?.[0]
  if (!file || !contract.value) return
  try {
    $q.loading.show({ message: 'Загрузка...' })
    const contractFolder = await ensureYdFolder(contract.value)
    // Маппинг stage → подпапка на ЯД (как в десктопе contract_dialogs.py)
    const STAGE_FOLDERS = {
      documents: 'Документы',                         // Файл договора
      tech_task: 'Анкета',                            // Техническое задание
      measurement: 'Замер',                           // Замер
      act_pr: 'Документы/Акты',                       // Акт ПР (без подписи)
      act_kd: 'Документы/Акты',                       // Акт КД (без подписи)
      act_rch: 'Документы/Акты',                      // Акт РЧ (без подписи)
      act_pr_signed: 'Документы/Акты',                // Акт ПР (с подписью)
      act_kd_signed: 'Документы/Акты',                // Акт КД (с подписью)
      act_rch_signed: 'Документы/Акты',               // Акт РЧ (с подписью)
      supervision: 'Документы/Доп. соглашения',       // Доп. соглашения
      references: 'Референсы',
      photo_documentation: 'Фотофиксация',
    }
    const stageFolder = STAGE_FOLDERS[uploadStage.value] || uploadStage.value
    if (!contractFolder) { $q.notify({ type: 'negative', message: 'Папка проекта на ЯД не создана' }); return }
    const ydPath = `${contractFolder}/${stageFolder}/${file.name}`
    const uploadRes = await filesApi.upload(file, ydPath)
    const publicLink = uploadRes.data?.public_link || ''
    const { api: apiInst } = await import('src/boot/axios')
    await apiInst.post('/api/v1/files/', {
      contract_id: contract.value.id, stage: uploadStage.value,
      file_type: file.type?.includes('image') ? 'image' : file.name.endsWith('.pdf') ? 'pdf' : 'other',
      public_link: publicLink, yandex_path: ydPath, file_name: file.name,
      file_order: files.value.length + 1, variation: 1,
    })
    // Обновляем поля contracts для совместимости с десктопом (все 19 типов файлов)
    const CONTRACT_FIELD_MAP = {
      documents: { link: 'contract_file_link', path: 'contract_file_yandex_path', name: 'contract_file_name' },
      tech_task: { link: 'tech_task_link', path: 'tech_task_yandex_path', name: 'tech_task_file_name' },
      measurement: { link: 'measurement_image_link', path: 'measurement_yandex_path', name: 'measurement_file_name' },
      act_pr: { link: 'act_planning_link', path: 'act_planning_yandex_path', name: 'act_planning_file_name' },
      act_kd: { link: 'act_concept_link', path: 'act_concept_yandex_path', name: 'act_concept_file_name' },
      act_rch: { link: 'act_final_link', path: 'act_final_yandex_path', name: 'act_final_file_name' },
      act_pr_signed: { link: 'act_planning_signed_link', path: 'act_planning_signed_yandex_path', name: 'act_planning_signed_file_name' },
      act_kd_signed: { link: 'act_concept_signed_link', path: 'act_concept_signed_yandex_path', name: 'act_concept_signed_file_name' },
      act_rch_signed: { link: 'act_final_signed_link', path: 'act_final_signed_yandex_path', name: 'act_final_signed_file_name' },
      supervision: { link: 'additional_agreement_link', path: 'additional_agreement_yandex_path', name: 'additional_agreement_file_name' },
    }
    const fieldMap = CONTRACT_FIELD_MAP[uploadStage.value]
    if (fieldMap) {
      const update = {}
      update[fieldMap.link] = publicLink
      update[fieldMap.path] = ydPath
      update[fieldMap.name] = file.name
      try { await contractsApi.update(contract.value.id, update) } catch {}
    }
    $q.notify({ type: 'positive', message: 'Файл загружен' })
    const { data } = await filesApi.getContractFiles(contract.value.id)
    files.value = data || []
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка загрузки' }) }
  finally { $q.loading.hide(); event.target.value = '' }
}

async function handleReceiptUpload(event) {
  const file = event.target.files?.[0]
  if (!file || !contract.value) return
  try {
    $q.loading.show({ message: 'Загрузка чека...' })
    const yandexPath = `/CRM/Чеки/${contract.value.contract_number}/${receiptType.value}_${file.name}`
    await filesApi.upload(file, yandexPath)
    $q.notify({ type: 'positive', message: 'Чек загружен' })
  } catch { $q.notify({ type: 'negative', message: 'Ошибка загрузки' }) }
  finally { $q.loading.hide(); event.target.value = '' }
}

async function deleteContract() {
  $q.dialog({ title: 'Удалить договор?', message: contract.value?.contract_number || '', cancel: true, persistent: true }).onOk(async () => {
    try {
      await contractsApi.delete(contract.value.id)
      $q.notify({ type: 'positive', message: 'Договор удалён' })
      window.history.back()
    } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  })
}

async function reload() {
  const { data } = await contractsApi.getById(route.params.id)
  contract.value = data
}

// Синхронизация файлов с ЯД — проверяем существование, удаляем мёртвые записи
async function syncFilesWithYd() {
  if (!files.value.length) return
  const { api: ax } = await import('src/boot/axios')
  const toRemove = []
  for (const f of files.value) {
    const path = f.yandex_path || ''
    if (!path) continue
    try {
      await filesApi.getPublicLink(path.replace(/^disk:/, ''))
    } catch {
      // Файл не найден на ЯД — удаляем запись
      try { await ax.delete(`/api/v1/files/${f.id}`) } catch {}
      toRemove.push(f.id)
    }
  }
  if (toRemove.length > 0) {
    files.value = files.value.filter(f => !toRemove.includes(f.id))
    $q.notify({ type: 'info', message: `Удалено ${toRemove.length} файл(ов) — отсутствуют на ЯД` })
  }
}

// Обратная синхронизация: сканирование ЯД → БД (новые файлы)
async function syncWithYd() {
  if (!contract.value?.id) return
  syncing.value = true
  try {
    const { api: ax } = await import('src/boot/axios')
    // 1. Загружаем свежие данные договора
    const { data: fresh } = await contractsApi.getById(contract.value.id)
    contract.value = fresh

    // 2. Проверяем/создаём/переименовываем папку
    const correctPath = buildYdFolderPath(fresh)
    const currentPath = fresh.yandex_folder_path || ''

    if (currentPath !== correctPath) {
      // Путь не совпадает — пробуем переименовать старую, иначе создаём новую
      if (currentPath) {
        try {
          await ax.post('/api/v1/files/move-folder', null, { params: { from_path: currentPath, to_path: correctPath } })
        } catch {
          // move не удался — создаём новую
          try { await ax.post('/api/v1/files/folder', null, { params: { folder_path: correctPath } }) } catch {}
        }
      } else {
        try { await ax.post('/api/v1/files/folder', null, { params: { folder_path: correctPath } }) } catch {}
      }
      await contractsApi.update(fresh.id, { yandex_folder_path: correctPath })
      contract.value.yandex_folder_path = correctPath
    }
    // Всегда убеждаемся что папка + подпапки физически существуют на ЯД
    const folderPath = contract.value.yandex_folder_path || correctPath
    try { await ax.post('/api/v1/files/folder', null, { params: { folder_path: folderPath } }) } catch {}
    await createYdSubfolders(folderPath)

    // 3. Сканируем файлы на ЯД → БД
    const { data } = await ax.post(`/api/v1/files/scan/${contract.value.id}`)
    const added = data.new_files_added || 0

    // 4. Перезагружаем файлы
    const { data: freshFiles } = await filesApi.getContractFiles(contract.value.id)
    files.value = freshFiles || []

    // 5. Удаляем мёртвые записи
    await syncFilesWithYd()

    if (added > 0) {
      $q.notify({ type: 'positive', message: `Синхронизация: +${added} файл(ов) с ЯД` })
    } else {
      $q.notify({ type: 'info', message: 'Синхронизировано — новых файлов не найдено' })
    }
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка синхронизации' })
  } finally { syncing.value = false }
}

onMounted(async () => {
  const id = route.params.id
  try {
    const [cRes, fRes, tRes] = await Promise.allSettled([
      contractsApi.getById(id), filesApi.getContractFiles(id), timelineApi.get(id),
    ])
    if (cRes.status === 'fulfilled') contract.value = cRes.value.data
    if (fRes.status === 'fulfilled') files.value = fRes.value.data || []
    if (tRes.status === 'fulfilled') timeline.value = tRes.value.data || []
    // Загружаем данные клиента (для контактов) всегда при наличии client_id
    if (contract.value?.client_id) {
      try {
        const { data: cl } = await clientsApi.getById(contract.value.client_id)
        clientData.value = cl
        if (cl?.full_name && !contract.value.client_name) clientName.value = cl.full_name
      } catch {}
    }
    // Фоновая синхронизация файлов с ЯД
    syncFilesWithYd()
    // Загрузка опросов
    loadSurveys()
  } finally { loading.value = false }
})
</script>

<style scoped>
.tl-export-btn {
  height: 26px;
  padding: 0 10px;
  border: 1px solid #2196f3;
  border-radius: 4px;
  background: white;
  color: #2196f3;
  font-size: 11px;
  font-family: inherit;
  cursor: pointer;
  flex-shrink: 0;
  outline: none;
  white-space: nowrap;
  display: flex;
  align-items: center;
  justify-content: center;
}
.tl-export-btn:hover {
  background: #e3f2fd;
}

/* Ландшафт: основная сетка — 2 колонки (левая=данные, правая=документы) */
@media (orientation: landscape) {
  .contract-detail-grid {
    display: flex;
    flex-direction: row;
    gap: 12px;
    align-items: stretch;
  }
  .contract-left-col,
  .contract-right-col {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
  .contract-left-col > * + *,
  .contract-right-col > * + * {
    margin-top: 12px;
  }
  .contract-left-col > *,
  .contract-right-col > * {
    margin-bottom: 0 !important;
  }
  .contract-right-col > .is-card {
    flex: 1;
  }
}

/* Чипы контактов клиента */
.contact-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  background: #F5F5F5;
  color: #333;
  text-decoration: none;
  cursor: pointer;
}
.contact-chip--tg {
  background: #E3F2FD;
  color: #1565C0;
}

/* В ландшафте блоки Договор/ТЗ/Доп.соглашения стоят вертикально внутри левой колонки */
.contract-files-grid {
  display: flex;
  flex-direction: column;
  gap: 0;
}
</style>
