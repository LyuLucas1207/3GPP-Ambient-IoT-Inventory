import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import type { LiveDevices } from '@/hooks/useLiveRun'
import { FLAGGED_CODES } from '@/lib/thesisRunStates'
import type { RunCounters, RunRound } from '@/types/thesis'
import { inScope, PERCENTILES, scopedCurve, STAGES, SUBTYPES, sum, timeToPercent, type Scope } from './data'

/** KPI cards + per-type / per-stage / per-reader tables for the current scope (and replay time). */
export function MetricsPanel({
  rounds,
  scope,
  curve,
  all,
  counters,
  replaying,
  devices,
}: {
  rounds: RunRound[]
  scope: Scope
  curve: ReturnType<typeof scopedCurve>
  all: boolean
  counters: Partial<RunCounters>
  replaying: boolean
  devices: LiveDevices | null
}) {
  const { t } = useTranslation()
  const m = useMemo(() => {
    const slots = sum(rounds.map((r) => r.slot_count))
    const successes = sum(rounds.map((r) => r.success_count))
    const deaths: Record<string, Record<string, number>> = {}
    for (const st of STAGES) deaths[st] = { '1': 0, '2a': 0, '2b': 0 }
    const energy: Record<string, number> = { '1': 0, '2a': 0, '2b': 0 }
    const overhead: Record<string, number> = { paging: 0, m1: 0, ebi: 0, m2: 0, m3: 0 }
    const perReader = new Map<number, { rounds: number; identified: number; success: number; slots: number }>()
    for (const r of rounds) {
      for (const st of STAGES) for (const s of SUBTYPES) deaths[st][s] += r.deaths?.[st]?.[s] ?? 0
      for (const s of SUBTYPES) energy[s] += r.energy_j?.[s] ?? 0
      for (const k of Object.keys(overhead)) overhead[k] += r.timing?.[k as keyof typeof r.timing] ?? 0
      const pr = perReader.get(r.reader_id) ?? { rounds: 0, identified: 0, success: 0, slots: 0 }
      pr.rounds++
      pr.identified += r.served ?? 0
      pr.success += r.success_count
      pr.slots += r.slot_count
      perReader.set(r.reader_id, pr)
    }
    // Devices in scope that are red on the map (never identified, run over).
    let unidentified = 0
    if (devices) {
      for (let i = 0; i < devices.codes.length; i++) {
        if (inScope(scope, i) && FLAGGED_CODES.has(devices.codes[i])) unidentified++
      }
    }
    return {
      efficiency: slots > 0 ? successes / slots : 0,
      deaths,
      energy,
      overhead,
      unidentified,
      perReader: [...perReader.entries()].sort((a, b) => a[0] - b[0]),
    }
  }, [rounds, scope, devices])

  const n = scope.size || (counters.total ?? 0)
  const identified = curve.total[curve.total.length - 1] ?? 0
  const fmtT = (v: number | null) => (v == null ? '—' : `${v.toFixed(2)} s`)
  const kpi: [string, string][] = [
    ...PERCENTILES.map((p): [string, string] => [`T${p}`, fmtT(timeToPercent(curve.t, curve.total, n, p))]),
    [t('thesis.live.identified'), `${identified}/${n}`],
    [t('thesis.charts.unidentified'), String(m.unidentified)],
    [t('thesis.charts.efficiency'), `${(100 * m.efficiency).toFixed(1)}%`],
    [t('thesis.live.rounds'), String(rounds.length)],
    [t('thesis.live.depletions'), String(STAGES.reduce((acc, st) => acc + SUBTYPES.reduce((a, s) => a + m.deaths[st][s], 0), 0))],
  ]
  if (all && !replaying) kpi.push([t('thesis.live.unreachable'), String(counters.unreachable ?? 0)])

  return (
    <div className="grid h-full content-start gap-3 overflow-auto text-xs">
      <div className="grid grid-cols-[repeat(auto-fill,minmax(110px,1fr))] gap-1.5">
        {kpi.map(([label, value]) => (
          <div key={label} className="rounded-md bg-muted/50 px-2 py-1">
            <div className="text-[10px] text-muted-foreground">{label}</div>
            <div className="font-medium tabular-nums">{value}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <Table
          title={t('thesis.charts.perType')}
          head={[t('thesis.charts.type'), t('thesis.charts.devices'), t('thesis.live.identified'), 'T50', 'T99', t('thesis.charts.energySpentShort')]}
          rows={SUBTYPES.map((s) => {
            const size = scope.subtypeSize[s]
            const ys = curve.sub[s]
            return [
              t(`thesis.kind.device${s}`),
              size,
              ys[ys.length - 1] ?? 0,
              fmtT(timeToPercent(curve.t, ys, size, 50)),
              fmtT(timeToPercent(curve.t, ys, size, 99)),
              `${(m.energy[s] * 1e6).toFixed(2)} µJ`,
            ]
          })}
        />
        <Table
          title={t('thesis.charts.deathsByStage')}
          head={[t('thesis.charts.stageCol'), ...SUBTYPES.map((s) => t(`thesis.kind.device${s}`)), t('thesis.charts.all')]}
          rows={STAGES.map((st) => [
            t(`thesis.charts.stage.${st}`),
            ...SUBTYPES.map((s) => m.deaths[st][s]),
            SUBTYPES.reduce((acc, s) => acc + m.deaths[st][s], 0),
          ])}
        />
        <Table
          title={t('thesis.charts.overhead')}
          head={[t('thesis.charts.stageCol'), t('thesis.charts.totalTime'), '%']}
          rows={(() => {
            const total = Object.values(m.overhead).reduce((a, b) => a + b, 0) || 1
            return Object.entries(m.overhead).map(([k, v]) => [t(`thesis.charts.stage.${k}`), `${v.toFixed(3)} s`, `${((100 * v) / total).toFixed(1)}`])
          })()}
        />
        <Table
          title={t('thesis.charts.perReader')}
          head={[t('thesis.inspector.reader'), t('thesis.live.rounds'), t('thesis.live.identified'), t('thesis.charts.efficiency')]}
          rows={m.perReader.map(([id, r]) => [`#${id}`, r.rounds, r.identified, `${r.slots ? ((100 * r.success) / r.slots).toFixed(1) : '0.0'}%`])}
        />
      </div>
    </div>
  )
}

function Table({ title, head, rows }: { title: string; head: string[]; rows: (string | number)[][] }) {
  return (
    <div>
      <h4 className="mb-1 font-medium">{title}</h4>
      <table className="w-full tabular-nums">
        <thead className="text-left text-muted-foreground">
          <tr>
            {head.map((h) => (
              <th key={h} className="py-0.5 pr-2 font-normal">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t">
              {row.map((cell, j) => (
                <td key={j} className="py-0.5 pr-2">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
