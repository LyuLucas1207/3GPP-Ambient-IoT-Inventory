import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { THESIS_ANALYSIS_PATH, THESIS_SIMULATION_PATH } from '@/components/PaperNav'
import { cn } from '@/lib/utils'

/** Second-level navigation inside the thesis simulation: the scene editor and the run analysis. */
export function ThesisSubNav({ className }: { className?: string }) {
  const { t } = useTranslation()
  const links = [
    { to: THESIS_SIMULATION_PATH, label: t('thesis.subnav.scene'), end: true },
    { to: THESIS_ANALYSIS_PATH, label: t('nav.thesisAnalysis'), end: false },
  ]
  return (
    <nav aria-label={t('thesis.subnav.label')} className={cn('inline-flex rounded-lg border border-border bg-muted/40 p-0.5', className)}>
      {links.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          end={link.end}
          className={({ isActive }) =>
            cn(
              'rounded-md px-2.5 py-1 text-xs font-medium whitespace-nowrap transition-colors',
              isActive ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground',
            )
          }
        >
          {link.label}
        </NavLink>
      ))}
    </nav>
  )
}
