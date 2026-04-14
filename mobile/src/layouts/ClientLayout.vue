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
// Нет логики — чистый layout
</script>
