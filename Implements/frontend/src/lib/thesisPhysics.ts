// Mirror of Implements/backend/app/thesis_simulator/physics.py so the UI can
// recompute per-device-type ranges live without a network round-trip. The
// backend endpoint stays authoritative.

import type { DerivedRanges, DeviceSubtype, Params } from '@/types/thesis'

export const FC_GHZ = 0.9
export const H_BS = 8.0
export const H_AIOT = 1.5
export const FIXED_DEV_DB = 7.0
export const L_OBJ_DB = 0.9
export const CANCEL_DEPTH_DB = 140.0
export const SNR_REQ_DB = 0.5
export const DEFAULT_READER_TX_DBM = 33.0

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

export function readerRequiredLevelDbm(txPowerDbm: number = DEFAULT_READER_TX_DBM): number {
  return txPowerDbm - CANCEL_DEPTH_DB + SNR_REQ_DB
}

function mplToHorizontalM(mplDb: number, carrierGhz: number, h_tx: number, h_rx: number): number {
  if (mplDb <= 0) return 0
  const d3d = solveDistanceFromMpl(mplDb, carrierGhz)
  return horizontalFrom3d(d3d, h_tx, h_rx)
}

export function d2rBackscatterRangeM(
  backscatterLossDb: number,
  backscatterGainDb: number,
  rf: RfParams = {},
  h_tx: number = H_BS,
  h_rx: number = H_AIOT,
): number {
  const tx = rf.tx_power_dbm ?? DEFAULT_READER_TX_DBM
  const extra = rf.extra_attenuation_db ?? 0
  const carrier = rf.carrier_ghz ?? FC_GHZ
  const gbs = -backscatterLossDb + backscatterGainDb
  const pReq = readerRequiredLevelDbm(tx)
  const mpl = 0.5 * (tx + gbs - FIXED_DEV_DB - extra - pReq)
  return mplToHorizontalM(mpl, carrier, h_tx, h_rx)
}

export function d2rActiveRangeM(
  activeTxDbm: number,
  rf: RfParams = {},
  h_tx: number = H_BS,
  h_rx: number = H_AIOT,
): number {
  const tx = rf.tx_power_dbm ?? DEFAULT_READER_TX_DBM
  const extra = rf.extra_attenuation_db ?? 0
  const carrier = rf.carrier_ghz ?? FC_GHZ
  const pReq = readerRequiredLevelDbm(tx)
  const mpl = activeTxDbm - FIXED_DEV_DB - extra - pReq
  return mplToHorizontalM(mpl, carrier, h_tx, h_rx)
}

export function effectiveCoverageM(deviceParams: Params, rf: RfParams = {}, includeD2r: boolean = true): number {
  const rxSens = typeof deviceParams.rx_sensitivity_dbm === 'number' ? deviceParams.rx_sensitivity_dbm : -36
  const r2d = rangeFromSensitivityM(rxSens, rf)
  if (!includeD2r) return r2d
  const uplink = deviceParams.uplink
  let d2r = 0
  if (uplink === 'active') {
    const activeTx = typeof deviceParams.active_tx_power_dbm === 'number' ? deviceParams.active_tx_power_dbm : null
    if (activeTx == null) return 0
    d2r = d2rActiveRangeM(activeTx, rf)
  } else {
    const loss = typeof deviceParams.backscatter_loss_db === 'number' ? deviceParams.backscatter_loss_db : 6
    const gain = typeof deviceParams.backscatter_gain_db === 'number' ? deviceParams.backscatter_gain_db : 0
    d2r = d2rBackscatterRangeM(loss, gain, rf)
  }
  return Math.min(r2d, d2r)
}

export function deriveReaderRanges(
  rf: RfParams,
  deviceDefaults: Partial<Record<DeviceSubtype, Params>>,
  includeD2r: boolean = true,
): DerivedRanges {
  const out = { '1': 0, '2a': 0, '2b': 0 } as DerivedRanges
  for (const subtype of DEVICE_SUBTYPES) {
    const params = deviceDefaults[subtype]
    if (!params) continue
    out[subtype] = effectiveCoverageM(params, rf, includeD2r)
  }
  return out
}
