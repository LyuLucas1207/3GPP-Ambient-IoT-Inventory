import type { FlowHighlight } from '@/strategyMaps/types'
import type { StepDeviceRound, StepRound } from '@/types/aperiodicSimulation'

// Sub-steps of one CBRA round in the Step process view (paper Fig. 2/3).
export const STEP_PHASES = ['before', 'paging', 'access', 'msg1', 'ei', 'msg2', 'msg3', 'after'] as const
export type StepPhase = (typeof STEP_PHASES)[number]

/** T–F block revealed up to each phase (index into the block order paging, msg1, ei, msg2, msg3). */
export const PHASE_BLOCK: Record<StepPhase, number> = {
  before: -1,
  paging: 0,
  access: 0,
  msg1: 1,
  ei: 2,
  msg2: 3,
  msg3: 4,
  after: 4,
}

export function phaseIndex(p: StepPhase) {
  return STEP_PHASES.indexOf(p)
}

export function stateCounts(states: string[]): Record<string, number> {
  const out: Record<string, number> = {}
  for (const s of states) out[s] = (out[s] ?? 0) + 1
  return out
}

export interface PhaseCounts {
  off: number
  monitor: number
  sync: number
  done: number
  paged: number
  pagedMonitor: number
  pagedWake: number
  pagedResync: number
  pageDepleted: number
  afterPage: number
  rejected: number
  participants: number
  flagged: number
  noFlag: number
  captureLoss: number
  toMsg3: number
  identified: number
  depleted: number
  toOff: number
  toSync: number
  failed: number
}

export function phaseCounts(r: StepRound): PhaseCounts {
  const before = stateCounts(r.devices.map((d) => d.before.state))
  const part = r.devices.filter((d) => d.access === 'transmit')
  const flagged = part.filter((d) => d.msg2_index != null).length
  const midDepleted = part.filter((d) => d.fate === 'depleted').length
  const captureLoss = part.filter((d) => d.fate === 'capture_loss').length
  const failed = part.filter((d) => d.fate && d.fate !== 'success' && d.fate !== 'depleted').length
  const c = r.counts
  return {
    off: before.OFF ?? 0,
    monitor: before.MONITOR ?? 0,
    sync: before.INTERROUND_SYNC_SLEEP ?? 0,
    done: before.DONE ?? 0,
    paged: c.paged,
    pagedMonitor: c.paged_monitor,
    pagedWake: c.paged_sync_wake,
    pagedResync: c.paged_resync,
    pageDepleted: c.page_depleted,
    afterPage: c.participants + c.rejected,
    rejected: c.rejected,
    participants: c.participants,
    flagged,
    noFlag: part.length - flagged,
    captureLoss,
    toMsg3: part.filter((d) => d.fate === 'success').length,
    identified: c.identified,
    depleted: midDepleted + c.page_depleted,
    toOff: c.to_off,
    toSync: c.to_sync,
    failed,
  }
}

/** Which state-machine nodes are active and how many devices take each edge in a phase. */
export function phaseHighlight(p: StepPhase, r: StepRound): FlowHighlight {
  const k = phaseCounts(r)
  const n = (v: number) => `${v} dev`
  switch (p) {
    case 'before':
      return {
        nodes: ['charge', 'monitor', ...(k.sync ? ['sync'] : [])],
        edges: { charge_monitor: `${k.monitor} MONITOR · ${k.off} OFF` },
      }
    case 'paging':
      return {
        nodes: ['page', 'caught', 'monitor', ...(k.pagedWake ? ['sync'] : [])],
        edges: {
          page_caught: n(k.paged),
          monitor_caught: n(k.pagedMonitor),
          ...(k.pagedWake ? { sync_access: n(k.pagedWake) } : {}),
        },
      }
    case 'access':
      return {
        nodes: ['access', 'rejected'],
        edges: { caught_access: n(k.afterPage), access_msg1: n(k.participants), access_rej: n(k.rejected) },
      }
    case 'msg1':
      return { nodes: ['msg1'], edges: { access_msg1: n(k.participants), msg1_ei: n(k.participants) } }
    case 'ei':
      return { nodes: ['ei', 'fail'], edges: { ei_msg2: n(k.flagged), ei_fail: n(k.noFlag) } }
    case 'msg2':
      return { nodes: ['msg2', 'fail'], edges: { msg2_msg3: n(k.toMsg3), msg2_fail: n(k.captureLoss) } }
    case 'msg3':
      return { nodes: ['msg3', 'done'], edges: { msg3_done: n(k.identified) } }
    case 'after':
      return {
        nodes: ['done', r.periodic ? 'sync' : 'charge', ...(k.depleted ? ['depleted'] : [])],
        edges: {
          msg3_done: n(k.identified),
          ...(r.periodic
            ? { fail_sync: n(k.toSync), rej_sync: '' }
            : { fail_off: n(k.toOff), rej_off: '' }),
          ...(k.depleted ? { round_dep: n(k.depleted), dep_off: n(k.depleted) } : {}),
        },
      }
  }
}

/** Device relevant to a phase (row emphasis in the table). */
export function activeInPhase(p: StepPhase, d: StepDeviceRound): boolean {
  switch (p) {
    case 'before':
      return d.before.state === 'MONITOR' || d.before.state === 'INTERROUND_SYNC_SLEEP'
    case 'paging':
      return d.paged_via != null
    case 'access':
      return d.access != null
    case 'msg1':
    case 'ei':
      return d.access === 'transmit'
    case 'msg2':
      return d.msg2_index != null
    case 'msg3':
      return d.fate === 'success'
    case 'after':
      return d.paged_via != null
  }
}

export const FATE_TONE: Record<string, string> = {
  success: 'text-emerald-600 dark:text-emerald-400',
  rejected: 'text-muted-foreground',
  collision: 'text-red-600 dark:text-red-400',
  missed_detection: 'text-amber-600 dark:text-amber-400',
  capture_loss: 'text-fuchsia-600 dark:text-fuchsia-400',
  unserved: 'text-amber-600 dark:text-amber-400',
  depleted: 'text-red-700 dark:text-red-300',
  depleted_paging: 'text-red-700 dark:text-red-300',
}
