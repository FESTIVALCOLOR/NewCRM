<template>
  <q-page class="column" :style="{ height: chatPageH, overflow: 'hidden' }">
    <!-- Шапка -->
    <div
      class="row items-center q-px-md q-py-sm bg-white"
      style="border-bottom: 1px solid #E0E0E0; flex-shrink: 0"
    >
      <div class="column" style="flex: 1; min-width: 0">
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
          <q-icon name="wifi_off" size="10px" color="negative" class="q-mr-xs" />переподключение…
        </div>
      </div>
    </div>

    <!-- Баннер установки PWA (inline, чтобы не перекрывать поле ввода) -->
    <PwaInstallBanner inline />

    <!-- Список сообщений -->
    <div
      ref="messagesEl"
      class="col q-pa-md"
      style="overflow-y: auto; background: #F5F5F5"
    >
      <!-- Sentinel для Intersection Observer (автозагрузка при скролле вверх) -->
      <div ref="topSentinelEl" style="height: 2px" />
      <div v-if="loadingOlder" class="text-center q-mb-sm">
        <q-spinner size="20px" color="grey-5" />
      </div>

      <div v-if="loadingMessages" class="text-center q-mt-lg">
        <q-spinner size="24px" color="grey" />
      </div>

      <div v-else-if="!messages.length" class="text-center text-grey q-mt-xl">
        <q-icon name="chat_bubble_outline" size="40px" />
        <div class="q-mt-sm text-body2">
          Напишите нам — мы ответим!
        </div>
      </div>

      <template v-else>
        <template v-for="item in renderedItems" :key="item.key">
          <!-- Галерея (несколько изображений одной отправкой) -->
          <template v-if="item.type === 'group'">
            <div class="q-mb-sm" :class="isOwn(item.msgs[0]) ? 'row justify-end' : 'row justify-start'">
              <div
                :class="[isOwn(item.msgs[0]) ? 'bubble-img-own' : 'bubble-img-staff']"
                :style="galleryBubbleStyle(item.msgs.length)"
              >
                <div class="row no-wrap items-center justify-between" style="padding: 6px 10px 4px; min-height: 16px; gap: 2px">
                  <div
                    class="text-caption text-weight-bold"
                    :style="{ color: isOwn(item.msgs[0]) ? '#1B5E20' : '#1565C0' }"
                    style="flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap"
                  >
                    {{ item.msgs[0].sender_display_name || (isOwn(item.msgs[0]) ? clientName : '') }}
                  </div>
                </div>
                <template v-if="item.msgs.length < 4">
                  <div :class="galleryGridClass(item.msgs.length)" :style="galleryGridStyle(item.msgs.length)">
                    <a
                      v-for="(gm, gi) in item.msgs"
                      :key="gm.id"
                      :href="gm.file_url"
                      target="_blank"
                      style="display: block; text-decoration: none; overflow: hidden"
                    >
                      <q-img
                        v-if="imgStreamUrl(gm)"
                        :src="imgStreamUrl(gm)"
                        :style="galleryImgStyle(item.msgs.length, gi)"
                        fit="cover"
                        spinner-color="grey-4"
                        spinner-size="20px"
                      />
                    </a>
                  </div>
                </template>
                <template v-else>
                  <div style="display: flex; flex-direction: column; gap: 2px">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2px">
                      <a
                        v-for="gm in item.msgs.slice(0, 2)"
                        :key="gm.id"
                        :href="gm.file_url"
                        target="_blank"
                        style="display: block; text-decoration: none; overflow: hidden"
                      >
                        <q-img
                          v-if="imgStreamUrl(gm)"
                          :src="imgStreamUrl(gm)"
                          style="width: 100%; display: block; height: 180px"
                          fit="cover"
                          spinner-color="grey-4"
                          spinner-size="20px"
                        />
                      </a>
                    </div>
                    <div v-if="item.msgs.length > 2" :style="galleryThumbGridStyle(item.msgs.length)">
                      <a
                        v-for="(gm, gi) in item.msgs.slice(2)"
                        :key="gm.id"
                        :href="gm.file_url"
                        target="_blank"
                        :style="galleryItemSpanStyle(item.msgs.length - 2, gi)"
                        style="display: block; text-decoration: none; overflow: hidden"
                      >
                        <q-img
                          v-if="imgStreamUrl(gm)"
                          :src="imgStreamUrl(gm)"
                          style="width: 100%; display: block; height: 90px"
                          fit="cover"
                          spinner-color="grey-4"
                          spinner-size="20px"
                        />
                      </a>
                    </div>
                  </div>
                </template>
                <div class="row no-wrap items-center justify-end" style="padding: 2px 8px 4px; color: #888; font-size: 10px">
                  <span class="text-caption">{{ formatTime(item.msgs[item.msgs.length - 1].created_at) }}</span>
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
                :id="`msg-${msg.id}`"
                :data-msg-id="msg.id"
                class="q-mb-sm"
                :class="isOwn(msg) ? 'row justify-end' : 'row justify-start'"
              >
                <!-- Системные сообщения -->
                <div v-if="msg.message_type === 'system'" class="text-center full-width">
                  <q-chip dense size="sm" color="green-1" text-color="green-9">
                    {{ msg.content }}
                  </q-chip>
                </div>

                <!-- Обычные -->
                <div
                  v-else
                  :class="[(msg.message_type === 'image' || (isPdf(msg) && pdfThumbnails[msg.id]))
                    ? (isOwn(msg) ? 'bubble-img-own' : 'bubble-img-staff')
                    : (isOwn(msg) ? 'bubble-own' : 'bubble-staff'), { 'bubble-forwarded': isForwarded(msg) }]"
                  :style="pdfBubbleStyle(msg)"
                >
                  <!-- Верхняя строка: имя отправителя + кнопка меню -->
                  <div
                    class="row no-wrap items-center justify-between q-mb-xs"
                    :style="(msg.message_type === 'image' || (isPdf(msg) && pdfThumbnails[msg.id])) ? 'min-height:16px;gap:2px;padding:6px 10px 4px' : 'min-height:16px;gap:2px'"
                  >
                    <div
                      class="text-caption text-weight-bold"
                      :style="{ color: isOwn(msg) ? '#1B5E20' : '#1565C0', flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }"
                    >
                      {{ msg.sender_display_name || (isOwn(msg) ? clientName : '') }}
                    </div>
                    <q-btn
                      v-if="!msg.is_deleted"
                      flat
                      round
                      dense
                      size="xs"
                      icon="more_vert"
                      color="grey-5"
                      style="margin: -4px -6px -2px 2px; flex-shrink: 0"
                    >
                      <q-menu auto-close>
                        <q-list dense style="min-width: 210px; white-space: nowrap">
                          <!-- Быстрые реакции -->
                          <q-item dense style="padding: 4px 8px 2px">
                            <div class="row items-center">
                              <button
                                v-for="em in QUICK_EMOJIS"
                                :key="em"
                                class="react-quick-btn"
                                :class="{ 'react-quick-btn--active': isOwnGuestReaction(msg, em) }"
                                @click.stop="sendGuestReaction(msg, em)"
                              >
                                {{ em }}
                              </button>
                            </div>
                          </q-item>
                          <q-separator />
                          <q-item clickable @click="replyingTo = msg">
                            <q-item-section avatar>
                              <q-icon name="reply" size="16px" color="grey-7" />
                            </q-item-section>
                            <q-item-section style="font-size: 12px">
                              Ответить
                            </q-item-section>
                          </q-item>
                          <q-separator v-if="isOwn(msg)" />
                          <q-item
                            v-if="isOwn(msg) && msg.message_type === 'text'"
                            clickable
                            @click="startClientEdit(msg)"
                          >
                            <q-item-section avatar>
                              <q-icon name="edit" size="16px" color="grey-7" />
                            </q-item-section>
                            <q-item-section style="font-size: 12px">
                              Редактировать
                            </q-item-section>
                          </q-item>
                          <q-separator v-if="isOwn(msg)" />
                          <q-item v-if="isOwn(msg)" clickable @click="deleteClientMsg(msg)">
                            <q-item-section avatar>
                              <q-icon name="delete_outline" size="16px" color="red-5" />
                            </q-item-section>
                            <q-item-section class="text-red-6" style="font-size: 12px">
                              Удалить
                            </q-item-section>
                          </q-item>
                        </q-list>
                      </q-menu>
                    </q-btn>
                  </div>

                  <!-- Цитата (reply preview) -->
                  <div
                    v-if="msg.reply_preview"
                    class="reply-quote q-mb-xs"
                    style="cursor: pointer"
                    @click="scrollToMsg(msg.reply_preview.id)"
                  >
                    <div class="row no-wrap items-center" style="gap: 6px">
                      <q-img
                        v-if="msg.reply_preview.message_type === 'image' && msg.reply_preview.yandex_path"
                        :src="imgStreamUrl({ yandex_path: msg.reply_preview.yandex_path })"
                        style="width: 36px; height: 36px; border-radius: 3px; flex-shrink: 0"
                        fit="cover"
                        spinner-size="12px"
                      />
                      <div style="min-width: 0">
                        <div class="text-caption text-weight-bold" style="color: #1565C0; line-height: 1.2">
                          {{ msg.reply_preview.sender_display_name }}
                        </div>
                        <div class="text-caption ellipsis" style="color: #555; line-height: 1.3">
                          {{ msg.reply_preview.message_type === 'image' ? '[Изображение]' : msg.reply_preview.message_type === 'file' ? '[Файл]' : msg.reply_preview.content }}
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Загрузка файла (оптимистичное сообщение) -->
                  <template v-if="msg._uploading">
                    <div v-if="msg._previewUrl">
                      <q-img :src="msg._previewUrl" style="width:100%;max-height:200px;display:block" fit="cover" />
                      <div class="row items-center q-gutter-xs" style="padding:3px 8px 2px;opacity:0.7">
                        <q-spinner size="10px" color="grey-5" />
                        <span class="text-caption text-grey-6">{{ msg.file_name }}</span>
                      </div>
                    </div>
                    <div v-else class="row items-center q-gutter-xs">
                      <q-icon :name="isPdf(msg) ? 'picture_as_pdf' : 'upload'" size="16px" :color="isPdf(msg) ? 'red-5' : 'grey-5'" />
                      <span class="text-caption text-grey-6" style="word-break:break-word">{{ msg.file_name }}…</span>
                      <q-spinner size="12px" color="grey-5" />
                    </div>
                  </template>
                  <template v-else-if="msg.message_type === 'image'">
                    <div style="display: block; text-decoration: none; color: inherit; cursor: pointer" @click="openGallery(msg)">
                      <q-img
                        v-if="imgStreamUrl(msg)"
                        :src="imgStreamUrl(msg)"
                        style="width: 100%; max-height: clamp(160px, 35vh, 480px); display: block; min-height: 80px"
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
                    </div>
                  </template>
                  <template v-else-if="msg.message_type === 'file'">
                    <div v-if="isPdf(msg) && pdfThumbnails[msg.id]">
                      <a :href="msg.file_url" target="_blank" style="display:block;text-decoration:none">
                        <img
                          :src="pdfThumbnails[msg.id]"
                          style="display:block;max-height:200px;width:auto;max-width:min(85vw,440px);cursor:pointer"
                          @load="(e) => { pdfImgWidths[msg.id] = e.target.offsetWidth }"
                        >
                      </a>
                      <div style="padding:3px 8px 2px;display:flex;align-items:center;gap:4px;overflow:hidden">
                        <q-icon name="picture_as_pdf" size="14px" color="red-6" style="flex-shrink:0" />
                        <a :href="msg.file_url" target="_blank" class="text-caption ellipsis" style="flex:1;min-width:0;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;color:inherit">{{ msg.file_name || 'Документ' }}</a>
                      </div>
                    </div>
                    <div v-else class="row items-center q-gutter-xs">
                      <q-icon :name="isPdf(msg) ? 'picture_as_pdf' : 'attach_file'" :size="isPdf(msg) ? '28px' : '18px'" :color="isPdf(msg) ? 'red-6' : 'grey-7'" />
                      <a :href="msg.file_url" target="_blank" class="text-body2 ellipsis" style="max-width:200px;color:inherit">{{ msg.file_name || 'Файл' }}</a>
                    </div>
                  </template>

                  <!-- Голосовое -->
                  <template v-else-if="msg.message_type === 'voice'">
                    <audio
                      :ref="el => { if (el) _voiceRefs[msg.id] = el }"
                      :src="imgStreamUrl(msg)"
                      preload="none"
                      style="display: none"
                      @timeupdate="voiceCurrent[msg.id] = $event.target.currentTime"
                      @ended="voicePlaying[msg.id] = false; voiceCurrent[msg.id] = 0"
                      @play="voicePlaying[msg.id] = true"
                      @pause="voicePlaying[msg.id] = false"
                    />
                    <div class="row items-center" style="gap: 6px; width: 220px; padding: 4px 0">
                      <q-btn
                        flat
                        round
                        dense
                        :icon="voicePlaying[msg.id] ? 'pause' : 'play_arrow'"
                        color="primary"
                        size="sm"
                        @click="toggleVoice(msg)"
                      />
                      <div class="column" style="flex: 1; min-width: 0; gap: 3px">
                        <div style="height: 3px; background: #e0e0e0; border-radius: 2px; overflow: hidden">
                          <div :style="{ width: voiceProgressPct(msg) + '%', background: '#1976d2', height: '100%' }" />
                        </div>
                        <div class="text-caption text-grey-6" style="font-size: 10px">
                          {{ voicePlaying[msg.id] ? fmtDuration(voiceCurrent[msg.id]) : fmtDuration(msg.content) }}
                        </div>
                      </div>
                    </div>
                  </template>

                  <template v-else>
                    <div class="text-body2" style="white-space: pre-wrap; word-break: break-word">
                      {{ msg.content }}
                    </div>
                  </template>

                  <!-- Inline-редактирование -->
                  <div v-if="editingClientMsgId === msg.id" class="q-mt-xs">
                    <q-input
                      v-model="editClientContent"
                      dense
                      outlined
                      autofocus
                      autogrow
                      hide-bottom-space
                      style="font-size: 13px"
                      @keydown.enter.exact.prevent="saveClientEdit"
                      @keydown.escape="cancelClientEdit"
                    />
                    <div class="row justify-end q-gutter-xs q-mt-xs">
                      <q-btn
                        flat
                        dense
                        no-caps
                        size="sm"
                        label="Отмена"
                        color="grey-6"
                        @click="cancelClientEdit"
                      />
                      <q-btn
                        unelevated
                        dense
                        no-caps
                        size="sm"
                        label="Сохранить"
                        color="green-7"
                        :loading="savingClientEdit"
                        @click="saveClientEdit"
                      />
                    </div>
                  </div>

                  <!-- Нижняя строка: время -->
                  <div
                    class="row no-wrap items-center"
                    :class="isOwn(msg) ? 'justify-end' : 'justify-start'"
                    :style="(msg.message_type === 'image' || (isPdf(msg) && pdfThumbnails[msg.id])) ? 'padding:2px 10px 6px;margin-top:0' : 'margin-top:4px'"
                  >
                    <span v-if="msg.is_edited" class="text-caption text-grey-5 q-mr-xs" style="font-size: 9px">изм.</span>
                    <div class="text-caption" style="color: #888; font-size: 10px">
                      {{ formatTime(msg.created_at) }}
                    </div>
                  </div>
                  <!-- Реакции -->
                  <div
                    v-if="msg.reactions && Object.keys(msg.reactions).length"
                    class="row items-center q-gutter-xs"
                    :style="(msg.message_type === 'image' || (isPdf(msg) && pdfThumbnails[msg.id])) ? 'margin-top: 0; padding: 0 10px 4px; flex-wrap: wrap' : 'margin-top: 4px; flex-wrap: wrap'"
                  >
                    <button
                      v-for="(reactors, emoji) in msg.reactions"
                      :key="emoji"
                      class="reaction-chip"
                      :class="{ 'reaction-chip--own': isOwnGuestReaction(msg, emoji) }"
                      @click="sendGuestReaction(msg, emoji)"
                    >
                      {{ emoji }} {{ reactors.length }}
                    </button>
                  </div>
                </div>
              </div>
            </template>
          </template>
        </template>
      </template>
    </div>

    <!-- Прогресс загрузки файла -->
    <q-linear-progress
      v-if="uploadProgress > 0 && uploadProgress < 100"
      :value="uploadProgress / 100"
      color="green-6"
      style="flex-shrink: 0"
    />

    <!-- Панель ответа -->
    <div
      v-if="replyingTo"
      class="row items-center q-px-md q-py-xs bg-white"
      style="border-top: 1px solid #E0E0E0; flex-shrink: 0; gap: 8px"
    >
      <q-icon name="reply" size="16px" color="grey-5" />
      <div class="col" style="min-width: 0">
        <div class="text-caption text-weight-bold text-blue-8 ellipsis">
          {{ replyingTo.sender_display_name }}
        </div>
        <div class="text-caption text-grey-7 ellipsis">
          {{ replyingTo.message_type === 'image' ? '[Изображение]' : replyingTo.message_type === 'file' ? '[Файл]' : replyingTo.content }}
        </div>
      </div>
      <q-btn
        flat
        round
        dense
        size="xs"
        icon="close"
        color="grey-5"
        @click="replyingTo = null"
      />
    </div>

    <!-- Панель ввода -->
    <div class="q-pa-sm bg-white" style="border-top: 1px solid #E0E0E0; flex-shrink: 0">
      <div class="row items-center q-gutter-xs">
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
        <!-- Запись голоса: удерживать для записи -->
        <q-btn
          v-if="!inputText.trim()"
          round
          dense
          icon="mic"
          :color="isRecording ? 'red-6' : 'grey-6'"
          @pointerdown.prevent="onVoiceBtnDown"
          @pointerup="onVoiceBtnUp"
          @pointercancel="onVoiceBtnCancel"
          @contextmenu.prevent
        >
          <q-tooltip>Удерживайте для записи голосового</q-tooltip>
        </q-btn>
        <div v-if="isRecording" class="text-caption text-red-6 q-mx-xs" style="flex: 1">
          ● {{ recordSeconds }}с — отпустите для отправки
        </div>
        <q-input
          v-if="!isRecording"
          v-model="inputText"
          outlined
          dense
          autogrow
          hide-bottom-space
          placeholder="Ваше сообщение…"
          style="flex: 1"
          @keydown.enter.exact.prevent="sendText"
          @input="onTyping"
        />
        <q-btn
          v-if="!isRecording"
          round
          dense
          icon="send"
          color="green-7"
          :disable="!inputText.trim()"
          @click="sendText"
        />
      </div>
    </div>
    <!-- Галерея изображений -->
    <q-dialog v-model="galleryOpen" maximized>
      <div class="column" style="background: #000; width: 100%; height: 100%">
        <div class="row items-center justify-between q-pa-sm" style="flex-shrink: 0">
          <q-btn
            flat
            round
            dense
            icon="close"
            color="white"
            @click="galleryOpen = false"
          />
          <span class="text-caption text-white">{{ galleryIndex + 1 }} / {{ galleryImages.length }}</span>
          <a :href="galleryImages[galleryIndex]?.file_url" target="_blank" style="text-decoration: none">
            <q-btn
              flat
              round
              dense
              icon="open_in_new"
              color="white"
            />
          </a>
        </div>
        <q-carousel
          v-model="galleryIndex"
          animated
          swipeable
          navigation
          infinite
          style="flex: 1; background: #000"
          control-color="white"
        >
          <q-carousel-slide
            v-for="(img, idx) in galleryImages"
            :key="img.id"
            :name="idx"
            style="padding: 0; display: flex; align-items: center; justify-content: center"
          >
            <q-img
              :src="imgStreamUrl(img)"
              style="max-width: 100%; max-height: 100%"
              fit="contain"
              spinner-color="grey-4"
              spinner-size="32px"
            />
          </q-carousel-slide>
        </q-carousel>
      </div>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChatWebSocket } from 'src/composables/useChatWebSocket'
import { useQuasar } from 'quasar'
import { getPdfThumbnail } from 'src/composables/usePdfThumbnail'
import axios from 'axios'
import PwaInstallBanner from 'src/components/PwaInstallBanner.vue'
import { clientPushApi } from 'src/services/api.js'

function _urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)))
}

async function _trySubscribeGuestPush(token) {
  try {
    if (!('Notification' in window) || !('serviceWorker' in navigator) || !('PushManager' in window)) return
    if (Notification.permission === 'denied') return
    // Не спрашивать повторно если уже подписан
    if (localStorage.getItem(`push_subscribed_${token}`)) return
    const permission = await Notification.requestPermission()
    if (permission !== 'granted') return
    const { data } = await clientPushApi.getVapidKey(token)
    if (!data.vapid_public_key) return
    const registration = await navigator.serviceWorker.ready
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: _urlBase64ToUint8Array(data.vapid_public_key),
    })
    await clientPushApi.subscribe(token, subscription.toJSON())
    localStorage.setItem(`push_subscribed_${token}`, '1')
  } catch (e) {
    console.warn('Guest push subscribe error:', e)
  }
}

const route = useRoute()
const router = useRouter()
const $q = useQuasar()
const mainToken = route.params.token  // UUID из URL /c/{token}
// Персональный токен гостя (создаётся при регистрации, сохраняется в localStorage)
const memberToken = localStorage.getItem(`chat_member_token_${mainToken}`) || null
const activeToken = memberToken || mainToken  // токен для API/WS

const { isConnected: wsConnected, connectClient, disconnect, sendMessage, sendTypingStart, sendTypingStop, sendRead, typingUsers, messages: wsMessages } = useChatWebSocket()

const chatTitle = ref('Чат с бюро')
const messages = ref([])
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
const inputText = ref('')
const pdfThumbnails = ref({})
const pdfImgWidths = reactive({})
function pdfBubbleStyle(msg) {
  if (!isPdf(msg) || !pdfThumbnails.value[msg.id]) return 'max-width: 80%'
  const w = pdfImgWidths[msg.id]
  return w ? `width: ${w}px; min-width: 0` : 'width: fit-content; max-width: min(85vw, 440px); min-width: 0'
}
const replyingTo = ref(null)
const loadingMessages = ref(false)
const hasMoreMessages = ref(false)
const loadingOlder = ref(false)
const messagesEl = ref(null)
const topSentinelEl = ref(null)
let _topObserver = null
// Галерея
const galleryOpen = ref(false)
const galleryIndex = ref(0)
const galleryImages = computed(() => messages.value.filter(m => m.message_type === 'image' && m.yandex_path && !m.is_deleted && !m._uploading))
const fileInput = ref(null)
const clientName = localStorage.getItem('client_name') || 'Клиент'
const chatPageH = ref('100dvh')
const uploadProgress = ref(0)
const editingClientMsgId = ref(null)
const editClientContent = ref('')
const savingClientEdit = ref(false)

// Emoji реакции (гостевые)
const QUICK_EMOJIS = ['👍', '👎', '❤️', '😂', '😮', '😢', '🔥', '🎉', '👏', '🤝', '👌', '🙏', '😍', '🤔', '✅']

// Голосовая запись
const isRecording = ref(false)
const recordSeconds = ref(0)
let _mediaRecorder = null
let _audioChunks = []
let _recordTimer = null
let _cancelRequested = false
let _pressStartTime = 0
let _holdTimer = null

// Ключ хранения последнего прочитанного сообщения в localStorage
const _lastReadKey = `chat_last_read_${activeToken}`
const firstUnreadId = ref(null)

/** Бейдж иконки PWA для клиента */
function _updateClientAppBadge(msgList, lastReadId) {
  if (!('setAppBadge' in navigator)) return
  const unread = msgList.filter(m => m.id > lastReadId && !m.sender_guest_token).length
  if (unread > 0) {
    navigator.setAppBadge(unread).catch(() => {})
  } else {
    navigator.clearAppBadge().catch(() => {})
  }
}

function recalcChatH() {
  const vh = window.visualViewport?.height ?? window.innerHeight
  const header = document.querySelector('.q-header')
  const footer = document.querySelector('.q-footer')
  const headerH = header?.offsetHeight ?? 0
  const footerH = footer?.offsetHeight ?? 0
  chatPageH.value = Math.max(300, vh - headerH - footerH) + 'px'
  scrollToBottom()
}

const typingText = computed(() => {
  if (!typingUsers.value.length) return ''
  const names = typingUsers.value.map(u => u.name)
  if (names.length === 1) return `${names[0]} печатает…`
  return `${names.join(', ')} печатают…`
})

function fmtDuration(sec) {
  const s = parseInt(sec) || 0
  const m = Math.floor(s / 60)
  return `${m}:${String(s % 60).padStart(2, '0')}`
}

const voicePlaying = reactive({})
const voiceCurrent = reactive({})
const _voiceRefs = {}

function toggleVoice(msg) {
  const audio = _voiceRefs[msg.id]
  if (!audio) return
  if (audio.paused) {
    Object.entries(_voiceRefs).forEach(([id, a]) => {
      if (id !== String(msg.id) && !a.paused) a.pause()
    })
    audio.play()
  } else {
    audio.pause()
  }
}

function voiceProgressPct(msg) {
  const dur = parseInt(msg.content) || 0
  if (!dur) return 0
  return Math.min(100, ((voiceCurrent[msg.id] || 0) / dur) * 100)
}

function isOwn(msg) {
  // Сравниваем по персональному токену (после регистрации) или основной ссылке
  if (memberToken) return msg.sender_guest_token === memberToken
  return msg.sender_guest_token === mainToken
}

function isForwarded(msg) {
  return typeof msg.sender_display_name === 'string' && msg.sender_display_name.includes('(переслано)')
}

function imgStreamUrl(msg) {
  if (msg._previewUrl) return msg._previewUrl
  if (!msg.yandex_path) return ''
  const path = msg.yandex_path.replace(/^disk:/, '')
  return `/api/v1/client-chat/${activeToken}/stream?yandex_path=${encodeURIComponent(path)}`
}

function isPdf(msg) {
  return msg.file_name?.toLowerCase().endsWith('.pdf')
}

async function loadPdfThumbnail(msg) {
  if (pdfThumbnails.value[msg.id]) return
  if (!isPdf(msg) || !msg.yandex_path) return
  const path = msg.yandex_path.replace(/^disk:/, '')
  try {
    const { data } = await axios.get(`/api/v1/client-chat/${activeToken}/stream`, {
      params: { yandex_path: path },
      responseType: 'arraybuffer',
    })
    const thumb = await getPdfThumbnail(data, String(msg.id))
    if (thumb) pdfThumbnails.value[msg.id] = thumb
  } catch { }
}

function formatTime(dt) {
  if (!dt) return ''
  let s = String(dt).replace(' ', 'T')
  s = s.replace(/([+-]\d{2}:\d{2})Z$/, '$1')
  const d = new Date(s)
  if (isNaN(d.getTime())) return ''
  const time = d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
  const now = new Date()
  const isToday = d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate()
  if (isToday) return time
  const day = String(d.getDate()).padStart(2, '0')
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const year = d.getFullYear()
  return `${day}.${month}.${year} ${time}`
}

function scrollToBottom() {
  nextTick(() => {
    requestAnimationFrame(() => {
      if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    })
  })
}

function scrollToMsg(id) {
  nextTick(() => {
    const el = document.getElementById(`msg-${id}`)
    if (!el || !messagesEl.value) return
    const container = messagesEl.value
    const containerRect = container.getBoundingClientRect()
    const elRect = el.getBoundingClientRect()
    container.scrollTop = container.scrollTop + (elRect.top - containerRect.top) - 60
    el.classList.add('msg-highlight')
    setTimeout(() => el.classList.remove('msg-highlight'), 1500)
  })
}

function scrollToFirstUnread() {
  nextTick(() => {
    requestAnimationFrame(() => {
      const container = messagesEl.value
      if (!container) return
      if (firstUnreadId.value) {
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
  })
}

async function loadMessages() {
  loadingMessages.value = true
  try {
    const baseURL = window.location.origin
    const { data } = await axios.get(`${baseURL}/api/v1/client-chat/${activeToken}`)
    if (data.requires_registration && !memberToken) {
      // Не зарегистрирован и нет сохранённого токена → на страницу регистрации
      router.replace({ name: 'client-register', params: { token: mainToken } })
      return
    }
    chatTitle.value = data.title || 'Чат с бюро'
    messages.value = data.messages || []
    hasMoreMessages.value = data.has_more_messages || false

    // Находим первое непрочитанное (localStorage-based, т.к. гость не имеет серверного трекинга)
    const lastRead = parseInt(localStorage.getItem(_lastReadKey) || '0', 10)
    const firstUnread = messages.value.find(m => m.id > lastRead && !m.sender_guest_token)
    firstUnreadId.value = firstUnread?.id || null
    // Показать бейдж иконки ДО сохранения прочитанного (чтоб увидеть счётчик)
    _updateClientAppBadge(messages.value, lastRead)
    scrollToFirstUnread()

    if (messages.value.length) {
      const lastId = messages.value[messages.value.length - 1].id
      sendRead(lastId)
      // Сохраняем последний id прочитанного для следующего визита → очищаем бейдж
      localStorage.setItem(_lastReadKey, String(lastId))
      if ('clearAppBadge' in navigator) navigator.clearAppBadge().catch(() => {})
    }
    messages.value
      .filter(m => isPdf(m) && m.yandex_path && !m._uploading)
      .forEach(m => loadPdfThumbnail(m))
    nextTick(() => setupTopObserver())
  } catch (e) {
    if (e.response?.status === 404) {
      $q.notify({ type: 'negative', message: 'Ссылка недействительна' })
    } else {
      console.error('[ClientChatPage]', e)
    }
  } finally {
    loadingMessages.value = false
  }
}

async function loadOlderMessages() {
  if (!hasMoreMessages.value || loadingOlder.value || !messages.value.length) return
  loadingOlder.value = true
  const firstId = messages.value[0].id
  const container = messagesEl.value
  const prevScrollHeight = container?.scrollHeight ?? 0
  try {
    const baseURL = window.location.origin
    const { data } = await axios.get(`${baseURL}/api/v1/client-chat/${activeToken}/messages`, {
      params: { limit: 150, before_id: firstId },
    })
    if (!data.length) { hasMoreMessages.value = false; return }
    if (data.length < 150) hasMoreMessages.value = false
    const existingIds = new Set(messages.value.map(m => m.id))
    const newMsgs = data.filter(m => !existingIds.has(m.id))
    messages.value = [...newMsgs, ...messages.value]
    newMsgs.filter(m => isPdf(m) && m.yandex_path && !m._uploading)
      .forEach(m => loadPdfThumbnail(m))
    await nextTick()
    if (container) container.scrollTop += container.scrollHeight - prevScrollHeight
  } catch (e) {
    console.error('[ClientChatPage] Ошибка загрузки старых:', e)
  } finally {
    loadingOlder.value = false
  }
}

function setupTopObserver() {
  if (_topObserver) _topObserver.disconnect()
  if (!topSentinelEl.value || !messagesEl.value) return
  _topObserver = new IntersectionObserver(
    (entries) => {
      if (entries[0].isIntersecting && hasMoreMessages.value && !loadingOlder.value) {
        loadOlderMessages()
      }
    },
    { root: messagesEl.value, threshold: 0 },
  )
  _topObserver.observe(topSentinelEl.value)
}

function openGallery(msg) {
  const idx = galleryImages.value.findIndex(m => m.id === msg.id)
  galleryIndex.value = idx >= 0 ? idx : 0
  galleryOpen.value = true
}

function galleryGridClass(count) {
  if (count <= 1) return 'media-grid-1'
  if (count === 2) return 'media-grid-2'
  if (count === 3) return 'media-grid-3'
  return 'media-grid-dynamic'
}

function galleryCols(count) {
  const minCols = Math.max(2, Math.ceil(count / 4))
  const maxCols = Math.min(4, count)
  let best = null
  for (let c = minCols; c <= maxCols; c++) {
    const r = count % c
    const priority = r === 0 ? 0 : r === 1 ? 2 : 1
    if (!best || priority < best.priority || (priority === best.priority && c > best.c)) {
      best = { c, priority }
    }
  }
  return best ? best.c : minCols
}

function galleryBubbleStyle(count) {
  if (count <= 3) return 'min-width: 0; width: min(50vw, 282px); max-width: min(50vw, 282px)'
  const thumbCount = count - 2
  const cols = thumbCount > 0 ? galleryCols(thumbCount) : 2
  const effectiveCols = Math.max(2, cols)
  const targetW = effectiveCols * 140 + (effectiveCols - 1) * 2
  return `min-width: 0; width: min(50vw, ${targetW}px); max-width: min(50vw, ${targetW}px)`
}

function galleryGridStyle(count) {
  if (count === 2) return 'display: grid; grid-template-columns: 1fr 1fr; gap: 2px;'
  if (count === 3) return 'display: grid; grid-template-columns: 2fr 1fr; gap: 2px;'
  return undefined
}

function galleryThumbGridStyle(count) {
  const thumbCount = count - 2
  if (thumbCount <= 0) return undefined
  const cols = galleryCols(thumbCount)
  return `display: grid; grid-template-columns: repeat(${cols}, 1fr); gap: 2px;`
}

function galleryItemSpanStyle(thumbCount, index) {
  if (thumbCount <= 0) return undefined
  const cols = galleryCols(thumbCount)
  const remainder = thumbCount % cols
  if (remainder === 0) return undefined
  if (index < thumbCount - remainder) return undefined
  const pos = index - (thumbCount - remainder)
  const baseSpan = Math.floor(cols / remainder)
  const extra = cols - baseSpan * remainder
  return { gridColumn: `span ${pos < extra ? baseSpan + 1 : baseSpan}` }
}

function galleryImgStyle(count, index) {
  const base = 'width: 100%; display: block;'
  if (count <= 1) return `${base} height: clamp(140px, 42vw, 340px);`
  if (count === 2) return `${base} height: 170px;`
  if (count === 3) return index === 0 ? `${base} height: 184px;` : `${base} height: 91px;`
  return base
}

function sendText() {
  const text = inputText.value.trim()
  if (!text) return
  sendMessage(text, replyingTo.value?.id || null)
  inputText.value = ''
  replyingTo.value = null
}

let typingTimer = null
function onTyping() {
  sendTypingStart()
  if (typingTimer) clearTimeout(typingTimer)
  typingTimer = setTimeout(() => sendTypingStop(), 2000)
}

function pickFile() {
  fileInput.value?.click()
}

function startClientEdit(msg) {
  editingClientMsgId.value = msg.id
  editClientContent.value = msg.content || ''
}

function cancelClientEdit() {
  editingClientMsgId.value = null
  editClientContent.value = ''
}

async function saveClientEdit() {
  const text = editClientContent.value.trim()
  if (!text || !editingClientMsgId.value) return
  savingClientEdit.value = true
  try {
    const baseURL = window.location.origin
    const { data } = await axios.patch(
      `${baseURL}/api/v1/client-chat/${activeToken}/messages/${editingClientMsgId.value}`,
      { content: text, message_type: 'text' },
    )
    const idx = messages.value.findIndex(m => m.id === editingClientMsgId.value)
    if (idx !== -1) messages.value.splice(idx, 1, data)
    cancelClientEdit()
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Ошибка редактирования' })
  } finally {
    savingClientEdit.value = false
  }
}

async function deleteClientMsg(msg) {
  try {
    const baseURL = window.location.origin
    await axios.delete(`${baseURL}/api/v1/client-chat/${activeToken}/messages/${msg.id}`)
    messages.value = messages.value.filter(m => m.id !== msg.id)
  } catch (e) {
    console.error('[ClientChat] Ошибка удаления:', e)
    // Локальное скрытие если сервер недоступен
    messages.value = messages.value.filter(m => m.id !== msg.id)
  }
}

async function _uploadClientFile(file) {
  const ext = file.name.split('.').pop()?.toLowerCase() || ''
  const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif']
  const msgType = imageExts.includes(ext) ? 'image' : 'file'
  const isPdfUpload = ext === 'pdf'
  const tempId = `temp_${Date.now()}_${Math.random()}`
  const previewUrl = msgType === 'image' ? URL.createObjectURL(file) : null
  messages.value.push({
    id: tempId,
    sender_guest_token: activeToken,
    sender_display_name: clientName || 'Вы',
    message_type: msgType,
    content: null,
    file_url: '',
    file_name: file.name,
    file_size: file.size,
    yandex_path: null,
    is_deleted: false,
    is_edited: false,
    created_at: new Date().toISOString(),
    _uploading: true,
    _previewUrl: previewUrl,
  })
  scrollToBottom()
  if (isPdfUpload) {
    getPdfThumbnail(file).then(thumb => {
      if (thumb) {
        const m = messages.value.find(m2 => m2.id === tempId)
        if (m) m._previewUrl = thumb
      }
    })
  }
  try {
    const baseURL = window.location.origin
    const formData = new FormData()
    formData.append('file', file)
    formData.append('message_type', msgType)
    const { data: savedMsg } = await axios.post(`${baseURL}/api/v1/client-chat/${activeToken}/files`, formData, {
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
  } finally {
    if (previewUrl) URL.revokeObjectURL(previewUrl)
  }
}

async function onFileSelected(event) {
  const files = [...(event.target.files || [])]
  if (!files.length) return
  uploadProgress.value = 1
  const errors = []
  for (const file of files) {
    try { await _uploadClientFile(file) } catch { errors.push(file.name) }
  }
  uploadProgress.value = 0
  event.target.value = ''
  if (errors.length) $q.notify({ type: 'negative', message: `Ошибка загрузки: ${errors.join(', ')}` })
}

onMounted(async () => {
  recalcChatH()
  window.addEventListener('resize', recalcChatH)
  window.visualViewport?.addEventListener('resize', recalcChatH)
  await loadMessages()
  if (memberToken) _trySubscribeGuestPush(activeToken)
  connectClient(activeToken, {
    onMessage: (msg) => {
      const exists = messages.value.some(m => m.id === msg.id)
      if (!exists) {
        messages.value.push(msg)
        scrollToBottom()
        if (isPdf(msg)) loadPdfThumbnail(msg)
        // Если новое сообщение от сотрудника — обновить бейдж иконки
        if (!msg.sender_guest_token && 'setAppBadge' in navigator) {
          const lastRead = parseInt(localStorage.getItem(_lastReadKey) || '0', 10)
          _updateClientAppBadge(messages.value, lastRead)
        }
      }
    },
    onReactionUpdated: (evt) => {
      const idx = messages.value.findIndex(m => m.id === evt.message_id)
      if (idx !== -1) {
        const c = messagesEl.value
        const atBottom = !c || (c.scrollHeight - c.scrollTop - c.clientHeight < 50)
        messages.value[idx] = { ...messages.value[idx], reactions: evt.reactions }
        if (atBottom) nextTick(() => requestAnimationFrame(() => { if (c) c.scrollTop = c.scrollHeight }))
      }
    },
  })
})

onUnmounted(() => {
  disconnect()
  if (_topObserver) _topObserver.disconnect()
  window.removeEventListener('resize', recalcChatH)
  window.visualViewport?.removeEventListener('resize', recalcChatH)
  if (typingTimer) clearTimeout(typingTimer)
  clearInterval(_recordTimer)
})

// ---- Emoji реакции (гость) ----

async function sendGuestReaction(msg, emoji) {
  try {
    const { data } = await axios.post(
      `/api/v1/client-chat/${activeToken}/messages/${msg.id}/react?emoji=${encodeURIComponent(emoji)}`,
    )
    const idx = messages.value.findIndex(m => m.id === msg.id)
    if (idx !== -1) messages.value[idx] = { ...messages.value[idx], reactions: data.reactions }
  } catch (e) {
    console.warn('[reaction]', e)
  }
}

function isOwnGuestReaction(msg, emoji) {
  const reactors = msg.reactions?.[emoji] || []
  return reactors.some(r => r.guest_token === activeToken)
}

// ---- Голосовая запись (гость) ----

function _getVoiceMimeType() {
  if (!window.MediaRecorder?.isTypeSupported) return ''
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4']
  return candidates.find(t => MediaRecorder.isTypeSupported(t)) || ''
}

async function _fixWebmDuration(blob, durationSec) {
  try {
    const buf = await blob.arrayBuffer()
    const u8 = new Uint8Array(buf)
    for (let i = 0; i < u8.length - 11; i++) {
      if (u8[i] === 0x44 && u8[i + 1] === 0x89 && u8[i + 2] === 0x88) {
        const view = new DataView(buf)
        view.setFloat64(i + 3, durationSec * 1000, false)
        return new Blob([buf], { type: blob.type })
      }
    }
  } catch {}
  return blob
}

function onVoiceBtnDown(e) {
  try { e?.currentTarget?.setPointerCapture(e.pointerId) } catch {}
  _pressStartTime = Date.now()
  _cancelRequested = false
  _holdTimer = setTimeout(() => {
    _holdTimer = null
    startRecording()
  }, 300)
}

function onVoiceBtnUp() {
  if (_holdTimer !== null) {
    clearTimeout(_holdTimer)
    _holdTimer = null
    return
  }
  if (!isRecording.value) {
    _cancelRequested = true
    return
  }
  stopRecording()
}

function onVoiceBtnCancel() {
  if (_holdTimer !== null) {
    clearTimeout(_holdTimer)
    _holdTimer = null
    return
  }
  if (isRecording.value) cancelRecording()
}

function cancelRecording() {
  clearInterval(_recordTimer)
  isRecording.value = false
  _audioChunks = []
  _cancelRequested = true
  if (_mediaRecorder && _mediaRecorder.state !== 'inactive') _mediaRecorder.stop()
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    if (_cancelRequested) {
      stream.getTracks().forEach(t => t.stop())
      return
    }
    _audioChunks = []
    const mimeType = _getVoiceMimeType()
    _mediaRecorder = new MediaRecorder(stream, ...(mimeType ? [{ mimeType }] : []))
    _mediaRecorder.ondataavailable = e => { if (e.data.size > 0) _audioChunks.push(e.data) }
    _mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      if (_cancelRequested) return
      const mt = _mediaRecorder.mimeType || mimeType || 'audio/webm'
      const rawBlob = new Blob(_audioChunks, { type: mt })
      if (rawBlob.size === 0) {
        $q.notify({ type: 'negative', message: 'Запись пуста — попробуйте ещё раз', timeout: 2000 })
        return
      }
      const blob = await _fixWebmDuration(rawBlob, recordSeconds.value)
      const ext = mt.includes('ogg') ? '.ogg' : mt.includes('mp4') ? '.m4a' : '.webm'
      const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
      const file = new File([blob], `voice_${ts}${ext}`, { type: mt })
      await _uploadGuestVoice(file)
    }
    _mediaRecorder.start()
    isRecording.value = true
    recordSeconds.value = 0
    _recordTimer = setInterval(() => { recordSeconds.value++ }, 1000)
  } catch {
    $q.notify({ type: 'negative', message: 'Нет доступа к микрофону', timeout: 2000 })
  }
}

function stopRecording() {
  clearInterval(_recordTimer)
  isRecording.value = false
  if (_mediaRecorder && _mediaRecorder.state !== 'inactive') _mediaRecorder.stop()
}

async function _uploadGuestVoice(file) {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('message_type', 'voice')
  fd.append('caption', String(recordSeconds.value))
  const dismiss = $q.notify({ group: false, spinner: true, message: 'Отправка голосового…', timeout: 0 })
  try {
    const { data } = await axios.post(`/api/v1/client-chat/${activeToken}/files`, fd)
    dismiss()
    const exists = messages.value.some(m => m.id === data.id)
    if (!exists) { messages.value.push(data); scrollToBottom() }
  } catch {
    dismiss()
    $q.notify({ type: 'negative', message: 'Ошибка загрузки голосового', timeout: 2000 })
  }
}
</script>

<style scoped>
.bubble-own {
  background: #E8F5E9;
  border-radius: 12px 12px 2px 12px;
  padding: 8px 12px;
}
.bubble-forwarded {
  background: #EEEEEE !important;
}
.bubble-staff {
  background: #fff;
  border-radius: 12px 12px 12px 2px;
  padding: 8px 12px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}
.bubble-img-own {
  background: #E8F5E9;
  border-radius: 12px 12px 2px 12px;
  overflow: hidden;
  min-width: 160px;
  max-width: 280px;
}
.bubble-img-staff {
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
.reply-quote {
  border-left: 3px solid #1565C0;
  background: rgba(21,101,192,0.07);
  border-radius: 4px;
  padding: 3px 8px;
  max-width: 100%;
  overflow: hidden;
}
@keyframes msg-highlight-pulse {
  0%   { background-color: rgba(255,214,0,0.45); }
  70%  { background-color: rgba(255,214,0,0.25); }
  100% { background-color: transparent; }
}
.msg-highlight {
  animation: msg-highlight-pulse 1.5s ease-out;
  border-radius: 8px;
}
.reaction-chip {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 7px;
  border-radius: 12px;
  border: 1px solid #E0E0E0;
  background: #F5F5F5;
  font-size: 13px;
  cursor: pointer;
  line-height: 1.4;
}
.reaction-chip--own {
  background: #E3F2FD;
  border-color: #90CAF9;
}
.react-quick-btn {
  font-size: 20px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 5px;
  border-radius: 6px;
  line-height: 1.3;
}
.react-quick-btn:hover { background: #F0F0F0; }
.react-quick-btn--active { background: #E3F2FD; }
.hidden { display: none; }
/* Медиа-галерея (Telegram-стиль) */
.media-grid-1 { display: block; }
.media-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-auto-rows: 170px;
  gap: 2px;
}
.media-grid-3 {
  display: grid;
  grid-template-columns: 2fr 1fr;
  grid-template-rows: 91px 91px;
  gap: 2px;
}
.media-grid-3 > a:first-child { grid-row: span 2; }
.media-grid-dynamic { overflow: hidden; }
</style>
