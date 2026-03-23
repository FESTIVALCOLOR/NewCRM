<template>
  <router-view />
</template>

<script setup>
import { useMeta } from 'quasar'

useMeta({
  title: 'Interior Studio CRM',
  meta: {
    description: { name: 'description', content: 'CRM для интерьерного бюро Festival Color' }
  }
})
</script>
