import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchRounds, fetchSnapshot, runStreamUrl } from '@/api/thesisRuns'
import { thesisKeys } from '@/lib/thesisQueryKeys'
import { decodeBase64 } from '@/lib/thesisRunStates'
import type { RunCounters, RunRound, RunSnapshot, RunStatus, RunTick } from '@/types/thesis'

/** Per-device live state. The typed arrays are mutated in place; `version` changes on every update. */
export type LiveDevices = {
  deviceIds: number[]
  indexById: Map<number, number>
  codes: Uint8Array
  energy: Float32Array
  version: number
}

export type LiveRunState = ReturnType<typeof useLiveRun>

const LIVE: ReadonlySet<RunStatus> = new Set(['pending', 'running'])

/**
 * Follow one run over Server-Sent Events (browser-native EventSource: automatic
 * reconnect with Last-Event-ID). A `snapshot` seeds the device arrays, each
 * `tick` applies the merged changes, `status`/`done` report lifecycle changes.
 * Finished/paused runs get one snapshot followed by `done`.
 */
export function useLiveRun(runId: number | null, listedStatus: RunStatus | undefined, onLifecycle?: () => void) {
  const queryClient = useQueryClient()
  const [devices, setDevices] = useState<LiveDevices | null>(null)
  const [rounds, setRounds] = useState<RunRound[]>([])
  const [counters, setCounters] = useState<Partial<RunCounters>>({})
  const [simTime, setSimTime] = useState(0)
  const [status, setStatus] = useState<RunStatus | null>(null)
  const [speed, setSpeed] = useState<number | null>(null)
  const [connected, setConnected] = useState(false)
  /** null = following the live/latest state; a number = showing a stored snapshot at that sim time */
  const [viewTime, setViewTime] = useState<number | null>(null)

  const devicesRef = useRef<LiveDevices | null>(null)
  const roundIds = useRef(new Set<number>())
  const lifecycleRef = useRef(onLifecycle)
  useEffect(() => {
    lifecycleRef.current = onLifecycle
  }, [onLifecycle])

  const publish = useCallback((next: LiveDevices) => {
    devicesRef.current = next
    setDevices({ ...next })
  }, [])

  const addRounds = useCallback((incoming: RunRound[]) => {
    const fresh = incoming.filter((r) => !roundIds.current.has(r.id))
    if (fresh.length === 0) return
    for (const r of fresh) roundIds.current.add(r.id)
    setRounds((prev) => [...prev, ...fresh])
  }, [])

  const applySnapshot = useCallback(
    (snap: RunSnapshot) => {
      const ids = snap.device_ids
      const prev = devicesRef.current
      const indexById =
        prev && prev.deviceIds.length === ids.length && prev.deviceIds.every((id, i) => id === ids[i])
          ? prev.indexById
          : new Map(ids.map((id, i) => [id, i]))
      publish({
        deviceIds: ids,
        indexById,
        codes: new Uint8Array(decodeBase64(snap.state_codes_b64)),
        energy: new Float32Array(decodeBase64(snap.energy_b64)),
        version: (prev?.version ?? 0) + 1,
      })
      setSimTime(snap.sim_time_s)
      if (snap.counters) setCounters(snap.counters)
      if (snap.status) setStatus(snap.status)
      if (snap.speed !== undefined) setSpeed(snap.speed ?? null)
    },
    [publish],
  )

  // Reset whenever another run is selected.
  useEffect(() => {
    devicesRef.current = null
    roundIds.current = new Set()
    setDevices(null)
    setRounds([])
    setCounters({})
    setSimTime(0)
    setStatus(null)
    setSpeed(null)
    setViewTime(null)
  }, [runId])

  // (Re)open the stream when the run is selected and whenever it becomes live again (resume).
  const live = listedStatus != null && LIVE.has(listedStatus)
  useEffect(() => {
    if (runId == null) return
    const es = new EventSource(runStreamUrl(runId))
    let roundsLoaded = false
    setConnected(true)

    es.addEventListener('snapshot', (ev) => {
      const snap = JSON.parse((ev as MessageEvent).data) as RunSnapshot
      applySnapshot(snap)
      // The run may have changed state before this stream connected.
      if (snap.status && snap.status !== listedStatus) lifecycleRef.current?.()
      if (!roundsLoaded) {
        roundsLoaded = true
        // Rounds persisted so far; the stream then appends new ones (deduplicated by id).
        void queryClient
          .fetchQuery({ queryKey: thesisKeys.rounds(runId), queryFn: () => fetchRounds(runId), staleTime: 0 })
          .then(addRounds)
          .catch(() => undefined)
      }
    })
    es.addEventListener('tick', (ev) => {
      const tick = JSON.parse((ev as MessageEvent).data) as RunTick
      const cur = devicesRef.current
      if (cur) {
        for (const [idx, code] of tick.changes) cur.codes[idx] = code
        const energy = tick.energy_b64 ? new Float32Array(decodeBase64(tick.energy_b64)) : cur.energy
        publish({ ...cur, energy, version: cur.version + 1 })
      }
      addRounds(tick.rounds)
      setCounters(tick.counters)
      setSimTime(tick.sim_time_s)
    })
    es.addEventListener('status', (ev) => {
      const msg = JSON.parse((ev as MessageEvent).data) as { status: RunStatus; speed: number | null }
      setStatus(msg.status)
      setSpeed(msg.speed)
      lifecycleRef.current?.()
    })
    es.addEventListener('done', (ev) => {
      const msg = JSON.parse((ev as MessageEvent).data) as { status: RunStatus }
      setStatus(msg.status)
      es.close() // otherwise EventSource would auto-reconnect to a finished stream
      setConnected(false)
      lifecycleRef.current?.()
    })
    return () => {
      es.close()
      setConnected(false)
    }
    // listedStatus is read only to compare on connect; reconnecting is driven by `live`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId, live, applySnapshot, addRounds, publish, queryClient])

  /** Show the stored device states at simulated time `t` (null = back to latest/live).
   *  Snapshots are immutable once written, so they are cached per (run, time). */
  const seek = useCallback(
    async (t: number | null) => {
      if (runId == null) return
      setViewTime(t)
      const key = t == null ? null : Math.round(t * 2) / 2 // snapshots are 0.5 s apart
      try {
        const snap = await queryClient.fetchQuery({
          queryKey: thesisKeys.snapshot(runId, key),
          queryFn: () => fetchSnapshot(runId, key ?? undefined),
          staleTime: key == null ? 0 : Infinity,
        })
        applySnapshot({ ...snap, sim_time_s: t ?? snap.sim_time_s })
      } catch {
        /* no snapshot yet */
      }
    },
    [runId, applySnapshot, queryClient],
  )

  return { devices, rounds, counters, simTime, status, speed, connected, viewTime, seek }
}
