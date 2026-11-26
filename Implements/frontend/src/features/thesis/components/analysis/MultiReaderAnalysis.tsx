import { useQueries } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchDeviceMetrics, fetchInterference } from '@/apis/thesisRuns'
import { axis, baseLayout, PLOT_CONFIG } from '@/features/aperiodic/components/plotLayout'
import { defaultTermination, terminationLabel, TerminationEditor } from '@/features/thesis/components/MultiReaderOptions'
import { ParamHint } from '@/components/ParamHint'
import { Button } from '@/components/ui/button'
import { Dropdown } from '@/components/ui/dropdown'
import { useTerminationReplay } from '@/features/thesis/hooks/useMultiReader'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/utils/Plot'
import { thesisKeys } from '@/features/thesis/lib/thesisQueryKeys'
import type { DeviceMetrics, InterferenceReport, RunAnalysis, TerminationOutcome, TerminationSpec } from '@/features/thesis/types'

export const RUN_COLORS = ['#0072bd', '#d95319', '#edb120', '#7e2f8e', '#77ac30', '#4dbeee', '#a2142f', '#525252']
const SUBTYPES = ['1', '2a', '2b'] as const
const LOSS_KINDS = ['r2d_lost', 'm1_lost', 'm2_lost', 'm3_lost'] as const
const LOSS_COLOR: Record<string, string> = { r2d_lost: '#4dbeee', m1_lost: '#0072bd', m2_lost: '#77ac30', m3_lost: '#edb120' }
const LIVE = new Set(['pending', 'running'])

export function runShortLabel(a: RunAnalysis) {
  return a.summary?.name?.trim() || `#${a.run_id}`
}

function t99Of(a: RunAnalysis): number | null {
  const pt = a.reachable_completion_times ?? a.population_completion_times ?? a.completion_times
  return pt['99'] ?? null
}

function Panel({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border bg-card p-3">
      <h3 className="mb-1 text-xs font-medium text-muted-foreground">{title}</h3>
      {hint ? <p className="mb-2 text-[11px] text-muted-foreground">{hint}</p> : null}
      {children}
    </section>
  )
}

function RunSelect({ analyses, value, onChange, label }: { analyses: RunAnalysis[]; value: number | null; onChange: (id: number) => void; label: string }) {
  return (
    <label className="flex items-center gap-2 text-xs text-muted-foreground">
      <span>{label}</span>
      <Dropdown
        value={value == null ? '' : String(value)}
        placeholder="—"
        size="sm"
        className="min-w-40"
        options={analyses.map((a) => ({
          value: String(a.run_id),
          trigger: runShortLabel(a),
          label: `${runShortLabel(a)} · ${a.summary.resource_mode ?? 'independent'}`,
        }))}
        onChange={(v) => onChange(Number(v))}
      />
    </label>
  )
}

// ------------------------------------------------------------------ configuration table

/** Controller, resource policy and termination rule of every selected run. */
export function ConfigTable({ analyses }: { analyses: RunAnalysis[] }) {
  const { t } = useTranslation()
  return (
    <div className="overflow-auto">
      <table className="w-full text-xs">
        <thead className="bg-muted/40 text-left text-muted-foreground">
          <tr>
            {['run', 'controller', 'resource', 'f', 'termination', 'terminatedEarly', 'readersStopped'].map((c) => (
              <th key={c} className="px-2 py-1 font-normal">
                {t(`thesis.analysis.multi.cols.${c}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {analyses.map((a, i) => {
            const s = a.summary
            const cfg = (a.config ?? {}) as Record<string, unknown>
            return (
              <tr key={a.run_id} className="border-t tabular-nums">
                <td className="px-2 py-1">
                  <span className="mr-1 inline-block size-2 rounded-full" style={{ background: RUN_COLORS[i % RUN_COLORS.length] }} />
                  {runShortLabel(a)}
                </td>
                <td className="px-2 py-1">
                  {s.controller_kind === 'policy' ? `policy · ${s.policy_id}` : t(`thesis.newRun.controller.kinds.${s.controller_kind ?? 'auto'}`)}
                </td>
                <td className="px-2 py-1">{t(`thesis.newRun.resource.modes.${s.resource_mode ?? 'independent'}`, { defaultValue: s.resource_mode })}</td>
                <td className="px-2 py-1">{typeof cfg.f_freq === 'number' ? cfg.f_freq : 8}</td>
                <td className="px-2 py-1 font-mono text-[11px]">{s.termination_label ?? 'oracle'}</td>
                <td className="px-2 py-1">{s.terminated_early_count ?? 0}</td>
                <td className="px-2 py-1">{s.readers_stopped ?? 0}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ------------------------------------------------------------------ gain retention

/**
 * G = (T_serial - T_policy) / (T_serial - T_ideal) on T99 (the resource sweep's
 * metric): 1 keeps all of the ideal multi-reader gain, 0 is no better than
 * serving the readers one after another. Only defined when all three runs
 * reach 99 % of their reachable devices.
 */
export function RetentionPanel({ analyses }: { analyses: RunAnalysis[] }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const byT99 = [...analyses].sort((a, b) => (t99Of(a) ?? Infinity) - (t99Of(b) ?? Infinity))
  const defIdeal = analyses.find((a) => (a.summary.resource_mode ?? 'independent') === 'independent') ?? byT99[0]
  const defSerial = [...analyses].reverse().find((a) => a.summary.resource_mode === 'tdma') ?? byT99[byT99.length - 1]
  const [idealId, setIdealId] = useState<number | null>(null)
  const [serialId, setSerialId] = useState<number | null>(null)
  const ideal = analyses.find((a) => a.run_id === (idealId ?? defIdeal?.run_id)) ?? null
  const serial = analyses.find((a) => a.run_id === (serialId ?? defSerial?.run_id)) ?? null
  const tI = ideal ? t99Of(ideal) : null
  const tS = serial ? t99Of(serial) : null
  const rows = analyses.map((a) => {
    const tp = t99Of(a)
    const g = tI != null && tS != null && tp != null && tS - tI > 1e-9 ? (tS - tp) / (tS - tI) : null
    return { a, tp, g }
  })
  if (analyses.length < 2) return <p className="text-xs text-muted-foreground">{t('thesis.analysis.multi.retention.needTwo')}</p>
  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <RunSelect analyses={analyses} value={ideal?.run_id ?? null} onChange={setIdealId} label={t('thesis.analysis.multi.retention.ideal')} />
        <RunSelect analyses={analyses} value={serial?.run_id ?? null} onChange={setSerialId} label={t('thesis.analysis.multi.retention.serial')} />
      </div>
      {tI == null || tS == null ? (
        <p className="text-xs text-amber-600">{t('thesis.analysis.multi.retention.unreached')}</p>
      ) : tS <= 1.05 * tI ? (
        <p className="text-xs text-amber-600">{t('thesis.analysis.multi.retention.degenerate')}</p>
      ) : null}
      <Plot
        data={[
          {
            type: 'bar',
            x: rows.map((r) => runShortLabel(r.a)),
            y: rows.map((r) => r.g),
            marker: { color: rows.map((_, i) => RUN_COLORS[i % RUN_COLORS.length]) },
            text: rows.map((r) => (r.g == null ? '—' : r.g.toFixed(2))),
            textposition: 'outside',
            hovertemplate: '%{x}: G=%{y:.3f}<extra></extra>',
          },
        ]}
        layout={{
          ...baseLayout(plot, { height: 260, showlegend: false }),
          xaxis: axis(plot, t('thesis.analysis.cols.run')),
          yaxis: axis(plot, 'G', { rangemode: 'tozero' }),
          shapes: [1, 0].map((y) => ({ type: 'line' as const, xref: 'paper' as const, x0: 0, x1: 1, y0: y, y1: y, line: { color: plot.grid, width: 1, dash: 'dash' as const } })),
        }}
        config={PLOT_CONFIG}
        style={{ width: '100%' }}
        useResizeHandler
      />
      <table className="w-full text-xs tabular-nums">
        <thead className="text-left text-muted-foreground">
          <tr>
            <th className="py-0.5 font-normal">{t('thesis.analysis.cols.run')}</th>
            <th className="py-0.5 font-normal">{t('thesis.analysis.multi.cols.resource')}</th>
            <th className="py-0.5 font-normal">T99</th>
            <th className="py-0.5 font-normal">G</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ a, tp, g }) => (
            <tr key={a.run_id} className="border-t">
              <td className="py-0.5">
                {runShortLabel(a)}
                {a.run_id === ideal?.run_id ? ` (${t('thesis.analysis.multi.retention.idealTag')})` : ''}
                {a.run_id === serial?.run_id ? ` (${t('thesis.analysis.multi.retention.serialTag')})` : ''}
              </td>
              <td className="py-0.5">{a.summary.resource_mode ?? 'independent'}</td>
              <td className="py-0.5">{tp == null ? '—' : `${tp.toFixed(2)} s`}</td>
              <td className="py-0.5">{g == null ? '—' : g.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ------------------------------------------------------------------ termination Pareto

const PRESET_RULES: TerminationSpec[] = [
  { kind: 'oracle' },
  ...[3, 5, 10, 20, 40].map((n): TerminationSpec => ({ kind: 'quiet_rounds', quiet_rounds: n })),
  ...[10, 20, 50].map((w): TerminationSpec => ({ kind: 'id_rate', window_mode: 'rounds', window: w, r_rel: 0.01, r_min: null, min_frames: 5, ewma_alpha: 0.1 })),
  ...[1, 5].map((w): TerminationSpec => ({ kind: 'id_rate', window_mode: 'seconds', window: w, r_rel: 0.01, r_min: null, min_frames: 5, ewma_alpha: 0.1 })),
  ...([['edge', 0], ['edge', 0.1], ['actual', 0], ['actual', 0.1]] as const).map(([src, m]): TerminationSpec => ({ kind: 'energy_bound', energy_source: src, margin: m })),
]

/** Zoom to the cluster. A few rules that keep paging for hundreds of seconds would otherwise flatten every other point onto the axis. */
function clusterWindow(values: number[]): { lo: number; hi: number; edge: number | null } {
  const finite = values.filter((v) => Number.isFinite(v)).sort((a, b) => a - b)
  if (!finite.length) return { lo: -1, hi: 1, edge: null }
  const lo0 = Math.min(0, finite[0])
  const hi0 = finite[finite.length - 1]
  const pivot = finite[Math.floor((finite.length - 1) * 0.75)]
  const squash = hi0 > Math.max(pivot * 3, pivot + 40) && pivot > 0
  const hi = squash ? pivot : hi0
  const span = Math.max(hi - lo0, 1)
  return { lo: lo0 - span * 0.08, hi: hi + span * 0.22, edge: squash ? hi + span * 0.12 : null }
}

function paretoFront(outcomes: TerminationOutcome[]): TerminationOutcome[] {
  const pts = outcomes.filter((o) => o.rule !== 'oracle' && Number.isFinite(o.extra_time_s))
  return pts
    .filter((p) => !pts.some((q) => q !== p && q.extra_time_s <= p.extra_time_s && q.missed <= p.missed && (q.extra_time_s < p.extra_time_s || q.missed < p.missed)))
    .sort((a, b) => a.extra_time_s - b.extra_time_s)
}

export function TerminationPanel({ analyses }: { analyses: RunAnalysis[] }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const finished = analyses.filter((a) => !LIVE.has(a.status))
  const [runId, setRunId] = useState<number | null>(null)
  const run = finished.find((a) => a.run_id === runId) ?? finished[0] ?? null
  const [custom, setCustom] = useState<TerminationSpec[]>([])
  const [draft, setDraft] = useState<TerminationSpec>(defaultTermination('quiet_rounds'))
  const rules = useMemo(() => [...PRESET_RULES, ...custom], [custom])
  const replay = useTerminationReplay(run?.run_id ?? null, rules, run != null)
  const data = replay.data
  const front = useMemo(() => (data ? paretoFront(data.outcomes) : []), [data])
  const oracle = data?.outcomes.find((o) => o.rule === 'oracle') ?? null

  if (!run) return <p className="text-xs text-muted-foreground">{t('thesis.analysis.multi.termination.needFinished')}</p>
  const kindOf = (o: TerminationOutcome) => o.spec.kind
  const KIND_COLOR: Record<string, string> = { quiet_rounds: '#0072bd', id_rate: '#d95319', energy_bound: '#77ac30', combined: '#7e2f8e' }
  const pts = (data?.outcomes ?? []).filter((o) => o.rule !== 'oracle')
  const xWindow = clusterWindow(pts.map((o) => o.extra_time_s))
  const missedPct = pts.map((o) => 100 * o.missed_fraction)
  const yMax = Math.max(0, ...missedPct, 0)
  const yHi = yMax < 1 ? 8 : yMax * 1.25
  const placeX = (v: number) => (xWindow.edge != null && v > xWindow.edge ? xWindow.edge : v)
  const multi = Object.keys(data?.outcomes[0]?.reader_stop ?? {}).length > 1
  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <RunSelect analyses={finished} value={run.run_id} onChange={setRunId} label={t('thesis.analysis.multi.termination.run')} />
        {data ? (
          <span className="text-xs text-muted-foreground tabular-nums">
            {t('thesis.analysis.multi.termination.summary', {
              reachable: data.reachable,
              t99: data.t99 != null ? data.t99.toFixed(2) : '—',
              tLast: data.t_last_id != null ? data.t_last_id.toFixed(2) : '—',
            })}
          </span>
        ) : null}
      </div>
      {!data?.oracle && data ? <p className="text-xs text-amber-600">{t('thesis.analysis.multi.termination.notOracle')}</p> : null}
      {multi ? <p className="text-[11px] text-muted-foreground">{t('thesis.analysis.multi.termination.multiApprox')}</p> : null}
      {replay.isLoading ? <p className="text-xs text-muted-foreground">{t('thesis.analysis.loading')}</p> : null}
      {replay.error ? <p className="text-xs text-destructive">{String((replay.error as Error).message)}</p> : null}
      {data ? (
        <Plot
          data={[
            ...Object.keys(KIND_COLOR).map((k) => {
              const sel = pts.filter((o) => kindOf(o) === k)
              return {
                type: 'scatter' as const,
                mode: 'markers+text' as const,
                name: t(`thesis.newRun.termination.kinds.${k}`),
                x: sel.map((o) => (Number.isFinite(o.extra_time_s) ? placeX(o.extra_time_s) : null)),
                y: sel.map((o) => 100 * o.missed_fraction),
                text: sel.map((o) => (xWindow.edge != null && o.extra_time_s > xWindow.edge ? `${o.extra_time_s.toFixed(0)} s` : '')),
                textposition: 'top center' as const,
                textfont: { size: 10, color: KIND_COLOR[k] },
                customdata: sel.map((o) => [o.rule, o.extra_time_s, 100 * o.missed_fraction]),
                hovertemplate: '%{customdata[0]}<br>+%{customdata[1]:.2f} s · %{customdata[2]:.2f}% missed<extra></extra>',
                cliponaxis: false,
                marker: {
                  size: 13,
                  color: KIND_COLOR[k],
                  symbol: sel.map((o) => (xWindow.edge != null && o.extra_time_s > xWindow.edge ? 'triangle-right' : 'circle')),
                  line: { width: 1, color: plot.paper },
                },
              }
            }),
            {
              type: 'scatter' as const,
              mode: 'lines' as const,
              name: t('thesis.analysis.multi.termination.front'),
              x: front.map((o) => placeX(o.extra_time_s)),
              y: front.map((o) => 100 * o.missed_fraction),
              line: { color: plot.line, width: 1.5, dash: 'dot' as const },
              hoverinfo: 'skip' as const,
            },
          ]}
          layout={{
            ...baseLayout(plot, { height: 320, hovermode: 'closest' }),
            xaxis: axis(plot, t('thesis.analysis.multi.termination.extra'), { range: [xWindow.lo, xWindow.hi], zeroline: false }),
            yaxis: axis(plot, t('thesis.analysis.multi.termination.missed'), { range: [-Math.max(1.5, yHi * 0.18), yHi], zeroline: true, zerolinecolor: plot.grid, zerolinewidth: 1 }),
            shapes: oracle && Number.isFinite(oracle.extra_time_s)
              ? [{ type: 'line' as const, yref: 'paper' as const, x0: oracle.extra_time_s, x1: oracle.extra_time_s, y0: 0, y1: 1, line: { color: plot.grid, width: 1, dash: 'dash' as const } }]
              : [],
          }}
          config={PLOT_CONFIG}
          style={{ width: '100%' }}
          useResizeHandler
        />
      ) : null}
      {data && xWindow.edge != null ? (
        <p className="text-[11px] text-muted-foreground">{t('thesis.analysis.multi.termination.zoomed', { max: Math.max(...pts.map((o) => o.extra_time_s).filter((v) => Number.isFinite(v))).toFixed(0) })}</p>
      ) : null}
      <div className="grid grid-cols-2 gap-2 rounded-md border border-dashed p-2 text-xs md:max-w-xl">
        <TerminationEditor value={draft} onChange={setDraft} allowCombined />
        <div className="col-span-2 flex items-center gap-2">
          <Button type="button" size="sm" variant="outline" onClick={() => setCustom((c) => [...c, draft])}>
            {t('thesis.analysis.multi.termination.addRule')}
          </Button>
          <span className="font-mono text-[10px] text-muted-foreground">{terminationLabel(draft)}</span>
          {custom.length ? (
            <Button type="button" size="sm" variant="ghost" onClick={() => setCustom([])}>
              {t('thesis.analysis.clearSelection')}
            </Button>
          ) : null}
        </div>
      </div>
      {data ? (
        <div className="overflow-auto">
          <table className="w-full text-xs tabular-nums">
            <thead className="text-left text-muted-foreground">
              <tr>
                {['rule', 'tStop', 'extra', 'extraT99', 'missed', 'missedPct'].map((c) => (
                  <th key={c} className="py-0.5 pr-2 font-normal">
                    {t(`thesis.analysis.multi.termination.cols.${c}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.outcomes.map((o, i) => (
                <tr key={`${o.rule}-${i}`} className={`border-t ${front.includes(o) ? 'font-medium' : ''}`}>
                  <td className="py-0.5 pr-2 font-mono text-[11px]">{o.rule}</td>
                  <td className="py-0.5 pr-2">{Number.isFinite(o.t_stop) ? `${o.t_stop.toFixed(2)} s` : '∞'}</td>
                  <td className="py-0.5 pr-2">{Number.isFinite(o.extra_time_s) ? `${o.extra_time_s.toFixed(2)} s` : '∞'}</td>
                  <td className="py-0.5 pr-2">{o.extra_vs_t99_s != null && Number.isFinite(o.extra_vs_t99_s) ? `${o.extra_vs_t99_s.toFixed(2)} s` : '—'}</td>
                  <td className="py-0.5 pr-2">{o.missed}</td>
                  <td className="py-0.5 pr-2">{(100 * o.missed_fraction).toFixed(2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  )
}

// ------------------------------------------------------------------ interference

export function InterferencePanel({ analyses }: { analyses: RunAnalysis[] }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const results = useQueries({
    queries: analyses.map((a) => ({
      queryKey: thesisKeys.interference(a.run_id, a.status),
      queryFn: () => fetchInterference(a.run_id),
      staleTime: LIVE.has(a.status) ? 0 : Infinity,
    })),
  })
  const reports = results.map((r) => r.data ?? null)
  const totals = reports.map((rep) => {
    const out: Record<string, number> = { r2d_lost: 0, m1_lost: 0, m2_lost: 0, m3_lost: 0, frames_hit: 0, deferred_s: 0 }
    for (const r of Object.values(rep?.readers ?? {})) {
      for (const k of [...LOSS_KINDS, 'frames_hit', 'deferred_s'] as const) out[k] += r.interference[k] ?? 0
    }
    return out
  })
  const x = analyses.map(runShortLabel)
  const [detailId, setDetailId] = useState<number | null>(null)
  const detailIdx = Math.max(0, analyses.findIndex((a) => a.run_id === detailId))
  const detail: InterferenceReport | null = reports[detailIdx] ?? null
  return (
    <div className="grid gap-3">
      <div className="grid gap-3 xl:grid-cols-2">
        <Plot
          data={LOSS_KINDS.map((k) => ({
            type: 'bar' as const,
            x,
            y: totals.map((tot) => tot[k]),
            name: t(`thesis.coord.loss.${k}`),
            marker: { color: LOSS_COLOR[k] },
          }))}
          layout={{
            ...baseLayout(plot, { height: 260, barmode: 'stack' }),
            xaxis: axis(plot, t('thesis.analysis.cols.run')),
            yaxis: axis(plot, t('thesis.coord.lostDevices'), { rangemode: 'tozero' }),
          }}
          config={PLOT_CONFIG}
          style={{ width: '100%' }}
          useResizeHandler
        />
        <Plot
          data={[
            {
              type: 'bar' as const,
              x,
              y: totals.map((tot) => tot.deferred_s),
              name: t('thesis.coord.col.deferred'),
              marker: { color: '#7e2f8e' },
            },
          ]}
          layout={{
            ...baseLayout(plot, { height: 260, showlegend: false }),
            xaxis: axis(plot, t('thesis.analysis.cols.run')),
            yaxis: axis(plot, t('thesis.analysis.multi.interference.deferredAxis'), { rangemode: 'tozero' }),
          }}
          config={PLOT_CONFIG}
          style={{ width: '100%' }}
          useResizeHandler
        />
      </div>
      <RunSelect analyses={analyses} value={analyses[detailIdx]?.run_id ?? null} onChange={setDetailId} label={t('thesis.analysis.multi.interference.detail')} />
      {detail ? (
        <>
          <Plot
            data={LOSS_KINDS.map((k, ki) => ({
              type: 'scattergl' as const,
              mode: 'markers' as const,
              name: t(`thesis.coord.loss.${k}`),
              x: detail.frames.filter((f) => f[2 + ki] > 0).map((f) => f[0]),
              y: detail.frames.filter((f) => f[2 + ki] > 0).map((f) => `#${f[1]}`),
              marker: { color: LOSS_COLOR[k], size: detail.frames.filter((f) => f[2 + ki] > 0).map((f) => 4 + 2 * Math.sqrt(f[2 + ki])) },
              hovertemplate: `%{y} @ %{x:.3f}s<extra>${k}</extra>`,
            }))}
            layout={{
              ...baseLayout(plot, { height: Math.max(200, 24 * Object.keys(detail.readers).length + 60) }),
              xaxis: axis(plot, t('thesis.analysis.axis.time')),
              yaxis: { ...axis(plot, ''), type: 'category' as const },
            }}
            config={PLOT_CONFIG}
            style={{ width: '100%' }}
            useResizeHandler
          />
          <p className="text-[11px] text-muted-foreground">{t('thesis.analysis.multi.interference.timelineHint')}</p>
        </>
      ) : null}
    </div>
  )
}

// ------------------------------------------------------------------ per-device metrics

const METRIC_KEYS = ['readers_in_range', 'cbra_failures', 'reader_changes'] as const

export function DeviceMetricsPanel({ analyses }: { analyses: RunAnalysis[] }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const finished = analyses.filter((a) => !LIVE.has(a.status))
  const results = useQueries({
    queries: finished.map((a) => ({
      queryKey: thesisKeys.deviceMetrics(a.run_id, a.status),
      queryFn: () => fetchDeviceMetrics(a.run_id),
      staleTime: Infinity,
    })),
  })
  const data: (DeviceMetrics | null)[] = results.map((r) => r.data ?? null)
  if (finished.length === 0) return <p className="text-xs text-muted-foreground">{t('thesis.analysis.multi.termination.needFinished')}</p>
  return (
    <div className="grid gap-3">
      <div className="grid gap-3 xl:grid-cols-3">
        {METRIC_KEYS.map((key) => (
          <div key={key}>
            <h4 className="mb-1 flex items-center gap-1 text-[11px] font-medium">
              {t(`thesis.deviceMetrics.${camel(key)}`)}
              <ParamHint text={t(`thesis.deviceMetrics.chart.${camel(key)}`)} title={t(`thesis.deviceMetrics.${camel(key)}`)} />
            </h4>
            <Plot
              data={finished.map((a, i) => {
                const hist = data[i]?.aggregate.all?.[key]?.hist ?? {}
                const xs = Object.keys(hist).map(Number).sort((p, q) => p - q)
                const n = data[i]?.aggregate.all?.devices ?? 1
                return {
                  type: 'bar' as const,
                  name: runShortLabel(a),
                  x: xs,
                  y: xs.map((v) => (100 * (hist[String(v)] ?? 0)) / Math.max(1, n)),
                  marker: { color: RUN_COLORS[analyses.indexOf(a) % RUN_COLORS.length] },
                }
              })}
              layout={{
                ...baseLayout(plot, { height: 220, barmode: 'group', margin: { t: 8, r: 12, b: 36, l: 44 } }),
                xaxis: axis(plot, t('thesis.analysis.multi.devices.perDevice'), { dtick: 1 }),
                yaxis: axis(plot, t('thesis.analysis.multi.devices.pctDevices'), { rangemode: 'tozero' }),
              }}
              config={PLOT_CONFIG}
              style={{ width: '100%' }}
              useResizeHandler
            />
          </div>
        ))}
      </div>
      <div className="mb-1 flex items-center gap-1 text-[11px] font-medium">
        {t('thesis.deviceMetrics.tableTitle')}
        <ParamHint text={t('thesis.deviceMetrics.tableHint')} title={t('thesis.deviceMetrics.tableTitle')} />
      </div>
      <div className="overflow-auto">
        <table className="w-full text-xs tabular-nums">
          <thead className="text-left text-muted-foreground">
            <tr>
              <th className="py-0.5 pr-2 font-normal">{t('thesis.analysis.cols.run')}</th>
              <th className="py-0.5 pr-2 font-normal">{t('thesis.charts.type')}</th>
              <th className="py-0.5 pr-2 font-normal">{t('thesis.deviceMetrics.readersInRange')} {t('thesis.deviceMetrics.mean')}</th>
              <th className="py-0.5 pr-2 font-normal">{t('thesis.deviceMetrics.cbraFailures')} {t('thesis.deviceMetrics.meanP95')}</th>
              <th className="py-0.5 pr-2 font-normal">{t('thesis.deviceMetrics.changedShare')}</th>
              <th className="py-0.5 pr-2 font-normal">{t('thesis.deviceMetrics.failToPage')} {t('thesis.deviceMetrics.meanP95')}</th>
            </tr>
          </thead>
          <tbody>
            {finished.flatMap((a, i) => {
              const agg = data[i]?.aggregate
              if (!agg?.all) return []
              const groups: [string, typeof agg.all][] = [[t('thesis.charts.all'), agg.all], ...SUBTYPES.filter((s) => agg.by_subtype?.[s]).map((s): [string, typeof agg.all] => [t(`thesis.kind.device${s}`), agg.by_subtype![s]])]
              return groups.map(([label, g], j) => (
                <tr key={`${a.run_id}-${j}`} className={`border-t ${j === 0 ? 'font-medium' : 'text-muted-foreground'}`}>
                  <td className="py-0.5 pr-2">{j === 0 ? runShortLabel(a) : ''}</td>
                  <td className="py-0.5 pr-2">
                    {label} ({g.devices})
                  </td>
                  <td className="py-0.5 pr-2">{fmt(g.readers_in_range?.mean)}</td>
                  <td className="py-0.5 pr-2">
                    {fmt(g.cbra_failures?.mean)} / {fmt(g.cbra_failures?.p95)}
                  </td>
                  <td className="py-0.5 pr-2">{g.reader_changes?.fraction_changed != null ? `${(100 * g.reader_changes.fraction_changed).toFixed(1)}%` : '—'}</td>
                  <td className="py-0.5 pr-2">
                    {fmtMs(g.fail_to_page_mean_s?.mean)} / {fmtMs(g.fail_to_page_mean_s?.p95)}
                  </td>
                </tr>
              ))
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function camel(s: string): string {
  return s.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase())
}

function fmt(v: number | null | undefined): string {
  return v == null ? '—' : v.toFixed(2)
}

function fmtMs(v: number | null | undefined): string {
  return v == null ? '—' : `${(1e3 * v).toFixed(0)} ms`
}

export { Panel as MultiPanel }
