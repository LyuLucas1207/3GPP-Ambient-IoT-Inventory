import type { usePlotTheme } from '@/hooks/usePlotTheme'

type Theme = ReturnType<typeof usePlotTheme>

export function baseLayout(plot: Theme, extra: Record<string, unknown> = {}) {
  return {
    margin: { t: 24, r: 12, b: 36, l: 48 },
    paper_bgcolor: plot.paper,
    plot_bgcolor: plot.plot,
    font: { color: plot.font, size: 11 },
    hovermode: 'x unified',
    legend: { orientation: 'h', y: 1.12, yanchor: 'bottom', font: { color: plot.font, size: 10 } },
    autosize: true,
    ...extra,
  }
}

export function axis(plot: Theme, title: string, extra: Record<string, unknown> = {}) {
  return { title: { text: title, standoff: 4 }, gridcolor: plot.grid, color: plot.font, zeroline: false, ...extra }
}

export const PLOT_CONFIG = { displayModeBar: false, responsive: true, scrollZoom: false } as const

export const MATLAB = {
  blue: '#0072bd',
  red: '#d95319',
  yellow: '#edb120',
  purple: '#7e2f8e',
  green: '#77ac30',
  cyan: '#4dbeee',
  maroon: '#a2142f',
}

export const STATE_COLORS: Record<string, string> = {
  OFF: '#71717a',
  MONITOR: '#4dbeee',
  RX: '#0072bd',
  TX: '#d95319',
  INTRA_ROUND_SLEEP: '#edb120',
  INTERROUND_SYNC_SLEEP: '#7e2f8e',
  DONE: '#77ac30',
}

/** Dashed boundary of the W × H m factory hall, drawn under the devices. */
export function warehouseOutline(W: number, H: number, color: string) {
  return {
    type: 'rect' as const,
    xref: 'x' as const,
    yref: 'y' as const,
    x0: 0,
    y0: 0,
    x1: W,
    y1: H,
    layer: 'below' as const,
    line: { color, width: 1.5, dash: 'dash' as const },
    fillcolor: 'rgba(0,0,0,0)',
  }
}

