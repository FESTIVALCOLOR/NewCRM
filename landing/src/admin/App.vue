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
            <label>WhatsApp (номер с кодом страны)<input v-model="sf.whatsapp_phone" placeholder="79991234567" /></label>
            <label>Telegram (@username без @)<input v-model="sf.telegram" placeholder="festivalcolor" /></label>
            <label>ВКонтакте (полный URL)<input v-model="sf.vk_url" placeholder="https://vk.com/festivalcolor" /></label>
            <label>Instagram (полный URL)<input v-model="sf.instagram_url" placeholder="https://instagram.com/festivalcolor" /></label>
            <label>Email<input v-model="sf.email" placeholder="info@festivalcolor.ru" /></label>
            <label>Адрес<input v-model="sf.address" placeholder="Москва, ул. Примерная, 1" /></label>
          </div>
          <button class="btn-primary" @click="saveSettings">Сохранить контакты</button>
        </div>
        <div class="card">
          <h3>Карта с офисом в блоке «Контакты»</h3>
          <p class="hint">Монохромная карта с цветным кружком на месте офиса — в том же стиле, что карта объектов. Цвет кружка — акцентный цвет сайта.</p>
          <div class="form-grid">
            <label>Координаты офиса (широта, долгота)<input v-model="sf.office_coords" placeholder="59.964229, 30.308495" /></label>
            <label>Ключ API Яндекс Карт<input v-model="sf.yandex_maps_api_key" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" /></label>
          </div>
          <p class="hint"><strong>Координаты:</strong> откройте Яндекс Карты, нажмите правой кнопкой на здание офиса и выберите «Что здесь?» — координаты появятся в карточке, скопируйте их сюда как есть.</p>
          <p class="hint"><strong>Ключ:</strong> с ключом карта рисуется на Яндекс Картах, без ключа — на OpenStreetMap в том же оформлении. Ключ бесплатный: в «Кабинете разработчика» Яндекса (developer.tech.yandex.ru) подключите «JavaScript API и HTTP Геокодер» и в ограничениях ключа укажите адрес сайта. Если ключ не подойдёт, сайт сам покажет карту OpenStreetMap.</p>
          <button class="btn-primary" @click="saveSettings">Сохранить</button>
        </div>
        <div class="card">
          <h3>Главный экран и оформление</h3>
          <p class="hint">Первый экран сайта: заголовок, подзаголовок, текст кнопки и фоновое фото.</p>
          <div class="form-grid">
            <label>Заголовок<input v-model="hf.hero_title" placeholder="Креативный дизайн для вашего успеха" /></label>
            <label>Текст кнопки<input v-model="hf.hero_cta" placeholder="Свяжитесь с нами" /></label>
          </div>
          <label>Подзаголовок<textarea v-model="hf.hero_subtitle" rows="2"></textarea></label>
          <label>Фоновое фото главного экрана
            <div class="upload-row">
              <input v-model="hf.hero_bg_url" placeholder="https://... или загрузите" />
              <button class="btn-sm" @click.prevent="$refs.heroBgInput.click()">Загрузить</button>
              <input ref="heroBgInput" type="file" accept="image/jpeg,image/png,image/webp" style="display:none" @change="uploadImg($event, v => hf.hero_bg_url = v)" />
            </div>
          </label>
          <label>Логотип в шапке
            <div class="upload-row">
              <input v-model="hf.logo_url" placeholder="https://... или загрузите" />
              <button class="btn-sm" @click.prevent="$refs.logoInput.click()">Загрузить</button>
              <input ref="logoInput" type="file" accept="image/jpeg,image/png,image/webp" style="display:none" @change="uploadImg($event, v => hf.logo_url = v)" />
            </div>
          </label>
          <label>Логотип в подвале (на тёмном фоне — удобно загрузить белый или монохромный вариант; пусто — текстовый логотип)
            <div class="upload-row">
              <input v-model="hf.footer_logo_url" placeholder="https://... или загрузите PNG с прозрачным фоном" />
              <button class="btn-sm" @click.prevent="$refs.footerLogoInput.click()">Загрузить</button>
              <input ref="footerLogoInput" type="file" accept="image/png,image/webp" style="display:none" @change="uploadImg($event, v => hf.footer_logo_url = v)" />
            </div>
            <div v-if="hf.footer_logo_url" class="footer-logo-preview"><img :src="hf.footer_logo_url" alt="" /></div>
          </label>
          <label>Текст в подвале сайта (копирайт)<input v-model="hf.copyright" /></label>
          <button class="btn-primary mt" @click="saveHero">Сохранить оформление</button>
        </div>
      </section>

      <!-- ── Секции ── -->
      <section v-if="currentTab === 'sections'" class="tab-body">
        <p class="hint">Перетащите секцию мышью, чтобы изменить порядок в меню и на главной странице — порядок сохраняется сразу. Переключатель скрывает секцию с сайта и из меню. Портфолио и цены показываются на странице «Индивидуальный дизайн».</p>
        <div class="drag-list" @dragover.prevent>
          <div v-for="(sec, i) in sectionsData" :key="sec.key"
            class="drag-item"
            draggable="true"
            @dragstart="onDragStart($event, i, 'sections')"
            @dragover.prevent
            @drop.prevent="onDrop(i, 'sections')">
            <span class="drag-handle">⠿</span>
            <div class="drag-info">
              <strong>{{ sectionLabel(sec) }}</strong>
              <span class="sec-key">{{ sectionHint(sec) }}</span>
            </div>
            <label class="toggle">
              <input type="checkbox" v-model="sec.is_visible" @change="saveSectionVisibility(sec)" />
              <span class="toggle-track"></span>
              <span class="toggle-label">{{ sec.is_visible ? 'Видна' : 'Скрыта' }}</span>
            </label>
          </div>
        </div>
      </section>

      <!-- ── Услуги ── -->
      <section v-if="currentTab === 'services'" class="tab-body">
        <div class="card-info">
          Карточки блока «Что мы предлагаем». Иконка выбирается из готового набора при редактировании услуги. Порядок меняется перетаскиванием и сохраняется сразу.
        </div>
        <div class="list-toolbar">
          <button class="btn-primary" @click="openServiceEdit({})">+ Добавить услугу</button>
        </div>
        <div class="drag-list" @dragover.prevent>
          <div v-for="(svc, i) in servicesData" :key="svc.id"
            class="drag-item"
            draggable="true"
            @dragstart="onDragStart($event, i, 'services')"
            @dragover.prevent
            @drop.prevent="onDrop(i, 'services')">
            <span class="drag-handle">⠿</span>
            <span class="svc-icon"><svg viewBox="0 0 24 24"><path :d="serviceIconPath(svc.icon)" /></svg></span>
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

        <div v-if="editingService" class="modal-overlay" @click.self="editingService = null">
          <div class="modal">
            <h3>{{ editingService.id ? 'Редактировать услугу' : 'Новая услуга' }}</h3>
            <label>Название услуги<input v-model="editingService.title" placeholder="Дизайн-проект квартиры" /></label>
            <div class="field">
              Иконка — нажмите на нужную
              <div class="icon-row">
                <button v-for="(ic, name) in SERVICE_ICONS" :key="name" type="button" :title="ic.label"
                  :class="['icon-pick', { active: editingService.icon === name }]" @click="editingService.icon = name">
                  <svg viewBox="0 0 24 24"><path :d="ic.path" /></svg>
                </button>
              </div>
            </div>
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
        <div class="card-info">Каждый план — одна карточка в блоке «Наши цены». Состав — список пунктов (что входит в услугу); у пункта могут быть раскрывающиеся подпункты.</div>
        <div class="list-toolbar">
          <button class="btn-primary" @click="openPlanEdit({})">+ Добавить план</button>
        </div>
        <div class="drag-list" @dragover.prevent>
          <div v-for="(plan, i) in pricingData" :key="plan.id"
            class="drag-item"
            draggable="true"
            @dragstart="onDragStart($event, i, 'pricing')"
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

        <div v-if="editingPlan" class="modal-overlay" @click.self="editingPlan = null">
          <div class="modal">
            <h3>{{ editingPlan.id ? 'Редактировать план' : 'Новый план' }}</h3>
            <div class="form-grid">
              <label>Название плана<input v-model="editingPlan.title" placeholder="Планировочные решения" /></label>
              <label>Цена (текст)<input v-model="editingPlan.price_label" placeholder="от 90 000 ₽" /></label>
            </div>
            <label>Текст сообщения, которое клиент отправит по кнопке «Заказать» (необязательно)<input v-model="editingPlan.whatsapp_text" placeholder="Здравствуйте, интересует тариф…" /></label>
            <label class="cb-row"><input type="checkbox" v-model="editingPlan.is_featured" /> Выделить (цветной блок)</label>
            <label>Состав услуги — каждый пункт с новой строки. Строка, начинающаяся с дефиса «-», становится подпунктом предыдущего пункта
              <textarea v-model="editingPlan.items_text" rows="10"
                placeholder="Обмерный план квартиры&#10;Планировочное решение&#10;- 3 варианта планировки&#10;- расстановка мебели&#10;3D-визуализация"></textarea>
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
          <input ref="portfolioInput" type="file" accept="image/jpeg,image/png,image/webp,image/gif" multiple style="display:none" @change="uploadPortfolio" />
          <span class="hint" style="margin:0">JPEG, PNG или WebP до 10 МБ. Порядок меняется перетаскиванием.</span>
        </div>
        <div v-if="portfolioData.length === 0" class="empty-state">Фото ещё не добавлены — нажмите «Загрузить фото»</div>
        <div class="portfolio-grid" @dragover.prevent>
          <div v-for="(img, i) in portfolioData" :key="img.id"
            class="portfolio-thumb"
            draggable="true"
            @dragstart="onDragStart($event, i, 'portfolio')"
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
            @dragstart="onDragStart($event, i, 'reviews')"
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
                <input type="checkbox" v-model="rev.is_active" @change="api.reviews.update(rev.id, {is_active: rev.is_active}).catch(e=>toast(e.message,'error'))" />
                <span class="toggle-track"></span>
                <span class="toggle-label">{{ rev.is_active ? 'Показывать' : 'Скрыт' }}</span>
              </label>
              <button class="btn-sm" @click="openReviewEdit(rev)">✏</button>
              <button class="btn-sm btn-danger" @click="deleteReview(rev.id)">✕</button>
            </div>
          </div>
        </div>

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
          На сайте в блоке «О нас» показывается <strong>первый видимый</strong> человек из этого списка: его фото, текст «о себе», имя, специальность и должность. Остальные хранятся про запас — перетащите нужного на первое место, чтобы показать его.
        </div>
        <div class="list-toolbar">
          <button class="btn-primary" @click="openTeamEdit({})">+ Добавить сотрудника</button>
        </div>
        <div class="team-grid">
          <div v-for="(m, i) in teamData" :key="m.id" class="team-card"
            draggable="true"
            @dragstart="onDragStart($event, i, 'team')"
            @dragover.prevent
            @drop.prevent="onDrop(i, 'team')">
            <img v-if="m.photo_url" :src="m.photo_url" class="team-photo" />
            <div v-else class="team-photo-ph">{{ m.name?.[0] || '?' }}</div>
            <div class="team-name">{{ m.name }}</div>
            <div class="team-pos">{{ m.role_label }}</div>
            <div class="team-actions">
              <label class="toggle">
                <input type="checkbox" v-model="m.is_visible" @change="api.team.update(m.id, {is_visible: m.is_visible}).catch(e=>toast(e.message,'error'))" />
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
              <label>Специальность<input v-model="editingTeam.position" placeholder="Дизайнер / Архитектор" /></label>
            </div>
            <label>Должность (выделяется цветом)<input v-model="editingTeam.role_label" placeholder="Руководитель студии FESTIVAL COLOR" /></label>
            <label>Текст блока «О нас»<textarea v-model="editingTeam.description" rows="8" placeholder="Здравствуйте, меня зовут…"></textarea></label>
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

      <!-- ── Стиль ── -->
      <section v-if="currentTab === 'style'" class="tab-body">
        <div class="card-info">
          «Весь сайт» — общее оформление. Выберите блок, чтобы задать ему свои шрифты, размеры, цвета и фон: всё, что не отмечено галочкой, берётся из общего стиля. Изменения сразу видны в «Предпросмотре», а на сайте появятся после нажатия «Сохранить стиль».
        </div>
        <div class="scope-row">
          <button :class="['scope-chip', { active: !styleScope }]" @click="styleScope = ''">Весь сайт</button>
          <button v-for="key in SECTION_KEYS" :key="key"
            :class="['scope-chip', { active: styleScope === key, custom: Object.keys(secStyles[key]).length > 0 }]"
            :title="Object.keys(secStyles[key]).length ? 'У блока есть свои настройки' : ''"
            @click="styleScope = key">{{ sectionLabels[key] }}</button>
        </div>
        <div class="style-layout">
          <div class="style-form">
            <div v-if="styleScope" class="card">
              <h3>Блок «{{ sectionLabels[styleScope] }}» — свои настройки</h3>
              <p class="hint">Отметьте галочкой то, что в этом блоке должно отличаться от общего стиля.</p>
              <div v-for="f in scopeFields" :key="f.key" class="sec-field">
                <label class="cb-row sec-field-name">
                  <input type="checkbox" :checked="f.key in curSec" @change="toggleSecField(f, $event.target.checked)" />
                  {{ f.label }}
                </label>
                <template v-if="f.key in curSec">
                  <select v-if="f.type === 'font'" v-model="curSec[f.key]">
                    <option v-for="font in FONTS" :key="font.name" :value="font.name">{{ font.name }}{{ font.fallback === 'serif' ? ' (с засечками)' : '' }}</option>
                  </select>
                  <div v-else-if="f.type === 'size'" class="size-row">
                    <input type="range" :min="SIZE_MIN" :max="SIZE_MAX" step="5" v-model="curSec[f.key]" />
                    <span>{{ curSec[f.key] }}%</span>
                  </div>
                  <div v-else class="color-row">
                    <input type="color" v-model="curSec[f.key]" />
                    <input v-model="curSec[f.key]" maxlength="7" placeholder="#000000" />
                  </div>
                </template>
                <span v-else class="sec-inherit">как на всём сайте</span>
              </div>
            </div>
            <template v-else>
            <div class="card">
              <h3>Шрифты</h3>
              <div class="form-grid">
                <label>Шрифт заголовков
                  <select v-model="stf.style_font_head">
                    <option v-for="f in FONTS" :key="f.name" :value="f.name">{{ f.name }}{{ f.fallback === 'serif' ? ' (с засечками)' : '' }}</option>
                  </select>
                </label>
                <label>Шрифт основного текста
                  <select v-model="stf.style_font_body">
                    <option v-for="f in FONTS" :key="f.name" :value="f.name">{{ f.name }}{{ f.fallback === 'serif' ? ' (с засечками)' : '' }}</option>
                  </select>
                </label>
              </div>
            </div>
            <div class="card">
              <h3>Размеры</h3>
              <label>Размер заголовков — {{ stf.style_head_size }}%
                <input type="range" :min="SIZE_MIN" :max="SIZE_MAX" step="5" v-model="stf.style_head_size" />
              </label>
              <label style="margin-top:12px">Размер текста — {{ stf.style_text_size }}%
                <input type="range" :min="SIZE_MIN" :max="SIZE_MAX" step="5" v-model="stf.style_text_size" />
              </label>
              <p class="hint" style="margin:10px 0 0">100% — исходный размер. Текст меняется вместе с кнопками и меню, заголовки — отдельно.</p>
            </div>
            <div class="card">
              <h3>Декор по краям</h3>
              <label class="cb-row">
                <input type="checkbox" v-model="stf.style_decor" true-value="1" false-value="0" />
                Показывать предметы интерьера в пустых полях по бокам блоков
              </label>
              <p class="hint" style="margin:10px 0 0">Линейные рисунки светильников, кресла, растения и столика в блоках «О нас», «Услуги», «Цены», «Отзывы» и «Контакты». Видны только на широких экранах (от 1600 px), где по бокам от содержимого остаётся свободное место. Цвет рисунков задаётся ниже.</p>
            </div>
            <div class="card">
              <h3>Цвета</h3>
              <div class="form-grid">
                <label v-for="c in styleColors" :key="c.key">{{ c.label }}
                  <div class="color-row">
                    <input type="color" v-model="stf[c.key]" />
                    <input v-model="stf[c.key]" maxlength="7" placeholder="#000000" />
                  </div>
                </label>
              </div>
            </div>
            </template>
            <div class="list-toolbar">
              <button class="btn-primary" @click="saveStyle">Сохранить стиль</button>
              <button v-if="styleScope" class="btn-ghost" @click="resetSection">Сбросить настройки блока</button>
              <button v-else class="btn-ghost" @click="resetStyle">Вернуть исходный стиль</button>
            </div>
          </div>

          <div class="style-preview" :style="stylePreview.vars">
            <div class="sp-label">Предпросмотр — {{ styleScope ? 'блок «' + sectionLabels[styleScope] + '»' : 'весь сайт' }}</div>
            <div v-if="!styleScope || styleScope === 'hero'" class="sp-hero">
              <div class="sp-h1">Заголовок главного экрана</div>
              <p class="sp-hero-sub">Подзаголовок главного экрана</p>
              <span class="sp-btn">Свяжитесь с нами</span>
            </div>
            <div v-if="styleScope !== 'hero'" class="sp-body" :style="{ background: stylePreview.bg }">
              <div class="sp-h2">ЗАГОЛОВОК РАЗДЕЛА</div>
              <p class="sp-text">Основной текст сайта: описание услуг, отзывы клиентов, рассказ о студии.</p>
              <p class="sp-text sp-light">Второстепенный текст: подписи и пояснения.</p>
              <div class="sp-card">
                <span class="sp-icon"></span>
                <div>
                  <div class="sp-h3">НАЗВАНИЕ УСЛУГИ</div>
                  <span class="sp-price">5 000 руб/м²</span>
                </div>
              </div>
              <span class="sp-btn sp-btn--outline">Заказать</span>
            </div>
          </div>
        </div>
      </section>

      <!-- ── Цифры ── -->
      <section v-if="currentTab === 'stats'" class="tab-body">
        <div class="card-info">Блок с цифрами на сайте («1000+ проектов реализовано»). Порядок меняется перетаскиванием.</div>
        <div class="card">
          <h3>Заголовок блока</h3>
          <p class="hint">Строка над цифрами. Оставьте поле пустым, чтобы блок шёл без заголовка.</p>
          <div class="upload-row">
            <input v-model="statsTitle" maxlength="200" placeholder="Обращаясь к нам, вы помогаете улучшить эту статистику:" class="stats-title-input" />
            <button class="btn-primary" @click="saveStatsTitle">Сохранить</button>
          </div>
        </div>
        <div class="list-toolbar">
          <button class="btn-primary" @click="openStatEdit({})">+ Добавить цифру</button>
        </div>
        <div class="drag-list" @dragover.prevent>
          <div v-for="(st, i) in statsData" :key="st.id"
            class="drag-item"
            draggable="true"
            @dragstart="onDragStart($event, i, 'stats')"
            @dragover.prevent
            @drop.prevent="onDrop(i, 'stats')">
            <span class="drag-handle">⠿</span>
            <div class="drag-info">
              <strong>{{ st.value }}</strong>
              <span class="sec-key">{{ st.label }}</span>
            </div>
            <div class="drag-actions">
              <button class="btn-sm" @click="openStatEdit(st)">✏ Изменить</button>
              <button class="btn-sm btn-danger" @click="deleteStat(st.id)">✕</button>
            </div>
          </div>
        </div>

        <div v-if="editingStat" class="modal-overlay" @click.self="editingStat = null">
          <div class="modal">
            <h3>{{ editingStat.id ? 'Редактировать цифру' : 'Новая цифра' }}</h3>
            <div class="form-grid">
              <label>Значение<input v-model="editingStat.value" placeholder="1000+" /></label>
              <label>Подпись<input v-model="editingStat.label" placeholder="Проектов реализовано" /></label>
            </div>
            <div class="modal-footer">
              <button class="btn-ghost" @click="editingStat = null">Отмена</button>
              <button class="btn-primary" @click="saveStatEdit">Сохранить</button>
            </div>
          </div>
        </div>
      </section>

      <!-- ── Карта объектов ── -->
      <section v-if="currentTab === 'map'" class="tab-body">
        <div class="card-info">
          Блок с картой в конце сайта. Объекты берутся из договоров CRM автоматически (все, кроме расторгнутых): новые договоры появляются на карте в течение шести часов или сразу по кнопке «Обновить карту». Объекты, которых в CRM нет, можно догрузить из файла Excel.
          Адреса клиентов на сайт не передаются: каждая точка сдвинута на 60–150 метров в случайную сторону, а карта не приближается до отдельного дома. Показать, скрыть или переместить блок можно во вкладке «Секции меню».
        </div>
        <div class="card">
          <h3>Состояние карты</h3>
          <div class="map-stats">
            <div><strong>{{ mapInfo.total }}</strong><span>объектов в CRM</span></div>
            <div><strong>{{ mapInfo.extra_total }}</strong><span>загружено из файлов</span></div>
            <div><strong>{{ mapInfo.shown }}</strong><span>показано на карте</span></div>
            <div><strong>{{ mapInfo.not_found }}</strong><span>адрес не найден</span></div>
            <div><strong>{{ mapInfo.hidden }}</strong><span>скрыто вручную</span></div>
            <div><strong>{{ mapInfo.pending }}</strong><span>ждут обработки</span></div>
          </div>
          <p v-if="mapInfo.approximate" class="hint">Из показанных {{ mapInfo.approximate }} найдены с точностью до улицы, остальные — до дома. На карте это незаметно: точки всё равно сдвинуты.</p>
          <div class="list-toolbar">
            <button class="btn-primary" :disabled="mapInfo.running" @click="syncMap">{{ mapInfo.running ? 'Идёт обновление…' : 'Обновить карту' }}</button>
            <span v-if="mapInfo.running" class="hint" style="margin:0">Поиск идёт по одному адресу в секунду, страницу можно не закрывать.</span>
            <span v-else-if="mapInfo.last_error" class="alert-err">{{ mapInfo.last_error }}</span>
          </div>
        </div>
        <div class="card">
          <h3>Объекты из файла Excel</h3>
          <p class="hint">Для объектов, которых нет в CRM, — например, проектов прошлых лет. Нужен файл .xlsx с двумя столбцами: «Город» и «Адрес» (остальные столбцы не читаются). Файлы можно загружать по очереди: новые адреса добавляются к уже загруженным, а адреса, которые уже есть в CRM или были загружены раньше, пропускаются. На карте такие объекты показываются как сданные проекты.</p>
          <div class="list-toolbar">
            <button class="btn-primary" :disabled="mapImporting" @click="$refs.mapFileInput.click()">{{ mapImporting ? 'Загрузка…' : 'Загрузить файл Excel' }}</button>
            <button class="btn-ghost" @click="downloadMapTemplate">Скачать образец файла</button>
            <button v-if="mapInfo.extra_total" class="btn-sm btn-danger" @click="deleteAllMapExtra">Удалить все загруженные ({{ mapInfo.extra_total }})</button>
            <input ref="mapFileInput" type="file" accept=".xlsx" style="display:none" @change="importMapFile" />
          </div>
          <div v-if="mapImportResult" class="map-import-result">
            <p>Добавлено объектов: <strong>{{ mapImportResult.added }}</strong><template v-if="mapImportResult.duplicates">, пропущено повторов: {{ mapImportResult.duplicates }}</template><template v-if="mapImportResult.skipped_count">, строк с ошибками: {{ mapImportResult.skipped_count }}</template>.
              <template v-if="mapImportResult.added"> Координаты ищутся по одному адресу в секунду — объекты появятся на карте по мере поиска.</template></p>
            <ul v-if="mapImportResult.skipped.length">
              <li v-for="line in mapImportResult.skipped" :key="line">{{ line }}</li>
              <li v-if="mapImportResult.skipped_count > mapImportResult.skipped.length">…и ещё {{ mapImportResult.skipped_count - mapImportResult.skipped.length }}</li>
            </ul>
          </div>
        </div>
        <div v-if="mapFailed.length" class="card">
          <h3>Адреса, которые не удалось найти</h3>
          <p class="hint">Этих объектов на карте нет. Чаще всего мешает название ЖК вместо улицы, опечатка или лишние пометки. Исправьте адрес в договоре CRM до вида «город, улица, дом» — объект появится при следующем обновлении карты. Объект из файла удалите в списке ниже и загрузите заново с исправленным адресом.</p>
          <table class="map-failed">
            <thead><tr><th>Договор</th><th>Город</th><th>Адрес</th></tr></thead>
            <tbody>
              <tr v-for="row in mapFailed" :key="row.key">
                <td>{{ row.contract_number }}</td><td>{{ row.city }}</td><td>{{ row.address }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="mapInfo.objects.length" class="card">
          <h3>Объекты на карте</h3>
          <p class="hint">Снимите переключатель, чтобы убрать объект с сайта — например, тестовый договор или объект клиента, который просил его не показывать. Адреса видны только здесь, в панели.</p>
          <input v-model="mapFilter" class="map-filter" placeholder="Поиск по номеру договора, городу или адресу" />
          <div class="map-objects">
            <table class="map-failed">
              <thead><tr><th>Договор</th><th>Город</th><th>Адрес</th><th>Состояние</th><th>Показывать</th><th></th></tr></thead>
              <tbody>
                <tr v-for="row in mapObjectsFiltered" :key="row.key" :class="{ muted: row.state !== 'shown' }">
                  <td>{{ row.contract_number }}</td><td>{{ row.city }}</td><td>{{ row.address }}</td>
                  <td>{{ mapStateLabels[row.state] }}</td>
                  <td>
                    <label v-if="row.can_toggle" class="toggle">
                      <input type="checkbox" :checked="row.state === 'shown'" @change="toggleMapObject(row, $event.target.checked)" />
                      <span class="toggle-track"></span>
                    </label>
                  </td>
                  <td><button v-if="row.source === 'file'" class="btn-sm btn-danger" title="Удалить объект, загруженный из файла" @click="deleteMapExtra(row)">✕</button></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="card">
          <h3>Оформление блока</h3>
          <label>Заголовок<input v-model="mf.map_title" placeholder="ГЕОГРАФИЯ НАШИХ ПРОЕКТОВ" /></label>
          <label style="margin-top:12px">Подзаголовок (необязательно)<input v-model="mf.map_subtitle" placeholder="Работаем в Москве, Санкт-Петербурге и других городах" /></label>
          <label class="cb-row" style="margin-top:14px">
            <input type="checkbox" v-model="mf.map_show_counts" true-value="1" false-value="0" />
            Показывать количество объектов рядом с названиями городов
          </label>
          <p class="hint" style="margin:6px 0 14px">По умолчанию выключено: на карте только объекты из CRM и загруженных файлов, и их число может расходиться с цифрами в блоке «Цифры».</p>
          <div class="form-grid">
            <label v-for="c in mapColors" :key="c.key">Цвет кружков — {{ c.label }}
              <div class="color-row">
                <input type="color" v-model="mf[c.key]" />
                <input v-model="mf[c.key]" maxlength="7" placeholder="#000000" />
              </div>
            </label>
          </div>
          <button class="btn-primary" @click="saveMapSettings">Сохранить оформление</button>
        </div>
      </section>

      <!-- ── Индивидуальный и готовый дизайн ── -->
      <IndividualTab v-if="currentTab === 'individual'" :toast="toast" />
      <ReadyTab v-if="currentTab === 'ready'" :toast="toast" />

      <!-- ── Аналитика / SEO ── -->
      <section v-if="currentTab === 'analytics'" class="tab-body">
        <div class="card-info">
          Все поля здесь необязательные — пустое поле просто не используется. Чтобы видеть посещаемость, достаточно завести счётчик в Яндекс.Метрике и вставить его номер в первое поле. Блок «SEO» отвечает за то, как сайт подписан в поиске, «Open Graph» — как выглядит ссылка в мессенджерах. Остальное можно заполнить позже или не заполнять вовсе.
        </div>
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
import IndividualTab from './IndividualTab.vue'
import ReadyTab from './ReadyTab.vue'
import * as api from './api.js'
import { SERVICE_ICONS, serviceIconPath } from '../serviceIcons.js'
import {
  FONTS, STYLE_DEFAULTS, SIZE_MIN, SIZE_MAX, SECTION_KEYS, SECTION_STYLE_KEY,
  themeVars, loadFont, sectionStyle, parseSectionStyles,
} from '../theme.js'

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
  { id: 'style',     icon: '✎',  label: 'Стиль' },
  { id: 'sections',  icon: '☰',  label: 'Секции меню' },
  { id: 'services',  icon: '◈',  label: 'Услуги' },
  { id: 'individual', icon: '✦', label: 'Индивидуальный дизайн' },
  { id: 'pricing',   icon: '₽',  label: '↳ Цены' },
  { id: 'portfolio', icon: '◉',  label: '↳ Портфолио' },
  { id: 'ready',     icon: '▦',  label: 'Готовый дизайн' },
  { id: 'reviews',   icon: '★',  label: 'Отзывы' },
  { id: 'team',      icon: '◎',  label: 'О нас / команда' },
  { id: 'stats',     icon: '#',  label: 'Цифры' },
  { id: 'map',       icon: '◍',  label: 'Карта объектов' },
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

function onDragStart(e, idx, listName) {
  dragFrom.value = idx; dragKey.value = listName
  // Firefox не начинает перетаскивание, пока в dataTransfer нет данных
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', String(idx))
}
async function onDrop(toIdx, listName) {
  const from = dragFrom.value
  const sameList = dragKey.value === listName
  dragFrom.value = null; dragKey.value = null
  if (!sameList || from === null || from === toIdx) return
  const list = dragLists[listName]
  const arr = list.data.value
  const [item] = arr.splice(from, 1)
  arr.splice(toIdx, 0, item)
  try {
    await list.reorder(arr.map((it, i) => (listName === 'sections' ? { key: it.key, sort_order: i } : { id: it.id, sort_order: i })))
    toast('Порядок сохранён')
  } catch (err) {
    toast('Не удалось сохранить порядок: ' + err.message, 'error')
    list.load()
  }
}

function loadError(e) {
  if (e.message !== '401') toast('Не удалось загрузить данные: ' + e.message, 'error')
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
  phone: '', whatsapp_phone: '', telegram: '', vk_url: '', instagram_url: '', email: '', address: '',
  office_coords: '', yandex_maps_api_key: '',
})
const hf = reactive({ hero_title: '', hero_subtitle: '', hero_cta: '', hero_bg_url: '', logo_url: '', footer_logo_url: '', copyright: '' })
// Заголовок блока «Цифры»: null — настройки ещё нет, на сайте стоит текст по умолчанию
const STATS_TITLE_DEFAULT = 'Обращаясь к нам, вы помогаете улучшить эту статистику:'
const statsTitle = ref(STATS_TITLE_DEFAULT)
async function saveStatsTitle() {
  try { await api.settings.update('stats_title', statsTitle.value.trim()); toast('Заголовок сохранён') }
  catch (e) { toast(e.message, 'error') }
}
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
      if (r.key in hf) hf[r.key] = r.value || ''
      if (r.key === 'cta_method') ctaMethod.value = r.value || 'whatsapp'
      if (r.key === 'stats_title') statsTitle.value = r.value ?? ''
    })
    // Пока координаты не заданы, сайт берёт их из старой ссылки на карту — показываем их же
    if (!sf.office_coords) {
      const legacy = decodeURIComponent(rows.find(r => r.key === 'yandex_map_src')?.value || '').match(/[?&]ll=(-?[\d.]+),(-?[\d.]+)/)
      if (legacy) sf.office_coords = `${legacy[2]}, ${legacy[1]}`
    }
    loadStyle(rows)
    loadMapSettings(rows)
  } catch (e) { loadError(e) }
}
async function saveSettings() {
  sf.whatsapp_phone = sf.whatsapp_phone.replace(/\D/g, '')
  sf.telegram = sf.telegram.trim().replace(/^@/, '')
  if (sf.whatsapp_phone && (sf.whatsapp_phone.length < 10 || sf.whatsapp_phone.length > 15)) {
    toast('Номер WhatsApp должен содержать от 10 до 15 цифр, например 79991234567', 'error'); return
  }
  sf.office_coords = sf.office_coords.trim()
  sf.yandex_maps_api_key = sf.yandex_maps_api_key.trim()
  const coords = sf.office_coords.match(/^(-?\d+(?:\.\d+)?)\s*[,;]\s*(-?\d+(?:\.\d+)?)$/)
  if (sf.office_coords && (!coords || Math.abs(coords[1]) > 90 || Math.abs(coords[2]) > 180)) {
    toast('Координаты офиса — два числа через запятую: широта, долгота. Например: 59.964229, 30.308495', 'error'); return
  }
  try {
    for (const key of Object.keys(sf)) await api.settings.update(key, sf[key])
    toast('Контакты сохранены')
  } catch (e) { toast(e.message, 'error') }
}
async function saveHero() {
  try {
    for (const key of Object.keys(hf)) await api.settings.update(key, hf[key])
    toast('Оформление сохранено')
  } catch (e) { toast(e.message, 'error') }
}
async function saveCta() {
  try { await api.settings.update('cta_method', ctaMethod.value); toast('Метод связи обновлён') }
  catch (e) { toast(e.message, 'error') }
}

// ══ Sections ══
const sectionsData = ref([])
// Названия совпадают с пунктами меню сайта; у секции «Цифры» пункта меню нет
const sectionLabels = {
  hero: 'Главная',
  about: 'О нас',
  services: 'Услуги',
  stats: 'Цифры',
  directions: 'Направления',
  portfolio: 'Портфолио',
  pricing: 'Цены',
  reviews: 'Отзывы',
  contacts: 'Контакты',
  objects_map: 'Карта объектов',
}
const sectionsWithoutMenu = {
  directions: 'Две карточки на главной: «Индивидуальный дизайн» и «Готовый дизайн». В меню на этом месте стоят ссылки на обе страницы',
  portfolio: 'Блок страницы «Индивидуальный дизайн» (на главной не показывается, порядок на него не влияет)',
  pricing: 'Блок страницы «Индивидуальный дизайн» (на главной не показывается, порядок на него не влияет)',
  stats: 'Блок с цифрами — показывается на странице, в меню пункта нет',
  objects_map: 'Карта с объектами из CRM — показывается на странице, в меню пункта нет',
}
function sectionLabel(sec) {
  return sectionLabels[sec.key] || sec.label || sec.key
}
function sectionHint(sec) {
  return sectionsWithoutMenu[sec.key] || 'Пункт меню и блок на странице'
}

async function loadSections() {
  try { sectionsData.value = await api.sections.list() } catch (e) { loadError(e) }
}
async function saveSectionVisibility(sec) {
  try { await api.sections.update(sec.key, { is_visible: sec.is_visible }) }
  catch (e) { toast(e.message, 'error') }
}

// ══ Services ══
const servicesData = ref([])
const editingService = ref(null)

async function loadServices() {
  try { servicesData.value = await api.services.list() } catch (e) { loadError(e) }
}
function openServiceEdit(svc) {
  editingService.value = { title: '', icon: 'star', description: '', is_visible: true, ...svc }
}
async function saveServiceEdit() {
  if (!editingService.value.title.trim()) { toast('Укажите название услуги', 'error'); return }
  try {
    const d = { title: editingService.value.title, icon: editingService.value.icon,
                description: editingService.value.description, is_visible: editingService.value.is_visible }
    if (editingService.value.id) {
      const r = await api.services.update(editingService.value.id, d)
      const i = servicesData.value.findIndex(s => s.id === r.id)
      if (i >= 0) servicesData.value[i] = r
    } else {
      const r = await api.services.create({ ...d, sort_order: servicesData.value.length })
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

// ══ Pricing ══
const pricingData = ref([])
const editingPlan = ref(null)

async function loadPricing() {
  try { pricingData.value = await api.pricing.list() } catch (e) { loadError(e) }
}
function openPlanEdit(plan) {
  editingPlan.value = {
    title: '', price_label: '', whatsapp_text: '', is_featured: false, is_visible: true,
    ...plan,
    items_text: itemsToText(plan.items || []),
  }
}
// Пункт — обычная строка, подпункт — строка с дефисом в начале
function itemsToText(items) {
  return items.flatMap(it => [it.text, ...(it.subitems || []).map(sub => `- ${sub}`)]).join('\n')
}
function textToItems(text) {
  const items = []
  for (const raw of (text || '').split('\n')) {
    const line = raw.trim()
    if (!line) continue
    const sub = line.match(/^[-–—•]\s*(.+)$/)
    if (sub && items.length) items[items.length - 1].subitems.push(sub[1])
    else items.push({ text: sub ? sub[1] : line, sort_order: items.length, subitems: [] })
  }
  return items
}
async function savePlanEdit() {
  if (!editingPlan.value.title.trim()) { toast('Укажите название плана', 'error'); return }
  try {
    const payload = { title: editingPlan.value.title, price_label: editingPlan.value.price_label,
                      whatsapp_text: editingPlan.value.whatsapp_text, is_featured: editingPlan.value.is_featured,
                      is_visible: editingPlan.value.is_visible, items: textToItems(editingPlan.value.items_text) }
    if (editingPlan.value.id) {
      const r = await api.pricing.update(editingPlan.value.id, payload)
      const i = pricingData.value.findIndex(p => p.id === r.id)
      if (i >= 0) pricingData.value[i] = r
    } else {
      const r = await api.pricing.create({ ...payload, sort_order: pricingData.value.length })
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

// ══ Portfolio ══
const portfolioData = ref([])
const editingPortfolio = ref(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadTotal = ref(0)

async function loadPortfolio() {
  try { portfolioData.value = await api.portfolio.list() } catch (e) { loadError(e) }
}
async function uploadPortfolio(e) {
  const files = Array.from(e.target.files)
  if (!files.length) return
  uploading.value = true; uploadTotal.value = files.length; uploadProgress.value = 0
  const failed = []
  for (const file of files) {
    try {
      const r = await api.portfolio.upload(file)
      const created = await api.portfolio.create({ url: r.url, alt: '', is_visible: true, sort_order: portfolioData.value.length })
      portfolioData.value.push(created)
      uploadProgress.value++
    } catch (err) { failed.push(`${file.name}: ${err.message}`) }
  }
  uploading.value = false; e.target.value = ''
  if (failed.length) toast(`Загружено ${uploadProgress.value} из ${files.length}. Не загружены — ${failed.join('; ')}`, 'error')
  else toast(`Загружено ${files.length} фото`)
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

// ══ Reviews ══
const reviewsData = ref([])
const editingReview = ref(null)

async function loadReviews() {
  try { reviewsData.value = await api.reviews.list() } catch (e) { loadError(e) }
}
function openReviewEdit(rev) {
  editingReview.value = { author_name: '', author_city: '', avatar_url: '', text: '', is_active: true, ...rev }
}
async function saveReviewEdit() {
  if (!editingReview.value.author_name.trim() || !editingReview.value.text.trim()) {
    toast('Заполните имя клиента и текст отзыва', 'error'); return
  }
  try {
    const d = { author_name: editingReview.value.author_name, author_city: editingReview.value.author_city,
                avatar_url: editingReview.value.avatar_url, text: editingReview.value.text, is_active: editingReview.value.is_active }
    if (editingReview.value.id) {
      const r = await api.reviews.update(editingReview.value.id, d)
      const i = reviewsData.value.findIndex(x => x.id === r.id)
      if (i >= 0) reviewsData.value[i] = r
    } else {
      const r = await api.reviews.create({ ...d, sort_order: reviewsData.value.length })
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

// ══ Team ══
const teamData = ref([])
const editingTeam = ref(null)

async function loadTeam() {
  try { teamData.value = await api.team.list() } catch (e) { loadError(e) }
}
function openTeamEdit(m) {
  editingTeam.value = { name: '', position: '', role_label: '', description: '', photo_url: '', is_visible: true, ...m }
}
async function saveTeamEdit() {
  if (!editingTeam.value.name.trim()) { toast('Укажите имя', 'error'); return }
  try {
    const d = { name: editingTeam.value.name, position: editingTeam.value.position || '',
                role_label: editingTeam.value.role_label || '',
                description: editingTeam.value.description || '', photo_url: editingTeam.value.photo_url || '',
                is_visible: editingTeam.value.is_visible }
    if (editingTeam.value.id) {
      const r = await api.team.update(editingTeam.value.id, d)
      const i = teamData.value.findIndex(t => t.id === r.id)
      if (i >= 0) teamData.value[i] = r
    } else {
      const r = await api.team.create({ ...d, sort_order: teamData.value.length })
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

// ══ Style ══
const stf = reactive({ ...STYLE_DEFAULTS })
const styleColors = [
  { key: 'style_accent', label: 'Акцентный цвет (кнопки, иконки, цены)' },
  { key: 'style_head_color', label: 'Цвет заголовков' },
  { key: 'style_text_color', label: 'Цвет основного текста' },
  { key: 'style_text_light_color', label: 'Цвет второстепенного текста' },
  { key: 'style_decor_color', label: 'Цвет декора по краям' },
]
// Стиль отдельных блоков: в объекте блока лежат только поля, отмеченные галочкой
const styleScope = ref('')
const secStyles = reactive(Object.fromEntries(SECTION_KEYS.map(key => [key, {}])))
const curSec = computed(() => secStyles[styleScope.value])
const sectionFields = [
  { key: 'font_head', type: 'font', label: 'Шрифт заголовков', global: 'style_font_head' },
  { key: 'font_body', type: 'font', label: 'Шрифт текста', global: 'style_font_body' },
  { key: 'head_size', type: 'size', label: 'Размер заголовков', global: 'style_head_size' },
  { key: 'text_size', type: 'size', label: 'Размер текста', global: 'style_text_size' },
  { key: 'bg', type: 'color', label: 'Цвет фона блока' },
  { key: 'accent', type: 'color', label: 'Акцентный цвет', global: 'style_accent' },
  { key: 'head_color', type: 'color', label: 'Цвет заголовков', global: 'style_head_color' },
  { key: 'text_color', type: 'color', label: 'Цвет основного текста', global: 'style_text_color' },
  { key: 'text_light_color', type: 'color', label: 'Цвет второстепенного текста', global: 'style_text_light_color' },
]
// У главного экрана фон — фотография, поэтому цвет фона для него не предлагается
const scopeFields = computed(() => sectionFields.filter(f => !(styleScope.value === 'hero' && f.key === 'bg')))
// Фон блоков на сайте до настройки — чтобы предпросмотр был похож на реальный блок
const defaultSectionBg = { about: '#f8f8f8', directions: '#f8f8f8', portfolio: '#f8f8f8', reviews: '#f8f8f8', stats: '#1a1a1a' }

function toggleSecField(field, checked) {
  if (!checked) { delete curSec.value[field.key]; return }
  // Стартовое значение — то, что блок показывает сейчас, чтобы включение галочки ничего не меняло
  curSec.value[field.key] = field.global ? String(stf[field.global]) : (defaultSectionBg[styleScope.value] || '#ffffff')
}
function resetSection() {
  for (const key of Object.keys(curSec.value)) delete curSec.value[key]
  toast('Настройки блока сброшены в форме — нажмите «Сохранить стиль», чтобы применить')
}

// Предпросмотр использует те же переменные, что и сайт; шрифты подгружаются по мере выбора
const stylePreview = computed(() => {
  const theme = themeVars(stf)
  theme.fonts.forEach(loadFont)
  const scope = styleScope.value
  const sec = scope ? curSec.value : {}
  const { background, ...secVars } = sectionStyle(scope, sec, stf)
  const vars = { ...theme.vars, ...secVars }
  if (scope === 'stats') {
    // Блок цифр тёмный: без своих цветов текст в нём светлый
    if (!sec.text_color) vars['--text'] = '#ffffff'
    if (!sec.text_light_color) vars['--text-light'] = 'rgba(255,255,255,0.7)'
    if (!sec.head_color) vars['--head-color'] = '#ffffff'
  }
  if (scope === 'hero') vars['--sp-hero-text'] = sec.text_color || '#ffffff'
  if (scope === 'hero' && sec.head_color) vars['--sp-hero-title'] = sec.head_color
  vars['--sp-text-scale'] = (sec.text_size || theme.textSize) / 100
  vars['--sp-head-scale'] = (sec.head_size || stf.style_head_size) / 100
  return { vars, bg: background || defaultSectionBg[scope] || '#ffffff' }
})

function loadStyle(rows) {
  rows.forEach(r => { if (r.key in stf && r.value) stf[r.key] = r.value })
  const saved = parseSectionStyles(Object.fromEntries(rows.map(r => [r.key, r.value])))
  for (const key of SECTION_KEYS) {
    for (const field of Object.keys(secStyles[key])) delete secStyles[key][field]
    Object.assign(secStyles[key], saved[key] || {})
  }
}
async function saveStyle() {
  const isHex = v => /^#[0-9a-f]{6}$/i.test(v)
  const badColor = styleColors.find(c => !isHex(stf[c.key]))
  if (badColor) { toast(`«${badColor.label}»: цвет должен быть в виде #RRGGBB, например #E8622A`, 'error'); return }
  const sections = {}
  for (const key of SECTION_KEYS) {
    const bad = sectionFields.find(f => f.type === 'color' && f.key in secStyles[key] && !isHex(secStyles[key][f.key]))
    if (bad) { toast(`Блок «${sectionLabels[key]}», «${bad.label}»: цвет должен быть в виде #RRGGBB`, 'error'); return }
    if (Object.keys(secStyles[key]).length) sections[key] = { ...secStyles[key] }
  }
  try {
    for (const key of Object.keys(stf)) await api.settings.update(key, String(stf[key]))
    await api.settings.update(SECTION_STYLE_KEY, JSON.stringify(sections))
    toast('Стиль сохранён — обновите страницу сайта, чтобы увидеть изменения')
  } catch (e) { toast(e.message, 'error') }
}
function resetStyle() {
  Object.assign(stf, STYLE_DEFAULTS)
  toast('Исходный стиль выставлен в форме — нажмите «Сохранить стиль», чтобы применить его на сайте')
}

// ══ Objects map ══
const mapInfo = reactive({ total: 0, extra_total: 0, shown: 0, approximate: 0, not_found: 0, pending: 0, hidden: 0, running: false, last_error: null, objects: [] })
const mapStateLabels = { shown: 'на карте', hidden: 'скрыт вручную', not_found: 'адрес не найден', pending: 'ждёт обработки' }
const mapFilter = ref('')
const mapFailed = computed(() => mapInfo.objects.filter(o => o.state === 'not_found'))
const mapObjectsFiltered = computed(() => {
  const query = mapFilter.value.trim().toLowerCase()
  if (!query) return mapInfo.objects
  return mapInfo.objects.filter(o => `${o.contract_number} ${o.city} ${o.address}`.toLowerCase().includes(query))
})
async function toggleMapObject(row, show) {
  try {
    if (row.source === 'file') await api.map.setExtraHidden(row.extra_id, !show)
    else await api.map.setHidden(row.contract_id, !show)
    await loadMap()
  } catch (e) { toast(e.message, 'error'); loadMap() }
}
const mapImporting = ref(false)
const mapImportResult = ref(null)
async function importMapFile(e) {
  const file = e.target.files[0]
  e.target.value = ''
  if (!file) return
  mapImporting.value = true
  mapImportResult.value = null
  try {
    const { added, duplicates, skipped, skipped_count, ...info } = await api.map.importFile(file)
    mapImportResult.value = { added, duplicates, skipped, skipped_count }
    applyMapInfo(info)
    toast(added ? `Добавлено объектов: ${added}` : 'Новых объектов в файле нет', added ? 'success' : 'error')
  } catch (err) { toast(err.message, 'error') }
  mapImporting.value = false
}
async function downloadMapTemplate() {
  try { await api.map.downloadTemplate() } catch (e) { toast(e.message, 'error') }
}
async function deleteMapExtra(row) {
  if (!confirm(`Удалить объект «${row.city}, ${row.address}»?`)) return
  try { await api.map.deleteExtra(row.extra_id); await loadMap(); toast('Удалено') } catch (e) { toast(e.message, 'error') }
}
async function deleteAllMapExtra() {
  if (!confirm(`Удалить все объекты, загруженные из файлов (${mapInfo.extra_total})? Объекты из договоров CRM останутся.`)) return
  try { await api.map.deleteAllExtra(); mapImportResult.value = null; await loadMap(); toast('Загруженные объекты удалены') } catch (e) { toast(e.message, 'error') }
}
const mf = reactive({ map_title: '', map_subtitle: '', map_show_counts: '0', map_color_done: '', map_color_work: '', map_color_supervision: '' })
// Цвет сданных проектов по умолчанию совпадает с акцентным цветом сайта и меняется вместе с ним
const mapColors = [
  { key: 'map_color_done', label: 'сданные проекты', fallback: () => stf.style_accent },
  { key: 'map_color_work', label: 'в работе', fallback: () => '#2b6cb0' },
  { key: 'map_color_supervision', label: 'авторский надзор', fallback: () => '#2f9e6b' },
]
let mapPollTimer = null

function loadMapSettings(rows) {
  rows.forEach(r => { if (r.key in mf && r.value) mf[r.key] = r.value })
  for (const c of mapColors) if (!mf[c.key]) mf[c.key] = c.fallback()
}
async function saveMapSettings() {
  const bad = mapColors.find(c => !/^#[0-9a-f]{6}$/i.test(mf[c.key]))
  if (bad) { toast(`Цвет «${bad.label}» должен быть в виде #RRGGBB, например #2b6cb0`, 'error'); return }
  try {
    for (const key of ['map_title', 'map_subtitle', 'map_show_counts']) await api.settings.update(key, mf[key])
    // Незаданный цвет хранится пустым, чтобы он и дальше следовал значению по умолчанию
    for (const c of mapColors) await api.settings.update(c.key, mf[c.key].toLowerCase() === c.fallback().toLowerCase() ? '' : mf[c.key])
    toast('Оформление карты сохранено')
  } catch (e) { toast(e.message, 'error') }
}
function applyMapInfo(info) {
  Object.assign(mapInfo, info)
  clearTimeout(mapPollTimer)
  // Пока идёт поиск координат, состояние обновляется само
  if (mapInfo.running) mapPollTimer = setTimeout(loadMap, 3000)
}
async function loadMap() {
  try { applyMapInfo(await api.map.status()) } catch (e) { loadError(e) }
}
async function syncMap() {
  try { applyMapInfo(await api.map.sync()) } catch (e) { toast(e.message, 'error') }
}

// ══ Stats ══
const statsData = ref([])
const editingStat = ref(null)

async function loadStats() {
  try { statsData.value = await api.stats.list() } catch (e) { loadError(e) }
}
function openStatEdit(st) { editingStat.value = { value: '', label: '', ...st } }
async function saveStatEdit() {
  if (!editingStat.value.value.trim() || !editingStat.value.label.trim()) { toast('Заполните значение и подпись', 'error'); return }
  try {
    const d = { value: editingStat.value.value, label: editingStat.value.label }
    if (editingStat.value.id) {
      const r = await api.stats.update(editingStat.value.id, d)
      const i = statsData.value.findIndex(s => s.id === r.id)
      if (i >= 0) statsData.value[i] = r
    } else {
      statsData.value.push(await api.stats.create({ ...d, sort_order: statsData.value.length }))
    }
    editingStat.value = null; toast('Сохранено')
  } catch (e) { toast(e.message, 'error') }
}
async function deleteStat(id) {
  if (!confirm('Удалить цифру?')) return
  try { await api.stats.delete(id); statsData.value = statsData.value.filter(s => s.id !== id) }
  catch (e) { toast(e.message, 'error') }
}

// Списки с перетаскиванием: данные, сохранение порядка и перезагрузка при ошибке
const dragLists = {
  sections:  { data: sectionsData,  reorder: api.sections.reorder,  load: loadSections },
  services:  { data: servicesData,  reorder: api.services.reorder,  load: loadServices },
  pricing:   { data: pricingData,   reorder: api.pricing.reorder,   load: loadPricing },
  portfolio: { data: portfolioData, reorder: api.portfolio.reorder, load: loadPortfolio },
  reviews:   { data: reviewsData,   reorder: api.reviews.reorder,   load: loadReviews },
  team:      { data: teamData,      reorder: api.team.reorder,      load: loadTeam },
  stats:     { data: statsData,     reorder: api.stats.reorder,     load: loadStats },
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
  try {
    const r = await api.analytics.get()
    for (const key of Object.keys(af)) if (r?.[key] != null) af[key] = r[key]
  } catch (e) { loadError(e) }
}
async function saveAnalytics() {
  try { await api.analytics.update({ ...af }); toast('Аналитика сохранена') }
  catch (e) { toast(e.message, 'error') }
}

// ══ Init ══
function loadAll() {
  loadSettings(); loadSections(); loadServices(); loadPricing()
  loadPortfolio(); loadReviews(); loadTeam(); loadStats(); loadMap(); loadAnalytics()
}
onMounted(() => { if (authed.value) loadAll() })
</script>

<!-- Без scoped: классы панели используют и вкладки-компоненты. Панель собирается отдельно от сайта, на его страницы эти стили не попадают -->
<style>
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
.modal--wide { max-width: 1180px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 6px; }

.upload-row { display: flex; gap: 8px; }
.upload-row input { flex: 1; }

.footer-logo-preview { margin-top: 6px; background: #1a1a1a; border-radius: 8px; padding: 14px 18px; display: inline-flex; align-self: flex-start; }
.footer-logo-preview img { height: 40px; width: auto; max-width: 220px; object-fit: contain; display: block; }
.stats-title-input { flex: 1; border: 1px solid #d9d9d9; border-radius: 6px; padding: 8px 12px; font-size: 0.9rem; font-family: inherit; outline: none; }
.stats-title-input:focus { border-color: #c0392b; }
.preview-img { max-width: 100%; max-height: 200px; border-radius: 8px; object-fit: contain; border: 1px solid #e8eaed; }
.preview-avatar { width: 80px; height: 80px; border-radius: 50%; object-fit: cover; }
.preview-og { max-width: 100%; max-height: 150px; border-radius: 6px; object-fit: contain; border: 1px solid #e8eaed; }

.field { display: flex; flex-direction: column; gap: 5px; font-size: 0.85rem; color: #374151; }

.map-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 14px; }
.map-stats div { background: #f7f8fa; border-radius: 8px; padding: 12px 14px; display: flex; flex-direction: column; gap: 2px; }
.map-stats strong { font-size: 1.5rem; font-weight: 700; color: #1a1a1a; }
.map-stats span { font-size: 0.8rem; color: #6b7280; }
.map-import-result { margin-top: 12px; background: #f7f8fa; border-radius: 8px; padding: 12px 14px; font-size: 0.88rem; }
.map-import-result p { margin: 0; }
.map-import-result ul { margin: 8px 0 0; padding-left: 18px; color: #6b7280; max-height: 160px; overflow: auto; }
.map-failed { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.map-failed th { text-align: left; font-weight: 600; color: #6b7280; padding: 6px 10px; border-bottom: 1px solid #e8eaed; }
.map-failed td { padding: 6px 10px; border-bottom: 1px solid #f0f1f3; vertical-align: top; }
.map-failed td:first-child { white-space: nowrap; }
.map-failed tr.muted td { color: #9ca3af; }
.map-filter { width: 100%; border: 1px solid #d9d9d9; border-radius: 6px; padding: 8px 12px; font-size: 0.9rem; margin-bottom: 10px; outline: none; }
.map-filter:focus { border-color: #c0392b; }
.map-objects { max-height: 460px; overflow: auto; border: 1px solid #f0f1f3; border-radius: 8px; }
.map-objects thead th { position: sticky; top: 0; background: #fff; }

.style-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(280px, 420px); gap: 20px; align-items: start; }
.style-form { display: flex; flex-direction: column; gap: 20px; }
.color-row { display: flex; gap: 8px; align-items: center; }
.color-row input[type="color"] { width: 44px; height: 36px; padding: 2px; cursor: pointer; flex-shrink: 0; }
.color-row input:not([type="color"]) { flex: 1; min-width: 0; font-family: Consolas, monospace; }
label input[type="range"] { padding: 0; border: none; accent-color: #c0392b; }
.style-preview { position: sticky; top: 16px; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.07); font-family: var(--font-body); font-size: calc(16px * var(--sp-text-scale)); color: var(--text); line-height: 1.6; }
.sp-label { font-family: Inter, sans-serif; font-size: 12px; color: #9ca3af; padding: 8px 16px; border-bottom: 1px solid #e8eaed; }
.scope-row { display: flex; flex-wrap: wrap; gap: 8px; }
.scope-chip { background: #fff; border: 1px solid #d9d9d9; border-radius: 16px; padding: 6px 14px; font-size: 0.85rem; cursor: pointer; color: #374151; }
.scope-chip:hover { background: #f3f4f6; }
.scope-chip.custom::after { content: ' •'; color: #c0392b; font-weight: 700; }
.scope-chip.active { background: #c0392b; border-color: #c0392b; color: #fff; }
.scope-chip.active.custom::after { color: #fff; }
.sec-field { display: grid; grid-template-columns: 240px minmax(0, 1fr); gap: 12px; align-items: center; padding: 8px 0; border-top: 1px solid #f0f1f3; }
.sec-field-name { cursor: pointer; }
.sec-field select { border: 1px solid #d9d9d9; border-radius: 6px; padding: 8px 12px; font-size: 0.9rem; font-family: inherit; }
.sec-field input:not([type="checkbox"]):not([type="range"]) { border: 1px solid #d9d9d9; border-radius: 6px; padding: 8px 12px; font-size: 0.9rem; }
.sec-inherit { font-size: 0.82rem; color: #9ca3af; }
.size-row { display: flex; align-items: center; gap: 10px; font-size: 0.85rem; color: #374151; }
.size-row input { flex: 1; accent-color: #c0392b; }
@media (max-width: 700px) { .sec-field { grid-template-columns: 1fr; } }
.sp-hero { background: linear-gradient(135deg, #2b2b2b, #555); color: var(--sp-hero-text, #fff); text-align: center; padding: 28px 16px; }
.sp-h1 { font-family: var(--font-head); font-weight: 800; font-size: calc(26px * var(--sp-head-scale)); line-height: 1.25; margin-bottom: 10px; color: var(--sp-hero-title, inherit); }
.sp-hero-sub { font-size: 1em; opacity: 0.9; margin-bottom: 14px; }
.sp-body { padding: 20px 16px; display: flex; flex-direction: column; gap: 12px; align-items: flex-start; }
.sp-h2 { font-family: var(--font-head); font-weight: 700; font-size: calc(22px * var(--sp-head-scale)); color: var(--head-color); letter-spacing: 0.03em; line-height: 1.25; }
.sp-h3 { font-family: var(--font-head); font-weight: 700; font-size: 1em; color: var(--head-color); }
.sp-text { font-size: 0.95em; }
.sp-light { color: var(--text-light); font-size: 0.9em; }
.sp-card { display: flex; align-items: center; gap: 12px; background: #f8f8f8; border: 1px solid #e0e0e0; border-radius: 10px; padding: 12px 14px; width: 100%; }
.sp-icon { width: 40px; height: 40px; border-radius: 50%; background: var(--accent); flex-shrink: 0; }
.sp-price { color: var(--accent); font-weight: 700; }
.sp-btn { display: inline-block; background: var(--accent); color: #fff; font-family: var(--font-head); font-weight: 600; font-size: 0.9em; padding: 10px 22px; border-radius: 8px; }
.sp-btn--outline { background: transparent; color: var(--accent); border: 2px solid var(--accent); }
@media (max-width: 1100px) { .style-layout { grid-template-columns: 1fr; } .style-preview { position: static; } }
.icon-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.icon-pick { width: 44px; height: 44px; border-radius: 50%; border: 2px solid transparent; background: #e5e7eb; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.icon-pick svg { width: 22px; height: 22px; fill: #6b7280; }
.icon-pick:hover { background: #d1d5db; }
.icon-pick.active { background: #c0392b; border-color: #7f1d1d; }
.icon-pick.active svg { fill: #fff; }
.svc-icon { width: 32px; height: 32px; border-radius: 50%; background: #c0392b; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.svc-icon svg { width: 16px; height: 16px; fill: #fff; }
</style>
