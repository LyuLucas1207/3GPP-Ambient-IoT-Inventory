import type { LegendItem } from '@/components/ChartLegend'
import type { TFunction } from 'i18next'

export const SCIENTIFIC_STATE_FILL: Record<string, string> = {
  OFF: 'rgba(90, 167, 255, 0.14)',
  ON: 'rgba(240, 162, 2, 0.16)',
  SLEEP: 'rgba(176, 134, 255, 0.16)',
  TX: 'rgba(224, 86, 86, 0.16)',
  DONE: 'rgba(61, 206, 139, 0.14)',
}

export const SCIENTIFIC_STATE_SWATCH: Record<string, string> = {
  OFF: 'rgba(90, 167, 255, 0.7)',
  ON: 'rgba(240, 162, 2, 0.8)',
  SLEEP: 'rgba(176, 134, 255, 0.8)',
  TX: 'rgba(224, 86, 86, 0.8)',
  DONE: 'rgba(61, 206, 139, 0.8)',
}

const STATES = ['OFF', 'ON', 'SLEEP', 'TX', 'DONE'] as const

export function scientificStateLegendItems(t: TFunction): LegendItem[] {
  return STATES.map((st) => ({
    id: `bg-${st}`,
    label: t(`energy.state.${st}`),
    swatch: SCIENTIFIC_STATE_SWATCH[st],
    helpTitle: t(`energy.state.${st}`),
    helpBody: t(`energy.itemHelp.bg-${st}`),
  }))
}

export const EVENT_MARK: Record<string, { symbol: string; color: string; key: string }> = {
  paging: { symbol: 'circle-open', color: '#ca8a04', key: 'pagingHeard' },
  paging_rejected: { symbol: 'circle-x', color: '#c2410c', key: 'pagingRejected' },
  paging_missed: { symbol: 'circle-dot', color: '#64748b', key: 'pagingMissed' },
  msg1_planned: { symbol: 'triangle-up-open', color: '#d97706', key: 'msg1Planned' },
  msg1: { symbol: 'triangle-up', color: '#f0a202', key: 'msg1Tx' },
  msg1_singleton: { symbol: 'star', color: '#b45309', key: 'msg1Singleton' },
  collision: { symbol: 'x', color: '#e05656', key: 'collision' },
  dropped_before_msg1: { symbol: 'x-thin', color: '#9f1239', key: 'dropped' },
  msg2: { symbol: 'triangle-down', color: '#2563eb', key: 'msg2' },
  msg3_start: { symbol: 'square-open', color: '#a16207', key: 'msg3Start' },
  msg3: { symbol: 'square', color: '#c9a227', key: 'msg3Done' },
  done: { symbol: 'diamond', color: '#16a34a', key: 'done' },
  energy_fail_paging: { symbol: 'hexagon', color: '#b91c1c', key: 'energyFail' },
  energy_fail_msg1: { symbol: 'hexagon', color: '#b91c1c', key: 'energyFail' },
  energy_fail_msg2: { symbol: 'hexagon', color: '#b91c1c', key: 'energyFail' },
  energy_fail_msg3: { symbol: 'hexagon', color: '#b91c1c', key: 'energyFail' },
}

function symbolKind(symbol: string): LegendItem['symbol'] {
  if (symbol.includes('triangle-up')) return 'triangle-up'
  if (symbol.includes('triangle-down')) return 'triangle-down'
  if (symbol.includes('square')) return 'square'
  if (symbol.includes('diamond')) return 'diamond'
  if (symbol === 'x' || symbol.includes('x')) return 'x'
  return undefined
}

export function protocolEventLegendItems(t: TFunction, present: Set<string>): LegendItem[] {
  const items: LegendItem[] = []
  for (const spec of Object.values(EVENT_MARK)) {
    if (!present.has(spec.key) || items.some((x) => x.id === spec.key)) continue
    items.push({
      id: spec.key,
      label: t(`energy.event.${spec.key}`),
      swatch: spec.color,
      symbol: symbolKind(spec.symbol),
      helpTitle: t(`energy.event.${spec.key}`),
      helpBody: t(`energy.itemHelp.${spec.key}`),
    })
  }
  return items
}
