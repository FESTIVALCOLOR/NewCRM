<template>
  <q-page class="column" :style="{ height: chatPageH, overflow: 'hidden' }">
    <!-- Шапка -->
    <div class="row items-center q-px-md q-py-sm bg-white" style="border-bottom: 1px solid #E0E0E0; flex-shrink: 0">
      <q-btn
        flat
        round
        dense
        icon="arrow_back"
        @click="$router.back()"
      />
      <div class="q-ml-sm column" style="flex: 1; min-width: 0">
        <div class="text-subtitle2 text-weight-bold" style="word-break: break-word; line-height: 1.3">
          {{ chatTitle }}
        </div>
        <div v-if="typingText" class="text-caption text-grey ellipsis">
          {{ typingText }}
        </div>
        <div v-else-if="wsConnected" class="text-caption text-grey">
          <q-icon name="wifi" size="10px" color="positive" class="q-mr-xs" />онлайн
        </div>
        <div v-else class="text-caption text-grey">
          <q-icon name="wifi_off" size="10px" color="negative" class="q-mr-xs" />оффлайн
        </div>
      </div>
      <q-btn
        flat
        round
        dense
        icon="people"
        @click="showMembers = true"
      >
        <q-tooltip>Участники</q-tooltip>
      </q-btn>
    </div>

    <!-- Закреплённое сообщение -->
    <div
      v-if="pinnedMsg"
      class="row items-center q-px-md q-py-xs bg-white"
      style="border-bottom: 1px solid #E0E0E0; flex-shrink: 0; cursor: pointer; gap: 8px"
      @click="scrollToPinned"
    >
      <q-icon name="push_pin" size="14px" color="orange-8" style="flex-shrink: 0" />
      <div style="flex: 1; min-width: 0; overflow: hidden">
        <div class="text-caption text-weight-bold" style="color: #E65100; font-size: 10px">
          Закреплено
        </div>
        <div class="text-caption ellipsis" style="font-size: 11px; color: #333">
          {{ pinnedMsg.content || pinnedMsg.file_name || '📎 Файл' }}
        </div>
      </div>
      <q-btn
        flat
        round
        dense
        size="xs"
        icon="close"
        color="grey-6"
        @click.stop="togglePin(pinnedMsg)"
      />
    </div>

    <!-- Список сообщений -->
    <div
      ref="messagesEl"
      class="col q-pa-md"
      style="overflow-y: auto; background: #F5F5F5"
    >
      <div v-if="loadingMessages" class="text-center q-mt-lg">
        <q-spinner size="24px" color="grey" />
      </div>

      <div v-else-if="!messages.length" class="text-center text-grey q-mt-xl">
        <q-icon name="chat_bubble_outline" size="40px" />
        <div class="q-mt-sm">
          Начните диалог
        </div>
      </div>

      <template v-else>
        <template v-for="item in renderedItems" :key="item.key">
          <!-- Галерея (несколько изображений одной отправкой) -->
          <template v-if="item.type === 'group'">
            <div
              v-if="firstUnreadId && item.msgs[0].id === firstUnreadId"
              data-unread-divider
              class="row items-center q-my-sm"
            >
              <div class="col" style="height: 1px; background: #E53935" />
              <span class="q-px-sm text-caption text-negative text-weight-medium">Непрочитанные сообщения</span>
              <div class="col" style="height: 1px; background: #E53935" />
            </div>
            <div
              :data-msg-id="item.msgs[0].id"
              class="q-mb-sm"
              :class="isOwn(item.msgs[0]) ? 'row justify-end' : 'row justify-start'"
            >
              <div
                :class="isOwn(item.msgs[0]) ? 'bubble-img-own' : 'bubble-img-other'"
                style="max-width: 75%"
              >
                <div class="row no-wrap items-center justify-between" style="padding: 6px 10px 4px; min-height: 16px; gap: 2px">
                  <div
                    class="text-caption text-weight-bold"
                    :style="{ color: isOwn(item.msgs[0]) ? '#999' : '#1565C0' }"
                    style="flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap"
                  >
                    {{ item.msgs[0].sender_display_name }}
                  </div>
                </div>
                <div :class="galleryGridClass(item.msgs.length)">
                  <a
                    v-for="gm in item.msgs"
                    :key="gm.id"
                    :href="gm.file_url"
                    target="_blank"
                    style="display: block; text-decoration: none; overflow: hidden"
                  >
                    <q-img
                      v-if="imgStreamUrl(gm)"
                      :src="imgStreamUrl(gm)"
                      style="width: 100%; height: 130px; display: block"
                      fit="cover"
                      spinner-color="grey-4"
                      spinner-size="20px"
                    />
                  </a>
                </div>
                <div v-if="groupCaption(item.msgs)" class="text-body2" style="padding: 4px 10px 2px; white-space: pre-wrap; word-break: break-word; font-size: 13px">
                  {{ groupCaption(item.msgs) }}
                </div>
                <div class="row no-wrap items-center" :class="isOwn(item.msgs[0]) ? 'justify-end' : 'justify-start'" style="padding: 2px 10px 6px; margin-top: 0">
                  <div class="text-caption" style="color: #888; font-size: 10px">
                    {{ formatTime(item.msgs[item.msgs.length - 1].created_at) }}
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- Одиночное сообщение -->
          <template v-else>
            <template v-for="msg in [item.msg]" :key="msg.id">
              <!-- Разделитель «Непрочитанные сообщения» -->
              <div
                v-if="firstUnreadId && msg.id === firstUnreadId"
                data-unread-divider
                class="row items-center q-my-sm"
              >
                <div class="col" style="height: 1px; background: #E53935" />
                <span class="q-px-sm text-caption text-negative text-weight-medium">Непрочитанные сообщения</span>
                <div class="col" style="height: 1px; background: #E53935" />
              </div>
              <div
                :data-msg-id="msg.id"
                class="q-mb-sm"
                :class="isOwn(msg) ? 'row justify-end' : 'row justify-start'"
              >
                <!-- Системные сообщения — по центру -->
                <div v-if="msg.message_type === 'system'" class="text-center full-width">
                  <q-chip dense size="sm" color="grey-3" text-color="grey-7">
                    {{ msg.content }}
                  </q-chip>
                </div>

                <!-- Обычные сообщения -->
                <div
                  v-else
                  :class="msg.message_type === 'image'
                    ? (isOwn(msg) ? 'bubble-img-own' : 'bubble-img-other')
                    : (isOwn(msg) ? 'bubble-own' : 'bubble-other')"
                  style="max-width: 75%"
                >
                  <!-- Верхняя строка: имя отправителя + кнопка меню -->
                  <div
                    class="row no-wrap items-center justify-between q-mb-xs"
                    :style="msg.message_type === 'image' ? 'min-height:16px;gap:2px;padding:6px 10px 4px' : 'min-height:16px;gap:2px'"
                  >
                    <div
                      class="text-caption text-weight-bold"
                      :style="{ color: isOwn(msg) ? '#999' : '#1565C0' }"
                      style="flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap"
                    >
                      {{ msg.sender_display_name }}
                    </div>
                    <q-btn
                      v-if="!msg.is_deleted && !msg._uploading"
                      flat
                      round
                      dense
                      size="xs"
                      icon="more_vert"
                      color="grey-6"
                      style="margin: -4px -6px -2px 2px; flex-shrink: 0"
                    >
                      <q-menu auto-close>
                        <q-list dense style="min-width: 150px; font-size: 12px">
                          <q-item
                            clickable
                            dense
                            @click="togglePin(msg)"
                          >
                            <q-item-section avatar style="min-width: 28px">
                              <q-icon name="push_pin" size="14px" :color="msg.is_pinned ? 'orange-8' : 'grey-8'" />
                            </q-item-section>
                            <q-item-section style="font-size: 12px">
                              {{ msg.is_pinned ? 'Открепить' : 'Закрепить' }}
                            </q-item-section>
                          </q-item>
                          <q-separator />
                          <q-item
                            v-if="isOwn(msg) && msg.message_type === 'text'"
                            clickable
                            dense
                            @click="startEdit(msg)"
                          >
                            <q-item-section avatar style="min-width: 28px">
                              <q-icon name="edit" size="14px" color="grey-8" />
                            </q-item-section>
                            <q-item-section style="font-size: 12px">
                              Редактировать
                            </q-item-section>
                          </q-item>
                          <q-item
                            v-if="isOwn(msg)"
                            clickable
                            dense
                            @click="deleteMsg(msg)"
                          >
                            <q-item-section avatar style="min-width: 28px">
                              <q-icon name="delete_outline" size="14px" color="grey-8" />
                            </q-item-section>
                            <q-item-section class="text-red-7" style="font-size: 12px">
                              Удалить
                            </q-item-section>
                          </q-item>
                          <q-item
                            clickable
                            dense
                            @click="openForwardDialog(msg)"
                          >
                            <q-item-section avatar style="min-width: 28px">
                              <q-icon name="forward" size="14px" color="grey-8" />
                            </q-item-section>
                            <q-item-section style="font-size: 12px">
                              Переслать
                            </q-item-section>
                          </q-item>
                          <q-item
                            v-if="msg.yandex_path && chatCrmCardId"
                            clickable
                            dense
                            @click="openCopyToCard(msg)"
                          >
                            <q-item-section avatar style="min-width: 28px">
                              <q-icon name="drive_file_move" size="14px" color="grey-8" />
                            </q-item-section>
                            <q-item-section style="font-size: 12px">
                              Скопировать в карточку
                            </q-item-section>
                          </q-item>
                        </q-list>
                      </q-menu>
                    </q-btn>
                  </div>

                  <!-- Загрузка файла (оптимистичное сообщение) -->
                  <template v-if="msg._uploading">
                    <div class="row items-center q-gutter-xs">
                      <q-spinner size="14px" color="grey-5" />
                      <span class="text-caption text-grey-6" style="word-break: break-word">{{ msg.file_name }}…</span>
                    </div>
                  </template>
                  <!-- Изображение — Telegram-стиль -->
                  <template v-else-if="msg.message_type === 'image'">
                    <a :href="msg.file_url" target="_blank" style="display: block; text-decoration: none; color: inherit">
                      <q-img
                        v-if="imgStreamUrl(msg)"
                        :src="imgStreamUrl(msg)"
                        style="width: 100%; max-height: clamp(160px, 35vh, 480px); display: block; cursor: pointer; min-height: 80px"
                        fit="contain"
                        spinner-color="grey-4"
                        spinner-size="28px"
                      />
                      <div class="row items-center q-gutter-xs" style="padding: 4px 10px 2px">
                        <q-icon name="image" size="14px" color="grey-6" />
                        <span class="text-caption text-grey-7 ellipsis" style="max-width: 220px">
                          {{ msg.file_name || 'Изображение' }}
                        </span>
                      </div>
                      <div v-if="msg.content" class="text-body2" style="padding: 2px 10px 4px; white-space: pre-wrap; word-break: break-word; font-size: 13px">
                        {{ msg.content }}
                      </div>
                    </a>
                  </template>
                  <template v-else-if="msg.message_type === 'file'">
                    <div class="row items-center q-gutter-xs">
                      <q-icon name="attach_file" size="20px" />
                      <a :href="msg.file_url" target="_blank" class="text-body2 ellipsis" style="max-width: 180px; color: inherit">
                        {{ msg.file_name || 'Файл' }}
                      </a>
                    </div>
                  </template>

                  <!-- Голосовое -->
                  <template v-else-if="msg.message_type === 'voice'">
                    <div class="row items-center q-gutter-xs">
                      <q-btn
                        flat
                        round
                        dense
                        icon="play_arrow"
                        size="sm"
                        @click="playVoice(msg.file_url)"
                      />
                      <span class="text-body2">Голосовое сообщение</span>
                    </div>
                  </template>

                  <!-- Текст -->
                  <template v-else>
                    <div class="text-body2" style="white-space: pre-wrap; word-break: break-word">
                      {{ msg.content }}
                    </div>
                  </template>

                  <!-- Редактирование сообщения -->
                  <div v-if="editingMsgId === msg.id" class="q-mt-xs">
                    <q-input
                      v-model="editContent"
                      dense
                      outlined
                      autofocus
                      autogrow
                      hide-bottom-space
                      style="font-size: 13px"
                      @keydown.enter.exact.prevent="saveEdit"
                      @keydown.escape="cancelEdit"
                    />
                    <div class="row justify-end q-gutter-xs q-mt-xs">
                      <q-btn
                        flat
                        dense
                        no-caps
                        size="sm"
                        label="Отмена"
                        color="grey-6"
                        @click="cancelEdit"
                      />
                      <q-btn
                        unelevated
                        dense
                        no-caps
                        size="sm"
                        label="Сохранить"
                        color="blue-6"
                        :loading="savingEdit"
                        @click="saveEdit"
                      />
                    </div>
                  </div>

                  <!-- Нижняя строка: время -->
                  <div
                    class="row no-wrap items-center"
                    :class="isOwn(msg) ? 'justify-end' : 'justify-start'"
                    :style="msg.message_type === 'image' ? 'padding: 2px 10px 6px; margin-top: 0' : 'margin-top: 4px'"
                  >
                    <span v-if="msg.is_edited" class="text-caption text-grey-5 q-mr-xs" style="font-size: 9px">изм.</span>
                    <div class="text-caption" style="color: #888; font-size: 10px">
                      {{ formatTime(msg.created_at) }}
                    </div>
                  </div>
                </div>
              </div>
            </template><!-- /v-for msg alias -->
          </template><!-- /v-else single -->
        </template><!-- /v-for renderedItems -->
      </template><!-- /v-else messages -->
    </div>

    <!-- Прогресс загрузки файла -->
    <q-linear-progress
      v-if="uploadProgress > 0 && uploadProgress < 100"
      :value="uploadProgress / 100"
      color="primary"
      style="flex-shrink: 0"
    />

    <!-- Превью прикреплённых файлов -->
    <div
      v-if="pendingFiles.length"
      class="q-px-sm q-pt-xs q-pb-xs bg-blue-1"
      style="border-top: 1px solid #BBDEFB; flex-shrink: 0"
    >
      <div class="row items-center q-gutter-xs">
        <q-chip
          v-for="(f, i) in pendingFiles"
          :key="i"
          dense
          removable
          color="blue-2"
          text-color="blue-9"
          :icon="isImageFile(f) ? 'image' : 'attach_file'"
          style="max-width: 160px"
          @remove="removePendingFile(i)"
        >
          <span class="ellipsis" style="font-size: 11px; max-width: 120px">{{ f.name }}</span>
        </q-chip>
      </div>
    </div>

    <!-- Панель ввода -->
    <div class="q-pa-sm bg-white" style="border-top: 1px solid #E0E0E0; flex-shrink: 0">
      <div class="row items-center q-gutter-xs">
        <!-- Прикрепить файл -->
        <q-btn
          flat
          round
          dense
          icon="attach_file"
          :loading="uploadProgress > 0 && uploadProgress < 100"
          @click="pickFile"
        >
          <q-tooltip>Прикрепить файл</q-tooltip>
        </q-btn>
        <input
          ref="fileInput"
          type="file"
          multiple
          class="hidden"
          @change="onFileSelected"
        >

        <!-- Поле ввода / подпись к файлу -->
        <q-input
          v-if="pendingFiles.length"
          v-model="pendingCaption"
          outlined
          dense
          autogrow
          hide-bottom-space
          placeholder="Подпись к файлу…"
          style="flex: 1"
          @keydown.enter.exact.prevent="sendWithAttachment"
          @input="onTyping"
        />
        <q-input
          v-else
          v-model="inputText"
          outlined
          dense
          autogrow
          hide-bottom-space
          placeholder="Сообщение…"
          style="flex: 1"
          @keydown.enter.exact.prevent="sendText"
          @input="onTyping"
        />

        <!-- Отправить -->
        <q-btn
          round
          dense
          icon="send"
          color="primary"
          :disable="pendingFiles.length ? false : !inputText.trim()"
          @click="pendingFiles.length ? sendWithAttachment() : sendText()"
        />
      </div>
    </div>

    <!-- Диалог: переслать сообщение -->
    <q-dialog v-model="showForwardDialog">
      <q-card style="min-width: 300px; max-width: 400px; width: 90vw">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-subtitle2">
            Переслать сообщение
          </div>
          <q-space />
          <q-btn
            v-close-popup
            flat
            round
            dense
            icon="close"
          />
        </q-card-section>
        <q-card-section class="q-py-sm q-px-md">
          <q-input
            v-model="forwardSearchQuery"
            dense
            outlined
            placeholder="Поиск чата…"
            clearable
            clear-icon="close"
          >
            <template #prepend>
              <q-icon name="search" size="16px" />
            </template>
          </q-input>
        </q-card-section>
        <q-separator />
        <q-card-section style="max-height: 50vh; overflow-y: auto; padding: 0">
          <div v-if="loadingForwardChats" class="text-center q-pa-md">
            <q-spinner size="24px" color="grey" />
          </div>
          <q-list v-else separator>
            <q-item
              v-for="c in filteredForwardChats"
              :key="c.id"
              clickable
              :active="selectedForwardChatId === c.id"
              active-class="bg-blue-1"
              @click="selectedForwardChatId = c.id"
            >
              <q-item-section>
                <q-item-label>{{ c.title || `Чат #${c.id}` }}</q-item-label>
                <q-item-label caption>
                  {{ c.chat_type === 'client' ? 'Чат с клиентом' : 'Чат сотрудников' }}
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-icon v-if="selectedForwardChatId === c.id" name="check_circle" color="blue-6" />
              </q-item-section>
            </q-item>
            <div v-if="!loadingForwardChats && !filteredForwardChats.length" class="text-center text-grey q-pa-md">
              {{ forwardSearchQuery ? 'Ничего не найдено' : 'Нет доступных чатов' }}
            </div>
          </q-list>
        </q-card-section>
        <q-card-actions align="right" class="q-pt-sm">
          <q-btn
            v-close-popup
            flat
            no-caps
            label="Отмена"
            color="grey-7"
          />
          <q-btn
            unelevated
            no-caps
            label="Переслать"
            color="blue-6"
            :disable="!selectedForwardChatId"
            :loading="sendingForward"
            @click="doForward"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог: скопировать файл в карточку -->
    <q-dialog v-model="showCopyToCard" persistent>
      <q-card style="min-width: 300px; max-width: 420px; width: 92vw">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-subtitle2">
            {{ copyStep === 1 ? 'Скопировать в карточку' : 'Выбрать вариацию' }}
          </div>
          <q-space />
          <q-btn
            v-close-popup
            flat
            round
            dense
            icon="close"
          />
        </q-card-section>

        <!-- Шаг 1: выбор назначения -->
        <template v-if="copyStep === 1">
          <q-card-section class="q-pt-sm">
            <div class="text-caption text-grey-6 q-mb-sm">
              Файл будет скопирован в папку карточки на Яндекс.Диске и сохранён в выбранном поле.
            </div>
            <div style="max-height: 52vh; overflow-y: auto">
              <q-expansion-item
                v-for="group in COPY_DESTINATIONS"
                :key="group.group"
                :label="group.group"
                :model-value="group.items.some(d => d.value === selectedDestination)"
                dense
                dense-toggle
                header-class="text-caption text-weight-bold text-grey-8 q-px-xs"
                class="q-mb-xs"
              >
                <q-list dense>
                  <q-item
                    v-for="dest in group.items"
                    :key="dest.value"
                    clickable
                    :active="selectedDestination === dest.value"
                    active-class="bg-green-1 text-green-9"
                    class="rounded-borders q-pl-md"
                    style="min-height: 34px"
                    @click="selectedDestination = dest.value"
                  >
                    <q-item-section avatar style="min-width: 24px">
                      <q-icon
                        :name="selectedDestination === dest.value ? 'radio_button_checked' : 'radio_button_unchecked'"
                        size="16px"
                        :color="selectedDestination === dest.value ? 'green-7' : 'grey-5'"
                      />
                    </q-item-section>
                    <q-item-section style="font-size: 13px">
                      {{ dest.label }}
                    </q-item-section>
                  </q-item>
                </q-list>
              </q-expansion-item>
            </div>
          </q-card-section>
          <q-card-actions align="right">
            <q-btn
              v-close-popup
              flat
              no-caps
              label="Отмена"
              color="grey-7"
            />
            <q-btn
              unelevated
              no-caps
              :label="STAGE_KEYS.has(selectedDestination) ? 'Далее' : 'Скопировать'"
              color="green-7"
              :disable="!selectedDestination"
              :loading="copyingToCard || loadingVariations"
              @click="goToVariationStep"
            />
          </q-card-actions>
        </template>

        <!-- Шаг 2: выбор вариации (только для стадий) -->
        <template v-else>
          <q-card-section class="q-pt-sm">
            <div class="text-caption text-grey-6 q-mb-sm">
              Выберите вариацию для добавления файла или создайте новую.
            </div>
            <q-list dense>
              <q-item
                v-for="v in stageVariations"
                :key="v.variation"
                clickable
                :active="selectedVariation === v.variation"
                active-class="bg-green-1 text-green-9"
                class="rounded-borders"
                style="min-height: 36px"
                @click="selectedVariation = v.variation"
              >
                <q-item-section avatar style="min-width: 24px">
                  <q-icon
                    :name="selectedVariation === v.variation ? 'radio_button_checked' : 'radio_button_unchecked'"
                    size="16px"
                    :color="selectedVariation === v.variation ? 'green-7' : 'grey-5'"
                  />
                </q-item-section>
                <q-item-section>
                  <div style="font-size: 13px">
                    Вариация {{ v.variation }}
                  </div>
                  <div class="text-caption text-grey-6" style="font-size: 11px">
                    {{ v.files.slice(0, 2).join(', ') }}{{ v.files.length > 2 ? ` +${v.files.length - 2}` : '' }}
                  </div>
                </q-item-section>
              </q-item>
              <!-- Новая вариация -->
              <q-item
                clickable
                :active="selectedVariation === null"
                active-class="bg-green-1 text-green-9"
                class="rounded-borders"
                style="min-height: 36px"
                @click="selectedVariation = null"
              >
                <q-item-section avatar style="min-width: 24px">
                  <q-icon
                    :name="selectedVariation === null ? 'radio_button_checked' : 'radio_button_unchecked'"
                    size="16px"
                    :color="selectedVariation === null ? 'green-7' : 'grey-5'"
                  />
                </q-item-section>
                <q-item-section style="font-size: 13px">
                  Создать новую (Вариация {{ nextVariation }})
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
          <q-card-actions align="right">
            <q-btn
              flat
              no-caps
              label="Назад"
              color="grey-7"
              @click="copyStep = 1"
            />
            <q-btn
              unelevated
              no-caps
              label="Скопировать"
              color="green-7"
              :loading="copyingToCard"
              @click="confirmCopyToCard"
            />
          </q-card-actions>
        </template>
      </q-card>
    </q-dialog>

    <!-- Участники -->
    <q-dialog v-model="showMembers" @show="onMembersDialogOpen">
      <q-card style="min-width: 300px; max-width: 400px; width: 90vw">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">
            Участники
          </div>
          <q-space />
          <q-btn
            v-close-popup
            flat
            round
            dense
            icon="close"
          />
        </q-card-section>

        <q-list dense>
          <q-item v-for="m in members" :key="m.id">
            <q-item-section avatar>
              <q-avatar
                :color="m.member_type === 'employee' ? 'blue-2' : 'green-2'"
                :text-color="m.member_type === 'employee' ? 'blue-9' : 'green-9'"
                icon="person"
                size="28px"
              />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ m.display_name || m.guest_name || `#${m.id}` }}</q-item-label>
              <q-item-label caption>
                {{ m.role_in_project || (m.member_type === 'employee' ? 'Сотрудник' : 'Клиент') }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-btn
                flat
                round
                dense
                size="xs"
                icon="close"
                color="red-4"
                :loading="removingMemberId === m.id"
                @click.stop="removeMember(m)"
              >
                <q-tooltip>Удалить из чата</q-tooltip>
              </q-btn>
            </q-item-section>
          </q-item>
          <q-item v-if="!members.length">
            <q-item-section>
              <q-item-label class="text-grey">
                Нет участников
              </q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <template v-if="availableEmployees !== null">
          <q-separator class="q-mt-sm" />
          <q-card-section class="q-py-sm">
            <div class="text-body2 text-weight-medium text-blue-grey-7 q-mb-xs">
              Добавить в чат
            </div>
            <div v-if="loadingAvailableEmps" class="text-center q-py-sm">
              <q-spinner size="20px" color="grey" />
            </div>
            <div v-else-if="!availableEmployees.length" class="text-caption text-grey-5 q-py-xs" style="font-style: italic">
              Все сотрудники карточки уже в чате
            </div>
            <q-list v-else dense>
              <q-item
                v-for="emp in availableEmployees"
                :key="emp.id"
                clickable
                class="rounded-borders"
                @click="addMemberToChat(emp)"
              >
                <q-item-section avatar>
                  <q-avatar color="grey-3" text-color="grey-8" icon="person_add" size="28px" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ emp.name }}</q-item-label>
                  <q-item-label caption>
                    {{ emp.role }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-spinner v-if="addingMemberId === emp.id" size="18px" color="blue-6" />
                  <q-icon v-else name="add_circle_outline" color="blue-6" size="20px" />
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </template>

        <q-card-actions align="right" class="q-pt-none">
          <q-btn
            v-close-popup
            flat
            no-caps
            label="Закрыть"
            color="grey-7"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { api } from 'src/boot/axios'
import { useChatWebSocket } from 'src/composables/useChatWebSocket'
import { useAuthStore } from 'src/stores/auth'
import { useChatUnreadStore } from 'src/stores/chatUnread'
import { useQuasar } from 'quasar'

const route = useRoute()
const authStore = useAuthStore()
const chatUnreadStore = useChatUnreadStore()
const $q = useQuasar()
const chatId = Number(route.params.chatId)

const { isConnected: wsConnected, connectEmployee, disconnect, sendMessage, sendTypingStart, sendTypingStop, sendRead, typingUsers } = useChatWebSocket()

const chatTitle = ref('Чат сотрудников')
const messages = ref([])
const members = ref([])
const inputText = ref('')
const loadingMessages = ref(false)
const showMembers = ref(false)
const messagesEl = ref(null)
const availableEmployees = ref(null)
const loadingAvailableEmps = ref(false)
const addingMemberId = ref(null)
const removingMemberId = ref(null)
const chatCrmCardId = ref(null)
const fileInput = ref(null)
const clientChatId = ref(null)
const chatPageH = ref('100dvh')
const uploadProgress = ref(0)
// Диалог пересылки
const showForwardDialog = ref(false)
const forwardingMsg = ref(null)
const forwardTargetChats = ref([])
const loadingForwardChats = ref(false)
const selectedForwardChatId = ref(null)
const sendingForward = ref(false)
const forwardSearchQuery = ref('')
const filteredForwardChats = computed(() => {
  const q = forwardSearchQuery.value.trim().toLowerCase()
  if (!q) return forwardTargetChats.value
  return forwardTargetChats.value.filter(c => (c.title || `Чат #${c.id}`).toLowerCase().includes(q))
})

// Группировка сообщений: consecutive messages с одинаковым group_id → медиа-группа
const renderedItems = computed(() => {
  const items = []
  let i = 0
  const msgs = messages.value
  while (i < msgs.length) {
    const msg = msgs[i]
    if (msg.group_id && msg.message_type === 'image' && !msg.is_deleted && !msg._uploading) {
      const group = [msg]
      let j = i + 1
      while (j < msgs.length && msgs[j].group_id === msg.group_id && !msgs[j].is_deleted) {
        group.push(msgs[j])
        j++
      }
      if (group.length > 1) {
        items.push({ type: 'group', msgs: group, key: `g_${msg.group_id}` })
        i = j
        continue
      }
    }
    items.push({ type: 'single', msg, key: `s_${msg.id ?? i}` })
    i++
  }
  return items
})

function galleryGridClass(count) {
  if (count <= 1) return 'media-grid-1'
  if (count === 2) return 'media-grid-2'
  if (count === 3) return 'media-grid-3'
  return 'media-grid-4plus'
}

function groupCaption(msgs) {
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].content) return msgs[i].content
  }
  return ''
}

// Первое непрочитанное сообщение
const firstUnreadId = ref(null)

// Ожидающие отправки файлы + подпись
const pendingFiles = ref([])
const pendingCaption = ref('')

// Закреплённое сообщение
const pinnedMsg = ref(null)

// Редактирование
const editingMsgId = ref(null)
const editContent = ref('')
const savingEdit = ref(false)
// Удаление
const deletingMsgId = ref(null)
// Копирование в карточку
const showCopyToCard = ref(false)
const copyToCardMsg = ref(null)
const selectedDestination = ref(null)
const copyingToCard = ref(false)
const copyStep = ref(1) // 1 = выбор назначения, 2 = выбор вариации
const stageVariations = ref([]) // [{variation: N, files: [...]}]
const nextVariation = ref(1)
const selectedVariation = ref(null) // число = конкретная вариация, null = новая
const loadingVariations = ref(false)

// Только для этих назначений показываем шаг выбора вариации
// Правки не нуждаются в вариации (файл идёт прямо в папку правки)
const STAGE_KEYS = new Set(['stage_1', 'stage_2', 'stage_3'])

const COPY_DESTINATIONS = [
  { group: 'Договор', items: [
    { label: 'Договор', value: 'contract_file_yandex_path' },
    { label: 'Доп. соглашение', value: 'additional_agreement_yandex_path' },
  ] },
  { group: 'Акты', items: [
    { label: 'Акт планировочного', value: 'act_planning_yandex_path' },
    { label: 'Акт концептуального', value: 'act_concept_yandex_path' },
    { label: 'Акт финального', value: 'act_final_yandex_path' },
    { label: 'Информационное письмо', value: 'info_letter_yandex_path' },
    { label: 'Акт планировочного (подписанный)', value: 'act_planning_signed_yandex_path' },
    { label: 'Акт концептуального (подписанный)', value: 'act_concept_signed_yandex_path' },
    { label: 'Акт финального (подписанный)', value: 'act_final_signed_yandex_path' },
    { label: 'Информационное письмо (подписанное)', value: 'info_letter_signed_yandex_path' },
  ] },
  { group: 'Чеки', items: [
    { label: 'Чек аванса', value: 'advance_receipt_yandex_path' },
    { label: 'Чек доплаты', value: 'additional_receipt_yandex_path' },
    { label: 'Чек (3-й платёж)', value: 'third_receipt_yandex_path' },
  ] },
  { group: 'Общие данные', items: [
    { label: 'ТЗ', value: 'tech_task_yandex_path' },
    { label: 'Фотофиксация', value: 'photo_documentation_yandex_path' },
    { label: 'Референсы', value: 'references_yandex_path' },
    { label: 'Замер', value: 'measurement_yandex_path' },
  ] },
  { group: 'Стадии', items: [
    { label: 'Стадия 1: Планировочное решение', value: 'stage_1' },
    { label: 'Стадия 1: Правки', value: 'stage_1_revisions' },
    { label: 'Стадия 2: Концепция дизайна', value: 'stage_2' },
    { label: 'Стадия 2: Правки', value: 'stage_2_revisions' },
    { label: 'Стадия 3: Чертёжная документация', value: 'stage_3' },
    { label: 'Стадия 3: Правки', value: 'stage_3_revisions' },
  ] },
]

function recalcChatH() {
  const vh = window.visualViewport?.height ?? window.innerHeight
  const header = document.querySelector('.q-header')
  const footer = document.querySelector('.q-footer')
  const headerH = header?.offsetHeight ?? 0
  const footerH = footer?.offsetHeight ?? 0
  chatPageH.value = Math.max(300, vh - headerH - footerH) + 'px'
  scrollToBottom()
}

let typingTimer = null

const typingText = computed(() => {
  if (!typingUsers.value.length) return ''
  const names = typingUsers.value.map(u => u.name)
  if (names.length === 1) return `${names[0]} печатает…`
  return `${names.join(', ')} печатают…`
})

function isOwn(msg) {
  const myId = authStore.user?.id
  if (!myId) return false
  return Number(msg.sender_employee_id) === Number(myId)
}

function imgStreamUrl(msg) {
  if (!msg.yandex_path) return ''
  const path = msg.yandex_path.replace(/^disk:/, '')
  const token = localStorage.getItem('access_token') || ''
  return `/api/v1/files/stream?yandex_path=${encodeURIComponent(path)}&token=${encodeURIComponent(token)}`
}

function formatTime(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  })
}

function scrollToFirstUnread() {
  nextTick(() => {
    const container = messagesEl.value
    if (!container) return
    if (firstUnreadId.value) {
      // Прокручиваем к разделителю (который стоит перед первым непрочитанным)
      const divider = container.querySelector('[data-unread-divider]')
      const target = divider || container.querySelector(`[data-msg-id="${firstUnreadId.value}"]`)
      if (target) {
        const containerRect = container.getBoundingClientRect()
        const targetRect = target.getBoundingClientRect()
        container.scrollTop = container.scrollTop + (targetRect.top - containerRect.top) - 8
        return
      }
    }
    container.scrollTop = container.scrollHeight
  })
}

async function loadMessages() {
  loadingMessages.value = true
  try {
    const { data } = await api.get(`/api/v1/chats/${chatId}`)
    chatTitle.value = data.title || `Чат #${chatId}`
    messages.value = data.messages || []
    members.value = data.members || []
    firstUnreadId.value = data.first_unread_message_id || null
    pinnedMsg.value = data.pinned_message || null
    scrollToFirstUnread()

    // Отметить прочитанными — REST гарантирует доставку до сервера (WS может быть не открыт ещё)
    if (messages.value.length) {
      const lastId = messages.value[messages.value.length - 1].id
      api.post(`/api/v1/chats/${chatId}/messages/${lastId}/read`).catch(() => {})
    }
    chatUnreadStore.markChatRead(chatId)

    chatCrmCardId.value = data.crm_card_id || null

    // Загрузить клиентский чат для той же карточки (для пересылки)
    if (data.crm_card_id) {
      loadClientChat(data.crm_card_id)
    }
  } catch (e) {
    console.error('[ChatRoom] Ошибка загрузки:', e)
  } finally {
    loadingMessages.value = false
  }
}

async function loadClientChat(cardId) {
  try {
    const { data } = await api.get('/api/v1/chats/', {
      params: { chat_type: 'client', crm_card_id: cardId },
    })
    const list = Array.isArray(data) ? data : (data.items || [])
    if (list.length > 0) {
      clientChatId.value = list[0].id
    }
  } catch {
    // Клиентский чат не найден — кнопка не показывается
  }
}

async function openForwardDialog(msg) {
  forwardingMsg.value = msg
  selectedForwardChatId.value = null
  forwardSearchQuery.value = ''
  showForwardDialog.value = true
  loadingForwardChats.value = true
  try {
    const { data } = await api.get('/api/v1/chats/')
    forwardTargetChats.value = (Array.isArray(data) ? data : (data.items || []))
      .filter(c => c.id !== chatId)
  } catch {
    forwardTargetChats.value = []
  } finally {
    loadingForwardChats.value = false
  }
}

async function doForward() {
  if (!forwardingMsg.value || !selectedForwardChatId.value) return
  sendingForward.value = true
  try {
    await api.post(`/api/v1/chats/${chatId}/forward/${selectedForwardChatId.value}`, { msg_id: forwardingMsg.value.id })
    $q.notify({ type: 'positive', message: 'Переслано' })
    showForwardDialog.value = false
  } catch (e) {
    const raw = e.response?.data?.detail
    const message = Array.isArray(raw) ? raw.map(d => d.msg || String(d)).join('; ') : (raw || 'Ошибка пересылки')
    $q.notify({ type: 'negative', message: String(message) })
  } finally {
    sendingForward.value = false
  }
}

function sendText() {
  const text = inputText.value.trim()
  if (!text) return
  sendMessage(text)
  inputText.value = ''
}

function onTyping() {
  sendTypingStart()
  if (typingTimer) clearTimeout(typingTimer)
  typingTimer = setTimeout(() => {
    sendTypingStop()
  }, 2000)
}

// ── Edit ──────────────────────────────────────────────────────────────────
function startEdit(msg) {
  editingMsgId.value = msg.id
  editContent.value = msg.content || ''
}
function cancelEdit() {
  editingMsgId.value = null
  editContent.value = ''
}
async function saveEdit() {
  if (!editContent.value.trim()) return
  savingEdit.value = true
  try {
    const { data: updated } = await api.patch(
      `/api/v1/chats/${chatId}/messages/${editingMsgId.value}`,
      { content: editContent.value.trim() },
    )
    const idx = messages.value.findIndex(m => m.id === editingMsgId.value)
    if (idx !== -1) messages.value.splice(idx, 1, updated)
    cancelEdit()
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Ошибка редактирования' })
  } finally {
    savingEdit.value = false
  }
}

// ── Delete ────────────────────────────────────────────────────────────────
async function deleteMsg(msg) {
  if (deletingMsgId.value) return
  deletingMsgId.value = msg.id
  try {
    await api.delete(`/api/v1/chats/${chatId}/messages/${msg.id}`)
    const idx = messages.value.findIndex(m => m.id === msg.id)
    if (idx !== -1) {
      messages.value[idx] = { ...messages.value[idx], is_deleted: true, content: '[Сообщение удалено]' }
    }
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Ошибка удаления' })
  } finally {
    deletingMsgId.value = null
  }
}

// ── Copy to card ──────────────────────────────────────────────────────────
function openCopyToCard(msg) {
  copyToCardMsg.value = msg
  selectedDestination.value = null
  copyStep.value = 1
  stageVariations.value = []
  selectedVariation.value = null
  showCopyToCard.value = true
}

async function goToVariationStep() {
  if (!selectedDestination.value || !chatCrmCardId.value) return
  if (!STAGE_KEYS.has(selectedDestination.value)) {
    await confirmCopyToCard()
    return
  }
  loadingVariations.value = true
  try {
    const { data } = await api.get(`/api/v1/chats/${chatId}/card-stage-variations`, {
      params: { crm_card_id: chatCrmCardId.value, destination: selectedDestination.value },
    })
    stageVariations.value = data.variations || []
    nextVariation.value = data.next_variation || 1
    selectedVariation.value = stageVariations.value.length > 0 ? stageVariations.value[0].variation : null
    copyStep.value = 2
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Ошибка загрузки вариаций' })
  } finally {
    loadingVariations.value = false
  }
}

async function confirmCopyToCard() {
  if (!selectedDestination.value || !copyToCardMsg.value || !chatCrmCardId.value) return
  copyingToCard.value = true
  try {
    const body = { crm_card_id: chatCrmCardId.value, destination: selectedDestination.value }
    if (STAGE_KEYS.has(selectedDestination.value) && selectedVariation.value !== null) {
      body.variation = selectedVariation.value
    }
    await api.post(
      `/api/v1/chats/${chatId}/messages/${copyToCardMsg.value.id}/copy-to-card`,
      body,
    )
    $q.notify({ type: 'positive', message: 'Файл скопирован в карточку' })
    showCopyToCard.value = false
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Ошибка копирования' })
  } finally {
    copyingToCard.value = false
  }
}

// ── File upload ───────────────────────────────────────────────────────────
const IMAGE_EXTS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif']

function isImageFile(file) {
  return IMAGE_EXTS.includes(file.name.split('.').pop()?.toLowerCase() || '')
}

function pickFile() {
  fileInput.value?.click()
}

// Выбор файлов → pending (не сразу загружать)
function onFileSelected(event) {
  const files = [...(event.target.files || [])]
  if (!files.length) return
  pendingFiles.value = [...pendingFiles.value, ...files]
  event.target.value = ''
}

function removePendingFile(idx) {
  pendingFiles.value = pendingFiles.value.filter((_, i) => i !== idx)
  if (!pendingFiles.value.length) pendingCaption.value = ''
}

// Отправить pending файлы (с подписью и group_id для нескольких изображений)
async function sendWithAttachment() {
  const files = pendingFiles.value
  if (!files.length) return
  const caption = pendingCaption.value.trim()
  const allImages = files.every(f => isImageFile(f))
  const groupId = (files.length > 1 && allImages) ? crypto.randomUUID() : null

  pendingFiles.value = []
  pendingCaption.value = ''

  uploadProgress.value = 1
  const errors = []
  for (let i = 0; i < files.length; i++) {
    try {
      await _uploadSingleFile(files[i], groupId, i === files.length - 1 ? caption : null)
    } catch {
      errors.push(files[i].name)
    }
  }
  uploadProgress.value = 0
  if (errors.length) $q.notify({ type: 'negative', message: `Ошибка загрузки: ${errors.join(', ')}` })
}

async function _uploadSingleFile(file, groupId = null, caption = null) {
  const ext = file.name.split('.').pop()?.toLowerCase() || ''
  const msgType = IMAGE_EXTS.includes(ext) ? 'image' : 'file'
  const tempId = `temp_${Date.now()}_${Math.random()}`
  messages.value.push({
    id: tempId,
    sender_employee_id: authStore.user?.id,
    sender_display_name: authStore.user?.full_name || 'Вы',
    message_type: msgType,
    content: caption || null,
    group_id: groupId,
    file_url: '',
    file_name: file.name,
    file_size: file.size,
    yandex_path: null,
    is_deleted: false,
    is_edited: false,
    is_pinned: false,
    created_at: new Date().toISOString(),
    _uploading: true,
  })
  scrollToBottom()
  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('message_type', msgType)
    if (groupId) formData.append('group_id', groupId)
    if (caption) formData.append('caption', caption)
    const { data: savedMsg } = await api.post(`/api/v1/chats/${chatId}/files`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        uploadProgress.value = e.total ? Math.round((e.loaded / e.total) * 100) : 50
      },
    })
    const idx = messages.value.findIndex(m => m.id === tempId)
    if (idx !== -1) {
      const alreadyAdded = messages.value.some(m => m.id === savedMsg.id)
      alreadyAdded ? messages.value.splice(idx, 1) : messages.value.splice(idx, 1, savedMsg)
    }
  } catch {
    messages.value = messages.value.filter(m => m.id !== tempId)
    throw new Error(file.name)
  }
}

// ── Pin / Unpin ────────────────────────────────────────────────────────────
async function togglePin(msg) {
  try {
    const { data } = await api.post(`/api/v1/chats/${chatId}/messages/${msg.id}/pin`)
    // Обновить локальный список
    messages.value.forEach((m, i) => {
      if (m.is_pinned && m.id !== msg.id) messages.value[i] = { ...m, is_pinned: false }
    })
    const idx = messages.value.findIndex(m => m.id === msg.id)
    if (idx !== -1) messages.value[idx] = { ...messages.value[idx], is_pinned: data.pinned }
    pinnedMsg.value = data.pinned ? (messages.value.find(m => m.id === msg.id) || null) : null
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Ошибка закрепления' })
  }
}

function scrollToPinned() {
  if (!pinnedMsg.value) return
  nextTick(() => {
    const el = messagesEl.value?.querySelector(`[data-msg-id="${pinnedMsg.value.id}"]`)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  })
}

function playVoice(url) {
  if (url) window.open(url, '_blank')
}

async function onMembersDialogOpen() {
  if (!chatCrmCardId.value) return
  availableEmployees.value = null
  loadingAvailableEmps.value = true
  try {
    const { data } = await api.get(`/api/v1/crm/cards/${chatCrmCardId.value}`)
    const emps = new Map()
    const roles = [
      { id: data.senior_manager_id, name: data.senior_manager_name, role: 'Старший менеджер' },
      { id: data.sdp_id, name: data.sdp_name, role: 'СДП' },
      { id: data.gap_id, name: data.gap_name, role: 'ГАП' },
      { id: data.manager_id, name: data.manager_name, role: 'Менеджер' },
      { id: data.surveyor_id, name: data.surveyor_name, role: 'Замерщик' },
    ]
    for (const r of roles) {
      if (r.id && r.name) emps.set(r.id, { name: r.name, role: r.role })
    }
    for (const se of (data.stage_executors || [])) {
      if (se.executor_id && se.executor_name) {
        emps.set(se.executor_id, { name: se.executor_name, role: se.stage_name || 'Исполнитель' })
      }
    }
    const memberIds = new Set(members.value.filter(m => m.employee_id).map(m => m.employee_id))
    availableEmployees.value = [...emps.entries()]
      .filter(([id]) => !memberIds.has(id))
      .map(([id, info]) => ({ id, name: info.name, role: info.role }))
  } catch {
    availableEmployees.value = []
  } finally {
    loadingAvailableEmps.value = false
  }
}

async function addMemberToChat(emp) {
  if (addingMemberId.value) return
  addingMemberId.value = emp.id
  try {
    await api.post(`/api/v1/chats/${chatId}/members`, { employee_id: emp.id })
    const { data } = await api.get(`/api/v1/chats/${chatId}`)
    members.value = data.members || []
    availableEmployees.value = availableEmployees.value.filter(e => e.id !== emp.id)
    $q.notify({ type: 'positive', message: `${emp.name} добавлен в чат` })
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Ошибка добавления' })
  } finally {
    addingMemberId.value = null
  }
}

async function removeMember(m) {
  if (removingMemberId.value) return
  removingMemberId.value = m.id
  try {
    await api.delete(`/api/v1/chats/${chatId}/members/${m.id}`)
    members.value = members.value.filter(mb => mb.id !== m.id)
    $q.notify({ type: 'positive', message: `${m.display_name || 'Участник'} удалён из чата` })
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Ошибка удаления' })
  } finally {
    removingMemberId.value = null
  }
}

onMounted(() => {
  recalcChatH()
  window.addEventListener('resize', recalcChatH)
  window.visualViewport?.addEventListener('resize', recalcChatH)
  loadMessages()
  const token = localStorage.getItem('access_token')
  if (token) {
    connectEmployee(chatId, token, {
      onMessage: (msg) => {
        const exists = messages.value.some(m => m.id === msg.id)
        if (!exists) {
          messages.value.push(msg)
          scrollToBottom()
          sendRead(msg.id)
        }
      },
      onMessageUpdated: (msg) => {
        const idx = messages.value.findIndex(m => m.id === msg.id)
        if (idx !== -1) messages.value.splice(idx, 1, msg)
      },
      onMessageDeleted: (msgId) => {
        const idx = messages.value.findIndex(m => m.id === msgId)
        if (idx !== -1) {
          messages.value[idx] = { ...messages.value[idx], is_deleted: true, content: '[Сообщение удалено]' }
        }
      },
      onMemberAdded: async () => {
        try {
          const { data } = await api.get(`/api/v1/chats/${chatId}`)
          members.value = data.members || []
        } catch { }
      },
      onMemberRemoved: (evt) => {
        if (evt.member_id) {
          members.value = members.value.filter(m => m.id !== evt.member_id)
        }
      },
    })
  }
})

onUnmounted(() => {
  disconnect()
  window.removeEventListener('resize', recalcChatH)
  window.visualViewport?.removeEventListener('resize', recalcChatH)
  if (typingTimer) clearTimeout(typingTimer)
})
</script>

<style scoped>
.bubble-own {
  background: #E8F5E9;
  border-radius: 12px 12px 2px 12px;
  padding: 8px 12px;
}
.bubble-other {
  background: #fff;
  border-radius: 12px 12px 12px 2px;
  padding: 8px 12px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}
/* Telegram-стиль: картинка на всю ширину пузыря, без внутреннего padding */
.bubble-img-own {
  background: #E8F5E9;
  border-radius: 12px 12px 2px 12px;
  overflow: hidden;
  min-width: 160px;
  max-width: 280px;
}
.bubble-img-other {
  background: #fff;
  border-radius: 12px 12px 12px 2px;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
  min-width: 160px;
  max-width: 280px;
}
.hidden {
  display: none;
}
/* Медиа-галерея */
.media-grid-1 { display: block; }
.media-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 2px; }
.media-grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 2px; }
.media-grid-4plus { display: grid; grid-template-columns: 1fr 1fr; gap: 2px; }
</style>
