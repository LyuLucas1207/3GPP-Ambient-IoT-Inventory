import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Layers } from 'lucide-react'
import { MarkerShape } from '@/components/thesis/MarkerShape'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { inside } from '@/lib/thesisGeometry'
import type { Kind, Placement, Scene, Shape } from '@/types/thesis'

const LAYER_KEYS = ['device1', 'device2a', 'device2b', 'radar', 'station'] as const
type LayerKey = (typeof LAYER_KEYS)[number]
type Layers = Record<LayerKey, boolean>

const LAYER_LABEL: Record<LayerKey, string> = {
  device1: 'thesis.showDevice1',
  device2a: 'thesis.showDevice2a',
  device2b: 'thesis.showDevice2b',
  radar: 'thesis.showRadar',
  station: 'thesis.showStation',
}

const FILL: Record<string, string> = {
  'device:1': 'fill-[#1d4ed8]',
  'device:2a': 'fill-[#0f766e]',
  'device:2b': 'fill-[#c2410c]',
  station: 'fill-[#6d28d9]',
  radar: 'fill-[#b91c1c]',
}

export function ThesisWarehouse({
  scene,
  selectedId,
  markerScale,
  selecting = false,
  pickedIds = [],
  onTogglePick,
  onEdit,
  onPlace,
}: {
  scene: Scene | null
  selectedId: string | null
  markerScale: number
  selecting?: boolean
  pickedIds?: string[]
  onTogglePick?: (id: Placement['id']) => void
  onEdit: (id: Placement['id'], clientX: number, clientY: number) => void
  onPlace: (x: number, y: number, clientX: number, clientY: number) => void
}) {
  const { t } = useTranslation()
  const hostRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ vw: 0, vh: 0 })
  const [view, setView] = useState({ zoom: 1, panX: 0, panY: 0 })
  const viewRef = useRef(view)
  useEffect(() => {
    viewRef.current = view
  }, [view])
  const drag = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null)
  const layersRef = useRef<HTMLDivElement>(null)
  const layersContentRef = useRef<HTMLDivElement>(null)
  const [layersOpen, setLayersOpen] = useState(false)
  const [layersSize, setLayersSize] = useState({ width: 176, height: 36 })
  const [layers, setLayers] = useState<Layers>({
    device1: true,
    device2a: true,
    device2b: true,
    radar: true,
    station: true,
  })

  useLayoutEffect(() => {
    const node = layersContentRef.current
    if (!node) return
    const measure = () => {
      const width = node.offsetWidth
      const height = node.offsetHeight
      if (width < 1 || height < 1) return
      setLayersSize((prev) => (prev.width === width && prev.height === height ? prev : { width, height }))
    }
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(node)
    return () => observer.disconnect()
  }, [t])

  useEffect(() => {
    if (!layersOpen) return
    const onPointerDown = (event: PointerEvent) => {
      if (layersRef.current?.contains(event.target as Node)) return
      setLayersOpen(false)
      event.stopPropagation()
      event.preventDefault()
    }
    window.addEventListener('pointerdown', onPointerDown, true)
    return () => window.removeEventListener('pointerdown', onPointerDown, true)
  }, [layersOpen])

  useEffect(() => {
    const host = hostRef.current
    if (!host) return
    const observer = new ResizeObserver(() => {
      setSize({ vw: host.clientWidth, vh: host.clientHeight })
    })
    observer.observe(host)
    setSize({ vw: host.clientWidth, vh: host.clientHeight })
    return () => observer.disconnect()
  }, [])

  const fittedFloor = useRef('')
  useEffect(() => {
    if (!scene || size.vw < 10 || size.vh < 10) {
      if (!scene) fittedFloor.current = ''
      return
    }
    const key = `${scene.width_m}x${scene.height_m}:${Math.round(size.vw)}x${Math.round(size.vh)}:square`
    if (fittedFloor.current === key) return
    fittedFloor.current = key
    const scale = meterScale(size.vw, size.vh, scene.width_m, scene.height_m, 1)
    setView(centeredPan(size.vw, size.vh, scene.width_m, scene.height_m, scale))
  }, [scene, size.vw, size.vh])

  useEffect(() => {
    const host = hostRef.current
    if (!host || !scene) return
    const onWheel = (event: WheelEvent) => {
      event.preventDefault()
      const rect = host.getBoundingClientRect()
      const sx = event.clientX - rect.left
      const sy = event.clientY - rect.top
      const current = viewRef.current
      const now = meterScale(rect.width, rect.height, scene.width_m, scene.height_m, current.zoom)
      const worldX = (sx - current.panX) / now
      const worldY = scene.height_m - (sy - current.panY) / now
      const nextZoom = clamp(current.zoom * (event.deltaY < 0 ? 1.08 : 1 / 1.08), 0.25, 12)
      const nextScale = meterScale(rect.width, rect.height, scene.width_m, scene.height_m, nextZoom)
      const next = {
        zoom: nextZoom,
        panX: sx - worldX * nextScale,
        panY: sy - (scene.height_m - worldY) * nextScale,
      }
      viewRef.current = next
      setView(next)
    }
    host.addEventListener('wheel', onWheel, { passive: false })
    return () => host.removeEventListener('wheel', onWheel)
  }, [scene, size.vw, size.vh])

  const scale = scene ? meterScale(size.vw, size.vh, scene.width_m, scene.height_m, view.zoom) : 1
  const visible = scene
    ? visibleWorld(size.vw, size.vh, scene.height_m, view.panX, view.panY, scale, scale)
    : { x0: 0, x1: 1, y0: 0, y1: 1 }

  function screenToWorld(clientX: number, clientY: number) {
    const rect = hostRef.current?.getBoundingClientRect()
    if (!rect || !scene) return null
    const sx = clientX - rect.left
    const sy = clientY - rect.top
    return {
      x: (sx - view.panX) / scale,
      y: scene.height_m - (sy - view.panY) / scale,
    }
  }

  function fitView() {
    if (!scene || size.vw < 10) return
    fittedFloor.current = `${scene.width_m}x${scene.height_m}:${Math.round(size.vw)}x${Math.round(size.vh)}:square`
    const scale = meterScale(size.vw, size.vh, scene.width_m, scene.height_m, 1)
    setView(centeredPan(size.vw, size.vh, scene.width_m, scene.height_m, scale))
  }

  return (
    <div ref={hostRef} className="relative h-full min-h-0 w-full overflow-hidden bg-background">
      {scene ? (
        <svg
          className="h-full w-full touch-none"
          onPointerDown={(event) => {
            if (event.button !== 0) return
            if ((event.target as Element).closest('[data-placement]')) return
            drag.current = { x: event.clientX, y: event.clientY, panX: view.panX, panY: view.panY }
            event.currentTarget.setPointerCapture(event.pointerId)
          }}
          onPointerMove={(event) => {
            const current = drag.current
            if (!current) return
            setView((prev) => {
              const next = {
                ...prev,
                panX: current.panX + event.clientX - current.x,
                panY: current.panY + event.clientY - current.y,
              }
              viewRef.current = next
              return next
            })
          }}
          onPointerUp={() => {
            drag.current = null
          }}
          onContextMenu={(event) => {
            event.preventDefault()
            const hit = (event.target as Element).closest('[data-placement]')
            if (hit) {
              const raw = hit.getAttribute('data-placement')
              const placement = scene.placements.find((item) => String(item.id) === raw)
              if (placement) onEdit(placement.id, event.clientX, event.clientY)
              return
            }
            const world = screenToWorld(event.clientX, event.clientY)
            if (selecting) return
            if (!world || !inside(world.x, world.y, scene.width_m, scene.height_m)) return
            onPlace(world.x, world.y, event.clientX, event.clientY)
          }}
        >
          <rect width="100%" height="100%" className="fill-foreground/4" />
          <g transform={`translate(${view.panX} ${view.panY}) scale(${scale} ${scale})`}>
            <g transform={`translate(0 ${scene.height_m}) scale(1 -1)`}>
              {gridLines(visible)}
              <FloorAxes
                width={scene.width_m}
                height={scene.height_m}
                bounds={visible}
                scaleX={scale}
                scaleY={scale}
                xLabel={t('factory.xAxis')}
                yLabel={t('factory.yAxis')}
              />
              <rect
                width={scene.width_m}
                height={scene.height_m}
                fill="none"
                className="pointer-events-none stroke-foreground"
                strokeWidth={1.5}
                strokeDasharray="6 4"
                vectorEffect="non-scaling-stroke"
              />
              {scene.placements.map((placement) => {
                if (placement.kind !== 'radar' && placement.kind !== 'station') return null
                if (placement.kind === 'radar' && !layers.radar) return null
                if (placement.kind === 'station' && !layers.station) return null
                if (placement.params.show_range !== true) return null
                const fallback = placement.kind === 'radar' ? 30 : 20
                const radius = Number(placement.params.radius_m)
                const range = Number.isFinite(radius) && radius > 0 ? radius : fallback
                const radar = placement.kind === 'radar'
                return (
                  <circle
                    key={`range-${placement.id}`}
                    cx={placement.x_m}
                    cy={placement.y_m}
                    r={range}
                    className={radar ? 'fill-[#b91c1c]/15 stroke-[#b91c1c]' : 'fill-[#6d28d9]/12 stroke-[#6d28d9]'}
                    strokeDasharray={radar ? '6 4' : undefined}
                    strokeWidth={1.5}
                    vectorEffect="non-scaling-stroke"
                  />
                )
              })}
              {scene.placements.map((placement) => {
                if (!layerVisible(placement, layers)) return null
                const beacon = placement.kind !== 'device'
                const tone = beaconTone(placement)
                const picked = pickedIds.includes(String(placement.id))
                const size = (beacon ? 0.85 : 0.42) * markerScale * (selectedId === String(placement.id) ? 1.15 : 1)
                return (
                  <g
                    key={placement.id}
                    data-placement={placement.id}
                    transform={`translate(${placement.x_m} ${placement.y_m})`}
                    className="cursor-pointer"
                    onClick={(event) => {
                      event.stopPropagation()
                      if (selecting && placement.kind !== 'device') {
                        onTogglePick?.(placement.id)
                        return
                      }
                      onEdit(placement.id, event.clientX, event.clientY)
                    }}
                  >
                    {picked ? (
                      <circle r={size * 2.2} className="fill-none stroke-foreground" strokeWidth={2} vectorEffect="non-scaling-stroke" />
                    ) : null}
                    {beacon ? (
                      <>
                        <PulseRing size={size} tone={tone} delay={beaconDelay(placement.id)} />
                        <PulseRing size={size} tone={tone} delay={beaconDelay(placement.id) + 1400} />
                      </>
                    ) : null}
                    <g opacity={beacon ? 0.85 : 1}>
                      {beacon ? (
                        <animate
                          attributeName="opacity"
                          values="0.68;1;0.68"
                          keyTimes="0;0.5;1"
                          calcMode="spline"
                          keySplines="0.42 0 0.58 1;0.42 0 0.58 1"
                          dur="3.6s"
                          begin={`${beaconDelay(placement.id)}ms`}
                          repeatCount="indefinite"
                        />
                      ) : null}
                      <MarkerShape
                        shape={shapeOf(placement)}
                        r={size}
                        className={fillClass(placement)}
                        strokeWidth={0}
                      />
                    </g>
                  </g>
                )
              })}
            </g>
          </g>
        </svg>
      ) : (
        <div className="flex h-full items-center justify-center px-6 text-center text-sm text-muted-foreground">
          {t('thesis.emptyCanvas')}
        </div>
      )}
      <div
        ref={layersRef}
        className="absolute top-3 right-3 overflow-hidden bg-background/80 text-foreground shadow-sm ring-1 ring-foreground/10 backdrop-blur-md transition-[width,height,border-radius] duration-[420ms] ease-[cubic-bezier(0.22,1,0.36,1)]"
        style={{
          width: layersOpen ? layersSize.width : 36,
          height: layersOpen ? layersSize.height : 36,
          borderRadius: layersOpen ? 'var(--radius-xl)' : 18,
        }}
      >
        <div
          ref={layersContentRef}
          className={`w-44 p-2 transition-opacity duration-200 ${layersOpen ? 'opacity-100' : 'pointer-events-none opacity-0'}`}
          inert={!layersOpen}
        >
          <div className="flex flex-col gap-2">
            <Button type="button" size="sm" variant="outline" className="w-full bg-background/80" onClick={fitView} disabled={!scene}>
              {t('thesis.fit')}
            </Button>
            {LAYER_KEYS.map((key) => (
              <LayerToggle
                key={key}
                checked={layers[key]}
                label={t(LAYER_LABEL[key])}
                onChange={(checked) => setLayers((prev) => ({ ...prev, [key]: checked }))}
              />
            ))}
          </div>
        </div>
        <button
          type="button"
          aria-expanded={layersOpen}
          aria-label={t('thesis.layers')}
          tabIndex={layersOpen ? -1 : 0}
          className={`absolute top-0 right-0 flex size-9 items-center justify-center rounded-full transition-opacity duration-150 ${
            layersOpen ? 'pointer-events-none opacity-0' : 'opacity-100 hover:bg-background'
          }`}
          onClick={() => setLayersOpen(true)}
        >
          <Layers className="size-4" />
        </button>
      </div>
    </div>
  )
}

const GRID_M = 10
/** Same free-axis placement as the paper factory plots. */
const AXIS_FROM_LEFT = 0.15
const AXIS_FROM_BOTTOM = 0.15

function gridLines(bounds: WorldBounds) {
  const lines = []
  for (const x of ticksBetween(bounds.x0, bounds.x1, GRID_M)) {
    lines.push(
      <line
        key={`x-${x}`}
        x1={x}
        y1={bounds.y0}
        x2={x}
        y2={bounds.y1}
        className="stroke-foreground/12"
        strokeWidth={1}
        vectorEffect="non-scaling-stroke"
      />,
    )
  }
  for (const y of ticksBetween(bounds.y0, bounds.y1, GRID_M)) {
    lines.push(
      <line
        key={`y-${y}`}
        x1={bounds.x0}
        y1={y}
        x2={bounds.x1}
        y2={y}
        className="stroke-foreground/12"
        strokeWidth={1}
        vectorEffect="non-scaling-stroke"
      />,
    )
  }
  return lines
}

function FloorAxes({
  width,
  height,
  bounds,
  scaleX,
  scaleY,
  xLabel,
  yLabel,
}: {
  width: number
  height: number
  bounds: WorldBounds
  scaleX: number
  scaleY: number
  xLabel: string
  yLabel: string
}) {
  const pxX = (pixels: number) => pixels / scaleX
  const pxY = (pixels: number) => pixels / scaleY
  const upright = `scale(${pxX(1)} ${-pxY(1)})`
  const xSpine = width * AXIS_FROM_LEFT
  const ySpine = height * AXIS_FROM_BOTTOM
  return (
    <g className="pointer-events-none fill-foreground stroke-foreground">
      <line x1={bounds.x0} y1={ySpine} x2={bounds.x1} y2={ySpine} strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
      <line x1={xSpine} y1={bounds.y0} x2={xSpine} y2={bounds.y1} strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
      {ticksBetween(bounds.x0, bounds.x1, GRID_M).map((x) => (
        <g key={`xt-${x}`} transform={`translate(${x} ${ySpine})`}>
          <line y2={-pxY(8)} strokeWidth={1} vectorEffect="non-scaling-stroke" />
          <g transform={`translate(0 ${-pxY(12)}) ${upright}`}>
            <text textAnchor="middle" dominantBaseline="hanging" fontSize={11}>
              {formatTick(x)}
            </text>
          </g>
        </g>
      ))}
      {ticksBetween(bounds.y0, bounds.y1, GRID_M).map((y) => (
        <g key={`yt-${y}`} transform={`translate(${xSpine} ${y})`}>
          <line x2={-pxX(8)} strokeWidth={1} vectorEffect="non-scaling-stroke" />
          <g transform={`translate(${-pxX(12)} 0) ${upright}`}>
            <text textAnchor="end" dominantBaseline="middle" fontSize={11}>
              {formatTick(y)}
            </text>
          </g>
        </g>
      ))}
      <g transform={`translate(${(bounds.x0 + bounds.x1) / 2} ${ySpine - pxY(28)}) ${upright}`}>
        <text textAnchor="middle" fontSize={12}>
          {xLabel}
        </text>
      </g>
      <g transform={`translate(${xSpine - pxX(56)} ${(bounds.y0 + bounds.y1) / 2}) ${upright}`}>
        <text textAnchor="middle" fontSize={12} transform="rotate(-90)">
          {yLabel}
        </text>
      </g>
    </g>
  )
}

type WorldBounds = { x0: number; x1: number; y0: number; y1: number }

function visibleWorld(
  vw: number,
  vh: number,
  height: number,
  panX: number,
  panY: number,
  scaleX: number,
  scaleY: number,
): WorldBounds {
  const x0 = (0 - panX) / scaleX
  const x1 = (vw - panX) / scaleX
  const yTop = height - (0 - panY) / scaleY
  const yBottom = height - (vh - panY) / scaleY
  return {
    x0: Math.min(x0, x1),
    x1: Math.max(x0, x1),
    y0: Math.min(yTop, yBottom),
    y1: Math.max(yTop, yBottom),
  }
}

function ticksBetween(start: number, end: number, step: number) {
  if (!(step > 0) || !Number.isFinite(start) || !Number.isFinite(end)) return []
  const values: number[] = []
  const first = Math.ceil((start - 1e-6) / step) * step
  for (let value = first; value <= end + 1e-6; value += step) {
    values.push(Math.round(value * 1000) / 1000)
    if (values.length > 400) break
  }
  return values
}

function formatTick(value: number) {
  return Number.isInteger(value) ? String(value) : String(Math.round(value * 10) / 10)
}

function meterScale(vw: number, vh: number, width: number, height: number, zoom: number) {
  const fit = Math.min((Math.max(vw, 80) - 48) / width, (Math.max(vh, 80) - 48) / height)
  return Math.max(1e-6, fit * zoom)
}

function centeredPan(vw: number, vh: number, width: number, height: number, scale: number) {
  return {
    zoom: 1,
    panX: (vw - width * scale) / 2,
    panY: (vh - height * scale) / 2,
  }
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function shapeOf(placement: Placement): Shape {
  if (placement.kind === 'station') return 'diamond'
  if (placement.kind === 'radar') return 'hexagon'
  return 'circle'
}

function layerVisible(placement: Placement, layers: Layers) {
  if (placement.kind === 'device' && placement.subtype === '1') return layers.device1
  if (placement.kind === 'device' && placement.subtype === '2a') return layers.device2a
  if (placement.kind === 'device' && placement.subtype === '2b') return layers.device2b
  if (placement.kind === 'radar') return layers.radar
  if (placement.kind === 'station') return layers.station
  return true
}

function LayerToggle({ checked, label, onChange }: { checked: boolean; label: string; onChange: (checked: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 text-xs">
      <Checkbox checked={checked} onCheckedChange={(value) => onChange(value === true)} />
      <span>{label}</span>
    </label>
  )
}

function PulseRing({ size, tone, delay }: { size: number; tone: string; delay: number }) {
  const inner = size * 1.25
  const outer = size * 3.6
  return (
    <circle r={inner} className={tone} fill="currentColor" stroke="none" opacity={0.4}>
      <animate
        attributeName="r"
        values={`${inner};${outer};${outer}`}
        keyTimes="0;0.82;1"
        calcMode="spline"
        keySplines="0.22 0.6 0.36 1;0 0 1 1"
        dur="2.8s"
        begin={`${delay}ms`}
        repeatCount="indefinite"
      />
      <animate
        attributeName="opacity"
        values="0.42;0;0"
        keyTimes="0;0.82;1"
        calcMode="spline"
        keySplines="0.4 0 0.6 1;0 0 1 1"
        dur="2.8s"
        begin={`${delay}ms`}
        repeatCount="indefinite"
      />
    </circle>
  )
}

function beaconTone(placement: Placement) {
  if (placement.kind === 'radar') return 'text-[#b91c1c]'
  if (placement.kind === 'station') return 'text-[#6d28d9]'
  return 'text-foreground'
}

function beaconDelay(id: Placement['id']) {
  const text = String(id)
  let hash = 0
  for (let index = 0; index < text.length; index += 1) hash = (hash + text.charCodeAt(index) * (index + 1)) % 900
  return hash
}

function fillClass(placement: Placement) {
  if (placement.kind === 'device') return FILL[`device:${placement.subtype}`] ?? 'fill-chart-1'
  return FILL[placement.kind as Kind]
}
