import { PaperCaption, type PaperRefId } from '@/components/aperiodic/PaperRef'
import { axis, baseLayout, MATLAB, PLOT_CONFIG } from '@/components/aperiodic/plotLayout'
import { Segmented } from '@/components/aperiodic/Segmented'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/lib/Plot'
import type { JobStatus, ReproResult, ReproTarget } from '@/types/aperiodicSimulation'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

interface Preset {
  id: Exclude<PaperRefId, 'tf' | 'inventory' | 'controller' | 'trace' | 'factory' | 'metrics'>
  target: ReproTarget
  panel?: string
}

const PRESETS: Preset[] = [
  { id: 'fig4', target: 'figure4' },
  { id: 'fig5a', target: 'figure5', panel: 'a_L16' },
  { id: 'fig5b', target: 'figure5', panel: 'b_L1' },
  { id: 'fig6a', target: 'figure6', panel: 'a_L16' },
  { id: 'fig6b', target: 'figure6', panel: 'b_L1' },
  { id: 'fig7', target: 'figure7' },
  { id: 'fig8', target: 'figure8' },
  { id: 'tab4', target: 'figure5' },
  { id: 'tab5', target: 'tables' },
  { id: 'tab6', target: 'tables' },
]

const CURVE_COLORS: Record<string, string> = {
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

function ProtocolFigure({ result, panel }: { result: ReproResult; panel: string }) {
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
                {k} {t('ap.repro.simVsPaper')}
              </th>
            ))}
            <th className="text-right font-normal">MAE (pp)</th>
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

function Figure4View({ result }: { result: ReproResult }) {
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

function Figure8View({ result }: { result: ReproResult }) {
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

function CheckpointNotes({ result }: { result: ReproResult }) {
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

function GenericObject({ value }: { value: unknown }) {
  return (
    <pre className="max-h-60 overflow-auto rounded-md bg-muted/50 p-2 text-[10px] leading-snug">{JSON.stringify(value, (_, v) => (typeof v === 'number' ? Number(v.toPrecision(5)) : v), 1)}</pre>
  )
}

function RowsTable({ rows }: { rows: Array<Record<string, unknown>> }) {
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

export function ReproductionPanel({ job, reproduce }: { job: JobStatus | null; reproduce: (t: ReproTarget, e: number, c: boolean, p?: string[]) => void }) {
  const { t } = useTranslation()
  const [preset, setPreset] = useState<Preset['id']>('fig5a')
  const [episodes, setEpisodes] = useState(100)
  const [useCached, setUseCached] = useState(true)
  const sel = PRESETS.find((p) => p.id === preset)!
  const running = job?.status === 'queued' || job?.status === 'running'
  const result = job?.status === 'done' ? job.result : undefined
  const source = result?.source

  const body = () => {
    if (!result) return null
    if (sel.id === 'fig4' && result.figure === 'figure4') return <Figure4View result={result} />
    if (sel.panel && result.panels) return <ProtocolFigure result={result} panel={sel.panel} />
    if (sel.id === 'tab4' && Array.isArray(result.table_iv)) return <RowsTable rows={result.table_iv as Array<Record<string, unknown>>} />
    if (sel.id === 'fig8' && result.series) return <Figure8View result={result} />
    if (sel.id === 'fig7' && result.panels)
      return (
        <div className="grid gap-4">
          {Object.keys(result.panels as object).map((k) => (
            <div key={k}>
              <p className="text-xs font-medium">{t(`ap.terms.${k === 'single_source' ? 'singleSource' : 'multiSource'}`)}</p>
              <ProtocolFigure result={result} panel={k} />
            </div>
          ))}
        </div>
      )
    const key = sel.id === 'tab5' ? 'table_v' : sel.id === 'tab6' ? 'table_vi' : null
    if (key && Array.isArray(result[key])) return <RowsTable rows={result[key] as Array<Record<string, unknown>>} />
    return <GenericObject value={result} />
  }

  return (
    <Card plain size="sm">
      <CardHeader>
        <CardTitle>{t('ap.repro.title')}</CardTitle>
        <CardDescription>{t('ap.repro.subtitle')}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        <Segmented value={preset} onChange={setPreset} options={PRESETS.map((p) => ({ value: p.id, label: t(`ap.paperRef.${p.id}.label`) }))} />
        <PaperCaption id={sel.id} />
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <label className="flex items-center gap-2">
            {t('ap.repro.useCached')}
            <Switch checked={useCached} onCheckedChange={setUseCached} />
          </label>
          <label className="flex items-center gap-2">
            {t('ap.controls.episodes')}
            <Input className="w-20" type="number" min={1} max={100} value={episodes} onChange={(e) => setEpisodes(Number(e.target.value))} />
          </label>
          <Button size="sm" disabled={running} onClick={() => reproduce(sel.target, episodes, useCached, sel.panel && !useCached ? [sel.panel] : undefined)}>
            {running ? t('ap.common.running') : t('ap.repro.run')}
          </Button>
          {job && (
            <Badge variant={job.status === 'error' ? 'destructive' : job.status === 'done' ? 'default' : 'secondary'}>
              {job.target} · {t(`ap.repro.status.${job.status}`)}
            </Badge>
          )}
          {source && (
            <span className="text-[11px] text-muted-foreground">
              {source.kind === 'computed' ? t('ap.repro.sourceComputed', { n: source.episodes }) : t('ap.repro.sourceCached', { path: source.path })}
            </span>
          )}
        </div>
        {!useCached && <p className="text-[11px] text-muted-foreground">{t('ap.repro.slowNote')}</p>}
        {job?.progress && job.progress.length > 0 && running && (
          <pre className="max-h-24 overflow-auto rounded-md bg-muted/50 p-2 text-[10px]">{job.progress.slice(-8).join('\n')}</pre>
        )}
        {job?.error && <p className="text-xs text-destructive">{job.error}</p>}
        {result && result.figure && result.figure !== sel.target && (
          <p className="text-xs text-muted-foreground">{t('ap.repro.otherTarget')}</p>
        )}
        {result && result.figure === sel.target && <CheckpointNotes result={result} />}
        {result && result.figure === sel.target && body()}
      </CardContent>
    </Card>
  )
}
