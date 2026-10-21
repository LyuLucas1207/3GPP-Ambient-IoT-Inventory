import { X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import Plot from '@/lib/Plot'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { Placement, Timeline } from '@/types/thesis'

const STATE_ORDER = [
  'charging',
  'on',
  'missed_page',
  'latched',
  'm1_tx',
  'm1_empty',
  'm1_collision',
  'm1_success',
  'ebi_received',
  'm2_tx',
  'm3_rx',
  'identified',
  'removed',
  'died',
  'dropped',
] as const

export function PlacementTimeline({
  open,
  placement,
  loader,
  onClose,
}: {
  open: boolean
  placement: Placement | null
  loader: (deviceId: number) => Promise<Timeline | null>
  onClose: () => void
}) {
  const { t } = useTranslation()
  const [timeline, setTimeline] = useState<Timeline | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open || !placement || typeof placement.id !== 'number' || placement.kind !== 'device') {
      setTimeline(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setTimeline(null)
    void (async () => {
      const tl = await loader(placement.id as number)
      if (cancelled) return
      setTimeline(tl)
      setLoading(false)
    })()
    return () => {
      cancelled = true
    }
  }, [open, placement, loader])

  if (!open || !placement) return null

  const title = placement.kind === 'device'
    ? t('thesis.timeline.titleDevice', { id: placement.id, subtype: placement.subtype ?? '' })
    : t('thesis.timeline.titleReader', { id: placement.id })
  const supported = placement.kind === 'device' && typeof placement.id === 'number'

  return (
    <div className="pointer-events-none fixed inset-0 z-40 flex items-stretch justify-end">
      <button
        type="button"
        className="pointer-events-auto absolute inset-0 cursor-default bg-background/40"
        aria-label={t('thesis.timeline.close')}
        onClick={onClose}
      />
      <aside className="pointer-events-auto relative flex h-full w-[min(640px,calc(100vw-16px))] flex-col overflow-hidden border-l bg-card shadow-xl">
        <header className="flex shrink-0 items-center justify-between gap-2 border-b px-3 py-2">
          <h2 className="text-sm font-medium">{title}</h2>
          <Button type="button" size="icon-sm" variant="ghost" onClick={onClose} aria-label={t('thesis.timeline.close')}>
            <X />
          </Button>
        </header>
        <div className="flex min-h-0 flex-1 flex-col">
          {!supported ? (
            <p className="p-4 text-sm text-muted-foreground">{t('thesis.timeline.unsupported')}</p>
          ) : loading ? (
            <p className="p-4 text-sm text-muted-foreground">{t('thesis.timeline.loading')}</p>
          ) : timeline == null ? (
            <p className="p-4 text-sm text-muted-foreground">{t('thesis.timeline.noEvents')}</p>
          ) : (
            <>
              <div className="shrink-0 p-2">
                <TimelinePlot timeline={timeline} />
              </div>
              <div className="min-h-0 flex-1 border-t">
                <ScrollArea className="h-full">
                  <table className="w-full text-xs">
                    <thead className="sticky top-0 bg-card">
                      <tr className="text-left text-muted-foreground">
                        <th className="px-2 py-1">{t('thesis.timeline.col.t')}</th>
                        <th className="px-2 py-1">{t('thesis.timeline.col.event')}</th>
                        <th className="px-2 py-1">{t('thesis.timeline.col.reader')}</th>
                        <th className="px-2 py-1">{t('thesis.timeline.col.cause')}</th>
                        <th className="px-2 py-1">{t('thesis.timeline.col.energy')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {timeline.events.map((event) => (
                        <tr key={event.id} className="border-t">
                          <td className="px-2 py-1 tabular-nums">{event.t_s.toFixed(4)}</td>
                          <td className="px-2 py-1 font-mono text-[11px]">{event.event_type}</td>
                          <td className="px-2 py-1 tabular-nums">{event.reader_id ?? '—'}</td>
                          <td className="px-2 py-1">{event.cause ?? ''}</td>
                          <td className="px-2 py-1 tabular-nums">{event.energy_j != null ? event.energy_j.toExponential(2) : ''}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </ScrollArea>
              </div>
            </>
          )}
        </div>
      </aside>
    </div>
  )
}

function TimelinePlot({ timeline }: { timeline: Timeline }) {
  const { t } = useTranslation()
  const stateIndex = (name: string) => {
    const idx = STATE_ORDER.indexOf(name as (typeof STATE_ORDER)[number])
    return idx === -1 ? STATE_ORDER.length : idx
  }
  const xs = timeline.events.map((e) => e.t_s)
  const states = timeline.events.map((e) => stateIndex(e.event_type))
  const hoverText = timeline.events.map(
    (e) => `${e.event_type}${e.cause ? ` · ${e.cause}` : ''}${e.reader_id != null ? ` · reader ${e.reader_id}` : ''}`,
  )
  const energyXs = timeline.energy_series.map(([x]) => x)
  const energyYs = timeline.energy_series.map(([, y]) => y)
  return (
    <Plot
      data={[
        {
          x: xs,
          y: states,
          mode: 'lines+markers',
          line: { shape: 'hv' },
          marker: { size: 6 },
          name: 'state',
          hovertext: hoverText,
          hovertemplate: 't=%{x:.4f}s<br>%{hovertext}<extra></extra>',
          type: 'scattergl',
        },
        {
          x: energyXs,
          y: energyYs,
          mode: 'lines',
          name: 'energy (J)',
          yaxis: 'y2',
          line: { dash: 'dot' },
          type: 'scattergl',
        },
      ]}
      layout={{
        margin: { l: 110, r: 60, t: 10, b: 32 },
        height: 260,
        showlegend: false,
        xaxis: { title: { text: t('thesis.timeline.axis.t') } },
        yaxis: {
          title: { text: t('thesis.timeline.axis.state') },
          tickmode: 'array',
          tickvals: STATE_ORDER.map((_, i) => i),
          ticktext: STATE_ORDER as unknown as string[],
        },
        yaxis2: {
          overlaying: 'y',
          side: 'right',
          title: { text: t('thesis.timeline.axis.energy') },
          tickformat: '.1e',
        },
      }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: '100%' }}
    />
  )
}
