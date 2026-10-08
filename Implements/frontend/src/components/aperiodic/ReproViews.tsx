import { ParamHint } from '@/components/ParamHint'
import { axis, baseLayout, MATLAB, PLOT_CONFIG } from '@/components/aperiodic/plotLayout'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/lib/Plot'
import type { JobStatus, ReproResult, ReproTarget } from '@/types/aperiodicSimulation'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

// Shared views of the paper reproduction payloads (100-episode batch jobs).

export const CURVE_COLORS: Record<string, string> = {
  aperiodic: MATLAB.yellow,
  periodic_Ng1: MATLAB.green,
  periodic_Ng1_wo_depletion: MATLAB.purple,
  periodic_Ng4_wo_depletion: MATLAB.maroon,
  periodic_Ng2: MATLAB.cyan,
  periodic_Ng4: MATLAB.red,
  recurrent_ppo: MATLAB.blue,
  pfsa_pze: MATLAB.yellow,
  dfsa_schoute: MATLAB.green,
  cmebe: MATLAB.purple,
  pfsa_L1: MATLAB.red,
  pfsa_L8: MATLAB.yellow,
  pfsa_L32: MATLAB.purple,
}

type Curve = {
  label: string
  curve_mean: number[]
  curve_p05?: number[]
  curve_p95?: number[]
  curve_step_s?: number
  aggregate?: Record<string, { mean: number; ci95: number; n: number } | unknown>
  paper_reference?: { x: number[]; y: number[] } | null
  reference?: { mae?: number; rmse?: number; paper_T?: Record<string, number | null> } | null
}
type Panel = { L?: number; curves: Record<string, Curve>; validation?: Record<string, unknown> }

export function ProtocolFigure({ result, panel }: { result: ReproResult; panel: string }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const p = (result.panels as Record<string, Panel> | undefined)?.[panel]
  const data = useMemo(() => {
    if (!p) return []
    const out: Array<Record<string, unknown>> = []
    for (const [name, c] of Object.entries(p.curves)) {
      const step = c.curve_step_s ?? 2
      const x = c.curve_mean.map((_, i) => i * step)
      const color = CURVE_COLORS[name] ?? plot.line
      if (c.curve_p05 && c.curve_p95) {
        out.push({ x, y: c.curve_p95, type: 'scatter', mode: 'lines', line: { width: 0 }, showlegend: false, hoverinfo: 'skip', legendgroup: name })
        out.push({ x, y: c.curve_p05, type: 'scatter', mode: 'lines', fill: 'tonexty', fillcolor: `${color}26`, line: { width: 0 }, showlegend: false, hoverinfo: 'skip', legendgroup: name })
      }
      out.push({ x, y: c.curve_mean, type: 'scatter', mode: 'lines', line: { color, width: 2.2 }, name: c.label, legendgroup: name })
      if (c.paper_reference)
        out.push({
          x: c.paper_reference.x,
          y: c.paper_reference.y,
          type: 'scatter',
          mode: 'lines',
          line: { color, width: 1.4, dash: 'dash' },
          name: `${c.label} (${t('ap.repro.paper')})`,
          legendgroup: name,
          opacity: 0.8,
        })
    }
    return out
  }, [p, plot.line, t])
  if (!p) return <p className="text-xs text-muted-foreground">{t('ap.repro.panelMissing', { panel })}</p>
  return (
    <div className="grid gap-2">
      <Plot
        data={data}
        layout={baseLayout(plot, {
          xaxis: axis(plot, t('ap.plots.time')),
          yaxis: axis(plot, t('ap.plots.ratio'), { range: [0, 102] }),
          uirevision: `${result.figure}-${panel}`,
        })}
        useResizeHandler
        style={{ width: '100%', height: 340 }}
        config={PLOT_CONFIG}
      />
      <table className="w-full text-xs">
        <thead>
          <tr className="text-muted-foreground">
            <th className="text-left font-normal">{t('ap.repro.curve')}</th>
            {['T50', 'T90', 'T99'].map((k) => (
              <th key={k} className="text-right font-normal">
                <span className="inline-flex items-center gap-1">
                  {k} {t('ap.repro.simVsPaper')}
                  {k === 'T50' && <ParamHint text={t('ap.help.tq')} title="T_q" />}
                </span>
              </th>
            ))}
            <th className="text-right font-normal">
              <span className="inline-flex items-center gap-1">
                MAE (pp) <ParamHint text={t('ap.help.mae')} title="MAE" />
              </span>
            </th>
          </tr>
        </thead>
        <tbody className="font-mono">
          {Object.entries(p.curves).map(([name, c]) => (
            <tr key={name}>
              <td className="font-sans">{c.label}</td>
              {['T50', 'T90', 'T99'].map((k) => {
                const s = (c.aggregate?.[k] as { mean: number } | null | undefined)?.mean
                const ref = c.reference?.paper_T?.[k]
                return (
                  <td key={k} className="text-right">
                    {s != null ? s.toFixed(0) : '—'} / {ref != null ? ref.toFixed(0) : '—'}
                  </td>
                )
              })}
              <td className="text-right">{c.reference?.mae != null ? c.reference.mae.toFixed(2) : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {p.validation && <GenericObject value={p.validation} />}
    </div>
  )
}

export function Figure4View({ result }: { result: ReproResult }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const scen = (result.scenarios ?? {}) as Record<
    string,
    {
      n_eff: number
      paper_n_eff: number
      type_shares: Record<string, number>
      cdf: { pin_dbm: number[]; cdf: number[] }
      paper_reference?: { x: number[]; y: number[] } | null
      paper_cdf_quantile_gap_db?: { mean_abs: number; max_abs: number }
    }
  >
  const colors: Record<string, string> = { single_source: MATLAB.blue, multi_source: MATLAB.red }
  const data = Object.entries(scen).flatMap(([k, e]) => [
    { x: e.cdf.pin_dbm, y: e.cdf.cdf, type: 'scatter', mode: 'lines', name: t(`ap.terms.${k === 'single_source' ? 'singleSource' : 'multiSource'}`), line: { color: colors[k], width: 2.2 } },
    ...(e.paper_reference
      ? [{ x: e.paper_reference.x, y: e.paper_reference.y, type: 'scatter', mode: 'lines', name: `${t('ap.repro.paper')} (${k})`, line: { color: colors[k], dash: 'dash', width: 1.4 } }]
      : []),
  ])
  return (
    <div className="grid gap-2">
      <Plot
        data={data}
        layout={baseLayout(plot, { xaxis: axis(plot, t('ap.repro.pin')), yaxis: axis(plot, 'CDF', { range: [0, 1.02] }) })}
        useResizeHandler
        style={{ width: '100%', height: 300 }}
        config={PLOT_CONFIG}
      />
      <div className="grid gap-1 text-xs">
        {Object.entries(scen).map(([k, e]) => (
          <p key={k}>
            <span className="font-medium">{k}</span>: N<sub>eff</sub> {e.n_eff} ({t('ap.repro.paper')} {e.paper_n_eff}) · shares{' '}
            {Object.entries(e.type_shares)
              .map(([ty, v]) => `${ty} ${(v * 100).toFixed(1)}%`)
              .join(' / ')}
            {e.paper_cdf_quantile_gap_db && ` · CDF gap ${e.paper_cdf_quantile_gap_db.mean_abs.toFixed(2)} dB`}
          </p>
        ))}
      </div>
    </div>
  )
}

type Fig8Series = {
  label: string
  points: Array<{ n_tot: number; re_pct: { mean: number; ci95: number } | null }>
  paper_reference: { n_tot: number[]; re_pct: number[] } | null
  reference?: { mae?: number }
}

export function Figure8View({ result }: { result: ReproResult }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const series = (result.series ?? {}) as Record<string, Fig8Series>
  const data = Object.entries(series).flatMap(([name, s]) => {
    const color = CURVE_COLORS[name] ?? plot.line
    return [
      {
        x: s.points.map((p) => p.n_tot / 1000),
        y: s.points.map((p) => p.re_pct?.mean ?? null),
        error_y: { type: 'data', array: s.points.map((p) => p.re_pct?.ci95 ?? 0), visible: true, thickness: 1 },
        type: 'scatter',
        mode: 'lines+markers',
        marker: { size: 5 },
        line: { color, width: 2 },
        name: s.label,
        legendgroup: name,
      },
      ...(s.paper_reference
        ? [
            {
              x: s.paper_reference.n_tot.map((n) => n / 1000),
              y: s.paper_reference.re_pct,
              type: 'scatter',
              mode: 'lines',
              line: { color, dash: 'dash', width: 1.4 },
              name: `${s.label} (${t('ap.repro.paper')})`,
              legendgroup: name,
            },
          ]
        : []),
    ]
  })
  return (
    <div className="grid gap-2">
      <Plot
        data={data}
        layout={baseLayout(plot, { hovermode: 'closest', xaxis: axis(plot, 'N_tot (×10³)'), yaxis: axis(plot, t('ap.plots.re'), { rangemode: 'tozero' }) })}
        useResizeHandler
        style={{ width: '100%', height: 320 }}
        config={PLOT_CONFIG}
      />
      <p className="text-xs text-muted-foreground">
        MAE (pp):{' '}
        {Object.values(series)
          .map((s) => `${s.label} ${s.reference?.mae != null ? s.reference.mae.toFixed(2) : '—'}`)
          .join(' · ')}
      </p>
    </div>
  )
}

export function CheckpointNotes({ result }: { result: ReproResult }) {
  const { t } = useTranslation()
  const cks = (result.checkpoints ?? {}) as Record<string, { available: boolean; training_steps?: number; fully_trained?: boolean }>
  const unavailable = (result.unavailable ?? {}) as Record<string, string>
  const notes = [
    ...Object.entries(cks)
      .filter(([, c]) => c.available && !c.fully_trained)
      .map(([a, c]) => t('ap.repro.underTrained', { alpha: a, steps: c.training_steps?.toLocaleString() })),
    ...Object.entries(cks)
      .filter(([, c]) => !c.available)
      .map(([a]) => t('ap.repro.ckMissing', { alpha: a })),
    ...Object.keys(unavailable).map((k) => t('ap.repro.methodMissing', { method: k })),
  ]
  if (!notes.length) return null
  return (
    <ul className="grid gap-0.5 rounded-md border border-amber-500/40 bg-amber-500/10 p-2 text-[11px] text-amber-800 dark:text-amber-200">
      {notes.map((n) => (
        <li key={n}>{n}</li>
      ))}
    </ul>
  )
}

export function GenericObject({ value }: { value: unknown }) {
  return (
    <pre className="max-h-60 overflow-auto rounded-md bg-muted/50 p-2 text-[10px] leading-snug">{JSON.stringify(value, (_, v) => (typeof v === 'number' ? Number(v.toPrecision(5)) : v), 1)}</pre>
  )
}

export function RowsTable({ rows }: { rows: Array<Record<string, unknown>> }) {
  const flat = rows.map((r) => {
    const o: Record<string, string> = {}
    const walk = (prefix: string, v: unknown) => {
      if (v && typeof v === 'object' && !Array.isArray(v)) for (const [k, x] of Object.entries(v)) walk(prefix ? `${prefix}.${k}` : k, x)
      else o[prefix] = typeof v === 'number' ? (Number.isInteger(v) ? String(v) : v.toFixed(2)) : String(v ?? '—')
    }
    walk('', r)
    return o
  })
  const cols = Array.from(new Set(flat.flatMap((r) => Object.keys(r))))
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[11px]">
        <thead>
          <tr className="text-muted-foreground">
            {cols.map((c) => (
              <th key={c} className="px-1 text-right font-normal whitespace-nowrap">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="font-mono">
          {flat.map((r, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <td key={c} className="px-1 text-right whitespace-nowrap">
                  {r[c] ?? ''}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export type Reproduce = (target: ReproTarget, episodes: number, useCached: boolean, panels?: string[]) => void

/** Episodes / cached switch / run button and job status for one reproduction target. */
export function ReproRunControls({
  job,
  target,
  panels,
  reproduce,
  baseSeed,
  defaultEpisodes = 100,
}: {
  job: JobStatus | null
  target: ReproTarget
  panels?: string[]
  reproduce: Reproduce
  baseSeed: number
  defaultEpisodes?: number
}) {
  const { t } = useTranslation()
  const [episodes, setEpisodes] = useState(defaultEpisodes)
  const [useCached, setUseCached] = useState(true)
  const running = job?.status === 'queued' || job?.status === 'running'
  const mine = job?.target === target
  const result = mine && job?.status === 'done' ? job.result : undefined
  const source = result?.source
  const cachedSeed = (result as { base_seed?: number } | undefined)?.base_seed
  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <label className="flex items-center gap-2">
          {t('ap.repro.useCached')}
          <ParamHint text={t('ap.help.useCached')} title={t('ap.repro.useCached')} />
          <Switch checked={useCached} onCheckedChange={setUseCached} />
        </label>
        <label className="flex items-center gap-2">
          {t('ap.controls.episodes')}
          <ParamHint text={t('ap.help.episodes', { seed: baseSeed })} title={t('ap.controls.episodes')} />
          <Input className="w-20" type="number" min={1} max={100} value={episodes} onChange={(e) => setEpisodes(Number(e.target.value))} />
        </label>
        <Button size="sm" disabled={running} onClick={() => reproduce(target, episodes, useCached, panels && !useCached ? panels : undefined)}>
          {running && mine ? t('ap.common.running') : t('ap.repro.run')}
        </Button>
        {job && mine && (
          <Badge variant={job.status === 'error' ? 'destructive' : job.status === 'done' ? 'default' : 'secondary'}>
            {t(`ap.repro.status.${job.status}`)}
          </Badge>
        )}
        {source && (
          <span className="text-[11px] text-muted-foreground">
            {source.kind === 'computed' ? t('ap.repro.sourceComputed', { n: source.episodes }) : t('ap.repro.sourceCached', { path: source.path })}
            {cachedSeed != null && ` · ${t('ap.repro.baseSeed', { seed: cachedSeed })}`}
          </span>
        )}
      </div>
      <p className="text-[11px] leading-snug text-muted-foreground">
        {useCached ? t('ap.repro.cachedNote') : t('ap.repro.seedNote', { seed: baseSeed, last: baseSeed + episodes - 1 })}
        {!useCached && ` ${t('ap.repro.slowNote')}`}
      </p>
      {job?.progress && job.progress.length > 0 && running && mine && (
        <pre className="max-h-24 overflow-auto rounded-md bg-muted/50 p-2 text-[10px]">{job.progress.slice(-8).join('\n')}</pre>
      )}
      {job?.error && mine && <p className="text-xs text-destructive">{job.error}</p>}
      {running && !mine && <p className="text-xs text-muted-foreground">{t('ap.repro.otherRunning', { target: job?.target })}</p>}
    </div>
  )
}

/** The finished reproduction result for ``target`` (if the last job was for it). */
export function jobResult(job: JobStatus | null, target: ReproTarget): ReproResult | undefined {
  return job?.status === 'done' && job.target === target && job.result?.figure === target ? job.result : undefined
}
