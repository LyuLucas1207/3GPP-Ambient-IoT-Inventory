export type Kind = 'device' | 'station' | 'radar'
export type Shape = 'circle' | 'square' | 'triangle' | 'diamond' | 'hexagon'
export type ParamValue = string | number | boolean | null
export type Params = Record<string, ParamValue>
export type PlacementId = number | string
export type DeviceMix = 'mixed' | '1' | '2a' | '2b'

export type CatalogEntry = {
  kind: Kind
  subtype: string | null
  shape: Shape
  defaults: Params
}

export type Placement = {
  id: PlacementId
  kind: Kind
  subtype: string | null
  x_m: number
  y_m: number
  params: Params
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
