<template>
  <q-page
    class="column"
    :style="{ height: chatPageH, overflow: 'hidden', position: 'relative' }"
    @dragenter="onDragEnter"
    @dragleave="onDragLeave"
    @dragover="onDragOver"
    @drop="onDrop"
  >
    <!-- Drag & Drop оверлей -->
    <div
      v-if="isDraggingOver"
      class="absolute-full flex flex-center"
      style="background: rgba(25,118,210,0.13); border: 3px dashed #1976d2; border-radius: 8px; z-index: 9999; pointer-events: none"
    >
      <div class="text-center text-primary text-h6">
        <q-icon name="upload_file" size="48px" class="q-mb-sm" style="display: block; margin: 0 auto" />
        Отпустите файл для прикрепления
      </div>
    </div>
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
        <div
          v-else
          class="text-caption text-grey row no-wrap items-center"
          style="gap: 6px; cursor: pointer"
          @click="showMembers = true"
        >
          <span v-if="isConnected">
            <q-icon name="wifi" size="10px" color="positive" class="q-mr-xs" />онлайн
          </span>
          <span v-else>
            <q-icon name="wifi_off" size="10px" color="negative" class="q-mr-xs" />оффлайн
          </span>
          <span v-if="members.length" style="color: #aaa">•</span>
          <span v-if="members.length">
            <q-icon name="people" size="10px" class="q-mr-xs" />{{ members.length }}
          </span>
        </div>
      </div>

      <!-- Кнопка: доступ клиента -->
      <q-btn
        v-if="canManage"
        flat
        round
        dense
        icon="manage_accounts"
        @click="showInviteMenu = true; extraInviteLink = ''"
      >
        <q-tooltip>Доступ клиента</q-tooltip>
      </q-btn>

      <!-- Кнопка: отправить скрипт -->
      <q-btn
        v-if="canScript"
        flat
        round
        dense
        icon="text_snippet"
        @click="showScriptDialog = true"
      >
        <q-tooltip>Отправить скрипт</q-tooltip>
      </q-btn>

      <!-- Кнопка: поиск -->
      <q-btn
        flat
        round
        dense
        icon="search"
        @click="showSearch = !showSearch"
      >
        <q-tooltip>Поиск в чате</q-tooltip>
      </q-btn>

      <!-- Кнопка: участники -->
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

    <!-- Панель поиска -->
    <div
      v-if="showSearch"
      class="q-px-md q-py-xs bg-white"
      style="border-bottom: 1px solid #E0E0E0; flex-shrink: 0"
    >
      <q-input
        v-model="searchQuery"
        dense
        outlined
        clearable
        placeholder="Поиск в чате…"
        @update:model-value="doSearch"
        @clear="searchResults = []"
      >
        <template #prepend>
          <q-icon name="search" />
        </template>
      </q-input>
      <div v-if="searchLoading" class="text-center q-py-xs">
        <q-spinner size="20px" color="primary" />
      </div>
      <q-list v-else-if="searchResults.length" separator dense style="max-height: 200px; overflow-y: auto">
        <q-item
          v-for="r in searchResults"
          :key="r.id"
          v-ripple
          clickable
          dense
          @click="goToSearchResult(r)"
        >
          <q-item-section>
            <q-item-label class="text-caption text-weight-bold">
              {{ r.sender_display_name }}
            </q-item-label>
            <q-item-label caption lines="1">
              {{ r.content }}
            </q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-item-label caption>
              {{ new Date(r.created_at).toLocaleDateString('ru') }}
            </q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
      <div v-else-if="searchQuery?.length >= 2 && !searchLoading" class="text-caption text-grey q-py-xs q-px-sm">
        Ничего не найдено
      </div>
    </div>

    <!-- Закреплённые сообщения (до 10, Telegram-стиль) -->
    <div
      v-if="pinnedMsgs.length"
      class="row items-center q-px-md q-py-xs bg-white"
      style="border-bottom: 1px solid #E0E0E0; flex-shrink: 0; cursor: pointer; gap: 8px"
      @click="cyclePinned"
    >
      <div style="display: flex; flex-direction: column; gap: 2px; flex-shrink: 0; align-self: stretch; justify-content: center">
        <div
          v-for="(_, i) in pinnedMsgs"
          :key="i"
          :style="{
            width: '3px',
            height: `${Math.max(4, 28 / pinnedMsgs.length - 2)}px`,
            borderRadius: '2px',
            background: i === pinnedIdx ? '#E65100' : '#E0E0E0',
            transition: 'background 0.2s',
          }"
        />
      </div>
      <q-icon name="push_pin" size="14px" color="orange-8" style="flex-shrink: 0" />
      <div style="flex: 1; min-width: 0; overflow: hidden">
        <div class="text-caption text-weight-bold" style="color: #E65100; font-size: 10px">
          Закреплено{{ pinnedMsgs.length > 1 ? ` • ${pinnedIdx + 1} из ${pinnedMsgs.length}` : '' }}
        </div>
        <div class="text-caption ellipsis" style="font-size: 11px; color: #333">
          {{ pinnedMsgs[pinnedIdx]?.content || pinnedMsgs[pinnedIdx]?.file_name || 'Файл' }}
        </div>
      </div>
      <q-btn
        flat
        round
        dense
        size="xs"
        icon="close"
        color="grey-6"
        @click.stop="confirmUnpin(pinnedMsgs[pinnedIdx])"
      />
    </div>

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
        <div class="q-mt-sm">
          Нет сообщений
        </div>
      </div>

      <template v-else>
        <template v-for="item in renderedItems" :key="item.key">
          <!-- Галерея (несколько изображений одной отправкой) -->
          <template v-if="item.type === 'group'">
            <div
              :data-msg-id="item.msgs[0].id"
              class="q-mb-sm"
              :class="isOwn(item.msgs[0]) ? 'row justify-end' : 'row justify-start'"
            >
              <div
                :class="[isOwn(item.msgs[0]) ? 'bubble-img-own' : 'bubble-img-other', { 'bubble-forwarded': isForwarded(item.msgs[0]) }]"
                :style="galleryBubbleStyle(item.msgs.length)"
              >
                <div class="row no-wrap items-center justify-between" style="padding: 6px 10px 4px; min-height: 16px; gap: 2px">
                  <div
                    class="text-caption text-weight-bold"
                    :style="{ color: isOwn(item.msgs[0]) ? '#999' : (isGuest(item.msgs[0]) ? '#2E7D32' : '#1565C0') }"
                    style="flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap"
                  >
                    {{ item.msgs[0].sender_display_name }}
                    <q-chip
                      v-if="isGuest(item.msgs[0])"
                      dense
                      size="xs"
                      color="green-2"
                      text-color="green-9"
                    >
                      клиент
                    </q-chip>
                  </div>
                  <q-btn
                    flat
                    round
                    dense
                    size="xs"
                    icon="more_vert"
                    color="grey-6"
                    style="margin: -4px -6px -2px 2px; flex-shrink: 0"
                  >
                    <q-menu auto-close>
                      <q-list dense style="min-width: 210px; font-size: 12px; white-space: nowrap">
                        <q-item clickable dense @click="togglePin(item.msgs[0])">
                          <q-item-section avatar style="min-width: 28px">
                            <q-icon name="push_pin" size="14px" :color="item.msgs[0].is_pinned ? 'orange-8' : 'grey-8'" />
                          </q-item-section>
                          <q-item-section style="font-size: 12px">
                            {{ item.msgs[0].is_pinned ? 'Открепить' : 'Закрепить' }}
                          </q-item-section>
                        </q-item>
                        <q-separator />
                        <q-item clickable dense @click="openForwardDialog(item.msgs)">
                          <q-item-section avatar style="min-width: 28px">
                            <q-icon name="forward" size="14px" color="grey-8" />
                          </q-item-section>
                          <q-item-section style="font-size: 12px">
                            Переслать
                          </q-item-section>
                        </q-item>
                        <q-item
                          v-if="item.msgs.some(m => m.yandex_path)"
                          clickable
                          dense
                          @click="openInGallery(item.msgs.find(m => m.yandex_path))"
                        >
                          <q-item-section avatar style="min-width: 28px">
                            <q-icon name="photo_library" size="14px" color="grey-8" />
                          </q-item-section>
                          <q-item-section style="font-size: 12px">
                            Открыть в галерее
                          </q-item-section>
                        </q-item>
                        <q-item v-if="isOwn(item.msgs[0])" clickable dense @click="deleteMsg(item.msgs[0])">
                          <q-item-section avatar style="min-width: 28px">
                            <q-icon name="delete_outline" size="14px" color="grey-8" />
                          </q-item-section>
                          <q-item-section class="text-red-7" style="font-size: 12px">
                            Удалить
                          </q-item-section>
                        </q-item>
                      </q-list>
                    </q-menu>
                  </q-btn>
                </div>
                <template v-if="item.msgs.length < 4">
                  <div :class="galleryGridClass(item.msgs.length)" :style="galleryGridStyle(item.msgs.length)">
                    <div
                      v-for="(gm, gi) in item.msgs"
                      :key="gm.id"
                      style="display: block; overflow: hidden; cursor: pointer"
                      @click="openImgGallery(item.msgs, gi)"
                    >
                      <q-img
                        v-if="imgStreamUrl(gm)"
                        :src="imgStreamUrl(gm)"
                        :style="galleryImgStyle(item.msgs.length, gi)"
                        fit="cover"
                        spinner-color="grey-4"
                        spinner-size="20px"
                      />
                    </div>
                  </div>
                </template>
                <template v-else>
                  <div style="display: flex; flex-direction: column; gap: 2px">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2px">
                      <div
                        v-for="(gm, gi) in item.msgs.slice(0, 2)"
                        :key="gm.id"
                        style="display: block; overflow: hidden; cursor: pointer"
                        @click="openImgGallery(item.msgs, gi)"
                      >
                        <q-img
                          v-if="imgStreamUrl(gm)"
                          :src="imgStreamUrl(gm)"
                          style="width: 100%; display: block; height: 180px"
                          fit="cover"
                          spinner-color="grey-4"
                          spinner-size="20px"
                        />
                      </div>
                    </div>
                    <div v-if="item.msgs.length > 2" :style="galleryThumbGridStyle(item.msgs.length)">
                      <div
                        v-for="(gm, gi) in item.msgs.slice(2)"
                        :key="gm.id"
                        :style="galleryItemSpanStyle(item.msgs.length - 2, gi)"
                        style="display: block; overflow: hidden; cursor: pointer"
                        @click="openImgGallery(item.msgs, gi + 2)"
                      >
                        <q-img
                          v-if="imgStreamUrl(gm)"
                          :src="imgStreamUrl(gm)"
                          style="width: 100%; display: block; height: 90px"
                          fit="cover"
                          spinner-color="grey-4"
                          spinner-size="20px"
                        />
                      </div>
                    </div>
                  </div>
                </template>
                <div class="row no-wrap items-center justify-between" style="padding: 2px 8px 4px; color: #888; font-size: 10px">
                  <q-btn
                    v-if="item.msgs.some(m => m.yandex_path)"
                    flat
                    dense
                    no-caps
                    unelevated
                    size="xs"
                    icon="photo_library"
                    label="Открыть в галерее"
                    color="grey-6"
                    class="gallery-open-btn"
                    style="font-size: 10px; padding: 0 4px"
                    @click.stop="openInGallery(item.msgs.find(m => m.yandex_path))"
                  />
                  <span v-else />
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
                <!-- Системные -->
                <div v-if="msg.message_type === 'system'" class="text-center full-width">
                  <q-chip dense size="sm" color="grey-3" text-color="grey-7">
                    {{ msg.content }}
                  </q-chip>
                </div>

                <div
                  v-else
                  :class="[(msg.message_type === 'image' || (isPdf(msg) && pdfThumbnails[msg.id]))
                    ? (isOwn(msg) ? 'bubble-img-own' : 'bubble-img-other')
                    : (isOwn(msg) ? 'bubble-own' : 'bubble-other'), { 'bubble-forwarded': isForwarded(msg) }]"
                  :style="pdfBubbleStyle(msg)"
                >
                  <!-- Верхняя строка: имя + меню -->
                  <div
                    class="row no-wrap items-center justify-between q-mb-xs"
                    :style="(msg.message_type === 'image' || (isPdf(msg) && pdfThumbnails[msg.id])) ? 'min-height:16px;gap:2px;padding:6px 10px 4px' : 'min-height:16px;gap:2px'"
                  >
                    <div
                      class="text-caption text-weight-bold"
                      :style="{ color: isOwn(msg) ? '#999' : (isGuest(msg) ? '#2E7D32' : '#1565C0') }"
                      style="flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: default"
                    >
                      {{ msg.sender_display_name }}
                      <q-chip
                        v-if="isGuest(msg)"
                        dense
                        size="xs"
                        color="green-2"
                        text-color="green-9"
                      >
                        клиент
                      </q-chip>
                      <!-- Телефон клиента (только при наличии прав) -->
                      <q-tooltip
                        v-if="isGuest(msg) && canShowPhone && guestPhone(msg)"
                        anchor="top middle"
                        self="bottom middle"
                      >
                        <q-icon name="phone" size="12px" class="q-mr-xs" />{{ guestPhone(msg) }}
                      </q-tooltip>
                    </div>
                    <!-- 3-точечное меню для ВСЕХ сообщений (не только своих) -->
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
                        <q-list dense style="min-width: 210px; font-size: 12px; white-space: nowrap">
                          <!-- Быстрые реакции -->
                          <q-item dense style="padding: 4px 8px 2px">
                            <div class="row items-center">
                              <button
                                v-for="em in QUICK_EMOJIS"
                                :key="em"
                                class="react-quick-btn"
                                :class="{ 'react-quick-btn--active': isOwnReaction(msg, em) }"
                                @click.stop="sendReaction(msg, em)"
                              >
                                {{ em }}
                              </button>
                            </div>
                          </q-item>
                          <q-separator />
                          <q-item clickable dense @click="togglePin(msg)">
                            <q-item-section avatar style="min-width: 28px">
                              <q-icon name="push_pin" size="14px" :color="msg.is_pinned ? 'orange-8' : 'grey-8'" />
                            </q-item-section>
                            <q-item-section style="font-size: 12px">
                              {{ msg.is_pinned ? 'Открепить' : 'Закрепить' }}
                            </q-item-section>
                          </q-item>
                          <q-item clickable dense @click="replyingTo = msg">
                            <q-item-section avatar style="min-width: 28px">
                              <q-icon name="reply" size="14px" color="grey-8" />
                            </q-item-section>
                            <q-item-section style="font-size: 12px">
                              Ответить
                            </q-item-section>
                          </q-item>
                          <q-separator />
                          <q-item v-if="isOwn(msg) && msg.message_type === 'text'" clickable dense @click="startEdit(msg)">
                            <q-item-section avatar style="min-width: 28px">
                              <q-icon name="edit" size="14px" color="grey-8" />
                            </q-item-section>
                            <q-item-section style="font-size: 12px">
                              Редактировать
                            </q-item-section>
                          </q-item>
                          <q-item clickable dense @click="openForwardDialog(msg)">
                            <q-item-section avatar style="min-width: 28px">
                              <q-icon name="forward" size="14px" color="grey-8" />
                            </q-item-section>
                            <q-item-section style="font-size: 12px">
                              Переслать
                            </q-item-section>
                          </q-item>
                          <q-item v-if="msg.yandex_path && chatCrmCardId" clickable dense @click="openCopyToCard(msg)">
                            <q-item-section avatar style="min-width: 28px">
                              <q-icon name="drive_file_move" size="14px" color="grey-8" />
                            </q-item-section>
                            <q-item-section style="font-size: 12px">
                              Скопировать в карточку
                            </q-item-section>
                          </q-item>
                          <q-separator v-if="isOwn(msg)" />
                          <q-item v-if="isOwn(msg)" clickable dense @click="deleteMsg(msg)">
                            <q-item-section avatar style="min-width: 28px">
                              <q-icon name="delete_outline" size="14px" color="grey-8" />
                            </q-item-section>
                            <q-item-section class="text-red-7" style="font-size: 12px">
                              Удалить
                            </q-item-section>
                          </q-item>
                        </q-list>
                      </q-menu>
                    </q-btn>
                  </div>

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
                  <template v-else>
                    <!-- Цитата (ответ на сообщение) -->
                    <div
                      v-if="msg.reply_preview"
                      class="reply-quote q-mb-xs"
                      style="border-left: 3px solid #1565C0; background: rgba(21,101,192,0.07); border-radius: 4px; padding: 4px 8px; cursor: pointer"
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
                        <div style="min-width: 0; overflow: hidden">
                          <div class="text-caption text-weight-bold" style="color: #1565C0; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">
                            {{ msg.reply_preview.sender_display_name }}
                          </div>
                          <div class="text-caption text-grey-7" style="font-size: 11px; word-break: break-word; overflow-wrap: anywhere; white-space: pre-wrap">
                            {{ msg.reply_preview.message_type === 'image' ? '[Изображение]' : msg.reply_preview.message_type === 'file' ? '[Файл]' : msg.reply_preview.content }}
                          </div>
                        </div>
                      </div>
                    </div>

                    <template v-if="msg.message_type === 'image'">
                      <div style="display: block; cursor: pointer; color: inherit" @click="openImgGallery([msg], 0)">
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
                      <div class="text-body2" style="white-space: pre-wrap; word-break: break-word; font-size: 13px">
                        {{ msg.content }}
                      </div>
                    </template>
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

                  <div
                    class="row no-wrap items-center"
                    :class="isOwn(msg) ? 'justify-end' : 'justify-start'"
                    :style="(msg.message_type === 'image' || (isPdf(msg) && pdfThumbnails[msg.id])) ? 'padding:2px 10px 6px;color:#888;font-size:10px' : 'margin-top:4px;color:#888;font-size:10px'"
                  >
                    <span v-if="msg.is_edited" class="text-caption text-grey-5 q-mr-xs" style="font-size: 9px">изм.</span>
                    <span class="text-caption">{{ formatTime(msg.created_at) }}</span>
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
                      :class="{ 'reaction-chip--own': isOwnReaction(msg, emoji) }"
                      @click="sendReaction(msg, emoji)"
                    >
                      {{ emoji }} {{ reactors.length }}
                    </button>
                  </div>
                </div>
              </div>
            </template><!-- /single msg loop -->
          </template><!-- /single -->
        </template><!-- /renderedItems loop -->
      </template>
    </div>

    <!-- Прогресс загрузки файла -->
    <q-linear-progress
      v-if="uploadProgress > 0 && uploadProgress < 100"
      :value="uploadProgress / 100"
      color="green-6"
      style="flex-shrink: 0"
    />

    <!-- Превью прикреплённых файлов -->
    <div
      v-if="pendingFiles.length"
      class="q-px-sm q-pt-xs q-pb-xs bg-blue-1"
      style="border-top: 1px solid #BBDEFB; flex-shrink: 0"
    >
      <div class="row items-center q-gutter-xs">
        <div
          v-for="(f, i) in pendingFiles"
          :key="i"
          class="relative-position"
        >
          <template v-if="isImageFile(f) && pendingPreviews[i]">
            <img
              :src="pendingPreviews[i]"
              style="width: 52px; height: 52px; object-fit: cover; border-radius: 6px; display: block"
            >
            <button
              type="button"
              style="position:absolute;top:-5px;right:-5px;width:20px;height:20px;border-radius:50%;background:rgba(0,0,0,0.75);border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0"
              @click.stop="removePendingFile(i)"
            >
              <q-icon name="close" size="10px" color="white" />
            </button>
          </template>
          <q-chip
            v-else
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
    </div>

    <!-- Reply-бар: ответ на сообщение -->
    <div
      v-if="replyingTo"
      class="row no-wrap items-center q-px-md q-py-xs"
      style="background: #F3F6FF; border-top: 1px solid #D0D9F0; flex-shrink: 0; gap: 8px"
    >
      <q-icon name="reply" size="16px" color="blue-7" />
      <div style="flex: 1; min-width: 0">
        <div class="text-caption text-weight-bold" style="color: #1565C0; font-size: 11px">
          {{ replyingTo.sender_display_name }}
        </div>
        <div class="text-caption text-grey-7 ellipsis" style="font-size: 11px">
          {{ replyingTo.content || '[Медиафайл]' }}
        </div>
      </div>
      <q-btn
        flat
        round
        dense
        icon="close"
        size="xs"
        color="grey-6"
        @click="replyingTo = null"
      />
    </div>

    <!-- Панель ввода -->
    <div class="q-pa-sm bg-white" style="border-top: 1px solid #E0E0E0; flex-shrink: 0">
      <div class="row no-wrap items-end q-gutter-xs">
        <q-btn
          round
          dense
          icon="attach_file"
          color="grey-6"
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
        <!-- Файлы из карточки CRM (не для замерщика) -->
        <q-btn
          v-if="chatCrmCardId && COPY_DESTINATIONS.length > 0"
          round
          dense
          icon="folder_open"
          color="grey-6"
          @click="showCardFilesDialog = true; loadCardFiles()"
        >
          <q-tooltip>Файлы из карточки CRM</q-tooltip>
        </q-btn>
        <!-- Запись голоса: удерживать для записи (скрыта при pending файлах) -->
        <q-btn
          v-if="!pendingFiles.length && !inputText.trim()"
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
          v-if="pendingFiles.length && !isRecording"
          v-model="pendingCaption"
          outlined
          dense
          autogrow
          hide-bottom-space
          placeholder="Подпись к файлу…"
          style="flex: 1"
          @keydown.enter.exact.prevent="sendWithAttachment"
          @input="onTyping"
          @paste="onPaste"
        />
        <q-input
          v-else-if="!isRecording"
          v-model="inputText"
          outlined
          dense
          autogrow
          hide-bottom-space
          placeholder="Сообщение…"
          style="flex: 1"
          @keydown.enter.exact.prevent="sendText"
          @input="onTyping"
          @paste="onPaste"
        />
        <q-btn
          v-if="!isRecording"
          round
          dense
          icon="send"
          color="green"
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

    <!-- Диалог скрипта -->
    <q-dialog v-model="showScriptDialog" @show="loadScripts">
      <q-card style="min-width: 380px; max-width: 520px">
        <q-card-section class="row items-center">
          <div class="text-h6">
            Отправить скрипт
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
        <q-separator />

        <!-- Выбор скрипта -->
        <q-card-section v-if="!selectedScript" class="q-pb-sm">
          <div v-if="loadingScripts" class="text-center q-pa-md">
            <q-spinner size="24px" color="primary" />
          </div>
          <q-list v-else separator>
            <q-item
              v-for="s in scripts"
              :key="s.id"
              v-ripple
              clickable
              @click="selectScript(s)"
            >
              <q-item-section>
                <q-item-label>{{ s.name || s.script_type }}</q-item-label>
                <q-item-label caption lines="2">
                  {{ s.message_template?.substring(0, 80) }}…
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-icon name="chevron_right" color="grey" />
              </q-item-section>
            </q-item>
            <q-item v-if="!scripts.length">
              <q-item-section>
                <q-item-label class="text-grey">
                  Скрипты не найдены
                </q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>

        <!-- Редактирование и отправка выбранного скрипта -->
        <q-card-section v-else class="q-pt-sm">
          <div class="text-caption text-grey q-mb-sm">
            {{ selectedScript.name || selectedScript.script_type }}
          </div>
          <q-input
            v-model="scriptText"
            type="textarea"
            outlined
            label="Текст (можно отредактировать)"
            rows="6"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn
            v-if="selectedScript"
            flat
            label="Назад"
            @click="selectedScript = null"
          />
          <q-btn v-close-popup flat label="Отмена" />
          <q-btn
            v-if="selectedScript"
            color="primary"
            label="Отправить"
            :disable="!scriptText.trim()"
            @click="sendScript"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог: Доступ клиента -->
    <q-dialog v-model="showInviteMenu">
      <q-card style="min-width: 340px; max-width: 460px; width: 100%">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">
            Доступ клиента
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

        <!-- Секция: Отправить приглашение на email -->
        <q-card-section>
          <div class="text-subtitle2 q-mb-xs">
            <q-icon name="email" size="16px" class="q-mr-xs" />
            Пригласить клиента
          </div>
          <div class="text-caption text-grey-7 q-mb-sm">
            Клиент получит письмо с инструкцией и ссылкой на чат проекта
          </div>
          <q-btn
            v-if="chatCrmCardId"
            color="primary"
            icon="send"
            label="Отправить приглашение на email"
            :loading="sendingInvite"
            unelevated
            class="full-width"
            @click="sendEmailInvite"
          />
          <div v-else class="text-caption text-orange-8 q-pa-sm bg-orange-1 rounded-borders">
            <q-icon name="warning" size="14px" class="q-mr-xs" />
            Чат не привязан к CRM-карточке — отправка невозможна
          </div>
        </q-card-section>

        <q-separator />

        <!-- Секция: Основная ссылка -->
        <q-card-section v-if="clientLink">
          <div class="text-subtitle2 q-mb-xs">
            <q-icon name="link" size="16px" class="q-mr-xs" />
            Основная ссылка
          </div>
          <div class="text-caption text-grey-7 q-mb-sm">
            Та же ссылка, что и в email-приглашении
          </div>
          <q-input :model-value="clientLink" readonly outlined dense>
            <template #append>
              <q-btn flat dense icon="content_copy" @click="copyText(clientLink)">
                <q-tooltip>Скопировать</q-tooltip>
              </q-btn>
            </template>
          </q-input>
        </q-card-section>

        <q-separator />

        <!-- Секция: Ссылки для представителей -->
        <q-card-section>
          <div class="text-subtitle2 q-mb-xs">
            <q-icon name="group_add" size="16px" class="q-mr-xs" />
            Ссылки для представителей
          </div>
          <div class="text-caption text-grey-7 q-mb-sm">
            Для жены, прораба или других участников проекта
          </div>
          <q-input
            v-if="extraInviteLink"
            :model-value="extraInviteLink"
            readonly
            outlined
            dense
            class="q-mb-sm"
          >
            <template #append>
              <q-btn flat dense icon="content_copy" @click="copyText(extraInviteLink)">
                <q-tooltip>Скопировать</q-tooltip>
              </q-btn>
            </template>
          </q-input>
          <q-btn
            outline
            color="primary"
            icon="add_link"
            label="Создать новую ссылку"
            class="full-width"
            @click="createExtraLink"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Закрыть" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог участников -->
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
              <div style="position: relative; display: inline-block">
                <q-avatar
                  :color="m.member_type === 'employee' ? 'blue-2' : 'green-2'"
                  :text-color="m.member_type === 'employee' ? 'blue-9' : 'green-9'"
                  size="28px"
                  style="overflow:hidden"
                >
                  <img v-if="m.photo_url" :src="m.photo_url" style="width:100%;height:100%;object-fit:cover;border-radius:50%">
                  <q-icon v-else name="person" />
                </q-avatar>
                <span
                  v-if="m.is_online !== null && m.is_online !== undefined"
                  :style="{
                    position: 'absolute', bottom: '0', right: '0',
                    width: '9px', height: '9px', borderRadius: '50%',
                    background: m.is_online ? '#4CAF50' : '#9E9E9E',
                    border: '1.5px solid #fff',
                  }"
                />
              </div>
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ m.display_name || m.guest_name || `#${m.id}` }}</q-item-label>
              <q-item-label caption>
                {{ m.role_in_project || (m.member_type === 'employee' ? 'Сотрудник' : 'Клиент') }}
              </q-item-label>
              <q-item-label
                v-if="canShowPhone && m.member_type === 'client_guest' && m.guest_phone"
                caption
                style="font-size: 11px; color: #388E3C"
              >
                <q-icon name="phone" size="11px" class="q-mr-xs" />{{ m.guest_phone }}
              </q-item-label>
              <q-item-label
                v-if="canShowLastLogin && (m.member_type === 'employee' || m.last_login)"
                caption
                style="font-size: 10px; color: #aaa"
              >
                {{ m.is_online ? 'В сети' : (m.last_login ? `Был(а): ${fmtLastLogin(m.last_login)}` : 'Не входил(а)') }}
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

    <!-- Диалог: скопировать в карточку -->
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

    <!-- Диалог: файлы из карточки CRM -->
    <q-dialog v-model="showCardFilesDialog" persistent>
      <q-card style="min-width: 320px; max-width: 96vw; width: 480px; max-height: 85vh; display: flex; flex-direction: column">
        <q-card-section class="row items-center q-pb-none" style="flex-shrink: 0">
          <div class="text-subtitle1 text-weight-medium">
            Файлы из карточки CRM
          </div>
          <q-space />
          <q-btn
            v-close-popup
            icon="close"
            flat
            round
            dense
          />
        </q-card-section>

        <q-card-section style="overflow-y: auto; flex: 1; padding: 8px 0">
          <div v-if="cardFilesLoading" class="flex flex-center q-pa-md">
            <q-spinner size="28px" color="grey" />
          </div>
          <div v-else-if="!cardFiles.length" class="text-grey-6 text-caption q-pa-sm q-px-md">
            Файлы не найдены
          </div>
          <template v-else>
            <template v-for="item in cardFileItems" :key="item.key">
              <!-- Заголовок стадии -->
              <div
                v-if="item.type === 'stage'"
                class="q-px-md q-py-xs text-weight-bold"
                style="background: #E8EEF6; color: #1a3a6b; font-size: 11px; letter-spacing: 0.3px"
              >
                {{ item.label }}
              </div>
              <!-- Подзаголовок вариации -->
              <div
                v-else-if="item.type === 'var'"
                class="q-px-lg q-py-xs"
                style="background: #F3F3F3; color: #666; font-style: italic; font-size: 10px"
              >
                Вариант {{ item.varNum }}
              </div>
              <!-- Файл -->
              <q-item
                v-else-if="item.type === 'file'"
                clickable
                :disable="sendingCardFile"
                style="min-height: 52px"
                :style="isCardFileSelected(item.file) ? 'background: #EBF2FF' : ''"
                @click="toggleCardFileSelection(item.file)"
              >
                <!-- Чекбокс -->
                <q-item-section side style="min-width: 36px; padding-right: 0">
                  <q-checkbox
                    dense
                    color="blue-6"
                    :model-value="isCardFileSelected(item.file)"
                    @click.stop
                    @update:model-value="toggleCardFileSelection(item.file)"
                  />
                </q-item-section>
                <!-- Превью -->
                <q-item-section avatar style="min-width: 64px; padding-left: 4px">
                  <q-img
                    v-if="cfIsPreviewImg(item.file) && item.file.yandex_path"
                    :src="cfImgStreamUrl(item.file)"
                    fit="cover"
                    style="width: 56px; height: 42px; border-radius: 4px; flex-shrink: 0"
                    spinner-color="grey-4"
                  >
                    <template #error>
                      <div :style="cfBadgeStyle(item.file)">
                        {{ cfBadgeText(item.file) }}
                      </div>
                    </template>
                  </q-img>
                  <img
                    v-else-if="cfIsPdf(item.file) && cfPdfThumbs[String(item.file.id)]"
                    :src="cfPdfThumbs[String(item.file.id)]"
                    style="width: 56px; height: 42px; border-radius: 4px; object-fit: cover; flex-shrink: 0"
                  >
                  <div v-else :style="cfBadgeStyle(item.file)">
                    {{ cfBadgeText(item.file) }}
                  </div>
                </q-item-section>
                <!-- Имя файла -->
                <q-item-section style="overflow: hidden; min-width: 0">
                  <q-item-label
                    style="font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap"
                    :title="item.fname"
                  >
                    {{ cfTrunc(item.fname) }}
                  </q-item-label>
                </q-item-section>
              </q-item>
            </template>
          </template>
        </q-card-section>

        <q-card-actions style="flex-shrink: 0; border-top: 1px solid #eee; justify-content: space-between; padding: 8px 12px">
          <q-btn
            v-close-popup
            flat
            no-caps
            label="Закрыть"
            color="grey-7"
          />
          <q-btn
            v-if="selectedCardFiles.length"
            unelevated
            no-caps
            color="blue-6"
            :label="`Отправить (${selectedCardFiles.length})`"
            :loading="sendingCardFile"
            :disable="sendingCardFile"
            @click="sendSelectedCardFiles()"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <ImageGalleryDialog
      v-model="galleryVisible"
      :images="galleryImages"
      :start-index="galleryStartIndex"
    />
  </q-page>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, onBeforeRouteUpdate } from 'vue-router'
import { api } from 'src/boot/axios'
import { crmApi } from 'src/services/api'
import { useChatWebSocket } from 'src/composables/useChatWebSocket'
import { getPdfThumbnail } from 'src/composables/usePdfThumbnail'
import { usePermission } from 'src/composables/usePermission'
import { useAuthStore } from 'src/stores/auth'
import { useChatUnreadStore } from 'src/stores/chatUnread'
import { useQuasar } from 'quasar'
import ImageGalleryDialog from 'src/components/ImageGalleryDialog.vue'

const route = useRoute()
const authStore = useAuthStore()
const chatUnreadStore = useChatUnreadStore()
const { can } = usePermission()
const $q = useQuasar()
let chatId = Number(route.params.chatId)

const { isConnected, connectEmployee, disconnect, sendMessage, sendTypingStart, sendTypingStop, sendRead, typingUsers } = useChatWebSocket()

const chatTitle = ref('Чат с клиентом')
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
const members = ref([])
const inputText = ref('')
const loadingMessages = ref(false)
const hasMoreMessages = ref(false)
const loadingOlder = ref(false)
const messagesEl = ref(null)
let _scrollBottomTimer = null
const topSentinelEl = ref(null)
let _topObserver = null
const fileInput = ref(null)
const pendingFiles = ref([])
const pendingPreviews = ref([])
const pendingCaption = ref('')
const clientToken = ref('')
const showScriptDialog = ref(false)
const showInviteMenu = ref(false)
const sendingInvite = ref(false)
const extraInviteLink = ref('')
const showMembers = ref(false)
const showSearch = ref(false)
const searchQuery = ref('')
const searchResults = ref([])
const searchLoading = ref(false)
const scriptText = ref('')
const chatPageH = ref('100dvh')
const uploadProgress = ref(0)
const availableEmployees = ref(null)
const loadingAvailableEmps = ref(false)
const addingMemberId = ref(null)
const removingMemberId = ref(null)
const chatCrmCardId = ref(null)
const editingMsgId = ref(null)
const editContent = ref('')
const savingEdit = ref(false)
// Пересылка сообщений
const showForwardDialog = ref(false)
const replyingTo = ref(null)

const forwardingMsgs = ref([])
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

// Первое непрочитанное сообщение
const firstUnreadId = ref(null)
// Закреплённые сообщения (до 10, как в Telegram)
const pinnedMsgs = ref([])
const pinnedIdx = ref(0)
const pdfThumbnails = ref({})
const pdfImgWidths = reactive({})
function pdfBubbleStyle(msg) {
  if (!isPdf(msg) || !pdfThumbnails.value[msg.id]) return 'min-width: 0'
  const w = pdfImgWidths[msg.id]
  return w ? `width: ${w}px; min-width: 0` : 'width: fit-content; max-width: min(85vw, 440px); min-width: 0'
}
const chatYdFolder = ref(null)

// Emoji реакции
const QUICK_EMOJIS = ['👍', '❤️', '😂', '😮', '😢', '🔥']

// Голосовая запись
const isRecording = ref(false)
const recordSeconds = ref(0)
let _mediaRecorder = null
let _audioChunks = []
let _cancelRequested = false
let _pressStartTime = 0
let _holdTimer = null
let _recordTimer = null

// Копирование в карточку
const showCopyToCard = ref(false)
const copyToCardMsg = ref(null)
const selectedDestination = ref(null)
const copyingToCard = ref(false)
const copyStep = ref(1)
const stageVariations = ref([])
const nextVariation = ref(1)
const selectedVariation = ref(null)
const loadingVariations = ref(false)

const STAGE_KEYS = new Set(['stage_1', 'stage_2', 'stage_3'])

const _ALL_COPY_DESTINATIONS = [
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
const _EXECUTOR_ONLY_GROUPS = ['Общие данные', 'Стадии']
const COPY_DESTINATIONS = computed(() => {
  const pos = authStore.user?.position || ''
  const secPos = authStore.user?.secondary_position || ''
  const isMeasurer = pos === 'Замерщик' || secPos === 'Замерщик'
  const isExecutorOnly = ['Дизайнер', 'Чертёжник'].some(p => pos === p || secPos === p)
  if (isMeasurer) return []
  if (isExecutorOnly) return _ALL_COPY_DESTINATIONS.filter(g => _EXECUTOR_ONLY_GROUPS.includes(g.group))
  return _ALL_COPY_DESTINATIONS
})

function recalcChatH() {
  const vh = window.visualViewport?.height ?? window.innerHeight
  const header = document.querySelector('.q-header')
  const footer = document.querySelector('.q-footer')
  const headerH = header?.offsetHeight ?? 0
  const footerH = footer?.offsetHeight ?? 0
  chatPageH.value = Math.max(300, vh - headerH - footerH) + 'px'
  scrollToBottom()
}

const canManage = computed(() => can('chat.client.manage'))
const canScript = computed(() => can('chat.client.send_script'))
const canShowPhone = computed(() => can('chat.client.show_phone'))
const canShowLastLogin = computed(() => can('chat.members.show_last_login'))

function fmtLastLogin(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getDate()}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// Карта guest_name → phone из списка участников (token не передаётся в ответе API)
const guestPhoneMap = computed(() => {
  const map = {}
  for (const m of members.value) {
    if (!m.employee_id && m.guest_phone && m.guest_name) {
      map[m.guest_name] = m.guest_phone
    }
  }
  return map
})

function guestPhone(msg) {
  if (!isGuest(msg) || !msg.sender_display_name) return ''
  return guestPhoneMap.value[msg.sender_display_name] || ''
}
const membersCount = computed(() => members.value.length)

const scripts = ref([])
const loadingScripts = ref(false)
const selectedScript = ref(null)
const cardData = ref(null)

const clientLink = computed(() => {
  if (!clientToken.value) return ''
  return `${window.location.origin}/c/${clientToken.value}`
})

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
  const myId = authStore.user?.id
  if (!myId) return false
  return Number(msg.sender_employee_id) === Number(myId)
}

function isForwarded(msg) {
  return typeof msg.sender_display_name === 'string' && msg.sender_display_name.includes('(переслано)')
}

function startEdit(msg) {
  editingMsgId.value = msg.id
  editContent.value = msg.content
}

function cancelEdit() {
  editingMsgId.value = null
  editContent.value = ''
}

async function saveEdit() {
  if (!editContent.value.trim() || !editingMsgId.value) return
  savingEdit.value = true
  try {
    await api.patch(`/api/v1/chats/${chatId}/messages/${editingMsgId.value}`, { content: editContent.value.trim() })
    const msg = messages.value.find(m => m.id === editingMsgId.value)
    if (msg) {
      msg.content = editContent.value.trim()
      msg.is_edited = true
    }
    cancelEdit()
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка редактирования' })
  } finally {
    savingEdit.value = false
  }
}

async function openForwardDialog(msgOrMsgs) {
  forwardingMsgs.value = Array.isArray(msgOrMsgs) ? msgOrMsgs : [msgOrMsgs]
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
  if (!forwardingMsgs.value.length || !selectedForwardChatId.value) return
  sendingForward.value = true
  try {
    if (forwardingMsgs.value.length === 1) {
      await api.post(`/api/v1/chats/${chatId}/forward/${selectedForwardChatId.value}`, { msg_id: forwardingMsgs.value[0].id })
    } else {
      await api.post(`/api/v1/chats/${chatId}/forward-group/${selectedForwardChatId.value}`, { msg_ids: forwardingMsgs.value.map(m => m.id) })
    }
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

async function deleteMsg(msg) {
  try {
    await api.delete(`/api/v1/chats/${chatId}/messages/${msg.id}`)
    const m = messages.value.find(m => m.id === msg.id)
    if (m) {
      m.is_deleted = true
      m.content = 'Сообщение удалено'
      m.message_type = 'text'
    }
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка удаления' })
  }
}

// ── Pin / Unpin ────────────────────────────────────────────────────────────
function confirmUnpin(msg) {
  $q.dialog({
    title: 'Открепить сообщение',
    message: 'Убрать из закреплённых?',
    cancel: true,
    persistent: false,
  }).onOk(() => togglePin(msg))
}

async function togglePin(msg) {
  try {
    const { data } = await api.post(`/api/v1/chats/${chatId}/messages/${msg.id}/pin`)
    const localIdx = messages.value.findIndex(m => m.id === msg.id)
    if (localIdx !== -1) messages.value[localIdx] = { ...messages.value[localIdx], is_pinned: data.pinned }
    if (data.pinned) {
      const msgObj = messages.value.find(m => m.id === msg.id) || msg
      if (!pinnedMsgs.value.find(m => m.id === msgObj.id)) {
        pinnedMsgs.value.unshift(msgObj)
      }
      pinnedIdx.value = 0
    } else {
      const pi = pinnedMsgs.value.findIndex(m => m.id === msg.id)
      if (pi !== -1) pinnedMsgs.value.splice(pi, 1)
      if (pinnedIdx.value >= pinnedMsgs.value.length) pinnedIdx.value = Math.max(0, pinnedMsgs.value.length - 1)
    }
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка закрепления' })
  }
}

function cyclePinned() {
  if (!pinnedMsgs.value.length) return
  pinnedIdx.value = (pinnedIdx.value + 1) % pinnedMsgs.value.length
  scrollToPinnedMsg(pinnedMsgs.value[pinnedIdx.value])
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

const _imgBlobCache = {}
const _imgCacheVersion = ref(0)

function imgStreamUrl(msg) {
  if (msg._previewUrl) return msg._previewUrl
  if (!msg.yandex_path) return ''
  void _imgCacheVersion.value
  const key = msg.yandex_path
  if (_imgBlobCache[key]) return _imgBlobCache[key]
  if (!_imgBlobCache[`${key}:loading`]) {
    _imgBlobCache[`${key}:loading`] = true
    const path = msg.yandex_path.replace(/^disk:/, '')
    const token = localStorage.getItem('access_token') || ''
    fetch(`/api/v1/files/stream?yandex_path=${encodeURIComponent(path)}&token=${encodeURIComponent(token)}`)
      .then(r => r.ok ? r.blob() : Promise.reject(r.status))
      .then(blob => { _imgBlobCache[key] = URL.createObjectURL(blob); _imgCacheVersion.value++ })
      .catch(() => { delete _imgBlobCache[`${key}:loading`] })
  }
  const path = msg.yandex_path.replace(/^disk:/, '')
  const token = localStorage.getItem('access_token') || ''
  return `/api/v1/files/stream?yandex_path=${encodeURIComponent(path)}&token=${encodeURIComponent(token)}`
}

async function openInGallery(msg) {
  if (!msg?.id) return
  try {
    const { data } = await api.post(`/api/v1/chats/${chatId}/messages/${msg.id}/gallery-link`)
    if (data.public_url) window.open(data.public_url, '_blank')
    else $q.notify({ type: 'warning', message: 'Не удалось получить ссылку на галерею' })
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка публикации галереи' })
  }
}

// ── Image gallery viewer ──────────────────────────────────────────────────
const galleryVisible = ref(false)
const galleryImages = ref([])
const galleryStartIndex = ref(0)

function openImgGallery(msgs, clickedIdx) {
  galleryImages.value = msgs.map(m => ({
    src: imgStreamUrl(m),
    filename: m.file_name || 'Изображение',
    url: m.file_url || null,
  }))
  galleryStartIndex.value = clickedIdx
  galleryVisible.value = true
}

function isPdf(msg) {
  return msg.file_name?.toLowerCase().endsWith('.pdf')
}

async function loadPdfThumbnail(msg) {
  if (pdfThumbnails.value[msg.id]) return
  if (!isPdf(msg) || !msg.yandex_path) return
  const path = msg.yandex_path.replace(/^disk:/, '')
  try {
    const { data } = await api.get('/api/v1/files/stream', {
      params: { yandex_path: path, token: localStorage.getItem('access_token') || '' },
      responseType: 'arraybuffer',
    })
    const thumb = await getPdfThumbnail(data, String(msg.id))
    if (thumb) pdfThumbnails.value[msg.id] = thumb
  } catch { }
}

function isGuest(msg) {
  return !!msg.sender_guest_token
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

function _anchorToBottom(container) {
  container.scrollTop = container.scrollHeight
  let expected = container.scrollTop
  if (_scrollBottomTimer) { clearInterval(_scrollBottomTimer); _scrollBottomTimer = null }
  const tick = setInterval(() => {
    if (!container) { clearInterval(tick); _scrollBottomTimer = null; return }
    if (container.scrollTop >= expected - 50) {
      container.scrollTop = container.scrollHeight
      expected = container.scrollTop
    } else {
      clearInterval(tick)
      _scrollBottomTimer = null
    }
  }, 150)
  _scrollBottomTimer = tick
  setTimeout(() => { clearInterval(tick); if (_scrollBottomTimer === tick) _scrollBottomTimer = null }, 3000)
}

function scrollToBottom() {
  nextTick(() => {
    requestAnimationFrame(() => {
      if (messagesEl.value) _anchorToBottom(messagesEl.value)
    })
  })
}

function scrollToMsg(id) {
  nextTick(() => {
    const el = document.getElementById(`msg-${id}`) ||
               document.querySelector(`[data-msg-id="${id}"]`)
    if (!el) return
    const container = messagesEl.value
    if (container) {
      const cRect = container.getBoundingClientRect()
      const eRect = el.getBoundingClientRect()
      container.scrollTop = Math.max(0, container.scrollTop + (eRect.top - cRect.top) - cRect.height / 2 + eRect.height / 2)
    }
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
      _anchorToBottom(container)
    })
  })
}

async function loadMessages() {
  loadingMessages.value = true
  try {
    const { data } = await api.get(`/api/v1/chats/${chatId}`)
    chatTitle.value = data.title || `Чат #${chatId}`
    messages.value = data.messages || []
    hasMoreMessages.value = data.has_more_messages || false
    members.value = data.members || []
    clientToken.value = data.client_access_token || ''
    chatYdFolder.value = data.yandex_folder_path || null
    firstUnreadId.value = data.first_unread_message_id || null
    pinnedMsgs.value = data.pinned_messages || []
    pinnedIdx.value = 0
    scrollToFirstUnread()

    if (messages.value.length) {
      sendRead(messages.value[messages.value.length - 1].id)
    }
    chatUnreadStore.markChatRead(chatId)

    chatCrmCardId.value = data.crm_card_id || null

    // Загружаем данные карточки для подстановки переменных в скрипты
    if (data.crm_card_id) {
      loadCardData(data.crm_card_id)
    }
    messages.value
      .filter(m => isPdf(m) && m.yandex_path && !m._uploading)
      .forEach(m => loadPdfThumbnail(m))
    nextTick(() => setupTopObserver())
  } catch (e) {
    console.error('[ClientChatRoom] Ошибка:', e)
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
    const { data } = await api.get(`/api/v1/chats/${chatId}/messages`, {
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
    console.error('[ClientChatRoom] Ошибка загрузки старых:', e)
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

async function scrollToPinnedMsg(msg) {
  if (!messages.value.find(m => m.id === msg.id)) {
    let attempts = 0
    while (hasMoreMessages.value && !messages.value.find(m => m.id === msg.id) && attempts < 20) {
      await loadOlderMessages()
      attempts++
    }
  }
  scrollToMsg(msg.id)
}

async function loadCardData(cardId) {
  try {
    const { data } = await api.get(`/api/v1/crm/cards/${cardId}`)
    cardData.value = data
  } catch {
    // Не критично — переменные останутся незаполненными
  }
}

function fillScriptVars(template) {
  if (!template) return ''
  const d = cardData.value || {}
  const clientFullName = d.client_name || ''
  const clientFirstName = clientFullName.split(' ').filter(Boolean)[1] || clientFullName.split(' ')[0] || ''
  const vars = {
    client_name: clientFullName,
    client_first_name: clientFirstName,
    address: d.address || '',
    area: d.area ? `${d.area} м²` : '',
    contract_number: d.contract_number || '',
    deadline: d.deadline || '',
    deadline_date: d.deadline || '',
    senior_manager: d.senior_manager_name || '',
    senior_manager_username: d.senior_manager_name || '',
    manager_name: d.manager_name || '',
    manager_username: d.manager_name || '',
    sdp: d.sdp_name || '',
    sdp_username: d.sdp_name || '',
    sender_name: authStore.employee?.full_name || '',
    role_name: authStore.employee?.position || '',
  }
  // Обрабатываем построчно: строки с незаполненными переменными убираем
  return template.split('\n').map(line => {
    const varMatches = [...line.matchAll(/\{(\w+)\}/g)]
    if (!varMatches.length) return line
    let hasEmptyVar = false
    const substituted = line.replace(/\{(\w+)\}/g, (match, key) => {
      if (key in vars) {
        if (!vars[key]) hasEmptyVar = true
        return vars[key]
      }
      return match // Неизвестная переменная — оставляем
    })
    return hasEmptyVar ? null : substituted
  }).filter(line => line !== null).join('\n').trim()
}

function sendText() {
  const text = inputText.value.trim()
  if (!text) return
  sendMessage(text, replyingTo.value?.id || null)
  replyingTo.value = null
  inputText.value = ''
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

// ── Файлы из карточки CRM ─────────────────────────────────────
const _CF_STAGE_LABELS = {
  measurement: 'Замер',
  stage1: 'Стадия 1 — Планировочное решение',
  stage2_concept: 'Стадия 2 — Концепция / коллажи',
  stage2_3d: 'Стадия 2 — 3D визуализация',
  stage3: 'Стадия 3 — Чертёжный проект',
  supervision: 'Авторский надзор',
  references: 'Референсы',
  photo_documentation: 'Фотофиксация',
  tech_task: 'Техническое задание',
  documents: 'Документы',
  acts: 'Акты',
  info_letters: 'Информационные письма',
  questionnaire: 'Анкета',
  // Акты (неподписанные)
  act_planning_yandex_path: 'Акт планировочного решения',
  act_concept_yandex_path: 'Акт концептуального дизайна',
  act_final_yandex_path: 'Акт финального дизайна',
  info_letter_yandex_path: 'Информационное письмо',
  // Акты (подписанные)
  act_planning_signed_yandex_path: 'Акт планировочного (подписанный)',
  act_concept_signed_yandex_path: 'Акт концептуального (подписанный)',
  act_final_signed_yandex_path: 'Акт финального (подписанный)',
  info_letter_signed_yandex_path: 'Информационное письмо (подписанное)',
  // Договор
  contract_file_yandex_path: 'Договор',
  additional_agreement_yandex_path: 'Дополнительное соглашение',
  // Чеки
  advance_receipt_yandex_path: 'Чек аванса',
  additional_receipt_yandex_path: 'Чек доплаты',
  third_receipt_yandex_path: 'Чек (3-й платёж)',
  // Прочие поля карточки
  tech_task_yandex_path: 'Техническое задание',
  photo_documentation_yandex_path: 'Фотофиксация',
  references_yandex_path: 'Референсы',
  measurement_yandex_path: 'Замер',
}
const _CF_STAGE_ORDER = [
  'measurement', 'stage1', 'stage2_concept', 'stage2_3d', 'stage3', 'supervision',
  'tech_task', 'documents', 'acts', 'info_letters', 'references', 'photo_documentation', 'questionnaire',
]
const _CF_IMG_EXTS = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff', 'heic'])
const _CF_PALETTE = {
  img:  { bg: '#C8E6C9', text: '#2E7D32' },
  pdf:  { bg: '#FFCDD2', text: '#B71C1C' },
  xls:  { bg: '#C8E6C9', text: '#1B5E20' },
  doc:  { bg: '#BBDEFB', text: '#0D47A1' },
  zip:  { bg: '#E1BEE7', text: '#4A148C' },
  def:  { bg: '#E0E0E0', text: '#424242' },
}
function _cfExt(name) { const d = (name || '').lastIndexOf('.'); return d >= 0 ? name.slice(d + 1).toLowerCase() : '' }
function cfBadgeColor(f) {
  const e = _cfExt(f.file_name || f.filename || '')
  if (_CF_IMG_EXTS.has(e)) return _CF_PALETTE.img
  if (e === 'pdf') return _CF_PALETTE.pdf
  if (['xls', 'xlsx', 'csv', 'ods'].includes(e)) return _CF_PALETTE.xls
  if (['doc', 'docx', 'odt', 'rtf', 'txt'].includes(e)) return _CF_PALETTE.doc
  if (['zip', 'rar', '7z', 'tar', 'gz'].includes(e)) return _CF_PALETTE.zip
  return _CF_PALETTE.def
}
function cfBadgeText(f) {
  const e = _cfExt(f.file_name || f.filename || '')
  return e ? e.toUpperCase().slice(0, 4) : 'FILE'
}
function cfBadgeStyle(f) {
  const c = cfBadgeColor(f)
  return { width: '56px', height: '42px', borderRadius: '4px', background: c.bg, color: c.text, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', fontSize: '11px', flexShrink: '0' }
}
function cfIsPreviewImg(f) { return _CF_IMG_EXTS.has(_cfExt(f.file_name || f.filename || '')) }
function cfIsPdf(f) { return _cfExt(f.file_name || f.filename || '') === 'pdf' }
function cfImgStreamUrl(f) {
  const raw = f?.yandex_path || ''
  if (!raw) return ''
  const path = raw.replace(/^disk:/, '')
  const token = localStorage.getItem('access_token') || ''
  return `/api/v1/files/stream?yandex_path=${encodeURIComponent(path)}&token=${encodeURIComponent(token)}`
}
function cfTrunc(name, max = 30) {
  if (!name || name.length <= max) return name || ''
  const dot = name.lastIndexOf('.')
  const ext = dot >= 0 ? name.slice(dot) : ''
  const keep = Math.max(max - 3 - ext.length, 8)
  return name.slice(0, keep) + '…' + ext
}

const showCardFilesDialog = ref(false)
const cardFiles = ref([])
const cardFilesLoading = ref(false)
const sendingCardFile = ref(false)
const selectedCardFiles = ref([])
const cfPdfThumbs = reactive({})

function isCardFileSelected(f) {
  const key = f.id || f.yandex_path
  return selectedCardFiles.value.some(sf => (sf.id || sf.yandex_path) === key)
}
function toggleCardFileSelection(f) {
  const key = f.id || f.yandex_path
  const idx = selectedCardFiles.value.findIndex(sf => (sf.id || sf.yandex_path) === key)
  if (idx >= 0) selectedCardFiles.value.splice(idx, 1)
  else selectedCardFiles.value.push(f)
}

const cardFileItems = computed(() => {
  const byStage = {}
  for (const f of cardFiles.value) {
    const s = f.stage || 'documents'
    const v = f.variation || 1
    if (!byStage[s]) byStage[s] = {}
    if (!byStage[s][v]) byStage[s][v] = []
    byStage[s][v].push(f)
  }
  const stageSet = new Set(Object.keys(byStage))
  const ordered = [
    ..._CF_STAGE_ORDER.filter(s => stageSet.has(s)),
    ...[...stageSet].filter(s => !_CF_STAGE_ORDER.includes(s)),
  ]
  const items = []
  for (const stage of ordered) {
    items.push({ type: 'stage', key: 's:' + stage, label: _CF_STAGE_LABELS[stage] || stage })
    const byVar = byStage[stage]
    const varNums = Object.keys(byVar).map(Number).sort((a, b) => a - b)
    const showVarHdr = varNums.length > 1 || (varNums.length === 1 && varNums[0] !== 1)
    for (const vn of varNums) {
      if (showVarHdr) items.push({ type: 'var', key: `v:${stage}:${vn}`, varNum: vn })
      const sorted = [...byVar[vn]].sort((a, b) => (a.file_order || 0) - (b.file_order || 0))
      for (const f of sorted) {
        const fname = f.file_name || f.filename || 'файл'
        items.push({ type: 'file', key: `f:${f.id || f.yandex_path}`, file: f, fname })
      }
    }
  }
  return items
})

async function loadCardFiles() {
  if (!chatCrmCardId.value) return
  cardFiles.value = []
  selectedCardFiles.value = []
  cardFilesLoading.value = true
  try {
    const { data: card } = await api.get(`/api/v1/crm/cards/${chatCrmCardId.value}`)
    const contractId = card?.contract_id
    if (contractId) {
      const { data: files } = await api.get(`/api/v1/files/contract/${contractId}`)
      cardFiles.value = Array.isArray(files) ? files : (files?.items || [])
      // Загружаем PDF-миниатюры асинхронно
      for (const f of cardFiles.value) {
        if (cfIsPdf(f) && f.yandex_path && !cfPdfThumbs[String(f.id)]) {
          getPdfThumbnail(cfImgStreamUrl(f), String(f.id)).then(thumb => {
            if (thumb) cfPdfThumbs[String(f.id)] = thumb
          })
        }
      }
    }
    // Файлы правок из папок workflow (revision_file_path)
    try {
      const { data: states } = await api.get(`/api/v1/crm/cards/${chatCrmCardId.value}/workflow/state`)
      const statesList = Array.isArray(states) ? states : []
      const revFolders = [...new Set(statesList.filter(s => s.revision_file_path).map(s => s.revision_file_path))]
      for (const folder of revFolders) {
        try {
          const { data: fl } = await api.get('/api/v1/files/list', { params: { folder_path: folder } })
          const items = fl?.files || []
          const revStage = statesList.find(s => s.revision_file_path === folder)?.stage_name || 'стадия'
          for (const item of items) {
            if (item.type !== 'file') continue
            const revFile = { id: `rev-${item.path}`, file_name: item.name, yandex_path: item.path, stage: `Правки: ${revStage}`, file_type: 'file' }
            cardFiles.value.push(revFile)
            if (cfIsPdf(revFile) && !cfPdfThumbs[revFile.id]) {
              getPdfThumbnail(cfImgStreamUrl(revFile), revFile.id).then(thumb => {
                if (thumb) cfPdfThumbs[revFile.id] = thumb
              })
            }
          }
        } catch {}
      }
    } catch {}
  } catch {
    cardFiles.value = []
  } finally {
    cardFilesLoading.value = false
  }
}

async function sendSelectedCardFiles() {
  if (!selectedCardFiles.value.length) return
  const files = [...selectedCardFiles.value]
  showCardFilesDialog.value = false
  sendingCardFile.value = true
  selectedCardFiles.value = []

  const allImages = files.every(f => cfIsPreviewImg(f))
  const useGallery = files.length > 1 && allImages && !!chatYdFolder.value

  if (useGallery) {
    const groupId = crypto.randomUUID()
    try {
      const { data: savedMsgs } = await api.post(`/api/v1/chats/${chatId}/card-files-gallery`, {
        group_id: groupId,
        files: files.map(f => ({
          yandex_path: f.yandex_path || '',
          file_name: f.file_name || f.filename || 'файл',
          file_size: f.file_size || null,
        })),
      })
      for (const msg of savedMsgs) {
        if (!messages.value.some(m => m.id === msg.id)) {
          messages.value.push(msg)
          if (isPdf(msg)) loadPdfThumbnail(msg)
        }
      }
      scrollToBottom()
      if (savedMsgs.length) sendRead(savedMsgs[savedMsgs.length - 1].id)
    } catch {
      $q.notify({ type: 'negative', message: 'Не удалось отправить файлы в галерею' })
    }
  } else {
    const errors = []
    let lastMsgId = null
    for (const f of files) {
      try {
        const fname = f.file_name || f.filename || 'файл'
        const message_type = cfIsPreviewImg(f) ? 'image' : 'file'
        const { data: msgData } = await api.post(`/api/v1/chats/${chatId}/messages/from-project-file`, {
          yandex_path: f.yandex_path || '',
          file_name: fname,
          public_link: f.public_link || '',
          message_type,
        })
        if (msgData?.id) {
          if (!messages.value.some(m => m.id === msgData.id)) {
            messages.value.push(msgData)
            if (isPdf(msgData)) loadPdfThumbnail(msgData)
          }
          lastMsgId = msgData.id
        }
      } catch {
        errors.push(f.file_name || f.filename || 'файл')
      }
    }
    if (lastMsgId) { scrollToBottom(); sendRead(lastMsgId) }
    if (errors.length) $q.notify({ type: 'negative', message: `Не удалось прикрепить: ${errors.join(', ')}` })
  }

  sendingCardFile.value = false
}

// ── File upload ───────────────────────────────────────────────────────────
const IMAGE_EXTS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif']

function isImageFile(file) {
  return IMAGE_EXTS.includes(file.name.split('.').pop()?.toLowerCase() || '')
}

function addFilesToPending(files) {
  if (!files.length) return
  const newPreviews = files.map(f => isImageFile(f) ? URL.createObjectURL(f) : null)
  const combined = [...pendingFiles.value, ...files]
  const combinedPreviews = [...pendingPreviews.value, ...newPreviews]
  if (combined.length > 20) {
    $q.notify({ type: 'warning', message: 'Максимум 20 файлов за раз', timeout: 2500 })
    combinedPreviews.slice(20).forEach(url => url && URL.revokeObjectURL(url))
    pendingFiles.value = combined.slice(0, 20)
    pendingPreviews.value = combinedPreviews.slice(0, 20)
  } else {
    pendingFiles.value = combined
    pendingPreviews.value = combinedPreviews
  }
}

function onFileSelected(event) {
  addFilesToPending([...(event.target.files || [])])
  event.target.value = ''
}

function removePendingFile(idx) {
  const url = pendingPreviews.value[idx]
  if (url) URL.revokeObjectURL(url)
  pendingFiles.value = pendingFiles.value.filter((_, i) => i !== idx)
  pendingPreviews.value = pendingPreviews.value.filter((_, i) => i !== idx)
  if (!pendingFiles.value.length) pendingCaption.value = ''
}

async function sendWithAttachment() {
  const files = pendingFiles.value
  if (!files.length) return
  const caption = pendingCaption.value.trim()
  const allImages = files.every(f => isImageFile(f))
  const groupId = (files.length > 1 && allImages) ? crypto.randomUUID() : null

  pendingFiles.value = []
  pendingPreviews.value.forEach(url => url && URL.revokeObjectURL(url))
  pendingPreviews.value = []
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

// Drag & Drop
const isDraggingOver = ref(false)
let _dragCounter = 0

function onDragEnter(e) {
  if (!e.dataTransfer?.types?.includes('Files')) return
  _dragCounter++
  isDraggingOver.value = true
}
function onDragLeave() {
  _dragCounter--
  if (_dragCounter <= 0) { _dragCounter = 0; isDraggingOver.value = false }
}
function onDragOver(e) { e.preventDefault() }
function onDrop(e) {
  e.preventDefault()
  _dragCounter = 0
  isDraggingOver.value = false
  const files = [...(e.dataTransfer?.files || [])]
  if (files.length) addFilesToPending(files)
}

// Вставка из буфера обмена
function onPaste(e) {
  const files = [...(e.clipboardData?.files || [])]
  if (!files.length) return
  e.preventDefault()
  addFilesToPending(files)
}

async function _uploadSingleFile(file, groupId = null, caption = null) {
  const ext = file.name.split('.').pop()?.toLowerCase() || ''
  const msgType = IMAGE_EXTS.includes(ext) ? 'image' : 'file'
  const isPdfUpload = ext === 'pdf'
  const tempId = `temp_${Date.now()}_${Math.random()}`
  const previewUrl = msgType === 'image' ? URL.createObjectURL(file) : null

  messages.value.push({
    id: tempId,
    sender_employee_id: null,
    sender_display_name: 'Вы',
    message_type: msgType,
    content: null,
    file_url: '',
    file_name: file.name,
    file_size: file.size,
    yandex_path: null,
    is_deleted: false,
    is_edited: false,
    is_pinned: false,
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
    const formData = new FormData()
    formData.append('file', file)
    formData.append('message_type', msgType)
    if (groupId) formData.append('group_id', groupId)
    if (caption) formData.append('caption', caption)
    uploadProgress.value = 1
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
      if (!alreadyAdded && isPdf(savedMsg)) loadPdfThumbnail(savedMsg)
    }
  } catch (e) {
    messages.value = messages.value.filter(m => m.id !== tempId)
    $q.notify({ type: 'negative', message: 'Ошибка загрузки файла' })
    throw e
  } finally {
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    uploadProgress.value = 0
  }
}

async function loadScripts() {
  if (scripts.value.length) return
  loadingScripts.value = true
  try {
    const { data } = await api.get('/api/v1/messenger/scripts')
    scripts.value = Array.isArray(data) ? data : (data.items || [])
  } catch (e) {
    console.error('[ClientChatRoom] Ошибка загрузки скриптов:', e)
  } finally {
    loadingScripts.value = false
  }
}

async function sendReaction(msg, emoji) {
  try {
    const { data } = await api.post(`/api/v1/chats/${chatId}/messages/${msg.id}/react`, { emoji })
    const idx = messages.value.findIndex(m => m.id === msg.id)
    if (idx !== -1) {
      const c = messagesEl.value
      const atBottom = !c || (c.scrollHeight - c.scrollTop - c.clientHeight < 50)
      messages.value[idx] = { ...messages.value[idx], reactions: data.reactions }
      if (atBottom) nextTick(() => requestAnimationFrame(() => { if (c) c.scrollTop = c.scrollHeight }))
    }
  } catch (e) {
    console.warn('[reaction]', e)
  }
}

function isOwnReaction(msg, emoji) {
  const reactors = msg.reactions?.[emoji] || []
  return reactors.some(r => r.employee_id === authStore.user?.id)
}

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
      await _uploadVoice(file)
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

async function _uploadVoice(file) {
  const folder = chatYdFolder.value
  if (!folder) {
    $q.notify({ type: 'negative', message: 'Папка чата не найдена', timeout: 2000 })
    return
  }
  const fd = new FormData()
  fd.append('file', file)
  fd.append('message_type', 'voice')
  fd.append('caption', String(recordSeconds.value))
  const dismiss = $q.notify({ group: false, spinner: true, message: 'Отправка голосового…', timeout: 0 })
  try {
    const { data } = await api.post(`/api/v1/chats/${chatId}/files`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    dismiss()
    const exists = messages.value.some(m => m.id === data.id)
    if (!exists) { messages.value.push(data); scrollToBottom() }
  } catch {
    dismiss()
    $q.notify({ type: 'negative', message: 'Ошибка загрузки голосового', timeout: 2000 })
  }
}

let _searchTimer = null
async function doSearch(val) {
  clearTimeout(_searchTimer)
  if (!val || val.length < 2) { searchResults.value = []; return }
  _searchTimer = setTimeout(async () => {
    searchLoading.value = true
    try {
      const { data } = await api.get(`/api/v1/chats/${chatId}/messages/search`, { params: { q: val, limit: 20 } })
      searchResults.value = Array.isArray(data) ? data : []
    } catch { searchResults.value = [] } finally { searchLoading.value = false }
  }, 400)
}

async function goToSearchResult(msg) {
  showSearch.value = false
  searchQuery.value = ''
  searchResults.value = []
  if (_topObserver) _topObserver.disconnect()
  await nextTick()
  if (!messages.value.find(m => m.id === msg.id)) {
    let attempts = 0
    while (hasMoreMessages.value && !messages.value.find(m => m.id === msg.id) && attempts < 20) {
      await loadOlderMessages()
      attempts++
    }
    await nextTick()
  }
  // Ждём закрытия клавиатуры на мобильном (анимация ~250-300мс)
  await new Promise(r => setTimeout(r, 350))
  const container = messagesEl.value
  if (!container) { setupTopObserver(); return }
  const el = container.querySelector(`#msg-${msg.id}`) ||
             container.querySelector(`[data-msg-id="${msg.id}"]`)
  if (!el) { setupTopObserver(); return }
  el.scrollIntoView({ block: 'center', behavior: 'instant' })
  el.classList.add('msg-highlight')
  setTimeout(() => el.classList.remove('msg-highlight'), 1500)
  setTimeout(() => setupTopObserver(), 300)
}

function selectScript(s) {
  selectedScript.value = s
  scriptText.value = fillScriptVars(s.message_template || '')
}

async function sendScript() {
  const text = scriptText.value.trim()
  if (!text) return
  try {
    const { data } = await api.post(`/api/v1/chats/${chatId}/messages`, {
      content: text,
      message_type: 'text',
    })
    // Добавляем сообщение сразу из ответа REST (не ждём WS)
    if (data && data.id) {
      const exists = messages.value.some(m => m.id === data.id)
      if (!exists) {
        messages.value.push(data)
        scrollToBottom()
      }
    }
    scriptText.value = ''
    selectedScript.value = null
    showScriptDialog.value = false
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Ошибка отправки скрипта' })
  }
}

async function createExtraLink() {
  try {
    const { data } = await api.post(`/api/v1/chats/${chatId}/invite-links`)
    extraInviteLink.value = `${window.location.origin}/c/${data.access_token}`
    $q.notify({ type: 'positive', message: 'Ссылка создана' })
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Ошибка создания ссылки' })
  }
}

async function sendEmailInvite() {
  if (!chatCrmCardId.value) return
  sendingInvite.value = true
  try {
    const { data } = await crmApi.inviteClientToChat(chatCrmCardId.value)
    $q.notify({ type: 'positive', message: data.message || 'Приглашение отправлено' })
  } catch (e) {
    const msg = e.response?.data?.detail || 'Ошибка отправки приглашения'
    $q.notify({ type: 'negative', message: msg })
  } finally {
    sendingInvite.value = false
  }
}

function copyText(text) {
  navigator.clipboard.writeText(text).catch(() => { })
}

async function onMembersDialogOpen() {
  if (!chatCrmCardId.value) return
  availableEmployees.value = null
  loadingAvailableEmps.value = true
  try {
    // Свежий статус участников (is_online, last_login)
    const { data: chatData } = await api.get(`/api/v1/chats/${chatId}`)
    members.value = chatData.members || []

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
      if (r.id) emps.set(r.id, { name: r.name || `Сотрудник #${r.id}`, role: r.role })
    }
    for (const se of (data.stage_executors || [])) {
      if (se.executor_id) {
        const existing = emps.get(se.executor_id)
        const stageName = se.stage_name || 'Исполнитель'
        if (existing) {
          existing.role = existing.role.includes(stageName) ? existing.role : existing.role + ' + ' + stageName
        } else {
          emps.set(se.executor_id, { name: se.executor_name || `Сотрудник #${se.executor_id}`, role: stageName })
        }
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
  const isGuest = m.member_type === 'client_guest' || !m.employee_id
  const name = m.display_name || m.guest_name || 'Участник'
  const confirmed = await new Promise(resolve => {
    $q.dialog({
      title: isGuest ? 'Аннулировать доступ клиента?' : 'Удалить из чата?',
      message: isGuest
        ? `Клиент «${name}» потеряет доступ к чату. Для восстановления нужно будет создать новую ссылку и передать её клиенту.`
        : `Удалить «${name}» из чата?`,
      ok: { label: isGuest ? 'Аннулировать' : 'Удалить', color: 'negative', flat: true },
      cancel: { label: 'Отмена', flat: true },
    }).onOk(() => resolve(true)).onCancel(() => resolve(false))
  })
  if (!confirmed) return
  removingMemberId.value = m.id
  try {
    await api.delete(`/api/v1/chats/${chatId}/members/${m.id}`)
    members.value = members.value.filter(mb => mb.id !== m.id)
    $q.notify({ type: 'positive', message: isGuest ? `Доступ клиента «${name}» аннулирован` : `${name} удалён из чата` })
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Ошибка удаления' })
  } finally {
    removingMemberId.value = null
  }
}

function connectWs() {
  const token = localStorage.getItem('access_token')
  if (!token) return
  connectEmployee(chatId, token, {
    onMessage: (msg) => {
      const exists = messages.value.some(m => m.id === msg.id)
      if (!exists) {
        messages.value.push(msg)
        scrollToBottom()
        if (isPdf(msg)) loadPdfThumbnail(msg)
      }
    },
    onMessageGroup: (msgs) => {
      msgs.forEach(msg => {
        const exists = messages.value.some(m => m.id === msg.id)
        if (!exists) {
          messages.value.push(msg)
          if (isPdf(msg)) loadPdfThumbnail(msg)
        }
      })
      scrollToBottom()
      if (msgs.length) sendRead(msgs[msgs.length - 1].id)
    },
    onMessageUpdated: (msg) => {
      const idx = messages.value.findIndex(m => m.id === msg.id)
      if (idx !== -1) messages.value.splice(idx, 1, msg)
    },
    onMessageDeleted: (msgId) => {
      const idx = messages.value.findIndex(m => m.id === msgId)
      if (idx !== -1) messages.value[idx] = { ...messages.value[idx], is_deleted: true, content: '[Сообщение удалено]', message_type: 'text' }
    },
    onPinned: (evt) => {
      const idx = messages.value.findIndex(m => m.id === evt.message_id)
      if (idx !== -1) messages.value[idx] = { ...messages.value[idx], is_pinned: evt.pinned }
      if (evt.pinned && evt.message) {
        if (!pinnedMsgs.value.some(p => p.id === evt.message_id)) pinnedMsgs.value.push(evt.message)
      } else {
        pinnedMsgs.value = pinnedMsgs.value.filter(p => p.id !== evt.message_id)
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
}

onMounted(() => {
  recalcChatH()
  window.addEventListener('resize', recalcChatH)
  window.visualViewport?.addEventListener('resize', recalcChatH)
  loadMessages()
  connectWs()
})

onBeforeRouteUpdate((to, from, next) => {
  const newChatId = Number(to.params.chatId)
  if (newChatId !== chatId) {
    chatId = newChatId
    disconnect()
    if (_topObserver) _topObserver.disconnect()
    messages.value = []
    members.value = []
    pinnedMsgs.value = []
    pinnedIdx.value = 0
    chatTitle.value = 'Чат с клиентом'
    inputText.value = ''
    hasMoreMessages.value = false
    chatCrmCardId.value = null
    chatYdFolder.value = null
    firstUnreadId.value = null
    searchQuery.value = ''
    searchResults.value = []
    loadMessages()
    connectWs()
  }
  next()
})

onUnmounted(() => {
  disconnect()
  if (_topObserver) _topObserver.disconnect()
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
  max-width: 75%;
}
.bubble-forwarded {
  background: #EEEEEE !important;
}
.bubble-other {
  background: #fff;
  border-radius: 12px 12px 12px 2px;
  padding: 8px 12px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
  max-width: 75%;
}
.bubble-img-own {
  background: #E8F5E9;
  border-radius: 12px 12px 2px 12px;
  overflow: hidden;
  min-width: 160px;
  max-width: min(85vw, 440px);
}
.bubble-img-other {
  background: #fff;
  border-radius: 12px 12px 12px 2px;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
  min-width: 160px;
  max-width: min(85vw, 440px);
}
.hidden {
  display: none;
}
@keyframes msg-highlight-pulse {
  0% { background: rgba(255, 214, 0, 0.45); }
  100% { background: transparent; }
}
.msg-highlight { animation: msg-highlight-pulse 1.5s ease-out; border-radius: 8px; }
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
  transition: background 0.15s;
}
.react-quick-btn:hover { background: #F0F0F0; }
.react-quick-btn--active { background: #E3F2FD; }
</style>
