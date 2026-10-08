import { PaperRef } from '@/components/aperiodic/PaperRef'
import { fetchAperiodicDeviceTrace } from '@/api/aperiodicSimulator'
import { axis, baseLayout, PLOT_CONFIG, STATE_COLORS } from '@/components/aperiodic/plotLayout'
import { Segmented } from '@/components/aperiodic/Segmented'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/lib/Plot'
import type { AperiodicDeviceTrace, AperiodicSimulationResult } from '@/types/aperiodicSimulation'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

const STATES = ['OFF', 'MONITOR', 'RX', 'TX', 'INTRA_ROUND_SLEEP', 'INTERROUND_SYNC_SLEEP', 'DONE']

export function DeviceTracePanel({
  result,
  selectedId,
  onSelect,
}: {
  result: AperiodicSimulationResult
  selectedId?: number | null
  onSelect?: (id: number) => void
}) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const traced = useMemo(() => (result.devices ?? []).filter((d) => d.traced), [result.devices])
  const [ownId, setOwnId] = useState<number | null>(null)
  const deviceId = selectedId !== undefined ? selectedId : ownId
  const setDeviceId = onSelect ?? setOwnId
  const [trace, setTrace] = useState<AperiodicDeviceTrace | null>(null)
  const [error, setError] = useState<string | null>(null)
  const id = deviceId != null && traced.some((d) => d.id === deviceId) ? deviceId : (traced[0]?.id ?? null)

  useEffect(() => {
    if (id == null) return
    let live = true
    setError(null)
    fetchAperiodicDeviceTrace(result.run_id, result.controller, id)
      .then((tr) => live && setTrace(tr))
      .catch((e) => live && setError(String(e)))
    return () => {
      live = false
    }
  }, [id, result.run_id, result.controller])

  const data = useMemo(() => {
    if (!trace) return []
    const out: Array<Record<string, unknown>> = STATES.map((st) => {
      const xs: Array<number | null> = []
      const ys: Array<string | null> = []
      for (const s of trace.segments)
        if (s.state === st) {
          xs.push(s.t0, s.t1, null)
          ys.push(st, st, null)
        }
      return {
        x: xs,
        y: ys,
        type: 'scatter',
        mode: 'lines',
        line: { color: STATE_COLORS[st], width: 10 },
        name: t(`ap.states.${st}`),
        hoverinfo: 'x+name',
      }
    })
    const ex: number[] = []
    const ey: number[] = []
    for (const s of trace.segments)
      if (s.e0_uJ != null && s.e1_uJ != null) {
        ex.push(s.t0, s.t1)
        ey.push(s.e0_uJ, s.e1_uJ)
      }
    out.push({ x: ex, y: ey, yaxis: 'y2', type: 'scatter', mode: 'lines', line: { color: plot.line, width: 1.4 }, name: t('ap.trace.energy') })
    for (const [v, name] of [
      [trace.E_up_uJ, 'E_up'],
      [trace.E_low_uJ, 'E_low'],
    ] as const)
      out.push({
        x: [0, trace.segments.at(-1)?.t1 ?? 1],
        y: [v, v],
        yaxis: 'y2',
        type: 'scatter',
        mode: 'lines',
        line: { color: plot.grid, dash: 'dash', width: 1 },
        name,
        showlegend: false,
      })
    return out
  }, [trace, t, plot.line, plot.grid])

  if (!traced.length) return null
  const dev = traced.find((d) => d.id === id)
  const compressed = trace?.segments.some((s) => s.duty_cycle_compressed)
  return (
    <Card plain size="sm">
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          {t('ap.trace.title')} <PaperRef id="trace" />
        </CardTitle>
        <CardDescription>
          {dev &&
            t('ap.trace.subtitle', {
              id: dev.id,
              type: dev.type,
              p: dev.p_harv_uW.toFixed(2),
              done: dev.completion_s != null ? `${dev.completion_s.toFixed(1)} s` : t('ap.trace.notDone'),
            })}
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-2">
        <Segmented value={id ?? -1} onChange={setDeviceId} options={traced.map((d) => ({ value: d.id, label: `#${d.id} (${d.type})` }))} />
        {error && <p className="text-xs text-destructive">{error}</p>}
        {trace && (
          <Plot
            data={data}
            layout={baseLayout(plot, {
              hovermode: 'closest',
              xaxis: axis(plot, t('ap.plots.time')),
              yaxis: axis(plot, '', { domain: [0.45, 1], type: 'category', categoryarray: STATES, categoryorder: 'array' }),
              yaxis2: axis(plot, t('ap.trace.energyAxis'), { domain: [0, 0.38] }),
              uirevision: `${result.run_id}-${id}`,
            })}
            useResizeHandler
            style={{ width: '100%', height: 300 }}
            config={PLOT_CONFIG}
          />
        )}
        {compressed && <p className="text-[11px] text-muted-foreground">{t('ap.trace.compressed')}</p>}
      </CardContent>
    </Card>
  )
}
