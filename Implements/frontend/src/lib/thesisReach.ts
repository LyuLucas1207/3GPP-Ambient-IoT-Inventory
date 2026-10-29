import { effectiveCoverageM, FIXED_DEV_DB, H_AIOT, H_BS, L_OBJ_DB, plNlos } from '@/lib/thesisPhysics'
import type { Placement, RunSummary } from '@/types/thesis'

export type ReaderLink = {
  id: Placement['id']
  x_m: number
  y_m: number
  d2: number
  pinDbm: number
  coverage: number
  /** device lies inside this reader's effective coverage disk */
  inside: boolean
  /** reader skipped by the selected run */
  disabled: boolean
}

/**
 * Per-reader radio facts for one device, nearest first. Mirrors the backend
 * cover mask (inventory/episode.py): a reader's own ``include_d2r`` wins over the
 * run config, and readers the run skipped never inventory anything.
 */
export function readerLinksForDevice(
  placements: Placement[],
  device: Placement,
  run?: Pick<RunSummary, 'include_d2r' | 'disabled_reader_ids'> | null,
): ReaderLink[] {
  const runD2r = run?.include_d2r
  const disabledIds = new Set(run?.disabled_reader_ids ?? [])
  return placements
    .filter((p) => p.kind === 'radar')
    .map((r) => {
      const rf = {
        tx_power_dbm: num(r.params.tx_power_dbm, 33),
        antenna_gain_dbi: num(r.params.antenna_gain_dbi, 6),
        extra_attenuation_db: num(r.params.extra_attenuation_db, 0),
        carrier_ghz: num(r.params.carrier_ghz, 0.9),
      }
      const own = r.params.include_d2r
      const includeD2r = typeof own === 'boolean' ? own : runD2r !== false
      const d2 = Math.hypot(r.x_m - device.x_m, r.y_m - device.y_m)
      const d3 = Math.hypot(d2, H_BS - H_AIOT)
      const pinDbm =
        rf.tx_power_dbm + rf.antenna_gain_dbi - plNlos(d3, rf.carrier_ghz) - FIXED_DEV_DB - L_OBJ_DB - rf.extra_attenuation_db
      const coverage = effectiveCoverageM(device.params, rf, includeD2r)
      return {
        id: r.id,
        x_m: r.x_m,
        y_m: r.y_m,
        d2,
        pinDbm,
        coverage,
        inside: d2 <= coverage,
        disabled: disabledIds.has(Number(r.id)),
      }
    })
    .sort((a, b) => a.d2 - b.d2)
}

function num(value: unknown, fallback: number): number {
  const n = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(n) ? n : fallback
}
