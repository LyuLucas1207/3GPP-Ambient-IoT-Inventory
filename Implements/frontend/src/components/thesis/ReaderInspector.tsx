import { useQuery } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchDeviceMap, fetchIdentifications } from '@/api/thesisRuns'
import { axis, baseLayout, MATLAB, PLOT_CONFIG } from '@/components/aperiodic/plotLayout'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { LiveDevices } from '@/hooks/useLiveRun'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/lib/Plot'
import { thesisKeys } from '@/lib/thesisQueryKeys'
import { FLAGGED_CODES, RUN_STATE_LABELS } from '@/lib/thesisRunStates'
import type { Placement, RunRound, RunStatus } from '@/types/thesis'

const SUBTYPES = ['1', '2a', '2b'] as const
const STAGES = ['paging', 'm1', 'ebi', 'm2', 'm3'] as const
const IDENTIFIED = RUN_STATE_LABELS.indexOf('identified')

/**
 * Right-hand drawer for one reader of the selected run: what it covers, how
 * many devices it identified itself (vs. other readers inside its coverage),
 * its slot statistics, and its cumulative identifications over time.
 * Device map + identifications come from the same TanStack queries as the charts.
 */
export function ReaderInspector({
  reader,
  runId,
  runStatus,
  rounds,
  devices,
  onClose,
}: {
  reader: Placement
  runId: number
  runStatus: RunStatus | null
  rounds: RunRound[]
  devices: LiveDevices | null
  onClose: () => void
}) {
  const { t } = useTranslation()
  const rid = reader.id as number
  const isLive = runStatus === 'running' || runStatus === 'pending'
  const mapQuery = useQuery({ queryKey: thesisKeys.deviceMap(runId), queryFn: () => fetchDeviceMap(runId), staleTime: Infinity })
  const identQuery = useQuery({
    queryKey: thesisKeys.identifications(runId),
    queryFn: () => fetchIdentifications(runId),
    refetchInterval: isLive ? 1000 : false,
    staleTime: isLive ? 0 : Infinity,
  })

  const stats = useMemo(() => {
    const map = mapQuery.data
    const ident = identQuery.data
    const coverage = new Set(map?.coverage[String(rid)] ?? [])
    const covered: Record<string, number> = { '1': 0, '2a': 0, '2b': 0 }
    for (const i of coverage) {
      const s = map?.subtypes[i] ?? ''
      if (s in covered) covered[s]++
    }
    const byMe: Record<string, number> = { '1': 0, '2a': 0, '2b': 0 }
    let byOthersInCoverage = 0
    let identifiedAll = 0
    const curveT: number[] = [0]
    const curveN: number[] = [0]
    if (map && ident) {
      for (let k = 0; k < ident.t.length; k++) {
        identifiedAll++
        const i = ident.device[k]
        if (ident.reader[k] === rid) {
          const s = map.subtypes[i]
          if (s in byMe) byMe[s]++
          curveT.push(ident.t[k])
          curveN.push(curveN[curveN.length - 1] + 1)
        } else if (coverage.has(i)) {
          byOthersInCoverage++
        }
      }
    }
    let pending = 0
    let unidentified = 0
    if (devices) {
      for (const i of coverage) {
        const code = devices.codes[i]
        if (FLAGGED_CODES.has(code)) unidentified++
        else if (code !== IDENTIFIED) pending++
      }
    }
    const mine = rounds.filter((r) => r.reader_id === rid)
    const slots = mine.reduce((a, r) => a + r.slot_count, 0)
    const success = mine.reduce((a, r) => a + r.success_count, 0)
    const collision = mine.reduce((a, r) => a + r.collision_count, 0)
    const empty = mine.reduce((a, r) => a + r.empty_count, 0)
    const busy = mine.reduce((a, r) => a + (r.t_end_s - r.t_start_s), 0)
    let depletions = 0
    for (const r of mine) for (const st of STAGES) for (const s of SUBTYPES) depletions += r.deaths?.[st]?.[s] ?? 0
    const total = (o: Record<string, number>) => SUBTYPES.reduce((a, s) => a + o[s], 0)
    return {
      covered,
      coveredTotal: total(covered),
      byMe,
      byMeTotal: total(byMe),
      byOthersInCoverage,
      identifiedAll,
      pending,
      unidentified,
      rounds: mine.length,
      slots,
      success,
      collision,
      empty,
      efficiency: slots ? success / slots : 0,
      meanK: mine.length ? mine.reduce((a, r) => a + (r.k_estimate ?? 0), 0) / mine.length : 0,
      meanFrameMs: mine.length ? (1e3 * busy) / mine.length : 0,
      depletions,
      curveT,
      curveN,
    }
  }, [mapQuery.data, identQuery.data, devices, rounds, rid])

  const pct = (a: number, b: number) => (b > 0 ? `${((100 * a) / b).toFixed(1)}%` : '—')
  const rf = reader.params

  return (
    <aside className="absolute top-14 right-0 bottom-0 z-20 flex w-[min(440px,calc(100%-16px))] flex-col overflow-hidden rounded-tl-xl border-t border-l bg-card/95 shadow-xl backdrop-blur-md">
      <header className="flex shrink-0 items-center justify-between gap-2 border-b px-3 py-2">
        <div className="min-w-0">
          <h2 className="truncate text-sm font-medium">{t('thesis.readerInspector.title', { id: rid })}</h2>
          <p className="text-[11px] text-muted-foreground tabular-nums">
            ({reader.x_m.toFixed(1)}, {reader.y_m.toFixed(1)}) m · {String(rf.tx_power_dbm ?? 33)} dBm ·{' '}
            {String(rf.antenna_gain_dbi ?? 6)} dBi · {String(rf.carrier_ghz ?? 0.9)} GHz
          </p>
        </div>
        <Button type="button" size="icon-sm" variant="ghost" onClick={onClose} aria-label={t('thesis.inspector.close')}>
          <X />
        </Button>
      </header>
      <ScrollArea className="min-h-0 flex-1">
        <div className="grid gap-3 p-3 text-xs">
          <div className="grid grid-cols-2 gap-1.5">
            <Stat label={t('thesis.readerInspector.identifiedByMe')} strong>
              {stats.byMeTotal} <span className="text-muted-foreground">({pct(stats.byMeTotal, stats.identifiedAll)} {t('thesis.readerInspector.ofAll')})</span>
            </Stat>
            <Stat label={t('thesis.readerInspector.covered')}>{stats.coveredTotal}</Stat>
            <Stat label={t('thesis.readerInspector.byOthers')}>{stats.byOthersInCoverage}</Stat>
            <Stat label={t('thesis.readerInspector.pending')}>{stats.pending}</Stat>
            <Stat label={t('thesis.charts.unidentified')}>
              <span className={stats.unidentified ? 'text-red-500' : ''}>{stats.unidentified}</span>
            </Stat>
            <Stat label={t('thesis.live.depletions')}>{stats.depletions}</Stat>
          </div>

          <section className="grid gap-1">
            <h3 className="font-medium">{t('thesis.readerInspector.perType')}</h3>
            <table className="w-full tabular-nums">
              <thead className="text-left text-muted-foreground">
                <tr>
                  <th className="py-0.5 font-normal">{t('thesis.charts.type')}</th>
                  <th className="py-0.5 font-normal">{t('thesis.readerInspector.covered')}</th>
                  <th className="py-0.5 font-normal">{t('thesis.readerInspector.identifiedByMe')}</th>
                  <th className="py-0.5 font-normal">{t('thesis.readerInspector.share')}</th>
                </tr>
              </thead>
              <tbody>
                {SUBTYPES.map((s) => (
                  <tr key={s} className="border-t">
                    <td className="py-0.5">{t(`thesis.kind.device${s}`)}</td>
                    <td className="py-0.5">{stats.covered[s]}</td>
                    <td className="py-0.5">{stats.byMe[s]}</td>
                    <td className="py-0.5">{pct(stats.byMe[s], stats.covered[s])}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="grid gap-1">
            <h3 className="font-medium">{t('thesis.readerInspector.slots')}</h3>
            <div className="grid grid-cols-3 gap-1.5">
              <Stat label={t('thesis.live.rounds')}>{stats.rounds}</Stat>
              <Stat label={t('thesis.charts.efficiency')}>{(100 * stats.efficiency).toFixed(1)}%</Stat>
              <Stat label={t('thesis.readerInspector.meanK')}>{stats.meanK.toFixed(0)}</Stat>
              <Stat label={t('thesis.analysis.rounds.success')}>{stats.success}</Stat>
              <Stat label={t('thesis.analysis.rounds.collision')}>{stats.collision}</Stat>
              <Stat label={t('thesis.analysis.rounds.empty')}>{stats.empty}</Stat>
              <Stat label={t('thesis.readerInspector.meanFrame')}>{stats.meanFrameMs.toFixed(0)} ms</Stat>
            </div>
          </section>

          <section className="grid gap-1">
            <h3 className="font-medium">{t('thesis.readerInspector.curve')}</h3>
            <ReaderCurve t={stats.curveT} n={stats.curveN} />
          </section>
          <p className="text-[11px] text-muted-foreground">{t('thesis.readerInspector.hint')}</p>
        </div>
      </ScrollArea>
    </aside>
  )
}

function Stat({ label, children, strong = false }: { label: string; children: React.ReactNode; strong?: boolean }) {
  return (
    <div className="rounded-md bg-muted/50 px-2 py-1">
      <div className="text-[10px] text-muted-foreground">{label}</div>
      <div className={`tabular-nums ${strong ? 'text-sm font-semibold' : ''}`}>{children}</div>
    </div>
  )
}

function ReaderCurve({ t: xs, n }: { t: number[]; n: number[] }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  return (
    <Plot
      data={[{ x: xs, y: n, type: 'scatter', mode: 'lines', line: { shape: 'hv', width: 2.2, color: MATLAB.green }, name: '' }]}
      layout={{
        ...baseLayout(plot, { height: 200, showlegend: false, margin: { t: 8, r: 12, b: 32, l: 44 } }),
        xaxis: axis(plot, t('thesis.charts.time')),
        yaxis: axis(plot, t('thesis.charts.devices'), { rangemode: 'tozero' }),
      }}
      config={PLOT_CONFIG}
      style={{ width: '100%' }}
      useResizeHandler
    />
  )
}
