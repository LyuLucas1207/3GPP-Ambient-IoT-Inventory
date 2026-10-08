import { PaperRef } from '@/components/aperiodic/PaperRef'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { AperiodicSimulationResult, Stat } from '@/types/aperiodicSimulation'
import { useTranslation } from 'react-i18next'

const STAGES = ['paging', 'msg1', 'EI', 'msg2', 'msg3'] as const

function fmt(v: number | null | undefined, digits = 1) {
  return v == null || Number.isNaN(v) ? '—' : v.toFixed(digits)
}

function Cell({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-md border border-border/60 px-2 py-1.5">
      <div className="text-[10px] tracking-wide text-muted-foreground uppercase">{label}</div>
      <div className="font-mono text-sm">{value}</div>
      {sub && <div className="font-mono text-[10px] text-muted-foreground">{sub}</div>}
    </div>
  )
}

export function AperiodicMetrics({ result }: { result: AperiodicSimulationResult }) {
  const { t } = useTranslation()
  const m = result.metrics
  const agg = result.aggregate as Record<string, Stat | null> | undefined
  const stat = (k: string) => {
    const s = agg?.[k]
    return s && typeof s === 'object' && 'mean' in s ? `±${fmt(s.ci95)} (n=${s.n})` : undefined
  }
  return (
    <Card plain size="sm">
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          {t('ap.metrics.title')} <PaperRef id="metrics" />
        </CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 xl:grid-cols-5">
          {(['T50', 'T90', 'T95', 'T99'] as const).map((k) => (
            <Cell key={k} label={`${k} (s)`} value={fmt(agg?.[k]?.mean ?? m[k])} sub={stat(k)} />
          ))}
          <Cell label={t('ap.metrics.totalTime')} value={fmt(agg?.T_total_s?.mean ?? m.T_total_s)} sub={stat('T_total_s')} />
          <Cell label={t('ap.metrics.final')} value={`${fmt(m.final_ratio * 100)} %`} />
          <Cell label={t('ap.metrics.meanIdTime')} value={fmt(m.mean_identification_time_s ?? m.mean_identification_time_partial_s)} />
          <Cell label={t('ap.metrics.rounds')} value={String(m.rounds)} />
          <Cell label={t('ap.metrics.neff')} value={`${m.n_eff} / ${m.n_tot}`} />
          <Cell label={t('ap.metrics.re')} value={`${fmt(m.resource_efficiency * 100, 2)} %`} />
          <Cell label={t('ap.metrics.msg2Wasted')} value={fmt(m.msg2_wasted, 0)} sub={`${t('ap.metrics.alloc')} ${fmt(m.msg2_allocated, 0)}`} />
          <Cell label={t('ap.metrics.aoObs')} value={`${m.ao_success_obs}/${m.ao_collision_obs}/${m.ao_idle_obs}`} sub="S/C/I" />
          <Cell label={t('ap.metrics.reward')} value={fmt(m.mean_reward, 3)} />
          <Cell label={t('ap.metrics.interround')} value={String(m.interround_depletions)} />
          <Cell label={t('ap.metrics.lostSuccess')} value={String(m.msg1_success_lost_to_depletion)} />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-muted-foreground">
                <th className="text-left font-normal">{t('ap.metrics.depletionStage')}</th>
                {STAGES.map((s) => (
                  <th key={s} className="text-right font-normal">
                    {t(`ap.stages.${s}`)}
                  </th>
                ))}
                <th className="text-right font-normal">{t('ap.metrics.total')}</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              <tr>
                <td>{t('ap.metrics.enforced')}</td>
                {STAGES.map((s) => (
                  <td key={s} className="text-right">
                    {m.depletion_by_stage[s] ?? 0}
                  </td>
                ))}
                <td className="text-right">{m.depletion_total}</td>
              </tr>
              <tr className="text-muted-foreground">
                <td>{t('ap.metrics.wouldDeplete')}</td>
                {STAGES.map((s) => (
                  <td key={s} className="text-right">
                    {m.would_deplete_by_stage[s] ?? 0}
                  </td>
                ))}
                <td className="text-right">{Object.values(m.would_deplete_by_stage).reduce((a, b) => a + b, 0)}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-muted-foreground">
                <th className="text-left font-normal">{t('ap.metrics.type')}</th>
                <th className="text-right font-normal">n</th>
                <th className="text-right font-normal">{t('ap.metrics.identified')}</th>
                <th className="text-right font-normal">T50</th>
                <th className="text-right font-normal">T99</th>
                <th className="text-right font-normal">{t('ap.metrics.meanIdTime')}</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {Object.entries(m.per_type).map(([k, v]) => (
                <tr key={k}>
                  <td>{t(`ap.terms.type${k}`)}</td>
                  <td className="text-right">{v.n}</td>
                  <td className="text-right">{v.identified}</td>
                  <td className="text-right">{fmt(v.T50)}</td>
                  <td className="text-right">{fmt(v.T99)}</td>
                  <td className="text-right">{fmt(v.mean_completion_s)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {m.group_populations && (
          <p className="text-xs text-muted-foreground">
            {t('ap.metrics.groups')}:{' '}
            <span className="font-mono">
              {Object.entries(m.group_populations)
                .map(([g, n]) => `G${g}=${n}`)
                .join(' · ')}
            </span>
          </p>
        )}
      </CardContent>
    </Card>
  )
}
