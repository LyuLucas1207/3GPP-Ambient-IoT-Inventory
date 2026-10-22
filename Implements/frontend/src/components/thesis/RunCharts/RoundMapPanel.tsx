import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { TimeFrequencyLegend, TimeFrequencyMap } from '@/components/aperiodic/TimeFrequencyMap'
import { fetchRoundSlots } from '@/api/thesisRuns'
import { Slider } from '@/components/ui/slider'
import { thesisKeys } from '@/lib/thesisQueryKeys'
import type { RunRound } from '@/types/thesis'
import { toInspectRound } from './data'

/** Time-frequency map of one round (latest by default) plus its stage counts. */
export function RoundMapPanel({
  runId,
  rounds,
  periodic,
  followKey,
}: {
  runId: number
  rounds: RunRound[]
  periodic: boolean
  /** replay time: whenever it moves, jump back to the latest round at that time */
  followKey: number | null
}) {
  const { t } = useTranslation()
  const ordered = useMemo(() => [...rounds].sort((a, b) => a.t_start_s - b.t_start_s || a.id - b.id), [rounds])
  const [pick, setPick] = useState<number | null>(null) // index into ordered; null = follow latest
  useEffect(() => setPick(null), [followKey])
  const idx = pick == null ? ordered.length - 1 : Math.min(pick, ordered.length - 1)
  const round = idx >= 0 ? ordered[idx] : null

  // A finished round never changes: cache its slot payload for good.
  const slotsQuery = useQuery({
    queryKey: thesisKeys.roundSlots(runId, round?.id ?? -1),
    queryFn: () => fetchRoundSlots(runId, round!.id),
    enabled: round != null,
    staleTime: Infinity,
  })
  const slots = slotsQuery.data ?? null

  if (!round) return <p className="p-2 text-xs text-muted-foreground">{t('thesis.charts.noRounds')}</p>
  const inspect = slots && slots.id === round.id ? toInspectRound(round, slots.slots, periodic) : null

  return (
    <div className="grid h-full content-start gap-2 overflow-auto text-xs">
      <div className="flex items-center gap-2">
        <span className="shrink-0 tabular-nums">
          R#{round.reader_id} · {t('thesis.charts.roundN', { n: round.round_index })} · {round.t_start_s.toFixed(3)}–{round.t_end_s.toFixed(3)} s
        </span>
        <Slider
          className="min-w-32 flex-1"
          min={0}
          max={Math.max(0, ordered.length - 1)}
          step={1}
          value={[idx]}
          onValueChange={(v) => {
            const n = Array.isArray(v) ? v[0] : v
            setPick(n >= ordered.length - 1 ? null : n)
          }}
        />
        <span className="shrink-0 text-muted-foreground">{pick == null ? t('thesis.charts.followLatest') : `${idx + 1}/${ordered.length}`}</span>
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 tabular-nums text-muted-foreground">
        <span>K={round.k_estimate}</span>
        <span>p*={round.pstar?.toFixed(3)}</span>
        <span>{t('thesis.charts.candidates')}: {round.candidates ?? '—'}</span>
        <span>{t('thesis.charts.joiners')}: {round.joiners ?? '—'}</span>
        <span>S/C/E: {round.success_count}/{round.collision_count}/{round.empty_count}</span>
        <span>{t('thesis.charts.budget')}: {round.s_budget ?? '—'}</span>
        <span>{t('thesis.charts.budgetDropped')}: {round.budget_dropped ?? 0}</span>
        <span>{t('thesis.live.identified')}: {round.served ?? 0}</span>
        <span>n̂={round.n_hat != null ? round.n_hat.toFixed(1) : '—'}</span>
        <span>{t('thesis.charts.backlogTrue')}: {round.backlog_true ?? '—'}</span>
      </div>
      {inspect ? (
        <>
          <TimeFrequencyMap r={inspect} />
          <TimeFrequencyLegend />
        </>
      ) : (
        <p className="text-muted-foreground">{t('thesis.timeline.loading')}</p>
      )}
    </div>
  )
}
