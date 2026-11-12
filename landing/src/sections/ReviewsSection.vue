<template>
  <section class="section section--alt">
    <div class="container">
      <h2 class="section-title">СЧАСТЛИВЫЕ КЛИЕНТЫ</h2>
      <div class="reviews__grid">
        <div v-for="review in reviews" :key="review.id" class="review-card reveal">
          <div class="review-card__avatar">{{ initials(review.author_name) }}</div>
          <p class="review-card__text">{{ review.text }}</p>
          <strong class="review-card__name">{{ review.author_name }}</strong>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({ reviews: Array })
function initials(name) {
  return (name || '').split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase()
}
</script>

<style scoped>
.reviews__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 24px; }
.review-card { background: #fff; border-radius: 12px; padding: 28px; box-shadow: 0 2px 16px rgba(0,0,0,0.06); display: flex; flex-direction: column; gap: 16px; }
.review-card__avatar { width: 52px; height: 52px; border-radius: 50%; background: var(--accent); color: #fff; display: flex; align-items: center; justify-content: center; font-family: var(--font-head); font-weight: 700; font-size: 1.1rem; }
.review-card__text { color: var(--text-light); font-size: 0.9rem; line-height: 1.7; flex: 1; font-style: italic; }
.review-card__name { font-family: var(--font-head); font-size: 0.95rem; color: var(--dark); }
</style>
