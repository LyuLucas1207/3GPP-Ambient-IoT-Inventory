import { useEffect, useRef, useState } from 'react'
import type { DeviceMap, Identifications } from '@/api/thesisRuns'
import type { CbraInspectRound } from '@/types/aperiodicSimulation'
import type { RoundSlots, RunRound } from '@/types/thesis'

export const SUBTYPES = ['1', '2a', '2b'] as const
export const SUBTYPE_COLOR: Record<string, string> = { '1': '#1d4ed8', '2a': '#0f766e', '2b': '#c2410c' }
export const STAGES = ['paging', 'm1', 'ebi', 'm2', 'm3'] as const
export const PERCENTILES = [50, 90, 95, 99] as const

/** Re-render charts at most once per `ms` while a run streams at 10 Hz. */
export function useThrottled<T>(value: T, ms: number): T {
  const [shown, setShown] = useState(value)
  const last = useRef(0)
  useEffect(() => {
    const wait = Math.max(0, last.current + ms - Date.now())
    const h = window.setTimeout(() => {
      last.current = Date.now()
      setShown(value)
    }, wait)
    return () => window.clearTimeout(h)
  }, [value, ms])
  return shown
}

export function byEndTime(rounds: RunRound[]): RunRound[] {
  return [...rounds].sort((a, b) => a.t_end_s - b.t_end_s || a.id - b.id)
}

/** Cumulative identifications over simulated time, overall and per subtype. */
export function identificationCurve(rounds: RunRound[]) {
  const sorted = byEndTime(rounds)
  const t: number[] = [0]
  const total: number[] = [0]
  const sub: Record<string, number[]> = { '1': [0], '2a': [0], '2b': [0] }
  for (const r of sorted) {
    if (r.n_done_total == null) continue
    t.push(r.t_end_s)
    total.push(r.n_done_total)
    for (const s of SUBTYPES) sub[s].push(r.identified_by_subtype?.[s] ?? sub[s][sub[s].length - 1])
  }
  // n_done_total is a global running count; across readers it is monotone in t_end.
  for (let i = 1; i < total.length; i++) total[i] = Math.max(total[i], total[i - 1])
  for (const s of SUBTYPES) for (let i = 1; i < sub[s].length; i++) sub[s][i] = Math.max(sub[s][i], sub[s][i - 1])
  return { t, total, sub }
}

/** First time the curve reaches pct % of `n` (null when not reached yet). */
export function timeToPercent(t: number[], y: number[], n: number, pct: number): number | null {
  if (n <= 0) return null
  const target = Math.ceil((pct / 100) * n)
  for (let i = 0; i < y.length; i++) if (y[i] >= target) return t[i]
  return null
}

export function sum(values: (number | null | undefined)[]): number {
  let s = 0
  for (const v of values) s += v ?? 0
  return s
}

/** Adapt one thesis round + its slot payload to the aperiodic time-frequency map. */
export function toInspectRound(r: RunRound, slots: RoundSlots['slots'], periodic: boolean): CbraInspectRound | null {
  if (!slots) return null
  const F = Math.max(1, slots.f)
  const K = slots.res.length
  const L = Math.ceil(K / F)
  const physical: number[] = []
  const observed: number[] = []
  const occupancy: number[] = []
  for (let ao = 0; ao < L * F; ao++) {
    const res = ao < K ? slots.res[ao] : 0
    occupancy.push(ao < K ? slots.occ[ao] : 0)
    // backend codes: 0 idle, 1 single, 2 captured, 3 collision, 4 singleton missed by the detector
    physical.push(res === 4 ? 1 : res)
    observed.push(res === 0 ? 0 : res === 1 || res === 2 ? 1 : 2)
  }
  const tm = r.timing ?? { paging: 0, m1: 0, ebi: 0, m2: 0, m3: 0 }
  const kAlloc = r.s_budget ?? 0
  const served = r.served ?? 0
  return {
    round: r.round_index,
    t_start_s: r.t_start_s,
    t_end_s: r.t_end_s,
    L,
    F,
    occupancy,
    physical,
    observed,
    k_decoded: r.success_count,
    k_alloc: kAlloc,
    k_served: Math.min(kAlloc, r.success_count),
    msg3_slots: Math.ceil(kAlloc / F),
    components_s: { paging_s: tm.paging, msg1_s: tm.m1, ei_s: tm.ebi, msg2_s: tm.m2, msg3_s: tm.m3 },
    n_paged: r.on_at_page ?? 0,
    n_participants: r.joiners ?? 0,
    n_rejected: (r.candidates ?? 0) - (r.joiners ?? 0),
    identified: served,
    periodic,
  }
}

// ------------------------------------------------------------------ chart scope


/** What every chart counts: all devices, or the devices inside one reader's coverage. */
export type Scope = {
  reader: number | 'all'
  /** members[i] = 1 when device index i is in scope; null = every device */
  members: Uint8Array | null
  size: number
  subtypeSize: Record<string, number>
}

export function buildScope(map: DeviceMap | undefined, reader: number | 'all'): Scope {
  const subtypeSize: Record<string, number> = { '1': 0, '2a': 0, '2b': 0 }
  if (!map) return { reader, members: null, size: 0, subtypeSize }
  const n = map.subtypes.length
  let members: Uint8Array | null = null
  if (reader !== 'all') {
    members = new Uint8Array(n)
    for (const i of map.coverage[String(reader)] ?? []) members[i] = 1
  }
  let size = 0
  for (let i = 0; i < n; i++) {
    if (members && !members[i]) continue
    size++
    const s = map.subtypes[i]
    if (s in subtypeSize) subtypeSize[s]++
  }
  return { reader, members, size, subtypeSize }
}

export function inScope(scope: Scope, deviceIndex: number): boolean {
  return scope.members == null || scope.members[deviceIndex] === 1
}

/** Cumulative identifications of in-scope devices (by any reader), overall and per subtype. */
export function scopedCurve(
  ident: Identifications | undefined,
  map: DeviceMap | undefined,
  scope: Scope,
  until: number | null = null,
) {
  const t: number[] = [0]
  const total: number[] = [0]
  const sub: Record<string, number[]> = { '1': [0], '2a': [0], '2b': [0] }
  if (!ident || !map) return { t, total, sub }
  const count: Record<string, number> = { '1': 0, '2a': 0, '2b': 0 }
  let all = 0
  for (let k = 0; k < ident.t.length; k++) {
    if (until != null && ident.t[k] > until) break // replay: only what had happened by then
    const i = ident.device[k]
    if (!inScope(scope, i)) continue
    all++
    const s = map.subtypes[i]
    if (s in count) count[s]++
    t.push(ident.t[k])
    total.push(all)
    for (const key of SUBTYPES) sub[key].push(count[key])
  }
  return { t, total, sub }
}

export type RoundBin = {
  t0: number
  t1: number
  rounds: number
  success: number
  collision: number
  empty: number
  slots: number
  timing: Record<string, number>
}

/** Sum every reader's rounds into equal time bins ("all readers" view of per-round charts). */
export function binRounds(rounds: RunRound[], bins = 120): RoundBin[] {
  if (rounds.length === 0) return []
  let tMax = 0
  for (const r of rounds) tMax = Math.max(tMax, r.t_start_s)
  const width = Math.max(tMax / bins, 1e-6)
  const out: RoundBin[] = Array.from({ length: bins + 1 }, (_, i) => ({
    t0: i * width,
    t1: (i + 1) * width,
    rounds: 0,
    success: 0,
    collision: 0,
    empty: 0,
    slots: 0,
    timing: { paging: 0, m1: 0, ebi: 0, m2: 0, m3: 0 },
  }))
  for (const r of rounds) {
    const b = out[Math.min(bins, Math.floor(r.t_start_s / width))]
    b.rounds++
    b.success += r.success_count
    b.collision += r.collision_count
    b.empty += r.empty_count
    b.slots += r.slot_count
    for (const k of STAGES) b.timing[k] += r.timing?.[k] ?? 0
  }
  return out.filter((b) => b.rounds > 0)
}
