<template>
  <!-- Загрузка -->
  <div v-if="loading" class="flex flex-center q-pa-xl">
    <q-spinner size="32px" color="grey" />
  </div>

  <!-- Чат не создан -->
  <div v-else-if="!chat" class="flex flex-center q-pa-xl column items-center">
    <q-icon
      :name="chatType === 'client' ? 'support_agent' : 'chat_bubble_outline'"
      size="48px"
      color="grey-4"
      class="q-mb-md"
    />
    <div class="text-grey-6 q-mb-md text-body2">
      {{ chatType === 'client' ? 'Чат с клиентом не создан' : chatType === 'supervision' ? 'Чат надзора не создан' : 'Чат сотрудников не создан' }}
    </div>
    <q-btn
      unelevated
      no-caps
      :color="chatType === 'client' ? 'green-7' : 'blue-7'"
      :label="chatType === 'client' ? 'Создать чат с клиентом' : chatType === 'supervision' ? 'Создать чат надзора' : 'Создать чат сотрудников'"
      :loading="creating"
      @click="createChat"
    />
  </div>

  <!-- Чат существует -->
  <div
    v-else
    ref="chatContainerEl"
    class="column"
    :style="{ height: containerHeight, minHeight: '320px', width: '100%', maxWidth: '100%', overflow: 'hidden', position: 'relative' }"
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
    <!-- Шапка чата: ссылка и участники -->
    <div
      class="q-px-md q-py-xs bg-white"
      style="border-bottom: 1px solid #E0E0E0; flex-shrink: 0; min-height: 36px; display: flex; flex-wrap: nowrap; align-items: center; overflow: hidden; width: 100%; box-sizing: border-box"
    >
      <!-- Блок надзора: ссылка для клиента -->
      <div
        v-if="chatType === 'supervision'"
        style="flex: 1 1 0%; min-width: 0; display: flex; flex-wrap: nowrap; align-items: center; overflow: hidden"
      >
        <template v-if="supervisionLink">
          <q-icon
            name="link"
            size="14px"
            color="blue-7"
            class="q-mr-xs"
            style="flex: 0 0 auto"
          />
          <span
            class="text-caption text-blue-8"
            style="flex: 1 1 0%; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap"
          >
            {{ supervisionLink }}
          </span>
          <q-btn
            flat
            dense
            size="xs"
            icon="content_copy"
            color="blue-7"
            style="flex: 0 0 auto; margin-left: 4px"
            @click="copySupervisionLink"
          >
            <q-tooltip>Копировать ссылку</q-tooltip>
          </q-btn>
        </template>
        <template v-else>
          <span class="text-caption text-grey-6" style="flex: 1 1 0%">Чат надзора</span>
          <q-btn
            flat
            dense
            size="xs"
            icon="add_link"
            color="blue-7"
            :loading="creatingSupervisionLink"
            style="flex: 0 0 auto"
            @click="createSupervisionLink"
          >
            <q-tooltip>Создать ссылку для клиента</q-tooltip>
          </q-btn>
        </template>
      </div>
      <span v-else class="text-caption text-grey-6" style="flex: 1 1 0%; min-width: 0">
        {{ chatType === 'client' ? 'Чат с клиентом' : 'Чат сотрудников' }}
      </span>
      <!-- Кнопка доступа клиента (только для клиентского чата из карточки) -->
      <q-btn
        v-if="chatType === 'client' && props.cardId"
        flat
        dense
        size="xs"
        icon="manage_accounts"
        color="green-7"
        style="flex: 0 0 auto; margin-left: 2px"
        @click="showClientAccess = true"
      >
        <q-tooltip>Доступ клиента</q-tooltip>
      </q-btn>
      <!-- Кнопка участников: всегда справа, никогда не сжимается -->
      <q-btn
        flat
        dense
        size="xs"
        icon="people"
        color="grey-7"
        style="flex: 0 0 auto; margin-left: 4px"
        @click="showMembers = true"
      >
        <q-tooltip>Участники</q-tooltip>
      </q-btn>
      <!-- Кнопка поиска -->
      <q-btn
        flat
        dense
        size="xs"
        icon="search"
        :color="showSearch ? 'primary' : 'grey-7'"
        style="flex: 0 0 auto; margin-left: 2px"
        @click="showSearch = !showSearch; searchQuery = ''; searchResults = []"
      >
        <q-tooltip>Поиск в чате</q-tooltip>
      </q-btn>
    </div>

    <!-- Поиск по сообщениям -->
    <div v-if="showSearch" class="q-px-sm q-py-xs bg-white" style="border-bottom: 1px solid #E0E0E0; flex-shrink: 0">
      <q-input
        v-model="searchQuery"
        dense
        outlined
        clearable
        autofocus
        hide-bottom-space
        placeholder="Поиск сообщений…"
        style="font-size: 13px"
        @update:model-value="handleSearch"
        @clear="searchResults = []"
      >
        <template #prepend>
          <q-icon name="search" size="16px" color="grey-6" />
        </template>
      </q-input>
      <q-list
        v-if="searchResults.length"
        dense
        separator
        class="q-mt-xs"
        style="max-height: 180px; overflow-y: auto; background: #fff; border: 1px solid #e0e0e0; border-radius: 4px"
      >
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
              {{ r.sender_display_name || '?' }}
              <span class="text-grey-5 text-weight-regular q-ml-xs">{{ formatTime(r.created_at) }}</span>
            </q-item-label>
            <q-item-label caption class="ellipsis">
              {{ r.content || r.file_name || '[файл]' }}
            </q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
      <div v-else-if="searchQuery && !searchLoading" class="text-caption text-grey-5 q-mt-xs text-center q-pb-xs">
        Ничего не найдено
      </div>
    </div>

    <!-- Индикатор печати -->
    <div
      v-if="typingText"
      class="q-px-md q-py-xs text-caption text-grey"
      style="flex-shrink: 0; background: #FAFAFA"
    >
      {{ typingText }}
    </div>

    <!-- Прогресс загрузки файла -->
    <q-linear-progress
      v-if="uploadProgress > 0 && uploadProgress < 100"
      :value="uploadProgress / 100"
      color="blue-5"
      style="flex-shrink: 0"
    />

    <!-- Закреплённые сообщения (до 10, Telegram-стиль) -->
    <div
      v-if="pinnedMsgs.length"
      class="row items-center q-px-sm q-py-xs bg-white"
      style="border-bottom: 1px solid #E0E0E0; flex-shrink: 0; cursor: pointer; gap: 6px"
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
      <q-icon name="push_pin" size="13px" color="orange-8" style="flex-shrink: 0" />
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
      class="col q-px-md q-py-sm"
      style="overflow-y: auto; background: #F5F5F5"
    >
      <div v-if="!messages.length" class="text-center text-grey q-mt-lg">
        <q-icon name="chat_bubble_outline" size="32px" />
        <div class="q-mt-xs text-body2">
          Нет сообщений
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
                :class="[isOwn(item.msgs[0]) ? 'bubble-img-own' : 'bubble-img-other', { 'bubble-forwarded': isForwarded(item.msgs[0]) }]"
                :style="galleryBubbleStyle(item.msgs.length)"
              >
                <div class="row no-wrap items-center justify-between" style="padding: 5px 8px 3px; min-height: 16px; gap: 2px">
                  <div
                    class="text-caption text-weight-bold"
                    :style="{ color: isOwn(item.msgs[0]) ? '#999' : '#1565C0' }"
                    style="flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap"
                  >
                    {{ item.msgs[0].sender_display_name }}
                  </div>
                  <!-- 3-точки для галереи -->
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
                        <q-item
                          v-if="item.msgs.some(m => m.yandex_path) && chat && chat.crm_card_id"
                          clickable
                          dense
                          @click="openCopyToCard(item.msgs.find(m => m.yandex_path))"
                        >
                          <q-item-section avatar style="min-width: 28px">
                            <q-icon name="drive_file_move" size="14px" color="grey-8" />
                          </q-item-section>
                          <q-item-section style="font-size: 12px">
                            Скопировать в карточку
                          </q-item-section>
                        </q-item>
                        <q-item
                          v-if="isOwn(item.msgs[0])"
                          clickable
                          dense
                          @click="deleteMsg(item.msgs[0])"
                        >
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
                <!-- 1-3 фото: стандартные раскладки -->
                <template v-if="item.msgs.length < 4">
                  <div :class="galleryGridClass(item.msgs.length)" :style="galleryGridStyle(item.msgs.length)">
                    <div
                      v-for="(gm, gi) in item.msgs"
                      :key="gm.id"
                      :style="galleryItemContainerStyle(item.msgs.length, gi)"
                      @click="openImgGallery(item.msgs, gi)"
                    >
                      <q-img
                        v-if="imgStreamUrl(gm)"
                        :src="imgStreamUrl(gm)"
                        :style="galleryImgStyle(item.msgs.length)"
                        fit="cover"
                        spinner-color="grey-4"
                        spinner-size="18px"
                      />
                    </div>
                  </div>
                </template>
                <!-- 4+ фото: первые 2 крупно, остальные мелкой сеткой -->
                <template v-else>
                  <div style="display: flex; flex-direction: column; gap: 2px;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2px;">
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
                          spinner-size="18px"
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
                          spinner-size="18px"
                        />
                      </div>
                    </div>
                  </div>
                </template>
                <div v-if="groupCaption(item.msgs)" class="text-body2" style="padding: 3px 8px 2px; white-space: pre-wrap; word-break: break-word; font-size: 13px">
                  {{ groupCaption(item.msgs) }}
                </div>
                <div class="row no-wrap items-center justify-between" style="padding: 2px 8px 4px 2px; margin-top: 0">
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
                  <div v-else />
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

                <!-- Обычные -->
                <div
                  v-else
                  :class="[(msg.message_type === 'image' || (isPdf(msg) && pdfThumbnails[msg.id]))
                    ? (isOwn(msg) ? 'bubble-img-own' : 'bubble-img-other')
                    : (isOwn(msg) ? 'bubble-own' : 'bubble-other'), { 'bubble-forwarded': isForwarded(msg) }]"
                  :style="pdfBubbleStyle(msg)"
                >
                  <!-- Верхняя строка: имя отправителя + кнопка меню -->
                  <div
                    class="row no-wrap items-center justify-between q-mb-xs"
                    :style="(msg.message_type === 'image' || (isPdf(msg) && pdfThumbnails[msg.id])) ? 'min-height:16px;gap:2px;padding:5px 8px 3px' : 'min-height:16px;gap:2px'"
                  >
                    <div
                      class="text-caption text-weight-bold"
                      :style="{ color: isOwn(msg) ? '#999' : (msg.sender_guest_token ? '#2E7D32' : '#1565C0') }"
                      style="flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap"
                    >
                      {{ msg.sender_display_name }}
                      <q-chip
                        v-if="msg.sender_guest_token"
                        dense
                        size="xs"
                        color="green-2"
                        text-color="green-9"
                      >
                        клиент
                      </q-chip>
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
                          <q-item v-if="msg.yandex_path && chat && chat.crm_card_id" clickable dense @click="openCopyToCard(msg)">
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

                  <!-- Загрузка файла (оптимистичное сообщение) -->
                  <template v-if="msg._uploading">
                    <div v-if="msg._previewUrl">
                      <q-img :src="msg._previewUrl" style="width: 100%; max-height: 200px; display: block" fit="cover" />
                      <div class="row items-center q-gutter-xs" style="padding: 3px 8px 2px; opacity: 0.7">
                        <q-spinner size="10px" color="grey-5" />
                        <span class="text-caption text-grey-6">{{ msg.file_name }}</span>
                      </div>
                    </div>
                    <div v-else class="row items-center q-gutter-xs">
                      <q-icon :name="isPdf(msg) ? 'picture_as_pdf' : 'upload'" size="16px" :color="isPdf(msg) ? 'red-5' : 'grey-5'" />
                      <span class="text-caption text-grey-6" style="word-break: break-word">{{ msg.file_name }}…</span>
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
                        <div style="min-width: 0">
                          <div class="text-caption text-weight-bold" style="color: #1565C0; font-size: 11px">
                            {{ msg.reply_preview.sender_display_name }}
                          </div>
                          <div class="text-caption text-grey-7 ellipsis" style="font-size: 11px">
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
                          style="width: 100%; max-height: clamp(140px, 30vh, 420px); display: block; cursor: pointer; min-height: 70px"
                          fit="contain"
                          spinner-color="grey-4"
                          spinner-size="24px"
                        />
                        <div class="row items-center q-gutter-xs" style="padding: 3px 8px 2px">
                          <q-icon name="image" size="13px" color="grey-6" />
                          <span class="text-caption text-grey-7 ellipsis" style="max-width: 200px; font-size: 11px">
                            {{ msg.file_name || 'Изображение' }}
                          </span>
                        </div>
                        <div v-if="msg.content" class="text-body2" style="padding: 2px 8px 3px; white-space: pre-wrap; word-break: break-word; font-size: 13px">
                          {{ msg.content }}
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
                      <div class="row items-center" style="gap: 6px; width: 200px; padding: 4px 0">
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

                  <!-- Нижняя строка: время + реакции -->
                  <div
                    class="row no-wrap items-center"
                    :class="isOwn(msg) ? 'justify-end' : 'justify-start'"
                    :style="(msg.message_type === 'image' || (isPdf(msg) && pdfThumbnails[msg.id])) ? 'padding: 2px 10px 6px; margin-top: 0' : 'margin-top: 4px'"
                  >
                    <span v-if="msg.is_edited" class="text-caption text-grey-5 q-mr-xs" style="font-size: 9px">изм.</span>
                    <div class="text-caption" style="color: #888; font-size: 10px">
                      {{ formatTime(msg.created_at) }}
                    </div>
                  </div>
                  <!-- Чипсы реакций -->
                  <div v-if="msg.reactions && Object.keys(msg.reactions).length" class="row items-center q-gutter-xs" style="margin-top: 4px; flex-wrap: wrap">
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
            </template><!-- /v-for msg alias -->
          </template><!-- /v-else single -->
        </template><!-- /v-for renderedItems -->
      </template>
    </div>

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
            style="max-width: 140px"
            @remove="removePendingFile(i)"
          >
            <span class="ellipsis" style="font-size: 11px; max-width: 100px">{{ f.name }}</span>
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
      <div class="row items-center q-gutter-xs" style="min-width: 0">
        <q-btn
          round
          dense
          size="sm"
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
          style="display: none"
          @change="onFileSelected"
        >
        <!-- Файлы из карточки CRM / надзора -->
        <q-btn
          v-if="props.cardId || props.supervisionCardId"
          round
          dense
          size="sm"
          icon="folder_open"
          color="grey-6"
          @click="showCardFilesDialog = true; loadCardFiles()"
        >
          <q-tooltip>{{ chatType === 'supervision' ? 'Файлы карточки надзора' : 'Файлы из карточки CRM' }}</q-tooltip>
        </q-btn>
        <!-- Кнопка микрофона (если нет ожидающих файлов и нет текста) -->
        <q-btn
          v-if="!pendingFiles.length && !inputText.trim()"
          round
          dense
          size="sm"
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
          style="flex: 1; min-width: 0"
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
          style="flex: 1; min-width: 0"
          @keydown.enter.exact.prevent="sendText"
          @input="onTyping"
          @paste="onPaste"
        />
        <q-btn
          v-if="!isRecording"
          round
          dense
          size="sm"
          icon="send"
          :color="chatType === 'client' ? 'green-7' : 'blue-7'"
          :disable="pendingFiles.length ? false : !inputText.trim()"
          @click="pendingFiles.length ? sendWithAttachment() : sendText()"
        />
      </div>
    </div>

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
        <q-separator class="q-mt-sm" />
        <q-card-section class="q-pb-none q-pt-sm">
          <q-input
            v-model="forwardSearchQuery"
            dense
            outlined
            placeholder="Поиск чата..."
            clearable
          >
            <template #prepend>
              <q-icon name="search" size="18px" />
            </template>
          </q-input>
        </q-card-section>
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
            <div v-if="!loadingForwardChats && !forwardTargetChats.length" class="text-center text-grey q-pa-md">
              Нет доступных чатов
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

        <!-- Текущие участники -->
        <q-list dense>
          <q-item v-for="m in chatMembers" :key="m.id">
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
                  v-if="m.member_type === 'employee'"
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
                v-if="canShowLastLogin && m.member_type === 'employee'"
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
          <q-item v-if="!chatMembers.length">
            <q-item-section>
              <q-item-label class="text-grey">
                Нет участников
              </q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <!-- Секция добавления сотрудников карточки -->
        <template v-if="cardEmployees !== null">
          <q-separator class="q-mt-sm" />
          <q-card-section class="q-py-sm">
            <div class="text-body2 text-weight-medium text-blue-grey-7 q-mb-xs">
              Добавить в чат
            </div>
            <div v-if="loadingCardEmployees" class="text-center q-py-sm">
              <q-spinner size="20px" color="grey" />
            </div>
            <div v-else-if="!cardEmployees.length" class="text-caption text-grey-5 q-py-xs" style="font-style: italic">
              Все сотрудники карточки уже в чате
            </div>
            <q-list v-else dense>
              <q-item
                v-for="emp in cardEmployees"
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

    <!-- Диалог: файлы из карточки CRM -->
    <q-dialog v-model="showCardFilesDialog" persistent>
      <q-card style="min-width: 340px; max-width: 500px; width: 100%; border-radius: 10px; overflow: hidden">
        <!-- Заголовок — белый с нижней границей, как в десктопе -->
        <q-card-section class="row items-center" style="background:#fff; border-bottom:1px solid #E0E0E0; padding:10px 16px">
          <div style="font-size:14px; font-weight:600; color:#222">
            {{ chatType === 'supervision' ? 'Файлы надзора' : 'Файлы из карточки CRM' }}
          </div>
          <q-space />
          <q-btn
            icon="close"
            flat
            round
            dense
            size="sm"
            @click="showCardFilesDialog = false; selectedCardFiles = new Set()"
          />
        </q-card-section>

        <!-- Подсказка -->
        <div style="padding:10px 16px 4px; font-size:11px; color:#555; background:#F9FAFB">
          Отметьте файлы для отправки в чат:
        </div>

        <!-- Список файлов — стиль QListWidget из десктопа -->
        <div style="background:#F9FAFB; padding:0 14px 8px">
          <div v-if="cardFilesLoading" class="flex flex-center q-pa-lg">
            <q-spinner size="28px" color="grey" />
          </div>
          <div v-else-if="!cardFiles.length" class="text-grey-6 text-caption q-pa-sm">
            Файлы не найдены
          </div>
          <div
            v-else
            style="border:1px solid #E0E0E0; border-radius:4px; background:#fff; max-height:55vh; overflow-y:auto"
          >
            <template v-for="group in groupedCardFiles" :key="group.stage">
              <!-- Заголовок секции -->
              <div class="cf-stage-hdr">
                {{ group.stage }}
              </div>
              <template v-for="vg in group.variants" :key="vg.varNum">
                <!-- Заголовок варианта (только если вариантов >1) -->
                <div v-if="group.showVariants" class="cf-var-hdr">
                  Вариант {{ vg.varNum }}
                </div>
                <!-- Строка файла -->
                <div
                  v-for="f in vg.files"
                  :key="cfFileKey(f)"
                  class="cf-file-row"
                  :class="{ 'cf-file-row--checked': selectedCardFiles.has(cfFileKey(f)) }"
                  @click="toggleCardFile(f)"
                >
                  <!-- Превью / иконка слева -->
                  <div class="cf-thumb">
                    <img
                      v-if="cardFileThumbUrl(f)"
                      :src="cardFileThumbUrl(f)"
                      class="cf-thumb-img"
                      @error="e => e.target.style.display='none'"
                    >
                    <div v-else class="cf-thumb-icon" :class="cfIconClass(f)">
                      {{ cfIconLabel(f) }}
                    </div>
                  </div>
                  <!-- Название файла по центру -->
                  <div class="cf-fname">
                    {{ f.file_name || f.filename || 'файл' }}
                  </div>
                  <!-- Чекбокс справа -->
                  <q-checkbox
                    :model-value="selectedCardFiles.has(cfFileKey(f))"
                    color="primary"
                    dense
                    @update:model-value="toggleCardFile(f)"
                    @click.stop
                  />
                </div>
              </template>
            </template>
          </div>
        </div>

        <!-- Кнопки -->
        <q-card-actions align="right" style="background:#F9FAFB; padding:6px 14px 12px; border-top:1px solid #E0E0E0">
          <button class="cf-btn-cancel" @click="showCardFilesDialog = false; selectedCardFiles = new Set()">
            Отмена
          </button>
          <button
            class="cf-btn-send"
            :class="{ 'cf-btn-send--disabled': selectedCardFiles.size === 0 }"
            :disabled="selectedCardFiles.size === 0"
            @click="sendSelectedCardFiles"
          >
            {{ selectedCardFiles.size > 0 ? `Отправить (${selectedCardFiles.size})` : 'Отправить' }}
          </button>
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог: Доступ клиента -->
    <q-dialog v-model="showClientAccess">
      <q-card style="min-width: 320px; max-width: 440px; width: 100%">
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

        <q-card-section>
          <div class="text-subtitle2 q-mb-xs">
            <q-icon name="email" size="16px" class="q-mr-xs" />Пригласить клиента
          </div>
          <div class="text-caption text-grey-7 q-mb-sm">
            Клиент получит письмо с инструкцией и ссылкой на чат
          </div>
          <q-btn
            v-if="props.cardId"
            color="primary"
            icon="send"
            label="Отправить приглашение на email"
            :loading="sendingInvite"
            unelevated
            class="full-width"
            @click="sendEmailInvite"
          />
        </q-card-section>

        <q-separator />

        <q-card-section v-if="clientLink">
          <div class="text-subtitle2 q-mb-xs">
            <q-icon name="link" size="16px" class="q-mr-xs" />Основная ссылка
          </div>
          <div class="text-caption text-grey-7 q-mb-sm">
            Та же, что и в email-приглашении
          </div>
          <q-input :model-value="clientLink" readonly outlined dense>
            <template #append>
              <q-btn flat dense icon="content_copy" @click="copyClientLink">
                <q-tooltip>Скопировать</q-tooltip>
              </q-btn>
            </template>
          </q-input>
        </q-card-section>

        <q-separator />

        <q-card-section>
          <div class="text-subtitle2 q-mb-xs">
            <q-icon name="group_add" size="16px" class="q-mr-xs" />Ссылки для представителей
          </div>
          <div class="text-caption text-grey-7 q-mb-sm">
            Для жены, прораба или других участников проекта
          </div>
          <q-input
            v-if="clientAccessInviteLink"
            :model-value="clientAccessInviteLink"
            readonly
            outlined
            dense
            class="q-mb-sm"
          >
            <template #append>
              <q-btn flat dense icon="content_copy" @click="copyClientAccessInviteLink">
                <q-tooltip>Скопировать</q-tooltip>
              </q-btn>
            </template>
          </q-input>
          <q-btn
            outline
            color="primary"
            icon="add_link"
            label="Создать новую ссылку"
            :loading="creatingClientLink"
            class="full-width"
            @click="createClientInviteLink"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Закрыть" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <ImageGalleryDialog
      v-model="galleryVisible"
      :images="galleryImages"
      :start-index="galleryStartIndex"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { api } from 'src/boot/axios'
import { crmApi } from 'src/services/api'
import { useChatWebSocket } from 'src/composables/useChatWebSocket'
import { getPdfThumbnail } from 'src/composables/usePdfThumbnail'
import { useAuthStore } from 'src/stores/auth'
import { usePermission } from 'src/composables/usePermission'
import { useChatUnreadStore } from 'src/stores/chatUnread'
import { useQuasar } from 'quasar'
import ImageGalleryDialog from 'src/components/ImageGalleryDialog.vue'

const props = defineProps({
  chatType: {
    type: String,
    required: true, // 'employee' | 'client' | 'supervision'
  },
  cardId: {
    type: Number,
    default: null,
  },
  supervisionCardId: {
    type: Number,
    default: null,
  },
})

const authStore = useAuthStore()
const chatUnreadStore = useChatUnreadStore()
const $q = useQuasar()
const { connectEmployee, disconnect, sendMessage, sendTypingStart, sendTypingStop, sendRead, typingUsers } = useChatWebSocket()

const loading = ref(false)
const creating = ref(false)
const chat = ref(null)
const messages = ref([])
const firstUnreadId = ref(null)
const inputText = ref('')
const messagesEl = ref(null)
let _scrollBottomTimer = null
const fileInput = ref(null)
const chatContainerEl = ref(null)
const containerHeight = ref('calc(100vh - 270px)')
const clientChatId = ref(null)
const pdfThumbnails = ref({})
const pdfImgWidths = reactive({})
function pdfBubbleStyle(msg) {
  if (!isPdf(msg) || !pdfThumbnails.value[msg.id]) return 'min-width: 0'
  const w = pdfImgWidths[msg.id]
  return w ? `width: ${w}px; min-width: 0` : 'width: fit-content; max-width: min(85vw, 440px); min-width: 0'
}
const uploadProgress = ref(0)

// ── Invite link надзора ───────────────────────────────────────
const supervisionLink = ref('')
const creatingSupervisionLink = ref(false)

async function loadSupervisionLink(chatId) {
  try {
    const { data } = await api.get(`/api/v1/chats/${chatId}/invite-links`)
    const links = Array.isArray(data) ? data : []
    supervisionLink.value = links.length > 0 ? links[0].url : ''
  } catch { supervisionLink.value = '' }
}

async function createSupervisionLink() {
  if (!chat.value || creatingSupervisionLink.value) return
  creatingSupervisionLink.value = true
  try {
    const { data } = await api.post(`/api/v1/chats/${chat.value.id}/invite-links`)
    supervisionLink.value = data.url || ''
    if (supervisionLink.value) navigator.clipboard.writeText(supervisionLink.value).catch(() => {})
    $q.notify({ type: 'positive', message: 'Ссылка создана и скопирована' })
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Ошибка создания ссылки' })
  } finally {
    creatingSupervisionLink.value = false
  }
}

function copySupervisionLink() {
  if (!supervisionLink.value) return
  navigator.clipboard.writeText(supervisionLink.value).then(() => {
    $q.notify({ type: 'positive', message: 'Ссылка скопирована', timeout: 1000 })
  }).catch(() => {})
}

// ── Файлы из карточки CRM / надзора ──────────────────────────
const showCardFilesDialog = ref(false)
const cardFiles = ref([])
const cardFilesLoading = ref(false)
const selectedCardFiles = ref(new Set())

function cardFileThumbUrl(f) {
  const name = f.file_name || f.filename || ''
  const ext = name.split('.').pop()?.toLowerCase() || ''
  if (!IMAGE_EXTS.includes(ext) || !f.yandex_path) return null
  const path = f.yandex_path.replace(/^disk:/, '')
  const token = localStorage.getItem('access_token') || ''
  return `/api/v1/preview?yandex_path=${encodeURIComponent(path)}&token=${encodeURIComponent(token)}`
}

function cfFileKey(f) {
  return String(f.id || f.yandex_path || f.file_name || '')
}

function cfIconLabel(f) {
  const name = f.file_name || f.filename || ''
  const ext = ('.' + name.split('.').pop()?.toLowerCase()) || ''
  if (['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'].includes(ext)) return 'IMG'
  if (ext === '.pdf') return 'PDF'
  if (['.xls', '.xlsx', '.csv'].includes(ext)) return 'XLS'
  if (['.doc', '.docx', '.txt', '.rtf'].includes(ext)) return 'DOC'
  if (['.zip', '.rar', '.7z'].includes(ext)) return 'ZIP'
  if (f.file_type === 'folder') return 'DIR'
  return 'FILE'
}

function cfIconClass(f) {
  const lbl = cfIconLabel(f)
  return {
    'cf-ico-img': lbl === 'IMG',
    'cf-ico-pdf': lbl === 'PDF',
    'cf-ico-xls': lbl === 'XLS',
    'cf-ico-doc': lbl === 'DOC',
    'cf-ico-zip': lbl === 'ZIP',
    'cf-ico-dir': lbl === 'DIR',
    'cf-ico-file': !['IMG', 'PDF', 'XLS', 'DOC', 'ZIP', 'DIR'].includes(lbl),
  }
}

function toggleCardFile(f) {
  const key = cfFileKey(f)
  const next = new Set(selectedCardFiles.value)
  next.has(key) ? next.delete(key) : next.add(key)
  selectedCardFiles.value = next
}

async function sendSelectedCardFiles() {
  if (!selectedCardFiles.value.size || !chat.value) return
  showCardFilesDialog.value = false
  const keys = new Set(selectedCardFiles.value)
  selectedCardFiles.value = new Set()
  const toSend = cardFiles.value.filter(f => keys.has(cfFileKey(f)))

  const allImages = toSend.every(f => IMAGE_EXTS.includes((f.file_name || f.filename || '').split('.').pop()?.toLowerCase() || ''))
  const useGallery = toSend.length > 1 && allImages && !!chat.value.yandex_folder_path

  if (useGallery) {
    // Копируем файлы в изолированную подпапку чата на ЯД — галерея откроет только её
    const groupId = crypto.randomUUID()
    try {
      const { data: savedMsgs } = await api.post(`/api/v1/chats/${chat.value.id}/card-files-gallery`, {
        group_id: groupId,
        files: toSend.map(f => ({
          yandex_path: f.yandex_path,
          file_name: f.file_name || f.filename || 'файл',
          file_size: f.file_size || null,
        })),
      })
      // WS broadcast уже добавит сообщения, но добавим оптимистично если ещё нет
      for (const msg of savedMsgs) {
        if (!messages.value.some(m => m.id === msg.id)) {
          messages.value.push(msg)
        }
      }
      scrollToBottom()
    } catch {
      $q.notify({ type: 'negative', message: 'Не удалось отправить файлы в галерею' })
    }
  } else {
    // Одиночный файл или смешанные типы — отправляем как ссылки без копирования
    for (const f of toSend) {
      await insertCardFileLink(f, null)
    }
  }
}

const stageRuNames = {
  // Надзорные (идут первыми)
  supervision: 'Авторский надзор',
  supervision_stage: 'Этапы надзора',
  supervision_reports: 'Отчёты надзора',
  'Авторский надзор': 'Авторский надзор',
  'Этапы надзора': 'Этапы надзора',
  'Отчёты надзора': 'Отчёты надзора',
  'Выезды на объект': 'Выезды на объект',
  // Стадии проекта
  stage1: 'Стадия 1: Планировочное решение',
  stage2: 'Стадия 2',
  stage2_concept: 'Стадия 2: Концепция',
  stage2_3d: 'Стадия 2: 3D визуализация',
  stage3: 'Стадия 3: Чертежи',
  planning: 'Планировочное решение',
  concept: 'Концепция дизайна',
  working: 'Рабочие чертежи',
  visualization: '3D визуализация',
  // Вспомогательные
  measurement: 'Замеры',
  photo_documentation: 'Фотодокументация',
  documents: 'Документы',
  references: 'Референсы',
  questionnaire: 'Анкета клиента',
  acts: 'Акты',
  act_pr: 'Акт ПР',
  act_pr_signed: 'Акт ПР (подписан)',
  act_kd: 'Акт КД',
  act_kd_signed: 'Акт КД (подписан)',
  act_rch: 'Акт РЧ',
  act_rch_signed: 'Акт РЧ (подписан)',
  info_letters: 'Информационные письма',
  info_letter: 'Информационное письмо',
  info_letter_signed: 'Информационное письмо (подписано)',
  tech_task: 'Техническое задание',
  additional_agreement_signed: 'Доп. соглашение (подписано)',
}

const STAGE_ORDER_KEYS = [
  'measurement', 'stage1', 'stage2_concept', 'stage2_3d', 'stage3',
  'supervision', 'supervision_stage', 'supervision_reports',
  'Авторский надзор', 'Этапы надзора', 'Отчёты надзора', 'Выезды на объект',
  'tech_task', 'documents', 'acts', 'info_letters', 'references',
  'photo_documentation', 'questionnaire',
]

const groupedCardFiles = computed(() => {
  // Группировка по stage → по variation
  const byStage = {}
  for (const f of cardFiles.value) {
    const raw = f.stage || 'documents'
    if (!byStage[raw]) byStage[raw] = []
    byStage[raw].push(f)
  }

  const orderedKeys = [
    ...STAGE_ORDER_KEYS.filter(k => byStage[k]),
    ...Object.keys(byStage).filter(k => !STAGE_ORDER_KEYS.includes(k)),
  ]

  return orderedKeys.map(stageKey => {
    const files = byStage[stageKey]
    const stageLabel = stageRuNames[stageKey] || stageKey

    // Sub-group by variation
    const byVar = {}
    for (const f of files) {
      const v = f.variation ?? 1
      if (!byVar[v]) byVar[v] = []
      byVar[v].push(f)
    }
    const varNums = Object.keys(byVar).map(Number).sort((a, b) => a - b)
    const showVariants = varNums.length > 1 || (varNums.length === 1 && varNums[0] !== 1)

    const variants = varNums.map(v => ({
      varNum: v,
      files: byVar[v].slice().sort((a, b) => (a.file_order ?? 0) - (b.file_order ?? 0)),
    }))

    return { stage: stageLabel, stageKey, showVariants, variants }
  })
})

async function loadCardFiles() {
  const isSupervision = props.chatType === 'supervision'
  if (!isSupervision && !props.cardId) return
  if (isSupervision && !props.supervisionCardId) return
  if (cardFiles.value.length) return
  cardFilesLoading.value = true
  try {
    if (isSupervision) {
      const files = []
      // Файлы договора из карточки надзора
      const { data: svCard } = await api.get(`/api/v1/supervision/cards/${props.supervisionCardId}`)
      const contractId = svCard?.contract_id
      if (contractId) {
        try {
          const { data: cf } = await api.get(`/api/v1/files/contract/${contractId}`)
          files.push(...(Array.isArray(cf) ? cf : (cf?.items || [])))
        } catch {}
      }
      // Файлы основной CRM карточки (если передана)
      if (props.cardId) {
        try {
          const { data: crmCard } = await api.get(`/api/v1/crm/cards/${props.cardId}`)
          const crmContractId = crmCard?.contract_id
          if (crmContractId && crmContractId !== contractId) {
            const { data: cf2 } = await api.get(`/api/v1/files/contract/${crmContractId}`)
            files.push(...(Array.isArray(cf2) ? cf2 : (cf2?.items || [])))
          }
        } catch {}
      }
      // Папки выездов на объект
      try {
        const { data: visits } = await api.get(`/api/v1/supervision-visits/${props.supervisionCardId}/visits`)
        const vList = Array.isArray(visits) ? visits : []
        for (const v of vList) {
          if (v.visit_yandex_folder) {
            files.push({
              id: `visit-${v.id}`,
              file_name: `Выезд: ${v.stage_name || ''} (${v.visit_date || ''})`,
              yandex_path: v.visit_yandex_folder,
              stage: 'Выезды на объект',
              file_type: 'folder',
            })
          }
        }
      } catch {}
      cardFiles.value = files
    } else {
      const { data: card } = await api.get(`/api/v1/crm/cards/${props.cardId}`)
      const contractId = card?.contract_id
      if (contractId) {
        const { data: files } = await api.get(`/api/v1/files/contract/${contractId}`)
        cardFiles.value = Array.isArray(files) ? files : (files?.items || [])
      }
      // Файлы правок из папок workflow (revision_file_path)
      try {
        const { data: states } = await api.get(`/api/v1/crm/cards/${props.cardId}/workflow/state`)
        const statesList = Array.isArray(states) ? states : []
        const revFolders = [...new Set(statesList.filter(s => s.revision_file_path).map(s => s.revision_file_path))]
        for (const folder of revFolders) {
          try {
            const { data: fl } = await api.get('/api/v1/files/list', { params: { folder_path: folder } })
            const items = fl?.files || []
            const revStage = statesList.find(s => s.revision_file_path === folder)?.stage_name || 'стадия'
            for (const item of items) {
              if (item.type !== 'file') continue
              cardFiles.value.push({
                id: `rev-${item.path}`,
                file_name: item.name,
                yandex_path: item.path,
                stage: `Правки: ${revStage}`,
                file_type: 'file',
              })
            }
          } catch {}
        }
      } catch {}
    }
  } catch {
    cardFiles.value = []
  } finally {
    cardFilesLoading.value = false
  }
}

async function insertCardFileLink(f, groupId = null) {
  if (!chat.value) return

  const name = f.file_name || f.filename || 'файл'
  const ext = name.split('.').pop()?.toLowerCase() || ''
  const isImg = IMAGE_EXTS.includes(ext)
  const msgType = f.file_type === 'folder' ? 'file' : (isImg ? 'image' : 'file')

  let fileUrl = f.public_link || ''
  if (!fileUrl && f.yandex_path) {
    const clean = f.yandex_path.startsWith('disk:') ? f.yandex_path.slice(5) : f.yandex_path
    fileUrl = 'https://disk.yandex.ru/client/disk' + encodeURIComponent(clean).replace(/%2F/g, '/')
    // Для изображений пытаемся получить прямую публичную ссылку ЯД
    if (isImg) {
      try {
        const { data } = await api.get(`/api/v1/files/public-link?path=${encodeURIComponent(f.yandex_path)}`)
        if (data?.public_link) fileUrl = data.public_link
      } catch {}
    }
  }

  const tempId = `temp_${Date.now()}_${Math.random()}`
  messages.value.push({
    id: tempId,
    sender_employee_id: authStore.user?.id,
    sender_display_name: authStore.user?.full_name || 'Вы',
    message_type: msgType,
    content: null,
    group_id: groupId,
    file_url: fileUrl,
    file_name: name,
    file_size: f.file_size || null,
    yandex_path: f.yandex_path || null,
    is_deleted: false,
    is_edited: false,
    is_pinned: false,
    created_at: new Date().toISOString(),
    _uploading: true,
    _previewUrl: isImg ? fileUrl : null,
  })
  scrollToBottom()

  try {
    const { data: savedMsg } = await api.post(`/api/v1/chats/${chat.value.id}/messages`, {
      message_type: msgType,
      file_url: fileUrl,
      file_name: name,
      file_size: f.file_size || null,
      yandex_path: f.yandex_path || null,
      content: null,
      group_id: groupId,
    })
    const idx = messages.value.findIndex(m => m.id === tempId)
    if (idx !== -1) {
      const alreadyAdded = messages.value.some(m => m.id === savedMsg.id)
      alreadyAdded ? messages.value.splice(idx, 1) : messages.value.splice(idx, 1, savedMsg)
    }
  } catch {
    messages.value = messages.value.filter(m => m.id !== tempId)
    $q.notify({ type: 'negative', message: 'Не удалось отправить файл' })
  }
}


// Закреплённые сообщения (до 10, как в Telegram)
const pinnedMsgs = ref([])
const pinnedIdx = ref(0)
// Ожидающие отправки файлы + подпись + превью
const pendingFiles = ref([])
const pendingPreviews = ref([])
const pendingCaption = ref('')
// Диалог пересылки
const showForwardDialog = ref(false)
const replyingTo = ref(null)

const forwardingMsgs = ref([])  // массив: для галереи — все фото, для одиночного — [msg]
const forwardTargetChats = ref([])
const loadingForwardChats = ref(false)
const selectedForwardChatId = ref(null)
const sendingForward = ref(false)
const forwardSearchQuery = ref('')
const filteredForwardChats = computed(() => {
  if (!forwardSearchQuery.value.trim()) return forwardTargetChats.value
  const q = forwardSearchQuery.value.toLowerCase()
  return forwardTargetChats.value.filter(c => (c.title || '').toLowerCase().includes(q))
})
const { can } = usePermission()
const canShowLastLogin = computed(() => can('chat.members.show_last_login'))

function fmtLastLogin(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getDate()}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const showMembers = ref(false)

// Поиск по сообщениям
const showSearch = ref(false)
const searchQuery = ref('')
const searchResults = ref([])
const searchLoading = ref(false)
let _searchTimer = null

function handleSearch(val) {
  clearTimeout(_searchTimer)
  if (!val || !val.trim()) { searchResults.value = []; return }
  searchLoading.value = true
  _searchTimer = setTimeout(async () => {
    try {
      if (!chat.value) return
      const { data } = await api.get(`/api/v1/chats/${chat.value.id}/messages/search`, { params: { q: val, limit: 20 } })
      searchResults.value = Array.isArray(data) ? data : []
    } catch { searchResults.value = [] } finally { searchLoading.value = false }
  }, 400)
}

async function goToSearchResult(msg) {
  showSearch.value = false
  searchQuery.value = ''
  searchResults.value = []
  await nextTick()
  await new Promise(r => setTimeout(r, 100))
  const container = messagesEl.value
  if (!container) return
  const el = container.querySelector(`#msg-${msg.id}`) || container.querySelector(`[data-msg-id="${msg.id}"]`)
  if (!el) return
  el.scrollIntoView({ block: 'center', behavior: 'instant' })
  el.classList.add('msg-highlight')
  setTimeout(() => el.classList.remove('msg-highlight'), 1500)
}

// Голосовые сообщения — воспроизведение
const voicePlaying = reactive({})
const voiceCurrent = reactive({})
const _voiceRefs = {}

// Голосовая запись
const isRecording = ref(false)
const recordSeconds = ref(0)
let _mediaRecorder = null
let _audioChunks = []
let _recordTimer = null
let _cancelRequested = false
let _holdTimer = null
let _pressStartTime = 0

function fmtDuration(sec) {
  const s = parseInt(sec) || 0
  const m = Math.floor(s / 60)
  return `${m}:${String(s % 60).padStart(2, '0')}`
}

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
    if (_cancelRequested) { stream.getTracks().forEach(t => t.stop()); return }
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
  if (!chat.value) return
  const fd = new FormData()
  fd.append('file', file)
  fd.append('message_type', 'voice')
  fd.append('caption', String(recordSeconds.value))
  const dismiss = $q.notify({ group: false, spinner: true, message: 'Отправка голосового…', timeout: 0 })
  try {
    const { data } = await api.post(`/api/v1/chats/${chat.value.id}/files`, fd, {
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
  return 'media-grid-dynamic'
}

function galleryCols(count) {
  // Для thumbnail-секции: предпочитаем 0 остаток (полные ряды),
  // затем остаток ≥ 2, избегаем остаток 1 (одинокое фото).
  // maxCols = count: разрешаем 1 ряд для малых count.
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

function galleryBubbleStyle() {
  return 'min-width: 0; width: min(60vw, 380px); max-width: min(60vw, 380px)'
}

function galleryGridStyle(count) {
  if (count >= 2) return 'display: grid; grid-template-columns: 1fr 1fr; gap: 2px;'
  return undefined
}

function galleryItemContainerStyle(count, index) {
  if (count === 3 && index === 2) return 'display: block; overflow: hidden; cursor: pointer; grid-column: span 2'
  return 'display: block; overflow: hidden; cursor: pointer'
}

// Сетка thumbnail-секции (фото 3+ в группе)
function galleryThumbGridStyle(count) {
  const thumbCount = count - 2
  if (thumbCount <= 0) return undefined
  const cols = galleryCols(thumbCount)
  return `display: grid; grid-template-columns: repeat(${cols}, 1fr); gap: 2px;`
}

// Span для последнего неполного ряда thumbnail-секции
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

function galleryImgStyle(count) {
  const base = 'width: 100%; display: block;'
  if (count <= 1) return `${base} height: clamp(200px, 56vw, 320px);`
  if (count === 2) return `${base} height: 155px;`
  if (count === 3) return `${base} height: 130px;`
  return base
}

function groupCaption(msgs) {
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].content) return msgs[i].content
  }
  return ''
}
const chatMembers = ref([])
// null = секция не показывалась; [] = загружено, но все уже в чате
const cardEmployees = ref(null)
const loadingCardEmployees = ref(false)
const addingMemberId = ref(null)
const removingMemberId = ref(null)

// Редактирование сообщений
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

function recalcHeight() {
  // Двойной requestAnimationFrame — ждём стабилизации layout
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      if (!chatContainerEl.value) return
      const rect = chatContainerEl.value.getBoundingClientRect()
      const topOffset = Math.max(0, rect.top)
      // Учитываем нижнюю панель навигации
      const footer = document.querySelector('.q-footer')
      const footerH = footer ? footer.offsetHeight : 0
      const vh = window.visualViewport?.height ?? window.innerHeight
      const h = Math.max(320, vh - topOffset - footerH - 4)
      containerHeight.value = h + 'px'
    })
  })
}

const clientLink = computed(() => {
  if (props.chatType !== 'client' || !chat.value?.client_access_token) return ''
  return `${window.location.origin}/c/${chat.value.client_access_token}`
})

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

function isForwarded(msg) {
  return typeof msg.sender_display_name === 'string' && msg.sender_display_name.includes('(переслано)')
}

const QUICK_EMOJIS = ['👍', '❤️', '😂', '😮', '😢', '🔥']

async function sendReaction(msg, emoji) {
  if (!chat.value) return
  try {
    const { data } = await api.post(`/api/v1/chats/${chat.value.id}/messages/${msg.id}/react`, { emoji })
    const idx = messages.value.findIndex(m => m.id === msg.id)
    if (idx !== -1) {
      const c = messagesEl.value
      const atBottom = !c || (c.scrollHeight - c.scrollTop - c.clientHeight < 50)
      messages.value[idx] = { ...messages.value[idx], reactions: data.reactions }
      if (atBottom) nextTick(() => requestAnimationFrame(() => { if (c) c.scrollTop = c.scrollHeight }))
    }
  } catch (e) { console.warn('[reaction]', e) }
}

function isOwnReaction(msg, emoji) {
  const reactors = msg.reactions?.[emoji] || []
  return reactors.some(r => r.employee_id === authStore.user?.id)
}

function imgStreamUrl(msg) {
  if (msg._previewUrl) return msg._previewUrl  // локальный blob во время загрузки
  if (!msg.yandex_path) return ''
  const path = msg.yandex_path.replace(/^disk:/, '')
  const token = localStorage.getItem('access_token') || ''
  return `/api/v1/preview?yandex_path=${encodeURIComponent(path)}&token=${encodeURIComponent(token)}`
}

function isPdf(msg) {
  return msg.file_name?.toLowerCase().endsWith('.pdf')
}

function loadPdfThumbnail(msg) {
  if (pdfThumbnails.value[msg.id]) return
  if (!isPdf(msg) || !msg.yandex_path) return
  const path = msg.yandex_path.replace(/^disk:/, '')
  const token = localStorage.getItem('access_token') || ''
  pdfThumbnails.value[msg.id] = `/api/v1/preview?yandex_path=${encodeURIComponent(path)}&token=${encodeURIComponent(token)}`
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
    const el = document.getElementById(`msg-${id}`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      el.classList.add('msg-highlight')
      setTimeout(() => el.classList.remove('msg-highlight'), 1500)
    }
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

async function loadChat() {
  const isSupervision = props.chatType === 'supervision'
  const idKey = isSupervision ? 'supervision_card_id' : 'crm_card_id'
  const idVal = isSupervision ? props.supervisionCardId : props.cardId
  if (!idVal) return
  loading.value = true
  try {
    const resolvedType = props.chatType === 'supervision' ? 'employee' : props.chatType
    const { data } = await api.get('/api/v1/chats/', {
      params: { chat_type: resolvedType, [idKey]: idVal },
    })
    const list = Array.isArray(data) ? data : (data.items || [])
    if (list.length > 0) {
      await openChat(list[0].id)
    }
  } catch (e) {
    console.error('[InlineChatRoom] loadChat:', e)
  } finally {
    loading.value = false
  }
}

async function openChat(chatId) {
  try {
    const { data } = await api.get(`/api/v1/chats/${chatId}`)
    chat.value = data
    messages.value = data.messages || []
    chatMembers.value = data.members || []
    firstUnreadId.value = data.first_unread_message_id || null
    pinnedMsgs.value = data.pinned_messages || []
    pinnedIdx.value = 0
    scrollToFirstUnread()
    chatUnreadStore.markChatRead(chatId)

    messages.value
      .filter(m => isPdf(m) && m.yandex_path && !m._uploading)
      .forEach(m => loadPdfThumbnail(m))

    // Для чата сотрудников загрузить клиентский чат (для пересылки)
    if (props.chatType === 'employee' && data.crm_card_id) {
      loadClientChat(data.crm_card_id)
    }
    // Для чата надзора загрузить ссылку приглашения
    if (props.chatType === 'supervision') {
      loadSupervisionLink(chatId)
    }

    const token = localStorage.getItem('access_token')
    if (token) {
      connectEmployee(chatId, token, {
        onMessage: (msg) => {
          const exists = messages.value.some(m => m.id === msg.id)
          if (!exists) {
            messages.value.push(msg)
            scrollToBottom()
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
          if (!chat.value) return
          try {
            const { data } = await api.get(`/api/v1/chats/${chat.value.id}`)
            chatMembers.value = data.members || []
          } catch { }
        },
        onMemberRemoved: (evt) => {
          if (evt.member_id) {
            chatMembers.value = chatMembers.value.filter(m => m.id !== evt.member_id)
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

    if (messages.value.length) {
      const lastId = messages.value[messages.value.length - 1].id
      // REST гарантирует доставку — WS может быть не открыт ещё в момент вызова
      api.post(`/api/v1/chats/${chat.value.id}/messages/${lastId}/read`).catch(() => {})
    }
  } catch (e) {
    console.error('[InlineChatRoom] openChat:', e)
  }
}

async function loadClientChat(cardId) {
  try {
    const { data } = await api.get('/api/v1/chats/', {
      params: { chat_type: 'client', crm_card_id: cardId },
    })
    const list = Array.isArray(data) ? data : (data.items || [])
    if (list.length > 0) clientChatId.value = list[0].id
  } catch {
    // Нет клиентского чата
  }
}

// Открытие диалога участников — сразу грузим сотрудников карточки
async function onMembersDialogOpen() {
  if (!chat.value) return
  const isSupervision = props.chatType === 'supervision'
  const sourceId = isSupervision ? props.supervisionCardId : props.cardId
  if (!sourceId) return
  cardEmployees.value = null
  loadingCardEmployees.value = true
  try {
    // Свежий статус участников (is_online, last_login)
    const { data: chatData } = await api.get(`/api/v1/chats/${chat.value.id}`)
    chatMembers.value = chatData.members || []

    const emps = new Map()
    if (isSupervision) {
      // Исполнители из карточки надзора
      const { data } = await api.get(`/api/v1/supervision/cards/${sourceId}`)
      const roles = [
        { id: data.senior_manager_id, name: data.senior_manager_name, role: 'Старший менеджер' },
        { id: data.dan_id, name: data.dan_name, role: 'ДАН' },
      ]
      for (const r of roles) {
        if (r.id) emps.set(r.id, { name: r.name || `Сотрудник #${r.id}`, role: r.role })
      }
    } else {
      // Исполнители из CRM карточки
      const { data } = await api.get(`/api/v1/crm/cards/${sourceId}`)
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
          const stageName = se.stage_name || 'Исполнитель'
          const existing = emps.get(se.executor_id)
          if (existing) {
            // Сотрудник назначен на несколько стадий — объединяем короткие номера
            const shortStage = (s) => { const m = s.match(/^(Стадия\s*\d+)/i); return m ? m[1] : s }
            const combined = shortStage(existing.role) + ' + ' + shortStage(stageName)
            emps.set(se.executor_id, { name: existing.name, role: combined })
          } else {
            emps.set(se.executor_id, { name: se.executor_name || `Сотрудник #${se.executor_id}`, role: stageName })
          }
        }
      }
    }
    const memberIds = new Set(chatMembers.value.filter(m => m.employee_id).map(m => m.employee_id))
    cardEmployees.value = [...emps.entries()]
      .filter(([id]) => !memberIds.has(id))
      .map(([id, info]) => ({ id, name: info.name, role: info.role }))
  } catch {
    cardEmployees.value = []
  } finally {
    loadingCardEmployees.value = false
  }
}

async function addMemberToChat(emp) {
  if (addingMemberId.value || !chat.value) return
  addingMemberId.value = emp.id
  try {
    await api.post(`/api/v1/chats/${chat.value.id}/members`, { employee_id: emp.id })
    // Обновляем список участников чата
    const { data } = await api.get(`/api/v1/chats/${chat.value.id}`)
    chatMembers.value = data.members || []
    // Убираем из списка доступных
    cardEmployees.value = cardEmployees.value.filter(e => e.id !== emp.id)
    $q.notify({ type: 'positive', message: `${emp.name} добавлен в чат` })
  } catch (e) {
    const msg = e.response?.data?.detail || 'Ошибка добавления'
    $q.notify({ type: 'negative', message: String(msg) })
  } finally {
    addingMemberId.value = null
  }
}

async function removeMember(m) {
  if (removingMemberId.value || !chat.value) return
  const name = m.display_name || 'Участник'
  const confirmed = await new Promise(resolve => {
    $q.dialog({
      title: 'Удалить из чата?',
      message: `Удалить «${name}» из чата?`,
      ok: { label: 'Удалить', color: 'negative', flat: true },
      cancel: { label: 'Отмена', flat: true },
    }).onOk(() => resolve(true)).onCancel(() => resolve(false))
  })
  if (!confirmed) return
  removingMemberId.value = m.id
  try {
    await api.delete(`/api/v1/chats/${chat.value.id}/members/${m.id}`)
    chatMembers.value = chatMembers.value.filter(mb => mb.id !== m.id)
    $q.notify({ type: 'positive', message: `${name} удалён из чата` })
  } catch (e) {
    const msg = e.response?.data?.detail || 'Ошибка удаления'
    $q.notify({ type: 'negative', message: String(msg) })
  } finally {
    removingMemberId.value = null
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
      .filter(c => c.id !== chat.value?.id)
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
      await api.post(`/api/v1/chats/${chat.value.id}/forward/${selectedForwardChatId.value}`, { msg_id: forwardingMsgs.value[0].id })
    } else {
      await api.post(`/api/v1/chats/${chat.value.id}/forward-group/${selectedForwardChatId.value}`, { msg_ids: forwardingMsgs.value.map(m => m.id) })
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

async function createChat() {
  const isSupervision = props.chatType === 'supervision'
  const idVal = isSupervision ? props.supervisionCardId : props.cardId
  if (!idVal) return
  creating.value = true
  try {
    const resolvedType = props.chatType === 'supervision' ? 'employee' : props.chatType
    const payload = {
      chat_type: resolvedType,
      ...(isSupervision
        ? { supervision_card_id: idVal }
        : { crm_card_id: idVal }),
    }
    const { data } = await api.post('/api/v1/chats/', payload)
    await openChat(data.id)
    if (chat.value) {
      $q.notify({ type: 'positive', message: 'Чат создан' })
    } else {
      // openChat может упасть с 403 если пользователь ещё не добавлен в участники
      await loadChat()
      $q.notify({ type: 'positive', message: 'Чат создан' })
    }
  } catch (e) {
    const msg = e.response?.data?.detail || 'Ошибка создания чата'
    $q.notify({ type: 'negative', message: msg })
  } finally {
    creating.value = false
  }
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
  if (!editContent.value.trim() || !chat.value) return
  savingEdit.value = true
  try {
    const { data: updated } = await api.patch(
      `/api/v1/chats/${chat.value.id}/messages/${editingMsgId.value}`,
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
  if (deletingMsgId.value || !chat.value) return
  deletingMsgId.value = msg.id
  try {
    await api.delete(`/api/v1/chats/${chat.value.id}/messages/${msg.id}`)
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
  if (!selectedDestination.value || !chat.value?.crm_card_id) return
  if (!STAGE_KEYS.has(selectedDestination.value)) {
    await confirmCopyToCard()
    return
  }
  loadingVariations.value = true
  try {
    const { data } = await api.get(`/api/v1/chats/${chat.value.id}/card-stage-variations`, {
      params: { crm_card_id: chat.value.crm_card_id, destination: selectedDestination.value },
    })
    stageVariations.value = data.variations || []
    nextVariation.value = data.next_variation || 1
    // По умолчанию: если есть вариации — выбираем первую, иначе — новая (null)
    selectedVariation.value = stageVariations.value.length > 0 ? stageVariations.value[0].variation : null
    copyStep.value = 2
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Ошибка загрузки вариаций' })
  } finally {
    loadingVariations.value = false
  }
}

async function confirmCopyToCard() {
  if (!selectedDestination.value || !copyToCardMsg.value || !chat.value?.crm_card_id) return
  copyingToCard.value = true
  try {
    const body = { crm_card_id: chat.value.crm_card_id, destination: selectedDestination.value }
    if (STAGE_KEYS.has(selectedDestination.value) && selectedVariation.value !== null) {
      body.variation = selectedVariation.value
    }
    await api.post(
      `/api/v1/chats/${chat.value.id}/messages/${copyToCardMsg.value.id}/copy-to-card`,
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

function removePendingFile(idx) {
  const url = pendingPreviews.value[idx]
  if (url) URL.revokeObjectURL(url)
  pendingFiles.value = pendingFiles.value.filter((_, i) => i !== idx)
  pendingPreviews.value = pendingPreviews.value.filter((_, i) => i !== idx)
  if (!pendingFiles.value.length) pendingCaption.value = ''
}

// Отправить pending файлы (с подписью и group_id для нескольких изображений)
async function sendWithAttachment() {
  const files = pendingFiles.value
  if (!files.length || !chat.value) return
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

async function _uploadSingleFile(file, groupId = null, caption = null) {
  if (!chat.value) return
  const ext = file.name.split('.').pop()?.toLowerCase() || ''
  const msgType = IMAGE_EXTS.includes(ext) ? 'image' : 'file'
  const previewUrl = msgType === 'image' ? URL.createObjectURL(file) : null
  const isPdfUpload = ext === 'pdf'

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
    _previewUrl: previewUrl,
  })
  if (isPdfUpload) {
    getPdfThumbnail(file).then(thumb => {
      if (thumb) {
        const m = messages.value.find(m2 => m2.id === tempId)
        if (m) m._previewUrl = thumb
      }
    })
  }
  scrollToBottom()

  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('message_type', msgType)
    if (groupId) formData.append('group_id', groupId)
    if (caption) formData.append('caption', caption)
    const { data: savedMsg } = await api.post(`/api/v1/chats/${chat.value.id}/files`, formData, {
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
  } catch {
    messages.value = messages.value.filter(m => m.id !== tempId)
    throw new Error(file.name)
  } finally {
    if (previewUrl) URL.revokeObjectURL(previewUrl)
  }
}

// ── Pin / Unpin ────────────────────────────────────────────────────────────
function confirmUnpin(msg) {
  $q.dialog({
    title: 'Открепить сообщение?',
    message: 'Сообщение будет удалено из закреплённых.',
    cancel: { label: 'Отмена', flat: true },
    ok: { label: 'Открепить', color: 'orange-8', unelevated: true },
  }).onOk(() => togglePin(msg))
}

async function togglePin(msg) {
  if (!chat.value) return
  try {
    const { data } = await api.post(`/api/v1/chats/${chat.value.id}/messages/${msg.id}/pin`)
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
  scrollToMsg(pinnedMsgs.value[pinnedIdx.value]?.id)
}

async function openInGallery(msg) {
  if (!msg?.id || !chat.value?.id) return
  try {
    const { data } = await api.post(`/api/v1/chats/${chat.value.id}/messages/${msg.id}/gallery-link`)
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

function imgStreamFullUrl(msg) {
  if (!msg.yandex_path) return imgStreamUrl(msg)
  const path = msg.yandex_path.replace(/^disk:/, '')
  const token = localStorage.getItem('access_token') || ''
  return `/api/v1/files/stream?yandex_path=${encodeURIComponent(path)}&token=${encodeURIComponent(token)}`
}

function openImgGallery(msgs, clickedIdx) {
  galleryImages.value = msgs.map(m => ({
    src: imgStreamFullUrl(m),
    filename: m.file_name || 'Изображение',
    url: m.file_url || null,
  }))
  galleryStartIndex.value = clickedIdx
  galleryVisible.value = true
}


function copyClientLink() {
  if (!clientLink.value) return
  navigator.clipboard.writeText(clientLink.value).then(() => {
    $q.notify({ type: 'positive', message: 'Ссылка скопирована' })
  }).catch(() => {})
}

const showClientAccess = ref(false)
const sendingInvite = ref(false)
const clientAccessInviteLink = ref('')
const creatingClientLink = ref(false)

async function sendEmailInvite() {
  if (!props.cardId) return
  sendingInvite.value = true
  try {
    const { data } = await crmApi.inviteClientToChat(props.cardId)
    $q.notify({ type: 'positive', message: data.message || 'Приглашение отправлено' })
  } catch (e) {
    const msg = e.response?.data?.detail || 'Ошибка отправки приглашения'
    $q.notify({ type: 'negative', message: msg })
  } finally {
    sendingInvite.value = false
  }
}

async function createClientInviteLink() {
  if (!chat.value?.id) return
  creatingClientLink.value = true
  try {
    const { data } = await api.post(`/api/v1/chats/${chat.value.id}/invite-links`)
    clientAccessInviteLink.value = `${window.location.origin}/c/${data.access_token}`
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Ошибка создания ссылки' })
  } finally {
    creatingClientLink.value = false
  }
}

function copyClientAccessInviteLink() {
  if (!clientAccessInviteLink.value) return
  navigator.clipboard.writeText(clientAccessInviteLink.value).then(() => {
    $q.notify({ type: 'positive', message: 'Ссылка скопирована' })
  }).catch(() => {})
}

onMounted(() => {
  loadChat()
  nextTick(() => {
    recalcHeight()
    window.addEventListener('resize', recalcHeight)
    window.visualViewport?.addEventListener('resize', recalcHeight)
    document.addEventListener('scroll', recalcHeight, true)
  })
})

// Пересчитываем высоту когда чат загружается
watch(chat, (newVal) => {
  if (!newVal) return
  nextTick(recalcHeight)
  setTimeout(recalcHeight, 150)
  setTimeout(recalcHeight, 500)
})

onUnmounted(() => {
  disconnect()
  window.removeEventListener('resize', recalcHeight)
  window.visualViewport?.removeEventListener('resize', recalcHeight)
  document.removeEventListener('scroll', recalcHeight, true)
  if (typingTimer) clearTimeout(typingTimer)
})
</script>

<style scoped>
.bubble-own {
  background: #E8F5E9;
  border-radius: 12px 12px 2px 12px;
  padding: 6px 10px;
  max-width: 80%;
}
.bubble-forwarded {
  background: #EEEEEE !important;
}
.bubble-other {
  background: #fff;
  border-radius: 12px 12px 12px 2px;
  padding: 6px 10px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
  max-width: 80%;
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
/* Медиа-галерея (Telegram-стиль) */
.media-grid-1 { display: block; }
.media-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px;
}
.media-grid-3 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px;
}
/* media-grid-dynamic — колонки задаются через galleryGridStyle() */
.media-grid-dynamic { overflow: hidden; }
@keyframes msg-highlight-pulse {
  0% { background: rgba(255, 214, 0, 0.45); }
  100% { background: transparent; }
}
.msg-highlight { animation: msg-highlight-pulse 1.5s ease-out; border-radius: 8px; }
.gallery-open-btn :deep(.q-focus-helper) { display: none; }
.reaction-chip {
  display: inline-flex; align-items: center; gap: 3px; padding: 2px 7px;
  border-radius: 12px; border: 1px solid #E0E0E0; background: #F5F5F5;
  font-size: 13px; cursor: pointer; line-height: 1.4;
}
.reaction-chip--own { background: #E3F2FD; border-color: #90CAF9; }
.react-quick-btn { font-size: 20px; background: none; border: none; cursor: pointer; padding: 2px 5px; border-radius: 6px; line-height: 1.3; transition: background 0.15s; }
.react-quick-btn:hover { background: #F0F0F0; }
.react-quick-btn--active { background: #E3F2FD; }
.gallery-open-btn :deep(.q-btn__content) { gap: 3px; }
/* Файловый диалог карточки — стиль десктопа */
.cf-stage-hdr {
  padding: 4px 10px; font-size: 11px; font-weight: 700;
  background: #E8EEF6; color: #1a3a6b;
  border-bottom: 1px solid #d0daea;
}
.cf-var-hdr {
  padding: 3px 20px; font-size: 10px; font-style: italic;
  background: #F3F3F3; color: #666;
  border-bottom: 1px solid #e8e8e8;
}
.cf-file-row {
  display: flex; align-items: center; gap: 10px;
  padding: 4px 8px; cursor: pointer; min-height: 54px;
  border-bottom: 1px solid #F0F0F0;
  transition: background 0.1s;
}
.cf-file-row:hover { background: #f5f5f5; }
.cf-file-row--checked { background: #FFF8DC; }
.cf-file-row:last-child { border-bottom: none; }
.cf-thumb {
  width: 56px; height: 42px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  border-radius: 3px; overflow: hidden;
}
.cf-thumb-img { width: 56px; height: 42px; object-fit: cover; }
.cf-thumb-icon {
  width: 56px; height: 42px; display: flex; align-items: center;
  justify-content: center; font-size: 10px; font-weight: 700;
  border-radius: 3px;
}
.cf-ico-img  { background: #C8E6C9; color: #2E7D32; }
.cf-ico-pdf  { background: #FFCDD2; color: #B71C1C; }
.cf-ico-xls  { background: #C8E6C9; color: #1B5E20; }
.cf-ico-doc  { background: #BBDEFB; color: #0D47A1; }
.cf-ico-zip  { background: #E1BEE7; color: #4A148C; }
.cf-ico-dir  { background: #FFF9C4; color: #F57F17; }
.cf-ico-file { background: #E0E0E0; color: #424242; }
.cf-fname {
  flex: 1; min-width: 0; font-size: 12px; color: #333;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.cf-btn-cancel, .cf-btn-send {
  height: 28px; border-radius: 4px; padding: 0 14px;
  font-size: 12px; cursor: pointer; border: none; outline: none;
}
.cf-btn-cancel {
  background: #fff; border: 1px solid #d9d9d9; color: #333;
}
.cf-btn-cancel:hover { background: #f5f5f5; }
.cf-btn-send {
  background: #ffd93c; color: #333; font-weight: 700; margin-left: 8px;
}
.cf-btn-send:hover { background: #f5c800; }
.cf-btn-send--disabled { background: #f0f0f0 !important; color: #aaa !important; cursor: default; }
</style>
