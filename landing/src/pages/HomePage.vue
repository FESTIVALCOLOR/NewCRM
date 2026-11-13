<template>
  <div>
    <template v-for="key in homeSectionKeys" :key="key">
      <HeroSection       v-if="key === 'hero'" :style="sectionStyles[key]" :settings="site.settings" />
      <AboutSection      v-else-if="key === 'about'" :style="sectionStyles[key]" :team="site.team" />
      <StatsSection      v-else-if="key === 'stats'" :style="sectionStyles[key]" :stats="site.stats" :settings="site.settings" />
      <ServicesSection   v-else-if="key === 'services'" :style="sectionStyles[key]" :services="site.services" />
      <ProjectExampleSection v-else-if="key === 'project_example'" :style="sectionStyles[key]" :settings="site.settings" />
      <DirectionsSection v-else-if="key === 'directions'" :style="sectionStyles[key]" :settings="site.settings" :portfolio="site.portfolio" />
      <ReviewsSection    v-else-if="key === 'reviews'" :style="sectionStyles[key]" :reviews="site.reviews" />
      <ContactsSection   v-else-if="key === 'contacts'" :style="sectionStyles[key]" :settings="site.settings" />
      <ObjectsMapSection v-else-if="key === 'objects_map'" :style="sectionStyles[key]" :settings="site.settings" />
    </template>
  </div>
</template>

<script setup>
import HeroSection from '../sections/HeroSection.vue'
import AboutSection from '../sections/AboutSection.vue'
import StatsSection from '../sections/StatsSection.vue'
import ServicesSection from '../sections/ServicesSection.vue'
import DirectionsSection from '../sections/DirectionsSection.vue'
import ProjectExampleSection from '../sections/ProjectExampleSection.vue'
import ReviewsSection from '../sections/ReviewsSection.vue'
import ContactsSection from '../sections/ContactsSection.vue'
import ObjectsMapSection from '../sections/ObjectsMapSection.vue'
import { site, homeSectionKeys, sectionStyles } from '../store.js'
</script>
