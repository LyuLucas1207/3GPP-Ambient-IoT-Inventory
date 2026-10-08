import { STATE_COLORS } from '@/components/aperiodic/plotLayout'
import { Segmented } from '@/components/aperiodic/Segmented'
import { cn } from '@/lib/utils'
import type { StepDeviceRound, StepDeviceStatic, StepRound } from '@/types/aperiodicSimulation'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { FATE_TONE, activeInPhase, phaseIndex, type StepPhase } from './stepModel'

type Filter = 'all' | 'paged' | 'participants'
const PHYS = ['idle', 'single', 'captured', 'collision'] as const

function EnergyCell({ e, stat }: { e: number | null; stat: StepDeviceStatic | undefined }) {
  if (e == null || !stat) return <span className="text-muted-foreground">—</span>
  const frac = Math.min(Math.max((e - stat.E_low_uJ) / Math.max(stat.E_up_uJ - stat.E_low_uJ, 1e-9), 0), 1)
  return (
    <div className="flex items-center gap-1" title={`E = ${e.toFixed(3)} µJ (E_low ${stat.E_low_uJ.toFixed(2)}, E_up ${stat.E_up_uJ.toFixed(2)})`}>
      <div className="h-1.5 w-10 overflow-hidden rounded-full bg-muted">
        <div className={cn('h-full', frac < 0.15 ? 'bg-red-500' : 'bg-emerald-500')} style={{ width: `${frac * 100}%` }} />
      </div>
      <span className="font-mono">{e.toFixed(2)}</span>
    </div>
  )
}

function StateCell({ s }: { s: string }) {
  const { t } = useTranslation()
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap">
      <i className="size-2 rounded-full" style={{ background: STATE_COLORS[s] ?? '#888' }} />
      {t(`ap.states.${s}`, { defaultValue: s })}
    </span>
  )
}

export function StepDeviceTable({
  r,
  phase,
  statics,
  selectedId,
  onSelect,
}: {
  r: StepRound
  phase: StepPhase
  statics: StepDeviceStatic[]
  selectedId: number | null
  onSelect: (id: number) => void
}) {
  const { t } = useTranslation()
  const [filter, setFilter] = useState<Filter>('all')
  const pi = phaseIndex(phase)
  const at = (p: StepPhase) => pi >= phaseIndex(p)
  const byId = new Map(statics.map((s) => [s.id, s]))
  const rows = r.devices.filter((d) =>
    filter === 'all' ? true : filter === 'paged' ? d.paged_via != null : d.access === 'transmit',
  )

  const eiCell = (d: StepDeviceRound) => {
    if (d.access !== 'transmit') return ''
    return d.msg2_index != null ? `✓ #${d.msg2_index + 1}` : '✗'
  }
  const msg2Cell = (d: StepDeviceRound) => {
    if (d.msg2_index == null) return ''
    if (d.fate === 'capture_loss') return t('ap.step.foreignRn16')
    return t('ap.step.ownRn16')
  }

  return (
    <div className="grid min-h-0 gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Segmented<Filter>
          value={filter}
          onChange={setFilter}
          options={[
            { value: 'all', label: t('ap.step.filterAll', { n: r.devices.length }) },
            { value: 'paged', label: t('ap.step.filterPaged', { n: r.counts.paged }) },
            { value: 'participants', label: t('ap.step.filterPart', { n: r.counts.participants }) },
          ]}
        />
        <span className="text-[10px] text-muted-foreground">{t('ap.step.tableHint')}</span>
      </div>
      <div className="overflow-auto rounded-md border">
        <table className="w-full text-[11px]">
          <thead className="sticky top-0 z-10 bg-card text-muted-foreground">
            <tr className="[&>th]:px-1.5 [&>th]:py-1 [&>th]:text-left [&>th]:font-normal [&>th]:whitespace-nowrap">
              <th>ID</th>
              <th>{t('ap.step.col.type')}</th>
              <th>{t('ap.step.col.before')}</th>
              <th>E (µJ)</th>
              {at('paging') && <th>{t('ap.step.col.paged')}</th>}
              {at('access') && <th>{t('ap.step.col.access')}</th>}
              {at('msg1') && <th>{t('ap.step.col.ao')}</th>}
              {at('ei') && <th>EI</th>}
              {at('msg2') && <th>Msg2</th>}
              {at('msg3') && <th>Msg3</th>}
              {at('after') && <th>{t('ap.step.col.fate')}</th>}
              {at('after') && <th>{t('ap.step.col.after')}</th>}
              {at('after') && <th>E (µJ)</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((d) => {
              const active = activeInPhase(phase, d)
              return (
                <tr
                  key={d.id}
                  onClick={() => d.paged_via != null && onSelect(d.id)}
                  className={cn(
                    'border-t border-border/50 [&>td]:px-1.5 [&>td]:py-0.5 [&>td]:whitespace-nowrap',
                    d.paged_via != null && 'cursor-pointer hover:bg-muted/60',
                    active ? 'bg-fuchsia-500/8' : 'opacity-60',
                    selectedId === d.id && 'bg-fuchsia-500/20 opacity-100',
                  )}
                >
                  <td className="font-mono">{d.id}</td>
                  <td>{d.type}</td>
                  <td>
                    <StateCell s={d.before.state} />
                  </td>
                  <td>
                    <EnergyCell e={d.before.E_uJ} stat={byId.get(d.id)} />
                  </td>
                  {at('paging') && (
                    <td>
                      {d.paged_via ? t(`ap.step.via.${d.paged_via}`) : '—'}
                      {d.page?.depleted && <span className="ml-1 text-red-600">E&lt;E_low</span>}
                    </td>
                  )}
                  {at('access') && (
                    <td className={d.access === 'reject' ? 'text-muted-foreground' : ''}>
                      {d.access ? t(`ap.step.access.${d.access}`) : ''}
                    </td>
                  )}
                  {at('msg1') && (
                    <td className="font-mono">
                      {d.ao ? (
                        <span title={t(`ap.cbra.phys.${PHYS[d.ao.physical]}`)}>
                          (t{d.ao.slot + 1}, f{d.ao.freq + 1}) {t(`ap.cbra.phys.${PHYS[d.ao.physical]}`)}
                          {d.ao.occupancy > 1 ? ` ×${d.ao.occupancy}` : ''}
                        </span>
                      ) : (
                        ''
                      )}
                    </td>
                  )}
                  {at('ei') && <td className="font-mono">{eiCell(d)}</td>}
                  {at('msg2') && <td>{msg2Cell(d)}</td>}
                  {at('msg3') && <td>{d.fate === 'success' ? '✓ ID' : d.fate === 'depleted' && d.depleted_stage === 'msg3' ? t('ap.tf.msg3Lost') : ''}</td>}
                  {at('after') && (
                    <td className={cn(FATE_TONE[d.fate ?? ''] ?? '')}>{d.fate ? t(`ap.step.fate.${d.fate}`) : '—'}</td>
                  )}
                  {at('after') && (
                    <td>
                      <StateCell s={d.after.state} />
                    </td>
                  )}
                  {at('after') && (
                    <td>
                      <EnergyCell e={d.after.E_uJ} stat={byId.get(d.id)} />
                    </td>
                  )}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
