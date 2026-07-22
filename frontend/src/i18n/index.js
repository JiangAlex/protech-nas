import { createI18n } from 'vue-i18n'
import zhTW from '../locales/zh-TW.json'
import en from '../locales/en.json'

const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem('locale') || 'zh-TW',
  fallbackLocale: 'en',
  messages: {
    'zh-TW': zhTW,
    en,
  },
})

export default i18n
