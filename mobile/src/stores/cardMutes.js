import { defineStore } from 'pinia'
import { ref } from 'vue'
import { cardMutesApi } from 'src/services/api'

export const useCardMutesStore = defineStore('cardMutes', () => {
  const mutedCrm = ref(new Set())
  const mutedSupervision = ref(new Set())
  const loaded = ref(false)

  function isMuted(entityType, entityId) {
    if (entityType === 'crm_card') return mutedCrm.value.has(entityId)
    if (entityType === 'supervision_card') return mutedSupervision.value.has(entityId)
    return false
  }

  async function load() {
    try {
      const { data } = await cardMutesApi.getMyMutes()
      mutedCrm.value = new Set(data.crm_cards || [])
      mutedSupervision.value = new Set(data.supervision_cards || [])
      loaded.value = true
    } catch {
      // Молча — не критично
    }
  }

  async function toggleMute(entityType, entityId) {
    const wasMuted = isMuted(entityType, entityId)
    // Оптимистичное обновление
    if (entityType === 'crm_card') {
      if (wasMuted) mutedCrm.value.delete(entityId)
      else mutedCrm.value.add(entityId)
    } else if (entityType === 'supervision_card') {
      if (wasMuted) mutedSupervision.value.delete(entityId)
      else mutedSupervision.value.add(entityId)
    }
    try {
      if (wasMuted) {
        await cardMutesApi.unmute(entityType, entityId)
      } else {
        await cardMutesApi.mute(entityType, entityId)
      }
    } catch {
      // Откатываем при ошибке
      if (entityType === 'crm_card') {
        if (wasMuted) mutedCrm.value.add(entityId)
        else mutedCrm.value.delete(entityId)
      } else if (entityType === 'supervision_card') {
        if (wasMuted) mutedSupervision.value.add(entityId)
        else mutedSupervision.value.delete(entityId)
      }
    }
  }

  return { mutedCrm, mutedSupervision, loaded, isMuted, load, toggleMute }
})
