<template>
  <!-- ══════════════════════ LOGIN ══════════════════════ -->
  <div v-if="!authed" class="login-wrap">
    <div class="login-box">
      <div class="login-logo">FESTIVAL COLOR</div>
      <h2>Вход в админ-панель</h2>
      <div v-if="loginError" class="alert-err">{{ loginError }}</div>
      <input v-model="loginForm.username" placeholder="Логин" @keyup.enter="doLogin" />
      <input v-model="loginForm.password" type="password" placeholder="Пароль" @keyup.enter="doLogin" />
      <button class="btn-primary" :disabled="loginLoading" @click="doLogin">
        {{ loginLoading ? 'Вход…' : 'Войти' }}
      </button>
    </div>
  </div>

  <!-- ══════════════════════ ADMIN SHELL ══════════════════════ -->
  <div v-else class="admin-shell">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-brand">FC Admin</div>
      <nav>
        <button v-for="t in tabs" :key="t.id"
          :class="['nav-item', { active: currentTab === t.id }]"
          @click="currentTab = t.id">
          <span class="nav-icon">{{ t.icon }}</span>
          <span>{{ t.label }}</span>
        </button>
      </nav>
      <button class="nav-item nav-logout" @click="doLogout">⬡ Выйти</button>
    </aside>

    <!-- Content -->
    <main class="content">
      <div class="content-header">
        <h1>{{ currentTabLabel }}</h1>
        <a :href="siteUrl" target="_blank" class="btn-ghost">↗ Сайт</a>
      </div>

      <div v-if="globalMsg" :class="['toast', globalMsg.type]">{{ globalMsg.text }}</div>

      <!-- ── Настройки ── -->
      <section v-if="currentTab === 'settings'" class="tab-body">
        <div class="card">
          <h3>Кнопки связи (CTA)</h3>
          <p class="hint">Выберите основной способ связи для кнопок «Написать нам»</p>
          <div class="radio-group">
            <label v-for="m in contactMethods" :key="m.value">
              <input type="radio" v-model="ctaMethod" :value="m.value" @change="saveCta" />
              {{ m.label }}
            </label>
          </div>
        </div>
        <div class="card">
          <h3>Контактные данные</h3>
          <div class="form-grid">
            <label>Телефон<input v-model="settingsForm.phone" placeholder="+7 (495) 000-00-00" /></label>
            <label>WhatsApp (номер)<input v-model="settingsForm.whatsapp" placeholder="79991234567" /></label>
            <label>Telegram (username)<input v-model="settingsForm.telegram" placeholder="festivalcolor" /></label>
            <label>ВКонтакте (URL)<input v-model="settingsForm.vk_url" placeholder="https://vk.com/..." /></label>
            <label>Instagram (URL)<input v-model="settingsForm.instagram_url" placeholder="https://instagram.com/..." /></label>
            <label>Email<input v-model="settingsForm.email" placeholder="info@festivalcolor.ru" /></label>
            <label>Адрес<input v-model="settingsForm.address" placeholder="Москва, ул. ..." /></label>
          </div>
          <button class="btn-primary" @click="saveSettings">Сохранить</button>
        </div>
        <div class="card">
          <h3>Тексты кнопок</h3>
          <div class="form-grid">
            <label>Текст CTA кнопки (Hero)<input v-model="settingsForm.cta_hero_text" placeholder="Получить консультацию" /></label>
            <label>Текст CTA кнопки (Цены)<input v-model="settingsForm.cta_pricing_text" placeholder="Узнать стоимость" /></label>
          </div>
          <button class="btn-primary" @click="saveSettings">Сохранить</button>
        </div>
      </section>

      <!-- ── Секции ── -->
      <section v-if="currentTab === 'sections'" class="tab-body">
        <p class="hint">Перетащите секции для изменения порядка. Скройте/покажите любую секцию.</p>
        <div class="drag-list" @dragover.prevent>
          <div v-for="(sec, i) in sectionsData" :key="sec.key"
            class="drag-item"
            draggable="true"
            @dragstart="onDragStart(i, 'sections')"
            @drop="onDrop(i, 'sections')">
            <span class="drag-handle">⠿</span>
            <div class="drag-info">
              <strong>{{ sec.title || sec.key }}</strong>
              <span class="sec-key">{{ sec.key }}</span>
            </div>
            <div class="drag-actions">
              <label class="toggle">
                <input type="checkbox" v-model="sec.is_visible" @change="saveSectionVisibility(sec)" />
                <span class="toggle-track"></span>
                <span class="toggle-label">{{ sec.is_visible ? 'Видна' : 'Скрыта' }}</span>
              </label>
              <button class="btn-sm" @click="openSectionEdit(sec)">Редактировать</button>
            </div>
          </div>
        </div>
        <button class="btn-primary mt" @click="saveSectionsOrder">Сохранить порядок</button>

        <!-- Section edit modal -->
        <div v-if="editingSection" class="modal-overlay" @click.self="editingSection = null">
          <div class="modal">
            <h3>Редактировать секцию: {{ editingSection.key }}</h3>
            <label>Заголовок<input v-model="editingSection.title" /></label>
            <label>Подзаголовок<textarea v-model="editingSection.subtitle" rows="2"></textarea></label>
            <label>Описание<textarea v-model="editingSection.description" rows="4"></textarea></label>
            <label>Изображение (URL или загрузите)
              <div class="upload-row">
                <input v-model="editingSection.image_url" placeholder="https://..." />
                <button class="btn-sm" @click="triggerUpload('section-img')">Загрузить</button>
                <input ref="secImgInput" type="file" accept="image/*" style="display:none" @change="uploadForSection" />
              </div>
            </label>
            <img v-if="editingSection.image_url" :src="editingSection.image_url" class="preview-img" />
            <label>Позиция изображения
              <select v-model="editingSection.image_position">
                <option value="left">Слева</option>
                <option value="right">Справа</option>
                <option value="background">Фон</option>
                <option value="top">Сверху</option>
              </select>
            </label>
            <div class="modal-footer">
              <button class="btn-ghost" @click="editingSection = null">Отмена</button>
              <button class="btn-primary" @click="saveSectionEdit">Сохранить</button>
            </div>
          </div>
        </div>
      </section>

      <!-- ── Услуги ── -->
      <section v-if="currentTab === 'services'" class="tab-body">
        <div class="list-toolbar">
          <button class="btn-primary" @click="addService">+ Добавить услугу</button>
        </div>
        <div class="drag-list" @dragover.prevent>
          <div v-for="(svc, i) in servicesData" :key="svc.id"
            class="drag-item"
            draggable="true"
            @dragstart="onDragStart(i, 'services')"
            @drop="onDrop(i, 'services')">
            <span class="drag-handle">⠿</span>
            <div class="drag-info">
              <strong>{{ svc.title }}</strong>
              <span class="sec-key">{{ svc.icon }}</span>
            </div>
            <div class="drag-actions">
              <label class="toggle">
                <input type="checkbox" v-model="svc.is_visible" @change="updateService(svc)" />
                <span class="toggle-track"></span>
              </label>
              <button class="btn-sm" @click="openServiceEdit(svc)">✏</button>
              <button class="btn-sm btn-danger" @click="deleteService(svc.id)">✕</button>
            </div>
          </div>
        </div>
        <button class="btn-ghost mt" @click="saveServicesOrder">Сохранить порядок</button>

        <div v-if="editingService" class="modal-overlay" @click.self="editingService = null">
          <div class="modal">
            <h3>{{ editingService.id ? 'Редактировать' : 'Новая' }} услуга</h3>
            <label>Название<input v-model="editingService.title" /></label>
            <label>Иконка (эмодзи или текст)<input v-model="editingService.icon" /></label>
            <label>Описание<textarea v-model="editingService.description" rows="4"></textarea></label>
            <label>URL ссылки<input v-model="editingService.link_url" placeholder="/portfolio" /></label>
            <div class="modal-footer">
              <button class="btn-ghost" @click="editingService = null">Отмена</button>
              <button class="btn-primary" @click="saveServiceEdit">Сохранить</button>
            </div>
          </div>
        </div>
      </section>

      <!-- ── Цены ── -->
      <section v-if="currentTab === 'pricing'" class="tab-body">
        <div class="list-toolbar">
          <button class="btn-primary" @click="addPlan">+ Добавить план</button>
        </div>
        <div class="drag-list" @dragover.prevent>
          <div v-for="(plan, i) in pricingData" :key="plan.id"
            class="drag-item"
            draggable="true"
            @dragstart="onDragStart(i, 'pricing')"
            @drop="onDrop(i, 'pricing')">
            <span class="drag-handle">⠿</span>
            <div class="drag-info">
              <strong>{{ plan.title }}</strong>
              <span class="sec-key">{{ plan.price }}</span>
            </div>
            <div class="drag-actions">
              <label class="toggle">
                <input type="checkbox" v-model="plan.is_visible" @change="updatePlan(plan)" />
                <span class="toggle-track"></span>
              </label>
              <button class="btn-sm" @click="openPlanEdit(plan)">✏</button>
              <button class="btn-sm btn-danger" @click="deletePlan(plan.id)">✕</button>
            </div>
          </div>
        </div>
        <button class="btn-ghost mt" @click="savePricingOrder">Сохранить порядок</button>

        <div v-if="editingPlan" class="modal-overlay" @click.self="editingPlan = null">
          <div class="modal">
            <h3>{{ editingPlan.id ? 'Редактировать' : 'Новый' }} план</h3>
            <div class="form-grid">
              <label>Название<input v-model="editingPlan.title" /></label>
              <label>Цена (текст)<input v-model="editingPlan.price" placeholder="от 90 000 ₽" /></label>
              <label>Единица (м², объект…)<input v-model="editingPlan.unit" /></label>
            </div>
            <label>Описание<textarea v-model="editingPlan.description" rows="2"></textarea></label>
            <label>Состав услуги (каждый пункт с новой строки)
              <textarea v-model="editingPlan.features_text" rows="6" placeholder="Обмерный план&#10;Планировочное решение&#10;..."></textarea>
            </label>
            <label class="cb-row"><input type="checkbox" v-model="editingPlan.is_popular" /> Пометить как популярный</label>
            <div class="modal-footer">
              <button class="btn-ghost" @click="editingPlan = null">Отмена</button>
              <button class="btn-primary" @click="savePlanEdit">Сохранить</button>
            </div>
          </div>
        </div>
      </section>

      <!-- ── Портфолио ── -->
      <section v-if="currentTab === 'portfolio'" class="tab-body">
        <div class="list-toolbar">
          <button class="btn-primary" @click="triggerPortfolioUpload">+ Загрузить фото</button>
          <input ref="portfolioInput" type="file" accept="image/*" multiple style="display:none" @change="uploadPortfolio" />
        </div>
        <div class="portfolio-grid" @dragover.prevent>
          <div v-for="(img, i) in portfolioData" :key="img.id"
            class="portfolio-thumb"
            draggable="true"
            @dragstart="onDragStart(i, 'portfolio')"
            @drop="onDrop(i, 'portfolio')">
            <img :src="img.url" :alt="img.alt" />
            <div class="portfolio-overlay">
              <button class="btn-sm" @click="openPortfolioEdit(img)">✏</button>
              <button class="btn-sm btn-danger" @click="deletePortfolio(img.id)">✕</button>
              <label class="toggle-sm">
                <input type="checkbox" v-model="img.is_visible" @change="updatePortfolio(img)" />
                <span>{{ img.is_visible ? '✓' : '—' }}</span>
              </label>
            </div>
          </div>
        </div>
        <button class="btn-ghost mt" @click="savePortfolioOrder">Сохранить порядок</button>

        <div v-if="editingPortfolio" class="modal-overlay" @click.self="editingPortfolio = null">
          <div class="modal">
            <h3>Фото портфолио</h3>
            <img :src="editingPortfolio.url" class="preview-img" />
            <label>Подпись (alt)<input v-model="editingPortfolio.alt" /></label>
            <label>Категория<input v-model="editingPortfolio.category" placeholder="квартира, офис…" /></label>
            <div class="modal-footer">
              <button class="btn-ghost" @click="editingPortfolio = null">Отмена</button>
              <button class="btn-primary" @click="savePortfolioEdit">Сохранить</button>
            </div>
          </div>
        </div>
      </section>

      <!-- ── Отзывы ── -->
      <section v-if="currentTab === 'reviews'" class="tab-body">
        <div class="list-toolbar">
          <button class="btn-primary" @click="addReview">+ Добавить отзыв</button>
        </div>
        <div class="drag-list" @dragover.prevent>
          <div v-for="(rev, i) in reviewsData" :key="rev.id"
            class="drag-item"
            draggable="true"
            @dragstart="onDragStart(i, 'reviews')"
            @drop="onDrop(i, 'reviews')">
            <span class="drag-handle">⠿</span>
            <div class="drag-info">
              <strong>{{ rev.author_name }}</strong>
              <span class="sec-key">★ {{ rev.rating }}</span>
            </div>
            <div class="drag-actions">
              <label class="toggle">
                <input type="checkbox" v-model="rev.is_active" @change="updateReview(rev)" />
                <span class="toggle-track"></span>
              </label>
              <button class="btn-sm" @click="openReviewEdit(rev)">✏</button>
              <button class="btn-sm btn-danger" @click="deleteReview(rev.id)">✕</button>
            </div>
          </div>
        </div>
        <button class="btn-ghost mt" @click="saveReviewsOrder">Сохранить порядок</button>

        <div v-if="editingReview" class="modal-overlay" @click.self="editingReview = null">
          <div class="modal">
            <h3>{{ editingReview.id ? 'Редактировать' : 'Новый' }} отзыв</h3>
            <div class="form-grid">
              <label>Имя автора<input v-model="editingReview.author_name" /></label>
              <label>Рейтинг (1–5)<input v-model.number="editingReview.rating" type="number" min="1" max="5" /></label>
              <label>Дата (необязательно)<input v-model="editingReview.review_date" type="date" /></label>
            </div>
            <label>Текст отзыва<textarea v-model="editingReview.text" rows="5"></textarea></label>
            <label>Аватар (URL или загрузите)
              <div class="upload-row">
                <input v-model="editingReview.author_photo" placeholder="https://..." />
                <button class="btn-sm" @click="$refs.reviewAvatarInput.click()">Загрузить</button>
                <input ref="reviewAvatarInput" type="file" accept="image/*" style="display:none" @change="uploadReviewAvatar" />
              </div>
            </label>
            <img v-if="editingReview.author_photo" :src="editingReview.author_photo" class="preview-avatar" />
            <label>Источник<input v-model="editingReview.source" placeholder="Google, Яндекс, 2ГИС…" /></label>
            <div class="modal-footer">
              <button class="btn-ghost" @click="editingReview = null">Отмена</button>
              <button class="btn-primary" @click="saveReviewEdit">Сохранить</button>
            </div>
          </div>
        </div>
      </section>

      <!-- ── Команда ── -->
      <section v-if="currentTab === 'team'" class="tab-body">
        <div class="list-toolbar">
          <button class="btn-primary" @click="addTeamMember">+ Добавить сотрудника</button>
        </div>
        <div class="team-grid">
          <div v-for="(m, i) in teamData" :key="m.id" class="team-card"
            draggable="true"
            @dragstart="onDragStart(i, 'team')"
            @dragover.prevent
            @drop="onDrop(i, 'team')">
            <img v-if="m.photo_url" :src="m.photo_url" class="team-photo" />
            <div v-else class="team-photo-ph">{{ m.name ? m.name[0] : '?' }}</div>
            <div class="team-name">{{ m.name }}</div>
            <div class="team-pos">{{ m.position }}</div>
            <div class="team-actions">
              <label class="toggle">
                <input type="checkbox" v-model="m.is_visible" @change="updateTeamMember(m)" />
                <span class="toggle-track"></span>
              </label>
              <button class="btn-sm" @click="openTeamEdit(m)">✏</button>
              <button class="btn-sm btn-danger" @click="deleteTeamMember(m.id)">✕</button>
            </div>
          </div>
        </div>

        <div v-if="editingTeam" class="modal-overlay" @click.self="editingTeam = null">
          <div class="modal">
            <h3>{{ editingTeam.id ? 'Редактировать' : 'Новый' }} сотрудник</h3>
            <div class="form-grid">
              <label>Имя<input v-model="editingTeam.name" /></label>
              <label>Должность<input v-model="editingTeam.position" /></label>
            </div>
            <label>Описание<textarea v-model="editingTeam.bio" rows="3"></textarea></label>
            <label>Фото
              <div class="upload-row">
                <input v-model="editingTeam.photo_url" placeholder="https://..." />
                <button class="btn-sm" @click="$refs.teamPhotoInput.click()">Загрузить</button>
                <input ref="teamPhotoInput" type="file" accept="image/*" style="display:none" @change="uploadTeamPhoto" />
              </div>
            </label>
            <img v-if="editingTeam.photo_url" :src="editingTeam.photo_url" class="preview-avatar" />
            <div class="modal-footer">
              <button class="btn-ghost" @click="editingTeam = null">Отмена</button>
              <button class="btn-primary" @click="saveTeamEdit">Сохранить</button>
            </div>
          </div>
        </div>
      </section>

      <!-- ── Аналитика / SEO ── -->
      <section v-if="currentTab === 'analytics'" class="tab-body">
        <div class="card">
          <h3>Метрики и пиксели</h3>
          <div class="form-grid">
            <label>Яндекс.Метрика ID<input v-model="analyticsForm.yandex_metrika_id" placeholder="12345678" /></label>
            <label class="cb-row"><input type="checkbox" v-model="analyticsForm.yandex_metrika_webvisor" /> Вебвизор включён</label>
            <label>Google Analytics 4 (ID)<input v-model="analyticsForm.google_analytics_id" placeholder="G-XXXXXXXXXX" /></label>
            <label>Google Tag Manager (ID)<input v-model="analyticsForm.google_tag_manager_id" placeholder="GTM-XXXXXXX" /></label>
            <label>VK Pixel (ID)<input v-model="analyticsForm.vk_pixel_id" placeholder="VK-RTRG-..." /></label>
          </div>
          <button class="btn-primary" @click="saveAnalytics">Сохранить</button>
        </div>

        <div class="card">
          <h3>Верификация сайта</h3>
          <div class="form-grid">
            <label>Google Search Console (meta-tag content)<input v-model="analyticsForm.google_search_console_key" placeholder="xxxxxxxxxxxxxxxx" /></label>
            <label>Яндекс.Вебмастер (meta-tag content)<input v-model="analyticsForm.yandex_webmaster_key" placeholder="xxxxxxxxxxxxxxxx" /></label>
          </div>
          <button class="btn-primary" @click="saveAnalytics">Сохранить</button>
        </div>

        <div class="card">
          <h3>SEO: мета-теги</h3>
          <div class="form-grid">
            <label>Title (60–70 символов)<input v-model="analyticsForm.meta_title" :class="{ warn: analyticsForm.meta_title?.length > 70 }" /></label>
            <label>Canonical URL<input v-model="analyticsForm.canonical_url" placeholder="https://festivalcolor.ru/" /></label>
            <label>Robots<input v-model="analyticsForm.robots" placeholder="index, follow" /></label>
          </div>
          <label>Description (120–160 символов)
            <textarea v-model="analyticsForm.meta_description" rows="3"
              :class="{ warn: analyticsForm.meta_description?.length > 160 }"></textarea>
            <span class="char-count">{{ analyticsForm.meta_description?.length || 0 }} / 160</span>
          </label>
          <label>Keywords (через запятую)<textarea v-model="analyticsForm.meta_keywords" rows="2"></textarea></label>
          <button class="btn-primary" @click="saveAnalytics">Сохранить</button>
        </div>

        <div class="card">
          <h3>Open Graph (соцсети)</h3>
          <div class="form-grid">
            <label>OG Title<input v-model="analyticsForm.og_title" /></label>
          </div>
          <label>OG Description<textarea v-model="analyticsForm.og_description" rows="2"></textarea></label>
          <label>OG Image (URL)
            <div class="upload-row">
              <input v-model="analyticsForm.og_image_url" placeholder="https://..." />
              <button class="btn-sm" @click="$refs.ogImgInput.click()">Загрузить</button>
              <input ref="ogImgInput" type="file" accept="image/*" style="display:none" @change="uploadOgImage" />
            </div>
          </label>
          <img v-if="analyticsForm.og_image_url" :src="analyticsForm.og_image_url" class="preview-og" />
          <button class="btn-primary" @click="saveAnalytics">Сохранить</button>
        </div>

        <div class="card">
          <h3>Schema.org LocalBusiness</h3>
          <div class="form-grid">
            <label>Название организации<input v-model="analyticsForm.schema_org_name" placeholder="FESTIVAL COLOR" /></label>
            <label>Адрес<input v-model="analyticsForm.schema_org_address" /></label>
            <label>Телефон<input v-model="analyticsForm.schema_org_phone" /></label>
            <label>Широта (latitude)<input v-model="analyticsForm.schema_org_latitude" placeholder="55.7558" /></label>
            <label>Долгота (longitude)<input v-model="analyticsForm.schema_org_longitude" placeholder="37.6176" /></label>
            <label>Ценовой диапазон<input v-model="analyticsForm.schema_org_price_range" placeholder="₽₽₽" /></label>
          </div>
          <label>Часы работы (каждый пункт с новой строки, напр. Mo-Fr 09:00-18:00)
            <textarea v-model="analyticsForm.schema_org_opening_hours" rows="4"></textarea>
          </label>
          <button class="btn-primary" @click="saveAnalytics">Сохранить</button>
        </div>

        <div class="card">
          <h3>Произвольные скрипты</h3>
          <label>&lt;head&gt; (коды ретаргетинга, верификации)
            <textarea v-model="analyticsForm.custom_head_scripts" rows="6" class="mono"></textarea>
          </label>
          <label>Перед &lt;/body&gt; (чаты поддержки, виджеты)
            <textarea v-model="analyticsForm.custom_body_end_scripts" rows="6" class="mono"></textarea>
          </label>
          <button class="btn-primary" @click="saveAnalytics">Сохранить</button>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import * as api from './api.js'

// ══ Auth ══
const authed = ref(!!localStorage.getItem('admin_token'))
const loginForm = reactive({ username: '', password: '' })
const loginLoading = ref(false)
const loginError = ref('')

async function doLogin() {
  loginError.value = ''
  loginLoading.value = true
  try {
    await api.login(loginForm.username, loginForm.password)
    authed.value = true
    loadAll()
  } catch (e) {
    loginError.value = e.message
  } finally {
    loginLoading.value = false
  }
}
function doLogout() {
  api.logout()
  authed.value = false
}

// ══ Tabs ══
const tabs = [
  { id: 'settings',  icon: '⚙',  label: 'Настройки' },
  { id: 'sections',  icon: '☰',  label: 'Секции' },
  { id: 'services',  icon: '◈',  label: 'Услуги' },
  { id: 'pricing',   icon: '₽',  label: 'Цены' },
  { id: 'portfolio', icon: '◉',  label: 'Портфолио' },
  { id: 'reviews',   icon: '★',  label: 'Отзывы' },
  { id: 'team',      icon: '◎',  label: 'Команда' },
  { id: 'analytics', icon: '◈',  label: 'Аналитика / SEO' },
]
const currentTab = ref('settings')
const currentTabLabel = computed(() => tabs.find(t => t.id === currentTab.value)?.label || '')
const siteUrl = computed(() => window.location.origin + '/beta/')

// ══ Toast ══
const globalMsg = ref(null)
let toastTimer = null
function toast(text, type = 'success') {
  globalMsg.value = { text, type }
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { globalMsg.value = null }, 3000)
}

// ══ Drag-and-drop ══
const dragFrom = ref(null)
const dragList = ref(null)
function onDragStart(i, list) { dragFrom.value = i; dragList.value = list }
function onDrop(i, list) {
  if (dragList.value !== list || dragFrom.value === null) return
  const arr = listRef(list)
  const [item] = arr.splice(dragFrom.value, 1)
  arr.splice(i, 0, item)
  dragFrom.value = null
}
function listRef(list) {
  return { sections: sectionsData, services: servicesData, pricing: pricingData,
           portfolio: portfolioData, reviews: reviewsData, team: teamData }[list]
}

// ══ Settings ══
const settingsForm = reactive({
  phone: '', whatsapp: '', telegram: '', vk_url: '', instagram_url: '',
  email: '', address: '', cta_hero_text: '', cta_pricing_text: '',
})
const ctaMethod = ref('whatsapp')
const contactMethods = [
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'telegram', label: 'Telegram' },
  { value: 'phone',    label: 'Телефон (звонок)' },
  { value: 'email',    label: 'Email' },
]

async function loadSettings() {
  try {
    const rows = await api.settings.list()
    rows.forEach(r => {
      if (r.key in settingsForm) settingsForm[r.key] = r.value || ''
      if (r.key === 'cta_method') ctaMethod.value = r.value || 'whatsapp'
    })
  } catch {}
}
async function saveSettings() {
  try {
    for (const key of Object.keys(settingsForm)) {
      await api.settings.update(key, settingsForm[key])
    }
    toast('Настройки сохранены')
  } catch (e) { toast(e.message, 'error') }
}
async function saveCta() {
  try { await api.settings.update('cta_method', ctaMethod.value); toast('Метод связи обновлён') }
  catch (e) { toast(e.message, 'error') }
}

// ══ Sections ══
const sectionsData = ref([])
const editingSection = ref(null)
const secImgInput = ref(null)

async function loadSections() {
  try { sectionsData.value = await api.sections.list() } catch {}
}
function openSectionEdit(sec) { editingSection.value = { ...sec } }
async function saveSectionVisibility(sec) {
  try { await api.sections.update(sec.key, { is_visible: sec.is_visible }) }
  catch (e) { toast(e.message, 'error') }
}
async function saveSectionEdit() {
  try {
    await api.sections.update(editingSection.value.key, editingSection.value)
    const i = sectionsData.value.findIndex(s => s.key === editingSection.value.key)
    if (i >= 0) sectionsData.value[i] = { ...editingSection.value }
    editingSection.value = null
    toast('Секция обновлена')
  } catch (e) { toast(e.message, 'error') }
}
async function saveSectionsOrder() {
  try {
    await api.sections.reorder(sectionsData.value.map((s, i) => ({ key: s.key, sort_order: i })))
    toast('Порядок секций сохранён')
  } catch (e) { toast(e.message, 'error') }
}
function triggerUpload(type) { secImgInput.value?.click() }
async function uploadForSection(e) {
  const file = e.target.files[0]
  if (!file) return
  try {
    const r = await api.portfolio.upload(file)
    editingSection.value.image_url = r.url
  } catch (e) { toast(e.message, 'error') }
  e.target.value = ''
}

// ══ Services ══
const servicesData = ref([])
const editingService = ref(null)

async function loadServices() {
  try { servicesData.value = await api.services.list() } catch {}
}
function addService() {
  editingService.value = { title: '', icon: '', description: '', link_url: '', is_visible: true }
}
function openServiceEdit(svc) { editingService.value = { ...svc } }
async function updateService(svc) {
  try { await api.services.update(svc.id, { is_visible: svc.is_visible }) }
  catch (e) { toast(e.message, 'error') }
}
async function saveServiceEdit() {
  try {
    if (editingService.value.id) {
      await api.services.update(editingService.value.id, editingService.value)
      const i = servicesData.value.findIndex(s => s.id === editingService.value.id)
      if (i >= 0) servicesData.value[i] = { ...editingService.value }
    } else {
      const r = await api.services.create(editingService.value)
      servicesData.value.push(r)
    }
    editingService.value = null
    toast('Услуга сохранена')
  } catch (e) { toast(e.message, 'error') }
}
async function deleteService(id) {
  if (!confirm('Удалить услугу?')) return
  try {
    await api.services.delete(id)
    servicesData.value = servicesData.value.filter(s => s.id !== id)
    toast('Удалено')
  } catch (e) { toast(e.message, 'error') }
}
async function saveServicesOrder() {
  try {
    await api.services.reorder(servicesData.value.map((s, i) => ({ id: s.id, sort_order: i })))
    toast('Порядок услуг сохранён')
  } catch (e) { toast(e.message, 'error') }
}

// ══ Pricing ══
const pricingData = ref([])
const editingPlan = ref(null)

async function loadPricing() {
  try { pricingData.value = await api.pricing.list() } catch {}
}
function addPlan() {
  editingPlan.value = { title: '', price: '', unit: '', description: '', features_text: '', is_popular: false, is_visible: true }
}
function openPlanEdit(plan) {
  editingPlan.value = { ...plan, features_text: (plan.features || []).join('\n') }
}
async function updatePlan(plan) {
  try { await api.pricing.update(plan.id, { is_visible: plan.is_visible }) }
  catch (e) { toast(e.message, 'error') }
}
async function savePlanEdit() {
  try {
    const payload = { ...editingPlan.value, features: editingPlan.value.features_text.split('\n').filter(Boolean) }
    if (editingPlan.value.id) {
      await api.pricing.update(editingPlan.value.id, payload)
      const i = pricingData.value.findIndex(p => p.id === editingPlan.value.id)
      if (i >= 0) pricingData.value[i] = { ...pricingData.value[i], ...payload }
    } else {
      const r = await api.pricing.create(payload)
      pricingData.value.push(r)
    }
    editingPlan.value = null
    toast('Сохранено')
  } catch (e) { toast(e.message, 'error') }
}
async function deletePlan(id) {
  if (!confirm('Удалить план?')) return
  try {
    await api.pricing.delete(id)
    pricingData.value = pricingData.value.filter(p => p.id !== id)
    toast('Удалено')
  } catch (e) { toast(e.message, 'error') }
}
async function savePricingOrder() {
  try {
    await api.pricing.reorder(pricingData.value.map((p, i) => ({ id: p.id, sort_order: i })))
    toast('Порядок цен сохранён')
  } catch (e) { toast(e.message, 'error') }
}

// ══ Portfolio ══
const portfolioData = ref([])
const editingPortfolio = ref(null)
const portfolioInput = ref(null)

async function loadPortfolio() {
  try { portfolioData.value = await api.portfolio.list() } catch {}
}
function triggerPortfolioUpload() { portfolioInput.value?.click() }
async function uploadPortfolio(e) {
  const files = Array.from(e.target.files)
  for (const file of files) {
    try {
      const r = await api.portfolio.upload(file)
      const created = await api.portfolio.create({ url: r.url, alt: file.name, is_visible: true })
      portfolioData.value.push(created)
    } catch (err) { toast(err.message, 'error') }
  }
  e.target.value = ''
  toast(`Загружено ${files.length} фото`)
}
function openPortfolioEdit(img) { editingPortfolio.value = { ...img } }
async function updatePortfolio(img) {
  try { await api.portfolio.update(img.id, { is_visible: img.is_visible }) }
  catch (e) { toast(e.message, 'error') }
}
async function savePortfolioEdit() {
  try {
    await api.portfolio.update(editingPortfolio.value.id, editingPortfolio.value)
    const i = portfolioData.value.findIndex(p => p.id === editingPortfolio.value.id)
    if (i >= 0) portfolioData.value[i] = { ...editingPortfolio.value }
    editingPortfolio.value = null
    toast('Сохранено')
  } catch (e) { toast(e.message, 'error') }
}
async function deletePortfolio(id) {
  if (!confirm('Удалить фото?')) return
  try {
    await api.portfolio.delete(id)
    portfolioData.value = portfolioData.value.filter(p => p.id !== id)
  } catch (e) { toast(e.message, 'error') }
}
async function savePortfolioOrder() {
  try {
    await api.portfolio.reorder(portfolioData.value.map((p, i) => ({ id: p.id, sort_order: i })))
    toast('Порядок сохранён')
  } catch (e) { toast(e.message, 'error') }
}

// ══ Reviews ══
const reviewsData = ref([])
const editingReview = ref(null)

async function loadReviews() {
  try { reviewsData.value = await api.reviews.list() } catch {}
}
function addReview() {
  editingReview.value = { author_name: '', text: '', rating: 5, author_photo: '', source: '', review_date: '', is_active: true }
}
function openReviewEdit(rev) { editingReview.value = { ...rev } }
async function updateReview(rev) {
  try { await api.reviews.update(rev.id, { is_active: rev.is_active }) }
  catch (e) { toast(e.message, 'error') }
}
async function saveReviewEdit() {
  try {
    if (editingReview.value.id) {
      await api.reviews.update(editingReview.value.id, editingReview.value)
      const i = reviewsData.value.findIndex(r => r.id === editingReview.value.id)
      if (i >= 0) reviewsData.value[i] = { ...editingReview.value }
    } else {
      const r = await api.reviews.create(editingReview.value)
      reviewsData.value.push(r)
    }
    editingReview.value = null
    toast('Отзыв сохранён')
  } catch (e) { toast(e.message, 'error') }
}
async function deleteReview(id) {
  if (!confirm('Удалить отзыв?')) return
  try {
    await api.reviews.delete(id)
    reviewsData.value = reviewsData.value.filter(r => r.id !== id)
  } catch (e) { toast(e.message, 'error') }
}
async function saveReviewsOrder() {
  try {
    await api.reviews.reorder(reviewsData.value.map((r, i) => ({ id: r.id, sort_order: i })))
    toast('Порядок отзывов сохранён')
  } catch (e) { toast(e.message, 'error') }
}
async function uploadReviewAvatar(e) {
  const file = e.target.files[0]
  if (!file) return
  try {
    const r = await api.portfolio.upload(file)
    editingReview.value.author_photo = r.url
  } catch (err) { toast(err.message, 'error') }
  e.target.value = ''
}

// ══ Team ══
const teamData = ref([])
const editingTeam = ref(null)

async function loadTeam() {
  try { teamData.value = await api.team.list() } catch {}
}
function addTeamMember() {
  editingTeam.value = { name: '', position: '', bio: '', photo_url: '', is_visible: true }
}
function openTeamEdit(m) { editingTeam.value = { ...m } }
async function updateTeamMember(m) {
  try { await api.team.update(m.id, { is_visible: m.is_visible }) }
  catch (e) { toast(e.message, 'error') }
}
async function saveTeamEdit() {
  try {
    if (editingTeam.value.id) {
      await api.team.update(editingTeam.value.id, editingTeam.value)
      const i = teamData.value.findIndex(t => t.id === editingTeam.value.id)
      if (i >= 0) teamData.value[i] = { ...editingTeam.value }
    } else {
      const r = await api.team.create(editingTeam.value)
      teamData.value.push(r)
    }
    editingTeam.value = null
    toast('Сохранено')
  } catch (e) { toast(e.message, 'error') }
}
async function deleteTeamMember(id) {
  if (!confirm('Удалить сотрудника?')) return
  try {
    await api.team.delete(id)
    teamData.value = teamData.value.filter(t => t.id !== id)
  } catch (e) { toast(e.message, 'error') }
}
async function uploadTeamPhoto(e) {
  const file = e.target.files[0]
  if (!file) return
  try {
    const r = await api.portfolio.upload(file)
    editingTeam.value.photo_url = r.url
  } catch (err) { toast(err.message, 'error') }
  e.target.value = ''
}

// ══ Analytics ══
const analyticsForm = reactive({
  yandex_metrika_id: '', yandex_metrika_webvisor: true,
  google_analytics_id: '', google_tag_manager_id: '', vk_pixel_id: '',
  google_search_console_key: '', yandex_webmaster_key: '',
  meta_title: '', meta_description: '', meta_keywords: '',
  canonical_url: '', robots: 'index, follow',
  og_title: '', og_description: '', og_image_url: '',
  schema_org_name: '', schema_org_address: '', schema_org_phone: '',
  schema_org_latitude: '', schema_org_longitude: '',
  schema_org_opening_hours: '', schema_org_price_range: '',
  custom_head_scripts: '', custom_body_end_scripts: '',
})

async function loadAnalytics() {
  try {
    const r = await api.analytics.get()
    Object.assign(analyticsForm, r)
  } catch {}
}
async function saveAnalytics() {
  try {
    await api.analytics.update({ ...analyticsForm })
    toast('Аналитика / SEO сохранены')
  } catch (e) { toast(e.message, 'error') }
}
async function uploadOgImage(e) {
  const file = e.target.files[0]
  if (!file) return
  try {
    const r = await api.portfolio.upload(file)
    analyticsForm.og_image_url = r.url
  } catch (err) { toast(err.message, 'error') }
  e.target.value = ''
}

// ══ Init ══
function loadAll() {
  loadSettings()
  loadSections()
  loadServices()
  loadPricing()
  loadPortfolio()
  loadReviews()
  loadTeam()
  loadAnalytics()
}

onMounted(() => { if (authed.value) loadAll() })
</script>

<style scoped>
/* ── Reset / base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* ── Login ── */
.login-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #f0f2f5; font-family: Inter, sans-serif; }
.login-box { background: #fff; border-radius: 12px; padding: 40px 48px; width: 380px; display: flex; flex-direction: column; gap: 16px; box-shadow: 0 4px 24px rgba(0,0,0,.12); }
.login-logo { font-size: 1.1rem; font-weight: 700; letter-spacing: 0.08em; color: #c0392b; text-align: center; }
.login-box h2 { font-size: 1.3rem; font-weight: 600; text-align: center; color: #1a1a1a; }
.login-box input { border: 1px solid #d9d9d9; border-radius: 8px; padding: 10px 14px; font-size: 0.95rem; outline: none; }
.login-box input:focus { border-color: #c0392b; }
.alert-err { background: #fff1f0; border: 1px solid #ffccc7; border-radius: 6px; padding: 8px 12px; color: #cf1322; font-size: 0.88rem; }

/* ── Shell ── */
.admin-shell { display: flex; min-height: 100vh; font-family: Inter, sans-serif; background: #f7f8fa; }

/* ── Sidebar ── */
.sidebar { width: 220px; background: #1c1f26; display: flex; flex-direction: column; padding: 0; flex-shrink: 0; }
.sidebar-brand { padding: 20px 20px 12px; font-size: 0.85rem; font-weight: 700; letter-spacing: 0.1em; color: #c0392b; text-transform: uppercase; }
.nav-item { display: flex; align-items: center; gap: 10px; width: 100%; padding: 11px 20px; background: none; border: none; color: #9fa8b7; font-size: 0.9rem; cursor: pointer; text-align: left; transition: background .15s, color .15s; }
.nav-item:hover { background: #2a2f3b; color: #fff; }
.nav-item.active { background: #2a2f3b; color: #fff; border-left: 3px solid #c0392b; }
.nav-icon { font-size: 1rem; width: 18px; text-align: center; }
.nav-logout { margin-top: auto; border-top: 1px solid #2a2f3b; color: #6b7280; }

/* ── Content ── */
.content { flex: 1; display: flex; flex-direction: column; overflow: auto; }
.content-header { display: flex; align-items: center; justify-content: space-between; padding: 20px 32px 12px; border-bottom: 1px solid #e8eaed; background: #fff; }
.content-header h1 { font-size: 1.3rem; font-weight: 600; color: #1a1a1a; }
.tab-body { padding: 24px 32px; display: flex; flex-direction: column; gap: 20px; }

/* ── Toast ── */
.toast { margin: 12px 32px 0; padding: 10px 18px; border-radius: 8px; font-size: 0.9rem; }
.toast.success { background: #f6ffed; border: 1px solid #b7eb8f; color: #389e0d; }
.toast.error   { background: #fff1f0; border: 1px solid #ffa39e; color: #cf1322; }

/* ── Card ── */
.card { background: #fff; border-radius: 10px; padding: 24px; box-shadow: 0 1px 4px rgba(0,0,0,.07); }
.card h3 { font-size: 1rem; font-weight: 600; margin-bottom: 16px; color: #1a1a1a; }
.hint { font-size: 0.85rem; color: #6b7280; margin-bottom: 8px; }

/* ── Form ── */
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 16px; }
label { display: flex; flex-direction: column; gap: 5px; font-size: 0.85rem; color: #374151; }
label input, label select, label textarea { border: 1px solid #d9d9d9; border-radius: 6px; padding: 8px 12px; font-size: 0.9rem; outline: none; font-family: inherit; }
label input:focus, label select:focus, label textarea:focus { border-color: #c0392b; }
label input.warn, label textarea.warn { border-color: #faad14; background: #fffbe6; }
.char-count { font-size: 0.78rem; color: #9ca3af; text-align: right; }
.cb-row { flex-direction: row; align-items: center; gap: 8px; }
.radio-group { display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 16px; }
.radio-group label { flex-direction: row; align-items: center; gap: 7px; font-size: 0.9rem; cursor: pointer; }
.mono { font-family: 'Consolas', 'Courier New', monospace; font-size: 0.82rem; }

/* ── Buttons ── */
.btn-primary { background: #c0392b; color: #fff; border: none; border-radius: 7px; padding: 9px 20px; font-size: 0.9rem; cursor: pointer; font-weight: 500; }
.btn-primary:hover { background: #a93226; }
.btn-primary:disabled { opacity: .6; cursor: not-allowed; }
.btn-ghost { background: none; color: #374151; border: 1px solid #d9d9d9; border-radius: 7px; padding: 8px 16px; font-size: 0.88rem; cursor: pointer; }
.btn-ghost:hover { background: #f3f4f6; }
.btn-sm { background: #f3f4f6; border: 1px solid #d9d9d9; border-radius: 5px; padding: 4px 10px; font-size: 0.8rem; cursor: pointer; }
.btn-sm:hover { background: #e5e7eb; }
.btn-danger { background: #fff1f0; border-color: #ffa39e; color: #cf1322; }
.btn-danger:hover { background: #ffccc7; }
.mt { margin-top: 4px; }

/* ── Drag list ── */
.drag-list { display: flex; flex-direction: column; gap: 6px; }
.drag-item { display: flex; align-items: center; gap: 12px; background: #fff; border: 1px solid #e8eaed; border-radius: 8px; padding: 10px 14px; cursor: grab; }
.drag-item:active { cursor: grabbing; }
.drag-handle { color: #9ca3af; font-size: 1.1rem; cursor: grab; }
.drag-info { flex: 1; min-width: 0; }
.drag-info strong { font-size: 0.92rem; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sec-key { font-size: 0.78rem; color: #9ca3af; }
.drag-actions { display: flex; align-items: center; gap: 8px; }

/* ── Toggle ── */
.toggle { display: flex; align-items: center; gap: 6px; cursor: pointer; }
.toggle input { display: none; }
.toggle-track { width: 36px; height: 20px; background: #d1d5db; border-radius: 10px; position: relative; transition: background .2s; }
.toggle input:checked + .toggle-track { background: #22c55e; }
.toggle-track::after { content: ''; position: absolute; width: 16px; height: 16px; background: #fff; border-radius: 50%; top: 2px; left: 2px; transition: left .2s; }
.toggle input:checked + .toggle-track::after { left: 18px; }
.toggle-label { font-size: 0.8rem; color: #6b7280; }
.toggle-sm { font-size: 0.75rem; color: #fff; cursor: pointer; }

/* ── List toolbar ── */
.list-toolbar { display: flex; gap: 10px; }

/* ── Portfolio grid ── */
.portfolio-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; }
.portfolio-thumb { position: relative; aspect-ratio: 1; border-radius: 8px; overflow: hidden; background: #f3f4f6; cursor: grab; }
.portfolio-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.portfolio-overlay { position: absolute; inset: 0; background: rgba(0,0,0,.55); display: flex; align-items: center; justify-content: center; gap: 6px; opacity: 0; transition: opacity .2s; }
.portfolio-thumb:hover .portfolio-overlay { opacity: 1; }

/* ── Team grid ── */
.team-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 14px; }
.team-card { background: #fff; border-radius: 10px; border: 1px solid #e8eaed; padding: 16px; display: flex; flex-direction: column; align-items: center; gap: 8px; cursor: grab; }
.team-photo { width: 72px; height: 72px; border-radius: 50%; object-fit: cover; }
.team-photo-ph { width: 72px; height: 72px; border-radius: 50%; background: #c0392b; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; font-weight: 700; }
.team-name { font-weight: 600; font-size: 0.92rem; text-align: center; }
.team-pos { font-size: 0.8rem; color: #6b7280; text-align: center; }
.team-actions { display: flex; gap: 6px; }

/* ── Modal ── */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.5); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 20px; }
.modal { background: #fff; border-radius: 12px; padding: 28px; width: 100%; max-width: 560px; max-height: 90vh; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; }
.modal h3 { font-size: 1.1rem; font-weight: 600; }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 6px; }

/* ── Upload row ── */
.upload-row { display: flex; gap: 8px; }
.upload-row input { flex: 1; }

/* ── Previews ── */
.preview-img { max-width: 100%; max-height: 200px; border-radius: 8px; object-fit: contain; border: 1px solid #e8eaed; }
.preview-avatar { width: 80px; height: 80px; border-radius: 50%; object-fit: cover; }
.preview-og { max-width: 100%; max-height: 150px; border-radius: 6px; object-fit: contain; border: 1px solid #e8eaed; }
</style>
