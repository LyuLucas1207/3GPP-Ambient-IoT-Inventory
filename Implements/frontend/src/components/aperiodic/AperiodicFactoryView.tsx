import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { MATLAB, STATE_COLORS, warehouseOutline } from '@/components/aperiodic/plotLayout'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/lib/Plot'
import type { AperiodicPaperConfig, AperiodicSimulationResult, Snapshot as AperiodicSnapshot } from '@/types/aperiodicSimulation'

const AXIS_FROM_LEFT = 0.15
const AXIS_FROM_BOTTOM = 0.15

interface Props {
  result: AperiodicSimulationResult | null
  paper: AperiodicPaperConfig | null
  snapshot: AperiodicSnapshot | null
  selectedId: number | null
  onSelect: (id: number) => void
  pad: { top: number; right: number; bottom: number; left: number }
}

/** Full-screen factory floor (paper Sec. V-A layout), styled like the periodic page's FactoryView. */
export function AperiodicFactoryView({ result, paper, snapshot, selectedId, onSelect, pad }: Props) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const [W, H] = paper?.layout.factory_m ?? [120, 60]

  const data = useMemo(() => {
    const devices = snapshot ? (result?.devices ?? []) : []
    const codes = result?.state_codes ?? []
    const stateOf = (i: number) => codes[snapshot?.state[i] ?? 0] ?? 'OFF'
    const out: Array<Record<string, unknown>> = []
    if (paper) {
      out.push({
        type: 'scatter',
        mode: 'markers',
        x: paper.layout.bs_xy.map((p) => p[0]),
        y: paper.layout.bs_xy.map((p) => p[1]),
        marker: { symbol: 'triangle-up', size: 11, color: plot.font, opacity: 0.55 },
        hovertemplate: `${t('ap.factory.bs')}<extra></extra>`,
      })
    }
    out.push({
      type: 'scatter',
      mode: 'markers',
      x: devices.map((d) => d.x),
      y: devices.map((d) => d.y),
      customdata: devices.map((d, i) => [d.id, t(`ap.states.${stateOf(i)}`), d.type, d.p_harv_uW]),
      marker: {
        size: devices.map((d) => (d.id === selectedId ? 12 : 7)),
        color: devices.map((d, i) => (d.id === selectedId ? '#ffffff' : (STATE_COLORS[stateOf(i)] ?? '#888'))),
        line: {
          width: devices.map((d) => (d.id === selectedId ? 2 : d.traced ? 1.2 : 0)),
          color: devices.map((d) => (d.id === selectedId ? MATLAB.yellow : plot.font)),
        },
      },
      hovertemplate: t('ap.factory.deviceHover'),
    })
    if (paper) {
      out.push({
        type: 'scatter',
        mode: 'markers+text',
        x: [paper.layout.reader_xy[0]],
        y: [paper.layout.reader_xy[1]],
        marker: { size: 18, color: '#c9a227', symbol: 'star' },
        text: [t('ap.factory.reader')],
        textposition: 'top center',
        hovertemplate: `${t('ap.factory.reader')}<extra></extra>`,
      })
    }
    return out
  }, [result, paper, snapshot, selectedId, plot.font, t])

  const axisLine = {
    ticks: 'outside' as const,
    ticklen: 8,
    tickwidth: 1,
    tickcolor: plot.font,
    showticklabels: true,
    showline: true,
    linewidth: 1.5,
    linecolor: plot.font,
    gridcolor: plot.grid,
    zeroline: false,
    automargin: false,
    fixedrange: false,
    color: plot.font,
    tickfont: { size: 11, color: plot.font },
  }

  return (
    <div className="warehouse-floor absolute inset-0 z-0">
      <Plot
        data={data}
        layout={{
          margin: { t: pad.top, r: pad.right, b: pad.bottom, l: pad.left },
          paper_bgcolor: plot.paper,
          plot_bgcolor: plot.plot,
          dragmode: 'pan',
          hovermode: 'closest',
          uirevision: 'ap-factory-bay',
          shapes: [warehouseOutline(W, H, plot.font)],
          xaxis: {
            ...axisLine,
            range: [0, W],
            anchor: 'free',
            position: AXIS_FROM_BOTTOM,
            tickmode: 'linear',
            dtick: 20,
            title: { text: t('ap.factory.xAxis'), standoff: 6, font: { size: 12, color: plot.font } },
          },
          yaxis: {
            ...axisLine,
            range: [0, H],
            anchor: 'free',
            position: AXIS_FROM_LEFT,
            tickmode: 'linear',
            dtick: 10,
            title: { text: t('ap.factory.yAxis'), standoff: 6, font: { size: 12, color: plot.font } },
          },
          font: { color: plot.font, size: 11 },
          showlegend: false,
          autosize: true,
        }}
        useResizeHandler
        style={{ width: '100%', height: '100%', cursor: 'grab' }}
        config={{ displayModeBar: false, scrollZoom: true, doubleClick: 'reset', responsive: true, displaylogo: false }}
        onClick={(ev: { points?: Array<{ customdata?: unknown }> }) => {
          const raw = ev.points?.[0]?.customdata
          const id = Array.isArray(raw) ? raw[0] : raw
          if (typeof id === 'number') onSelect(id)
        }}
      />
    </div>
  )
}
