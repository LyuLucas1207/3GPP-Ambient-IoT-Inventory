import { Info, XIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import {
  Popover,
  PopoverClose,
  PopoverDescription,
  PopoverPopup,
  PopoverPortal,
  PopoverPositioner,
  PopoverTitle,
  PopoverTrigger,
} from '@/components/ui/popover'

/** Term ids explained under each chart tab (keys of thesis.charts.terms). */
const TERMS_PER_TAB: Record<string, string[]> = {
  ident: ['identified', 'dropped', 'unreachable', 't50'],
  controller: ['K', 'pstar', 'nHat', 'backlogTrue', 'joiners'],
  outcome: ['success', 'collision', 'empty', 'efficiency'],
  timing: ['paging', 'm1', 'ebi', 'm2', 'm3'],
  energy: ['energyNow', 'energySpent', 'depletions'],
  round: ['candidates', 'joiners', 'budget', 'budgetDropped', 'backlogTrue', 'slotCodes'],
  metrics: ['efficiency', 'depletions', 'unreachable', 'no_progress', 't50'],
  pin: ['pin', 'cdf'],
}

/** One-line description of the active chart tab + an (i) popover with the full explanation and legend. */
export function ChartHelp({ tab }: { tab: string }) {
  const { t } = useTranslation()
  return (
    <div className="flex min-w-0 items-center gap-1.5 text-[11px] text-muted-foreground">
      <span className="truncate">{t(`thesis.charts.help.${tab}.lead`)}</span>
      <Popover>
        <PopoverTrigger
          className="inline-flex size-5 shrink-0 items-center justify-center rounded-full text-muted-foreground outline-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
          aria-label={t('thesis.charts.help.open')}
          title={t('thesis.charts.help.open')}
        >
          <Info className="size-3.5" />
        </PopoverTrigger>
        <PopoverPortal>
          <PopoverPositioner side="top" align="start">
            <PopoverPopup className="w-[min(420px,calc(100vw-32px))]">
              <div className="flex items-start justify-between gap-2">
                <PopoverTitle>{t(`thesis.charts.tab.${tab}`)}</PopoverTitle>
                <PopoverClose
                  className="rounded-md p-1 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
                  aria-label={t('thesis.inspector.close')}
                >
                  <XIcon className="size-3.5" />
                </PopoverClose>
              </div>
              <PopoverDescription className="mt-2 text-xs">{t(`thesis.charts.help.${tab}.body`)}</PopoverDescription>
              <div className="mt-3 text-xs font-medium">{t('thesis.charts.help.legend')}</div>
              <ul className="mt-1 grid gap-1 text-xs text-muted-foreground">
                {(TERMS_PER_TAB[tab] ?? []).map((id) => (
                  <li key={id}>{t(`thesis.charts.terms.${id}`)}</li>
                ))}
              </ul>
            </PopoverPopup>
          </PopoverPositioner>
        </PopoverPortal>
      </Popover>
    </div>
  )
}
