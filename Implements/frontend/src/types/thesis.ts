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
