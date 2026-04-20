<template>
  <!-- Минималистичный layout для клиентов без авторизации -->
  <q-layout view="hHh Lpr lFf">
    <q-header elevated style="background: #2E7D32">
      <q-toolbar>
        <q-toolbar-title class="text-center">
          <span style="font-size: 15px; font-weight: 600">Чат с дизайн-бюро</span>
        </q-toolbar-title>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

// Динамически подменяем манифест, чтобы при установке PWA клиент попадал
// сразу в свой чат (start_url = /c/{token}), а не на главную дашборд.
let _blobUrl = null
let _origHref = null

onMounted(() => {
  const token = route.params.token
  if (!token) return

  const link = document.querySelector('link[rel="manifest"]')
  if (!link) return

  _origHref = link.getAttribute('href')

  const clientManifest = {
    name: 'Чат Festival Color',
    short_name: 'Чат FC',
    description: 'Чат с дизайн-бюро Festival Color',
    display: 'standalone',
    orientation: 'any',
    background_color: '#ffffff',
    theme_color: '#2e7d32',
    lang: 'ru',
    start_url: `/c/${token}`,
    scope: '/',
    icons: [
      { src: '/icons/icon-192x192.png', sizes: '192x192', type: 'image/png' },
      { src: '/icons/icon-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
    ],
  }

  const blob = new Blob([JSON.stringify(clientManifest)], { type: 'application/json' })
  _blobUrl = URL.createObjectURL(blob)
  link.setAttribute('href', _blobUrl)
})

onUnmounted(() => {
  const link = document.querySelector('link[rel="manifest"]')
  if (link && _origHref) link.setAttribute('href', _origHref)
  if (_blobUrl) URL.revokeObjectURL(_blobUrl)
})
</script>
