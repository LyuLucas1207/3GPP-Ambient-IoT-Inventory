import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  createRun as apiCreateRun,
  deleteRun as apiDeleteRun,
  fetchRun,
  fetchRuns,
  pauseRun as apiPauseRun,
  resumeRun as apiResumeRun,
  setRunSpeed as apiSetRunSpeed,
  stopRun as apiStopRun,
} from '@/api/thesisRuns'
import { thesisKeys } from '@/lib/thesisQueryKeys'
import type { RunCreateInput, RunSummary } from '@/types/thesis'

function explain(err: unknown, t: (key: string) => string) {
  const raw = err instanceof Error ? err.message : 'request_failed'
  if (raw === 'Failed to fetch') return t('thesis.errors.network')
  const key = `thesis.errors.${raw}`
  const translated = t(key)
  return translated === key ? raw : translated
}

export type InventoryRunsState = ReturnType<typeof useInventoryRuns>

/**
 * Run list + run controls for one section (TanStack Query). There is no
 * polling: the selected run's SSE stream reports lifecycle changes and the page
 * calls `refreshRuns()` (an invalidation) on each one.
 */
export function useInventoryRuns(sectionId: number | null, options: { pollWhileLive?: boolean } = {}) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fail = useCallback((err: unknown) => setError(explain(err, t)), [t])

  useEffect(() => {
    setSelectedRunId(null)
  }, [sectionId])

  const runsKey = thesisKeys.runs(sectionId)
  const runsQuery = useQuery({
    queryKey: runsKey,
    queryFn: () => fetchRuns(sectionId as number),
    enabled: sectionId != null,
    // Pages without an SSE feed (analysis) refresh the list while something is running.
    refetchInterval: (query) =>
      options.pollWhileLive && query.state.data?.some((r) => r.status === 'running' || r.status === 'pending') ? 2000 : false,
  })
  const runs = useMemo(() => runsQuery.data ?? [], [runsQuery.data])

  const runQuery = useQuery({
    queryKey: thesisKeys.run(selectedRunId),
    queryFn: () => fetchRun(selectedRunId as number),
    enabled: selectedRunId != null,
  })

  useEffect(() => {
    if (runsQuery.error) fail(runsQuery.error)
  }, [runsQuery.error, fail])

  const refreshRuns = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: runsKey })
  }, [queryClient, runsKey])

  /** Put the server's answer for one run into the cached list right away, then refetch. */
  const patchRun = useCallback(
    (summary: RunSummary) =>
      queryClient.setQueryData<RunSummary[]>(runsKey, (prev) =>
        prev?.map((r) => (r.run_id === summary.run_id ? summary : r)),
      ),
    [queryClient, runsKey],
  )

  const createMutation = useMutation({
    mutationFn: (config: RunCreateInput) => apiCreateRun(sectionId as number, config),
    onSuccess: (detail) => setSelectedRunId(detail.id),
    onError: fail,
    onSettled: refreshRuns,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiDeleteRun(id),
    // Optimistic: the backend cascade runs in the background.
    onMutate: (id) => {
      queryClient.setQueryData<RunSummary[]>(runsKey, (prev) => prev?.filter((r) => r.run_id !== id))
      setSelectedRunId((cur) => (cur === id ? null : cur))
    },
    onError: fail,
    onSettled: refreshRuns,
  })

  const controlMutation = useMutation({
    mutationFn: ({ action }: { id: number; action: () => Promise<RunSummary> }) => action(),
    onSuccess: patchRun,
    onError: fail,
    onSettled: refreshRuns,
  })

  const control = useCallback(
    (id: number, action: () => Promise<RunSummary>) => controlMutation.mutateAsync({ id, action }).then(() => undefined, () => undefined),
    [controlMutation],
  )

  const createRun = useCallback(
    async (config: RunCreateInput) => {
      if (sectionId == null) return
      setError(null)
      await createMutation.mutateAsync(config).catch(() => undefined)
    },
    [sectionId, createMutation],
  )
  const deleteRun = useCallback((id: number) => deleteMutation.mutateAsync(id).catch(() => undefined), [deleteMutation])
  const stopRun = useCallback((id: number) => control(id, () => apiStopRun(id)), [control])
  const pauseRun = useCallback((id: number) => control(id, () => apiPauseRun(id)), [control])
  const resumeRun = useCallback((id: number) => control(id, () => apiResumeRun(id)), [control])
  const setSpeed = useCallback((id: number, speed: number | null) => control(id, () => apiSetRunSpeed(id, speed)), [control])

  const selectedRun = useMemo(() => runs.find((r) => r.run_id === selectedRunId) ?? null, [runs, selectedRunId])

  return {
    runs,
    selectedRunId,
    setSelectedRunId,
    selectedRun,
    activeRun: runQuery.data ?? null,
    busy: createMutation.isPending || controlMutation.isPending,
    error,
    clearError: () => setError(null),
    createRun,
    deleteRun,
    stopRun,
    pauseRun,
    resumeRun,
    setSpeed,
    refreshRuns,
  }
}
