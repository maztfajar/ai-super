import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import id from './id'
import en from './en'
import ar from './ar'
import jv from './jv'
import jp from './jp'

const resources = {
  id: { translation: id },
  en: { translation: en },
  ar: { translation: ar },
  jv: { translation: jv },
  jp: { translation: jp },
}

console.log('🌍 i18n: Starting initialization...')

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'id',
    debug: false,

    interpolation: {
      escapeValue: false, // React already does escaping
    },

    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      lookupLocalStorage: 'ai-super-language',
      caches: ['localStorage'],
    },
  })

console.log('✅ i18n: Initialized successfully - language:', i18n.language)

export default i18n