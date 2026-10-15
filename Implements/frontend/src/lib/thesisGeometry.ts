import type { CatalogEntry, Kind, Params, Placement } from '@/types/thesis'

export const DEFAULT_WIDTH_M = 100
export const DEFAULT_HEIGHT_M = 50
export const DEFAULT_RADAR_MARGIN_M = 25
export const DEFAULT_RADAR_SPACING_M = 50
export const DEFAULT_RADAR_RADIUS_M = 30
export const MAX_BULK = 5000
export const MAX_GRID = 2000

export type Point = { x_m: number; y_m: number }

export function inside(x: number, y: number, width: number, height: number): boolean {
  return x >= -1e-6 && y >= -1e-6 && x <= width + 1e-6 && y <= height + 1e-6
}

export function radarGrid(
  width: number,
  height: number,
  margin: number,
  spacing: number,
): { points: Point[]; capped: boolean } {
  if (!(spacing > 1e-6) || margin < 0) return { points: [], capped: false }
  const xEnd = width - margin
  const yEnd = height - margin
  if (margin > xEnd + 1e-6 || margin > yEnd + 1e-6) return { points: [], capped: false }
  const xs = axis(margin, xEnd, spacing)
  const ys = axis(margin, yEnd, spacing)
  if (xs.capped || ys.capped || xs.values.length * ys.values.length > MAX_GRID) {
    return { points: [], capped: true }
  }
  const points: Point[] = []
  for (const y of ys.values) {
    for (const x of xs.values) points.push({ x_m: round3(x), y_m: round3(y) })
  }
  return { points, capped: false }
}

export function intervalGrid(
  width: number,
  height: number,
  spacingX: number,
  spacingY: number,
): { points: Point[]; capped: boolean } {
  if (!(spacingX > 1e-6) || !(spacingY > 1e-6)) return { points: [], capped: false }
  const xs = axis(spacingX, width - spacingX, spacingX)
  const ys = axis(spacingY, height - spacingY, spacingY)
  if (xs.capped || ys.capped || xs.values.length * ys.values.length > MAX_GRID) {
    return { points: [], capped: true }
  }
  const points: Point[] = []
  for (const y of ys.values) {
    for (const x of xs.values) points.push({ x_m: round3(x), y_m: round3(y) })
  }
  return { points, capped: false }
}

export function randomPoints(count: number, width: number, height: number): Point[] {
  return Array.from({ length: count }, () => ({
    x_m: Math.random() * width,
    y_m: Math.random() * height,
  }))
}

export function findCatalog(catalog: CatalogEntry[], kind: Kind, subtype: string | null) {
  return catalog.find((entry) => entry.kind === kind && entry.subtype === subtype)
}

export function cloneParams(params: Params): Params {
  return { ...params }
}

export function placementInput(placement: Placement) {
  return {
    kind: placement.kind,
    subtype: placement.subtype,
    x_m: placement.x_m,
    y_m: placement.y_m,
    params: cloneParams(placement.params),
  }
}

function axis(start: number, end: number, step: number) {
  const values: number[] = []
  for (let value = start; value <= end + 1e-6; value += step) {
    values.push(value)
    if (values.length > MAX_GRID) return { values, capped: true }
  }
  return { values, capped: false }
}

function round3(value: number) {
  return Math.round(value * 1000) / 1000
}
