import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { fetchHealth, fetchPaperConfig, runSimulation } from '../api/simulation'
import {
  DeviceType,
  StrategyKey,
  type PaperConfig,
  type SimulateRequest,
  type SimulationResult,
} from '../types/simulation'

const PAPER: SimulateRequest = {
  num_devices: 600,
  device_type: DeviceType.Device1,
  strategies: [StrategyKey.EM, StrategyKey.DCM_1_GROUP, StrategyKey.DCM_4_GROUP],
  seed: 42,
  max_time_s: 25,
  snapshot_interval_ms: 100,
  collect_snapshots: true,
  collect_paging_events: true,
}

export function useSimulation() {
  const [request, setRequest] = useState<SimulateRequest>(PAPER)
  const [paper, setPaper] = useState<PaperConfig | null>(null)
  const [result, setResult] = useState<SimulationResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [backendUp, setBackendUp] = useState<boolean | null>(null)
  const [viewStrategy, setViewStrategy] = useState(StrategyKey.DCM_4_GROUP)
  const [frame, setFrame] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [pagingIndex, setPagingIndex] = useState(0)
  const timer = useRef<number | null>(null)

  useEffect(() => {
    fetchHealth().then(setBackendUp)
    fetchPaperConfig()
      .then(setPaper)
      .catch((err: Error) => setError(err.message))
  }, [])

  const snapshots = result?.snapshots[viewStrategy] ?? []
  const events = result?.paging_events[viewStrategy] ?? []

  useEffect(() => {
    setFrame(0)
    setPagingIndex(0)
    setPlaying(false)
  }, [result, viewStrategy])

  useEffect(() => {
    if (!playing || snapshots.length === 0) return
    timer.current = window.setInterval(() => {
      setFrame((i) => (i + 1 >= snapshots.length ? 0 : i + 1))
    }, 80)
    return () => {
      if (timer.current != null) window.clearInterval(timer.current)
    }
  }, [playing, snapshots.length])

  const run = useCallback(async (override?: Partial<SimulateRequest>) => {
    const body = { ...request, ...override }
    setRequest(body)
    setBusy(true)
    setError(null)
    setPlaying(false)
    try {
      const data = await runSimulation(body)
      setResult(data)
      const first = body.strategies.includes(StrategyKey.DCM_4_GROUP)
        ? StrategyKey.DCM_4_GROUP
        : body.strategies[0]
      setViewStrategy(first)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }, [request])

  const currentSnapshot = snapshots[Math.min(frame, Math.max(0, snapshots.length - 1))] ?? null
  const currentEvent = events[Math.min(pagingIndex, Math.max(0, events.length - 1))] ?? null

  const selectedStats = useMemo(() => {
    if (selectedId == null || !result) return null
    return result.device_stats[viewStrategy]?.[selectedId] ?? null
  }, [result, selectedId, viewStrategy])

  return {
    request,
    setRequest,
    paper,
    result,
    busy,
    error,
    backendUp,
    viewStrategy,
    setViewStrategy,
    frame,
    setFrame,
    playing,
    setPlaying,
    selectedId,
    setSelectedId,
    pagingIndex,
    setPagingIndex,
    snapshots,
    events,
    currentSnapshot,
    currentEvent,
    selectedStats,
    run,
    resetPaper: () => setRequest(PAPER),
  }
}
