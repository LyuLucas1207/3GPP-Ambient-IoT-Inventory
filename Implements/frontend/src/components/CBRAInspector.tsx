import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Slider } from '@/components/ui/slider'
import { Badge } from '@/components/ui/badge'
import { TermHelp } from '@/components/TermHelp'
import { ExplainButton } from '@/components/ViewExplanationDialog'
import { MathInline } from '@/components/MathText'
import {
  Dialog,
  DialogBackdrop,
  DialogClose,
  DialogDescription,
  DialogPopup,
  DialogPortal,
  DialogTitle,
} from '@/components/ui/dialog'
import { AOStatus, StrategyKey, type AOCell, type PagingEvent, type SimulationResult } from '@/types/simulation'
import { TermId, ViewId } from '@/explain/ids'
import { ChevronLeftIcon, ChevronRightIcon, XIcon } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

interface Props {
  events: PagingEvent[]
  index: number
  setIndex: (i: number) => void
  result: SimulationResult | null
  strategy: StrategyKey
  playbackTimeS: number | null
}

function cellVariant(status: string) {
  if (status === AOStatus.MSG1_SINGLETON || status === AOStatus.SUCCESS) return 'default' as const
  if (status === AOStatus.COLLISION) return 'destructive' as const
  return 'outline' as const
}

function statusKey(status: string) {
  if (status === AOStatus.MSG1_SINGLETON || status === AOStatus.SUCCESS) return 'cbra.singleton'
  if (status === AOStatus.COLLISION) return 'cbra.collision'
  return 'cbra.idle'
}

function ids(list?: number[]) {
  if (!list?.length) return '—'
  return list.map((id) => `#${id}`).join(', ')
}

export function CBRAInspector({ events, index, setIndex, result, strategy, playbackTimeS }: Props) {
  const { t } = useTranslation()
  const ev = events[index]
  const [ao, setAo] = useState<AOCell | null>(null)
  const meta = result?.metadata
  const total = events.length
  const jumpNearest = () => {
    if (playbackTimeS == null || events.length === 0) return
    let best = 0
    let dist = Infinity
    events.forEach((e, i) => {
      const d = Math.abs(e.time_s - playbackTimeS)
      if (d < dist) {
        dist = d
        best = i
      }
    })
    setIndex(best)
  }

  const cells = useMemo(() => {
    if (!ev) return []
    const out: Array<{ kind: 'label'; tAo: number } | { kind: 'cell'; ao: AOCell }> = []
    for (const tAo of [0, 1, 2, 3]) {
      out.push({ kind: 'label', tAo })
      const row = ev.aos.filter((a) => a.time_ao === tAo).sort((a, b) => a.freq_ao - b.freq_ao)
      for (const cell of row) out.push({ kind: 'cell', ao: cell })
    }
    return out
  }, [ev])

  return (
    <Card className="bg-card/90 backdrop-blur-md" size="sm">
      <CardHeader>
        <CardTitle className="inline-flex items-center gap-1">
          {t('cbra.title')}
          <TermHelp term={TermId.Cbra} />
          <TermHelp term={TermId.Ao} />
        </CardTitle>
        <CardAction>
          <ExplainButton view={ViewId.Cbra} />
        </CardAction>
        <CardDescription>{t('cbra.subtitle')}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        <dl className="grid grid-cols-2 gap-x-2 gap-y-1 text-[11px] text-muted-foreground">
          <dt>{t('cbra.metaStrategy')}</dt>
          <dd>{t(`strategy.${strategy}`)}</dd>
          <dt>{t('sim.seed')}</dt>
          <dd>{meta?.seed ?? '—'}</dd>
          <dt>{t('cbra.runId')}</dt>
          <dd className="truncate font-mono" title={result?.run_id ?? meta?.run_id}>
            {result?.run_id ?? meta?.run_id ?? '—'}
          </dd>
          <dt>{t('cbra.grouping')}</dt>
          <dd>{meta?.group_assignment ?? 'even_id_mod'}</dd>
          <dt>{t('cbra.cdf')}</dt>
          <dd className="font-mono">{meta?.cdf?.sha256_12 ?? '—'}</dd>
        </dl>
        {events.length === 0 || ev == null ? (
          <p className="text-sm text-muted-foreground">{t('cbra.empty')}</p>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                type="button"
                size="icon-sm"
                variant="outline"
                disabled={index <= 0}
                aria-label={t('cbra.prev')}
                onClick={() => setIndex(Math.max(0, index - 1))}
              >
                <ChevronLeftIcon />
              </Button>
              <label className="flex items-center gap-1 text-xs">
                {t('cbra.pagingJump')}
                <Input
                  className="h-7 w-16"
                  type="number"
                  min={0}
                  max={Math.max(0, total - 1)}
                  value={ev.paging_index}
                  onChange={(e) => {
                    const n = Number(e.target.value)
                    const i = events.findIndex((p) => p.paging_index === n)
                    if (i >= 0) setIndex(i)
                  }}
                />
              </label>
              <span className="text-xs text-muted-foreground">
                {index + 1} / {total}
              </span>
              <Button
                type="button"
                size="icon-sm"
                variant="outline"
                disabled={index >= total - 1}
                aria-label={t('cbra.next')}
                onClick={() => setIndex(Math.min(total - 1, index + 1))}
              >
                <ChevronRightIcon />
              </Button>
              <Button type="button" size="sm" variant="outline" onClick={jumpNearest}>
                {t('cbra.jumpPlayback')}
              </Button>
            </div>
            <Slider
              min={0}
              max={Math.max(1, total - 1)}
              disabled={total < 2}
              value={[index]}
              onValueChange={(v) => {
                const next = Array.isArray(v) ? v[0] : v
                if (typeof next === 'number') setIndex(next)
              }}
            />
            <p className="text-sm">{t('cbra.paging', { id: ev.paging_index })}</p>
            <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
              <span>
                <MathInline tex="t" /> = {ev.time_s.toFixed(3)} s
              </span>
              {ev.group_index != null ? <span>g={ev.group_index}</span> : null}
              <span className="inline-flex items-center gap-1">
                <MathInline tex="p_{\mathrm{access}}" /> = {ev.p_access.toFixed(3)}
                {ev.p_access_after != null ? ` → ${ev.p_access_after.toFixed(3)}` : ''}
                <TermHelp term={TermId.Paccess} />
              </span>
              <span>
                {t('cbra.onCount', { n: ev.n_on ?? '—' })}
              </span>
              <span className="inline-flex items-center gap-1">
                {t('cbra.eligible', { n: ev.n_eligible })}
                <TermHelp term={TermId.Eligible} />
              </span>
              <span>{t('cbra.heardNoAttempt', { n: ev.n_heard_no_attempt ?? ev.n_eligible - ev.n_attempting })}</span>
              <span>{t('cbra.planned', { n: ev.n_planned_attempts ?? ev.n_attempting })}</span>
              <span>{t('cbra.actualTx', { n: ev.n_actual_tx ?? ev.n_attempting })}</span>
              <span>{t('cbra.aoCounts', { s: ev.success_ao_count, c: ev.collision_ao_count, i: ev.idle_count })}</span>
            </div>
            <div className="grid grid-cols-[2rem_1fr_1fr] gap-1.5" role="grid" aria-label={t('cbra.grid')}>
              <div />
              <div className="text-center text-xs text-muted-foreground">F0</div>
              <div className="text-center text-xs text-muted-foreground">F1</div>
              {cells.map((item) =>
                item.kind === 'label' ? (
                  <div key={`t-${item.tAo}`} className="flex items-center text-xs text-muted-foreground">
                    T{item.tAo}
                  </div>
                ) : (
                  <button
                    type="button"
                    key={item.ao.ao_index}
                    className="rounded-md border border-border p-1.5 text-left outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                    onClick={() => setAo(item.ao)}
                  >
                    <Badge variant={cellVariant(item.ao.status)}>{t(statusKey(item.ao.status))}</Badge>
                    <p className="mt-1 truncate text-[11px] text-muted-foreground">
                      {(item.ao.transmitted_ids ?? item.ao.device_ids).length === 0
                        ? t('cbra.emptyCell')
                        : (item.ao.transmitted_ids ?? item.ao.device_ids).map((id) => `#${id}`).join(', ')}
                    </p>
                  </button>
                ),
              )}
            </div>
          </>
        )}
      </CardContent>
      <Dialog open={ao != null} onOpenChange={(open) => { if (!open) setAo(null) }}>
        <DialogPortal>
          <DialogBackdrop />
          <DialogPopup className="w-[min(440px,calc(100vw-32px))]">
            <div className="flex items-start justify-between gap-3 border-b px-4 py-3">
              <div>
                <DialogTitle>
                  {ao ? `AO T${ao.time_ao} F${ao.freq_ao}` : ''}
                </DialogTitle>
                <DialogDescription>{ao ? t(statusKey(ao.status)) : ''}</DialogDescription>
              </div>
              <DialogClose className="rounded-md p-1 outline-none focus-visible:ring-3 focus-visible:ring-ring/50" aria-label={t('maps.close')}>
                <XIcon className="size-4" />
              </DialogClose>
            </div>
            {ao ? (
              <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 overflow-auto px-4 py-3 text-sm">
                <dt>{t('cbra.plannedIds')}</dt>
                <dd>{ids(ao.planned_ids)}</dd>
                <dt>{t('cbra.txIds')}</dt>
                <dd>{ids(ao.transmitted_ids ?? ao.device_ids)}</dd>
                <dt>{t('cbra.droppedIds')}</dt>
                <dd>{ids(ao.dropped_before_msg1)}</dd>
                <dt>{t('cbra.msg1Result')}</dt>
                <dd>{ao.msg1_result ?? ao.status}</dd>
                <dt>{t('cbra.finalResult')}</dt>
                <dd>{ao.final_result ?? '—'}</dd>
              </dl>
            ) : null}
          </DialogPopup>
        </DialogPortal>
      </Dialog>
    </Card>
  )
}
