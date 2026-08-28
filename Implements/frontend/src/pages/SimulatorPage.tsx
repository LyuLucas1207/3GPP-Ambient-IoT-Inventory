import { useEffect, useState } from 'react'
import { PauseIcon, PlayIcon } from 'lucide-react'
import { AssumptionsPanel } from '@/components/AssumptionsPanel'
import { CBRAInspector } from '@/components/CBRAInspector'
import { DeviceAnatomy } from '@/components/DeviceAnatomy'
import { DeviceInspector } from '@/components/DeviceInspector'
import { EnergyHistory } from '@/components/EnergyHistory'
import { FactoryView, STATE_COLORS, STATE_SOURCE } from '@/components/FactoryView'
import { HudPanel, HudSplit } from '@/components/HudDock'
import { InventoryCurve } from '@/components/InventoryCurve'
import { LanguageToggle } from '@/components/LanguageToggle'
import { MetricsPanel } from '@/components/MetricsPanel'
import { SimulationControls } from '@/components/SimulationControls'
import { ThemeToggle } from '@/components/ThemeToggle'
import { HoverHelp } from '@/components/HoverHelp'
import { OverviewFlowButton } from '@/components/OverviewFlowDialog'
import { ExplainButton } from '@/components/ViewExplanationDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Slider } from '@/components/ui/slider'
import { useSimulation } from '@/hooks/useSimulation'
import { HudDock } from '@/types/hud'
import { DeviceType, DeviceVizState, StrategyKey } from '@/types/simulation'
import { ViewId } from '@/explain/ids'
import { useTranslation } from 'react-i18next'

const LEFT_DEFAULT = 320
const RIGHT_DEFAULT = 336
const TAB_GUTTER = 52

function defaultBottomHeight(viewportH: number) {
  return Math.max(180, Math.floor(viewportH / 3))
}

function SimulatorPage() {
  const { t, i18n } = useTranslation()
  const sim = useSimulation()
  const devices = sim.result?.static_devices ?? []
  const reader = sim.result?.reader ?? { x: 60, y: 30, tx_dbm: 33 }
  const selected = devices.find((d) => d.id === sim.selectedId) ?? null
  const snap = sim.currentSnapshot
  const inventoried = snap ? snap.inventoried.filter(Boolean).length : 0
  const n = devices.length
  const counts = countStates(snap?.state ?? [])

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
    document.title = t('app.documentTitle')
  }, [t, i18n.language])

  useEffect(() => {
    const update = () => setViewport({ w: window.innerWidth, h: window.innerHeight })
    update()
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [])

  useEffect(() => {
    if (sim.selectedId != null) setRightOpen(true)
  }, [sim.selectedId])

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

  const runPaper = () => {
    sim.resetPaper()
    void sim.run({
      num_devices: 600,
      device_type: DeviceType.Device1,
      strategies: [StrategyKey.EM, StrategyKey.DCM_1_GROUP, StrategyKey.DCM_4_GROUP],
      seed: 42,
      max_time_s: 25,
    })
  }

  const bottomClearance = bottomOpen ? bottomSize + 20 : 20
  const leftMax = Math.min(480, Math.floor(viewport.w * 0.42))
  const rightMax = Math.min(480, Math.floor(viewport.w * 0.42))
  const bottomMax = Math.min(Math.floor(viewport.h * 0.72), viewport.h - 96)
  const bottomDefault = Math.min(Math.max(180, bottomMax), defaultBottomHeight(viewport.h))
  const headerLeft = leftOpen ? leftSize + 24 : TAB_GUTTER
  const headerRight = rightOpen ? rightSize + 24 : TAB_GUTTER

  return (
    <div className="relative h-dvh w-screen overflow-hidden bg-background">
      <FactoryView
        devices={devices}
        snapshot={snap}
        reader={reader}
        selectedId={sim.selectedId}
        onSelect={sim.setSelectedId}
        pad={{
          top: 108,
          right: rightOpen ? rightSize + 24 : TAB_GUTTER,
          bottom: bottomOpen ? bottomSize + 24 : TAB_GUTTER,
          left: leftOpen ? leftSize + 24 : TAB_GUTTER,
        }}
      />

      <header
        className="absolute z-30"
        style={{ top: 12, left: headerLeft, right: headerRight }}
      >
        <Card className="bg-card/90 px-4 py-2.5 backdrop-blur-md" size="sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="text-[11px] tracking-[0.16em] text-muted-foreground uppercase">{t('app.kicker')}</p>
              <h1 className="flex flex-wrap items-center gap-2 text-lg font-medium">
                <span className="min-w-0">{t('app.title')}</span>
                <ExplainButton view={ViewId.Factory} />
                <OverviewFlowButton />
              </h1>
              <p className="truncate text-xs text-muted-foreground">{t('app.subtitle')}</p>
            </div>
            <div className="flex flex-wrap items-center justify-end gap-2">
              <Badge variant="secondary">{t('app.time', { value: snap ? snap.time_s.toFixed(2) : '0.00' })}</Badge>
              <Badge variant="secondary">
                {t('app.done', { value: n ? ((100 * inventoried) / n).toFixed(1) : '0.0' })}
              </Badge>
              <Badge variant="outline">{t('state.ON')} {counts[DeviceVizState.ON]}</Badge>
              <Badge variant="outline">{t('state.SLEEP')} {counts[DeviceVizState.SLEEP]}</Badge>
              <Badge variant="outline">{t('state.OFF')} {counts[DeviceVizState.OFF]}</Badge>
              <Badge variant="outline">{t('state.DONE')} {counts[DeviceVizState.DONE]}</Badge>
              <LanguageToggle />
              <ThemeToggle />
              <Button disabled={sim.busy} onClick={runPaper}>
                {sim.busy ? t('common.running') : t('app.runPaper')}
              </Button>
            </div>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
              {Object.entries(STATE_COLORS).map(([k, c]) => (
                <HoverHelp
                  key={k}
                  title={t(`state.${k}`)}
                  paper={t(`factory.stateHelp.${k}.paper`)}
                  ui={t(`factory.stateHelp.${k}.ui`)}
                  source={STATE_SOURCE[k as DeviceVizState]}
                >
                  <Badge variant="outline" className="cursor-help gap-1.5">
                    <i className="size-2 rounded-full" style={{ background: c }} />
                    {t(`state.${k}`)}
                  </Badge>
                </HoverHelp>
              ))}
            </div>
        </Card>
      </header>

      {sim.error ? (
        <div className="absolute top-24 left-1/2 z-40 max-w-lg -translate-x-1/2 rounded-lg border border-destructive bg-destructive/10 px-3 py-2 text-sm text-destructive">
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
        minSize={260}
        maxSize={leftMax}
        defaultSize={LEFT_DEFAULT}
        inset={{ top: 12, left: 12, bottom: bottomClearance }}
      >
        <ScrollArea className="h-full">
          <div className="grid gap-3 p-3">
            <SimulationControls
              request={sim.request}
              setRequest={sim.setRequest}
              busy={sim.busy}
              backendUp={sim.backendUp}
              onRun={() => void sim.run()}
              onPaper={runPaper}
            />
            <AssumptionsPanel
              paper={sim.result?.paper_parameters ?? sim.paper?.paper_parameters ?? null}
              assumptions={
                sim.result?.reproduction_assumptions ?? sim.paper?.reproduction_assumptions ?? null
              }
            />
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
        minSize={260}
        maxSize={rightMax}
        defaultSize={RIGHT_DEFAULT}
        inset={{ top: 12, right: 12, bottom: bottomClearance }}
      >
        <ScrollArea className="h-full">
          <div className="grid gap-3 p-3">
            <DeviceAnatomy deviceType={sim.request.device_type} />
            <DeviceInspector device={selected} stats={sim.selectedStats} snapshot={snap} />
            <EnergyHistory
              deviceId={sim.selectedId}
              result={sim.result}
              strategy={sim.viewStrategy}
            />
            <CBRAInspector
              events={sim.events}
              index={sim.pagingIndex}
              setIndex={sim.setPagingIndex}
              result={sim.result}
              strategy={sim.viewStrategy}
              playbackTimeS={snap?.time_s ?? null}
            />
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
        minSize={180}
        maxSize={Math.max(180, bottomMax)}
        defaultSize={bottomDefault}
        inset={{ left: 12, right: 12, bottom: 12 }}
      >
        <div className="flex h-full min-h-0 gap-0 pt-2">
          <Card className="h-full min-h-0 min-w-0 bg-transparent ring-0" size="sm" style={{ width: `${split * 100}%` }}>
            <CardHeader>
              <CardTitle>{t('playback.title')}</CardTitle>
              <CardDescription>{t('playback.subtitle')}</CardDescription>
            </CardHeader>
            <CardContent className="grid min-h-0 flex-1 gap-3 overflow-auto">
              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  size="icon"
                  disabled={sim.snapshots.length === 0}
                  onClick={() => sim.setPlaying(!sim.playing)}
                  aria-label={sim.playing ? t('common.pause') : t('common.play')}
                >
                  {sim.playing ? <PauseIcon /> : <PlayIcon />}
                </Button>
                <Slider
                  className="flex-1"
                  min={0}
                  max={Math.max(1, sim.snapshots.length - 1)}
                  disabled={sim.snapshots.length < 2}
                  value={[sim.frame]}
                  onValueChange={(v) => {
                    sim.setPlaying(false)
                    const next = Array.isArray(v) ? v[0] : v
                    if (typeof next === 'number') sim.setFrame(next)
                  }}
                />
                <Select
                  value={sim.viewStrategy}
                  items={{
                    [StrategyKey.EM]: t(`strategy.${StrategyKey.EM}`),
                    [StrategyKey.DCM_1_GROUP]: t(`strategy.${StrategyKey.DCM_1_GROUP}`),
                    [StrategyKey.DCM_4_GROUP]: t(`strategy.${StrategyKey.DCM_4_GROUP}`),
                  }}
                  onValueChange={(v) => {
                    if (
                      v === StrategyKey.EM ||
                      v === StrategyKey.DCM_1_GROUP ||
                      v === StrategyKey.DCM_4_GROUP
                    ) {
                      sim.setViewStrategy(v)
                    }
                  }}
                >
                  <SelectTrigger className="w-48 shrink-0" aria-label={t('playback.title')}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent align="end" alignItemWithTrigger className="z-[80]">
                    {Object.values(StrategyKey).map((k) => (
                      <SelectItem key={k} value={k}>
                        {t(`strategy.${k}`)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <MetricsPanel result={sim.result} />
            </CardContent>
          </Card>
          <HudSplit ratio={split} onRatioChange={setSplit} />
          <div className="min-h-0 min-w-0 flex-1">
            <InventoryCurve result={sim.result} />
          </div>
        </div>
      </HudPanel>
    </div>
  )
}

function countStates(states: DeviceVizState[]) {
  const out: Record<DeviceVizState, number> = {
    [DeviceVizState.OFF]: 0,
    [DeviceVizState.ON]: 0,
    [DeviceVizState.SLEEP]: 0,
    [DeviceVizState.ACCESS]: 0,
    [DeviceVizState.COLLISION]: 0,
    [DeviceVizState.DONE]: 0,
  }
  for (const s of states) {
    out[s] += 1
  }
  return out
}

export default SimulatorPage
