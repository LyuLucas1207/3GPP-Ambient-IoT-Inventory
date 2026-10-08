import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchHealth } from '@/api/http'
import {
  fetchAperiodicPaperConfig,
  fetchJob,
  fetchPpoStatus,
  runAperiodicSimulation,
  startReproduction,
} from '@/api/aperiodicSimulator'
import type {
  AperiodicPaperConfig,
  AperiodicSimulateRequest,
  AperiodicSimulationResult,
  JobStatus,
  PpoStatus,
  ReproTarget,
} from '@/types/aperiodicSimulation'

export const DEFAULT_APERIODIC_REQUEST: AperiodicSimulateRequest = {
  num_devices: 2000,
  seed: 42,
  harvesting_scenario: 'multi_source',
  paging_mode: 'aperiodic',
  controller: 'pfsa_pze',
  ppo_enabled: false,
  L_mode: 'fixed',
  L_fixed: 16,
  L_initial: 1,
  p_initial: 1,
  N_g: 1,
  enforce_midround_depletion: true,
  alpha: 0.5,
  F: 8,
  type_mix: 'mixed',
  impairments_enabled: true,
  capture_ratio_db: 6,
  missed_detection_rate: 0.01,
  false_alarm_rate: 0.001,
  runtime_mode: 'interactive',
  num_episodes: 1,
  max_time_s: 1200,
  n_trace_samples: 12,
  snapshot_interval_s: 1,
}

/** Keep the request consistent with the backend's combination rules (spec section 19). */
export function normalizeRequest(r: AperiodicSimulateRequest): AperiodicSimulateRequest {
  const next = { ...r }
  if (next.ppo_enabled) {
    next.controller = 'recurrent_ppo'
    next.paging_mode = 'aperiodic'
    next.L_mode = 'adaptive'
  } else if (next.controller === 'recurrent_ppo') {
    next.controller = 'pfsa_pze'
  }
  if (next.controller === 'pfsa_pze') next.L_mode = 'fixed'
  if (next.controller === 'dfsa_schoute' || next.controller === 'cmebe') {
    next.L_mode = 'adaptive'
    next.paging_mode = 'aperiodic'
  }
  if (next.paging_mode === 'aperiodic') next.N_g = 1
  if (next.runtime_mode === 'interactive') next.num_episodes = 1
  return next
}

export function useAperiodicSimulation() {
  const [request, setRequestRaw] = useState<AperiodicSimulateRequest>(DEFAULT_APERIODIC_REQUEST)
  const [result, setResult] = useState<AperiodicSimulationResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [backendUp, setBackendUp] = useState<boolean | null>(null)
  const [paper, setPaper] = useState<AperiodicPaperConfig | null>(null)
  const [ppo, setPpo] = useState<PpoStatus | null>(null)
  const [job, setJob] = useState<JobStatus | null>(null)
  const pollRef = useRef<number | null>(null)

  const setRequest = useCallback((next: AperiodicSimulateRequest) => setRequestRaw(normalizeRequest(next)), [])

  useEffect(() => {
    fetchHealth().then(setBackendUp)
    fetchAperiodicPaperConfig().then(setPaper).catch(() => setPaper(null))
    fetchPpoStatus().then(setPpo).catch(() => setPpo(null))
    return () => {
      if (pollRef.current) window.clearTimeout(pollRef.current)
    }
  }, [])

  const run = useCallback(async (override?: Partial<AperiodicSimulateRequest>) => {
    const req = normalizeRequest({ ...request, ...override })
    setRequestRaw(req)
    setBusy(true)
    setError(null)
    try {
      setResult(await runAperiodicSimulation(req))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }, [request])

  const poll = useCallback((jobId: string) => {
    fetchJob(jobId)
      .then((s) => {
        setJob(s)
        if (s.status === 'queued' || s.status === 'running') {
          pollRef.current = window.setTimeout(() => poll(jobId), 1500)
        }
      })
      .catch((e) => setJob({ target: '', status: 'error', error: String(e) }))
  }, [])

  const reproduce = useCallback(
    async (target: ReproTarget, episodes: number, useCached: boolean, panels?: string[]) => {
      if (pollRef.current) window.clearTimeout(pollRef.current)
      setJob({ target, status: 'queued', progress: [] })
      try {
        const s = await startReproduction(target, { episodes, base_seed: request.seed, use_cached: useCached, panels })
        setJob({ ...s, target })
        if (s.job_id && s.status !== 'done') poll(s.job_id)
      } catch (e) {
        setJob({ target, status: 'error', error: e instanceof Error ? e.message : String(e) })
      }
    },
    [poll, request.seed],
  )

  return { request, setRequest, result, busy, error, backendUp, paper, ppo, run, job, reproduce }
}
