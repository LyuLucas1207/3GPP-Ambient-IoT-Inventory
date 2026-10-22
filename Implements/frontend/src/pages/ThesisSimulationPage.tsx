import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { LanguageToggle } from '@/components/LanguageToggle'
import { PaperNav } from '@/components/PaperNav'
import { ThemeToggle } from '@/components/ThemeToggle'
import { HudPanel } from '@/components/HudDock'
import { DeviceInspector } from '@/components/thesis/DeviceInspector'
import { ReaderInspector } from '@/components/thesis/ReaderInspector'
import { PlaceMenu, PlacementMenu } from '@/components/thesis/PlacementMenu'
import { RunCharts } from '@/components/thesis/RunCharts'
import { RunControlBar } from '@/components/thesis/RunControlBar'
import { ThesisRightPanel } from '@/components/thesis/ThesisRightPanel'
import { ThesisSidebar } from '@/components/thesis/ThesisSidebar'
import { ThesisSubNav } from '@/components/thesis/ThesisSubNav'
import { ThesisWarehouse } from '@/components/thesis/ThesisWarehouse'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useInventoryRuns } from '@/hooks/useInventoryRuns'
import { useLiveRun } from '@/hooks/useLiveRun'
import { useThesisScene } from '@/hooks/useThesisScene'
import { cloneParams, findCatalog } from '@/lib/thesisGeometry'
import { HudDock } from '@/types/hud'
import type { Kind, Placement, PlacementId, RunSummary } from '@/types/thesis'

const DOCK_SIZE_KEY = 'thesis.runDock.height'
const DOCK_MIN = 150
const DOCK_DEFAULT = 380

function readDockSize(): number {
  try {
    const v = Number(localStorage.getItem(DOCK_SIZE_KEY))
    return Number.isFinite(v) && v >= DOCK_MIN ? v : DOCK_DEFAULT
  } catch {
    return DOCK_DEFAULT
  }
}

type Menu =
  | { type: 'edit'; id: PlacementId; x: number; y: number }
  | { type: 'place'; x: number; y: number; worldX: number; worldY: number }

export default function ThesisSimulationPage() {
  const { t } = useTranslation()
  const studio = useThesisScene()
  const scene = studio.scene
  const sceneKey = `${scene?.id ?? 'none'}:${scene?.saved ?? false}:${scene?.nonce ?? 0}`
  const runs = useInventoryRuns(scene?.id ?? null)
  const live = useLiveRun(runs.selectedRunId, runs.selectedRun?.status, () => void runs.refreshRuns())
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | null>(null)
  const [inspectedReaderId, setInspectedReaderId] = useState<number | null>(null)
  const [chartReader, setChartReader] = useState<number | 'all'>('all')
  function inspectReader(id: number | null) {
    setInspectedReaderId(id)
    setFocusReaderId(id)
    setChartReader(id ?? 'all')
    if (id != null) setSelectedDeviceId(null)
  }
  function inspectDevice(id: number | null) {
    setSelectedDeviceId(id)
    if (id != null) setInspectedReaderId(null)
  }
  const [dockOpen, setDockOpen] = useState(true)
  const [dockSize, setDockSize] = useState(readDockSize)
  const mainRef = useRef<HTMLElement>(null)
  const [mainHeight, setMainHeight] = useState(800)
  useEffect(() => {
    const node = mainRef.current
    if (!node) return
    const observer = new ResizeObserver(() => setMainHeight(node.clientHeight))
    observer.observe(node)
    setMainHeight(node.clientHeight)
    return () => observer.disconnect()
  }, [])
  function resizeDock(size: number) {
    setDockSize(size)
    try {
      localStorage.setItem(DOCK_SIZE_KEY, String(Math.round(size)))
    } catch {
      /* per-viewer convenience only */
    }
  }
  const [menu, setMenu] = useState<Menu | null>(null)
  const [selecting, setSelecting] = useState(false)
  const [picked, setPicked] = useState<string[]>([])
  const [focusReaderId, setFocusReaderId] = useState<PlacementId | null>(null)
  const [menuKey, setMenuKey] = useState(sceneKey)
  if (menuKey !== sceneKey) {
    setMenuKey(sceneKey)
    setMenu(null)
    setPicked([])
    setSelecting(false)
    setFocusReaderId(null)
    setSelectedDeviceId(null)
    setInspectedReaderId(null)
    setChartReader('all')
  }

  useEffect(() => {
    document.title = t('thesis.documentTitle')
  }, [t])

  const selected = menu?.type === 'edit' ? scene?.placements.find((item) => item.id === menu.id) : undefined
  const inspected =
    selectedDeviceId != null ? scene?.placements.find((p) => p.id === selectedDeviceId && p.kind === 'device') ?? null : null
  // The selected run's card follows the SSE feed instead of polling the list.
  const liveSummary = (r: RunSummary): RunSummary =>
    // Not while replaying: the stream state then shows a past snapshot.
    r.run_id === runs.selectedRunId && live.status && live.viewTime == null
      ? {
          ...r,
          status: live.status,
          identified_total: live.counters.identified ?? r.identified_total,
          rounds_total: live.counters.rounds ?? r.rounds_total,
          died_count: live.counters.depletions ?? r.died_count,
          sim_time_s: live.simTime || r.sim_time_s,
        }
      : r
  const panelRuns = runs.runs.map(liveSummary)
  const selectedRun = runs.selectedRun ? liveSummary(runs.selectedRun) : null
  const inspectedReader =
    inspectedReaderId != null && selectedRun
      ? scene?.placements.find((p) => p.id === inspectedReaderId && p.kind === 'radar') ?? null
      : null

  function place(kind: Kind, subtype: string | null) {
    if (!menu || menu.type !== 'place') return
    const entry = findCatalog(studio.catalog, kind, subtype)
    if (!entry) return
    void studio.addOne({
      kind,
      subtype,
      x_m: menu.worldX,
      y_m: menu.worldY,
      params: cloneParams(entry.defaults),
    })
    setMenu(null)
  }

  return (
    <div className="flex h-dvh w-screen flex-col overflow-hidden bg-background">
      <header className="flex w-full shrink-0 items-center gap-4 border-b bg-card px-4 py-2">
        <div className="min-w-0">
          <PaperNav className="mb-1" />
          <div className="flex items-center gap-3">
            <h1 className="truncate text-lg font-medium">{t('thesis.title')}</h1>
            <ThesisSubNav />
          </div>
          <p className="truncate text-xs text-muted-foreground">{t('thesis.subtitle')}</p>
        </div>
        <div className="ml-auto flex flex-wrap items-center justify-end gap-2">
          <Badge variant={scene?.status === 'initialized' ? 'secondary' : 'outline'}>
            {!scene
              ? t('thesis.statusEmpty')
              : t(`thesis.sectionStatus.${scene.status ?? 'initializing'}`)}
          </Badge>
          <Button
            type="button"
            disabled={!scene || scene.status === 'initialized' || studio.busy}
            onClick={() => void (scene?.saved ? studio.markInitialized() : studio.save())}
          >
            {t('thesis.save')}
          </Button>
          <LanguageToggle />
          <ThemeToggle />
        </div>
      </header>
      {studio.error ? (
        <div className="flex items-center justify-between gap-3 border-b bg-destructive/10 px-4 py-2 text-sm text-destructive">
          <span>{studio.error}</span>
          <Button type="button" size="xs" variant="ghost" onClick={studio.clearError}>
            {t('thesis.dismiss')}
          </Button>
        </div>
      ) : null}
      <div className="flex min-h-0 flex-1">
        <ThesisSidebar
          catalog={studio.catalog}
          pristineCatalog={studio.pristineCatalog}
          scenarioDefaults={studio.scenarioDefaults}
          sections={studio.sections}
          scene={scene}
          busy={studio.busy}
          onCreate={studio.createSavedSection}
          onOpen={(id) => void studio.openSection(id)}
          onDelete={studio.removeSection}
          onApplySize={(width, height) => void studio.applySize(width, height)}
          onMarkerScale={(scale) => void studio.setMarkerScale(scale)}
          onDeviceMarkerScale={(scale) => void studio.setDeviceMarkerScale(scale)}
          onAddDevices={studio.addRandomDevices}
          onAddStations={studio.addRandomStations}
          onAddStationGrid={studio.addStationGrid}
          onApplyStandardLayout={studio.applyStandardLayout}
          onClearDevices={() => studio.clearPlacements('device')}
          onClearInfra={() => studio.clearPlacements('infra')}
          onCatalogValue={studio.setCatalogValue}
          onResetCatalog={studio.resetCatalog}
          onApplyKind={(kind, subtype, params) => void studio.applyKindParams(kind, subtype, params)}
          selecting={selecting}
          pickedCount={picked.length}
          onToggleSelecting={() => {
            setSelecting((value) => !value)
            setMenu(null)
          }}
          onPickEvery={(gapX, gapY) => {
            setSelecting(true)
            setPicked(everyStation(scene?.placements ?? [], gapX, gapY))
          }}
          onConvert={(kind) => {
            const ids = (scene?.placements ?? [])
              .filter((item) => picked.includes(String(item.id)) && item.kind !== 'device' && item.kind !== kind)
              .map((item) => item.id)
            void studio.convertPlacements(ids, kind)
            setPicked([])
          }}
          onClearPicked={() => setPicked([])}
          onLeaveSelect={() => {
            setSelecting(false)
            setPicked([])
          }}
        />
        <main ref={mainRef} className="relative min-w-0 flex-1 overflow-hidden">
          <ThesisWarehouse
            scene={scene}
            catalog={studio.catalog}
            selectedId={selected ? String(selected.id) : null}
            focusReaderId={focusReaderId}
            markerScale={scene?.markerScale ?? 0.7}
            deviceMarkerScale={scene?.deviceMarkerScale ?? 0.3}
            live={runs.selectedRunId != null ? live.devices : null}
            selectedDeviceId={selectedDeviceId}
            onSelectDevice={inspectDevice}
            onSelectReader={selectedRun ? (id) => inspectReader(id) : undefined}
            selecting={selecting}
            pickedIds={picked}
            onTogglePick={(id) => {
              const key = String(id)
              setPicked((prev) => (prev.includes(key) ? prev.filter((item) => item !== key) : [...prev, key]))
            }}
            onEdit={(id, x, y) => setMenu({ type: 'edit', id, x, y })}
            onPlace={(worldX, worldY, x, y) => setMenu({ type: 'place', worldX, worldY, x, y })}
          />
          {scene && inspected ? (
            <DeviceInspector
              scene={scene}
              placement={inspected}
              live={runs.selectedRunId != null ? live.devices : null}
              runId={runs.selectedRunId}
              runStatus={live.status ?? selectedRun?.status ?? null}
              onClose={() => setSelectedDeviceId(null)}
            />
          ) : null}
          {inspectedReader && selectedRun ? (
            <ReaderInspector
              reader={inspectedReader}
              runId={selectedRun.run_id}
              runStatus={live.status ?? selectedRun.status}
              rounds={live.viewTime == null ? live.rounds : live.rounds.filter((r) => r.t_start_s <= (live.viewTime ?? 0))}
              devices={live.devices}
              onClose={() => inspectReader(null)}
            />
          ) : null}
          {scene && selectedRun ? (
            <HudPanel
              dock={HudDock.Bottom}
              open={dockOpen}
              onOpenChange={setDockOpen}
              label={t('thesis.live.dock')}
              size={Math.min(dockSize, Math.max(DOCK_MIN, mainHeight - 72))}
              onSizeChange={resizeDock}
              minSize={DOCK_MIN}
              maxSize={Math.max(DOCK_MIN, mainHeight - 72)}
              defaultSize={DOCK_DEFAULT}
              inset={{ left: 12, right: inspected || inspectedReader ? 452 : 56, bottom: 12 }}
            >
              <div className="flex h-full min-h-0 flex-col gap-2 p-2 pt-3">
                <RunControlBar
                  run={selectedRun}
                  live={live}
                  busy={runs.busy}
                  onPause={() => void runs.pauseRun(selectedRun.run_id)}
                  onResume={() => void runs.resumeRun(selectedRun.run_id)}
                  onStop={() => void runs.stopRun(selectedRun.run_id)}
                  onSpeed={(speed) => void runs.setSpeed(selectedRun.run_id, speed)}
                />
                <div className="min-h-0 flex-1">
                  <RunCharts
                    runId={selectedRun.run_id}
                    scheme={selectedRun.scheme}
                    scene={scene}
                    live={live}
                    totalDevices={live.counters.total ?? selectedRun.total_devices}
                    reader={chartReader}
                    onReader={setChartReader}
                  />
                </div>
              </div>
            </HudPanel>
          ) : null}
        </main>
        <ThesisRightPanel
          scene={scene}
          focusReaderId={focusReaderId}
          onFocus={setFocusReaderId}
          runs={panelRuns}
          selectedRunId={runs.selectedRunId}
          runsBusy={runs.busy}
          onSelectRun={runs.setSelectedRunId}
          onCreateRun={runs.createRun}
          onDeleteRun={runs.deleteRun}
          onStopRun={runs.stopRun}
          onPauseRun={runs.pauseRun}
          onResumeRun={runs.resumeRun}
        />
      </div>
      {menu?.type === 'place' ? (
        <PlaceMenu anchor={{ x: menu.x, y: menu.y }} onClose={() => setMenu(null)} onPick={place} />
      ) : null}
      {menu?.type === 'edit' && selected ? (
        <PlacementMenu
          placement={selected}
          catalog={studio.catalog}
          pristineCatalog={studio.pristineCatalog}
          anchor={{ x: menu.x, y: menu.y }}
          busy={studio.busy}
          locked={scene?.locked ?? false}
          runSelected={runs.selectedRunId != null}
          onClose={() => setMenu(null)}
          onApply={(input) => {
            void studio.updatePlacement(selected.id, input)
            setMenu(null)
          }}
          onDelete={() => {
            void studio.deletePlacement(selected.id)
            setMenu(null)
          }}
          onViewHistory={() => {
            if (selected.kind === 'device' && typeof selected.id === 'number') setSelectedDeviceId(selected.id)
            setMenu(null)
          }}
        />
      ) : null}
    </div>
  )
}

function everyStation(placements: Placement[], gapX: number, gapY: number) {
  const stepX = Math.max(1, Math.floor(gapX) + 1)
  const stepY = Math.max(1, Math.floor(gapY) + 1)
  const nodes = placements.filter((item) => item.kind === 'station' || item.kind === 'radar')
  const xs = axisIndex(nodes.map((item) => item.x_m))
  const ys = axisIndex(nodes.map((item) => item.y_m))
  return nodes
    .filter((item) => item.kind === 'station' && xs.get(axisKey(item.x_m))! % stepX === 0 && ys.get(axisKey(item.y_m))! % stepY === 0)
    .map((item) => String(item.id))
}

function axisKey(value: number) {
  return Math.round(value * 1000) / 1000
}

function axisIndex(values: number[]) {
  const sorted = [...new Set(values.map(axisKey))].sort((a, b) => a - b)
  return new Map(sorted.map((value, index) => [value, index]))
}
