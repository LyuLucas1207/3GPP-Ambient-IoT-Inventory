import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ExplainButton } from '@/components/ViewExplanationDialog'
import { TermHelp } from '@/components/TermHelp'
import { ViewId, TermId } from '@/explain/ids'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/lib/Plot'
import { StrategyKey, type SimulationResult } from '@/types/simulation'
import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'

interface Props {
  result: SimulationResult | null
}

const SIM_DASH: Record<string, 'dot' | 'dash' | 'solid'> = {
  [StrategyKey.EM]: 'dot',
  [StrategyKey.DCM_1_GROUP]: 'dash',
  [StrategyKey.DCM_4_GROUP]: 'solid',
}

export function InventoryCurve({ result }: Props) {
  const { t } = useTranslation()
  const plot = usePlotTheme()

  const traces = useMemo(() => {
    const out: Array<Record<string, unknown>> = []
    if (!result) return out
    for (const [key, curve] of Object.entries(result.curves)) {
      out.push({
        type: 'scatter',
        mode: 'lines',
        name: t(`strategy.${key}`),
        x: curve.times_s.map((sec) => sec * 1000),
        y: curve.ratio_pct,
        line: {
          width: key === StrategyKey.DCM_4_GROUP ? 2.6 : 1.8,
          dash: SIM_DASH[key] ?? 'solid',
        },
      })
    }
    return out
  }, [result, t])

  const xMax = useMemo(() => {
    let max = 0
    for (const tr of traces) {
      const xs = tr.x as number[] | undefined
      const last = xs?.[xs.length - 1]
      if (typeof last === 'number' && last > max) max = last
    }
    return Math.max(max, 1)
  }, [traces])

  return (
    <Card className="flex h-full min-h-0 flex-col bg-transparent ring-0" size="sm">
      <CardHeader>
        <CardTitle className="inline-flex items-center gap-1">
          {t('curve.title')}
          <TermHelp term={TermId.T99} />
        </CardTitle>
        <CardAction>
          <ExplainButton view={ViewId.Fig5b} />
        </CardAction>
        <CardDescription>
          {t('curve.subtitle')}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col gap-1">
        <Plot
          data={traces}
          layout={{
            margin: { t: 28, r: 16, b: 8, l: 48 },
            paper_bgcolor: plot.paper,
            plot_bgcolor: plot.plot,
            dragmode: false,
            hovermode: 'x unified',
            uirevision: result?.run_id ?? 'fig5b',
            xaxis: {
              title: { text: t('curve.x'), standoff: 6 },
              gridcolor: plot.grid,
              color: plot.font,
              zeroline: false,
              range: [0, Math.max(xMax, 25000)],
              tickmode: 'linear',
              dtick: 2500,
              ticks: 'outside',
              minor: { dtick: 1250, ticks: 'inside' },
              exponentformat: 'power',
              showexponent: 'last',
              separatethousands: false,
              rangeslider: {
                visible: true,
                thickness: 0.22,
                bgcolor: plot.dark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)',
                bordercolor: plot.grid,
                yaxis: { rangemode: 'match' },
              },
            },
            yaxis: {
              title: { text: t('curve.y') },
              range: [0, 105],
              fixedrange: true,
              gridcolor: plot.grid,
              color: plot.font,
            },
            font: { color: plot.font, size: 11 },
            legend: { orientation: 'h', y: 1.16, yanchor: 'bottom', font: { color: plot.font, size: 11 } },
            autosize: true,
          }}
          useResizeHandler
          style={{ width: '100%', height: '100%', minHeight: 180 }}
          config={{
            displayModeBar: false,
            responsive: true,
            scrollZoom: false,
            doubleClick: 'reset',
          }}
        />
        <p className="text-[10px] text-muted-foreground">{t('curve.panHint')}</p>
      </CardContent>
    </Card>
  )
}
