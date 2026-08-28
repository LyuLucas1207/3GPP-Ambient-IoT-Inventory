export enum StrategyKey {
  EM = 'em',
  DCM_1_GROUP = 'dcm_1_group',
  DCM_4_GROUP = 'dcm_4_group',
}

export enum DeviceVizState {
  OFF = 'OFF',
  ON = 'ON',
  SLEEP = 'SLEEP',
  ACCESS = 'ACCESS',
  COLLISION = 'COLLISION',
  DONE = 'DONE',
}

export enum AOStatus {
  IDLE = 'IDLE',
  SUCCESS = 'SUCCESS',
  MSG1_SINGLETON = 'MSG1_SINGLETON',
  COLLISION = 'COLLISION',
  PENDING = 'PENDING',
}

export enum DeviceType {
  Device1 = 1,
  Device2 = 2,
}

export interface StaticDevice {
  id: number
  x: number
  y: number
  pin_dbm: number
  harvest_power_nw: number
}

export interface DeviceStats {
  id: number
  inventoried: boolean
  completion_time_s: number | null
  group: number | null
  attempts: number
  collisions: number
  first_paging_detected: boolean
  first_paging_time_s: number | null
  last_sync_time_s?: number | null
  sync_count?: number
  lost_sync_count?: number
}

export interface Snapshot {
  time_s: number
  state: DeviceVizState[]
  energy_nj: number[]
  inventoried: boolean[]
}

export interface AOCell {
  ao_index: number
  time_ao: number
  freq_ao: number
  status: AOStatus
  msg1_result?: string | null
  final_result?: string | null
  planned_ids?: number[]
  transmitted_ids?: number[]
  dropped_before_msg1?: number[]
  device_ids: number[]
  energy_before_msg1_nj?: Record<string, number>
  energy_after_msg1_nj?: Record<string, number>
}

export interface PagingEvent {
  paging_index: number
  time_s: number
  p_access: number
  p_access_after?: number | null
  group_index?: number | null
  n_on?: number | null
  n_eligible: number
  n_attempting: number
  n_planned_attempts?: number
  n_actual_tx?: number
  n_success: number
  n_msg1_singleton?: number
  n_collision: number
  idle_count: number
  collision_ao_count: number
  success_ao_count: number
  n_heard_no_attempt?: number
  attempting_ids: number[]
  actual_tx_ids?: number[]
  success_ids: number[]
  msg1_singleton_ids?: number[]
  dropped_before_msg1_ids?: number[]
  energy_fail?: Record<string, number[]>
  aos: AOCell[]
}

export interface StrategyMetrics {
  t50_s: number | null
  t90_s: number | null
  t95_s: number | null
  t99_s: number | null
  t50_ms: number | null
  t90_ms: number | null
  t99_ms: number | null
  final_ratio_pct: number
  n_inventoried: number
  n_paging: number
  n_msg1_attempts: number
  n_collisions: number
  collision_rate: number
  n_heard_no_attempt?: number
  energy_fail?: Record<string, number>
}

export interface DeviceScientificTrace {
  device_id: number
  dt_s: number
  time_s: number[]
  energy_nj: number[]
  scientific_state: string[]
  protocol_phase: string[]
  power_draw_nw: number[]
  harvest_power_nw: number
  paging_index: number[]
  time_ao: number[]
  freq_ao: number[]
  event: string[]
  events: Array<Record<string, unknown>>
  inventoried: boolean
  completion_time_s: number | null
  e_up_nj: number
  e_low_nj: number
  frozen_after_done: boolean
  simulation_dt_s?: number
  source: string
  run_id?: string
  strategy?: string
  seed?: number
}

export interface SimulationResult {
  run_id?: string
  metadata: {
    run_id?: string
    seed: number
    num_devices: number
    device_type: DeviceType
    max_time_s: number
    dt_s: number
    snapshot_interval_s: number
    group_assignment?: string
    cdf?: { file: string; sha256_12: string; sha256: string }
  }
  paper_parameters: Record<string, number>
  reproduction_assumptions: Record<string, string | boolean>
  reader: { x: number; y: number; tx_dbm: number }
  static_devices: StaticDevice[]
  strategy_labels: Record<StrategyKey, string>
  metrics: Record<StrategyKey, StrategyMetrics>
  curves: Record<StrategyKey, { times_s: number[]; ratio_pct: number[]; label: string }>
  snapshots: Record<StrategyKey, Snapshot[]>
  paging_events: Record<StrategyKey, PagingEvent[]>
  p_access_history: Record<StrategyKey, number[][]>
  device_stats: Record<StrategyKey, DeviceStats[]>
  energy_trace?: {
    dt_s: number
    on_demand: boolean
    path: string
  }
  warnings: string[]
  warmup_diagnostics?: Record<string, Record<string, number | string>>
  paper_fig5b?: {
    available: boolean
    source: string
    paper_stated_t99_s: Record<string, number | null>
    curves: Record<string, { time_ms: number[]; ratio_pct: number[]; file?: string }>
  }
  curve_error?: Record<string, { mae: number; rmse: number; t99_error_s?: number | null }>
}

export interface SimulateRequest {
  num_devices: number
  device_type: DeviceType
  strategies: StrategyKey[]
  seed: number
  max_time_s: number
  snapshot_interval_ms: number
  collect_snapshots: boolean
  collect_paging_events: boolean
}

export interface PaperConfig {
  num_devices: number
  device_type: DeviceType
  seed: number
  max_time_s: number
  dt_ms: number
  strategies: StrategyKey[]
  paper_parameters: Record<string, number>
  reproduction_assumptions: Record<string, string | boolean>
  factory: {
    length_m: number
    width_m: number
    reader_x_m: number
    reader_y_m: number
  }
  strategy_labels: Record<StrategyKey, string>
}
