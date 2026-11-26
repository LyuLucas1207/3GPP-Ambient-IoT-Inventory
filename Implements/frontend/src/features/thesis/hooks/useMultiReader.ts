import { useQuery } from '@tanstack/react-query'
import { fetchDeviceMetrics, fetchInterference, postTerminationReplay } from '@/apis/thesisRuns'
import { fetchPolicies, fetchTrainingExperiment, fetchTrainingExperiments } from '@/apis/thesisTraining'
import { thesisKeys } from '@/features/thesis/lib/thesisQueryKeys'
import type { RunStatus, TerminationSpec } from '@/features/thesis/types'

const LIVE: RunStatus[] = ['pending', 'running']

/** Coordination grants, per-reader interference counters and per-frame losses of a run. */
export function useInterference(runId: number | null, status: RunStatus | string | null) {
  const live = LIVE.includes(status as RunStatus)
  return useQuery({
    queryKey: thesisKeys.interference(runId ?? -1, String(status ?? '')),
    queryFn: () => fetchInterference(runId as number),
    enabled: runId != null,
    staleTime: live ? 0 : Infinity,
    refetchInterval: live ? 3000 : false,
  })
}

/** Per-device diagnostics; written when the run ends, so only fetched for finished runs. */
export function useDeviceMetrics(runId: number | null, status: RunStatus | string | null) {
  const finished = status != null && !LIVE.includes(status as RunStatus)
  return useQuery({
    queryKey: thesisKeys.deviceMetrics(runId ?? -1, String(status ?? '')),
    queryFn: () => fetchDeviceMetrics(runId as number),
    enabled: runId != null && finished,
    staleTime: Infinity,
  })
}

export function useTerminationReplay(runId: number | null, rules: TerminationSpec[], enabled = true) {
  const key = JSON.stringify(rules)
  return useQuery({
    queryKey: thesisKeys.terminationReplay(runId ?? -1, key),
    queryFn: () => postTerminationReplay(runId as number, rules),
    enabled: enabled && runId != null && rules.length > 0,
    staleTime: Infinity,
  })
}

export function usePolicies() {
  return useQuery({ queryKey: thesisKeys.policies, queryFn: fetchPolicies, staleTime: 30_000 })
}

export function useTrainingExperiments() {
  return useQuery({ queryKey: thesisKeys.trainingExperiments, queryFn: fetchTrainingExperiments, refetchInterval: 10_000 })
}

export function useTrainingExperiment(name: string | null) {
  return useQuery({
    queryKey: thesisKeys.trainingExperiment(name),
    queryFn: () => fetchTrainingExperiment(name as string),
    enabled: name != null,
    refetchInterval: 10_000,
  })
}
