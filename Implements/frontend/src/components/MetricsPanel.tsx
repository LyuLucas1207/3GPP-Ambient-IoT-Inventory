import { StrategyMapDialog } from '@/components/StrategyMapDialog'
import { TermHelp } from '@/components/TermHelp'
import { ExplainButton } from '@/components/ViewExplanationDialog'
import { MathInline, MathText } from '@/components/MathText'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { TermId, ViewId } from '@/explain/ids'
import { StrategyKey, type SimulationResult } from '@/types/simulation'
import { WaypointsIcon } from 'lucide-react'
import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

function fmt(v: number | null | undefined) {
  if (v == null) return '—'
  return `${v.toFixed(2)} s`
}

interface Props {
  result: SimulationResult | null
}

export function MetricsPanel({ result }: Props) {
  const { t } = useTranslation()
  const [openKey, setOpenKey] = useState<StrategyKey | null>(null)
  const rowRefs = useRef<Partial<Record<StrategyKey, HTMLTableRowElement | null>>>({})
  if (!result) {
    return (
      <div>
        <div className="mb-2 flex items-center justify-between gap-2">
          <p className="text-sm font-medium">{t('metrics.inventoryTimes')}</p>
          <ExplainButton view={ViewId.Metrics} />
        </div>
        <p className="text-sm text-muted-foreground">
          <MathText text={t('metrics.empty')} />
        </p>
      </div>
    )
  }
  const keys = Object.values(StrategyKey).filter((k) => result.metrics[k] != null)
  const val = result.fig5b_validation
  return (
    <>
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-sm font-medium">{t('metrics.inventoryTimes')}</p>
        <ExplainButton view={ViewId.Metrics} />
      </div>
      {val ? (
        <p className={`mb-2 text-xs font-medium ${val.pass ? 'text-emerald-700 dark:text-emerald-400' : 'text-red-700 dark:text-red-400'}`}>
          {t('metrics.validation', { status: val.status })}
          {val.reduction_4_vs_em != null
            ? ` · ${t('metrics.reduction', { value: (100 * val.reduction_4_vs_em).toFixed(0) })}`
            : ''}
        </p>
      ) : null}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t('metrics.strategy')}</TableHead>
            <TableHead>
              <span className="inline-flex items-center gap-1">
                <MathInline tex="T_{50}" />
                <TermHelp term={TermId.T50} />
              </span>
            </TableHead>
            <TableHead>
              <span className="inline-flex items-center gap-1">
                <MathInline tex="T_{90}" />
                <TermHelp term={TermId.T90} />
              </span>
            </TableHead>
            <TableHead>
              <span className="inline-flex items-center gap-1">
                <MathInline tex="T_{99}" />
                <TermHelp term={TermId.T99} />
              </span>
            </TableHead>
            <TableHead>{t('metrics.final')}</TableHead>
            <TableHead>{t('metrics.collisions')}</TableHead>
            <TableHead className="sr-only">{t('maps.view')}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {keys.map((k) => {
            const m = result.metrics[k]
            return (
              <TableRow
                key={k}
                ref={(el) => {
                  rowRefs.current[k] = el
                }}
                tabIndex={0}
                className="cursor-pointer outline-none hover:bg-muted/60 focus-visible:ring-3 focus-visible:ring-ring/50"
                aria-label={`${t(`strategy.${k}`)}. ${t('maps.view')}`}
                onClick={() => setOpenKey(k)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    setOpenKey(k)
                  }
                }}
              >
                <TableCell>{t(`strategy.${k}`)}</TableCell>
                <TableCell>{fmt(m.t50_s)}</TableCell>
                <TableCell>{fmt(m.t90_s)}</TableCell>
                <TableCell>{fmt(m.t99_s)}</TableCell>
                <TableCell>{m.final_ratio_pct.toFixed(1)}%</TableCell>
                <TableCell>{m.n_collisions}</TableCell>
                <TableCell className="text-muted-foreground">
                  <span className="inline-flex items-center gap-1 text-xs">
                    <WaypointsIcon className="size-3.5" aria-hidden />
                    {t('maps.view')}
                  </span>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
      <StrategyMapDialog
        strategy={openKey}
        result={result}
        onOpenChange={(open) => {
          if (!open) {
            const k = openKey
            setOpenKey(null)
            queueMicrotask(() => k && rowRefs.current[k]?.focus())
          }
        }}
      />
    </>
  )
}

export function MetricsCard({ result }: Props) {
  return <MetricsPanel result={result} />
}
