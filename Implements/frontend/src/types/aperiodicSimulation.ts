// Types for the aperiodic-paging paper simulator (/api/aperiodic-simulator).
// Kept separate from the legacy periodic-paging types in ./simulation.ts.

export type HarvestingScenario = 'single_source' | 'multi_source'
export type PagingMode = 'aperiodic' | 'periodic'
export type ControllerName = 'pfsa_pze' | 'dfsa_schoute' | 'cmebe' | 'recurrent_ppo'
export type RuntimeMode = 'interactive' | 'paper_batch'
export type TypeMix = 'mixed' | '1' | '2a' | '2b'

export interface AperiodicSimulateRequest {
  num_devices: number
  seed: number
  harvesting_scenario: HarvestingScenario
  paging_mode: PagingMode
  controller: ControllerName
  ppo_enabled: boolean
  L_mode: 'fixed' | 'adaptive'
  L_fixed: number
  L_initial: number
  p_initial: number
  N_g: number
  enforce_midround_depletion: boolean
  alpha: number
  F: number
  type_mix: TypeMix
  impairments_enabled: boolean
  capture_ratio_db: number
  missed_detection_rate: number
  false_alarm_rate: number
  runtime_mode: RuntimeMode
  num_episodes: number
  max_time_s: number
  n_trace_samples: number
  snapshot_interval_s: number
}

export interface Stat {
  mean: number
  std: number
  ci95: number
  p05: number
  p50: number
  p95: number
  n: number
}

export type StageKey = 'paging' | 'msg1' | 'EI' | 'msg2' | 'msg3'

export interface TypeMetrics {
  n: number
  identified: number
  mean_completion_s: number | null
  T50: number | null
  T90: number | null
  T95: number | null
  T99: number | null
}

export interface EpisodeMetrics {
  n_tot: number
  n_eff: number
  type_shares: Record<string, number>
  identified: number
  final_ratio: number
  sim_time_s: number
  rounds: number
  T50: number | null
  T90: number | null
  T95: number | null
  T99: number | null
  T_total_s: number | null
  mean_identification_time_s: number | null
  mean_identification_time_partial_s: number | null
  total_ao: number
  ao_idle_obs: number
  ao_collision_obs: number
  ao_success_obs: number
  msg2_allocated: number
  msg1_decoded: number
  msg2_wasted: number
  resource_efficiency: number
  depletion_by_stage: Record<StageKey, number>
  depletion_total: number
  would_deplete_by_stage: Record<StageKey, number>
  interround_depletions: number
  msg1_success_lost_to_depletion: number
  group_populations: Record<string, number> | null
  per_type: Record<string, TypeMetrics>
  energy_ledger_uJ: Record<string, number>
  mean_reward: number
}

export interface RoundRow {
  round: number
  t_start_s: number
  t_end_s: number
  L: number
  p: number
  group?: number | null
  S1?: number
  S2a?: number
  S2b?: number
  S?: number
  idle: number
  collision: number
  success?: number
  C2: number
  n_paged?: number
  n_participants: number
  n_rejected?: number
  k_decoded: number
  k_alloc: number
  k_served?: number
  msg2_wasted?: number
  reward: number
  resource_efficiency?: number
  n_done: number
  depleted?: number
  m?: number
  q?: number
  n_hat?: number
  backlog_hat?: number
}

export interface CbraInspectRound {
  round: number
  t_start_s?: number
  t_end_s?: number
  L: number
  F: number
  occupancy: number[]
  physical: number[] // 0 idle, 1 single, 2 captured, 3 collision
  observed: number[] // 0 idle, 1 success, 2 collision
  k_decoded: number
  k_alloc: number
  k_served: number
  msg3_slots: number
  components_s: Record<string, number>
  n_paged: number
  n_participants: number
  n_rejected: number
  identified: number
  periodic: boolean
}

export interface DeviceSample {
  id: number
  x: number
  y: number
  type: '1' | '2a' | '2b'
  p_harv_uW: number
  completion_s: number | null
  group: number | null
  traced: boolean
}

export interface Snapshot {
  time_s: number
  state: number[]
  energy_uJ: number[]
  n_done: number
}

export interface CheckpointMeta {
  path: string
  training_steps: number
  architecture: string
  trained_scenario: string
  alpha: number
  sha256: string
  seed: number
  [key: string]: unknown
}

export interface PopulationInfo {
  n_tot: number
  n_eff: number
  type_counts: Record<string, number>
  type_shares: Record<string, number>
  harvest_below_sleep: { share_of_n_eff: number; type2_share_of_below: number; count: number }
  p_harv_uW_quantiles: number[]
}

export interface AperiodicSimulationResult {
  run_id: string
  runtime_mode: RuntimeMode
  controller: ControllerName
  checkpoint: CheckpointMeta | null
  config: Record<string, unknown>
  population?: PopulationInfo
  metrics: EpisodeMetrics
  aggregate?: Record<string, Stat | number | Record<string, number> | null>
  episodes?: number
  seeds?: number[]
  curve: { times: number[]; ratio: number[]; p05?: number[]; p95?: number[] }
  rounds: RoundRow[]
  cbra_inspect?: CbraInspectRound[]
  devices?: DeviceSample[]
  snapshots?: Snapshot[]
  state_codes?: string[]
  traced_device_ids?: number[]
  warnings: string[]
}

export interface TraceSegment {
  t0: number
  t1: number
  state: string
  stage: string | null
  e0_uJ?: number
  e1_uJ?: number
  duty_cycle_compressed?: boolean
}

export interface AperiodicDeviceTrace {
  device_id: number
  type: string
  p_harv_uW: number
  E_up_uJ: number
  E_low_uJ: number
  group: number | null
  completion_s: number | null
  segments: TraceSegment[]
}

export interface PpoStatus {
  available: boolean
  reason?: string
  checkpoint?: string
  training_steps?: number
  paper_training_steps?: number
  fully_trained?: boolean
  architecture?: string
  trained_scenario?: string
  alpha?: number
  sha256?: string
  seed?: number
  created_at?: string
  alphas: number[]
  train_command: string
  [key: string]: unknown
}

export interface DeviceTypeInfo {
  name: string
  rx_sensitivity_dbm: number
  P_tx_uW: number
  P_rx_uW: number
  P_monitor_uW: number
  monitor_receiver: string
  E_up_uJ: number
  E_low_uJ: number
  uplink: string
}

export interface AperiodicPaperConfig {
  paper: { title: string; authors: string; pdf: string }
  system: Record<string, number>
  device_types: DeviceTypeInfo[]
  assumptions: Record<string, string | number | boolean>
  timing_ms: Record<string, number>
  lmax: { per_type: Record<string, { Lmax: number; E_base_uJ: number; E_scale_uJ: number }>; Lmax: number }
  layout: { factory_m: [number, number]; bs_xy: [number, number][]; reader_xy: [number, number]; reader_bs_index: number }
}

export type ReproTarget = 'figure4' | 'figure5' | 'figure6' | 'figure7' | 'figure8' | 'tables'

export interface ReproduceRequest {
  episodes: number
  base_seed: number
  use_cached: boolean
  panels?: string[] | null
}

export interface JobStatus {
  job_id?: string
  target: string
  status: 'queued' | 'running' | 'done' | 'error'
  progress?: string[]
  error?: string | null
  result?: ReproResult
}

// Reproduction payloads are figure-specific; the UI reads them defensively.
export type ReproResult = Record<string, unknown> & {
  figure?: string
  source?: { kind: string; path?: string; episodes?: number }
}
