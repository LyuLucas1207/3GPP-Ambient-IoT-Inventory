import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import {
  AppLocale,
  DEFAULT_LOCALE,
  LOCALES,
  LOCALE_STORAGE_KEY,
  readStoredLocale,
} from '@/i18n/locales'
import en from '@/i18n/locales/en.json'
import fr from '@/i18n/locales/fr.json'
import zh from '@/i18n/locales/zh.json'
import explainEn from '@/i18n/locales/explain-en.json'
import explainFr from '@/i18n/locales/explain-fr.json'
import explainZh from '@/i18n/locales/explain-zh.json'
import glossaryEn from '@/i18n/locales/glossary-en.json'
import glossaryFr from '@/i18n/locales/glossary-fr.json'
import glossaryZh from '@/i18n/locales/glossary-zh.json'

function mergeExplain(
  base: Record<string, unknown>,
  explain: Record<string, unknown>,
  overlay?: Record<string, unknown>,
) {
  const extra = overlay ?? {}
  const baseMaps = (base.maps ?? {}) as Record<string, unknown>
  const explainMaps = (explain.maps ?? {}) as Record<string, unknown>
  const extraMaps = (extra.maps ?? {}) as Record<string, unknown>
  const extraEnergy = (extra.energy ?? {}) as Record<string, unknown>
  const explainEnergy = (explain.energy ?? {}) as Record<string, unknown>
  const baseEnergy = (base.energy ?? {}) as Record<string, unknown>
  return {
    ...base,
    ...explain,
    ...extra,
    energy: {
      ...baseEnergy,
      ...explainEnergy,
      ...extraEnergy,
      y: {
        ...((baseEnergy.y ?? {}) as object),
        ...((explainEnergy.y ?? {}) as object),
        ...((extraEnergy.y ?? {}) as object),
      },
      tip: {
        ...((baseEnergy.tip ?? {}) as object),
        ...((explainEnergy.tip ?? {}) as object),
        ...((extraEnergy.tip ?? {}) as object),
      },
      itemHelp: {
        ...((explainEnergy.itemHelp ?? {}) as object),
        ...((extraEnergy.itemHelp ?? {}) as object),
      },
    },
    maps: {
      ...baseMaps,
      ...explainMaps,
      ...extraMaps,
      nodeHelp: {
        ...((explainMaps.nodeHelp ?? {}) as object),
        ...((extraMaps.nodeHelp ?? {}) as object),
      },
    },
    factory: {
      ...((base.factory ?? {}) as object),
      ...((explain.factory ?? {}) as object),
      ...((extra.factory ?? {}) as object),
    },
    glossary: mergeGlossary(
      (explain.glossary ?? {}) as Record<string, unknown>,
      (extra.glossary ?? {}) as Record<string, unknown>,
    ),
  }
}

function mergeGlossary(primary: Record<string, unknown>, overlay: Record<string, unknown>) {
  return {
    ...primary,
    ...overlay,
    kind: {
      ...((primary.kind ?? {}) as object),
      ...((overlay.kind ?? {}) as object),
    },
    entries: {
      ...((primary.entries ?? {}) as object),
      ...((overlay.entries ?? {}) as object),
    },
  }
}

const resources = {
  [AppLocale.En]: {
    translation: mergeExplain(en as Record<string, unknown>, {
      ...(explainEn as Record<string, unknown>),
      glossary: glossaryEn,
    }),
  },
  [AppLocale.Zh]: {
    translation: mergeExplain(zh as Record<string, unknown>, {
      ...(explainZh as Record<string, unknown>),
      glossary: glossaryZh,
    }),
  },
  [AppLocale.Fr]: {
    translation: mergeExplain(
      fr as Record<string, unknown>,
      { ...(explainEn as Record<string, unknown>), glossary: glossaryEn },
      { ...(explainFr as Record<string, unknown>), glossary: glossaryFr },
    ),
  },
}

void i18n.use(initReactI18next).init({
  resources,
  lng: readStoredLocale(),
  fallbackLng: DEFAULT_LOCALE,
  load: 'languageOnly',
  supportedLngs: LOCALES.map((loc) => loc.id),
  interpolation: { escapeValue: false },
})

i18n.on('languageChanged', (lng) => {
  window.localStorage.setItem(LOCALE_STORAGE_KEY, lng)
  document.documentElement.lang = lng
})

document.documentElement.lang = i18n.language

export { i18n }
