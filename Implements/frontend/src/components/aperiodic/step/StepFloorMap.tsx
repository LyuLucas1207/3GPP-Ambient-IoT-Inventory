import { MATLAB, STATE_COLORS, warehouseOutline } from '@/components/aperiodic/plotLayout'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/lib/Plot'
import type { AperiodicPaperConfig, StepDeviceRound, StepDeviceStatic, StepRound } from '@/types/aperiodicSimulation'
import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { activeInPhase, type StepPhase } from './stepModel'

const STAGE_ORDER = ['paging', 'msg1', 'ei', 'msg2', 'msg3']
const PHASE_STAGE: Partial<Record<StepPhase, number>> = { paging: 0, access: 0, msg1: 1, ei: 2, msg2: 3, msg3: 4 }

/** Power state of a device while the round is in the given sub-step (same colours as the factory floor). */
function phaseState(p: StepPhase, d: StepDeviceRound): string {
  if (p === 'before') return d.before.state
  if (p === 'after' || d.paged_via == null) return p === 'after' ? d.after.state : d.before.state
  const stage = PHASE_STAGE[p] ?? 0
  if (d.depleted_stage && STAGE_ORDER.indexOf(d.depleted_stage) <= stage) return 'OFF'
  if (p === 'paging') return 'RX'
  if (d.access !== 'transmit') return d.after.state
  switch (p) {
    case 'access':
    case 'msg1':
      return 'TX'
    case 'ei':
      return 'RX'
    case 'msg2':
      return d.msg2_index != null ? 'RX' : d.after.state
    case 'msg3':
      return d.fate === 'success' ? 'TX' : d.after.state
  }
  return d.before.state
}

interface Props {
  r: StepRound | null
  phase: StepPhase
  statics: StepDeviceStatic[]
  initialStates: string[]
  paper: AperiodicPaperConfig | null
  selectedId: number | null
  onSelect: (id: number) => void
}

/** Factory floor of the step session (paper Sec. V-A layout), coloured by device state in the current sub-step. */
export function StepFloorMap({ r, phase, statics, initialStates, paper, selectedId, onSelect }: Props) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const [W, H] = paper?.layout.factory_m ?? [120, 60]

  const data = useMemo(() => {
    const byId = new Map(r?.devices.map((d) => [d.id, d]) ?? [])
    const rows = statics.map((s, i) => {
      const d = byId.get(s.id)
      const state = d ? phaseState(phase, d) : (initialStates[i] ?? 'OFF')
      return { s, d, state, active: d ? activeInPhase(phase, d) : false }
    })
    const out: Array<Record<string, unknown>> = []
    if (paper) {
      out.push({
        type: 'scatter',
        mode: 'markers',
        x: paper.layout.bs_xy.map((p) => p[0]),
        y: paper.layout.bs_xy.map((p) => p[1]),
        marker: { symbol: 'triangle-up', size: 10, color: plot.font, opacity: 0.55 },
        hovertemplate: `${t('ap.factory.bs')}<extra></extra>`,
      })
    }
    out.push({
      type: 'scatter',
      mode: 'markers',
      x: rows.map((o) => o.s.x),
      y: rows.map((o) => o.s.y),
      customdata: rows.map((o) => [
        o.s.id,
        t(`ap.states.${o.state}`, { defaultValue: o.state }),
        o.s.type,
        o.d?.fate ? t(`ap.step.fate.${o.d.fate}`, { defaultValue: o.d.fate }) : '—',
      ]),
      marker: {
        size: rows.map((o) => (o.s.id === selectedId ? 14 : o.active ? 11 : 7)),
        color: rows.map((o) => STATE_COLORS[o.state] ?? '#888'),
        opacity: rows.map((o) => (o.active || o.s.id === selectedId || phase === 'before' ? 1 : 0.55)),
        line: {
          width: rows.map((o) => (o.s.id === selectedId ? 3 : o.active ? 1.5 : 0)),
          color: rows.map((o) => (o.s.id === selectedId ? MATLAB.yellow : '#d946ef')),
        },
      },
      hovertemplate: t('ap.step.mapHover'),
    })
    if (paper) {
      out.push({
        type: 'scatter',
        mode: 'markers+text',
        x: [paper.layout.reader_xy[0]],
        y: [paper.layout.reader_xy[1]],
        marker: { size: 16, color: '#c9a227', symbol: 'star' },
        text: [t('ap.factory.reader')],
        textposition: 'top center',
        hovertemplate: `${t('ap.factory.reader')}<extra></extra>`,
      })
    }
    return out
  }, [r, phase, statics, initialStates, paper, selectedId, plot.font, t])

  const axis = {
    showline: true,
    linewidth: 1,
    linecolor: plot.font,
    gridcolor: plot.grid,
    zeroline: false,
    tickfont: { size: 10, color: plot.font },
    tickmode: 'linear' as const,
  }

  const legend = ['OFF', 'MONITOR', 'RX', 'TX', 'INTRA_ROUND_SLEEP', 'INTERROUND_SYNC_SLEEP', 'DONE']

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="min-h-0 flex-1">
        <Plot
          data={data}
          layout={{
            margin: { t: 6, r: 8, b: 30, l: 34 },
            paper_bgcolor: plot.paper,
            plot_bgcolor: plot.plot,
            dragmode: 'pan',
            hovermode: 'closest',
            uirevision: 'ap-step-floor',
            shapes: [warehouseOutline(W, H, plot.font)],
            xaxis: { ...axis, range: [0, W], dtick: 20, constrain: 'domain', title: { text: t('ap.factory.xAxis'), standoff: 2, font: { size: 10, color: plot.font } } },
            yaxis: { ...axis, range: [0, H], dtick: 10, scaleanchor: 'x', scaleratio: 1, constrain: 'domain' },
            font: { color: plot.font, size: 10 },
            showlegend: false,
            autosize: true,
          }}
          useResizeHandler
          style={{ width: '100%', height: '100%' }}
          config={{ displayModeBar: false, scrollZoom: true, doubleClick: 'reset', responsive: true, displaylogo: false }}
          onClick={(ev: { points?: Array<{ customdata?: unknown }> }) => {
            const raw = ev.points?.[0]?.customdata
            const id = Array.isArray(raw) ? raw[0] : raw
            if (typeof id === 'number' && r?.devices.some((d) => d.id === id && d.paged_via != null)) onSelect(id)
          }}
        />
      </div>
      <div className="flex shrink-0 flex-wrap gap-x-3 gap-y-0.5 px-1 pt-1 text-[10px] text-muted-foreground">
        {legend.map((s) => (
          <span key={s} className="flex items-center gap-1">
            <span className="size-2 rounded-full" style={{ background: STATE_COLORS[s] }} />
            {t(`ap.states.${s}`, { defaultValue: s })}
          </span>
        ))}
        <span className="flex items-center gap-1">
          <span className="size-2.5 rounded-full border-[1.5px] border-fuchsia-500" />
          {t('ap.step.mapActive')}
        </span>
      </div>
    </div>
  )
}
