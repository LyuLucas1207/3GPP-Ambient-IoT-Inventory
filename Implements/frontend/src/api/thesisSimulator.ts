import { deleteOk, getJson, patchJson, postJson } from '@/api/http'
import type {
  CatalogEntry,
  Kind,
  Params,
  Placement,
  PlacementInput,
  SectionCreate,
  SectionDetail,
  SectionSummary,
} from '@/types/thesis'

const BASE = '/api/thesis-simulator'

export function fetchCatalog(): Promise<CatalogEntry[]> {
  return getJson(`${BASE}/catalog`)
}

export function fetchSections(): Promise<SectionSummary[]> {
  return getJson(`${BASE}/sections`)
}

export function fetchSection(id: number): Promise<SectionDetail> {
  return getJson(`${BASE}/sections/${id}`)
}

export function createSection(body: SectionCreate): Promise<SectionDetail> {
  return postJson(`${BASE}/sections`, body)
}

export function patchSection(
  id: number,
  body: { name?: string; width_m?: number; height_m?: number; status?: 'initialized'; marker_scale?: number },
): Promise<SectionDetail> {
  return patchJson(`${BASE}/sections/${id}`, body)
}

export function postPlacement(sectionId: number, body: PlacementInput): Promise<Placement> {
  return postJson(`${BASE}/sections/${sectionId}/placements`, body)
}

export function postPlacementBatch(sectionId: number, placements: PlacementInput[]): Promise<Placement[]> {
  return postJson(`${BASE}/sections/${sectionId}/placements/batch`, { placements })
}

export function patchPlacementBatch(
  sectionId: number,
  body: { kind: Kind; subtype: string | null; params: Params },
): Promise<Placement[]> {
  return patchJson(`${BASE}/sections/${sectionId}/placements/batch`, body)
}

export function convertPlacements(
  sectionId: number,
  body: { ids: number[]; kind: 'station' | 'radar' },
): Promise<Placement[]> {
  return postJson(`${BASE}/sections/${sectionId}/placements/convert`, body)
}

export function patchPlacement(
  sectionId: number,
  placementId: number,
  body: PlacementInput,
): Promise<Placement> {
  return patchJson(`${BASE}/sections/${sectionId}/placements/${placementId}`, body)
}

export function removePlacement(sectionId: number, placementId: number): Promise<void> {
  return deleteOk(`${BASE}/sections/${sectionId}/placements/${placementId}`)
}

export function removePlacementBatch(sectionId: number, ids: number[]): Promise<void> {
  return deleteOk(`${BASE}/sections/${sectionId}/placements/batch`, { ids })
}

export function deleteSection(id: number): Promise<void> {
  return deleteOk(`${BASE}/sections/${id}`)
}
