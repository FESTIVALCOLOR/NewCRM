<template>
  <!-- ══════════════════════ LOGIN ══════════════════════ -->
  <div v-if="!authed" class="login-wrap">
    <div class="login-box">
      <div class="login-logo">FESTIVAL COLOR</div>
      <h2>Вход в панель управления</h2>
      <p class="login-hint">Только для Руководителя студии</p>
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

    <main class="content">
      <div class="content-header">
        <h1>{{ currentTabLabel }}</h1>
        <a href="/beta/" target="_blank" class="btn-ghost">↗ Сайт</a>
      </div>

      <div v-if="globalMsg" :class="['toast', globalMsg.type]">{{ globalMsg.text }}</div>

      <!-- ── Настройки ── -->
      <section v-if="currentTab === 'settings'" class="tab-body">
        <div class="card">
          <h3>Способ связи — кнопки «Написать нам»</h3>
          <p class="hint">Выберите основной мессенджер для кнопок на сайте</p>
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
            <label>Телефон<input v-model="sf.phone" placeholder="+7 (495) 000-00-00" /></label>
            <label>WhatsApp (только цифры, без +)<input v-model="sf.whatsapp" placeholder="79991234567" /></label>
            <label>Telegram (@username без @)<input v-model="sf.telegram" placeholder="festivalcolor" /></label>
            <label>ВКонтакте (полный URL)<input v-model="sf.vk_url" placeholder="https://vk.com/festivalcolor" /></label>
            <label>Instagram (полный URL)<input v-model="sf.instagram_url" placeholder="https://instagram.com/festivalcolor" /></label>
            <label>Email<input v-model="sf.email" placeholder="info@festivalcolor.ru" /></label>
            <label>Адрес<input v-model="sf.address" placeholder="Москва, ул. Примерная, 1" /></label>
          </div>
          <button class="btn-primary" @click="saveSettings">Сохранить контакты</button>
        </div>
      </section>

      <!-- ── Секции ── -->
      <section v-if="currentTab === 'sections'" class="tab-body">
        <p class="hint">Перетащите секции чтобы изменить порядок в меню и на странице. Включите/выключите видимость.</p>
        <div class="drag-list" @dragover.prevent>
          <div v-for="(sec, i) in sectionsData" :key="sec.key"
            class="drag-item"
            draggable="true"
            @dragstart="dragFrom = i; dragKey = 'sections'"
            @dragover.prevent
            @drop.prevent="onDrop(i, 'sections')">
            <span class="drag-handle">⠿</span>
            <div class="drag-info">
              <strong>{{ sectionLabel(sec) }}</strong>
              <span class="sec-key">{{ sec.key }}</span>
            </div>
            <label class="toggle">
              <input type="checkbox" v-model="sec.is_visible" @change="saveSectionVisibility(sec)" />
              <span class="toggle-track"></span>
              <span class="toggle-label">{{ sec.is_visible ? 'Видна' : 'Скрыта' }}</span>
            </label>
          </div>
        </div>
        <button class="btn-primary mt" @click="saveSectionsOrder">Сохранить порядок</button>
      </section>

      <!-- ── Услуги ── -->
      <section v-if="currentTab === 'services'" class="tab-body">
        <div class="card-info">
          <strong>Иконки:</strong> введите любой эмодзи (🏠 🖊 📐 🎨 📄 ✏) — он отображается перед названием услуги на сайте.
        </div>
        <div class="list-toolbar">
          <button class="btn-primary" @click="openServiceEdit({})">+ Добавить услугу</button>
        </div>
        <div class="drag-list" @dragover.prevent>
          <div v-for="(svc, i) in servicesData" :key="svc.id"
            class="drag-item"
            draggable="true"
            @dragstart="dragFrom = i; dragKey = 'services'"
            @dragover.prevent
            @drop.prevent="onDrop(i, 'services')">
            <span class="drag-handle">⠿</span>
            <span style="font-size:1.4rem;width:30px;text-align:center">{{ svc.icon }}</span>
            <div class="drag-info">
              <strong>{{ svc.title }}</strong>
            </div>
            <div class="drag-actions">
              <label class="toggle">
                <input type="checkbox" v-model="svc.is_visible" @change="api.services.update(svc.id, {is_visible: svc.is_visible}).catch(e=>toast(e.message,'error'))" />
                <span class="toggle-track"></span>
              </label>
              <button class="btn-sm" @click="openServiceEdit(svc)">✏ Изменить</button>
              <button class="btn-sm btn-danger" @click="deleteService(svc.id)">✕</button>
            </div>
          </div>
        </div>
        <button class="btn-ghost mt" @click="saveServicesOrder">Сохранить порядок</button>

        <div v-if="editingService" class="modal-overlay" @click.self="editingService = null">
          <div class="modal">
            <h3>{{ editingService.id ? 'Редактировать услугу' : 'Новая услуга' }}</h3>
            <label>Название услуги<input v-model="editingService.title" placeholder="Дизайн-проект квартиры" /></label>
            <label>
              Иконка (эмодзи)
              <div class="emoji-row">
                <input v-model="editingService.icon" placeholder="🏠" style="width:80px" />
                <span v-for="e in ['🏠','🖊','📐','🎨','📄','✏','🔑','🛋','🪟','💡','📏','🏗']"
                  :key="e" class="emoji-pick" @click="editingService.icon = e">{{ e }}</span>
              </div>
            </label>
            <label>Описание<textarea v-model="editingService.description" rows="3" placeholder="Краткое описание услуги"></textarea></label>
            <div class="modal-footer">
              <button class="btn-ghost" @click="editingService = null">Отмена</button>
              <button class="btn-primary" @click="saveServiceEdit">Сохранить</button>
            </div>
          </div>
        </div>
      </section>

      <!-- ── Цены ── -->
      <section v-if="currentTab === 'pricing'" class="tab-body">
        <div class="card-info">Каждый план — это один столбец на странице цен. Состав — список пунктов (что входит в услугу).</div>
        <div class="list-toolbar">
          <button class="btn-primary" @click="openPlanEdit({})">+ Добавить план</button>
        </div>
        <div class="drag-list" @dragover.prevent>
          <div v-for="(plan, i) in pricingData" :key="plan.id"
            class="drag-item"
            draggable="true"
            @dragstart="dragFrom = i; dragKey = 'pricing'"
            @dragover.prevent
            @drop.prevent="onDrop(i, 'pricing')">
            <span class="drag-handle">⠿</span>
            <div class="drag-info">
              <strong>{{ plan.title }}</strong>
              <span class="sec-key">{{ plan.price_label }}</span>
            </div>
            <div class="drag-actions">
              <label class="toggle">
                <input type="checkbox" v-model="plan.is_visible" @change="api.pricing.update(plan.id, {is_visible: plan.is_visible}).catch(e=>toast(e.message,'error'))" />
                <span class="toggle-track"></span>
              </label>
              <button class="btn-sm" @click="openPlanEdit(plan)">✏ Изменить</button>
              <button class="btn-sm btn-danger" @click="deletePlan(plan.id)">✕</button>
            </div>
          </div>
        </div>
        <button class="btn-ghost mt" @click="savePricingOrder">Сохранить порядок</button>

        <div v-if="editingPlan" class="modal-overlay" @click.self="editingPlan = null">
          <div class="modal">
            <h3>{{ editingPlan.id ? 'Редактировать план' : 'Новый план' }}</h3>
            <div class="form-grid">
              <label>Название плана<input v-model="editingPlan.title" placeholder="Планировочные решения" /></label>
              <label>Цена (текст)<input v-model="editingPlan.price_label" placeholder="от 90 000 ₽" /></label>
            </div>
            <label>Текст для WhatsApp-кнопки (необязательно)<input v-model="editingPlan.whatsapp_text" placeholder="Хочу заказать..." /></label>
            <label class="cb-row"><input type="checkbox" v-model="editingPlan.is_featured" /> Выделить (цветной блок)</label>
            <label>Состав услуги — каждый пункт с новой строки
              <textarea v-model="editingPlan.items_text" rows="8"
                placeholder="Обмерный план квартиры&#10;Планировочное решение (3 варианта)&#10;3D-визуализация&#10;..."></textarea>
            </label>
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
          <button class="btn-primary" @click="$refs.portfolioInput.click()">+ Загрузить фото</button>
          <span v-if="uploading" class="upload-progress">Загрузка {{ uploadProgress }}/{{ uploadTotal }}…</span>
          <input ref="portfolioInput" type="file" accept="image/*" multiple style="display:none" @change="uploadPortfolio" />
        </div>
        <div v-if="portfolioData.length === 0" class="empty-state">Фото ещё не добавлены — нажмите «Загрузить фото»</div>
        <div class="portfolio-grid" @dragover.prevent>
          <div v-for="(img, i) in portfolioData" :key="img.id"
            class="portfolio-thumb"
            draggable="true"
            @dragstart="dragFrom = i; dragKey = 'portfolio'"
            @dragover.prevent
            @drop.prevent="onDrop(i, 'portfolio')">
            <img :src="img.url" :alt="img.alt" />
            <div class="portfolio-overlay">
              <label class="toggle-sm">
                <input type="checkbox" v-model="img.is_visible" @change="api.portfolio.update(img.id, {is_visible: img.is_visible}).catch(e=>toast(e.message,'error'))" />
                <span>{{ img.is_visible ? '👁 Видно' : '🚫 Скрыто' }}</span>
              </label>
              <button class="btn-sm" @click="openPortfolioEdit(img)">✏</button>
              <button class="btn-sm btn-danger" @click="deletePortfolio(img.id)">✕</button>
            </div>
          </div>
        </div>
        <button v-if="portfolioData.length > 0" class="btn-ghost mt" @click="savePortfolioOrder">Сохранить порядок</button>

        <div v-if="editingPortfolio" class="modal-overlay" @click.self="editingPortfolio = null">
          <div class="modal">
            <h3>Подпись к фото</h3>
            <img :src="editingPortfolio.url" class="preview-img" />
            <label>Подпись (отображается при наведении)<input v-model="editingPortfolio.alt" placeholder="Квартира в ЖК Маяк" /></label>
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
          <button class="btn-primary" @click="openReviewEdit({})">+ Добавить отзыв</button>
        </div>
        <div class="drag-list" @dragover.prevent>
          <div v-for="(rev, i) in reviewsData" :key="rev.id"
            class="drag-item"
            draggable="true"
            @dragstart="dragFrom = i; dragKey = 'reviews'"
            @dragover.prevent
            @drop.prevent="onDrop(i, 'reviews')">
            <span class="drag-handle">⠿</span>
            <img v-if="rev.avatar_url" :src="rev.avatar_url" class="rev-avatar" />
            <div v-else class="rev-avatar-ph">{{ rev.author_name?.[0] }}</div>
            <div class="drag-info">
              <strong>{{ rev.author_name }}</strong>
              <span class="sec-key">{{ rev.author_city }}</span>
            </div>
            <div class="drag-actions">
              <label class="toggle">
                <input type="checkbox" v-model="rev.is_active" @change="api.reviews.update(rev.id, {is_active: rev.is_active, author_name: rev.author_name, text: rev.text}).catch(e=>toast(e.message,'error'))" />
                <span class="toggle-track"></span>
                <span class="toggle-label">{{ rev.is_active ? 'Показывать' : 'Скрыт' }}</span>
              </label>
              <button class="btn-sm" @click="openReviewEdit(rev)">✏</button>
              <button class="btn-sm btn-danger" @click="deleteReview(rev.id)">✕</button>
            </div>
          </div>
        </div>
        <button class="btn-ghost mt" @click="saveReviewsOrder">Сохранить порядок</button>

        <div v-if="editingReview" class="modal-overlay" @click.self="editingReview = null">
          <div class="modal">
            <h3>{{ editingReview.id ? 'Редактировать отзыв' : 'Новый отзыв' }}</h3>
            <div class="form-grid">
              <label>Имя клиента<input v-model="editingReview.author_name" placeholder="Анна Смирнова" /></label>
              <label>Город (необязательно)<input v-model="editingReview.author_city" placeholder="Москва" /></label>
            </div>
            <label>Текст отзыва<textarea v-model="editingReview.text" rows="5" placeholder="Очень довольна результатом…"></textarea></label>
            <label>Фото клиента
              <div class="upload-row">
                <input v-model="editingReview.avatar_url" placeholder="https://... или загрузите" />
                <button class="btn-sm" @click="$refs.reviewAvatarInput.click()">Загрузить</button>
                <input ref="reviewAvatarInput" type="file" accept="image/*" style="display:none" @change="uploadImg($event, v => editingReview.avatar_url = v)" />
              </div>
            </label>
            <img v-if="editingReview.avatar_url" :src="editingReview.avatar_url" class="preview-avatar" />
            <div class="modal-footer">
              <button class="btn-ghost" @click="editingReview = null">Отмена</button>
              <button class="btn-primary" @click="saveReviewEdit">Сохранить</button>
            </div>
          </div>
        </div>
      </section>

      <!-- ── Команда ── -->
      <section v-if="currentTab === 'team'" class="tab-body">
        <div class="card-info">
          Сотрудники отображаются в секции «Наша команда» на сайте. Добавьте фото и должность каждого сотрудника.
        </div>
        <div class="list-toolbar">
          <button class="btn-primary" @click="openTeamEdit({})">+ Добавить сотрудника</button>
        </div>
        <div class="team-grid">
          <div v-for="(m, i) in teamData" :key="m.id" class="team-card"
            draggable="true"
            @dragstart="dragFrom = i; dragKey = 'team'"
            @dragover.prevent
            @drop.prevent="onDrop(i, 'team')">
            <img v-if="m.photo_url" :src="m.photo_url" class="team-photo" />
            <div v-else class="team-photo-ph">{{ m.name?.[0] || '?' }}</div>
            <div class="team-name">{{ m.name }}</div>
            <div class="team-pos">{{ m.role_label }}</div>
            <div class="team-actions">
              <label class="toggle">
                <input type="checkbox" v-model="m.is_visible" @change="api.team.update(m.id, {...m}).catch(e=>toast(e.message,'error'))" />
                <span class="toggle-track"></span>
              </label>
              <button class="btn-sm" @click="openTeamEdit(m)">✏</button>
              <button class="btn-sm btn-danger" @click="deleteTeamMember(m.id)">✕</button>
            </div>
          </div>
        </div>

        <div v-if="editingTeam" class="modal-overlay" @click.self="editingTeam = null">
          <div class="modal">
            <h3>{{ editingTeam.id ? 'Редактировать сотрудника' : 'Новый сотрудник' }}</h3>
            <div class="form-grid">
              <label>Имя<input v-model="editingTeam.name" placeholder="Мария Иванова" /></label>
              <label>Должность / роль<input v-model="editingTeam.role_label" placeholder="Главный дизайнер" /></label>
            </div>
            <label>О сотруднике (несколько слов)<textarea v-model="editingTeam.description" rows="2" placeholder="10 лет опыта, специализация — современный минимализм"></textarea></label>
            <label>Фото
              <div class="upload-row">
                <input v-model="editingTeam.photo_url" placeholder="https://... или загрузите" />
                <button class="btn-sm" @click="$refs.teamPhotoInput.click()">Загрузить</button>
                <input ref="teamPhotoInput" type="file" accept="image/*" style="display:none" @change="uploadImg($event, v => editingTeam.photo_url = v)" />
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
          <h3>Яндекс.Метрика и счётчики</h3>
          <p class="hint">Вставьте номер счётчика (только цифры) — скрипты подключатся автоматически.</p>
          <div class="form-grid">
            <label>Яндекс.Метрика — номер счётчика<input v-model="af.yandex_metrika_id" placeholder="12345678" /></label>
            <label class="cb-row"><input type="checkbox" v-model="af.yandex_metrika_webvisor" /> Вебвизор (запись поведения)</label>
            <label>Google Analytics 4 — Measurement ID<input v-model="af.google_analytics_id" placeholder="G-XXXXXXXXXX" /></label>
            <label>Google Tag Manager — Container ID<input v-model="af.google_tag_manager_id" placeholder="GTM-XXXXXXX" /></label>
            <label>VK Реклама — Pixel ID<input v-model="af.vk_pixel_id" placeholder="VK-RTRG-..." /></label>
          </div>
          <button class="btn-primary" @click="saveAnalytics">Сохранить</button>
        </div>

        <div class="card">
          <h3>SEO — основные мета-теги</h3>
          <p class="hint">Эти данные влияют на то, как сайт выглядит в поиске.</p>
          <label>Title — заголовок в Google/Яндекс (рекомендуется 50–70 символов)
            <input v-model="af.meta_title" :class="{ warn: (af.meta_title?.length||0) > 70 }" placeholder="Дизайн-проект интерьера в Москве — FESTIVAL COLOR" />
            <span class="char-count">{{ af.meta_title?.length || 0 }} / 70</span>
          </label>
          <label>Description — описание в поиске (120–160 символов)
            <textarea v-model="af.meta_description" rows="3" :class="{ warn: (af.meta_description?.length||0) > 160 }"
              placeholder="Студия интерьерного дизайна FESTIVAL COLOR — создаём уютные пространства от идеи до реализации."></textarea>
            <span class="char-count">{{ af.meta_description?.length || 0 }} / 160</span>
          </label>
          <div class="form-grid">
            <label>Canonical URL<input v-model="af.canonical_url" placeholder="https://festivalcolor.ru/" /></label>
            <label>Robots<input v-model="af.robots" placeholder="index, follow" /></label>
          </div>
          <button class="btn-primary" @click="saveAnalytics">Сохранить</button>
        </div>

        <div class="card">
          <h3>Open Graph — превью в соцсетях</h3>
          <p class="hint">Так выглядит ссылка при отправке в WhatsApp, Telegram, ВКонтакте.</p>
          <div class="form-grid">
            <label>OG Title (заголовок)<input v-model="af.og_title" placeholder="FESTIVAL COLOR — дизайн интерьера" /></label>
          </div>
          <label>OG Description (описание)<textarea v-model="af.og_description" rows="2"></textarea></label>
          <label>OG Image — картинка превью (1200×630 px рекомендуется)
            <div class="upload-row">
              <input v-model="af.og_image_url" placeholder="https://..." />
              <button class="btn-sm" @click="$refs.ogImgInput.click()">Загрузить</button>
              <input ref="ogImgInput" type="file" accept="image/*" style="display:none" @change="uploadImg($event, v => af.og_image_url = v)" />
            </div>
          </label>
          <img v-if="af.og_image_url" :src="af.og_image_url" class="preview-og" />
          <button class="btn-primary" @click="saveAnalytics">Сохранить</button>
        </div>

        <div class="card">
          <h3>Schema.org — структурированные данные</h3>
          <p class="hint">Помогает Google/Яндекс показывать расширенные сниппеты (адрес, телефон, рейтинг).</p>
          <div class="form-grid">
            <label>Название организации<input v-model="af.schema_org_name" placeholder="FESTIVAL COLOR" /></label>
            <label>Телефон<input v-model="af.schema_org_phone" placeholder="+7 (495) 000-00-00" /></label>
            <label>Адрес<input v-model="af.schema_org_address" placeholder="Москва, ул. Примерная, 1" /></label>
            <label>Ценовой диапазон<input v-model="af.schema_org_price_range" placeholder="₽₽₽" /></label>
            <label>Широта (координаты)<input v-model="af.schema_org_latitude" placeholder="55.7558" /></label>
            <label>Долгота (координаты)<input v-model="af.schema_org_longitude" placeholder="37.6176" /></label>
          </div>
          <label>Часы работы (каждый день с новой строки)
            <textarea v-model="af.schema_org_opening_hours" rows="4" placeholder="Mo-Fr 09:00-18:00&#10;Sa 10:00-15:00"></textarea>
          </label>
          <button class="btn-primary" @click="saveAnalytics">Сохранить</button>
        </div>

        <div class="card">
          <h3>Верификация сайта в поисковиках</h3>
          <p class="hint">Скопируйте content="" из meta-тега верификации и вставьте сюда.</p>
          <div class="form-grid">
            <label>Google Search Console (content=)<input v-model="af.google_search_console_key" placeholder="xxxxxxxxxxxxxxxx" /></label>
            <label>Яндекс.Вебмастер (content=)<input v-model="af.yandex_webmaster_key" placeholder="xxxxxxxxxxxxxxxx" /></label>
          </div>
          <button class="btn-primary" @click="saveAnalytics">Сохранить</button>
        </div>

        <div class="card">
          <h3>Произвольные скрипты</h3>
          <p class="hint">Для онлайн-чатов, ретаргетинга и других виджетов сторонних сервисов.</p>
          <label>Код в &lt;head&gt; (коды отслеживания, пиксели)
            <textarea v-model="af.custom_head_scripts" rows="6" class="mono" placeholder="<!-- Вставьте код здесь -->"></textarea>
          </label>
          <label>Код перед &lt;/body&gt; (онлайн-чаты, виджеты)
            <textarea v-model="af.custom_body_end_scripts" rows="6" class="mono" placeholder="<!-- Вставьте код здесь -->"></textarea>
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
function doLogout() { api.logout(); authed.value = false }

// ══ Tabs ══
const tabs = [
  { id: 'settings',  icon: '⚙',  label: 'Настройки' },
  { id: 'sections',  icon: '☰',  label: 'Секции меню' },
  { id: 'services',  icon: '◈',  label: 'Услуги' },
  { id: 'pricing',   icon: '₽',  label: 'Цены' },
  { id: 'portfolio', icon: '◉',  label: 'Портфолио' },
  { id: 'reviews',   icon: '★',  label: 'Отзывы' },
  { id: 'team',      icon: '◎',  label: 'Команда' },
  { id: 'analytics', icon: '📈', label: 'Аналитика / SEO' },
]
const currentTab = ref('settings')
const currentTabLabel = computed(() => tabs.find(t => t.id === currentTab.value)?.label || '')

// ══ Toast ══
const globalMsg = ref(null)
let toastTimer = null
function toast(text, type = 'success') {
  globalMsg.value = { text, type }
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { globalMsg.value = null }, 3500)
}

// ══ Drag-and-drop ══
const dragFrom = ref(null)
const dragKey = ref(null)

function onDrop(toIdx, listName) {
  if (dragKey.value !== listName || dragFrom.value === null || dragFrom.value === toIdx) return
  const arr = listRef(listName)
  const [item] = arr.splice(dragFrom.value, 1)
  arr.splice(toIdx, 0, item)
  dragFrom.value = null; dragKey.value = null
}
function listRef(name) {
  return { sections: sectionsData.value, services: servicesData.value, pricing: pricingData.value,
           portfolio: portfolioData.value, reviews: reviewsData.value, team: teamData.value }[name]
}

// ══ Upload helper ══
async function uploadImg(e, setter) {
  const file = e.target.files[0]
  if (!file) return
  try {
    const r = await api.portfolio.upload(file)
    setter(r.url)
  } catch (err) { toast('Ошибка загрузки: ' + err.message, 'error') }
  e.target.value = ''
}

// ══ Settings ══
const sf = reactive({
  phone: '', whatsapp: '', telegram: '', vk_url: '', instagram_url: '', email: '', address: '',
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
      if (r.key in sf) sf[r.key] = r.value || ''
      if (r.key === 'cta_method') ctaMethod.value = r.value || 'whatsapp'
    })
  } catch (e) { console.error(e) }
}
async function saveSettings() {
  try {
    for (const key of Object.keys(sf)) await api.settings.update(key, sf[key])
    toast('Контакты сохранены')
  } catch (e) { toast(e.message, 'error') }
}
async function saveCta() {
  try { await api.settings.update('cta_method', ctaMethod.value); toast('Метод связи обновлён') }
  catch (e) { toast(e.message, 'error') }
}

// ══ Sections ══
const sectionsData = ref([])
const sectionLabels = {
  hero: 'Главный экран',
  about: 'О нас',
  services: 'Что мы делаем',
  stats: 'Цифры и достижения',
  portfolio: 'Портфолио',
  pricing: 'Цены',
  reviews: 'Отзывы',
  contacts: 'Контакты',
  team: 'Команда',
  cta: 'Призыв к действию',
}
function sectionLabel(sec) {
  return sec.label || sectionLabels[sec.key] || sec.key
}

async function loadSections() {
  try { sectionsData.value = await api.sections.list() } catch (e) { console.error(e) }
}
async function saveSectionVisibility(sec) {
  try { await api.sections.update(sec.key, { is_visible: sec.is_visible }) }
  catch (e) { toast(e.message, 'error') }
}
async function saveSectionsOrder() {
  try {
    await api.sections.reorder(sectionsData.value.map((s, i) => ({ key: s.key, sort_order: i })))
    toast('Порядок секций сохранён')
  } catch (e) { toast(e.message, 'error') }
}

// ══ Services ══
const servicesData = ref([])
const editingService = ref(null)

async function loadServices() {
  try { servicesData.value = await api.services.list() } catch (e) { console.error(e) }
}
function openServiceEdit(svc) {
  editingService.value = { title: '', icon: '', description: '', is_visible: true, ...svc }
}
async function saveServiceEdit() {
  try {
    const d = { title: editingService.value.title, icon: editingService.value.icon,
                description: editingService.value.description, is_visible: editingService.value.is_visible }
    if (editingService.value.id) {
      await api.services.update(editingService.value.id, d)
      const i = servicesData.value.findIndex(s => s.id === editingService.value.id)
      if (i >= 0) servicesData.value[i] = { ...servicesData.value[i], ...d }
    } else {
      const r = await api.services.create(d)
      servicesData.value.push(r)
    }
    editingService.value = null; toast('Услуга сохранена')
  } catch (e) { toast(e.message, 'error') }
}
async function deleteService(id) {
  if (!confirm('Удалить услугу?')) return
  try { await api.services.delete(id); servicesData.value = servicesData.value.filter(s => s.id !== id); toast('Удалено') }
  catch (e) { toast(e.message, 'error') }
}
async function saveServicesOrder() {
  try { await api.services.reorder(servicesData.value.map((s, i) => ({ id: s.id, sort_order: i }))); toast('Порядок сохранён') }
  catch (e) { toast(e.message, 'error') }
}

// ══ Pricing ══
const pricingData = ref([])
const editingPlan = ref(null)

async function loadPricing() {
  try { pricingData.value = await api.pricing.list() } catch (e) { console.error(e) }
}
function openPlanEdit(plan) {
  editingPlan.value = {
    title: '', price_label: '', whatsapp_text: '', is_featured: false, is_visible: true,
    ...plan,
    items_text: (plan.items || []).map(it => it.text).join('\n'),
  }
}
async function savePlanEdit() {
  try {
    const items = (editingPlan.value.items_text || '').split('\n').filter(Boolean).map((text, i) => ({ text, sort_order: i }))
    const payload = { title: editingPlan.value.title, price_label: editingPlan.value.price_label,
                      whatsapp_text: editingPlan.value.whatsapp_text, is_featured: editingPlan.value.is_featured,
                      is_visible: editingPlan.value.is_visible, items }
    if (editingPlan.value.id) {
      await api.pricing.update(editingPlan.value.id, payload)
      const i = pricingData.value.findIndex(p => p.id === editingPlan.value.id)
      if (i >= 0) pricingData.value[i] = { ...pricingData.value[i], ...payload }
    } else {
      const r = await api.pricing.create(payload)
      pricingData.value.push(r)
    }
    editingPlan.value = null; toast('Сохранено')
  } catch (e) { toast(e.message, 'error') }
}
async function deletePlan(id) {
  if (!confirm('Удалить план?')) return
  try { await api.pricing.delete(id); pricingData.value = pricingData.value.filter(p => p.id !== id) }
  catch (e) { toast(e.message, 'error') }
}
async function savePricingOrder() {
  try { await api.pricing.reorder(pricingData.value.map((p, i) => ({ id: p.id, sort_order: i }))); toast('Порядок цен сохранён') }
  catch (e) { toast(e.message, 'error') }
}

// ══ Portfolio ══
const portfolioData = ref([])
const editingPortfolio = ref(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadTotal = ref(0)

async function loadPortfolio() {
  try { portfolioData.value = await api.portfolio.list() } catch (e) { console.error(e) }
}
async function uploadPortfolio(e) {
  const files = Array.from(e.target.files)
  if (!files.length) return
  uploading.value = true; uploadTotal.value = files.length; uploadProgress.value = 0
  for (const file of files) {
    try {
      const r = await api.portfolio.upload(file)
      const created = await api.portfolio.create({ url: r.url, alt: '', is_visible: true })
      portfolioData.value.push(created)
      uploadProgress.value++
    } catch (err) { toast('Ошибка: ' + err.message, 'error') }
  }
  uploading.value = false; e.target.value = ''
  toast(`Загружено ${files.length} фото`)
}
function openPortfolioEdit(img) { editingPortfolio.value = { ...img } }
async function savePortfolioEdit() {
  try {
    await api.portfolio.update(editingPortfolio.value.id, { alt: editingPortfolio.value.alt })
    const i = portfolioData.value.findIndex(p => p.id === editingPortfolio.value.id)
    if (i >= 0) portfolioData.value[i].alt = editingPortfolio.value.alt
    editingPortfolio.value = null; toast('Сохранено')
  } catch (e) { toast(e.message, 'error') }
}
async function deletePortfolio(id) {
  if (!confirm('Удалить фото из портфолио?')) return
  try { await api.portfolio.delete(id); portfolioData.value = portfolioData.value.filter(p => p.id !== id) }
  catch (e) { toast(e.message, 'error') }
}
async function savePortfolioOrder() {
  try { await api.portfolio.reorder(portfolioData.value.map((p, i) => ({ id: p.id, sort_order: i }))); toast('Порядок сохранён') }
  catch (e) { toast(e.message, 'error') }
}

// ══ Reviews ══
const reviewsData = ref([])
const editingReview = ref(null)

async function loadReviews() {
  try { reviewsData.value = await api.reviews.list() } catch (e) { console.error(e) }
}
function openReviewEdit(rev) {
  editingReview.value = { author_name: '', author_city: '', avatar_url: '', text: '', is_active: true, ...rev }
}
async function saveReviewEdit() {
  try {
    const d = { author_name: editingReview.value.author_name, author_city: editingReview.value.author_city,
                avatar_url: editingReview.value.avatar_url, text: editingReview.value.text, is_active: editingReview.value.is_active }
    if (editingReview.value.id) {
      await api.reviews.update(editingReview.value.id, d)
      const i = reviewsData.value.findIndex(r => r.id === editingReview.value.id)
      if (i >= 0) reviewsData.value[i] = { ...reviewsData.value[i], ...d }
    } else {
      const r = await api.reviews.create(d)
      reviewsData.value.push(r)
    }
    editingReview.value = null; toast('Отзыв сохранён')
  } catch (e) { toast(e.message, 'error') }
}
async function deleteReview(id) {
  if (!confirm('Удалить отзыв?')) return
  try { await api.reviews.delete(id); reviewsData.value = reviewsData.value.filter(r => r.id !== id) }
  catch (e) { toast(e.message, 'error') }
}
async function saveReviewsOrder() {
  try { await api.reviews.reorder(reviewsData.value.map((r, i) => ({ id: r.id, sort_order: i }))); toast('Порядок отзывов сохранён') }
  catch (e) { toast(e.message, 'error') }
}

// ══ Team ══
const teamData = ref([])
const editingTeam = ref(null)

async function loadTeam() {
  try { teamData.value = await api.team.list() } catch (e) { console.error(e) }
}
function openTeamEdit(m) {
  editingTeam.value = { name: '', role_label: '', description: '', photo_url: '', is_visible: true, ...m }
}
async function saveTeamEdit() {
  try {
    const d = { name: editingTeam.value.name, role_label: editingTeam.value.role_label,
                description: editingTeam.value.description, photo_url: editingTeam.value.photo_url,
                is_visible: editingTeam.value.is_visible }
    if (editingTeam.value.id) {
      await api.team.update(editingTeam.value.id, d)
      const i = teamData.value.findIndex(t => t.id === editingTeam.value.id)
      if (i >= 0) teamData.value[i] = { ...teamData.value[i], ...d }
    } else {
      const r = await api.team.create(d)
      teamData.value.push(r)
    }
    editingTeam.value = null; toast('Сохранено')
  } catch (e) { toast(e.message, 'error') }
}
async function deleteTeamMember(id) {
  if (!confirm('Удалить сотрудника?')) return
  try { await api.team.delete(id); teamData.value = teamData.value.filter(t => t.id !== id) }
  catch (e) { toast(e.message, 'error') }
}

// ══ Analytics ══
const af = reactive({
  yandex_metrika_id: '', yandex_metrika_webvisor: true,
  google_analytics_id: '', google_tag_manager_id: '', vk_pixel_id: '',
  google_search_console_key: '', yandex_webmaster_key: '',
  meta_title: '', meta_description: '', canonical_url: '', robots: 'index, follow',
  og_title: '', og_description: '', og_image_url: '',
  schema_org_name: '', schema_org_address: '', schema_org_phone: '',
  schema_org_latitude: '', schema_org_longitude: '',
  schema_org_opening_hours: '', schema_org_price_range: '',
  custom_head_scripts: '', custom_body_end_scripts: '',
})

async function loadAnalytics() {
  try { const r = await api.analytics.get(); if (r) Object.assign(af, r) } catch (e) { console.error(e) }
}
async function saveAnalytics() {
  try { await api.analytics.update({ ...af }); toast('Аналитика сохранена') }
  catch (e) { toast(e.message, 'error') }
}

// ══ Init ══
function loadAll() {
  loadSettings(); loadSections(); loadServices(); loadPricing()
  loadPortfolio(); loadReviews(); loadTeam(); loadAnalytics()
}
onMounted(() => { if (authed.value) loadAll() })
</script>

<style scoped>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

.login-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #f0f2f5; font-family: Inter, sans-serif; }
.login-box { background: #fff; border-radius: 12px; padding: 40px 48px; width: 400px; display: flex; flex-direction: column; gap: 14px; box-shadow: 0 4px 24px rgba(0,0,0,.12); }
.login-logo { font-size: 1rem; font-weight: 700; letter-spacing: 0.08em; color: #c0392b; text-align: center; }
.login-box h2 { font-size: 1.25rem; font-weight: 600; text-align: center; color: #1a1a1a; }
.login-hint { font-size: 0.82rem; color: #9ca3af; text-align: center; }
.login-box input { border: 1px solid #d9d9d9; border-radius: 8px; padding: 10px 14px; font-size: 0.95rem; outline: none; }
.login-box input:focus { border-color: #c0392b; }
.alert-err { background: #fff1f0; border: 1px solid #ffccc7; border-radius: 6px; padding: 8px 12px; color: #cf1322; font-size: 0.88rem; }

.admin-shell { display: flex; min-height: 100vh; font-family: Inter, sans-serif; background: #f7f8fa; }

.sidebar { width: 220px; background: #1c1f26; display: flex; flex-direction: column; flex-shrink: 0; }
.sidebar-brand { padding: 20px 20px 12px; font-size: 0.85rem; font-weight: 700; letter-spacing: 0.1em; color: #c0392b; text-transform: uppercase; }
.nav-item { display: flex; align-items: center; gap: 10px; width: 100%; padding: 11px 20px; background: none; border: none; color: #9fa8b7; font-size: 0.9rem; cursor: pointer; text-align: left; transition: background .15s, color .15s; }
.nav-item:hover { background: #2a2f3b; color: #fff; }
.nav-item.active { background: #2a2f3b; color: #fff; border-left: 3px solid #c0392b; }
.nav-icon { font-size: 1rem; width: 18px; text-align: center; }
.nav-logout { margin-top: auto; border-top: 1px solid #2a2f3b; color: #6b7280; }

.content { flex: 1; display: flex; flex-direction: column; overflow: auto; }
.content-header { display: flex; align-items: center; justify-content: space-between; padding: 20px 32px 12px; border-bottom: 1px solid #e8eaed; background: #fff; }
.content-header h1 { font-size: 1.3rem; font-weight: 600; color: #1a1a1a; }
.tab-body { padding: 24px 32px; display: flex; flex-direction: column; gap: 20px; }

.toast { margin: 10px 32px 0; padding: 10px 18px; border-radius: 8px; font-size: 0.9rem; }
.toast.success { background: #f6ffed; border: 1px solid #b7eb8f; color: #389e0d; }
.toast.error   { background: #fff1f0; border: 1px solid #ffa39e; color: #cf1322; }

.card { background: #fff; border-radius: 10px; padding: 24px; box-shadow: 0 1px 4px rgba(0,0,0,.07); }
.card h3 { font-size: 1rem; font-weight: 600; margin-bottom: 12px; color: #1a1a1a; }
.card-info { background: #e8f4fd; border: 1px solid #bae0ff; border-radius: 8px; padding: 10px 16px; font-size: 0.88rem; color: #0958d9; }
.hint { font-size: 0.85rem; color: #6b7280; margin-bottom: 12px; }
.empty-state { text-align: center; padding: 48px; color: #9ca3af; font-size: 0.95rem; background: #fff; border-radius: 10px; }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 16px; }
label { display: flex; flex-direction: column; gap: 5px; font-size: 0.85rem; color: #374151; }
label input, label select, label textarea { border: 1px solid #d9d9d9; border-radius: 6px; padding: 8px 12px; font-size: 0.9rem; outline: none; font-family: inherit; }
label input:focus, label select:focus, label textarea:focus { border-color: #c0392b; }
label input.warn, label textarea.warn { border-color: #faad14; background: #fffbe6; }
.char-count { font-size: 0.78rem; color: #9ca3af; text-align: right; margin-top: 2px; }
.cb-row { flex-direction: row; align-items: center; gap: 8px; }
.radio-group { display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 16px; }
.radio-group label { flex-direction: row; align-items: center; gap: 7px; font-size: 0.9rem; cursor: pointer; }
.mono { font-family: 'Consolas', 'Courier New', monospace; font-size: 0.82rem; }

.btn-primary { background: #c0392b; color: #fff; border: none; border-radius: 7px; padding: 9px 20px; font-size: 0.9rem; cursor: pointer; font-weight: 500; }
.btn-primary:hover { background: #a93226; }
.btn-primary:disabled { opacity: .6; cursor: not-allowed; }
.btn-ghost { background: none; color: #374151; border: 1px solid #d9d9d9; border-radius: 7px; padding: 8px 16px; font-size: 0.88rem; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; }
.btn-ghost:hover { background: #f3f4f6; }
.btn-sm { background: #f3f4f6; border: 1px solid #d9d9d9; border-radius: 5px; padding: 4px 10px; font-size: 0.8rem; cursor: pointer; white-space: nowrap; }
.btn-sm:hover { background: #e5e7eb; }
.btn-danger { background: #fff1f0; border-color: #ffa39e; color: #cf1322; }
.btn-danger:hover { background: #ffccc7; }
.mt { margin-top: 4px; align-self: flex-start; }

.list-toolbar { display: flex; align-items: center; gap: 12px; }
.upload-progress { font-size: 0.85rem; color: #6b7280; }

.drag-list { display: flex; flex-direction: column; gap: 6px; }
.drag-item { display: flex; align-items: center; gap: 12px; background: #fff; border: 1px solid #e8eaed; border-radius: 8px; padding: 10px 14px; cursor: grab; }
.drag-item:active { cursor: grabbing; opacity: .8; }
.drag-handle { color: #9ca3af; font-size: 1.1rem; cursor: grab; }
.drag-info { flex: 1; min-width: 0; }
.drag-info strong { font-size: 0.92rem; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sec-key { font-size: 0.78rem; color: #9ca3af; }
.drag-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }

.toggle { display: flex; align-items: center; gap: 6px; cursor: pointer; }
.toggle input { display: none; }
.toggle-track { width: 36px; height: 20px; background: #d1d5db; border-radius: 10px; position: relative; transition: background .2s; flex-shrink: 0; }
.toggle input:checked + .toggle-track { background: #22c55e; }
.toggle-track::after { content: ''; position: absolute; width: 16px; height: 16px; background: #fff; border-radius: 50%; top: 2px; left: 2px; transition: left .2s; }
.toggle input:checked + .toggle-track::after { left: 18px; }
.toggle-label { font-size: 0.8rem; color: #6b7280; white-space: nowrap; }
.toggle-sm { font-size: 0.78rem; cursor: pointer; display: flex; align-items: center; gap: 4px; }
.toggle-sm input { width: 14px; height: 14px; }

.portfolio-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; }
.portfolio-thumb { position: relative; aspect-ratio: 1; border-radius: 8px; overflow: hidden; background: #f3f4f6; cursor: grab; }
.portfolio-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.portfolio-overlay { position: absolute; inset: 0; background: rgba(0,0,0,.6); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; opacity: 0; transition: opacity .2s; padding: 8px; }
.portfolio-thumb:hover .portfolio-overlay { opacity: 1; }

.team-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 14px; }
.team-card { background: #fff; border-radius: 10px; border: 1px solid #e8eaed; padding: 16px; display: flex; flex-direction: column; align-items: center; gap: 8px; cursor: grab; }
.team-photo { width: 72px; height: 72px; border-radius: 50%; object-fit: cover; }
.team-photo-ph { width: 72px; height: 72px; border-radius: 50%; background: #c0392b; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; font-weight: 700; }
.team-name { font-weight: 600; font-size: 0.92rem; text-align: center; }
.team-pos { font-size: 0.8rem; color: #6b7280; text-align: center; }
.team-actions { display: flex; gap: 6px; }

.rev-avatar { width: 36px; height: 36px; border-radius: 50%; object-fit: cover; flex-shrink: 0; }
.rev-avatar-ph { width: 36px; height: 36px; border-radius: 50%; background: #c0392b; color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 700; flex-shrink: 0; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.5); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 20px; }
.modal { background: #fff; border-radius: 12px; padding: 28px; width: 100%; max-width: 560px; max-height: 90vh; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; }
.modal h3 { font-size: 1.1rem; font-weight: 600; }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 6px; }

.upload-row { display: flex; gap: 8px; }
.upload-row input { flex: 1; }

.preview-img { max-width: 100%; max-height: 200px; border-radius: 8px; object-fit: contain; border: 1px solid #e8eaed; }
.preview-avatar { width: 80px; height: 80px; border-radius: 50%; object-fit: cover; }
.preview-og { max-width: 100%; max-height: 150px; border-radius: 6px; object-fit: contain; border: 1px solid #e8eaed; }

.emoji-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.emoji-pick { font-size: 1.4rem; cursor: pointer; padding: 4px; border-radius: 4px; }
.emoji-pick:hover { background: #f3f4f6; }
</style>
