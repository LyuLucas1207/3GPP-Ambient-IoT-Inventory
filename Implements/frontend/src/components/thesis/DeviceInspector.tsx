import { useQuery } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchTimeline } from '@/api/thesisRuns'
import { axis, baseLayout, PLOT_CONFIG } from '@/components/aperiodic/plotLayout'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { LiveDevices } from '@/hooks/useLiveRun'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/lib/Plot'
import { effectiveCoverageM, FIXED_DEV_DB, H_AIOT, H_BS, L_OBJ_DB, plNlos } from '@/lib/thesisPhysics'
import { thesisKeys } from '@/lib/thesisQueryKeys'
import { RUN_STATE_COLOR, RUN_STATE_LABELS, type RunStateLabel } from '@/lib/thesisRunStates'
import type { Placement, RunStatus, Scene, Timeline } from '@/types/thesis'

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
  'm1_success',
  'budget_drop',
  'ebi_received',
  'm2_rx',
  'm3_tx',
  'identified',
] as const

const TIMELINE_REFRESH_MS = 1000
const MAX_TABLE_ROWS = 400

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
  onClose,
}: {
  scene: Scene
  placement: Placement
  live: LiveDevices | null
  runId: number | null
  runStatus: RunStatus | null
  onClose: () => void
}) {
  const { t } = useTranslation()
  const deviceId = placement.id as number
  const idx = live?.indexById.get(deviceId)
  const code = idx != null && live ? live.codes[idx] : null
  const state: RunStateLabel | null = code != null ? (RUN_STATE_LABELS[code] ?? null) : null
  const energyJ = idx != null && live ? live.energy[idx] : null

  const readers = useMemo(() => {
    const devParams = placement.params
    return scene.placements
      .filter((p) => p.kind === 'radar')
      .map((r) => {
        const rf = {
          tx_power_dbm: num(r.params.tx_power_dbm, 33),
          antenna_gain_dbi: num(r.params.antenna_gain_dbi, 6),
          extra_attenuation_db: num(r.params.extra_attenuation_db, 0),
          carrier_ghz: num(r.params.carrier_ghz, 0.9),
        }
        const d2 = Math.hypot(r.x_m - placement.x_m, r.y_m - placement.y_m)
        const d3 = Math.hypot(d2, H_BS - H_AIOT)
        const pinDbm =
          rf.tx_power_dbm + rf.antenna_gain_dbi - plNlos(d3, rf.carrier_ghz) - FIXED_DEV_DB - L_OBJ_DB - rf.extra_attenuation_db
        const coverage = effectiveCoverageM(devParams, rf, r.params.include_d2r !== false)
        return { id: r.id, d2, pinDbm, coverage, inside: d2 <= coverage }
      })
      .sort((a, b) => a.d2 - b.d2)
  }, [scene, placement])

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

  return (
    // Starts below the map's top-right buttons (layers, right-panel toggle) so it never covers them.
    <aside className="absolute top-14 right-0 bottom-0 z-20 flex w-[min(440px,calc(100%-16px))] flex-col overflow-hidden rounded-tl-xl border-t border-l bg-card/95 shadow-xl backdrop-blur-md">
      <header className="flex shrink-0 items-center justify-between gap-2 border-b px-3 py-2">
        <div className="min-w-0">
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

          <section className="grid gap-1.5">
            <h3 className="font-medium">{t('thesis.inspector.radio')}</h3>
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
                  <tr key={String(r.id)} className={`border-t ${r.inside ? '' : 'text-muted-foreground'}`}>
                    <td className="py-0.5">#{r.id}</td>
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

function num(value: unknown, fallback: number): number {
  const n = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(n) ? n : fallback
}
