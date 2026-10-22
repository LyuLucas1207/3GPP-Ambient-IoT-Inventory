import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { axis, baseLayout, PLOT_CONFIG } from '@/components/aperiodic/plotLayout'
import type { LiveDevices } from '@/hooks/useLiveRun'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/lib/Plot'
import { FIXED_DEV_DB, H_AIOT, H_BS, L_OBJ_DB, plNlos } from '@/lib/thesisPhysics'
import type { DeviceMap } from '@/api/thesisRuns'
import type { Placement, RunRound, Scene } from '@/types/thesis'
import { byEndTime, inScope, SUBTYPE_COLOR, SUBTYPES, type Scope } from './data'

/** Left: energy histogram of the in-scope devices (at the live / replay time).
 *  Right: cumulative protocol energy spent per subtype by the in-scope rounds. */
export function EnergyChart({
  map,
  scope,
  devices,
  rounds,
}: {
  map: DeviceMap | undefined
  scope: Scope
  devices: LiveDevices | null
  rounds: RunRound[]
}) {
  const { t } = useTranslation()
  const plot = usePlotTheme()

  const hist = useMemo(() => {
    const out: Record<string, number[]> = { '1': [], '2a': [], '2b': [] }
    if (!devices || !map) return out
    // devices and the device map share the run's scene-snapshot device order.
    for (let i = 0; i < devices.energy.length; i++) {
      if (!inScope(scope, i)) continue
      const s = map.subtypes[i]
      if (s in out) out[s].push(devices.energy[i] * 1e6)
    }
    return out
  }, [devices, map, scope])

  const spent = useMemo(() => {
    const sorted = byEndTime(rounds)
    const t: number[] = [0]
    const acc: Record<string, number[]> = { '1': [0], '2a': [0], '2b': [0] }
    for (const r of sorted) {
      t.push(r.t_end_s)
      for (const s of SUBTYPES) acc[s].push(acc[s][acc[s].length - 1] + (r.energy_j?.[s] ?? 0) * 1e6)
    }
    return { t, acc }
  }, [rounds])

  return (
    <div className="grid h-full min-h-[180px] grid-cols-2 gap-2">
      <Plot
        data={SUBTYPES.map((s) => ({
          x: hist[s],
          type: 'histogram' as const,
          name: t(`thesis.kind.device${s}`),
          marker: { color: SUBTYPE_COLOR[s] },
          opacity: 0.7,
          nbinsx: 40,
        }))}
        layout={{
          ...baseLayout(plot, { barmode: 'overlay', hovermode: 'closest' }),
          xaxis: axis(plot, t('thesis.charts.energyNow')),
          yaxis: axis(plot, t('thesis.charts.devices')),
        }}
        config={PLOT_CONFIG}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
      />
      <Plot
        data={SUBTYPES.map((s) => ({
          x: spent.t,
          y: spent.acc[s],
          type: 'scatter' as const,
          mode: 'lines' as const,
          line: { color: SUBTYPE_COLOR[s] },
          name: t(`thesis.kind.device${s}`),
        }))}
        layout={{
          ...baseLayout(plot),
          xaxis: axis(plot, t('thesis.charts.time')),
          yaxis: axis(plot, t('thesis.charts.energySpent')),
        }}
        config={PLOT_CONFIG}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
      />
    </div>
  )
}

/** CDF of received power (paper Fig. 4 style): all readers = strongest Pin from any
 *  reader for every device; one reader = that reader's Pin at the devices it covers. */
export function PinCdfChart({ scene, map, scope }: { scene: Scene; map: DeviceMap | undefined; scope: Scope }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const cdf = useMemo(() => {
    const byId = new Map<number, Placement>()
    for (const p of scene.placements) if (typeof p.id === 'number') byId.set(p.id, p)
    const readers = scene.placements.filter((p) => p.kind === 'radar' && (scope.reader === 'all' || p.id === scope.reader))
    const bySub: Record<string, number[]> = { '1': [], '2a': [], '2b': [] }
    const devices: Placement[] = map
      ? map.device_ids.flatMap((id, i) => (inScope(scope, i) && byId.get(id) ? [byId.get(id)!] : []))
      : scene.placements.filter((p) => p.kind === 'device')
    for (const d of devices) {
      if (!bySub[d.subtype ?? '']) continue
      let best = -Infinity
      for (const r of readers) {
        const tx = num(r.params.tx_power_dbm, 33)
        const g = num(r.params.antenna_gain_dbi, 6)
        const extra = num(r.params.extra_attenuation_db, 0)
        const fc = num(r.params.carrier_ghz, 0.9)
        const d3 = Math.hypot(r.x_m - d.x_m, r.y_m - d.y_m, H_BS - H_AIOT)
        best = Math.max(best, tx + g - plNlos(d3, fc) - FIXED_DEV_DB - L_OBJ_DB - extra)
      }
      if (Number.isFinite(best)) bySub[d.subtype as string].push(best)
    }
    return SUBTYPES.map((s) => {
      const xs = [...bySub[s]].sort((a, b) => a - b)
      return { s, xs, ys: xs.map((_, i) => (i + 1) / xs.length) }
    })
  }, [scene, map, scope])
  return (
    <div className="h-full min-h-[180px] w-full">
      <Plot
        data={cdf.map(({ s, xs, ys }) => ({
          x: xs,
          y: ys,
          type: 'scatter' as const,
          mode: 'lines' as const,
          line: { shape: 'hv' as const, color: SUBTYPE_COLOR[s] },
          name: t(`thesis.kind.device${s}`),
        }))}
        layout={{
          ...baseLayout(plot),
          xaxis: axis(plot, t('thesis.charts.pin')),
          yaxis: axis(plot, t('thesis.charts.cdf'), { range: [0, 1.02] }),
        }}
        config={PLOT_CONFIG}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
      />
    </div>
  )
}

function num(value: unknown, fallback: number): number {
  const n = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(n) ? n : fallback
}
