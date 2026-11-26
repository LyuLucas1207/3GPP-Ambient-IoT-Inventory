import { useTranslation } from 'react-i18next'
import { Dropdown } from '@/components/ui/dropdown'
import { i18n } from '@/i18n'
import { LOCALES, parseLocale } from '@/i18n/locales'

export function LanguageToggle() {
  const { t } = useTranslation()
  const current = parseLocale(i18n.language)
  return (
    <Dropdown
      value={current}
      align="end"
      aria-label={t('lang.label')}
      className="w-[8.5rem]"
      options={LOCALES.map((loc) => ({ value: loc.id, label: loc.nativeName }))}
      onChange={(v) => {
        void i18n.changeLanguage(parseLocale(v))
      }}
    />
  )
}
