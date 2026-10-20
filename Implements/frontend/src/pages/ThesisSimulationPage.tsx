import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { LanguageToggle } from '@/components/LanguageToggle'
import { PaperNav } from '@/components/PaperNav'
import { ThemeToggle } from '@/components/ThemeToggle'
import { PlaceMenu, PlacementMenu } from '@/components/thesis/PlacementMenu'
import { ThesisSidebar } from '@/components/thesis/ThesisSidebar'
import { ThesisWarehouse } from '@/components/thesis/ThesisWarehouse'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useThesisScene } from '@/hooks/useThesisScene'
import { cloneParams, findCatalog } from '@/lib/thesisGeometry'
import type { Kind, Placement, PlacementId } from '@/types/thesis'

type Menu =
  | { type: 'edit'; id: PlacementId; x: number; y: number }
  | { type: 'place'; x: number; y: number; worldX: number; worldY: number }

export default function ThesisSimulationPage() {
  const { t } = useTranslation()
  const studio = useThesisScene()
  const scene = studio.scene
  const sceneKey = `${scene?.id ?? 'none'}:${scene?.saved ?? false}:${scene?.nonce ?? 0}`
  const [menu, setMenu] = useState<Menu | null>(null)
  const [selecting, setSelecting] = useState(false)
  const [picked, setPicked] = useState<string[]>([])
  const [menuKey, setMenuKey] = useState(sceneKey)
  if (menuKey !== sceneKey) {
    setMenuKey(sceneKey)
    setMenu(null)
    setPicked([])
    setSelecting(false)
  }

  useEffect(() => {
    document.title = t('thesis.documentTitle')
  }, [t])

  const selected = menu?.type === 'edit' ? scene?.placements.find((item) => item.id === menu.id) : undefined

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
          <h1 className="truncate text-lg font-medium">{t('thesis.title')}</h1>
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
        <main className="relative min-w-0 flex-1">
          <ThesisWarehouse
            scene={scene}
            catalog={studio.catalog}
            selectedId={selected ? String(selected.id) : null}
            markerScale={scene?.markerScale ?? 0.7}
            deviceMarkerScale={scene?.deviceMarkerScale ?? 0.3}
            selecting={selecting}
            pickedIds={picked}
            onTogglePick={(id) => {
              const key = String(id)
              setPicked((prev) => (prev.includes(key) ? prev.filter((item) => item !== key) : [...prev, key]))
            }}
            onEdit={(id, x, y) => setMenu({ type: 'edit', id, x, y })}
            onPlace={(worldX, worldY, x, y) => setMenu({ type: 'place', worldX, worldY, x, y })}
          />
        </main>
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
          onClose={() => setMenu(null)}
          onApply={(input) => {
            void studio.updatePlacement(selected.id, input)
            setMenu(null)
          }}
          onDelete={() => {
            void studio.deletePlacement(selected.id)
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
