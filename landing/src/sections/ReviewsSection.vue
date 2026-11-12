<template>
  <section class="section section--alt">
    <div class="container">
      <h2 class="section-title">СЧАСТЛИВЫЕ КЛИЕНТЫ</h2>
      <div class="reviews__grid">
        <div v-for="review in reviews" :key="review.id" class="review-card reveal">
          <div class="review-card__header">
            <div class="review-card__avatar">
              <img v-if="review.avatar_url" :src="review.avatar_url" :alt="review.author_name" />
              <span v-else>{{ initials(review.author_name) }}</span>
            </div>
            <div class="review-card__meta">
              <strong class="review-card__name">{{ review.author_name }}</strong>
              <span v-if="review.author_city" class="review-card__city">{{ review.author_city }}</span>
            </div>
          </div>
          <p class="review-card__text">{{ review.text }}</p>
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
.review-card__header { display: flex; align-items: center; gap: 14px; }
.review-card__avatar { width: 56px; height: 56px; border-radius: 50%; overflow: hidden; flex-shrink: 0; background: var(--accent); display: flex; align-items: center; justify-content: center; }
.review-card__avatar img { width: 100%; height: 100%; object-fit: cover; }
.review-card__avatar span { color: #fff; font-family: var(--font-head); font-weight: 700; font-size: 1.1rem; }
.review-card__meta { display: flex; flex-direction: column; gap: 2px; }
.review-card__name { font-family: var(--font-head); font-size: 1rem; color: var(--dark); font-weight: 700; }
.review-card__city { font-size: 0.8rem; color: var(--text-light); text-transform: uppercase; letter-spacing: 0.06em; }
.review-card__text { color: var(--text-light); font-size: 0.9rem; line-height: 1.75; flex: 1; font-style: italic; }
</style>
