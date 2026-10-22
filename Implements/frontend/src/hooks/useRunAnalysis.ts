import { useQueries } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchRunAnalysis } from '@/api/thesisRuns'
import { thesisKeys } from '@/lib/thesisQueryKeys'
import type { RunAnalysis, RunSummary } from '@/types/thesis'

function explain(err: unknown, t: (key: string) => string): string {
  const raw = err instanceof Error ? err.message : 'request_failed'
  if (raw === 'Failed to fetch') return t('thesis.errors.network')
  const key = `thesis.errors.${raw}`
  const translated = t(key)
  return translated === key ? raw : translated
}

/**
 * Analysis bundles of the selected runs, one TanStack query per run. The run's
 * status is part of the key, so a run that finishes (or is resumed) is
 * refetched automatically while unchanged runs stay cached.
 */
export function useRunAnalysis(runs: RunSummary[], selectedRunIds: ReadonlySet<number>) {
  const { t } = useTranslation()
  const [dismissed, setDismissed] = useState<unknown>(null)
  const statusOf = useMemo(() => new Map(runs.map((r) => [r.run_id, r.status])), [runs])
  const ids = useMemo(() => Array.from(selectedRunIds).filter((id) => statusOf.has(id)), [selectedRunIds, statusOf])

  const results = useQueries({
    queries: ids.map((id) => ({
      queryKey: thesisKeys.analysis(id, statusOf.get(id) ?? ''),
      queryFn: () => fetchRunAnalysis(id),
    })),
  })

  const analyses = useMemo(() => {
    const out: Record<number, RunAnalysis> = {}
    for (const r of results) if (r.data) out[r.data.run_id] = r.data
    return out
  }, [results])
  const firstError = results.find((r) => r.error)?.error ?? null

  return {
    analyses,
    loading: results.some((r) => r.isLoading),
    error: firstError && firstError !== dismissed ? explain(firstError, t) : null,
    clearError: () => setDismissed(firstError),
    getAnalysis: (id: number): RunAnalysis | undefined => analyses[id],
  }
}
