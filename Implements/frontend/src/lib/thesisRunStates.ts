// Live per-device state codes pushed by the backend (inventory/state.py STATE_*).
// Index = code. Keep this list in the same order as the backend STATE_LABELS.
export const RUN_STATE_LABELS = [
  'off',
  'on',
  'latched',
  'tx',
  'm1_success',
  'collision',
  'identified',
  'depleted',
  'dropped',
  'unreachable',
] as const

export type RunStateLabel = (typeof RUN_STATE_LABELS)[number]

export const RUN_STATE_COLOR: Record<RunStateLabel, string> = {
  off: '#71717a',
  on: '#4dbeee',
  latched: '#7e2f8e',
  tx: '#edb120',
  m1_success: '#0072bd',
  collision: '#d95319',
  identified: '#77ac30',
  depleted: '#ec4899',
  // Never identified when the run ended (stalled / time cap / out of coverage): red, drawn on top.
  dropped: '#ef4444',
  unreachable: '#ef4444',
}

/** Codes drawn last and enlarged on the map so unidentified devices stand out. */
export const FLAGGED_CODES: ReadonlySet<number> = new Set([
  RUN_STATE_LABELS.indexOf('dropped'),
  RUN_STATE_LABELS.indexOf('unreachable'),
])

export const RUN_STATE_COLOR_BY_CODE: string[] = RUN_STATE_LABELS.map((label) => RUN_STATE_COLOR[label])

/** Decode a base64 payload (standard ``atob``) into the bytes of a typed array. */
export function decodeBase64(b64: string): ArrayBuffer {
  const bin = atob(b64)
  const out = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i)
  return out.buffer
}

export const SPEED_OPTIONS: (number | null)[] = [1, 2, 5, 10, 50, null]
