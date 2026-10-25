const isDevelopment =
  process.env.NODE_ENV === 'development' || process.env.npm_lifecycle_event === 'dev'
const devBackend = (process.env.POKEDEX_DEV_BACKEND || 'http://localhost:8080').replace(/\/$/, '')

export default defineNuxtConfig({
  compatibilityDate: '2026-10-09',
  devtools: { enabled: false },
  telemetry: false,
  modules: ['@nuxt/ui', '@nuxtjs/i18n', '@nuxt/image', '@nuxt/eslint'],
  css: ['~/assets/css/main.css'],
  ui: {
    fonts: false,
  },
  icon: {
    provider: 'none',
    clientBundle: {
      scan: true,
      icons: ['lucide:arrow-left', 'lucide:check', 'lucide:chevron-down', 'lucide:search'],
    },
  },
  runtimeConfig: {
    apiBase: process.env.NUXT_API_BASE || (isDevelopment ? devBackend : 'http://localhost:8000'),
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || '/api',
      siteUrl:
        process.env.NUXT_PUBLIC_SITE_URL ||
        (isDevelopment ? 'http://localhost:3000' : 'http://localhost:8080'),
    },
  },
  i18n: {
    strategy: 'prefix',
    defaultLocale: 'zh-Hans',
    locales: [
      { code: 'zh-Hans', language: 'zh-CN', name: '简体中文', file: 'zh-Hans.json' },
      { code: 'en', language: 'en-US', name: 'English', file: 'en.json' },
    ],
    langDir: 'locales',
    detectBrowserLanguage: false,
  },
  image: {
    provider: 'none',
  },
  nitro: {
    devProxy: {
      '/api/v1': { target: `${devBackend}/api/v1`, changeOrigin: true },
      '/media': { target: `${devBackend}/media`, changeOrigin: true },
    },
    routeRules: isDevelopment
      ? {}
      : {
          '/**': { swr: 3600 },
          '/pokemon/**': { swr: 86400 },
          '/types/**': { swr: 86400 },
        },
  },
  app: {
    head: {
      htmlAttrs: { lang: 'zh-Hans' },
      titleTemplate: '%s · Pokédex',
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'theme-color', content: '#ef4444' },
      ],
    },
  },
  typescript: {
    strict: true,
    typeCheck: true,
  },
})
