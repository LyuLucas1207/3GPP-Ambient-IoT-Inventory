import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  createRun as apiCreateRun,
  deleteRun as apiDeleteRun,
  fetchDeviceStates,
  fetchRun,
  fetchRuns,
  fetchTimeline,
  stopRun as apiStopRun,
} from '@/api/thesisRuns'
import type {
  DeviceStates,
  RunCreateInput,
  RunDetail,
  RunSummary,
  Timeline,
} from '@/types/thesis'

function explain(err: unknown, t: (key: string) => string) {
  const raw = err instanceof Error ? err.message : 'request_failed'
  if (raw === 'Failed to fetch') return t('thesis.errors.network')
  const key = `thesis.errors.${raw}`
  const translated = t(key)
  return translated === key ? raw : translated
}

export type InventoryRunsState = ReturnType<typeof useInventoryRuns>

export function useInventoryRuns(sectionId: number | null) {
  const { t } = useTranslation()
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null)
  const [activeRun, setActiveRun] = useState<RunDetail | null>(null)
  const [deviceStates, setDeviceStates] = useState<DeviceStates>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const timelineCache = useRef(new Map<string, Timeline>())

  const fail = useCallback(
    (err: unknown) => setError(explain(err, t)),
    [t],
  )

  const refreshRuns = useCallback(async () => {
    if (sectionId == null) {
      setRuns([])
      return
    }
    try {
      setRuns(await fetchRuns(sectionId))
    } catch (err) {
      fail(err)
    }
  }, [sectionId, fail])

  useEffect(() => {
    setRuns([])
    setSelectedRunId(null)
    setActiveRun(null)
    setDeviceStates({})
    timelineCache.current.clear()
    void refreshRuns()
  }, [sectionId, refreshRuns])

  useEffect(() => {
    const running = runs.some((r) => r.status === 'running' || r.status === 'pending')
    if (!running) return
    const id = window.setInterval(() => {
      void refreshRuns()
    }, 2000)
    return () => window.clearInterval(id)
  }, [runs, refreshRuns])

  useEffect(() => {
    if (selectedRunId == null) {
      setActiveRun(null)
      setDeviceStates({})
      return
    }
    let cancelled = false
    void (async () => {
      try {
        const [detail, statesResponse] = await Promise.all([
          fetchRun(selectedRunId),
          fetchDeviceStates(selectedRunId),
        ])
        if (cancelled) return
        setActiveRun(detail)
        setDeviceStates(statesResponse.states ?? {})
      } catch (err) {
        if (!cancelled) fail(err)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [selectedRunId, fail])

  const createRun = useCallback(
    async (config: RunCreateInput) => {
      if (sectionId == null) return
      setBusy(true)
      setError(null)
      try {
        const detail = await apiCreateRun(sectionId, config)
        setSelectedRunId(detail.id)
        await refreshRuns()
      } catch (err) {
        fail(err)
      } finally {
        setBusy(false)
      }
    },
    [sectionId, refreshRuns, fail],
  )

  const deleteRun = useCallback(
    async (id: number) => {
      // Optimistically remove so the UI updates before the network round-trip
      // and the backend's background cascade completes.
      setRuns((prev) => prev.filter((r) => r.run_id !== id))
      if (selectedRunId === id) setSelectedRunId(null)
      timelineCache.current = new Map(
        Array.from(timelineCache.current.entries()).filter(([key]) => !key.startsWith(`${id}:`)),
      )
      setError(null)
      try {
        await apiDeleteRun(id)
      } catch (err) {
        fail(err)
      }
      void refreshRuns()
    },
    [selectedRunId, refreshRuns, fail],
  )

  const stopRun = useCallback(
    async (id: number) => {
      // Optimistically mark it stopped locally so the chip updates immediately.
      setRuns((prev) => prev.map((r) => (r.run_id === id ? { ...r, status: 'stopped' } : r)))
      setError(null)
      try {
        await apiStopRun(id)
      } catch (err) {
        fail(err)
      }
      void refreshRuns()
    },
    [refreshRuns, fail],
  )

  const loadTimeline = useCallback(
    async (deviceId: number): Promise<Timeline | null> => {
      if (selectedRunId == null) return null
      const key = `${selectedRunId}:${deviceId}`
      const cached = timelineCache.current.get(key)
      if (cached) return cached
      try {
        const tl = await fetchTimeline(selectedRunId, deviceId)
        timelineCache.current.set(key, tl)
        return tl
      } catch (err) {
        fail(err)
        return null
      }
    },
    [selectedRunId, fail],
  )

  const selectedRun = useMemo(
    () => runs.find((r) => r.run_id === selectedRunId) ?? null,
    [runs, selectedRunId],
  )

  return {
    runs,
    selectedRunId,
    setSelectedRunId,
    selectedRun,
    activeRun,
    deviceStates,
    busy,
    error,
    clearError: () => setError(null),
    createRun,
    deleteRun,
    stopRun,
    loadTimeline,
    refreshRuns,
  }
}
