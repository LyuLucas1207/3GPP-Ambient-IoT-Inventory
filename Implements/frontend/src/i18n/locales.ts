export enum AppLocale {
  En = 'en',
  Zh = 'zh',
  Fr = 'fr',
}

export interface LocaleDef {
  id: AppLocale
  nativeName: string
}

/** Add a language: enum value + JSON under locales/ + one row here. */
export const LOCALES: LocaleDef[] = [
  { id: AppLocale.En, nativeName: 'English' },
  { id: AppLocale.Zh, nativeName: '中文' },
  { id: AppLocale.Fr, nativeName: 'Français' },
]

export const DEFAULT_LOCALE = AppLocale.En
export const LOCALE_STORAGE_KEY = 'ambient-iot-locale'

export function parseLocale(value: string): AppLocale {
  for (const loc of LOCALES) {
    if (loc.id === value) return loc.id
  }
  return DEFAULT_LOCALE
}

export function readStoredLocale(): AppLocale {
  if (typeof window === 'undefined') return DEFAULT_LOCALE
  const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY)
  if (stored == null) return DEFAULT_LOCALE
  return parseLocale(stored)
}
