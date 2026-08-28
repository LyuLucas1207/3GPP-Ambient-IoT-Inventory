import { ChartLegend, type LegendItem } from '@/components/ChartLegend'
import { ParamHint } from '@/components/ParamHint'
import { EVENT_MARK, protocolEventLegendItems, SCIENTIFIC_STATE_FILL, scientificStateLegendItems } from '@/explain/chartVisuals'
import { ExplainButton } from '@/components/ViewExplanationDialog'
import { TermHelp } from '@/components/TermHelp'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/lib/Plot'
import { fetchDeviceTrace } from '@/api/simulation'
import { TermId, ViewId } from '@/explain/ids'
import type { DeviceScientificTrace, SimulationResult, StrategyKey } from '@/types/simulation'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

interface Props {
  deviceId: number | null
  result: SimulationResult | null
  strategy: StrategyKey
}

const STATE_FILL = SCIENTIFIC_STATE_FILL

type TrimMs = 20 | 80 | 200 | 0
type YMode = 'auto' | 'full' | 'zoom'

function nearestEnergy(time: number[], energy: number[], t: number) {
  if (!time.length) return 0
  let best = 0
  let dist = Math.abs(time[0] - t)
  for (let i = 1; i < time.length; i++) {
    const d = Math.abs(time[i] - t)
    if (d < dist) {
      dist = d
      best = i
    }
  }
  return energy[best]
}

function nearestIndex(time: number[], t: number) {
  if (!time.length) return 0
  let best = 0
  let dist = Math.abs(time[0] - t)
  for (let i = 1; i < time.length; i++) {
    const d = Math.abs(time[i] - t)
    if (d < dist) {
      dist = d
      best = i
    }
  }
  return best
}

export function EnergyHistory({ deviceId, result, strategy }: Props) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const [trimMs, setTrimMs] = useState<TrimMs>(80)
  const [yMode, setYMode] = useState<YMode>('auto')
  const [trace, setTrace] = useState<DeviceScientificTrace | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const runId = result?.run_id ?? result?.metadata.run_id
  const eUp = trace?.e_up_nj ?? result?.paper_parameters.E_up_nJ ?? 500
  const eLow = trace?.e_low_nj ?? result?.paper_parameters.E_low_nJ ?? 250
  const simDt = trace?.simulation_dt_s ?? result?.metadata.dt_s ?? 0.0005

  useEffect(() => {
    if (deviceId == null || runId == null) {
      setTrace(null)
      setError(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchDeviceTrace(runId, strategy, deviceId)
      .then((data) => {
        if (!cancelled) setTrace(data)
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setTrace(null)
          setError(err.message)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [deviceId, runId, strategy])

  const view = useMemo(() => {
    if (!trace) return null
    const doneAt = trace.completion_time_s
    let end = trace.time_s.length
    if (trimMs > 0 && doneAt != null) {
      const cut = doneAt + trimMs / 1000
      const i = trace.time_s.findIndex((x) => x > cut)
      end = i < 0 ? trace.time_s.length : Math.max(i, 2)
    }
    const time = trace.time_s.slice(0, end)
    const energy = trace.energy_nj.slice(0, end)
    const state = trace.scientific_state.slice(0, end)
    const liveT: number[] = []
    const liveE: number[] = []
    const liveCustom: Array<[number, string, string, number, string, string, number]> = []
    const frozenT: number[] = []
    const frozenE: number[] = []
    for (let i = 0; i < time.length; i++) {
      const frozen = doneAt != null && time[i] > doneAt + 1e-9
      const d = i === 0 ? 0 : energy[i] - energy[i - 1]
      const st = state[i]
      let why = t('energy.reason.hold')
      if (frozen || st === 'DONE') why = t('energy.reason.frozen')
      else if (d > 1e-6) why = t('energy.reason.harvest')
      else if (d < -1e-6) why = t('energy.reason.draw')
      if (frozen) {
        frozenT.push(time[i])
        frozenE.push(energy[i])
      } else {
        liveT.push(time[i])
        liveE.push(energy[i])
        liveCustom.push([
          d,
          st,
          trace.protocol_phase[i] ?? '—',
          trace.power_draw_nw[i] ?? 0,
          (trace.paging_index[i] ?? -1) >= 0 ? String(trace.paging_index[i]) : '—',
          why,
          trace.harvest_power_nw - (trace.power_draw_nw[i] ?? 0),
        ])
      }
    }
    const shapes: Array<Record<string, unknown>> = []
    let i = 0
    while (i < time.length) {
      const st = state[i]
      let j = i + 1
      while (j < time.length && state[j] === st) j++
      shapes.push({
        type: 'rect',
        xref: 'x',
        yref: 'paper',
        x0: time[i],
        x1: time[Math.max(j - 1, i)],
        y0: 0,
        y1: 1,
        fillcolor: STATE_FILL[st] ?? 'transparent',
        line: { width: 0 },
        layer: 'below',
      })
      i = j
    }
    const t1 = time[0] ?? 0
    const t2 = time[time.length - 1] ?? 1
    shapes.push(
      {
        type: 'line',
        xref: 'x',
        yref: 'y',
        x0: t1,
        x1: t2,
        y0: eUp,
        y1: eUp,
        line: { color: '#0369a1', width: 1, dash: 'dash' },
      },
      {
        type: 'line',
        xref: 'x',
        yref: 'y',
        x0: t1,
        x1: t2,
        y0: eLow,
        y1: eLow,
        line: { color: '#b45309', width: 1, dash: 'dot' },
      },
    )
    if (doneAt != null) {
      shapes.push({
        type: 'line',
        x0: doneAt,
        x1: doneAt,
        y0: 0,
        y1: 1,
        yref: 'paper',
        line: { color: '#16a34a', width: 2 },
      })
    }
    const markers: Array<Record<string, unknown>> = []
    const presentEvents = new Set<string>()
    const rawEvents = Array.isArray(trace.events) ? trace.events : []
    for (const rec of rawEvents) {
      const ev = String(rec.event ?? '')
      const spec = EVENT_MARK[ev]
      if (!spec) continue
      const tev = Number(rec.time_s)
      if (!Number.isFinite(tev) || tev < t1 - 1e-9 || tev > t2 + 1e-9) continue
      presentEvents.add(spec.key)
      const k = nearestIndex(time, tev)
      const aoT = rec.time_ao
      const aoF = rec.freq_ao
      const ao = aoT != null && Number(aoT) >= 0 ? `T${aoT}${aoF != null && Number(aoF) >= 0 ? `/F${aoF}` : ''}` : '—'
      markers.push({
        type: 'scatter',
        mode: 'markers',
        x: [tev],
        y: [nearestEnergy(time, energy, tev)],
        marker: { symbol: spec.symbol, color: spec.color, size: 10 },
        name: t(`energy.event.${spec.key}`),
        showlegend: false,
        hovertemplate:
          `%{x:.4f} s<br>%{y:.3f} nJ<br>${t(`energy.event.${spec.key}`)}` +
          `<br>${t('energy.tip.state')}=${state[k]}` +
          `<br>${t('energy.tip.phase')}=${trace.protocol_phase[k] ?? '—'}` +
          `<br>P_eh=${trace.harvest_power_nw.toFixed(2)} nW` +
          `<br>${t('energy.tip.draw')}=${trace.power_draw_nw[k]?.toFixed(2) ?? '—'} nW` +
          `<br>${t('energy.tip.net')}=${(trace.harvest_power_nw - (trace.power_draw_nw[k] ?? 0)).toFixed(2)} nW` +
          `<br>AO ${ao}<extra></extra>`,
      })
    }
    const eMin = energy.length ? Math.min(...energy) : 0
    const eMax = energy.length ? Math.max(...energy) : eUp
    const span = Math.max(eMax - eMin, 0.5)
    const zoom = yMode === 'zoom' || (yMode === 'auto' && span < 0.1 * eUp)
    const pad = Math.max(span * 0.18, 1)
    const yRange: [number, number] = zoom ? [eMin - pad, Math.max(eMax + pad, eUp + pad * 0.2)] : [0, eUp * 1.08]
    return {
      time,
      energy,
      state,
      liveT,
      liveE,
      liveCustom,
      frozenT,
      frozenE,
      shapes,
      markers,
      doneAt,
      yRange,
      zoom,
      presentEvents,
    }
  }, [trace, trimMs, yMode, eUp, eLow, t])

  const legendItems: LegendItem[] = useMemo(() => {
    const items: LegendItem[] = [
      {
        id: 'ees',
        label: t('energy.legend.ees'),
        swatch: '#2563eb',
        helpTitle: t('energy.legend.ees'),
        helpBody: t('energy.itemHelp.ees'),
      },
      {
        id: 'frozen',
        label: t('energy.legend.frozen'),
        swatch: '#94a3b8',
        dashed: true,
        helpTitle: t('energy.legend.frozen'),
        helpBody: t('energy.itemHelp.frozen'),
      },
      {
        id: 'eup',
        label: t('energy.legend.eup'),
        swatch: '#0369a1',
        dashed: true,
        helpTitle: t('energy.legend.eup'),
        helpBody: t('energy.itemHelp.eup'),
      },
      {
        id: 'elow',
        label: t('energy.legend.elow'),
        swatch: '#b45309',
        dashed: true,
        helpTitle: t('energy.legend.elow'),
        helpBody: t('energy.itemHelp.elow'),
      },
      {
        id: 'doneLine',
        label: t('energy.legend.doneLine'),
        swatch: '#16a34a',
        symbol: 'line-ns',
        helpTitle: t('energy.legend.doneLine'),
        helpBody: t('energy.itemHelp.doneLine'),
      },
      ...scientificStateLegendItems(t),
    ]
    if (!view) return items
    items.push(...protocolEventLegendItems(t, view.presentEvents))
    return items
  }, [t, view])

  const example =
    trace && view?.doneAt != null
      ? t('views.energy.example', {
          id: deviceId,
          t: view.doneAt.toFixed(3),
          e: (view.liveE[0] ?? trace.energy_nj[0] ?? 0).toFixed(1),
        })
      : undefined

  if (deviceId == null) {
    return (
      <Card className="bg-card/90 backdrop-blur-md" size="sm">
        <CardHeader>
          <CardTitle>{t('energy.title')}</CardTitle>
          <CardAction>
            <ExplainButton view={ViewId.Energy} />
          </CardAction>
          <CardDescription>{t('energy.empty')}</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card className="bg-card/90 backdrop-blur-md" size="sm">
      <CardHeader>
        <CardTitle className="inline-flex items-center gap-1">
          {t('energy.title')}
          <TermHelp term={TermId.Ees} />
        </CardTitle>
        <CardAction>
          <ExplainButton view={ViewId.Energy} example={example} />
        </CardAction>
        <CardDescription>{t('energy.lead')}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-2">
        <div className="grid gap-2 sm:grid-cols-2">
          <div>
            <Label className="inline-flex items-center gap-1 text-xs">
              {t('energy.trim.label')}
              <ParamHint text={t('energy.trim.hint')} />
            </Label>
            <div className="mt-1 flex flex-wrap gap-1">
              {([20, 80, 200, 0] as const).map((ms) => (
                <button
                  key={ms}
                  type="button"
                  className={`rounded-md border px-2 py-0.5 text-[11px] ${trimMs === ms ? 'bg-muted text-foreground' : 'text-muted-foreground'}`}
                  onClick={() => setTrimMs(ms)}
                >
                  {ms === 0 ? t('energy.trim.full') : t('energy.trim.ms', { ms })}
                </button>
              ))}
            </div>
            <p className="mt-1 text-[11px] text-muted-foreground">{t('energy.trim.hint')}</p>
          </div>
          <div>
            <Label className="inline-flex items-center gap-1 text-xs">
              {t('energy.y.label')}
              <ParamHint text={t('energy.y.hint')} />
            </Label>
            <div className="mt-1 flex flex-wrap gap-1">
              {(['auto', 'full', 'zoom'] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  className={`rounded-md border px-2 py-0.5 text-[11px] ${yMode === mode ? 'bg-muted text-foreground' : 'text-muted-foreground'}`}
                  onClick={() => setYMode(mode)}
                >
                  {t(`energy.y.${mode}`)}
                </button>
              ))}
            </div>
          </div>
        </div>
        {loading ? <p className="text-sm text-muted-foreground">{t('energy.loading')}</p> : null}
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        {!loading && !error && view && trace ? (
          <>
            <Plot
              data={[
                {
                  type: 'scatter',
                  mode: 'lines',
                  x: view.liveT,
                  y: view.liveE,
                  line: { color: '#2563eb', width: 2.4 },
                  name: 'e_ES',
                  showlegend: false,
                  customdata: view.liveCustom,
                  hovertemplate:
                    `%{x:.4f} s<br>%{y:.3f} nJ` +
                    `<br>Δe=%{customdata[0]:.3f} nJ` +
                    `<br>${t('energy.tip.state')}=%{customdata[1]}` +
                    `<br>${t('energy.tip.phase')}=%{customdata[2]}` +
                    `<br>P_eh=${trace.harvest_power_nw.toFixed(2)} nW` +
                    `<br>${t('energy.tip.draw')}=%{customdata[3]:.2f} nW` +
                    `<br>${t('energy.tip.net')}=%{customdata[6]:.2f} nW` +
                    `<br>${t('energy.tip.page')}=%{customdata[4]}` +
                    `<br>${t('energy.tip.reason')}=%{customdata[5]}` +
                    `<extra>e_ES</extra>`,
                },
                {
                  type: 'scatter',
                  mode: 'lines',
                  x: view.frozenT,
                  y: view.frozenE,
                  line: { color: '#94a3b8', width: 1.6, dash: 'dot' },
                  name: t('energy.legend.frozen'),
                  showlegend: false,
                  hovertemplate: `%{x:.4f} s<br>%{y:.3f} nJ<extra>${t('energy.legend.frozen')}</extra>`,
                },
                ...view.markers,
              ]}
              layout={{
                margin: { t: 8, r: 52, b: 40, l: 52 },
                paper_bgcolor: plot.paper,
                plot_bgcolor: plot.plot,
                showlegend: false,
                xaxis: { title: { text: t('energy.timeAxis') }, gridcolor: plot.grid, color: plot.font },
                yaxis: {
                  title: { text: t('energy.energyAxis') },
                  range: view.yRange,
                  gridcolor: plot.grid,
                  color: plot.font,
                },
                font: { color: plot.font, size: 11 },
                autosize: true,
                shapes: view.shapes,
                annotations: [
                  {
                    x: 1,
                    y: eUp,
                    xref: 'paper',
                    yref: 'y',
                    text: t('energy.legend.eupShort'),
                    showarrow: false,
                    xanchor: 'left',
                    font: { size: 10, color: plot.font },
                  },
                  {
                    x: 1,
                    y: eLow,
                    xref: 'paper',
                    yref: 'y',
                    text: t('energy.legend.elowShort'),
                    showarrow: false,
                    xanchor: 'left',
                    font: { size: 10, color: plot.font },
                  },
                ],
              }}
              useResizeHandler
              style={{ width: '100%', height: 280 }}
              config={{ displayModeBar: false }}
            />
            <ChartLegend title={t('energy.chartKey')} items={legendItems} />
            <p className="text-[11px] text-muted-foreground">
              {t('energy.footer', {
                sim: (simDt * 1e3).toFixed(1),
                chart: (trace.dt_s * 1e3).toFixed(1),
                done: view.doneAt != null ? view.doneAt.toFixed(3) : '—',
              })}
            </p>
          </>
        ) : null}
        {!loading && !error && !trace ? (
          <p className="text-sm text-muted-foreground">{t('energy.empty')}</p>
        ) : null}
      </CardContent>
    </Card>
  )
}
