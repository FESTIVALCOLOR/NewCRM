<template>
  <Transition name="pwa-slide">
    <div v-if="show" :class="['pwa-banner', inline ? 'pwa-banner--inline' : 'pwa-banner--fixed']">
      <div class="pwa-banner__inner">
        <q-icon name="add_to_home_screen" size="22px" color="green-7" class="pwa-banner__icon" />

        <div class="pwa-banner__text">
          <div style="font-size: 13px; font-weight: 600; line-height: 1.3; color: #222">
            Добавить на главный экран
          </div>
          <!-- iOS: ручные инструкции (Safari Share → «На экран "Домой"») -->
          <div v-if="isIos" class="text-caption" style="margin-top: 2px; line-height: 1.4; color: #555">
            В Safari нажмите
            <q-icon name="ios_share" size="13px" color="blue-7" style="vertical-align: middle" />
            → «На экран "Домой"»
          </div>
          <!-- Android/Chrome: одна кнопка -->
          <div v-else class="text-caption" style="margin-top: 2px; color: #777">
            Быстрый доступ без браузера
          </div>
        </div>

        <q-btn
          v-if="!isIos"
          unelevated
          color="green-7"
          label="Добавить"
          no-caps
          size="sm"
          style="border-radius: 4px; flex-shrink: 0; padding: 5px 14px; font-size: 12px"
          @click="doInstall"
        />

        <q-btn
          flat
          round
          dense
          size="xs"
          icon="close"
          color="grey-5"
          style="flex-shrink: 0"
          @click="dismiss"
        />
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { computed } from 'vue'
import { usePwaInstall } from 'src/composables/usePwaInstall'

defineProps({
  /**
   * inline=true  → встроен в поток страницы (между элементами)
   * inline=false → position: fixed; bottom: 0 (по умолчанию)
   */
  inline: {
    type: Boolean,
    default: false,
  },
})

const { canInstall, isIos, isInstalled, dismissed, install, dismiss } = usePwaInstall()

// Показывать баннер: не установлено, не скрыто, и есть что предложить
const show = computed(
  () => !isInstalled.value && !dismissed.value && (canInstall.value || isIos.value),
)

async function doInstall() {
  await install()
}
</script>

<style scoped>
.pwa-banner--fixed {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  background: #fff;
  border-top: 1px solid #e0e0e0;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.10);
  padding: 10px 14px 16px;
}

.pwa-banner--inline {
  background: #f0fdf4;
  border-bottom: 1px solid #c8e6c9;
  padding: 8px 14px;
}

.pwa-banner__inner {
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: 520px;
  margin: 0 auto;
}

.pwa-banner__icon {
  flex-shrink: 0;
}

.pwa-banner__text {
  flex: 1;
  min-width: 0;
}

/* Анимация снизу для fixed-варианта */
.pwa-slide-enter-active,
.pwa-slide-leave-active {
  transition: transform 0.25s ease, opacity 0.25s ease;
}

.pwa-slide-enter-from,
.pwa-slide-leave-to {
  transform: translateY(20px);
  opacity: 0;
}
</style>
