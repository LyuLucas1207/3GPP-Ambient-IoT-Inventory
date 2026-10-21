import type { Kind, Params, Placement, Scene } from '@/types/thesis'

const DRAFT_KEY = 'thesis-simulation-draft-v1'

export function loadDraft(): Scene | null {
  try {
    const raw = window.localStorage.getItem(DRAFT_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as { v?: number; scene?: Scene }
    if (parsed.v !== 1 || !parsed.scene || parsed.scene.saved) return null
    if (!isScene(parsed.scene)) return null
    return {
      ...parsed.scene,
      saved: false,
      id: null,
      status: 'initializing',
      locked: false,
      markerScale: parsed.scene.markerScale || 0.7,
      deviceMarkerScale: parsed.scene.deviceMarkerScale ?? 0.3,
      nonce: parsed.scene.nonce || Date.now(),
    }
  } catch {
    return null
  }
}

export function saveDraft(scene: Scene) {
  try {
    window.localStorage.setItem(DRAFT_KEY, JSON.stringify({ v: 1, scene: { ...scene, saved: false, id: null } }))
  } catch {
    // A full browser store should not block editing. The database is still the save target.
  }
}

export function clearDraft() {
  try {
    window.localStorage.removeItem(DRAFT_KEY)
  } catch {
    // Ignore private-mode storage failures.
  }
}

function isScene(value: Scene): boolean {
  return (
    typeof value.name === 'string' &&
    typeof value.width_m === 'number' &&
    typeof value.height_m === 'number' &&
    Array.isArray(value.placements) &&
    value.placements.every(isPlacement)
  )
}

function isPlacement(value: Placement): boolean {
  return (
    !!value &&
    (value.kind === 'device' || value.kind === 'station' || value.kind === 'radar') &&
    (typeof value.id === 'string' || typeof value.id === 'number') &&
    typeof value.x_m === 'number' &&
    typeof value.y_m === 'number' &&
    isParams(value.params)
  )
}

function isParams(value: Params): boolean {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false
  return Object.values(value).every(
    (item) => item == null || typeof item === 'string' || typeof item === 'number' || typeof item === 'boolean',
  )
}

export function isKind(value: string): value is Kind {
  return value === 'device' || value === 'station' || value === 'radar'
}
