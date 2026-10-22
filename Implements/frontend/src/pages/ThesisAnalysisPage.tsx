import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchSections } from '@/api/thesisSimulator'
import { LanguageToggle } from '@/components/LanguageToggle'
import { PaperNav } from '@/components/PaperNav'
import { ThemeToggle } from '@/components/ThemeToggle'
import { StatusChip } from '@/components/thesis/ThesisRightPanel'
import { ThesisSubNav } from '@/components/thesis/ThesisSubNav'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useInventoryRuns } from '@/hooks/useInventoryRuns'
import { useRunAnalysis } from '@/hooks/useRunAnalysis'
import { axis, baseLayout, PLOT_CONFIG } from '@/components/aperiodic/plotLayout'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/lib/Plot'
import type { RunAnalysis, SectionSummary } from '@/types/thesis'

const MAX_SELECTED = 8
/** One colour per selected run (MATLAB order, as in the paper figures). */
const RUN_COLORS = ['#0072bd', '#d95319', '#edb120', '#7e2f8e', '#77ac30', '#4dbeee', '#a2142f', '#525252']
const SUBTYPES = ['1', '2a', '2b'] as const
const SUBTYPE_DASH: Record<string, 'solid' | 'dash' | 'dot'> = { '1': 'solid', '2a': 'dash', '2b': 'dot' }
const STAGES = ['paging', 'm1', 'ebi', 'm2', 'm3'] as const
const STAGE_COLOR: Record<string, string> = { paging: '#4dbeee', m1: '#0072bd', ebi: '#7e2f8e', m2: '#77ac30', m3: '#edb120' }
const LEVELS = [50, 90, 95, 99]

function runLabel(a: RunAnalysis) {
  return `#${a.run_id} · ${a.scheme}`
}

export default function ThesisAnalysisPage() {
  const { t } = useTranslation()
  useEffect(() => {
    document.title = t('thesis.analysis.title')
  }, [t])

  const [sections, setSections] = useState<SectionSummary[]>([])
  const [sectionId, setSectionId] = useState<number | null>(null)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const list = await fetchSections()
        if (cancelled) return
        setSections(list)
        if (list.length && sectionId == null) setSectionId(list[0].id)
      } catch {
        /* soft-fail */
      }
    })()
    return () => {
      cancelled = true
    }
  }, [sectionId])

  const runs = useInventoryRuns(sectionId, { pollWhileLive: true })
  const [selected, setSelected] = useState<Set<number>>(new Set())
  useEffect(() => {
    setSelected(new Set())
  }, [sectionId])

  const analysis = useRunAnalysis(runs.runs, selected)

  const selectedAnalyses = useMemo<RunAnalysis[]>(
    () => Array.from(selected).map((id) => analysis.getAnalysis(id)).filter((a): a is RunAnalysis => !!a),
    [selected, analysis],
  )

  function toggleRun(id: number) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else if (next.size < MAX_SELECTED) {
        next.add(id)
      }
      return next
    })
  }

  return (
    <div className="flex h-dvh w-screen flex-col overflow-hidden bg-background">
      <header className="flex w-full shrink-0 items-center gap-4 border-b bg-card px-4 py-2">
        <div className="min-w-0">
          <PaperNav className="mb-1" />
          <div className="flex items-center gap-3">
            <h1 className="truncate text-lg font-medium">{t('thesis.analysis.title')}</h1>
            <ThesisSubNav />
          </div>
          <p className="truncate text-xs text-muted-foreground">{t('thesis.analysis.subtitle')}</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <LanguageToggle />
          <ThemeToggle />
        </div>
      </header>
      <div className="flex shrink-0 items-center gap-3 border-b px-4 py-2">
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>{t('thesis.analysis.sectionLabel')}</span>
          <Select
            value={sectionId == null ? '' : String(sectionId)}
            items={Object.fromEntries(sections.map((s) => [String(s.id), s.name]))}
            onValueChange={(v) => setSectionId(v == null ? null : Number(v))}
          >
            <SelectTrigger className="h-8 min-w-48">
              <SelectValue placeholder={t('thesis.analysis.sectionLabel')} />
            </SelectTrigger>
            <SelectContent align="start">
              {sections.map((s) => (
                <SelectItem key={s.id} value={String(s.id)}>
                  {s.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </label>
        <span className="text-xs text-muted-foreground">
          {t('thesis.analysis.selectedCount', { count: selected.size, max: MAX_SELECTED })}
        </span>
        {selected.size > 0 ? (
          <Button type="button" size="xs" variant="outline" onClick={() => setSelected(new Set())}>
            {t('thesis.analysis.clearSelection')}
          </Button>
        ) : null}
      </div>
      <div className="flex min-h-0 flex-1">
        <aside className="flex w-72 shrink-0 flex-col overflow-hidden border-r bg-card">
          <h2 className="shrink-0 border-b px-3 py-2 text-sm font-medium">
            {t('thesis.analysis.runsLabel')}
          </h2>
          <ScrollArea className="min-h-0 flex-1">
            <div className="flex flex-col gap-1 p-2">
              {runs.runs.length === 0 ? (
                <p className="px-1 text-xs text-muted-foreground">{t('thesis.analysis.noRuns')}</p>
              ) : null}
              {runs.runs.map((run) => {
                const active = selected.has(run.run_id)
                const atCap = !active && selected.size >= MAX_SELECTED
                return (
                  <label
                    key={run.run_id}
                    className={`flex cursor-pointer flex-col gap-1 rounded-lg border px-2 py-1.5 text-xs transition ${
                      active ? 'border-foreground bg-muted/60' : 'hover:bg-muted/40'
                    } ${atCap ? 'opacity-40' : ''}`}
                  >
                    <div className="flex items-center gap-2">
                      <Checkbox
                        checked={active}
                        disabled={atCap}
                        onCheckedChange={() => toggleRun(run.run_id)}
                      />
                      <span className="font-medium">#{run.run_id}</span>
                      <StatusChip status={run.status} />
                    </div>
                    <div className="flex justify-between text-muted-foreground">
                      <span>{run.scheme}</span>
                      <span className="tabular-nums">
                        {run.identified_total}/{run.total_devices}
                      </span>
                    </div>
                    <div className="flex justify-between text-muted-foreground">
                      <span>{run.rounds_total} r</span>
                      <span className="tabular-nums">{run.wall_duration_s.toFixed(2)} s</span>
                    </div>
                  </label>
                )
              })}
            </div>
          </ScrollArea>
          {analysis.loading ? (
            <p className="shrink-0 border-t px-3 py-2 text-[11px] text-muted-foreground">
              ⏳ {t('thesis.analysis.loading')}
            </p>
          ) : null}
          {analysis.error ? (
            <div className="shrink-0 border-t bg-destructive/10 px-3 py-2 text-[11px] text-destructive">
              {analysis.error}
              <button type="button" className="ml-2 underline" onClick={analysis.clearError}>
                ×
              </button>
            </div>
          ) : null}
        </aside>
        <main className="min-h-0 min-w-0 flex-1 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="flex flex-col gap-4 p-4">
              {selectedAnalyses.length === 0 ? (
                <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                  {t('thesis.analysis.selectHint')}
                </p>
              ) : (
                <>
                  <ChartPanel title={t('thesis.analysis.charts.identification')}>
                    <IdentificationChart analyses={selectedAnalyses} />
                  </ChartPanel>
                  <ChartPanel title={t('thesis.analysis.charts.bySubtype')}>
                    <SubtypeChart analyses={selectedAnalyses} />
                  </ChartPanel>
                  <ChartPanel title={t('thesis.analysis.charts.metrics')}>
                    <MetricsTable analyses={selectedAnalyses} />
                  </ChartPanel>
                  <div className="grid gap-4 xl:grid-cols-2">
                    <ChartPanel title={t('thesis.analysis.charts.slots')}>
                      <SlotsChart analyses={selectedAnalyses} />
                    </ChartPanel>
                    <ChartPanel title={t('thesis.analysis.charts.overhead')}>
                      <OverheadChart analyses={selectedAnalyses} />
                    </ChartPanel>
                    <ChartPanel title={t('thesis.analysis.charts.depletions')}>
                      <DepletionChart analyses={selectedAnalyses} />
                    </ChartPanel>
                    <ChartPanel title={t('thesis.analysis.charts.contribution')}>
                      <ContributionChart analyses={selectedAnalyses} />
                    </ChartPanel>
                  </div>
                </>
              )}
            </div>
          </ScrollArea>
        </main>
      </div>
    </div>
  )
}

function ChartPanel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border bg-card p-3">
      <h3 className="mb-2 text-xs font-medium text-muted-foreground">{title}</h3>
      {children}
    </section>
  )
}

function IdentificationChart({ analyses }: { analyses: RunAnalysis[] }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  // Frame up to the last identification: a run that stalls keeps simulating
  // for stall_timeout_s afterwards without adding anything to the curve.
  const xMax = 1.05 * Math.max(0, ...analyses.map((a) => a.identification_curve.at(-1)?.[0] ?? 0))
  const runs = analyses.map((a, i) => {
    const n = Math.max(1, a.summary.total_devices)
    return {
      x: [0, ...a.identification_curve.map((p) => p[0])],
      y: [0, ...a.identification_curve.map((p) => (100 * p[1]) / n)],
      type: 'scattergl' as const,
      mode: 'lines' as const,
      name: runLabel(a),
      line: { shape: 'hv' as const, width: 2, color: RUN_COLORS[i % RUN_COLORS.length] },
    }
  })
  return (
    <Plot
      data={runs}
      layout={{
        ...baseLayout(plot, { height: 340 }),
        xaxis: axis(plot, t('thesis.analysis.axis.time'), xMax > 0 ? { range: [0, xMax] } : {}),
        yaxis: axis(plot, t('thesis.charts.identifiedPct'), { range: [0, 101], tickvals: [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100] }),
        shapes: LEVELS.map((l) => ({
          type: 'line' as const,
          xref: 'paper' as const,
          x0: 0,
          x1: 1,
          y0: l,
          y1: l,
          line: { color: plot.grid, width: 1, dash: 'dash' as const },
        })),
      }}
      config={PLOT_CONFIG}
      style={{ width: '100%' }}
      useResizeHandler
    />
  )
}

function SubtypeChart({ analyses }: { analyses: RunAnalysis[] }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const xMax = 1.05 * Math.max(0, ...analyses.map((a) => a.identification_curve.at(-1)?.[0] ?? 0))
  const data = analyses.flatMap((a, i) =>
    SUBTYPES.map((s) => {
      const pts = a.identification_by_subtype?.[s] ?? []
      return {
        x: [0, ...pts.map((p) => p[0])],
        y: [0, ...pts.map((p) => p[1])],
        type: 'scattergl' as const,
        mode: 'lines' as const,
        name: `#${a.run_id} · ${t(`thesis.kind.device${s}`)}`,
        line: { shape: 'hv' as const, color: RUN_COLORS[i % RUN_COLORS.length], dash: SUBTYPE_DASH[s] },
      }
    }),
  )
  return (
    <Plot
      data={data}
      layout={{
        ...baseLayout(plot, { height: 280 }),
        xaxis: axis(plot, t('thesis.analysis.axis.time'), xMax > 0 ? { range: [0, xMax] } : {}),
        yaxis: axis(plot, t('thesis.analysis.axis.count'), { rangemode: 'tozero' }),
      }}
      config={PLOT_CONFIG}
      style={{ width: '100%' }}
      useResizeHandler
    />
  )
}

function SlotsChart({ analyses }: { analyses: RunAnalysis[] }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const x = analyses.map((a) => `#${a.run_id}`)
  const agg = analyses.map((a) => a.aggregates)
  return (
    <Plot
      data={[
        { type: 'bar', x, y: agg.map((g) => g?.success_total ?? 0), name: t('thesis.analysis.rounds.success'), marker: { color: '#77ac30' } },
        { type: 'bar', x, y: agg.map((g) => g?.collision_total ?? 0), name: t('thesis.analysis.rounds.collision'), marker: { color: '#d95319' } },
        { type: 'bar', x, y: agg.map((g) => g?.empty_total ?? 0), name: t('thesis.analysis.rounds.empty'), marker: { color: '#a1a1aa' } },
        {
          type: 'scatter',
          mode: 'lines+markers',
          x,
          y: agg.map((g) => 100 * (g?.resource_efficiency ?? 0)),
          yaxis: 'y2',
          name: t('thesis.charts.efficiency'),
          line: { color: '#7e2f8e' },
        },
      ]}
      layout={{
        ...baseLayout(plot, { height: 260, barmode: 'stack' }),
        xaxis: axis(plot, t('thesis.analysis.cols.run')),
        yaxis: axis(plot, t('thesis.analysis.axis.slots')),
        yaxis2: axis(plot, '%', { overlaying: 'y', side: 'right', range: [0, 100] }),
      }}
      config={PLOT_CONFIG}
      style={{ width: '100%' }}
      useResizeHandler
    />
  )
}

function OverheadChart({ analyses }: { analyses: RunAnalysis[] }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const x = analyses.map((a) => `#${a.run_id}`)
  return (
    <Plot
      data={STAGES.map((st) => ({
        type: 'bar' as const,
        x,
        y: analyses.map((a) => a.aggregates?.overhead_s[st] ?? 0),
        name: t(`thesis.charts.stage.${st}`),
        marker: { color: STAGE_COLOR[st] },
      }))}
      layout={{
        ...baseLayout(plot, { height: 260, barmode: 'stack' }),
        xaxis: axis(plot, t('thesis.analysis.cols.run')),
        yaxis: axis(plot, t('thesis.analysis.axis.overheadS')),
      }}
      config={PLOT_CONFIG}
      style={{ width: '100%' }}
      useResizeHandler
    />
  )
}

function DepletionChart({ analyses }: { analyses: RunAnalysis[] }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const x = analyses.map((a) => `#${a.run_id}`)
  return (
    <Plot
      data={STAGES.map((st) => ({
        type: 'bar' as const,
        x,
        y: analyses.map((a) => {
          const row = a.aggregates?.deaths_by_stage[st] ?? {}
          return SUBTYPES.reduce((acc, s) => acc + (row[s] ?? 0), 0)
        }),
        name: t(`thesis.charts.stage.${st}`),
        marker: { color: STAGE_COLOR[st] },
      }))}
      layout={{
        ...baseLayout(plot, { height: 260, barmode: 'group' }),
        xaxis: axis(plot, t('thesis.analysis.cols.run')),
        yaxis: axis(plot, t('thesis.live.depletions')),
      }}
      config={PLOT_CONFIG}
      style={{ width: '100%' }}
      useResizeHandler
    />
  )
}

function ContributionChart({ analyses }: { analyses: RunAnalysis[] }) {
  const plot = usePlotTheme()
  const readerIds = Array.from(
    new Set(analyses.flatMap((a) => Object.keys(a.reader_contribution).map((k) => Number(k)))),
  ).sort((a, b) => a - b)
  const data = readerIds.map((rid) => ({
    type: 'bar' as const,
    name: `R#${rid}`,
    x: analyses.map((a) => `#${a.run_id}`),
    y: analyses.map((a) => Number(a.reader_contribution[rid] ?? 0)),
  }))
  return (
    <Plot
      data={data}
      layout={{ ...baseLayout(plot, { height: 260, barmode: 'group' }), xaxis: axis(plot, ''), yaxis: axis(plot, '') }}
      config={PLOT_CONFIG}
      style={{ width: '100%' }}
      useResizeHandler
    />
  )
}

function MetricsTable({ analyses }: { analyses: RunAnalysis[] }) {
  const { t } = useTranslation()
  const fmt = (v: number | null | undefined) => (v == null ? t('thesis.analysis.unreached') : v.toFixed(2))
  const cols = [
    t('thesis.analysis.cols.run'),
    t('thesis.analysis.cols.scheme'),
    'T50',
    'T90',
    'T95',
    'T99',
    t('thesis.analysis.cols.identified'),
    t('thesis.charts.efficiency'),
    t('thesis.live.depletions'),
    t('thesis.live.unreachable'),
    t('thesis.analysis.cols.dropped'),
    t('thesis.live.simTime'),
    t('thesis.analysis.cols.duration'),
  ]
  return (
    <div className="overflow-auto">
      <p className="mb-1 text-[11px] text-muted-foreground">{t('thesis.analysis.tNote')}</p>
      <table className="w-full text-xs">
        <thead className="bg-muted/40 text-left text-muted-foreground">
          <tr>
            {cols.map((c) => (
              <th key={c} className="px-2 py-1 font-normal">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {analyses.map((a, i) => {
            const pt = a.population_completion_times ?? a.completion_times
            return (
              <tr key={a.run_id} className="border-t tabular-nums">
                <td className="px-2 py-1">
                  <span className="mr-1 inline-block size-2 rounded-full" style={{ background: RUN_COLORS[i % RUN_COLORS.length] }} />#
                  {a.run_id}
                </td>
                <td className="px-2 py-1">{a.scheme}</td>
                <td className="px-2 py-1">{fmt(pt['50'])}</td>
                <td className="px-2 py-1">{fmt(pt['90'])}</td>
                <td className="px-2 py-1">{fmt(pt['95'])}</td>
                <td className="px-2 py-1">{fmt(pt['99'])}</td>
                <td className="px-2 py-1">
                  {a.summary.identified_total}/{a.summary.total_devices}
                </td>
                <td className="px-2 py-1">{(100 * (a.aggregates?.resource_efficiency ?? 0)).toFixed(1)}%</td>
                <td className="px-2 py-1">{a.summary.died_count}</td>
                <td className="px-2 py-1">{a.summary.unreachable_count ?? 0}</td>
                <td className="px-2 py-1">{a.summary.dropped_count}</td>
                <td className="px-2 py-1">{(a.summary.sim_time_s ?? 0).toFixed(2)}</td>
                <td className="px-2 py-1">{a.summary.wall_duration_s.toFixed(2)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
