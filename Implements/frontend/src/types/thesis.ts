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

export type ControllerKind = 'auto' | 'fixed' | 'dfsa' | 'policy'
export type ResourceMode = 'independent' | 'shared' | 'fdma' | 'tdma' | 'hybrid' | 'lbt'
export type TerminationKind = 'oracle' | 'quiet_rounds' | 'id_rate' | 'energy_bound' | 'combined'

/** Per-reader (K, p*) controller; ``auto`` = DFSA when adaptive_k, else fixed K. */
export type ControllerSpec = { kind: ControllerKind; policy_id?: string | null; deterministic?: boolean }

/** How readers share the F subbands (backend ``coordination/spec.py``). */
export type ResourceSpec = {
  mode: ResourceMode
  interference?: boolean
  cross_msg1?: boolean
  /** null = link-budget conflict graph (TR 38.769 Table 7.2.2-1 / 6.5) */
  conflict_distance_m?: number | null
  n_colors?: number | null
  tdma_window_s?: number
  freq_groups?: number
  lbt_backoff_s?: number
  lbt_max_on_s?: number
  lbt_pause_s?: number
  r2d_sir_db?: number
  d2r_sinr_db?: number
  other_cw_suppression_db?: number
}

/** When a reader stops paging (backend ``inventory/termination.py``). */
export type TerminationSpec = {
  kind: TerminationKind
  quiet_rounds?: number
  window_mode?: 'rounds' | 'seconds' | 'ewma'
  window?: number
  ewma_alpha?: number
  r_min?: number | null
  r_rel?: number | null
  min_frames?: number
  margin?: number
  energy_source?: 'edge' | 'actual'
  combine?: 'all' | 'any'
  rules?: TerminationSpec[]
}

export type RunCreateInput = {
  scheme: RunScheme
  /** Optional display label; omit / empty → UI shows #id. */
  name?: string | null
  /** null = no time cap: runs until every device is done, it stalls, or the user pauses/stops it. */
  max_time_s: number | null
  /** simulated seconds per wall-clock second; null = as fast as possible */
  speed?: number | null
  /** end automatically after this long (simulated s) without a new identification */
  stall_timeout_s?: number | null
  k_initial?: number | null
  /** Schoute DFSA after round 1; k_initial is then only the first-round K. */
  adaptive_k?: boolean
  g?: number | null
  use_grouping: boolean
  use_capture: boolean
  use_ebi: boolean
  include_d2r: boolean
  seed?: number | null
  reader_start_offsets?: Record<string, number>
  /** reader ids per start group, group i starting i × reader_start_interval_s after the first */
  reader_start_groups?: number[][]
  reader_start_interval_s?: number | null
  disabled_reader_ids?: number[]
  /** frequency subbands F (null = the paper's 8) */
  f_freq?: number | null
  controller?: ControllerSpec
  resource?: ResourceSpec
  termination?: TerminationSpec
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
  reachable_completion_times?: CompletionTimes
  reader_contribution: ReaderContribution
  rounds_breakdown: RoundBreakdown[]
  aggregates?: RoundAggregates | null
}

export type RunSummary = {
  run_id: number
  section_id: number
  scheme: RunScheme
  status: RunStatus
  name?: string | null
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
  include_d2r?: boolean
  disabled_reader_ids?: number[]
  reader_start_groups?: number[][]
  reader_start_interval_s?: number | null
  /** devices left unidentified because every reader covering them stopped (non-oracle termination) */
  terminated_early_count?: number
  readers_stopped?: number
  controller_kind?: string
  policy_id?: string | null
  resource_mode?: string
  termination_label?: string
}

export type RunDetail = {
  id: number
  section_id: number
  scheme: RunScheme
  status: RunStatus
  name?: string | null
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

export type FrameInterference = { r2d_lost: number; m1_lost: number; m2_lost: number; m3_lost: number; interferers?: number }

export type ReaderInterferenceCounters = {
  frames_hit: number
  r2d_lost: number
  m1_lost: number
  m2_lost: number
  m3_lost: number
  deferred_s: number
  deferrals: number
  sinr_sum_db: number
  sinr_n: number
}

/** Coordination grant and run outcome of one reader (``metrics_json.readers``). */
export type ReaderRunInfo = {
  color: number
  subbands: number[]
  /** [slot, n_slots] of the TDMA cycle, null when the mode has no time slots */
  time_slot: [number, number] | null
  neighbors: number[]
  rounds: number
  clock_s: number
  stopped: boolean
  stop_reason: string | null
  stop_t: number | null
  /** worst-case recharge time used by the energy-bound rule */
  t_wc_s: number | null
  exhausted: boolean
  interference: ReaderInterferenceCounters
  f_r: number
}

export type InterferenceReport = {
  mode: ResourceMode | string
  n_colors: number
  readers: Record<string, ReaderRunInfo>
  /** [t_start_s, reader_id, r2d_lost, m1_lost, m2_lost, m3_lost] per frame with interference data */
  frames: [number, number, number, number, number, number][]
}

export type MetricStats = { n: number; mean: number | null; p50: number | null; p95: number | null; max: number | null; hist?: Record<string, number>; fraction_changed?: number }
export type DeviceMetricsAggregate = {
  devices: number
  readers_in_range?: MetricStats
  cbra_failures?: MetricStats
  reader_changes?: MetricStats
  fail_to_page_mean_s?: MetricStats
  fail_to_page_max_s?: MetricStats
}
export type DeviceMetricsRow = {
  device_id: number
  subtype: string
  x_m: number
  y_m: number
  readers_in_range: number
  cbra_failures: number
  reader_changes: number
  fail_to_page_count: number
  fail_to_page_mean_s: number | null
  fail_to_page_max_s: number | null
  attempts: number
  depletions: number
  identified: boolean
  identified_t: number | null
  identified_by: number | null
  drop_cause: number
}
export type DeviceMetrics = {
  aggregate: { all?: DeviceMetricsAggregate; by_subtype?: Record<string, DeviceMetricsAggregate> }
  devices: DeviceMetricsRow[]
}

export type TerminationOutcome = {
  rule: string
  spec: TerminationSpec
  t_stop: number
  reader_stop: Record<string, number>
  identified_before_stop: number
  identified_total: number
  missed: number
  missed_fraction: number
  extra_time_s: number
  extra_vs_t99_s: number | null
}
export type TerminationReplay = {
  run_id: number
  oracle: boolean
  reachable: number
  t99: number | null
  t_last_id: number | null
  outcomes: TerminationOutcome[]
}

/** Policy registry entry (``GET /policies``). */
export type PolicyInfo = {
  policy_id: string
  available: boolean
  reason: string | null
  algo: 'sb3_ppo' | 'torch_mlp' | 'zero_shot_aperiodic' | string | null
  experiment: string | null
  alpha: number | null
  beta: number | null
  seed: number | null
  scale: string | null
  training_steps: number | null
  created_at: string | null
  sha256: string | null
  train_config: Record<string, unknown> | null
  eval_summary: Record<string, EvalCandidateSummary> | null
  notes: string | null
}

export type EvalCandidateSummary = {
  cells: number
  cells_reaching_99: number
  mean_identified_fraction: number
  geo_mean_t99_vs_dfsa: number | null
  mean_resource_efficiency: number | null
}

export type TrainingCurvePoint = {
  timesteps: number
  episode?: number
  return?: number | null
  identified_fraction?: number | null
  t99?: number | null
  t_mean?: number | null
  resource_efficiency?: number | null
  readers?: number | null
  resource?: string | null
  devices?: number | null
}

export type EvalMatrixRow = {
  candidate: string
  cell: string
  readers: number
  resource: string
  offsets: string
  episodes: number
  identified_fraction: number | null
  t99: number | null
  t_mean: number | null
  resource_efficiency: number | null
  sim_time: number | null
  t99_vs_dfsa: number | null
  t_mean_vs_dfsa: number | null
}

export type TrainingRunBrief = {
  run: string
  experiment: string
  policy_id: string | null
  status: 'running' | 'done' | 'failed' | 'unknown' | string
  algo: string | null
  alpha: number | null
  beta: number | null
  seed: number | null
  scale: string | null
  training_steps: number | null
  training_episodes: number | null
  mean_return_last20: number | null
  wall_time_s: number | null
  started_at: string | null
  promoted: string | null
  error: string | null
  eval_summary: Record<string, EvalCandidateSummary> | null
  plots: string[]
}

export type TrainingRunDetail = TrainingRunBrief & {
  curve: TrainingCurvePoint[]
  eval_matrix: EvalMatrixRow[]
  meta: Record<string, unknown> | null
}

export type TrainingExperiment = {
  experiment: string
  algo: string | null
  description: string | null
  config: Record<string, unknown> | null
  runs: number
  done: number
  failed: number
  latest: TrainingRunBrief | null
}

export type TrainingExperimentDetail = {
  experiment: string
  config: Record<string, unknown> | null
  runs: TrainingRunDetail[]
}

/** Engine timing constants (s) and the number of frequency subbands F. */
export type FrameConsts = { t_paging: number; t_m1: number; t_m2: number; t_m3: number; f: number }

/** One reader frame laid out on the time-frequency grid. */
export type TimeFreqFrame = {
  id: number
  round_index: number
  t_start_s: number
  t_end_s: number
  k: number
  group: number | null
  pstar: number | null
  timing: Partial<RoundTiming>
  f: number
  /** per Msg1 slot: devices that transmitted / result code (0 idle, 1 single, 2 captured, 3 collision, 4 missed) */
  occ: number[]
  res: number[]
  /** slot -> [device id, captured] for decoded slots */
  winners: Record<string, [number, boolean]>
  /** device ids in Msg2 order */
  m2: number[]
  /** [t_s, subband, device id, identified] per Msg3 */
  m3: [number, number, number, boolean][]
  budget_dropped: number
  /** absolute subbands of the grant; absent for runs recorded before coordination */
  subbands?: number[] | null
  color?: number | null
  controller?: string | null
  interference?: FrameInterference | null
}

export type ReaderTimeFreq = {
  reader_id: number
  scheme: RunScheme
  t_first: number
  t_end: number
  consts: FrameConsts
  truncated: boolean
  frames: TimeFreqFrame[]
}

/** [t_a, t_b, E_a, E_b, kind]: ON drains, OFF harvests (rebuilt with the engine's energy model). */
export type EnergySegment = [number, number, number, number, 'on' | 'off']

export type DeviceTrace = {
  device_id: number
  scheme: RunScheme
  t_end: number
  consts: FrameConsts
  energy: { ecap: number; eoff: number; p_on: number; ph: number; t_on: number }
  /** false for runs recorded before the on timer was logged: gaps are only known at the events */
  energy_exact: boolean
  events: DeviceEvent[]
  rounds: {
    id: number
    reader_id: number
    round_index: number
    t_start_s: number
    t_end_s: number
    k: number
    timing: Partial<RoundTiming>
    /** absolute subbands of the frame's grant (FDMA / hybrid) */
    subbands?: number[] | null
  }[]
  segments: EnergySegment[]
  truncated: boolean
}
