import { MathText } from '@/components/MathText'
import { ParamHint } from '@/components/ParamHint'
import { fetchPaperReference, type PaperReference } from '@/api/aperiodicSimulator'
import { PaperCaption } from '@/components/aperiodic/PaperRef'
import { paperRequest, type PaperCurve, type PaperFigure } from '@/components/aperiodic/paperPresets'
import { axis, baseLayout, PLOT_CONFIG } from '@/components/aperiodic/plotLayout'
import { texToPlotly } from '@/lib/tex'
import {
  CURVE_COLORS,
  CheckpointNotes,
  ProtocolFigure,
  ReproRunControls,
  jobResult,
  type Reproduce,
} from '@/components/aperiodic/ReproViews'
import { Badge } from '@/components/ui/badge'
import { usePlotTheme } from '@/hooks/usePlotTheme'
import Plot from '@/lib/Plot'
import type { AperiodicSimulateRequest, AperiodicSimulationResult, JobStatus, ReproTarget } from '@/types/aperiodicSimulation'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

const TARGET: Record<PaperFigure, { target: ReproTarget; panel?: string }> = {
  fig5a: { target: 'figure5', panel: 'a_L16' },
  fig5b: { target: 'figure5', panel: 'b_L1' },
  fig6a: { target: 'figure6', panel: 'a_L16' },
  fig6b: { target: 'figure6', panel: 'b_L1' },
  fig7: { target: 'figure7' },
}

const CURVE_LABEL_KEY: Record<string, string> = {
  aperiodic: 'ap.paperConfig.curves.aperiodic',
  periodic_Ng1: 'ap.paperConfig.curves.periodic_Ng1',
  periodic_Ng4: 'ap.paperConfig.curves.periodic_Ng4',
  periodic_Ng1_wo_depletion: 'ap.paperConfig.curves.periodic_Ng1_wo_depletion',
  periodic_Ng4_wo_depletion: 'ap.paperConfig.curves.periodic_Ng4_wo_depletion',
  recurrent_ppo: 'ap.paperConfig.curves.recurrent_ppo',
  dfsa_schoute: 'ap.paperConfig.curves.dfsa_schoute',
  cmebe: 'ap.paperConfig.curves.cmebe',
}

/** Name of the paper curve a run corresponds to (same naming as the reference CSVs). */
function runCurveName(cfg: Record<string, unknown>): string {
  if (cfg.controller && cfg.controller !== 'pfsa_pze') return String(cfg.controller)
  if (cfg.paging_mode === 'periodic') return `periodic_Ng${cfg.N_g}${cfg.enforce_midround_depletion === false ? '_wo_depletion' : ''}`
  return 'aperiodic'
}

function paperT(ref: { x: number[]; y: number[] } | undefined, q: number): number | null {
  if (!ref) return null
  let best = -Infinity
  for (let i = 0; i < ref.x.length; i++) {
    best = Math.max(best, ref.y[i])
    if (best >= q) {
      if (i === 0) return ref.x[0]
      const y0 = Math.max(...ref.y.slice(0, i))
      const frac = ref.y[i] === y0 ? 0 : (q - y0) / (ref.y[i] - y0)
      return ref.x[i - 1] + Math.min(Math.max(frac, 0), 1) * (ref.x[i] - ref.x[i - 1])
    }
  }
  return null
}

function settingDiffs(result: AperiodicSimulationResult, expected: AperiodicSimulateRequest): string[] {
  const c = result.config as Record<string, unknown>
  const checks: Array<[string, unknown, unknown]> = [
    ['N_tot', c.n_tot, expected.num_devices],
    ['harvesting', c.harvesting_scenario, expected.harvesting_scenario],
    ['F', (c.system as Record<string, unknown> | undefined)?.F, expected.F],
  ]
  if (expected.L_mode === 'fixed') checks.push(['L_s', c.L_fixed, expected.L_fixed])
  else checks.push(['L_1', c.L_initial, expected.L_initial])
  return checks.filter(([, a, b]) => a !== b).map(([k, a, b]) => `${k}: ${String(a)} ≠ ${String(b)}`)
}

function ThisRun({
  fig,
  curve,
  result,
  request,
}: {
  fig: PaperFigure
  curve: PaperCurve
  result: AperiodicSimulationResult | null
  request: AperiodicSimulateRequest
}) {
  const { t } = useTranslation()
  const plot = usePlotTheme()
  const [ref, setRef] = useState<PaperReference | null>(null)

  useEffect(() => {
    let live = true
    fetchPaperReference(fig)
      .then((r) => live && setRef(r))
      .catch(() => live && setRef(null))
    return () => {
      live = false
    }
  }, [fig])

  const runName = result ? runCurveName(result.config as Record<string, unknown>) : null
  const diffs = result ? settingDiffs(result, paperRequest(request, fig, curve)) : []
  const data = useMemo(() => {
    const out: Array<Record<string, unknown>> = []
    for (const [name, c] of Object.entries(ref?.curves ?? {})) {
      const mine = name === runName
      out.push({
        x: c.x,
        y: c.y,
        type: 'scatter',
        mode: 'lines',
        line: { color: CURVE_COLORS[name] ?? plot.line, width: mine ? 2.2 : 1.2, dash: 'dash' },
        opacity: mine ? 0.95 : 0.55,
        name: `${texToPlotly(t(CURVE_LABEL_KEY[name] ?? name, { defaultValue: name }))} (${t('ap.repro.paper')})`,
      })
    }
    if (result && runName)
      out.push({
        x: result.curve.times,
        y: result.curve.ratio,
        type: 'scatter',
        mode: 'lines',
        line: { color: CURVE_COLORS[runName] ?? plot.line, width: 2.8 },
        name: `${texToPlotly(t(CURVE_LABEL_KEY[runName] ?? runName, { defaultValue: runName }))} — ${t('ap.figTab.thisRunShort', { seed: result.config.seed as number })}`,
      })
    return out
  }, [ref, result, runName, plot.line, t])

  const xMax = Math.max(0, ...Object.values(ref?.curves ?? {}).map((c) => c.x[c.x.length - 1] ?? 0))
  const refCurve = runName ? ref?.curves[runName] : undefined

  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap items-center gap-2 text-sm font-medium">
        {t('ap.figTab.thisRun')}
        <ParamHint text={t('ap.figTab.thisRunHint')} title={t('ap.figTab.thisRun')} />
        {result && <Badge variant="outline">seed {String(result.config.seed)}</Badge>}
        {result && runName && (
          <Badge variant="secondary">
            <MathText text={t(CURVE_LABEL_KEY[runName] ?? runName, { defaultValue: runName })} />
          </Badge>
        )}
      </div>
      {!result ? (
        <p className="text-xs text-muted-foreground">{t('ap.figTab.noRun')}</p>
      ) : (
        <>
          {diffs.length > 0 && (
            <p className="rounded-md border border-amber-500/40 bg-amber-500/10 px-2 py-1 text-[11px] text-amber-800 dark:text-amber-200">
              {t('ap.figTab.mismatch', { fig: t(`ap.paperRef.${fig}.label`), diffs: diffs.join(' · ') })}
            </p>
          )}
          {runName && ref && !ref.curves[runName] && (
            <p className="text-[11px] text-muted-foreground">{t('ap.figTab.notInFigure', { fig: t(`ap.paperRef.${fig}.label`) })}</p>
          )}
          <Plot
            data={data}
            layout={baseLayout(plot, {
              xaxis: axis(plot, t('ap.plots.time'), xMax ? { range: [0, xMax] } : {}),
              yaxis: axis(plot, t('ap.plots.ratio'), { range: [0, 102] }),
              uirevision: `${fig}-${result.run_id}`,
            })}
            useResizeHandler
            style={{ width: '100%', height: 300 }}
            config={PLOT_CONFIG}
          />
          <table className="w-full max-w-md text-xs">
            <thead>
              <tr className="text-muted-foreground">
                <th className="text-left font-normal">
                  <span className="inline-flex items-center gap-1">
                    {t('ap.figTab.metric')} <ParamHint text={t('ap.help.tq')} title="T_q" />
                  </span>
                </th>
                <th className="text-right font-normal">{t('ap.figTab.thisRunCol')}</th>
                <th className="text-right font-normal">{t('ap.repro.paper')}</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {([50, 90, 99] as const).map((q) => {
                const s = result.metrics[`T${q}`]
                const p = paperT(refCurve, q)
                return (
                  <tr key={q}>
                    <td className="font-sans">T{q} (s)</td>
                    <td className="text-right">{s != null ? s.toFixed(1) : '—'}</td>
                    <td className="text-right">{p != null ? p.toFixed(1) : '—'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}

export function PaperFigureTab({
  fig,
  curve,
  result,
  request,
  job,
  reproduce,
}: {
  fig: PaperFigure
  curve: PaperCurve
  result: AperiodicSimulationResult | null
  request: AperiodicSimulateRequest
  job: JobStatus | null
  reproduce: Reproduce
}) {
  const { t } = useTranslation()
  const { target, panel } = TARGET[fig]
  const res = jobResult(job, target)
  const panels = res?.panels ? Object.keys(res.panels as object) : []

  return (
    <div className="grid gap-4 pr-2">
      <div className="grid gap-1">
        <PaperCaption id={fig} hint={t(`ap.help.fig.${fig}`)} />
        <p className="text-[11px] text-muted-foreground">{t('ap.figTab.synced')}</p>
      </div>

      <ThisRun fig={fig} curve={curve} result={result} request={request} />

      <div className="grid gap-2 border-t pt-3">
        <div className="flex items-center gap-2 text-sm font-medium">
          {t('ap.figTab.average')}
          <ParamHint text={t('ap.figTab.averageHint')} title={t('ap.figTab.average')} />
        </div>
        <ReproRunControls
          key={target}
          job={job}
          target={target}
          panels={panel ? [panel] : undefined}
          reproduce={reproduce}
          baseSeed={request.seed}
        />
        {res && <CheckpointNotes result={res} />}
        {res && panel && <ProtocolFigure result={res} panel={panel} />}
        {res &&
          !panel &&
          panels.map((k) => (
            <div key={k}>
              <p className="text-xs font-medium">{t(`ap.terms.${k === 'single_source' ? 'singleSource' : 'multiSource'}`)}</p>
              <ProtocolFigure result={res} panel={k} />
            </div>
          ))}
      </div>
    </div>
  )
}
