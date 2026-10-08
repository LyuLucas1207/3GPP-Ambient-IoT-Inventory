import { useEffect, useMemo, useState } from 'react'
import type { AperiodicSimulationResult } from '@/types/aperiodicSimulation'

const TICK_MS = 120

/** Last element whose start time is <= t (arrays are sorted by time). */
function lastAtOrBefore<T>(items: T[], t: number, start: (x: T) => number): T | null {
  let lo = 0
  let hi = items.length - 1
  let best = -1
  while (lo <= hi) {
    const mid = (lo + hi) >> 1
    if (start(items[mid]) <= t) {
      best = mid
      lo = mid + 1
    } else hi = mid - 1
  }
  return best >= 0 ? items[best] : null
}

/** Frame clock over the interactive snapshots of one run; autoplays when a new run arrives. */
export function useAperiodicPlayback(result: AperiodicSimulationResult | null) {
  const snaps = useMemo(() => result?.snapshots ?? [], [result])
  const [frame, setFrame] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(2)
  const [runId, setRunId] = useState<string | null>(null)

  if ((result?.run_id ?? null) !== runId) {
    setRunId(result?.run_id ?? null)
    setFrame(0)
    setPlaying(snaps.length > 1)
  }

  useEffect(() => {
    if (!playing || snaps.length < 2) return
    const id = window.setInterval(() => {
      setFrame((f) => {
        const next = f + speed
        if (next >= snaps.length - 1) {
          setPlaying(false)
          return snaps.length - 1
        }
        return next
      })
    }, TICK_MS)
    return () => window.clearInterval(id)
  }, [playing, speed, snaps.length])

  const idx = Math.min(frame, Math.max(snaps.length - 1, 0))
  const snap = snaps[idx] ?? null
  const time = snap?.time_s ?? 0
  const interactive = result?.runtime_mode === 'interactive' && snaps.length > 0
  const codes = useMemo(() => result?.state_codes ?? [], [result])

  const counts = useMemo(() => {
    const out: Record<string, number> = {}
    if (snap) for (const s of snap.state) out[codes[s]] = (out[codes[s]] ?? 0) + 1
    return out
  }, [snap, codes])
  const row = useMemo(() => (result ? lastAtOrBefore(result.rounds, time, (r) => r.t_start_s) : null), [result, time])
  const inspect = useMemo(
    () => (result?.cbra_inspect ? lastAtOrBefore(result.cbra_inspect, time, (r) => r.t_start_s ?? Infinity) : null),
    [result, time],
  )

  const togglePlay = () => {
    if (!playing && idx >= snaps.length - 1) setFrame(0)
    setPlaying(!playing)
  }
  const seek = (n: number) => {
    setPlaying(false)
    setFrame(n)
  }

  return {
    frames: snaps.length,
    idx,
    snap,
    time,
    interactive,
    codes,
    counts,
    row,
    inspect,
    playing,
    speed,
    setSpeed,
    togglePlay,
    restart: () => setFrame(0),
    seek,
  }
}

export type AperiodicPlayback = ReturnType<typeof useAperiodicPlayback>
