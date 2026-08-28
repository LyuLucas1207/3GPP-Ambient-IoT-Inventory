import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { fetchFig5bReference } from '@/api/simulation'
import { ExplainButton } from '@/components/ViewExplanationDialog'
import { TermHelp } from '@/components/TermHelp'
import { ViewId, TermId } from '@/explain/ids'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/lib/Plot'
import { StrategyKey, type SimulationResult } from '@/types/simulation'
import { useEffect, useMemo, useState } from 'react'
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
  const [ref, setRef] = useState<NonNullable<SimulationResult['paper_fig5b']> | null>(
    result?.paper_fig5b ?? null,
  )
  const [overlay, setOverlay] = useState<'sim' | 'paper' | 'both'>('both')

  useEffect(() => {
    if (result?.paper_fig5b) {
      setRef(result.paper_fig5b)
      return
    }
    let cancelled = false
    void fetchFig5bReference()
      .then((data) => {
        if (!cancelled) setRef(data)
      })
      .catch(() => {
        if (!cancelled) setRef(null)
      })
    return () => {
      cancelled = true
    }
  }, [result?.paper_fig5b, result?.run_id])

  const traces = useMemo(() => {
    const out: Array<Record<string, unknown>> = []
    const showSim = overlay !== 'paper'
    const showPaper = overlay !== 'sim'
    if (showSim && result) {
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
    }
    if (showPaper && ref?.available) {
      for (const [key, curve] of Object.entries(ref.curves)) {
        out.push({
          type: 'scatter',
          mode: 'lines',
          name: `${t(`strategy.${key}`)} (${t('curve.paperRef')})`,
          x: curve.time_ms,
          y: curve.ratio_pct,
          line: { width: 1.2, dash: 'dashdot', color: 'rgba(120,120,120,0.85)' },
        })
      }
    }
    return out
  }, [result, ref, overlay, t])

  const shapes = useMemo(() => {
    const marks = ref?.paper_stated_t99_s
    if (!marks) return []
    const colors: Record<string, string> = {
      em: 'rgba(76,120,168,0.45)',
      dcm_4_group: 'rgba(84,162,75,0.45)',
    }
    return Object.entries(marks)
      .filter(([, v]) => typeof v === 'number')
      .map(([key, sec]) => ({
        type: 'line' as const,
        x0: (sec as number) * 1000,
        x1: (sec as number) * 1000,
        y0: 0,
        y1: 105,
        yref: 'y' as const,
        line: { color: colors[key] ?? 'rgba(120,120,120,0.4)', width: 1, dash: 'dot' },
      }))
  }, [ref])

  const xMax = useMemo(() => {
    let max = 0
    for (const tr of traces) {
      const xs = tr.x as number[] | undefined
      const last = xs?.[xs.length - 1]
      if (typeof last === 'number' && last > max) max = last
    }
    for (const sec of Object.values(ref?.paper_stated_t99_s ?? {})) {
      if (typeof sec === 'number' && sec * 1000 > max) max = sec * 1000
    }
    return Math.max(max, 1)
  }, [traces, ref])

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
        <CardDescription>{t('curve.subtitle')}</CardDescription>
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col gap-1">
        <div className="flex flex-wrap gap-1 px-1">
          {(['sim', 'both', 'paper'] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              className={`rounded-md border px-2 py-0.5 text-[11px] ${
                overlay === mode ? 'bg-muted text-foreground' : 'text-muted-foreground'
              }`}
              onClick={() => setOverlay(mode)}
            >
              {t(`curve.overlay.${mode}`)}
            </button>
          ))}
        </div>
        <Plot
          data={traces}
          layout={{
            margin: { t: 28, r: 16, b: 8, l: 48 },
            paper_bgcolor: plot.paper,
            plot_bgcolor: plot.plot,
            dragmode: false,
            hovermode: 'x unified',
            uirevision: result?.run_id ?? 'fig5b',
            shapes,
            xaxis: {
              title: { text: t('curve.x'), standoff: 6 },
              gridcolor: plot.grid,
              color: plot.font,
              zeroline: false,
              range: [0, xMax],
              exponentformat: 'none',
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
        <p className="text-[10px] text-muted-foreground">
          {ref?.available ? t('curve.paperDigitized') : t('curve.paperMarkersOnly')}
        </p>
      </CardContent>
    </Card>
  )
}
