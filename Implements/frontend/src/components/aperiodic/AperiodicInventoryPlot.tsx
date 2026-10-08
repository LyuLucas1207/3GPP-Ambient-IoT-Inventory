import { PaperRef } from '@/components/aperiodic/PaperRef'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { axis, baseLayout, MATLAB, PLOT_CONFIG } from '@/components/aperiodic/plotLayout'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/lib/Plot'
import type { AperiodicSimulationResult } from '@/types/aperiodicSimulation'
import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'

export function AperiodicInventoryPlot({ result, time }: { result: AperiodicSimulationResult; time?: number | null }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const data = useMemo(() => {
    const c = result.curve
    const out: Array<Record<string, unknown>> = []
    if (c.p05 && c.p95) {
      out.push({ x: c.times, y: c.p95, type: 'scatter', mode: 'lines', line: { width: 0 }, showlegend: false, hoverinfo: 'skip' })
      out.push({
        x: c.times,
        y: c.p05,
        type: 'scatter',
        mode: 'lines',
        fill: 'tonexty',
        fillcolor: 'rgba(0,114,189,0.15)',
        line: { width: 0 },
        name: t('ap.plots.band'),
      })
    }
    out.push({
      x: c.times,
      y: c.ratio,
      type: 'scatter',
      mode: 'lines',
      line: { color: result.config.paging_mode === 'periodic' ? MATLAB.red : MATLAB.yellow, width: 2.4 },
      name: t(`ap.terms.${result.config.paging_mode === 'periodic' ? 'periodicBaseline' : 'aperiodic'}`),
    })
    for (const q of [50, 90, 99] as const) {
      const v = result.metrics[`T${q}`]
      if (v != null)
        out.push({
          x: [v, v],
          y: [0, q],
          type: 'scatter',
          mode: 'lines',
          line: { color: plot.line, width: 1, dash: 'dot' },
          name: `T${q} = ${v.toFixed(1)} s`,
        })
    }
    return out
  }, [result, t, plot.line])
  const episodes = result.episodes ?? 1
  return (
    <Card plain size="sm" className="flex h-full min-h-0 flex-col">
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          {t('ap.plots.inventoryTitle')} <PaperRef id="inventory" />
        </CardTitle>
        <CardDescription>
          {t('ap.plots.inventorySubtitle', { n: result.metrics.n_eff, episodes })}
        </CardDescription>
      </CardHeader>
      <CardContent className="min-h-40 flex-1">
        <Plot
          data={data}
          layout={baseLayout(plot, {
            margin: { t: 8, r: 12, b: 36, l: 48 },
            xaxis: axis(plot, t('ap.plots.time')),
            yaxis: axis(plot, t('ap.plots.ratio'), { range: [0, 102] }),
            shapes:
              time != null
                ? [{ type: 'line', x0: time, x1: time, y0: 0, y1: 102, line: { color: plot.font, width: 1.5, dash: 'dot' } }]
                : [],
            uirevision: result.run_id,
          })}
          useResizeHandler
          style={{ width: '100%', height: '100%' }}
          config={PLOT_CONFIG}
        />
      </CardContent>
    </Card>
  )
}
