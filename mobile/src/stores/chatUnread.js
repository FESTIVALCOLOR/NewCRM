import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

import { api } from 'src/boot/axios'

/** Обновить бейдж иконки PWA (Web App Badging API) */
function _setAppBadge(count) {
  if (!('setAppBadge' in navigator)) return
  if (count > 0) {
    navigator.setAppBadge(count).catch(() => {})
  } else {
    navigator.clearAppBadge().catch(() => {})
  }
}

export const useChatUnreadStore = defineStore('chatUnread', () => {
  const employeeChats = ref([])
  const clientChats = ref([])

  const totalEmployeeUnread = computed(() =>
    employeeChats.value.reduce((s, c) => s + (c.unread_count || 0), 0),
  )
  const totalClientUnread = computed(() =>
    clientChats.value.reduce((s, c) => s + (c.unread_count || 0), 0),
  )
  const totalUnread = computed(() => totalEmployeeUnread.value + totalClientUnread.value)

  /** Сумма непрочитанных для конкретной карточки CRM (employee + client) */
  function unreadByCardId(cardId) {
    const emp = employeeChats.value.find(c => c.crm_card_id === cardId)
    const cli = clientChats.value.find(c => c.crm_card_id === cardId)
    return (emp?.unread_count || 0) + (cli?.unread_count || 0)
  }

  /** Непрочитанных для конкретной карточки + конкретного типа чата */
  function unreadByCardAndType(cardId, chatType) {
    const list = chatType === 'client' ? clientChats.value : employeeChats.value
    const chat = list.find(c => c.crm_card_id === cardId)
    return chat?.unread_count || 0
  }

  async function fetchUnreadCounts() {
    try {
      const [empResp, cliResp] = await Promise.all([
        api.get('/api/v1/chats', { params: { chat_type: 'employee' } }),
        api.get('/api/v1/chats', { params: { chat_type: 'client' } }),
      ])
      employeeChats.value = Array.isArray(empResp.data) ? empResp.data : (empResp.data.items || [])
      clientChats.value = Array.isArray(cliResp.data) ? cliResp.data : (cliResp.data.items || [])
    } catch {
      // Тихо — некритично
    }
  }

  /** Обнулить непрочитанные для чата (вызывается при открытии чата) */
  function markChatRead(chatId) {
    const ec = employeeChats.value.find(c => c.id === chatId)
    if (ec) ec.unread_count = 0
    const cc = clientChats.value.find(c => c.id === chatId)
    if (cc) cc.unread_count = 0
  }

  /** Увеличить непрочитанные (при получении нового WS-сообщения вне активного чата) */
  function incrementUnread(chatId) {
    const ec = employeeChats.value.find(c => c.id === chatId)
    if (ec) ec.unread_count = (ec.unread_count || 0) + 1
    const cc = clientChats.value.find(c => c.id === chatId)
    if (cc) cc.unread_count = (cc.unread_count || 0) + 1
  }

  // Синхронизировать бейдж иконки PWA при изменении общего числа непрочитанных
  watch(totalUnread, (count) => {
    _setAppBadge(count)
  }, { immediate: true })

  return {
    employeeChats,
    clientChats,
    totalEmployeeUnread,
    totalClientUnread,
    totalUnread,
    unreadByCardId,
    unreadByCardAndType,
    fetchUnreadCounts,
    markChatRead,
    incrementUnread,
  }
})
