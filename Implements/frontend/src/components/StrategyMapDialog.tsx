import {
  Dialog,
  DialogBackdrop,
  DialogClose,
  DialogDescription,
  DialogPopup,
  DialogPortal,
  DialogTitle,
} from '@/components/ui/dialog'
import { ExplainButton } from '@/components/ViewExplanationDialog'
import { StrategyFlow } from '@/components/StrategyFlow'
import { dcmFourGroupsMap } from '@/strategyMaps/dcmFourGroups'
import { dcmOneGroupMap } from '@/strategyMaps/dcmOneGroup'
import { emMap } from '@/strategyMaps/em'
import type { StrategyMapDef } from '@/strategyMaps/types'
import { StrategyKey, type SimulationResult, type StrategyMetrics } from '@/types/simulation'
import { ViewId } from '@/explain/ids'
import { XIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

const MAPS: Record<StrategyKey, StrategyMapDef> = {
  [StrategyKey.EM]: emMap,
  [StrategyKey.DCM_1_GROUP]: dcmOneGroupMap,
  [StrategyKey.DCM_4_GROUP]: dcmFourGroupsMap,
}

const PAPER_T99: Record<StrategyKey, string> = {
  [StrategyKey.EM]: 'maps.expect.em',
  [StrategyKey.DCM_1_GROUP]: 'maps.expect.dcm1',
  [StrategyKey.DCM_4_GROUP]: 'maps.expect.dcm4',
}

function metricLine(m: StrategyMetrics | undefined, t: (k: string) => string) {
  if (!m) return t('metrics.empty')
  const fail = m.energy_fail
    ? Object.entries(m.energy_fail)
        .map(([k, v]) => `${k}:${v}`)
        .join(' · ')
    : '—'
  return [
    `T50 ${m.t50_s?.toFixed(2) ?? '—'} s`,
    `T90 ${m.t90_s?.toFixed(2) ?? '—'} s`,
    `T99 ${m.t99_s?.toFixed(2) ?? '—'} s`,
    `${t('metrics.final')} ${m.final_ratio_pct.toFixed(1)}%`,
    `${t('metrics.collisions')} ${m.n_collisions} (${(m.collision_rate * 100).toFixed(1)}%)`,
    `paging ${m.n_paging}`,
    `Msg1 ${m.n_msg1_attempts}`,
    `heard-no-attempt ${m.n_heard_no_attempt ?? '—'}`,
    `energy-fail ${fail}`,
  ].join('\n')
}

interface Props {
  strategy: StrategyKey | null
  result: SimulationResult | null
  onOpenChange: (open: boolean) => void
}

export function StrategyMapDialog({ strategy, result, onOpenChange }: Props) {
  const { t } = useTranslation()
  const open = strategy != null
  const def = strategy ? MAPS[strategy] : null
  const metrics = strategy && result ? result.metrics[strategy] : undefined

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogPortal>
        <DialogBackdrop />
        <DialogPopup className="h-[calc(100dvh-12px)] w-[calc(100vw-12px)] max-h-[calc(100dvh-12px)] max-w-[1920px]">
            <div className="flex shrink-0 items-start justify-between gap-3 border-b px-4 py-3">
            <div className="min-w-0">
              <DialogTitle>{strategy ? t(`strategy.${strategy}`) : ''}</DialogTitle>
              <DialogDescription>{def ? t(def.summaryKey) : ''}</DialogDescription>
            </div>
            <div className="flex items-center gap-2">
              <ExplainButton view={ViewId.StrategyMap} />
              <DialogClose
                className="rounded-md p-1 outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                aria-label={t('maps.close')}
              >
                <XIcon className="size-4" />
              </DialogClose>
            </div>
          </div>
          {def && strategy ? (
            <div className="grid min-h-0 flex-1 overflow-hidden lg:grid-cols-[minmax(0,1fr)_minmax(22rem,26rem)]">
              <div className="h-full min-h-0 border-b lg:border-r lg:border-b-0">
                <StrategyFlow key={strategy} def={def} />
              </div>
              <aside className="grid gap-4 overflow-auto p-5 text-sm">
                <section>
                  <h3 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                    {t('maps.how')}
                  </h3>
                  <ol className="mt-1.5 list-decimal space-y-1.5 pl-4 text-sm">
                    {t(def.stepsKey)
                      .split('\n')
                      .filter(Boolean)
                      .map((line) => (
                        <li key={line}>{line}</li>
                      ))}
                  </ol>
                </section>
                <section>
                  <h3 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                    {t('maps.paperExpect')}
                  </h3>
                  <p className="mt-1.5 text-sm leading-relaxed">{t(PAPER_T99[strategy])}</p>
                </section>
                <section>
                  <h3 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                    {t('maps.runMetrics')}
                  </h3>
                  <pre className="mt-1.5 overflow-auto rounded-md bg-muted/60 p-3 text-xs whitespace-pre-wrap">
                    {metricLine(metrics, t)}
                  </pre>
                </section>
                <section>
                  <h3 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                    {t('assumptions.repro')}
                  </h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                    {result
                      ? String(result.reproduction_assumptions.group_assignment ?? '')
                      : ''}
                  </p>
                </section>
                <p className="text-xs leading-relaxed text-muted-foreground">{t('maps.clickNode')}</p>
                <p className="text-xs leading-relaxed text-muted-foreground">{t('maps.legend')}</p>
                <p className="sr-only">{t(def.stepsKey)}</p>
              </aside>
            </div>
          ) : null}
        </DialogPopup>
      </DialogPortal>
    </Dialog>
  )
}
