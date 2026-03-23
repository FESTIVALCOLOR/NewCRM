<template>
  <q-page class="flex flex-center">
    <div class="text-center q-pa-md">
      <q-icon name="wifi_off" size="64px" color="grey-5" class="q-mb-md" />
      <div class="text-h6 text-grey-7 q-mb-sm">Нет подключения</div>
      <div class="text-body2 text-grey-5 q-mb-lg">
        Проверьте интернет-соединение и попробуйте снова
      </div>
      <q-btn
        color="primary"
        label="Повторить"
        no-caps
        unelevated
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
