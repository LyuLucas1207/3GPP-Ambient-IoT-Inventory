// Mirror of Implements/backend/app/thesis_simulator/physics.py so the UI can
// recompute per-device-type ranges live without a network round-trip. The
// backend endpoint stays authoritative.

import type { DerivedRanges, DeviceSubtype } from '@/types/thesis'

export const FC_GHZ = 0.9
export const H_BS = 8.0
export const H_AIOT = 1.5
export const FIXED_DEV_DB = 7.0
export const L_OBJ_DB = 0.9

export const DEVICE_SUBTYPES: readonly DeviceSubtype[] = ['1', '2a', '2b']

export function plNlos(d_m: number, fc_ghz: number = FC_GHZ): number {
  const d = d_m + 1e-3
  const pl_los = 31.84 + 21.5 * Math.log10(d) + 19.0 * Math.log10(fc_ghz)
  const pl_plus = 33.63 + 21.9 * Math.log10(d) + 20.0 * Math.log10(fc_ghz)
  return Math.max(pl_los, pl_plus)
}

export function solveDistanceFromMpl(mpl_db: number, fc_ghz: number = FC_GHZ): number {
  const d_min = 1e-3
  let hi = 1000
  if (plNlos(d_min, fc_ghz) > mpl_db) return d_min
  while (plNlos(hi, fc_ghz) < mpl_db && hi < 1e6) hi *= 2
  let lo = d_min
  for (let i = 0; i < 80; i += 1) {
    const mid = 0.5 * (lo + hi)
    if (Math.abs(plNlos(mid, fc_ghz) - mpl_db) < 1e-6) return mid
    if (plNlos(mid, fc_ghz) < mpl_db) lo = mid
    else hi = mid
  }
  return 0.5 * (lo + hi)
}

export function horizontalFrom3d(d3d: number, h_tx: number, h_rx: number): number {
  const dz = Math.abs(h_tx - h_rx)
  if (d3d <= dz) return 0
  return Math.sqrt(d3d * d3d - dz * dz)
}

export type RfParams = {
  tx_power_dbm?: number
  antenna_gain_dbi?: number
  extra_attenuation_db?: number
  carrier_ghz?: number
}

export function rangeFromSensitivityM(
  rx_sens_dbm: number,
  rf: RfParams = {},
  h_tx: number = H_BS,
  h_rx: number = H_AIOT,
): number {
  const tx = rf.tx_power_dbm ?? 33.0
  const gain = rf.antenna_gain_dbi ?? 6.0
  const extra = rf.extra_attenuation_db ?? 0.0
  const carrier = rf.carrier_ghz ?? FC_GHZ
  const eirp = tx + gain
  const mpl = eirp - L_OBJ_DB - FIXED_DEV_DB - extra - rx_sens_dbm
  if (mpl <= 0) return 0
  const d3d = solveDistanceFromMpl(mpl, carrier)
  return horizontalFrom3d(d3d, h_tx, h_rx)
}

export function deriveReaderRanges(
  rf: RfParams,
  deviceSensitivities: Partial<Record<DeviceSubtype, number>>,
): DerivedRanges {
  const out = { '1': 0, '2a': 0, '2b': 0 } as DerivedRanges
  for (const subtype of DEVICE_SUBTYPES) {
    const sens = deviceSensitivities[subtype]
    if (typeof sens !== 'number') continue
    out[subtype] = rangeFromSensitivityM(sens, rf)
  }
  return out
}
