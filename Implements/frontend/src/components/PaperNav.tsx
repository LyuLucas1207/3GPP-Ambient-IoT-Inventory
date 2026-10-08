import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'

export const PERIODIC_PAGING_PATH = '/periodic-paging'
export const APERIODIC_PAGING_PATH = '/aperiodic-paging'

const LINKS = [
  { to: PERIODIC_PAGING_PATH, key: 'nav.periodicPaper' },
  { to: APERIODIC_PAGING_PATH, key: 'nav.aperiodicPaper' },
] as const

export function PaperNav({ className }: { className?: string }) {
  const { t } = useTranslation()
  return (
    <nav
      aria-label={t('nav.label')}
      className={cn('inline-flex rounded-lg border border-border bg-muted/40 p-0.5', className)}
    >
      {LINKS.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          className={({ isActive }) =>
            cn(
              'rounded-md px-2.5 py-1 text-xs font-medium whitespace-nowrap transition-colors',
              isActive
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground',
            )
          }
        >
          {t(link.key)}
        </NavLink>
      ))}
    </nav>
  )
}
