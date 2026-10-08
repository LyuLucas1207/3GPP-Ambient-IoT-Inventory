import { PaperRef } from '@/components/aperiodic/PaperRef'
import { Segmented } from '@/components/aperiodic/Segmented'
import { axis, baseLayout, MATLAB, PLOT_CONFIG } from '@/components/aperiodic/plotLayout'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/lib/Plot'
import type { AperiodicSimulationResult, RoundRow } from '@/types/aperiodicSimulation'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

type View = 'action' | 'outcome' | 'reward'

const successOf = (r: RoundRow) => r.S ?? (r.S1 ?? 0) + (r.S2a ?? 0) + (r.S2b ?? 0)

export function RoundControllerPlot({ result }: { result: AperiodicSimulationResult }) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const [view, setView] = useState<View>('action')
  const rows = result.rounds
  const hasPpo = rows.some((r) => r.m != null)
  const x = rows.map((r) => r.round)

  const data = useMemo(() => {
    if (view === 'action') {
      const out: Array<Record<string, unknown>> = [
        { x, y: rows.map((r) => r.L), name: 'L', type: 'scatter', mode: 'lines', line: { color: MATLAB.blue, shape: 'hv' } },
        { x, y: rows.map((r) => r.p), name: 'p', yaxis: 'y2', type: 'scatter', mode: 'lines', line: { color: MATLAB.red, shape: 'hv' } },
      ]
      if (hasPpo) {
        out.push({ x, y: rows.map((r) => r.m ?? null), name: 'm', yaxis: 'y3', type: 'scatter', mode: 'lines', line: { color: MATLAB.green, dash: 'dot' } })
        out.push({ x, y: rows.map((r) => r.q ?? null), name: 'q', yaxis: 'y3', type: 'scatter', mode: 'lines', line: { color: MATLAB.purple, dash: 'dot' } })
      }
      return out
    }
    if (view === 'outcome') {
      const stacked = rows.some((r) => r.S1 != null)
      const succ = stacked
        ? [
            { name: 'S1', y: rows.map((r) => r.S1 ?? 0), color: MATLAB.green },
            { name: 'S2a', y: rows.map((r) => r.S2a ?? 0), color: MATLAB.cyan },
            { name: 'S2b', y: rows.map((r) => r.S2b ?? 0), color: MATLAB.blue },
          ]
        : [{ name: 'S', y: rows.map(successOf), color: MATLAB.green }]
      return [
        ...succ.map((s) => ({ x, y: s.y, name: s.name, type: 'bar', marker: { color: s.color } })),
        { x, y: rows.map((r) => r.idle), name: t('ap.plots.idle'), type: 'bar', marker: { color: '#a1a1aa' } },
        { x, y: rows.map((r) => r.collision), name: t('ap.plots.collision'), type: 'bar', marker: { color: MATLAB.red } },
        {
          x,
          y: rows.map((r) => (r.resource_efficiency ?? successOf(r) / Math.max(r.L * 8, 1)) * 100),
          name: t('ap.plots.re'),
          yaxis: 'y2',
          type: 'scatter',
          mode: 'lines',
          line: { color: MATLAB.purple },
        },
      ]
    }
    return [
      { x, y: rows.map((r) => r.reward), name: t('ap.plots.reward'), type: 'scatter', mode: 'lines', line: { color: MATLAB.blue } },
      { x, y: rows.map((r) => r.C2), name: 'C2', yaxis: 'y2', type: 'scatter', mode: 'lines', line: { color: MATLAB.red, dash: 'dot' } },
    ]
  }, [view, rows, x, hasPpo, t])

  const y2Title = view === 'action' ? 'p' : view === 'outcome' ? t('ap.plots.re') : 'C2'
  return (
    <Card plain size="sm" className="flex h-full min-h-0 flex-col">
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          {t('ap.plots.roundTitle')} <PaperRef id="controller" />
        </CardTitle>
        <CardDescription>{t('ap.plots.roundSubtitle', { n: result.metrics.rounds })}</CardDescription>
        <CardAction>
          <Segmented
            value={view}
            onChange={setView}
            options={[
              { value: 'action', label: t('ap.plots.viewAction') },
              { value: 'outcome', label: t('ap.plots.viewOutcome') },
              { value: 'reward', label: t('ap.plots.viewReward') },
            ]}
          />
        </CardAction>
      </CardHeader>
      <CardContent className="min-h-40 flex-1">
        <Plot
          data={data}
          layout={baseLayout(plot, {
            barmode: 'stack',
            bargap: 0,
            xaxis: axis(plot, t('ap.plots.round'), { domain: [0, view === 'action' && hasPpo ? 0.88 : 0.94] }),
            yaxis: axis(plot, view === 'action' ? 'L' : view === 'outcome' ? t('ap.plots.aoCount') : t('ap.plots.reward')),
            yaxis2: axis(plot, y2Title, { overlaying: 'y', side: 'right', showgrid: false, ...(view === 'action' ? { range: [0, 1.05] } : {}) }),
            yaxis3: axis(plot, 'm, q', { overlaying: 'y', side: 'right', position: 1, anchor: 'free', type: 'log', showgrid: false, tickvals: [0.1, 0.25, 0.5, 1, 2, 5, 10], ticktext: ['0.1', '0.25', '0.5', '1', '2', '5', '10'] }),
            uirevision: result.run_id + view,
          })}
          useResizeHandler
          style={{ width: '100%', height: '100%' }}
          config={PLOT_CONFIG}
        />
      </CardContent>
    </Card>
  )
}
