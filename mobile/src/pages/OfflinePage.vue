<template>
  <q-page class="flex flex-center" style="background: #FFFFFF">
    <div class="text-center q-pa-lg">
      <q-icon name="wifi_off" size="72px" style="color: #E0E0E0" class="q-mb-md" />
      <div class="text-h6 q-mb-sm" style="color: #333">
        Нет подключения к интернету
      </div>
      <div class="text-body2 q-mb-lg" style="color: #888">
        Проверьте соединение и попробуйте снова
      </div>
      <q-btn
        label="Повторить"
        no-caps
        unelevated
        style="background: #ffd93c; color: #333; border-radius: 8px; min-width: 160px"
        @click="retry"
      />
    </div>
  </q-page>
</template>

<script setup>
function retry() {
  window.location.reload()
}
</script>
