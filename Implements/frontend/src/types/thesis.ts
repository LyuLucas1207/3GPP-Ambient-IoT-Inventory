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
export type RunStatus = 'pending' | 'running' | 'completed' | 'stopped' | 'failed'
export type DeviceFinalState = 'identified' | 'died' | 'dropped' | 'survived' | 'unknown'

export type RunCreateInput = {
  scheme: RunScheme
  max_time_s: number
  k_initial?: number | null
  g?: number | null
  use_grouping: boolean
  use_capture: boolean
  use_ebi: boolean
  include_d2r: boolean
  seed?: number | null
  reader_start_offsets?: Record<string, number>
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
  metadata: Record<string, unknown> | null
}

export type Timeline = {
  device_id: number
  final_state: DeviceFinalState
  events: DeviceEvent[]
  rounds_touched: number[]
  energy_series: [number, number][]
}

export type DeviceStates = Record<number, DeviceFinalState>
