import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { promoteTrainingRun, trainingPlotUrl } from '@/apis/thesisTraining'
import { axis, baseLayout, PLOT_CONFIG } from '@/features/aperiodic/components/plotLayout'
import { LanguageToggle } from '@/components/LanguageToggle'
import { HomeLink } from '@/layouts/SimulatorLayout'
import { ThemeToggle } from '@/components/ThemeToggle'
import { ThesisSubNav } from '@/features/thesis/components/ThesisSubNav'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { usePolicies, useTrainingExperiment, useTrainingExperiments } from '@/features/thesis/hooks/useMultiReader'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/utils/Plot'
import { thesisKeys } from '@/features/thesis/lib/thesisQueryKeys'
import type { EvalMatrixRow, TrainingCurvePoint, TrainingExperiment, TrainingRunDetail } from '@/features/thesis/types'

const SCALES = ['smoke', 'small', 'medium', 'full'] as const
const CURVES = [
  ['return', 'thesis.training.curve.return'],
  ['identified_fraction', 'thesis.training.curve.identified'],
  ['t99', 'thesis.training.curve.t99'],
  ['resource_efficiency', 'thesis.training.curve.efficiency'],
] as const

/**
 * Multi-reader RL training outputs (``Implements/backend/training/outputs``):
 * experiments from ``training/configs``, their runs, learning curves and
 * generalization matrices, plus the policy registry that inventory runs pick
 * from. Training itself runs offline from the CLI (``python -m training.train``).
 */
export default function ThesisTrainingPage() {
  const { t } = useTranslation()
  useEffect(() => {
    document.title = t('thesis.training.title')
  }, [t])
  const experiments = useTrainingExperiments()
  const [selected, setSelected] = useState<string | null>(null)
  const list = experiments.data ?? []
  const current = selected ?? list.find((e) => e.runs > 0)?.experiment ?? list[0]?.experiment ?? null
  const detail = useTrainingExperiment(current)
  const meta = list.find((e) => e.experiment === current) ?? null

  return (
    <div className="flex h-dvh w-screen flex-col overflow-hidden bg-background">
      <header className="flex w-full shrink-0 items-center gap-4 border-b bg-card px-4 py-2">
        <div className="min-w-0">
          <HomeLink className="mb-1" />
          <div className="flex items-center gap-3">
            <h1 className="truncate text-lg font-medium">{t('thesis.training.title')}</h1>
            <ThesisSubNav />
          </div>
          <p className="truncate text-xs text-muted-foreground">{t('thesis.training.subtitle')}</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <LanguageToggle />
          <ThemeToggle />
        </div>
      </header>
      <div className="flex min-h-0 flex-1">
        <aside className="flex w-72 shrink-0 flex-col overflow-hidden border-r bg-card">
          <h2 className="shrink-0 border-b px-3 py-2 text-sm font-medium">{t('thesis.training.experiments')}</h2>
          <ScrollArea className="min-h-0 flex-1">
            <div className="flex flex-col gap-1 p-2">
              {experiments.isLoading ? <p className="px-1 text-xs text-muted-foreground">{t('thesis.analysis.loading')}</p> : null}
              {experiments.error ? <p className="px-1 text-xs text-destructive">{String((experiments.error as Error).message)}</p> : null}
              {list.map((e) => (
                <ExperimentCard key={e.experiment} exp={e} active={e.experiment === current} onClick={() => setSelected(e.experiment)} />
              ))}
            </div>
          </ScrollArea>
        </aside>
        <main className="min-h-0 min-w-0 flex-1 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="flex flex-col gap-4 p-4">
              {meta ? <ExperimentHeader exp={meta} /> : null}
              {detail.data ? <RunsSection experiment={detail.data.experiment} runs={detail.data.runs} /> : null}
              <PolicyRegistry />
              <HowTo />
            </div>
          </ScrollArea>
        </main>
      </div>
    </div>
  )
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

function StatusDot({ status }: { status: string }) {
  const color = status === 'done' ? '#77ac30' : status === 'failed' ? '#ef4444' : status === 'running' ? '#edb120' : status === 'interrupted' ? '#d95319' : '#a1a1aa'
  return <span className="inline-block size-2 shrink-0 rounded-full" style={{ background: color }} title={status} />
}

function ExperimentCard({ exp, active, onClick }: { exp: TrainingExperiment; active: boolean; onClick: () => void }) {
  const { t } = useTranslation()
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex flex-col gap-1 rounded-lg border px-2 py-1.5 text-left text-xs transition ${active ? 'border-foreground bg-muted/60' : 'hover:bg-muted/40'}`}
    >
      <div className="flex items-center gap-2">
        {exp.latest ? <StatusDot status={exp.latest.status} /> : <span className="inline-block size-2 rounded-full border" />}
        <span className="truncate font-medium">{exp.experiment}</span>
      </div>
      <div className="flex justify-between text-muted-foreground">
        <span className="truncate">{exp.algo ? t(`thesis.training.algoConfig.${exp.algo}`, { defaultValue: exp.algo }) : '—'}</span>
        <span className="shrink-0 pl-2 tabular-nums">{t('thesis.training.runCount', { done: exp.done, total: exp.runs, failed: exp.failed })}</span>
      </div>
    </button>
  )
}

function ExperimentHeader({ exp }: { exp: TrainingExperiment }) {
  const { t } = useTranslation()
  const cfg = (exp.config ?? {}) as Record<string, unknown>
  const env = (cfg.env ?? {}) as Record<string, unknown>
  const list = (v: unknown) => (Array.isArray(v) ? v.join(', ') : v == null ? '—' : String(v))
  const rows: [string, string][] = [
    [t('thesis.training.algo'), exp.algo ? t(`thesis.training.algoConfig.${exp.algo}`, { defaultValue: exp.algo }) : '—'],
    ['α', list(cfg.alphas)],
    ['β', list(cfg.betas)],
    [t('thesis.training.seeds'), list(cfg.seeds)],
    [t('thesis.training.env.readers'), list(env.readers)],
    [t('thesis.training.env.subset'), list(env.subset)],
    [t('thesis.training.env.offsets'), list(env.offsets)],
    [t('thesis.training.env.resource'), list(env.resource_modes)],
    [t('thesis.training.env.mix'), list(env.subtype_mix)],
  ]
  return (
    <Panel title={exp.experiment} hint={exp.description ?? undefined}>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(160px,1fr))] gap-1.5 text-xs">
        {rows.map(([k, v]) => (
          <div key={k} className="rounded-md bg-muted/50 px-2 py-1">
            <div className="text-[10px] text-muted-foreground">{k}</div>
            <div className="truncate tabular-nums" title={v}>
              {v}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-2 grid gap-1">
        {SCALES.map((s) => (
          <code key={s} className="block truncate rounded bg-muted/60 px-2 py-0.5 font-mono text-[11px]">
            .venv/bin/python -m training.train --config {exp.experiment} --scale {s}
            {s === 'small' ? ' --promote' : ''}
          </code>
        ))}
      </div>
    </Panel>
  )
}

function RunsSection({ experiment, runs }: { experiment: string; runs: TrainingRunDetail[] }) {
  const { t } = useTranslation()
  const [runName, setRunName] = useState<string | null>(null)
  const sorted = useMemo(() => [...runs].reverse(), [runs])
  const run = sorted.find((r) => r.run === runName) ?? sorted[0] ?? null
  if (runs.length === 0) {
    return (
      <Panel title={t('thesis.training.runs')}>
        <p className="text-xs text-muted-foreground">{t('thesis.training.noRuns')}</p>
      </Panel>
    )
  }
  return (
    <>
      <Panel title={t('thesis.training.runs')}>
        <div className="overflow-auto">
          <table className="w-full text-xs whitespace-nowrap tabular-nums">
            <thead className="text-left text-muted-foreground">
              <tr>
                {['run', 'status', 'alpha', 'scale', 'steps', 'episodes', 'wall', 'reach99', 't99VsDfsa', 'promoted'].map((c) => (
                  <th key={c} className="py-0.5 pr-2 font-normal">
                    {t(`thesis.training.cols.${c}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map((r) => {
                const ev = r.eval_summary?.policy
                return (
                  <tr
                    key={r.run}
                    className={`cursor-pointer border-t ${r.run === run?.run ? 'bg-muted/60' : 'hover:bg-muted/30'}`}
                    onClick={() => setRunName(r.run)}
                  >
                    <td className="py-0.5 pr-2 font-mono text-[11px]">{r.run}</td>
                    <td className="py-0.5 pr-2">
                      <span className="inline-flex items-center gap-1">
                        <StatusDot status={r.status} />
                        {t(`thesis.training.status.${r.status}`, { defaultValue: r.status })}
                      </span>
                    </td>
                    <td className="py-0.5 pr-2">
                      {r.alpha ?? '—'} / {r.beta ?? '—'} / s{r.seed ?? '—'}
                    </td>
                    <td className="py-0.5 pr-2">{r.scale ?? '—'}</td>
                    <td className="py-0.5 pr-2">{r.training_steps?.toLocaleString() ?? '—'}</td>
                    <td className="py-0.5 pr-2">{r.training_episodes ?? r.curve.length}</td>
                    <td className="py-0.5 pr-2">{r.wall_time_s != null ? `${r.wall_time_s.toFixed(0)} s` : '—'}</td>
                    <td className="py-0.5 pr-2">{ev ? `${ev.cells_reaching_99}/${ev.cells}` : '—'}</td>
                    <td className="py-0.5 pr-2">{ev?.geo_mean_t99_vs_dfsa != null ? `${ev.geo_mean_t99_vs_dfsa.toFixed(2)}×` : '—'}</td>
                    <td className="py-0.5 pr-2 font-mono text-[11px]">{r.promoted ?? '—'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Panel>
      {run ? <RunDetail experiment={experiment} run={run} /> : null}
    </>
  )
}

function RunDetail({ experiment, run }: { experiment: string; run: TrainingRunDetail }) {
  const { t } = useTranslation()
  return (
    <>
      {run.status === 'failed' || run.status === 'interrupted' ? (
        <Panel title={t('thesis.training.error')} hint={run.status === 'interrupted' ? t('thesis.training.interruptedHint') : undefined}>
          <pre className="max-h-60 overflow-auto rounded bg-destructive/10 p-2 text-[11px] text-destructive">
            {String((run.meta as { traceback?: string } | null)?.traceback ?? run.error ?? '')}
          </pre>
        </Panel>
      ) : null}
      <Panel title={t('thesis.training.learning')} hint={t('thesis.training.learningHint')}>
        {run.curve.length ? (
          <div className="grid gap-3 xl:grid-cols-2">
            {CURVES.map(([key, label]) => (
              <CurveChart key={key} points={run.curve} field={key} label={t(label)} />
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">{t('thesis.training.noCurve')}</p>
        )}
      </Panel>
      <Panel title={t('thesis.training.evalMatrix')} hint={t('thesis.training.evalHint')}>
        {run.eval_matrix.length ? <EvalMatrix rows={run.eval_matrix} /> : <p className="text-xs text-muted-foreground">{t('thesis.training.noEval')}</p>}
      </Panel>
      {run.plots.length ? (
        <Panel title={t('thesis.training.plots')}>
          <div className="grid gap-3 xl:grid-cols-2">
            {run.plots.map((p) => (
              <a key={p} href={trainingPlotUrl(experiment, run.run, p)} target="_blank" rel="noreferrer">
                <img src={trainingPlotUrl(experiment, run.run, p)} alt={p} className="w-full rounded border bg-white" loading="lazy" />
              </a>
            ))}
          </div>
        </Panel>
      ) : null}
      {run.status === 'done' ? <PromoteBox experiment={experiment} run={run} /> : null}
    </>
  )
}

function rolling(y: (number | null)[], w: number): (number | null)[] {
  return y.map((_, i) => {
    const win = y.slice(Math.max(0, i - w + 1), i + 1).filter((v): v is number => v != null && Number.isFinite(v))
    return win.length ? win.reduce((a, b) => a + b, 0) / win.length : null
  })
}

function CurveChart({ points, field, label }: { points: TrainingCurvePoint[]; field: keyof TrainingCurvePoint; label: string }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const x = points.map((p) => p.timesteps)
  const y = points.map((p) => (typeof p[field] === 'number' ? (p[field] as number) : null))
  const w = Math.max(1, Math.round(points.length / 20))
  return (
    <Plot
      data={[
        { type: 'scattergl', mode: 'markers', x, y, name: label, marker: { size: 3, color: '#0072bd', opacity: 0.35 } },
        { type: 'scatter', mode: 'lines', x, y: rolling(y, w), name: t('thesis.training.rolling', { w }), line: { color: '#d95319', width: 2 } },
      ]}
      layout={{
        ...baseLayout(plot, { height: 220, margin: { t: 24, r: 12, b: 32, l: 48 }, showlegend: false }),
        title: { text: label, font: { size: 11 } },
        xaxis: axis(plot, t('thesis.training.steps')),
        yaxis: axis(plot, ''),
      }}
      config={PLOT_CONFIG}
      style={{ width: '100%' }}
      useResizeHandler
    />
  )
}

function EvalMatrix({ rows }: { rows: EvalMatrixRow[] }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const cands = [...new Set(rows.map((r) => r.candidate))].filter((c) => c !== 'dfsa')
  const cells = [...new Set(rows.map((r) => r.cell))].sort((a, b) => {
    const na = Number(a.split('_')[0].slice(1))
    const nb = Number(b.split('_')[0].slice(1))
    return na - nb || a.localeCompare(b)
  })
  const z = cands.map((c) => cells.map((cell) => rows.find((r) => r.candidate === c && r.cell === cell)?.t99_vs_dfsa ?? null))
  const span = Math.max(1, ...z.flat().map((v) => (v != null && v > 0 ? Math.abs(Math.log2(v)) : 0)))
  return (
    <div className="grid gap-3">
      <Plot
        data={[
          {
            type: 'heatmap',
            x: cells,
            y: cands,
            z: z.map((row) => row.map((v) => (v == null ? null : Math.log2(v)))),
            text: z.map((row) => row.map((v) => (v == null ? '—' : v.toFixed(2)))) as unknown as string[],
            texttemplate: '%{text}',
            hovertemplate: '%{y} · %{x}<br>T99 / DFSA = %{text}<extra></extra>',
            colorscale: [
              [0, '#1a9850'],
              [0.5, '#ffffbf'],
              [1, '#d73027'],
            ],
            zmin: -span,
            zmax: span,
            colorbar: { title: { text: 'log₂ T99/DFSA', side: 'right' }, thickness: 10, len: 1, lenmode: 'fraction' },
          },
        ]}
        layout={{
          ...baseLayout(plot, { height: 160 + 36 * cands.length, margin: { t: 8, r: 12, b: 120, l: 80 } }),
          xaxis: { ...axis(plot, ''), tickangle: -50 },
          yaxis: axis(plot, ''),
        }}
        config={PLOT_CONFIG}
        style={{ width: '100%' }}
        useResizeHandler
      />
      <div className="max-h-80 overflow-auto">
        <table className="w-full text-xs whitespace-nowrap tabular-nums">
          <thead className="sticky top-0 bg-card text-left text-muted-foreground">
            <tr>
              {['candidate', 'cell', 'identified', 't99', 'tMean', 'efficiency', 't99VsDfsa'].map((c) => (
                <th key={c} className="py-0.5 pr-2 font-normal">
                  {t(`thesis.training.matrix.${c}`)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={`${r.candidate}-${r.cell}`} className="border-t">
                <td className="py-0.5 pr-2">{r.candidate}</td>
                <td className="py-0.5 pr-2 font-mono text-[11px]">{r.cell}</td>
                <td className="py-0.5 pr-2">{r.identified_fraction != null ? `${(100 * r.identified_fraction).toFixed(1)}%` : '—'}</td>
                <td className="py-0.5 pr-2">{r.t99 != null ? `${r.t99.toFixed(2)} s` : '—'}</td>
                <td className="py-0.5 pr-2">{r.t_mean != null ? `${r.t_mean.toFixed(2)} s` : '—'}</td>
                <td className="py-0.5 pr-2">{r.resource_efficiency != null ? `${(100 * r.resource_efficiency).toFixed(2)}%` : '—'}</td>
                <td className="py-0.5 pr-2">{r.t99_vs_dfsa != null ? `${r.t99_vs_dfsa.toFixed(2)}×` : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function PromoteBox({ experiment, run }: { experiment: string; run: TrainingRunDetail }) {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const [pid, setPid] = useState('')
  const [force, setForce] = useState(false)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  async function promote() {
    setBusy(true)
    setMsg(null)
    try {
      const out = await promoteTrainingRun(experiment, run.run, { policy_id: pid.trim() || null, force })
      setMsg({ ok: true, text: t('thesis.training.promoted', { id: out.policy_id }) })
      await Promise.all([qc.invalidateQueries({ queryKey: thesisKeys.policies }), qc.invalidateQueries({ queryKey: thesisKeys.trainingExperiment(experiment) })])
    } catch (err) {
      setMsg({ ok: false, text: err instanceof Error ? err.message : String(err) })
    } finally {
      setBusy(false)
    }
  }
  return (
    <Panel title={t('thesis.training.promote')} hint={t('thesis.training.promoteHint')}>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <Input className="h-8 w-96" value={pid} onChange={(e) => setPid(e.target.value)} placeholder={run.policy_id ?? ''} />
        <label className="flex items-center gap-1">
          <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} />
          {t('thesis.training.overwrite')}
        </label>
        <Button type="button" size="sm" disabled={busy} onClick={() => void promote()}>
          {t('thesis.training.promoteButton')}
        </Button>
        {msg ? <span className={msg.ok ? 'text-green-600' : 'text-destructive'}>{msg.text}</span> : null}
      </div>
    </Panel>
  )
}

function PolicyRegistry() {
  const { t } = useTranslation()
  const policies = usePolicies()
  return (
    <Panel title={t('thesis.training.registry')} hint={t('thesis.training.registryHint')}>
      <div className="overflow-auto">
        <table className="w-full text-xs whitespace-nowrap tabular-nums">
          <thead className="text-left text-muted-foreground">
            <tr>
              {['policy', 'algo', 'alpha', 'scale', 'steps', 't99VsDfsa', 'sha', 'state'].map((c) => (
                <th key={c} className="py-0.5 pr-2 font-normal">
                  {t(`thesis.training.registryCols.${c}`)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(policies.data ?? []).map((p) => {
              const ev = p.eval_summary?.policy
              return (
                <tr key={p.policy_id} className={`border-t ${p.available ? '' : 'text-muted-foreground'}`}>
                  <td className="py-0.5 pr-2 font-mono text-[11px]">{p.policy_id}</td>
                  <td className="py-0.5 pr-2">{t(`thesis.training.algos.${p.algo}`, { defaultValue: p.algo ?? '—' })}</td>
                  <td className="py-0.5 pr-2">
                    {p.alpha ?? '—'} / {p.beta ?? '—'}
                  </td>
                  <td className="py-0.5 pr-2">{p.scale ?? '—'}</td>
                  <td className="py-0.5 pr-2">{p.training_steps?.toLocaleString() ?? '—'}</td>
                  <td className="py-0.5 pr-2">{ev?.geo_mean_t99_vs_dfsa != null ? `${ev.geo_mean_t99_vs_dfsa.toFixed(2)}×` : '—'}</td>
                  <td className="py-0.5 pr-2 font-mono text-[10px]">{p.sha256?.slice(0, 12) ?? '—'}</td>
                  <td className="py-0.5 pr-2">{p.available ? '✓' : <span className="text-destructive" title={p.reason ?? ''}>✗ {p.reason}</span>}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}

function HowTo() {
  const { t } = useTranslation()
  const steps = ['train', 'outputs', 'evaluate', 'promote', 'use'] as const
  return (
    <Panel title={t('thesis.training.howTo')}>
      <ol className="grid list-decimal gap-1 pl-5 text-xs">
        {steps.map((s) => (
          <li key={s}>{t(`thesis.training.steps_.${s}`)}</li>
        ))}
      </ol>
    </Panel>
  )
}
