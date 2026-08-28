import { useTranslation } from 'react-i18next'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { i18n } from '@/i18n'
import { LOCALES, parseLocale } from '@/i18n/locales'

export function LanguageToggle() {
  const { t } = useTranslation()
  const current = parseLocale(i18n.language)
  const items = Object.fromEntries(LOCALES.map((loc) => [loc.id, loc.nativeName]))

  return (
    <Select
      value={current}
      items={items}
      onValueChange={(v) => {
        if (v == null) return
        void i18n.changeLanguage(parseLocale(String(v)))
      }}
    >
      <SelectTrigger className="w-[8.5rem]" aria-label={t('lang.label')}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent align="end" alignItemWithTrigger={false}>
        {LOCALES.map((loc) => (
          <SelectItem key={loc.id} value={loc.id}>
            {loc.nativeName}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
