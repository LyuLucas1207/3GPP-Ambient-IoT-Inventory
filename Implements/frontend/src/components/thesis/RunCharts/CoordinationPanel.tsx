import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { axis, baseLayout, PLOT_CONFIG } from '@/components/aperiodic/plotLayout'
import { readerColor } from '@/components/thesis/ReaderInspector'
import { useInterference } from '@/hooks/useMultiReader'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/lib/Plot'
import type { FrameInterference, RunRound, RunStatus } from '@/types/thesis'

const LOSS_KINDS = ['r2d_lost', 'm1_lost', 'm2_lost', 'm3_lost'] as const
const LOSS_COLOR: Record<string, string> = { r2d_lost: '#4dbeee', m1_lost: '#0072bd', m2_lost: '#77ac30', m3_lost: '#edb120' }

function frameLoss(r: RunRound): FrameInterference | null {
  return (r.metadata?.interference as FrameInterference | undefined) ?? null
}

/**
 * Multi-reader coordination of the current scope: devices lost to other
 * readers' interference per frame over time (stacked by protocol step), and the
 * grant / termination / interference counters of every reader.
 */
export function CoordinationPanel({
  runId,
  status,
  rounds,
  all,
  tNow,
}: {
  runId: number
  status: RunStatus | null
  rounds: RunRound[]
  all: boolean
  tNow: number
}) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const report = useInterference(runId, status).data ?? null

  const series = useMemo(() => {
    const BINS = 120
    let tMax = 0
    for (const r of rounds) tMax = Math.max(tMax, r.t_start_s)
    const width = Math.max(tMax / BINS, 1e-6)
    const out: Record<string, number[]> = Object.fromEntries(LOSS_KINDS.map((k) => [k, new Array(BINS + 1).fill(0)]))
    for (const r of rounds) {
      const ix = frameLoss(r)
      if (!ix) continue
      const i = Math.min(BINS, Math.floor(r.t_start_s / width))
      for (const k of LOSS_KINDS) out[k][i] += ix[k] ?? 0
    }
    return { x: Array.from({ length: BINS + 1 }, (_, i) => (i + 0.5) * width), out }
  }, [rounds])

  const totals = useMemo(() => {
    const tot = { r2d_lost: 0, m1_lost: 0, m2_lost: 0, m3_lost: 0 }
    let hit = 0
    for (const r of rounds) {
      const ix = frameLoss(r)
      if (!ix) continue
      let any = 0
      for (const k of LOSS_KINDS) {
        tot[k] += ix[k] ?? 0
        any += ix[k] ?? 0
      }
      if (any) hit++
    }
    return { ...tot, hit }
  }, [rounds])

  const readers = report ? Object.entries(report.readers).sort((a, b) => Number(a[0]) - Number(b[0])) : []
  const independent = report?.mode === 'independent'

  return (
    <div className="grid h-full content-start gap-3 overflow-auto text-xs">
      <div className="grid grid-cols-[repeat(auto-fill,minmax(110px,1fr))] gap-1.5">
        <Kpi label={t('thesis.coord.mode')} value={report ? t(`thesis.newRun.resource.modes.${report.mode}`, { defaultValue: report.mode }) : '—'} />
        <Kpi label={t('thesis.coord.colors')} value={report ? String(report.n_colors) : '—'} />
        <Kpi label={t('thesis.coord.framesHit')} value={`${totals.hit} / ${rounds.length}`} />
        <Kpi label="R2D" value={String(totals.r2d_lost)} />
        <Kpi label="Msg1" value={String(totals.m1_lost)} />
        <Kpi label="Msg2" value={String(totals.m2_lost)} />
        <Kpi label="Msg3" value={String(totals.m3_lost)} />
        <Kpi label={t('thesis.coord.stopped')} value={report ? `${readers.filter(([, r]) => r.stopped).length} / ${readers.length}` : '—'} />
      </div>
      {independent ? <p className="text-muted-foreground">{t('thesis.coord.independentHint')}</p> : null}
      <div className="h-[200px]">
        <Plot
          data={LOSS_KINDS.map((k) => ({
            type: 'bar' as const,
            x: series.x,
            y: series.out[k],
            name: t(`thesis.coord.loss.${k}`),
            marker: { color: LOSS_COLOR[k] },
          }))}
          layout={{
            ...baseLayout(plot, { height: 200, barmode: 'stack', margin: { t: 8, r: 12, b: 32, l: 44 } }),
            xaxis: axis(plot, t('thesis.charts.time'), { range: [0, Math.max(tNow, 1e-3)] }),
            yaxis: axis(plot, t('thesis.coord.lostDevices'), { rangemode: 'tozero' }),
          }}
          config={PLOT_CONFIG}
          style={{ width: '100%', height: '100%' }}
          useResizeHandler
        />
      </div>
      {all && readers.length ? (
        <table className="w-full tabular-nums">
          <thead className="text-left text-muted-foreground">
            <tr>
              {['reader', 'color', 'subbands', 'slot', 'neighbors', 'rounds', 'lost', 'deferred', 'stop', 'tWc'].map((h) => (
                <th key={h} className="py-0.5 pr-2 font-normal">
                  {t(`thesis.coord.col.${h}`)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {readers.map(([rid, r]) => {
              const ix = r.interference
              return (
                <tr key={rid} className="border-t">
                  <td className="py-0.5 pr-2">#{rid}</td>
                  <td className="py-0.5 pr-2">
                    <span className="mr-1 inline-block size-2 rounded-full" style={{ background: readerColor(r.color) }} />
                    {r.color + 1}
                  </td>
                  <td className="py-0.5 pr-2">{r.f_r === 0 ? '—' : r.subbands.join(',')}</td>
                  <td className="py-0.5 pr-2">{r.time_slot ? `${r.time_slot[0] + 1}/${r.time_slot[1]}` : '—'}</td>
                  <td className="py-0.5 pr-2">{r.neighbors.length}</td>
                  <td className="py-0.5 pr-2">{r.rounds}</td>
                  <td className="py-0.5 pr-2">{ix.r2d_lost + ix.m1_lost + ix.m2_lost + ix.m3_lost}</td>
                  <td className="py-0.5 pr-2">{ix.deferred_s.toFixed(2)} s</td>
                  <td className="py-0.5 pr-2">
                    {r.stopped
                      ? `${t(`thesis.readerInspector.stopReason.${r.stop_reason ?? 'stopped'}`, { defaultValue: r.stop_reason ?? '' })} @ ${(r.stop_t ?? 0).toFixed(2)} s`
                      : r.exhausted
                        ? t('thesis.readerInspector.exhausted')
                        : '—'}
                  </td>
                  <td className="py-0.5 pr-2">{r.t_wc_s != null ? `${r.t_wc_s.toFixed(1)} s` : '—'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      ) : null}
    </div>
  )
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-muted/50 px-2 py-1">
      <div className="text-[10px] text-muted-foreground">{label}</div>
      <div className="font-medium tabular-nums">{value}</div>
    </div>
  )
}
