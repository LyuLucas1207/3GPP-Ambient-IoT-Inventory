import { useQuery } from '@tanstack/react-query'
import { GripVertical, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchTimeline } from '@/apis/thesisRuns'
import { axis, baseLayout, PLOT_CONFIG } from '@/features/aperiodic/components/plotLayout'
import { DeviceTimeline } from '@/features/thesis/components/timefreq/DeviceTimeline'
import { TimeFreqSection } from '@/features/thesis/components/timefreq/TimeFreqSection'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { LiveDevices } from '@/features/thesis/hooks/useLiveRun'
import { useDeviceMetrics } from '@/features/thesis/hooks/useMultiReader'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/utils/Plot'
import { thesisKeys } from '@/features/thesis/lib/thesisQueryKeys'
import { readerLinksForDevice } from '@/features/thesis/lib/thesisReach'
import { RUN_STATE_COLOR, RUN_STATE_LABELS, type RunStateLabel } from '@/features/thesis/lib/thesisRunStates'
import type { Placement, RunStatus, RunSummary, Scene, Timeline } from '@/features/thesis/types'

/** Device event types in protocol order (rows of the state plot). */
const EVENT_ORDER = [
  'dropped',
  'depleted',
  'ungrouped',
  'missed_page',
  'paged',
  'latched',
  'm1_tx',
  'm1_empty',
  'm1_collision',
  'm1_interfered',
  'm1_success',
  'budget_drop',
  'ebi_received',
  'm2_rx',
  'm2_interfered',
  'm3_tx',
  'm3_interfered',
  'identified',
] as const

/** ``DROP_CAUSE_LABEL`` of the backend (``inventory/state.py``). */
const DROP_CAUSES = ['', 'unreachable', 'max_time_reached', 'stopped', 'no_progress', 'terminated_early'] as const

const TIMELINE_REFRESH_MS = 1000
const MAX_TABLE_ROWS = 400
const WIDTH_KEY = 'thesis.deviceDrawer.width'
const WIDTH_MIN = 420
const WIDTH_DEFAULT = 560

function readDrawerWidth(): number {
  try {
    const v = Number(localStorage.getItem(WIDTH_KEY))
    return Number.isFinite(v) && v >= WIDTH_MIN ? v : WIDTH_DEFAULT
  } catch {
    return WIDTH_DEFAULT
  }
}

/**
 * Right-hand, non-modal drawer for one device: static radio facts (works
 * without a run), the live state from the SSE feed, and its event history.
 */
export function DeviceInspector({
  scene,
  placement,
  live,
  runId,
  runStatus,
  run = null,
  nowS = null,
  onClose,
}: {
  scene: Scene
  placement: Placement
  live: LiveDevices | null
  runId: number | null
  runStatus: RunStatus | null
  /** selected run: skipped readers and the D2R default */
  run?: RunSummary | null
  /** Live simulation clock, or the replay position. Null shows the finished trace. */
  nowS?: number | null
  onClose: () => void
}) {
  const { t } = useTranslation()
  const [width, setWidth] = useState(readDrawerWidth)
  const [shown, setShown] = useState(false)
  const [dragging, setDragging] = useState(false)
  useEffect(() => {
    const id = requestAnimationFrame(() => setShown(true))
    return () => cancelAnimationFrame(id)
  }, [])
  const deviceId = placement.id as number
  const idx = live?.indexById.get(deviceId)
  const code = idx != null && live ? live.codes[idx] : null
  const state: RunStateLabel | null = code != null ? (RUN_STATE_LABELS[code] ?? null) : null
  const energyJ = idx != null && live ? live.energy[idx] : null

  const runD2r = run?.include_d2r
  const runDisabled = run?.disabled_reader_ids
  const readers = useMemo(
    () => readerLinksForDevice(scene.placements, placement, { include_d2r: runD2r, disabled_reader_ids: runDisabled }),
    [scene, placement, runD2r, runDisabled],
  )
  const reachable = readers.filter((r) => r.inside && !r.disabled)

  // Event history: polled once a second while the run is live, fetched once otherwise.
  const liveRun = runStatus === 'running' || runStatus === 'pending'
  const timelineQuery = useQuery({
    queryKey: thesisKeys.timeline(runId, deviceId),
    queryFn: () => fetchTimeline(runId as number, deviceId),
    enabled: runId != null,
    refetchInterval: liveRun ? TIMELINE_REFRESH_MS : false,
    staleTime: liveRun ? 0 : Infinity,
  })
  const timeline: Timeline | null = timelineQuery.data ?? null
  const metricsQuery = useDeviceMetrics(runId, runStatus)
  const metrics = useMemo(
    () => metricsQuery.data?.devices.find((d) => d.device_id === deviceId) ?? null,
    [metricsQuery.data, deviceId],
  )

  const stats = useMemo(() => {
    const ev = timeline?.events ?? []
    const count = (type: string) => ev.filter((e) => e.event_type === type).length
    const ident = ev.find((e) => e.event_type === 'identified')
    return {
      pages: count('paged') + count('missed_page'),
      attempts: count('m1_tx'),
      collisions: count('m1_collision'),
      depletions: count('depleted'),
      identifiedAt: ident?.t_s ?? null,
      identifiedBy: ident?.reader_id ?? null,
    }
  }, [timeline])

  function startResize(event: React.PointerEvent) {
    event.preventDefault()
    const startX = event.clientX
    const startW = width
    setDragging(true)
    const move = (ev: PointerEvent) => {
      const max = Math.min(960, window.innerWidth * 0.72)
      const next = Math.min(max, Math.max(WIDTH_MIN, startW + startX - ev.clientX))
      setWidth(next)
    }
    const up = () => {
      setDragging(false)
      setWidth((current) => {
        try {
          localStorage.setItem(WIDTH_KEY, String(Math.round(current)))
        } catch {
          /* per-viewer convenience only */
        }
        return current
      })
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerup', up)
    }
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', up)
  }

  return (
    <aside
      className={`relative flex h-full shrink-0 flex-col overflow-hidden border-l bg-card ${dragging ? '' : 'transition-[width] duration-200 ease-out'}`}
      style={{ width: shown ? width : 0 }}
    >
      <div
        role="separator"
        aria-orientation="vertical"
        aria-label={t('thesis.inspector.resize')}
        className="absolute inset-y-0 left-0 z-10 w-1.5 cursor-ew-resize hover:bg-foreground/15"
        onPointerDown={startResize}
      />
      <header className="flex shrink-0 items-center gap-2 border-b px-2 py-1.5">
        <button
          type="button"
          aria-label={t('thesis.inspector.resize')}
          className="inline-flex size-7 cursor-ew-resize items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
          onPointerDown={startResize}
        >
          <GripVertical className="size-4" />
        </button>
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-sm font-medium">
            {t('thesis.inspector.title', { id: deviceId, subtype: placement.subtype ?? '' })}
          </h2>
          <p className="text-[11px] text-muted-foreground tabular-nums">
            ({placement.x_m.toFixed(2)}, {placement.y_m.toFixed(2)}) m
          </p>
        </div>
        <Button type="button" size="icon-sm" variant="ghost" onClick={onClose} aria-label={t('thesis.inspector.close')}>
          <X />
        </Button>
      </header>
      <ScrollArea className="min-h-0 flex-1">
        <div className="grid gap-3 p-3 text-xs">
          <section className="grid gap-1.5">
            <h3 className="font-medium">{t('thesis.inspector.live')}</h3>
            {runId == null ? (
              <p className="text-muted-foreground">{t('thesis.inspector.noRun')}</p>
            ) : (
              <div className="grid grid-cols-2 gap-1.5">
                <Stat label={t('thesis.inspector.state')}>
                  {state ? (
                    <span className="inline-flex items-center gap-1.5">
                      <span className="size-2.5 rounded-full" style={{ background: RUN_STATE_COLOR[state] }} />
                      {t(`thesis.live.state.${state}`)}
                    </span>
                  ) : (
                    '—'
                  )}
                </Stat>
                <Stat label={t('thesis.inspector.energy')}>{energyJ != null ? `${(energyJ * 1e6).toFixed(3)} µJ` : '—'}</Stat>
                <Stat label={t('thesis.inspector.pages')}>{stats.pages}</Stat>
                <Stat label={t('thesis.inspector.attempts')}>{stats.attempts}</Stat>
                <Stat label={t('thesis.inspector.collisions')}>{stats.collisions}</Stat>
                <Stat label={t('thesis.inspector.depletions')}>{stats.depletions}</Stat>
                <Stat label={t('thesis.inspector.identifiedAt')}>
                  {stats.identifiedAt != null ? `${stats.identifiedAt.toFixed(3)} s` : '—'}
                </Stat>
                <Stat label={t('thesis.inspector.identifiedBy')}>{stats.identifiedBy != null ? `#${stats.identifiedBy}` : '—'}</Stat>
              </div>
            )}
          </section>

          {runId != null ? (
            <section className="grid gap-1.5">
              <h3 className="flex items-center gap-1 font-medium">{t('thesis.deviceMetrics.title')}</h3>
              {liveRun ? (
                <p className="text-muted-foreground">{t('thesis.deviceMetrics.afterRun')}</p>
              ) : metrics ? (
                <div className="grid grid-cols-2 gap-1.5">
                  <Stat label={t('thesis.deviceMetrics.readersInRange')}>{metrics.readers_in_range}</Stat>
                  <Stat label={t('thesis.deviceMetrics.cbraFailures')}>
                    {metrics.cbra_failures} / {metrics.attempts}
                  </Stat>
                  <Stat label={t('thesis.deviceMetrics.readerChanges')}>{metrics.reader_changes}</Stat>
                  <Stat label={t('thesis.deviceMetrics.failToPage')}>
                    {metrics.fail_to_page_count > 0
                      ? `${metrics.fail_to_page_count} · ⌀ ${(1e3 * (metrics.fail_to_page_mean_s ?? 0)).toFixed(0)} ms · max ${(1e3 * (metrics.fail_to_page_max_s ?? 0)).toFixed(0)} ms`
                      : '—'}
                  </Stat>
                  {metrics.drop_cause > 0 ? (
                    <Stat label={t('thesis.deviceMetrics.dropCause')}>
                      <span className="text-red-500">{t(`thesis.deviceMetrics.drop.${DROP_CAUSES[metrics.drop_cause] ?? 'stopped'}`)}</span>
                    </Stat>
                  ) : null}
                </div>
              ) : metricsQuery.isLoading ? (
                <p className="text-muted-foreground">{t('thesis.timeline.loading')}</p>
              ) : (
                <p className="text-muted-foreground">{t('thesis.deviceMetrics.none')}</p>
              )}
              <p className="text-[11px] text-muted-foreground">{t('thesis.deviceMetrics.hint')}</p>
            </section>
          ) : null}

          {runId != null ? (
            <TimeFreqSection title={t('thesis.tf.deviceTitle', { id: deviceId })}>
              {(wide) => (
                <DeviceTimeline runId={runId} deviceId={deviceId} live={liveRun} wide={wide} energyJ={energyJ} nowS={nowS} />
              )}
            </TimeFreqSection>
          ) : null}

          <section className="grid gap-1.5">
            <h3 className="font-medium">{t('thesis.inspector.radio')}</h3>
            <p className={reachable.length === 0 ? 'text-red-500' : 'text-muted-foreground'}>
              {reachable.length === 0
                ? t('thesis.inspector.reachableNone')
                : t('thesis.inspector.reachableBy', {
                    count: reachable.length,
                    ids: reachable.map((r) => `#${r.id}`).join(', '),
                  })}
            </p>
            <table className="w-full">
              <thead className="text-left text-muted-foreground">
                <tr>
                  <th className="py-0.5 font-normal">{t('thesis.inspector.reader')}</th>
                  <th className="py-0.5 font-normal">{t('thesis.inspector.distance')}</th>
                  <th className="py-0.5 font-normal">{t('thesis.inspector.pin')}</th>
                  <th className="py-0.5 font-normal">{t('thesis.inspector.coverage')}</th>
                </tr>
              </thead>
              <tbody className="tabular-nums">
                {readers.map((r) => (
                  <tr key={String(r.id)} className={`border-t ${r.inside && !r.disabled ? '' : 'text-muted-foreground'}`}>
                    <td className="py-0.5">
                      #{r.id}
                      {r.disabled ? <span className="ml-1 text-[10px]">({t('thesis.inspector.skipped')})</span> : null}
                    </td>
                    <td className="py-0.5">{r.d2.toFixed(1)} m</td>
                    <td className="py-0.5">{r.pinDbm.toFixed(1)} dBm</td>
                    <td className="py-0.5">
                      {r.inside ? '✓' : '✗'} {Number.isFinite(r.coverage) ? `${r.coverage.toFixed(1)} m` : ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <details>
              <summary className="cursor-pointer text-muted-foreground">{t('thesis.inspector.params')}</summary>
              <dl className="mt-1 grid grid-cols-2 gap-x-3 gap-y-0.5">
                {Object.entries(placement.params).map(([k, v]) => (
                  <div key={k} className="contents">
                    <dt className="truncate text-muted-foreground">{k}</dt>
                    <dd className="truncate font-mono">{String(v)}</dd>
                  </div>
                ))}
              </dl>
            </details>
          </section>

          {runId != null && timeline ? (
            <section className="grid gap-1.5">
              <h3 className="font-medium">{t('thesis.inspector.history', { count: timeline.events.length })}</h3>
              <HistoryPlot timeline={timeline} />
              <table className="w-full">
                <thead className="sticky top-0 bg-card text-left text-muted-foreground">
                  <tr>
                    <th className="py-0.5 font-normal">{t('thesis.timeline.col.t')}</th>
                    <th className="py-0.5 font-normal">{t('thesis.timeline.col.event')}</th>
                    <th className="py-0.5 font-normal">{t('thesis.timeline.col.reader')}</th>
                    <th className="py-0.5 font-normal">{t('thesis.timeline.col.cause')}</th>
                    <th className="py-0.5 font-normal">µJ</th>
                  </tr>
                </thead>
                <tbody>
                  {timeline.events
                    .slice(-MAX_TABLE_ROWS)
                    .reverse()
                    .map((e) => (
                      <tr key={e.id} className="border-t">
                        <td className="py-0.5 tabular-nums">{e.t_s.toFixed(4)}</td>
                        <td className="py-0.5 font-mono text-[11px]">{t(`thesis.live.event.${e.event_type}`, e.event_type)}</td>
                        <td className="py-0.5 tabular-nums">{e.reader_id ?? '—'}</td>
                        <td className="py-0.5">{e.cause ?? ''}</td>
                        <td className="py-0.5 tabular-nums">{e.energy_j != null ? (e.energy_j * 1e6).toFixed(2) : ''}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </section>
          ) : runId != null ? (
            <p className="text-muted-foreground">{t('thesis.timeline.loading')}</p>
          ) : null}
        </div>
      </ScrollArea>
    </aside>
  )
}

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-md bg-muted/50 px-2 py-1">
      <div className="text-[10px] text-muted-foreground">{label}</div>
      <div className="tabular-nums">{children}</div>
    </div>
  )
}

function HistoryPlot({ timeline }: { timeline: Timeline }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const rowOf = (type: string) => {
    const i = EVENT_ORDER.indexOf(type as (typeof EVENT_ORDER)[number])
    return i === -1 ? null : i
  }
  const ev = timeline.events.filter((e) => rowOf(e.event_type) != null)
  return (
    <Plot
      data={[
        {
          x: ev.map((e) => e.t_s),
          y: ev.map((e) => rowOf(e.event_type)),
          mode: 'markers',
          type: 'scattergl',
          marker: { size: 6, color: '#0072bd' },
          hovertext: ev.map((e) => `${e.event_type}${e.cause ? ` · ${e.cause}` : ''}${e.reader_id != null ? ` · R${e.reader_id}` : ''}`),
          hovertemplate: 't=%{x:.4f}s<br>%{hovertext}<extra></extra>',
          name: t('thesis.inspector.events'),
        },
        {
          x: timeline.energy_series.map(([x]) => x),
          y: timeline.energy_series.map(([, y]) => y * 1e6),
          mode: 'lines',
          type: 'scattergl',
          line: { color: '#77ac30', width: 1.5 },
          yaxis: 'y2',
          name: 'µJ',
        },
      ]}
      layout={{
        ...baseLayout(plot, { margin: { t: 8, r: 44, b: 32, l: 96 }, height: 260, showlegend: false, hovermode: 'closest' }),
        xaxis: axis(plot, t('thesis.timeline.axis.t')),
        yaxis: {
          ...axis(plot, ''),
          tickmode: 'array',
          tickvals: EVENT_ORDER.map((_, i) => i),
          ticktext: EVENT_ORDER.map((e) => t(`thesis.live.event.${e}`, e)),
          range: [-0.5, EVENT_ORDER.length - 0.5],
        },
        yaxis2: { ...axis(plot, 'µJ'), overlaying: 'y', side: 'right', rangemode: 'tozero' },
      }}
      config={PLOT_CONFIG}
      style={{ width: '100%' }}
      useResizeHandler
    />
  )
}