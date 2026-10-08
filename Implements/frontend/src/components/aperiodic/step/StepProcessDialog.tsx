import { MathText } from '@/components/MathText'
import { ParamHint } from '@/components/ParamHint'
import { StrategyFlow } from '@/components/StrategyFlow'
import { Segmented } from '@/components/aperiodic/Segmented'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogBackdrop,
  DialogClose,
  DialogDescription,
  DialogPopup,
  DialogPortal,
  DialogTitle,
} from '@/components/ui/dialog'
import { Switch } from '@/components/ui/switch'
import { useStepSession } from '@/hooks/useStepSession'
import { cn } from '@/lib/utils'
import { aperiodicOverviewMap } from '@/strategyMaps/aperiodicOverview'
import type { AperiodicPaperConfig, AperiodicSimulateRequest, StepRound } from '@/types/aperiodicSimulation'
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  FootprintsIcon,
  PauseIcon,
  PlayIcon,
  RotateCcwIcon,
  SkipForwardIcon,
  XIcon,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { PowerTimeline } from './PowerTimeline'
import { StepDeviceTable } from './StepDeviceTable'
import { StepFloorMap } from './StepFloorMap'
import { StepTfMap } from './StepTfMap'
import { STEP_PHASES, phaseCounts, phaseHighlight, stateCounts, type StepPhase } from './stepModel'

const DEVICE_COUNTS = [20, 60, 120, 200]
const AUTO_MS = 1400

function Section({ title, hint, children, className }: { title: string; hint?: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={cn('grid min-w-0 content-start gap-2 rounded-lg border bg-card/60 p-3', className)}>
      <h3 className="flex items-center gap-1.5 text-xs font-medium tracking-wide text-muted-foreground uppercase">
        {title}
        {hint && <ParamHint text={hint} title={title} />}
      </h3>
      {children}
    </section>
  )
}

/** Fig. 2(a)-style strip: the paging opportunities (arrows) of the rounds walked so far. */
function RoundStrip({ rounds, current }: { rounds: StepRound[]; current: number }) {
  const { t } = useTranslation()
  if (!rounds.length) return null
  const a = rounds[0].t_start_s
  const b = rounds[rounds.length - 1].t_end_s
  const span = Math.max(b - a, 1e-6)
  const x = (tt: number) => ((tt - a) / span) * 100
  return (
    <div className="grid gap-1">
      <div className="relative h-10">
        {rounds.map((r, i) => (
          <div key={r.round}>
            <span
              className={cn('absolute top-0 -translate-x-1/2 text-[11px] leading-none', i === current ? 'text-fuchsia-500' : 'text-sky-600')}
              style={{ left: `${x(r.t_start_s)}%` }}
              title={`${t('ap.step.round', { r: r.round })} · t0 = ${r.t_start_s.toFixed(3)} s`}
            >
              ↓
            </span>
            <div
              className={cn(
                'absolute top-4 h-5 rounded-[2px] border text-center text-[9px] leading-5',
                i === current ? 'border-fuchsia-500 bg-fuchsia-500/25' : 'border-orange-400/70 bg-orange-300/40',
              )}
              style={{ left: `${x(r.t_start_s)}%`, width: `${Math.max(x(r.t_end_s) - x(r.t_start_s), 0.4)}%` }}
              title={`${t('ap.step.round', { r: r.round })} · ${((r.t_end_s - r.t_start_s) * 1e3).toFixed(0)} ms`}
            >
              {x(r.t_end_s) - x(r.t_start_s) > 6 ? r.round : ''}
            </div>
          </div>
        ))}
      </div>
      <div className="flex justify-between font-mono text-[10px] text-muted-foreground">
        <span>{a.toFixed(3)} s</span>
        <span>{b.toFixed(3)} s</span>
      </div>
    </div>
  )
}

export function StepProcessButton({ request, paper }: { request: AperiodicSimulateRequest; paper: AperiodicPaperConfig | null }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const btn = useRef<HTMLButtonElement>(null)
  return (
    <>
      <Button ref={btn} type="button" variant="outline" size="xs" className="gap-1" onClick={() => setOpen(true)}>
        <FootprintsIcon className="size-3.5" aria-hidden />
        {t('ap.step.button')}
      </Button>
      <Dialog modal open={open} onOpenChange={setOpen}>
        <DialogPortal>
          <DialogBackdrop />
          <DialogPopup
            className="h-[calc(100dvh-12px)] w-[calc(100vw-12px)] max-h-[calc(100dvh-12px)] max-w-[1920px]"
            finalFocus={btn}
            aria-modal="true"
          >
            {open && <StepProcessBody request={request} paper={paper} />}
          </DialogPopup>
        </DialogPortal>
      </Dialog>
    </>
  )
}

function StepProcessBody({ request, paper }: { request: AperiodicSimulateRequest; paper: AperiodicPaperConfig | null }) {
  const { t } = useTranslation()
  const s = useStepSession()
  const [nDevices, setNDevices] = useState(60)
  const [playing, setPlaying] = useState(false)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const { start } = s

  useEffect(() => {
    void start(request, nDevices)
  }, [start, request, nDevices])

  const phase: StepPhase = STEP_PHASES[s.phase]
  const r = s.round

  useEffect(() => {
    if (!playing) return
    if (!s.canNext) {
      setPlaying(false)
      return
    }
    const id = window.setTimeout(() => void s.next(), AUTO_MS)
    return () => window.clearTimeout(id)
  }, [playing, s])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return
      if (e.key === 'ArrowRight' && s.canNext) void s.next()
      if (e.key === 'ArrowLeft' && s.canPrev) s.prev()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [s])

  useEffect(() => {
    if (!r) return
    if (selectedId == null || !r.devices.some((d) => d.id === selectedId && d.paged_via != null)) {
      setSelectedId(r.devices.find((d) => d.access === 'transmit')?.id ?? null)
    }
  }, [r, selectedId])

  const highlight = useMemo(() => (r ? phaseHighlight(phase, r) : undefined), [r, phase])
  const counts = r ? phaseCounts(r) : null
  const init = s.info ? stateCounts(s.info.now.states) : null
  const proto = request.paging_mode === 'periodic' ? `${t('ap.terms.periodicBaseline')} ($N_g = ${request.N_g}$)` : t('ap.terms.aperiodic')
  const ctrlName = t(`ap.controllers.${request.controller}`, { defaultValue: request.controller })

  const explainParams = r && counts
    ? {
        ...counts,
        round: r.round,
        L: r.L,
        p: r.p.toFixed(3),
        F: r.F,
        nAo: r.L * r.F,
        t0: r.t_start_s.toFixed(3),
        idle: r.counts.idle_obs,
        success: r.counts.success_obs,
        coll: r.counts.collision_obs,
        decoded: r.counts.k_decoded,
        alloc: Math.round(r.counts.k_alloc),
        wasted: Math.max(Math.round(r.counts.k_alloc) - r.counts.k_served, 0),
        nextL: s.round?.controller.next.L,
        nextP: s.round?.controller.next.p.toFixed(3),
        msg3Slots: Math.ceil(r.counts.k_served / r.F),
        group: (r.group ?? 0) + 1,
        Ng: request.N_g,
      }
    : null

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 items-start justify-between gap-3 border-b px-4 py-3">
        <div className="min-w-0">
          <DialogTitle>{t('ap.step.title')}</DialogTitle>
          <DialogDescription>{t('ap.step.lead')}</DialogDescription>
        </div>
        <DialogClose className="rounded-md p-1 outline-none focus-visible:ring-3 focus-visible:ring-ring/50" aria-label={t('explain.close')}>
          <XIcon className="size-4" />
        </DialogClose>
      </div>

      <div className="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-2 border-b px-4 py-2 text-xs">
        <MathText
          className="text-muted-foreground"
          text={[
            proto,
            ctrlName,
            t(request.harvesting_scenario === 'single_source' ? 'ap.terms.singleSource' : 'ap.terms.multiSource'),
            `$F = ${request.F}$`,
            `seed ${request.seed}`,
            ...(s.info ? [`$N_{\\mathrm{eff}} = ${s.info.n_eff} / ${s.info.n_tot}$`] : []),
          ].join(' · ')}
        />
        <span className="flex items-center gap-1.5">
          <MathText text={t('ap.step.devices')} />
          <ParamHint text={t('ap.step.devicesHint')} title={t('ap.step.devices')} />
          <Segmented value={nDevices} onChange={setNDevices} options={DEVICE_COUNTS.map((n) => ({ value: n, label: String(n) }))} />
        </span>
        <label className="flex items-center gap-1.5">
          {t('ap.step.skipEmpty')}
          <ParamHint text={t('ap.step.skipEmptyHint')} title={t('ap.step.skipEmpty')} />
          <Switch checked={s.skipEmpty} onCheckedChange={s.setSkipEmpty} />
        </label>
        <Button size="xs" variant="outline" className="gap-1" onClick={() => void start(request, nDevices)} disabled={s.busy}>
          <RotateCcwIcon className="size-3" /> {t('ap.step.restart')}
        </Button>
      </div>

      <div className="flex shrink-0 flex-wrap items-center gap-2 border-b px-4 py-2">
        <div className="flex flex-wrap items-center gap-1">
          {STEP_PHASES.map((p, i) => (
            <button
              key={p}
              type="button"
              disabled={!r}
              onClick={() => s.setPhase(i)}
              className={cn(
                'flex items-center gap-1 rounded-md border px-2 py-1 text-xs transition-colors disabled:opacity-40',
                i === s.phase && r ? 'border-fuchsia-500 bg-fuchsia-500/15 font-medium' : i < s.phase && r ? 'border-border bg-muted/60' : 'border-border',
              )}
            >
              <span className="font-mono text-[10px] text-muted-foreground">{i + 1}</span>
              <MathText text={t(`ap.step.phase.${p}`)} />
            </button>
          ))}
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          {r && <Badge variant="secondary">{t('ap.step.round', { r: r.round })}</Badge>}
          {r && <Badge variant="outline">t0 = {r.t_start_s.toFixed(3)} s</Badge>}
          {s.info && (
            <Badge variant="outline">
              {t('ap.step.identifiedOf', { n: r ? r.n_done : s.info.now.n_done, total: s.info.n_eff })}
            </Badge>
          )}
          <Button size="sm" variant="outline" onClick={s.prev} disabled={!s.canPrev || s.busy}>
            <ChevronLeftIcon /> {t('ap.step.prev')}
          </Button>
          <Button size="sm" onClick={() => void s.next()} disabled={!s.canNext}>
            {r ? t('ap.step.next') : t('ap.step.first')} <ChevronRightIcon />
          </Button>
          <Button size="sm" variant="outline" onClick={() => setPlaying((v) => !v)} disabled={!s.canNext && !playing}>
            {playing ? <PauseIcon /> : <PlayIcon />} {playing ? t('ap.stage.pause') : t('ap.step.auto')}
          </Button>
          <Button size="sm" variant="outline" onClick={() => void s.nextRound()} disabled={!s.canNext}>
            <SkipForwardIcon /> {t('ap.step.nextRound')}
          </Button>
        </div>
      </div>

      {s.error && <p className="mx-4 mt-2 rounded-md border border-destructive bg-destructive/10 px-3 py-2 text-sm text-destructive">{s.error}</p>}

      <div className="grid min-h-0 flex-1 overflow-hidden lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <div className="grid min-h-0 content-start gap-3 overflow-auto p-3">
          <Section title={t('ap.step.nowTitle')}>
            {!s.info ? (
              <p className="text-sm text-muted-foreground">{s.busy ? t('ap.common.running') : t('ap.step.noSession')}</p>
            ) : !r || !explainParams ? (
              <div className="grid gap-1 text-sm">
                <p>
                  <MathText text={t('ap.step.intro', { n: s.info.n_eff, off: init?.OFF ?? 0, mon: init?.MONITOR ?? 0 })} />
                </p>
                <p className="text-xs text-muted-foreground">{t('ap.step.introHint')}</p>
              </div>
            ) : (
              <div className="grid gap-1.5 text-sm">
                <p className="font-medium">
                  {s.phase + 1}. <MathText text={t(`ap.step.phase.${phase}`)} />
                  {r.skipped_rounds > 0 && phase === 'before' && (
                    <span className="ml-2 text-xs font-normal text-muted-foreground">
                      {t('ap.step.skipped', { n: r.skipped_rounds, ms: (r.skipped_time_s * 1e3).toFixed(0) })}
                    </span>
                  )}
                </p>
                <p className="leading-relaxed">
                  <MathText text={t(`ap.step.explain.${phase}${r.periodic && (phase === 'before' || phase === 'paging' || phase === 'msg2' || phase === 'after') ? 'Periodic' : ''}`, explainParams)} />
                </p>
                <p className="text-xs text-muted-foreground">
                  <MathText text={t(`ap.step.paper.${phase}`)} />
                </p>
              </div>
            )}
          </Section>

          {s.rounds.length > 0 && (
            <Section title={t('ap.step.stripTitle')} hint={t('ap.step.stripHint')}>
              <RoundStrip rounds={s.rounds} current={s.roundIdx} />
            </Section>
          )}

          {r && (
            <Section title={t('ap.step.tfTitle')} hint={t('ap.step.tfHint')}>
              <StepTfMap r={r} phase={phase} selectedId={selectedId} onSelect={setSelectedId} />
            </Section>
          )}

          {r && s.info && (
            <Section title={t('ap.step.powerTitle')} hint={t('ap.step.powerHint')}>
              <PowerTimeline r={r} phase={phase} selectedId={selectedId} statics={s.info.devices} />
            </Section>
          )}
        </div>

        <div className="grid min-h-0 grid-rows-[minmax(14rem,36%)_minmax(13rem,30%)_minmax(0,1fr)] border-t lg:border-t-0 lg:border-l">
          <div className="min-h-0 border-b">
            <StrategyFlow def={aperiodicOverviewMap} highlight={highlight} toolbar={false} />
          </div>
          <div className="flex min-h-0 flex-col border-b px-3 pt-2 pb-1.5">
            <h3 className="flex shrink-0 items-center gap-1.5 text-xs font-medium tracking-wide text-muted-foreground uppercase">
              {t('ap.step.mapTitle')}
              <ParamHint text={t('ap.step.mapHint')} title={t('ap.step.mapTitle')} />
            </h3>
            <div className="min-h-0 flex-1">
              {s.info ? (
                <StepFloorMap
                  r={r}
                  phase={phase}
                  statics={s.info.devices}
                  initialStates={s.info.now.states}
                  paper={paper}
                  selectedId={selectedId}
                  onSelect={setSelectedId}
                />
              ) : (
                <p className="text-xs text-muted-foreground">{t('ap.step.noSession')}</p>
              )}
            </div>
          </div>
          <div className="min-h-0 overflow-auto p-3">
            {r && s.info ? (
              <StepDeviceTable r={r} phase={phase} statics={s.info.devices} selectedId={selectedId} onSelect={setSelectedId} />
            ) : (
              <p className="text-xs text-muted-foreground">{t('ap.step.tableEmpty')}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
