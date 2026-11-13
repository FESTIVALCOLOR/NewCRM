// Применяет настройки вкладки «Аналитика / SEO» из админки к странице сайта

function setMeta(attr, key, content) {
  if (!content) return
  let el = document.head.querySelector(`meta[${attr}="${key}"]`)
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute(attr, key)
    document.head.appendChild(el)
  }
  el.setAttribute('content', content)
}

function addScript({ src, code, type }, parent = document.head) {
  const el = document.createElement('script')
  if (type) el.type = type
  if (src) { el.src = src; el.async = true }
  if (code) el.textContent = code
  parent.appendChild(el)
}

// innerHTML не исполняет <script>, поэтому скрипты пересоздаются вручную
function injectHtml(html, parent) {
  if (!html) return
  const tpl = document.createElement('template')
  tpl.innerHTML = html
  tpl.content.childNodes.forEach(node => {
    if (node.nodeName !== 'SCRIPT') { parent.appendChild(node.cloneNode(true)); return }
    const el = document.createElement('script')
    for (const a of node.attributes) el.setAttribute(a.name, a.value)
    el.textContent = node.textContent
    parent.appendChild(el)
  })
}

function applySeo(a) {
  if (a.meta_title) document.title = a.meta_title
  setMeta('name', 'description', a.meta_description)
  setMeta('name', 'keywords', a.meta_keywords)
  setMeta('name', 'robots', a.robots)
  setMeta('name', 'google-site-verification', a.google_search_console_key)
  setMeta('name', 'yandex-verification', a.yandex_webmaster_key)
  setMeta('property', 'og:title', a.og_title || a.meta_title)
  setMeta('property', 'og:description', a.og_description || a.meta_description)
  setMeta('property', 'og:image', a.og_image_url)
  if (a.canonical_url) {
    let link = document.head.querySelector('link[rel="canonical"]')
    if (!link) { link = document.createElement('link'); link.rel = 'canonical'; document.head.appendChild(link) }
    link.href = a.canonical_url
  }
}

function applySchemaOrg(a) {
  if (!a.schema_org_name) return
  const data = { '@context': 'https://schema.org', '@type': 'LocalBusiness', name: a.schema_org_name, url: a.canonical_url || location.origin }
  if (a.schema_org_phone) data.telephone = a.schema_org_phone
  if (a.schema_org_address) data.address = a.schema_org_address
  if (a.schema_org_price_range) data.priceRange = a.schema_org_price_range
  if (a.og_image_url) data.image = a.og_image_url
  if (a.schema_org_opening_hours) data.openingHours = a.schema_org_opening_hours.split('\n').map(s => s.trim()).filter(Boolean)
  if (a.schema_org_latitude && a.schema_org_longitude) {
    data.geo = { '@type': 'GeoCoordinates', latitude: a.schema_org_latitude, longitude: a.schema_org_longitude }
  }
  addScript({ type: 'application/ld+json', code: JSON.stringify(data) })
}

function applyCounters(a) {
  const ym = String(a.yandex_metrika_id || '').replace(/\D/g, '')
  if (ym) {
    addScript({ code: `(function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};m[i].l=1*new Date();k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})(window,document,"script","https://mc.yandex.ru/metrika/tag.js","ym");ym(${ym},"init",{clickmap:true,trackLinks:true,accurateTrackBounce:true,webvisor:${a.yandex_metrika_webvisor !== false}});` })
  }
  const ga = String(a.google_analytics_id || '').trim()
  if (/^G-[A-Z0-9]+$/i.test(ga)) {
    addScript({ src: `https://www.googletagmanager.com/gtag/js?id=${ga}` })
    addScript({ code: `window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}gtag("js",new Date());gtag("config","${ga}");` })
  }
  const gtm = String(a.google_tag_manager_id || '').trim()
  if (/^GTM-[A-Z0-9]+$/i.test(gtm)) {
    addScript({ code: `(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({"gtm.start":new Date().getTime(),event:"gtm.js"});var f=d.getElementsByTagName(s)[0],j=d.createElement(s);j.async=true;j.src="https://www.googletagmanager.com/gtm.js?id="+i;f.parentNode.insertBefore(j,f)})(window,document,"script","dataLayer","${gtm}");` })
  }
  const vk = String(a.vk_pixel_id || '').trim()
  if (/^[\w-]+$/.test(vk)) {
    addScript({ code: `!function(){var t=document.createElement("script");t.async=!0,t.src="https://vk.com/js/api/openapi.js?169",t.onload=function(){VK.Retargeting.Init("${vk}"),VK.Retargeting.Hit()},document.head.appendChild(t)}();` })
  }
}

let applied = false

export function applyAnalytics(a) {
  if (!a || applied) return
  applied = true
  applySeo(a)
  applySchemaOrg(a)
  applyCounters(a)
  injectHtml(a.custom_head_scripts, document.head)
  injectHtml(a.custom_body_end_scripts, document.body)
}
