export type Kind = 'device' | 'station' | 'radar'
export type Shape = 'circle' | 'square' | 'triangle' | 'diamond' | 'hexagon'
export type ParamValue = string | number | boolean | null
export type Params = Record<string, ParamValue>
export type PlacementId = number | string
export type DeviceMix = 'mixed' | '1' | '2a' | '2b'
export type DeviceSubtype = '1' | '2a' | '2b'
export type DerivedRanges = Record<DeviceSubtype, number>

export type ScenarioDefaults = {
  width_m: number
  height_m: number
  bs_lattice_spacing_m: number
  bs_positions: [number, number][]
  active_bs_xy: [number, number]
  default_n_devices: number
  max_placements: number
}

export type CatalogEntry = {
  kind: Kind
  subtype: string | null
  shape: Shape
  defaults: Params
  derived_ranges?: DerivedRanges
}

export type Placement = {
  id: PlacementId
  kind: Kind
  subtype: string | null
  x_m: number
  y_m: number
  params: Params
  derived?: { effective_range_m?: DerivedRanges }
}

export type PlacementInput = {
  kind: Kind
  subtype: string | null
  x_m: number
  y_m: number
  params: Params
}

export type SectionStatus = 'initializing' | 'initialized'

export type Scene = {
  id: number | null
  name: string
  width_m: number
  height_m: number
  placements: Placement[]
  dirty: boolean
  saved: boolean
  status: SectionStatus
  locked: boolean
  markerScale: number
  deviceMarkerScale: number
  nonce: number
}

export type SectionSummary = {
  id: number
  name: string
  width_m: number
  height_m: number
  placement_count: number
  status: SectionStatus
  updated_at: string
}

export type SectionDetail = {
  id: number
  name: string
  width_m: number
  height_m: number
  status: SectionStatus
  marker_scale: number
  device_marker_scale: number
  created_at: string
  updated_at: string
  placements: Placement[]
}

export type SectionCreate = {
  name: string
  width_m: number
  height_m: number
  placements: PlacementInput[]
}

export type RunScheme = 'periodic' | 'aperiodic'
export type RunStatus = 'pending' | 'running' | 'paused' | 'completed' | 'stopped' | 'failed' | 'deleted'
export type DeviceFinalState = 'identified' | 'dropped' | 'unreachable' | 'pending'

export type RunCreateInput = {
  scheme: RunScheme
  /** null = no time cap: runs until every device is done, it stalls, or the user pauses/stops it. */
  max_time_s: number | null
  /** simulated seconds per wall-clock second; null = as fast as possible */
  speed?: number | null
  /** end automatically after this long (simulated s) without a new identification */
  stall_timeout_s?: number | null
  k_initial?: number | null
  g?: number | null
  use_grouping: boolean
  use_capture: boolean
  use_ebi: boolean
  include_d2r: boolean
  seed?: number | null
  reader_start_offsets?: Record<string, number>
  disabled_reader_ids?: number[]
}

export type IdentificationPoint = [number, number]
export type CompletionTimes = Partial<Record<'50' | '90' | '95' | '99' | '100', number | null>>
export type RoundAggregates = {
  slots_total: number
  success_total: number
  collision_total: number
  empty_total: number
  resource_efficiency: number
  overhead_s: Record<string, number>
  deaths_by_stage: Record<string, Record<string, number>>
  energy_j_by_subtype: Record<string, number>
}
export type ReaderContribution = Record<number, number>
export type RoundBreakdown = {
  reader_id: number
  round_index: number
  t_start_s: number
  t_end_s: number
  success: number
  collision: number
  empty: number
}
export type RunAnalysis = {
  run_id: number
  scheme: RunScheme
  status: RunStatus
  summary: RunSummary
  config?: Record<string, unknown>
  identification_curve: IdentificationPoint[]
  identification_by_subtype?: Record<string, IdentificationPoint[]>
  completion_times: CompletionTimes
  population_completion_times?: CompletionTimes
  reader_contribution: ReaderContribution
  rounds_breakdown: RoundBreakdown[]
  aggregates?: RoundAggregates | null
}

export type RunSummary = {
  run_id: number
  section_id: number
  scheme: RunScheme
  status: RunStatus
  total_devices: number
  identified_total: number
  identified_by_subtype: Record<string, number>
  died_count: number
  dropped_count: number
  rounds_total: number
  wall_duration_s: number
  created_at: string
  completed_at: string | null
  duration_s: number | null
  sim_time_s: number
  unreachable_count: number
  speed: number | null
  max_time_s: number | null
}

export type RunDetail = {
  id: number
  section_id: number
  scheme: RunScheme
  status: RunStatus
  config: Record<string, unknown>
  scene_snapshot: Record<string, unknown>
  requested_at: string
  started_at: string | null
  completed_at: string | null
  duration_s: number | null
  error_detail: string | null
  summary: RunSummary | null
}

export type DeviceEvent = {
  id: number
  device_id: number
  reader_id: number | null
  round_id: number | null
  t_s: number
  event_type: string
  cause: string | null
  energy_j: number | null
  payload: Record<string, unknown> | null
}

export type ReaderEvent = {
  id: number
  reader_id: number
  round_id: number | null
  t_s: number
  event_type: string
  slot_index: number | null
  payload: Record<string, unknown> | null
}

export type RunRound = {
  id: number
  frame_seq: number | null
  reader_id: number
  round_index: number
  t_start_s: number
  t_end_s: number
  k_estimate: number | null
  g: number | null
  pstar: number | null
  slot_count: number
  success_count: number
  collision_count: number
  empty_count: number
  candidates: number | null
  joiners: number | null
  on_at_page: number | null
  backlog_true: number | null
  served: number | null
  s_budget: number | null
  budget_dropped: number | null
  n_hat: number | null
  mnot_prev: number | null
  mnot_next: number | null
  n_done_total: number | null
  identified_by_subtype: Record<string, number> | null
  timing: RoundTiming | null
  energy_j: Record<string, number> | null
  deaths: Record<string, Record<string, number>> | null
  metadata: Record<string, unknown> | null
}

export type RoundTiming = { paging: number; m1: number; ebi: number; m2: number; m3: number }

/** Per-slot M1 outcome of one round: occupancy + result code (0 idle, 1 single, 2 captured, 3 collision, 4 missed). */
export type RoundSlots = {
  id: number
  reader_id: number
  round_index: number
  slots: { f: number; occ: number[]; res: number[] } | null
}

export type RunCounters = {
  sim_time_s: number
  total: number
  identified: number
  identified_by_subtype: Record<string, number>
  dropped: number
  unreachable: number
  no_progress: number
  depletions: number
  rounds: number
  frame_seq: number
}

/** SSE `snapshot` event / GET /runs/{id}/snapshot. */
export type RunSnapshot = {
  run_id?: number
  status?: RunStatus
  speed?: number | null
  seq?: number
  frame_seq?: number
  sim_time_s: number
  device_ids: number[]
  state_labels: string[]
  state_codes_b64: string
  energy_b64: string
  counters?: Partial<RunCounters>
}

/** SSE `tick` event: every frame since the previous tick, merged. */
export type RunTick = {
  seq: number
  sim_time_s: number
  changes: [number, number][]
  rounds: RunRound[]
  counters: RunCounters
  frames: number
  energy_b64?: string
}

export type Timeline = {
  device_id: number
  final_state: DeviceFinalState
  events: DeviceEvent[]
  rounds_touched: number[]
  energy_series: [number, number][]
}

export type DeviceStates = Record<number, string>
