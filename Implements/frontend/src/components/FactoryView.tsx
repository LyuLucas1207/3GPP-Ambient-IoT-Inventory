import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/lib/Plot'
import { DeviceVizState, type Snapshot, type StaticDevice } from '@/types/simulation'

const BAY_X = 120
const BAY_Y = 60
/** Vertical axis: 1/4 of the plot from the left. Horizontal axis: 1/4 from the bottom. */
const AXIS_FROM_LEFT = 0.15
const AXIS_FROM_BOTTOM = 0.15

const COLORS: Record<DeviceVizState, string> = {
  [DeviceVizState.OFF]: '#7a8490',
  [DeviceVizState.ON]: '#5aa7ff',
  [DeviceVizState.SLEEP]: '#b086ff',
  [DeviceVizState.ACCESS]: '#f0a202',
  [DeviceVizState.COLLISION]: '#e05656',
  [DeviceVizState.DONE]: '#3dce8b',
}

interface Props {
  devices: StaticDevice[]
  snapshot: Snapshot | null
  reader: { x: number; y: number }
  selectedId: number | null
  onSelect: (id: number) => void
  pad: { top: number; right: number; bottom: number; left: number }
}

export function FactoryView({ devices, snapshot, reader, selectedId, onSelect, pad }: Props) {
  const { t, i18n } = useTranslation()
  const plot = usePlotTheme()
  const data = useMemo(() => {
    const states = snapshot?.state ?? devices.map(() => DeviceVizState.OFF)
    const colors = devices.map((d, i) =>
      d.id === selectedId ? '#ffffff' : COLORS[states[i] ?? DeviceVizState.OFF],
    )
    const sizes = devices.map((d) => (d.id === selectedId ? 11 : 7))
    const customdata = devices.map((d, i) => [
      d.id,
      t(`state.${states[i] ?? DeviceVizState.OFF}`),
      snapshot?.energy_nj[i] ?? 0,
      d.pin_dbm,
      d.harvest_power_nw,
    ])
    return [
      {
        type: 'scatter' as const,
        mode: 'markers' as const,
        name: t('factory.devices'),
        x: devices.map((d) => d.x),
        y: devices.map((d) => d.y),
        marker: { size: sizes, color: colors, line: { width: 0 } },
        customdata,
        hovertemplate: t('factory.deviceHover'),
      },
      {
        type: 'scatter' as const,
        mode: 'markers+text' as const,
        name: t('factory.reader'),
        x: [reader.x],
        y: [reader.y],
        marker: { size: 18, color: '#c9a227', symbol: 'star' },
        text: [t('factory.reader')],
        textposition: 'top center',
        hovertemplate: `${t('factory.readerHover')}<extra></extra>`,
      },
    ]
  }, [devices, snapshot, reader, selectedId, t, i18n.language])

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
          uirevision: 'factory-bay',
          xaxis: {
            ...axisLine,
            range: [0, BAY_X],
            anchor: 'free',
            position: AXIS_FROM_BOTTOM,
            tickmode: 'linear',
            dtick: 20,
            title: { text: t('factory.xAxis'), standoff: 6, font: { size: 12, color: plot.font } },
          },
          yaxis: {
            ...axisLine,
            range: [0, BAY_Y],
            anchor: 'free',
            position: AXIS_FROM_LEFT,
            tickmode: 'linear',
            dtick: 10,
            title: { text: t('factory.yAxis'), standoff: 6, font: { size: 12, color: plot.font } },
          },
          font: { color: plot.font, size: 11 },
          showlegend: false,
          autosize: true,
        }}
        useResizeHandler
        style={{ width: '100%', height: '100%', cursor: 'grab' }}
        config={{
          displayModeBar: false,
          scrollZoom: true,
          doubleClick: 'reset',
          responsive: true,
          displaylogo: false,
        }}
        onClick={(ev: { points?: Array<{ customdata?: unknown }> }) => {
          const raw = ev.points?.[0]?.customdata
          const id = Array.isArray(raw) ? raw[0] : raw
          if (typeof id === 'number') onSelect(id)
        }}
      />
    </div>
  )
}

export const STATE_COLORS = COLORS

/** Paper energy/protocol names vs factory-only snapshot overlays. */
export const STATE_SOURCE: Record<DeviceVizState, 'paper' | 'viz'> = {
  [DeviceVizState.OFF]: 'paper',
  [DeviceVizState.ON]: 'paper',
  [DeviceVizState.SLEEP]: 'paper',
  [DeviceVizState.ACCESS]: 'viz',
  [DeviceVizState.COLLISION]: 'viz',
  [DeviceVizState.DONE]: 'paper',
}
