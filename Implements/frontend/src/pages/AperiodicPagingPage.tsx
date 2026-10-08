import { InfoIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { HudPanel, HudSplit } from '@/components/HudDock'
import { LanguageToggle } from '@/components/LanguageToggle'
import { PaperNav } from '@/components/PaperNav'
import { ThemeToggle } from '@/components/ThemeToggle'
import { AperiodicCBRAInspector } from '@/components/aperiodic/AperiodicCBRAInspector'
import { AperiodicControls } from '@/components/aperiodic/AperiodicControls'
import { AperiodicFactoryView } from '@/components/aperiodic/AperiodicFactoryView'
import { AperiodicInventoryPlot } from '@/components/aperiodic/AperiodicInventoryPlot'
import { AperiodicMetrics } from '@/components/aperiodic/AperiodicMetrics'
import { DeviceTracePanel } from '@/components/aperiodic/DeviceTracePanel'
import { paperRequest, type PaperCurve, type PaperFigure } from '@/components/aperiodic/paperPresets'
import { CurrentRoundCard, PlaybackControls } from '@/components/aperiodic/PlaybackPanel'
import { STATE_COLORS } from '@/components/aperiodic/plotLayout'
import { PpoStatusCard } from '@/components/aperiodic/PpoStatusCard'
import { ReproductionPanel } from '@/components/aperiodic/ReproductionPanel'
import { RoundControllerPlot } from '@/components/aperiodic/RoundControllerPlot'
import { Segmented } from '@/components/aperiodic/Segmented'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useAperiodicPlayback } from '@/hooks/useAperiodicPlayback'
import { useAperiodicSimulation } from '@/hooks/useAperiodicSimulation'
import { HudDock } from '@/types/hud'

const LEFT_DEFAULT = 320
const RIGHT_DEFAULT = 360
const TAB_GUTTER = 52

type DockTab = 'inventory' | 'rounds' | 'repro'

function defaultBottomHeight(viewportH: number) {
  return Math.max(200, Math.floor(viewportH / 3))
}

export default function AperiodicPagingPage() {
  const { t, i18n } = useTranslation()
  const sim = useAperiodicSimulation()
  const { result } = sim
  const pb = useAperiodicPlayback(result)
  const [paperFig, setPaperFig] = useState<PaperFigure>('fig6a')
  const [paperCurve, setPaperCurve] = useState<PaperCurve>('aperiodic')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [tab, setTab] = useState<DockTab>('inventory')

  const [leftOpen, setLeftOpen] = useState(true)
  const [rightOpen, setRightOpen] = useState(true)
  const [bottomOpen, setBottomOpen] = useState(true)
  const [leftSize, setLeftSize] = useState(LEFT_DEFAULT)
  const [rightSize, setRightSize] = useState(RIGHT_DEFAULT)
  const [bottomSize, setBottomSize] = useState(() =>
    defaultBottomHeight(typeof window !== 'undefined' ? window.innerHeight : 800),
  )
  const [split, setSplit] = useState(0.38)
  const [viewport, setViewport] = useState({ w: 1280, h: 800 })

  useEffect(() => {
    document.title = t('aperiodic.documentTitle')
  }, [t, i18n.language])

  useEffect(() => {
    const update = () => setViewport({ w: window.innerWidth, h: window.innerHeight })
    update()
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target
      if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) return
      if (e.key === '[') setLeftOpen((open) => !open)
      if (e.key === ']') setRightOpen((open) => !open)
      if (e.key === '\\') setBottomOpen((open) => !open)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const applyPaper = (run: boolean) => {
    const req = paperRequest(sim.request, paperFig, paperCurve)
    if (run) void sim.run(req)
    else sim.setRequest(req)
  }

  const selectDevice = (id: number) => {
    if (!result?.devices?.some((d) => d.id === id && d.traced)) return
    setSelectedId(id)
    setRightOpen(true)
  }

  const bottomClearance = bottomOpen ? bottomSize + 20 : 20
  const leftMax = Math.min(520, Math.floor(viewport.w * 0.42))
  const rightMax = Math.min(640, Math.floor(viewport.w * 0.45))
  const bottomMax = Math.min(Math.floor(viewport.h * 0.72), viewport.h - 96)
  const bottomDefault = Math.min(Math.max(200, bottomMax), defaultBottomHeight(viewport.h))
  const headerLeft = leftOpen ? leftSize + 24 : TAB_GUTTER
  const headerRight = rightOpen ? rightSize + 24 : TAB_GUTTER
  const nEff = result?.metrics.n_eff ?? 0
  const pct = pb.interactive && nEff ? ((100 * (pb.snap?.n_done ?? 0)) / nEff).toFixed(1) : null

  return (
    <div className="relative h-dvh w-screen overflow-hidden bg-background">
      <AperiodicFactoryView
        result={pb.interactive ? result : null}
        paper={sim.paper}
        snapshot={pb.snap}
        selectedId={selectedId}
        onSelect={selectDevice}
        pad={{
          top: 108,
          right: headerRight,
          bottom: bottomOpen ? bottomSize + 24 : TAB_GUTTER,
          left: headerLeft,
        }}
      />

      <header className="absolute z-30" style={{ top: 12, left: headerLeft, right: headerRight }}>
        <Card className="bg-card/90 px-4 py-2.5 backdrop-blur-md" size="sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <PaperNav className="mb-1.5" />
              <p className="text-[11px] tracking-[0.16em] text-muted-foreground uppercase">{t('aperiodic.kicker')}</p>
              <h1 className="truncate text-lg font-medium" title={t('aperiodic.title')}>
                {t('aperiodic.title')}
              </h1>
              <p className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                <span>
                  {t('ap.header.protocol')}:{' '}
                  <span className="font-medium text-foreground">
                    {t(sim.request.paging_mode === 'periodic' ? 'ap.terms.periodicBaseline' : 'ap.terms.aperiodic')}
                  </span>
                </span>
                <span>
                  PPO:{' '}
                  <span className="font-medium text-foreground">
                    {sim.request.ppo_enabled ? t('ap.controls.on') : t('ap.controls.off')}
                  </span>
                </span>
                {result && <span className="font-mono">run {result.run_id}</span>}
              </p>
            </div>
            <div className="flex flex-wrap items-center justify-end gap-2">
              {pb.interactive && <Badge variant="secondary">t = {pb.time.toFixed(1)} s</Badge>}
              {pct != null && <Badge variant="secondary">{t('ap.stage.identified', { pct })}</Badge>}
              <LanguageToggle />
              <ThemeToggle />
              <Button disabled={sim.busy} onClick={() => applyPaper(true)}>
                {sim.busy
                  ? t('ap.common.running')
                  : t('ap.paperConfig.runPaper', { fig: t(`ap.paperRef.${paperFig}.label`) })}
              </Button>
            </div>
          </div>
          {pb.interactive && (
            <div className="mt-2 flex flex-wrap items-center gap-1" title={t('ap.factory.tracedHint')}>
              {pb.codes.map((code) => (
                <Badge key={code} variant="outline" className="h-5 gap-1 px-1.5 text-[10px] font-normal">
                  <i className="size-2 rounded-full" style={{ background: STATE_COLORS[code] }} />
                  {t(`ap.states.${code}`)} {pb.counts[code] ?? 0}
                </Badge>
              ))}
              <InfoIcon className="size-3.5 text-muted-foreground" aria-label={t('ap.factory.tracedHint')} />
            </div>
          )}
        </Card>
      </header>

      {sim.error ? (
        <div className="absolute top-28 left-1/2 z-40 max-w-lg -translate-x-1/2 rounded-lg border border-destructive bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {sim.error}
        </div>
      ) : null}

      <HudPanel
        dock={HudDock.Left}
        open={leftOpen}
        onOpenChange={setLeftOpen}
        label={t('hud.setup')}
        size={leftSize}
        onSizeChange={setLeftSize}
        minSize={280}
        maxSize={leftMax}
        defaultSize={LEFT_DEFAULT}
        inset={{ top: 12, left: 12, bottom: bottomClearance }}
      >
        <ScrollArea className="h-full">
          <div className="flex w-full min-w-0 max-w-full flex-col divide-y divide-border overflow-x-hidden">
            <div className="p-3">
              <AperiodicControls
                request={sim.request}
                setRequest={sim.setRequest}
                busy={sim.busy}
                backendUp={sim.backendUp}
                ppo={sim.ppo}
                lmax={sim.paper?.lmax.Lmax ?? 83}
                onRun={() => sim.run()}
                paperFig={paperFig}
                setPaperFig={setPaperFig}
                paperCurve={paperCurve}
                setPaperCurve={setPaperCurve}
                onPaper={applyPaper}
              />
            </div>
            <div className="p-3">
              <PpoStatusCard ppo={sim.ppo} />
            </div>
          </div>
        </ScrollArea>
      </HudPanel>

      <HudPanel
        dock={HudDock.Right}
        open={rightOpen}
        onOpenChange={setRightOpen}
        label={t('hud.inspect')}
        size={rightSize}
        onSizeChange={setRightSize}
        minSize={300}
        maxSize={rightMax}
        defaultSize={RIGHT_DEFAULT}
        inset={{ top: 12, right: 12, bottom: bottomClearance }}
      >
        <ScrollArea className="h-full">
          <div className="flex w-full min-w-0 flex-col divide-y divide-border">
            {pb.interactive && (
              <div className="p-3">
                <CurrentRoundCard pb={pb} />
              </div>
            )}
            {result?.cbra_inspect && result.cbra_inspect.length > 0 && (
              <div className="p-3">
                <AperiodicCBRAInspector rounds={result.cbra_inspect} />
              </div>
            )}
            {result && (
              <div className="p-3">
                <DeviceTracePanel result={result} selectedId={selectedId} onSelect={setSelectedId} />
              </div>
            )}
            {!result && <p className="p-3 text-xs text-muted-foreground">{t('ap.stage.empty')}</p>}
          </div>
        </ScrollArea>
      </HudPanel>

      <HudPanel
        dock={HudDock.Bottom}
        open={bottomOpen}
        onOpenChange={setBottomOpen}
        label={t('hud.plots')}
        size={bottomSize}
        onSizeChange={setBottomSize}
        minSize={200}
        maxSize={Math.max(200, bottomMax)}
        defaultSize={bottomDefault}
        inset={{ left: 12, right: 12, bottom: 12 }}
      >
        <div className="flex h-full min-h-0 gap-0 pt-2">
          <ScrollArea className="h-full min-w-0" style={{ width: `${split * 100}%` }}>
            <div className="grid gap-3 px-3 py-2">
              <PlaybackControls pb={pb} result={result} busy={sim.busy} />
              {result && result.warnings.length > 0 && (
                <ul className="grid gap-1 rounded-md border border-amber-500/40 bg-amber-500/10 p-2 text-xs text-amber-800 dark:text-amber-200">
                  {result.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              )}
              {result && <AperiodicMetrics result={result} />}
            </div>
          </ScrollArea>
          <HudSplit ratio={split} onRatioChange={setSplit} />
          <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2 px-3 py-2">
            <Segmented
              value={tab}
              onChange={setTab}
              options={[
                { value: 'inventory', label: t('ap.dock.inventory') },
                { value: 'rounds', label: t('ap.dock.rounds') },
                { value: 'repro', label: t('ap.dock.repro') },
              ]}
            />
            <div className="min-h-0 flex-1">
              {tab === 'repro' ? (
                <ScrollArea className="h-full">
                  <ReproductionPanel job={sim.job} reproduce={sim.reproduce} />
                </ScrollArea>
              ) : !result ? (
                <p className="text-xs text-muted-foreground">{sim.busy ? t('ap.common.running') : t('ap.stage.empty')}</p>
              ) : tab === 'inventory' ? (
                <AperiodicInventoryPlot result={result} time={pb.interactive ? pb.time : null} />
              ) : result.rounds.length > 0 ? (
                <RoundControllerPlot result={result} />
              ) : (
                <p className="text-xs text-muted-foreground">{t('ap.stage.batchNote')}</p>
              )}
            </div>
          </div>
        </div>
      </HudPanel>
    </div>
  )
}
