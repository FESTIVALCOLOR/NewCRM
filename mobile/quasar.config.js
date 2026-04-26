import { configure } from 'quasar/wrappers'

export default configure(function (/* ctx */) {
  return {
    boot: [
      'axios'
    ],

    css: [
      'app.scss'
    ],

    extras: [
      'material-icons',
      'roboto-font'
    ],

    build: {
      target: {
        browser: ['es2022', 'firefox115', 'chrome115', 'safari14']
      },
      vueRouterMode: 'history',

      env: {
        API_URL: process.env.API_URL || 'https://crm.festivalcolor.ru'
      },

      vitePlugins: []
    },

    devServer: {
      port: 9000,
      open: false,
      proxy: {
        '/api': {
          target: 'https://crm.festivalcolor.ru',
          changeOrigin: true,
          secure: true
        }
      }
    },

    framework: {
      config: {
        brand: {
          primary: '#333333',
          secondary: '#F8F9FA',
          accent: '#ffd93c',
          dark: '#333333',
          positive: '#27AE60',
          negative: '#E74C3C',
          info: '#85C1E9',
          warning: '#F39C12'
        },
        notify: {
          position: 'top',
          timeout: 3000
        },
        loading: {}
      },

      plugins: [
        'Notify',
        'Dialog',
        'Loading',
        'LocalStorage',
        'SessionStorage',
        'Meta'
      ]
    },

    animations: [
      'fadeIn',
      'fadeOut',
      'slideInRight',
      'slideOutLeft'
    ],

    pwa: {
      // InjectManifest: custom-service-worker.js — главный SW-файл.
      // Workbox inject-ит в него precache-манифест через self.__WB_MANIFEST.
      // Позволяет использовать registerRoute + CacheFirst для кеширования картинок.
      workboxMode: 'InjectManifest',

      injectPwaMetaTags: true,
      swFilename: 'sw.js',
      manifestFilename: 'manifest.json',
      useCredentialsForManifestTag: false,

      extendInjectManifestOptions(cfg) {
        // Исключаем тяжёлые чанки из precache (pdf.js ~433KB, BarChart ~181KB) —
        // они будут закешированы через runtime CacheFirst при первом обращении
        cfg.globIgnores = cfg.globIgnores || []
        cfg.globIgnores.push(
          '**/pdf-*.js',
          '**/pdf-*.mjs',
          '**/BarChart-*.js',
        )
      },

      extendManifestJson(json) {
        json.name = 'Interior Studio CRM'
        json.short_name = 'IS CRM'
        json.description = 'CRM для интерьерного бюро Festival Color'
        json.display = 'standalone'
        json.orientation = 'any'
        json.background_color = '#ffffff'
        json.theme_color = '#2e7d32'
        json.lang = 'ru'
        json.start_url = '/?source=pwa'
        json.scope = '/'
        json.categories = ['business', 'productivity']
        json.icons = [
          {
            src: '/icons/icon-128x128.png',
            sizes: '128x128',
            type: 'image/png'
          },
          {
            src: '/icons/icon-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: '/icons/icon-256x256.png',
            sizes: '256x256',
            type: 'image/png'
          },
          {
            src: '/icons/icon-384x384.png',
            sizes: '384x384',
            type: 'image/png'
          },
          {
            src: '/icons/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          },
          {
            src: '/icons/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any'
          }
        ]
      }
    }
  }
})
