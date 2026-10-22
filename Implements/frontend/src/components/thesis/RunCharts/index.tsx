import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchDeviceMap, fetchIdentifications } from '@/api/thesisRuns'
import { axis, baseLayout, MATLAB, PLOT_CONFIG } from '@/components/aperiodic/plotLayout'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import type { LiveRunState } from '@/hooks/useLiveRun'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/lib/Plot'
import { thesisKeys } from '@/lib/thesisQueryKeys'
import type { RunRound, RunScheme, Scene } from '@/types/thesis'
import {
  binRounds,
  buildScope,
  PERCENTILES,
  scopedCurve,
  STAGES,
  SUBTYPE_COLOR,
  SUBTYPES,
  timeToPercent,
  useThrottled,
  type Scope,
} from './data'
import { ChartHelp } from './ChartHelp'
import { EnergyChart, PinCdfChart } from './EnergyCharts'
import { MetricsPanel } from './MetricsPanel'
import { RoundMapPanel } from './RoundMapPanel'

const MAX_BARS = 400
const TABS = ['ident', 'controller', 'outcome', 'timing', 'energy', 'round', 'metrics', 'pin'] as const
type Tab = (typeof TABS)[number]
const READER_COLORS = ['#0072bd', '#d95319', '#edb120', '#7e2f8e', '#77ac30', '#4dbeee', '#a2142f', '#525252', '#1d4ed8', '#0f766e', '#c2410c', '#be185d']
const STAGE_COLOR: Record<string, string> = { paging: '#4dbeee', m1: MATLAB.blue, ebi: MATLAB.purple, m2: MATLAB.green, m3: MATLAB.yellow }

/**
 * Bottom chart dock. The reader picker sets one scope for every tab:
 * "all" = every device and every reader; "#id" = the devices inside that
 * reader's coverage (engine's own coverage test) and that reader's rounds.
 * While a finished run is replayed, every chart stops at the replay time.
 */
export function RunCharts({
  runId,
  scheme,
  scene,
  live,
  totalDevices,
  reader,
  onReader,
}: {
  runId: number
  scheme: RunScheme
  scene: Scene
  live: LiveRunState
  totalDevices: number
  /** chart scope, owned by the page so clicking a reader on the map can set it */
  reader: number | 'all'
  onReader: (reader: number | 'all') => void
}) {
  const { t } = useTranslation()
  const isLive = live.status === 'running' || live.status === 'pending'
  // 10 Hz stream -> redraw the heavy Plotly charts at most twice a second.
  const allRounds = useThrottled(live.rounds, 500)
  const simTime = useThrottled(live.simTime, 500)
  const devices = useThrottled(live.devices, 1000)
  const cursor = live.viewTime // replay time; null = latest

  const mapQuery = useQuery({
    queryKey: thesisKeys.deviceMap(runId),
    queryFn: () => fetchDeviceMap(runId),
    staleTime: Infinity, // the run's scene snapshot never changes
  })
  const identQuery = useQuery({
    queryKey: thesisKeys.identifications(runId),
    queryFn: () => fetchIdentifications(runId),
    refetchInterval: isLive ? 1000 : false,
    staleTime: isLive ? 0 : Infinity,
  })

  const rounds = useMemo(
    () => (cursor == null ? allRounds : allRounds.filter((r) => r.t_start_s <= cursor)),
    [allRounds, cursor],
  )
  const readerIds = useMemo(
    () => Object.keys(mapQuery.data?.coverage ?? {}).map(Number).sort((a, b) => a - b),
    [mapQuery.data],
  )
  const readerStats = useMemo(() => {
    const m = new Map<number, { rounds: number; identified: number }>()
    for (const id of readerIds) m.set(id, { rounds: 0, identified: 0 })
    for (const r of rounds) {
      const s = m.get(r.reader_id) ?? { rounds: 0, identified: 0 }
      s.rounds++
      s.identified += r.served ?? 0
      m.set(r.reader_id, s)
    }
    return [...m.entries()].sort((a, b) => a[0] - b[0])
  }, [rounds, readerIds])

  const [tab, setTab] = useState<Tab>('ident')
  const [unit, setUnit] = useState<'count' | 'pct'>('count')
  const scope = useMemo(() => buildScope(mapQuery.data, reader), [mapQuery.data, reader])
  const scopeRounds = useMemo(
    () => (reader === 'all' ? rounds : rounds.filter((r) => r.reader_id === reader)),
    [rounds, reader],
  )
  const curve = useMemo(
    () => scopedCurve(identQuery.data, mapQuery.data, scope, cursor),
    [identQuery.data, mapQuery.data, scope, cursor],
  )
  const tNow = cursor ?? simTime

  return (
    <Tabs value={tab} onValueChange={(v) => setTab(v as Tab)} className="flex h-full min-h-0 flex-col gap-1">
      <div className="flex flex-wrap items-center gap-2">
        <TabsList className="h-7">
          {TABS.map((k) => (
            <TabsTrigger key={k} value={k} className="px-2 text-[11px]">
              {t(`thesis.charts.tab.${k}`)}
            </TabsTrigger>
          ))}
        </TabsList>
        <div className="ml-auto flex items-center gap-1.5 text-[11px] text-muted-foreground">
          {tab === 'ident' ? (
            <ToggleGroup
              size="sm"
              variant="outline"
              value={[unit]}
              onValueChange={(v) => v[0] && setUnit(v[0] as 'count' | 'pct')}
            >
              <ToggleGroupItem value="count" className="h-6 px-2 text-[11px]">
                {t('thesis.charts.unitCount')}
              </ToggleGroupItem>
              <ToggleGroupItem value="pct" className="h-6 px-2 text-[11px]">
                %
              </ToggleGroupItem>
            </ToggleGroup>
          ) : null}
          {reader !== 'all' ? (
            <span className="tabular-nums">{t('thesis.charts.scopeSize', { n: scope.size })}</span>
          ) : null}
          {t('thesis.charts.reader')}
          <Select
            value={String(reader)}
            items={Object.fromEntries([
              ['all', t('thesis.charts.allReaders')],
              ...readerStats.map(([id]) => [String(id), `#${id}`]),
            ])}
            onValueChange={(v) => onReader(v == null || v === 'all' ? 'all' : Number(v))}
          >
            <SelectTrigger size="sm" className="h-7 min-w-36 text-[11px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent align="end" alignItemWithTrigger={false} className="max-h-72 min-w-60">
              <SelectItem value="all" className="text-xs">
                {t('thesis.charts.allReaders')}
              </SelectItem>
              {readerStats.map(([id, st]) => (
                <SelectItem key={id} value={String(id)} className="text-xs">
                  <span className="flex w-full items-center justify-between gap-3">
                    <span className="font-medium">#{id}</span>
                    <span className="tabular-nums text-muted-foreground">
                      {t('thesis.charts.readerItem', { identified: st.identified, rounds: st.rounds })}
                    </span>
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <ChartHelp tab={tab} />
      <div className="min-h-0 flex-1">
        <TabsContent value="ident" className="h-full">
          <IdentificationChart scope={scope} curve={curve} tNow={tNow} fallbackTotal={totalDevices} scheme={scheme} unit={unit} />
        </TabsContent>
        <TabsContent value="controller" className="h-full">
          <ControllerChart rounds={scopeRounds} all={reader === 'all'} tNow={tNow} />
        </TabsContent>
        <TabsContent value="outcome" className="h-full">
          <OutcomeChart rounds={scopeRounds} all={reader === 'all'} tNow={tNow} />
        </TabsContent>
        <TabsContent value="timing" className="h-full">
          <TimingChart rounds={scopeRounds} all={reader === 'all'} tNow={tNow} />
        </TabsContent>
        <TabsContent value="energy" className="h-full">
          <EnergyChart map={mapQuery.data} scope={scope} devices={devices} rounds={scopeRounds} />
        </TabsContent>
        <TabsContent value="round" className="h-full">
          <RoundMapPanel runId={runId} rounds={scopeRounds} periodic={scheme === 'periodic'} followKey={cursor} />
        </TabsContent>
        <TabsContent value="metrics" className="h-full">
          <MetricsPanel
            rounds={scopeRounds}
            scope={scope}
            curve={curve}
            all={reader === 'all'}
            counters={live.counters}
            replaying={cursor != null}
            devices={devices}
          />
        </TabsContent>
        <TabsContent value="pin" className="h-full">
          <PinCdfChart scene={scene} map={mapQuery.data} scope={scope} />
        </TabsContent>
      </div>
    </Tabs>
  )
}

function ChartBox({ children }: { children: React.ReactNode }) {
  return <div className="h-full min-h-[180px] w-full">{children}</div>
}

function vLine(x: number, color: string, dash: 'dot' | 'dash' = 'dot') {
  return {
    type: 'line' as const,
    x0: x,
    x1: x,
    yref: 'paper' as const,
    y0: 0,
    y1: 1,
    line: { color, width: 1, dash },
  }
}

/** Identified-% vs time for the current scope (all devices, or one reader's coverage), with T50…T99. */
function IdentificationChart({
  scope,
  curve,
  tNow,
  fallbackTotal,
  scheme,
  unit,
}: {
  scope: Scope
  curve: ReturnType<typeof scopedCurve>
  tNow: number
  fallbackTotal: number
  scheme: RunScheme
  /** count = devices identified; pct = share of the in-scope population (per subtype for the dotted lines) */
  unit: 'count' | 'pct'
}) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const n = Math.max(1, scope.size || fallbackTotal)
  const marks = PERCENTILES.map((p) => ({ p, t: timeToPercent(curve.t, curve.total, n, p) })).filter(
    (m): m is { p: (typeof PERCENTILES)[number]; t: number } => m.t != null,
  )
  // Extend each step line to "now" (live / replay time) so the last level is visible.
  const xs = [...curve.t, Math.max(tNow, curve.t[curve.t.length - 1] ?? 0)]
  const extend = (ys: number[]) => [...ys, ys[ys.length - 1]]
  const xMax = (xs[xs.length - 1] || 1) * 1.03
  return (
    <ChartBox>
      <Plot
        data={[
          {
            x: xs,
            y: extend(curve.total).map((v) => (unit === 'pct' ? (100 * v) / n : v)),
            type: 'scatter',
            mode: 'lines',
            line: { shape: 'hv', width: 2.8, color: scheme === 'periodic' ? MATLAB.red : MATLAB.yellow },
            name: t('thesis.charts.all'),
          },
          // Each subtype as a share of its own in-scope population.
          ...SUBTYPES.filter((s) => scope.subtypeSize[s] > 0).map((s) => ({
            x: xs,
            y: extend(curve.sub[s]).map((v) => (unit === 'pct' ? (100 * v) / scope.subtypeSize[s] : v)),
            type: 'scatter' as const,
            mode: 'lines' as const,
            line: { shape: 'hv' as const, width: 1.2, dash: 'dot' as const, color: SUBTYPE_COLOR[s] },
            name: t(`thesis.kind.device${s}`),
          })),
        ]}
        layout={{
          ...baseLayout(plot),
          xaxis: axis(plot, t('thesis.charts.time'), { range: [0, xMax] }),
          yaxis:
            unit === 'pct'
              ? axis(plot, t('thesis.charts.identifiedPct'), {
                  range: [0, 101],
                  tickvals: [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100],
                })
              : axis(plot, t('thesis.charts.identifiedCount'), { range: [0, n * 1.02] }),
          shapes: [...marks.map((m) => vLine(m.t, plot.line, 'dash')), vLine(tNow, MATLAB.purple)],
          annotations: marks.map((m) => ({
            x: m.t,
            y: 1,
            yref: 'paper' as const,
            text: `T${m.p}`,
            showarrow: false,
            yanchor: 'bottom' as const,
            font: { size: 10, color: plot.font },
          })),
        }}
        config={PLOT_CONFIG}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
      />
    </ChartBox>
  )
}

/** One reader: K, p*, n̂ vs true backlog. All readers: one K line and one backlog line per reader. */
function ControllerChart({ rounds, all, tNow }: { rounds: RunRound[]; all: boolean; tNow: number }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const data = useMemo(() => {
    if (!all) {
      const x = rounds.map((r) => r.t_start_s)
      return [
        { x, y: rounds.map((r) => r.k_estimate), type: 'scattergl', mode: 'lines', line: { shape: 'hv', color: MATLAB.blue }, name: 'K' },
        { x, y: rounds.map((r) => r.pstar), type: 'scattergl', mode: 'lines', line: { shape: 'hv', color: MATLAB.red }, yaxis: 'y2', name: 'p*' },
        { x, y: rounds.map((r) => r.n_hat), type: 'scattergl', mode: 'markers', marker: { size: 4, color: MATLAB.green }, xaxis: 'x2', yaxis: 'y3', name: t('thesis.charts.nHat') },
        { x, y: rounds.map((r) => r.backlog_true), type: 'scattergl', mode: 'lines', line: { shape: 'hv', color: MATLAB.purple, dash: 'dot' }, xaxis: 'x2', yaxis: 'y3', name: t('thesis.charts.backlogTrue') },
        { x, y: rounds.map((r) => r.joiners), type: 'scattergl', mode: 'lines', line: { shape: 'hv', color: MATLAB.cyan, width: 1 }, xaxis: 'x2', yaxis: 'y3', name: t('thesis.charts.joiners') },
      ]
    }
    const byReader = new Map<number, RunRound[]>()
    for (const r of rounds) {
      const list = byReader.get(r.reader_id) ?? []
      list.push(r)
      byReader.set(r.reader_id, list)
    }
    return [...byReader.entries()]
      .sort((a, b) => a[0] - b[0])
      .flatMap(([id, rs], i) => {
        const color = READER_COLORS[i % READER_COLORS.length]
        const x = rs.map((r) => r.t_start_s)
        return [
          { x, y: rs.map((r) => r.k_estimate), type: 'scattergl', mode: 'lines', line: { shape: 'hv', color, width: 1.2 }, name: `#${id}`, legendgroup: String(id) },
          { x, y: rs.map((r) => r.backlog_true), type: 'scattergl', mode: 'lines', line: { shape: 'hv', color, width: 1, dash: 'dot' }, xaxis: 'x2', yaxis: 'y3', name: `#${id}`, legendgroup: String(id), showlegend: false },
        ]
      })
  }, [rounds, all, t])
  return (
    <ChartBox>
      <Plot
        data={data as Plotly.Data[]}
        layout={{
          ...baseLayout(plot),
          xaxis: axis(plot, '', { anchor: 'y', domain: [0, 1], matches: 'x2', showticklabels: false }),
          yaxis: axis(plot, 'K', { domain: [0.55, 1], rangemode: 'tozero' }),
          yaxis2: axis(plot, 'p*', { overlaying: 'y', side: 'right', range: [0, 1.05] }),
          xaxis2: axis(plot, t('thesis.charts.time'), { anchor: 'y3' }),
          yaxis3: axis(plot, all ? t('thesis.charts.backlogTrue') : t('thesis.charts.devices'), { domain: [0, 0.45], anchor: 'x2', rangemode: 'tozero' }),
          shapes: [vLine(tNow, MATLAB.purple)],
        }}
        config={PLOT_CONFIG}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
      />
    </ChartBox>
  )
}

function lastRounds(rounds: RunRound[]): RunRound[] {
  return rounds.length > MAX_BARS ? rounds.slice(-MAX_BARS) : rounds
}

/** Slot outcomes: per round for one reader, summed over time bins for all readers. */
function OutcomeChart({ rounds, all, tNow }: { rounds: RunRound[]; all: boolean; tNow: number }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const rows = useMemo(() => {
    if (all) {
      return binRounds(rounds).map((b) => ({ x: (b.t0 + b.t1) / 2, s: b.success, c: b.collision, e: b.empty, slots: b.slots }))
    }
    return lastRounds(rounds).map((r) => ({ x: r.t_start_s, s: r.success_count, c: r.collision_count, e: r.empty_count, slots: r.slot_count }))
  }, [rounds, all])
  const x = rows.map((r) => r.x)
  return (
    <ChartBox>
      <Plot
        data={[
          { x, y: rows.map((r) => r.s), type: 'bar', marker: { color: MATLAB.green }, name: t('thesis.analysis.rounds.success') },
          { x, y: rows.map((r) => r.c), type: 'bar', marker: { color: MATLAB.red }, name: t('thesis.analysis.rounds.collision') },
          { x, y: rows.map((r) => r.e), type: 'bar', marker: { color: '#a1a1aa' }, name: t('thesis.analysis.rounds.empty') },
          {
            x,
            y: rows.map((r) => (r.slots > 0 ? (100 * r.s) / r.slots : 0)),
            type: 'scatter',
            mode: 'lines',
            yaxis: 'y2',
            line: { color: MATLAB.purple, width: 1.4 },
            name: t('thesis.charts.efficiency'),
          },
        ]}
        layout={{
          ...baseLayout(plot, { barmode: 'stack', bargap: 0.05 }),
          xaxis: axis(plot, all ? t('thesis.charts.timeBin') : t('thesis.charts.roundStart')),
          yaxis: axis(plot, t('thesis.analysis.axis.slots'), { rangemode: 'tozero' }),
          yaxis2: axis(plot, '%', { overlaying: 'y', side: 'right', range: [0, 100] }),
          shapes: [vLine(tNow, MATLAB.purple)],
        }}
        config={PLOT_CONFIG}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
      />
    </ChartBox>
  )
}

/** Frame time per stage: per round for one reader, mean per round in each time bin for all readers. */
function TimingChart({ rounds, all, tNow }: { rounds: RunRound[]; all: boolean; tNow: number }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const rows = useMemo(() => {
    if (all) {
      return binRounds(rounds).map((b) => ({
        x: (b.t0 + b.t1) / 2,
        v: Object.fromEntries(STAGES.map((k) => [k, b.timing[k] / b.rounds])) as Record<string, number>,
      }))
    }
    return lastRounds(rounds).map((r) => ({
      x: r.t_start_s,
      v: Object.fromEntries(STAGES.map((k) => [k, r.timing?.[k] ?? 0])) as Record<string, number>,
    }))
  }, [rounds, all])
  return (
    <ChartBox>
      <Plot
        data={STAGES.map((k) => ({
          x: rows.map((r) => r.x),
          y: rows.map((r) => r.v[k] * 1e3),
          type: 'bar' as const,
          marker: { color: STAGE_COLOR[k] },
          name: t(`thesis.charts.stage.${k}`),
        }))}
        layout={{
          ...baseLayout(plot, { barmode: 'stack', bargap: 0.05 }),
          xaxis: axis(plot, all ? t('thesis.charts.timeBin') : t('thesis.charts.roundStart')),
          yaxis: axis(plot, all ? t('thesis.charts.frameMsMean') : t('thesis.charts.frameMs'), { rangemode: 'tozero' }),
          shapes: [vLine(tNow, MATLAB.purple)],
        }}
        config={PLOT_CONFIG}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
      />
    </ChartBox>
  )
}
