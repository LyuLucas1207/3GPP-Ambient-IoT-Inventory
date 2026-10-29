import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import KDBush from 'kdbush'
import { Layers } from 'lucide-react'
import { MarkerShape } from '@/components/thesis/MarkerShape'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { inside } from '@/lib/thesisGeometry'
import { DEVICE_SUBTYPES, deriveReaderRanges, effectiveCoverageM, rangeFromSensitivityM, readerRingVisible } from '@/lib/thesisPhysics'
import { FLAGGED_CODES, RUN_STATE_COLOR_BY_CODE, RUN_STATE_LABELS } from '@/lib/thesisRunStates'
import type { LiveDevices } from '@/hooks/useLiveRun'
import { readerLinksForDevice } from '@/lib/thesisReach'
import type { CatalogEntry, DeviceSubtype, Kind, Placement, RunSummary, Scene, Shape } from '@/types/thesis'

/** Extra screen pixels of slack around a device dot when hit-testing. */
const HIT_SLOP_PX = 3
/** Pointer travel (px) above which a press is a pan, not a click. */
const CLICK_TOLERANCE_PX = 4

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

const RANGE_STROKE: Record<DeviceSubtype, string> = {
  '1': '#1d4ed8',
  '2a': '#0f766e',
  '2b': '#c2410c',
}

export function ThesisWarehouse({
  scene,
  catalog,
  selectedId,
  focusReaderId,
  markerScale,
  deviceMarkerScale,
  live,
  flagPending = false,
  run = null,
  selectedDeviceId = null,
  onSelectDevice,
  onSelectReader,
  selecting = false,
  pickedIds = [],
  onTogglePick,
  onEdit,
  onPlace,
}: {
  scene: Scene | null
  catalog: CatalogEntry[]
  selectedId: string | null
  focusReaderId: Placement['id'] | null
  markerScale: number
  deviceMarkerScale: number
  /** live per-device state of the selected run (null = colour by subtype) */
  live: LiveDevices | null
  /** flag every device not identified yet, not only the dropped ones */
  flagPending?: boolean
  /** selected run, used to link the selected device to the readers that cover it */
  run?: RunSummary | null
  selectedDeviceId?: number | null
  onSelectDevice?: (id: number | null) => void
  /** when set (a run is selected), a left click on a reader inspects it instead of opening the edit menu */
  onSelectReader?: (id: number) => void
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

  const deviceCanvasRef = useRef<HTMLCanvasElement>(null)
  const pressRef = useRef<{ x: number; y: number } | null>(null)
  const hoverRaf = useRef(0)
  const [hover, setHover] = useState<{ id: number; sx: number; sy: number } | null>(null)
  const selectedDevice = useMemo(
    () => (selectedDeviceId != null ? scene?.placements.find((p) => p.id === selectedDeviceId && p.kind === 'device') ?? null : null),
    [scene, selectedDeviceId],
  )
  const runD2r = run?.include_d2r
  const runDisabled = run?.disabled_reader_ids
  const selectedLinks = useMemo(
    () =>
      scene && selectedDevice
        ? readerLinksForDevice(scene.placements, selectedDevice, { include_d2r: runD2r, disabled_reader_ids: runDisabled })
        : [],
    [scene, selectedDevice, runD2r, runDisabled],
  )

  // Spatial index over device positions (world metres), rebuilt when the scene changes.
  const deviceIndex = useMemo(() => {
    const devices = (scene?.placements ?? []).filter((p) => p.kind === 'device' && typeof p.id === 'number')
    if (devices.length === 0) return null
    const index = new KDBush(devices.length)
    for (const d of devices) index.add(d.x_m, d.y_m)
    index.finish()
    return { index, devices }
  }, [scene])

  const deviceDefaults = useMemo<Partial<Record<DeviceSubtype, CatalogEntry['defaults']>>>(() => {
    const out: Partial<Record<DeviceSubtype, CatalogEntry['defaults']>> = {}
    for (const subtype of DEVICE_SUBTYPES) {
      const entry = catalog.find((item) => item.kind === 'device' && item.subtype === subtype)
      if (entry) out[subtype] = entry.defaults
    }
    return out
  }, [catalog])
  const sensitivities = useMemo<Partial<Record<DeviceSubtype, number>>>(() => {
    const out: Partial<Record<DeviceSubtype, number>> = {}
    for (const subtype of DEVICE_SUBTYPES) {
      const value = deviceDefaults[subtype]?.rx_sensitivity_dbm
      if (typeof value === 'number') out[subtype] = value
    }
    return out
  }, [deviceDefaults])

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

  useEffect(() => {
    if (!scene) return
    const held = new Set<string>()
    const PAN_PX_PER_SEC = 600
    const ZOOM_PER_SEC = 1.6
    let raf = 0
    let last = performance.now()

    const isTextTarget = (target: EventTarget | null) => {
      if (!(target instanceof HTMLElement)) return false
      const tag = target.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true
      return target.isContentEditable
    }

    const step = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000)
      last = now
      if (held.size === 0) {
        raf = 0
        return
      }
      const host = hostRef.current
      if (!host) {
        raf = requestAnimationFrame(step)
        return
      }
      const rect = host.getBoundingClientRect()
      const current = viewRef.current
      let { zoom, panX, panY } = current
      const panDelta = PAN_PX_PER_SEC * dt
      if (held.has('w')) panY += panDelta
      if (held.has('s')) panY -= panDelta
      if (held.has('a')) panX += panDelta
      if (held.has('d')) panX -= panDelta
      const zoomMul = Math.pow(ZOOM_PER_SEC, dt)
      if (held.has('e') || held.has('q')) {
        const nextZoom = clamp(held.has('e') ? zoom * zoomMul : zoom / zoomMul, 0.25, 12)
        const sx = rect.width / 2
        const sy = rect.height / 2
        const now = meterScale(rect.width, rect.height, scene.width_m, scene.height_m, zoom)
        const worldX = (sx - panX) / now
        const worldY = scene.height_m - (sy - panY) / now
        const nextScale = meterScale(rect.width, rect.height, scene.width_m, scene.height_m, nextZoom)
        zoom = nextZoom
        panX = sx - worldX * nextScale
        panY = sy - (scene.height_m - worldY) * nextScale
      }
      const next = { zoom, panX, panY }
      viewRef.current = next
      setView(next)
      raf = requestAnimationFrame(step)
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.repeat) return
      if (event.ctrlKey || event.metaKey || event.altKey) return
      if (isTextTarget(event.target)) return
      const key = event.key.toLowerCase()
      if (!'wasdqe'.includes(key)) return
      event.preventDefault()
      held.add(key)
      if (raf === 0) {
        last = performance.now()
        raf = requestAnimationFrame(step)
      }
    }
    const onKeyUp = (event: KeyboardEvent) => {
      const key = event.key.toLowerCase()
      if (held.delete(key) && held.size === 0 && raf !== 0) {
        cancelAnimationFrame(raf)
        raf = 0
      }
    }
    const onBlur = () => {
      held.clear()
      if (raf !== 0) {
        cancelAnimationFrame(raf)
        raf = 0
      }
    }

    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('keyup', onKeyUp)
    window.addEventListener('blur', onBlur)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('keyup', onKeyUp)
      window.removeEventListener('blur', onBlur)
      if (raf !== 0) cancelAnimationFrame(raf)
    }
  }, [scene])

  const scale = scene ? meterScale(size.vw, size.vh, scene.width_m, scene.height_m, view.zoom) : 1
  const visible = scene
    ? visibleWorld(size.vw, size.vh, scene.height_m, view.panX, view.panY, scale, scale)
    : { x0: 0, x1: 1, y0: 0, y1: 1 }

  useEffect(() => {
    const canvas = deviceCanvasRef.current
    if (!canvas) return
    const dpr = window.devicePixelRatio || 1
    const vw = Math.max(1, size.vw)
    const vh = Math.max(1, size.vh)
    const nextW = Math.round(vw * dpr)
    const nextH = Math.round(vh * dpr)
    if (canvas.width !== nextW) canvas.width = nextW
    if (canvas.height !== nextH) canvas.height = nextH
    canvas.style.width = `${vw}px`
    canvas.style.height = `${vh}px`
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, vw, vh)
    if (!scene) return

    const panX = view.panX
    const panY = view.panY
    const flipY = scene.height_m
    const radiusPx = Math.max(0.4, 0.42 * deviceMarkerScale * scale)

    const focusReader = focusReaderId
      ? scene.placements.find((p) => p.id === focusReaderId && p.kind === 'radar')
      : null
    const coverageSq: Partial<Record<DeviceSubtype, number>> = {}
    let focusCx = 0
    let focusCy = 0
    if (focusReader) {
      focusCx = focusReader.x_m
      focusCy = focusReader.y_m
      const rf = {
        tx_power_dbm: toNumber(focusReader.params.tx_power_dbm, 33),
        antenna_gain_dbi: toNumber(focusReader.params.antenna_gain_dbi, 6),
        extra_attenuation_db: toNumber(focusReader.params.extra_attenuation_db, 0),
        carrier_ghz: toNumber(focusReader.params.carrier_ghz, 0.9),
      }
      const includeD2r = focusReader.params.include_d2r !== false
      for (const subtype of DEVICE_SUBTYPES) {
        const params = deviceDefaults[subtype]
        if (!params) continue
        const r = effectiveCoverageM(params, rf, includeD2r)
        coverageSq[subtype] = r * r
      }
    }

    const subtypeColor: Record<string, string> = {
      '1': '#1d4ed8',
      '2a': '#0f766e',
      '2b': '#c2410c',
    }
    const subtypeShow: Record<string, boolean> = {
      '1': layers.device1,
      '2a': layers.device2a,
      '2b': layers.device2b,
    }
    const byColor = new Map<string, Placement[]>()
    const dimmed: Placement[] = []
    const flagged: Placement[] = [] // unidentified at the end of the run, or so far when paused / stopped
    const identifiedCode = RUN_STATE_LABELS.indexOf('identified')
    const push = (color: string, placement: Placement) => {
      const list = byColor.get(color) ?? []
      list.push(placement)
      byColor.set(color, list)
    }
    for (const placement of scene.placements) {
      if (placement.kind !== 'device') continue
      if (!subtypeShow[placement.subtype ?? '']) continue
      let outOfRange = false
      if (focusReader) {
        const covSq = coverageSq[placement.subtype as DeviceSubtype]
        const dx = placement.x_m - focusCx
        const dy = placement.y_m - focusCy
        outOfRange = !(typeof covSq === 'number' && dx * dx + dy * dy <= covSq)
      }
      if (outOfRange) {
        dimmed.push(placement)
        continue
      }
      let color = subtypeColor[placement.subtype ?? ''] ?? '#737373'
      if (live) {
        const idx = live.indexById.get(placement.id as number)
        if (idx != null) {
          const code = live.codes[idx]
          if (FLAGGED_CODES.has(code) || (flagPending && code !== identifiedCode)) {
            flagged.push(placement)
            continue
          }
          color = RUN_STATE_COLOR_BY_CODE[code] ?? color
        }
      }
      push(color, placement)
    }
    const drawCircles = (items: Placement[], fillStyle: string, r = radiusPx) => {
      if (items.length === 0) return
      ctx.fillStyle = fillStyle
      ctx.beginPath()
      for (const placement of items) {
        const sx = placement.x_m * scale + panX
        const sy = (flipY - placement.y_m) * scale + panY
        ctx.moveTo(sx + r, sy)
        ctx.arc(sx, sy, r, 0, Math.PI * 2)
      }
      ctx.fill()
    }
    drawCircles(dimmed, 'rgba(120,120,120,0.25)')
    for (const [color, items] of byColor) {
      drawCircles(items, color)
    }
    // Unidentified devices last and larger, so they are visible among thousands of green dots.
    drawCircles(flagged, RUN_STATE_COLOR_BY_CODE[RUN_STATE_LABELS.indexOf('dropped')], Math.max(radiusPx * 1.8, 2.5))
    const ringed = [selectedDeviceId, hover?.id].filter((id): id is number => id != null)
    for (const id of new Set(ringed)) {
      const p = scene.placements.find((item) => item.id === id && item.kind === 'device')
      if (!p) continue
      const sx = p.x_m * scale + panX
      const sy = (flipY - p.y_m) * scale + panY
      ctx.beginPath()
      ctx.arc(sx, sy, radiusPx + (id === selectedDeviceId ? 4 : 2.5), 0, Math.PI * 2)
      ctx.lineWidth = id === selectedDeviceId ? 2.5 : 1.5
      ctx.strokeStyle = id === selectedDeviceId ? '#eab308' : 'rgba(127,127,127,0.9)'
      ctx.stroke()
    }
  }, [scene, view.panX, view.panY, scale, size.vw, size.vh, layers.device1, layers.device2a, layers.device2b, deviceMarkerScale, focusReaderId, deviceDefaults, live, live?.version, flagPending, selectedDeviceId, hover?.id])

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

  /** Nearest visible device under the pointer, within the dot radius plus a few pixels. */
  function deviceAt(clientX: number, clientY: number): Placement | null {
    if (!deviceIndex || !scene) return null
    const world = screenToWorld(clientX, clientY)
    if (!world) return null
    const radiusPx = Math.max(0.4, 0.42 * deviceMarkerScale * scale)
    const r = (radiusPx + HIT_SLOP_PX) / scale
    const show: Record<string, boolean> = { '1': layers.device1, '2a': layers.device2a, '2b': layers.device2b }
    let best: Placement | null = null
    let bestD = Infinity
    for (const i of deviceIndex.index.within(world.x, world.y, r)) {
      const d = deviceIndex.devices[i]
      if (!show[d.subtype ?? '']) continue
      const dist = Math.hypot(d.x_m - world.x, d.y_m - world.y)
      if (dist < bestD) {
        bestD = dist
        best = d
      }
    }
    return best
  }

  function fitView() {
    if (!scene || size.vw < 10) return
    fittedFloor.current = `${scene.width_m}x${scene.height_m}:${Math.round(size.vw)}x${Math.round(size.vh)}:square`
    const scale = meterScale(size.vw, size.vh, scene.width_m, scene.height_m, 1)
    setView(centeredPan(size.vw, size.vh, scene.width_m, scene.height_m, scale))
  }

  return (
    <div ref={hostRef} className="relative h-full min-h-0 w-full overflow-hidden bg-background">
      <canvas ref={deviceCanvasRef} className="pointer-events-none absolute inset-0" aria-hidden />
      {scene ? (
        <svg
          className={`absolute inset-0 h-full w-full touch-none ${hover ? 'cursor-pointer' : ''}`}
          onPointerDown={(event) => {
            if (event.button !== 0) return
            pressRef.current = { x: event.clientX, y: event.clientY }
            if ((event.target as Element).closest('[data-placement]')) return
            drag.current = { x: event.clientX, y: event.clientY, panX: view.panX, panY: view.panY }
            event.currentTarget.setPointerCapture(event.pointerId)
          }}
          onPointerMove={(event) => {
            const current = drag.current
            if (!current) {
              // Hover hit-test, throttled to one query per animation frame.
              const { clientX, clientY, target } = event
              if (hoverRaf.current) return
              hoverRaf.current = requestAnimationFrame(() => {
                hoverRaf.current = 0
                const overInfra = (target as Element).closest?.('[data-placement]')
                const hit = overInfra ? null : deviceAt(clientX, clientY)
                const rect = hostRef.current?.getBoundingClientRect()
                setHover((prev) => {
                  if (!hit || !rect) return prev === null ? prev : null
                  const id = hit.id as number
                  const sx = clientX - rect.left
                  const sy = clientY - rect.top
                  return prev?.id === id ? prev : { id, sx, sy }
                })
              })
              return
            }
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
          onPointerLeave={() => setHover(null)}
          onClick={(event) => {
            const press = pressRef.current
            pressRef.current = null
            if (press && Math.hypot(event.clientX - press.x, event.clientY - press.y) > CLICK_TOLERANCE_PX) return
            if ((event.target as Element).closest('[data-placement]')) return
            if (selecting) return
            const hit = deviceAt(event.clientX, event.clientY)
            onSelectDevice?.(hit ? (hit.id as number) : null)
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
            const device = deviceAt(event.clientX, event.clientY)
            if (device) {
              onEdit(device.id, event.clientX, event.clientY)
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
              <defs>
                <radialGradient id="station-fade">
                  <stop offset="0%" stopColor="#6d28d9" stopOpacity="0.35" />
                  <stop offset="60%" stopColor="#6d28d9" stopOpacity="0.12" />
                  <stop offset="100%" stopColor="#6d28d9" stopOpacity="0" />
                </radialGradient>
                <clipPath id="warehouse-clip">
                  <rect x={0} y={0} width={scene.width_m} height={scene.height_m} />
                </clipPath>
              </defs>
              {([false, true] as const).map((outer) => {
                const groupProps = outer ? {} : { clipPath: 'url(#warehouse-clip)' }
                return (
                  <g key={`range-outer-${outer}`} {...groupProps} className="pointer-events-none">
                    {scene.placements.map((placement) => {
                      if (placement.kind !== 'station') return null
                      if (placement.params.show_range !== true) return null
                      if ((placement.params.show_outer === true) !== outer) return null
                      const diagonal = Math.hypot(scene.width_m, scene.height_m)
                      const stationRf = {
                        tx_power_dbm: toNumber(placement.params.tx_power_dbm, 33),
                        antenna_gain_dbi: toNumber(placement.params.antenna_gain_dbi, 6),
                        extra_attenuation_db: toNumber(placement.params.extra_attenuation_db, 0),
                        carrier_ghz: toNumber(placement.params.carrier_ghz, 0.9),
                      }
                      const typicalSens = sensitivities['1'] ?? -36
                      const base = rangeFromSensitivityM(typicalSens, stationRf)
                      const r = outer ? Math.max(base * 1.6, 5) : Math.min(Math.max(base * 1.6, 5), diagonal)
                      return (
                        <circle
                          key={`station-fade-${placement.id}`}
                          cx={placement.x_m}
                          cy={placement.y_m}
                          r={r}
                          fill="url(#station-fade)"
                          stroke="none"
                        />
                      )
                    })}
                    {scene.placements.map((placement) => {
                      if (placement.kind !== 'radar') return null
                      if (placement.params.show_range !== true) return null
                      if ((placement.params.show_outer === true) !== outer) return null
                      const diagonal = Math.hypot(scene.width_m, scene.height_m)
                      const readerRf = {
                        tx_power_dbm: toNumber(placement.params.tx_power_dbm, 33),
                        antenna_gain_dbi: toNumber(placement.params.antenna_gain_dbi, 6),
                        extra_attenuation_db: toNumber(placement.params.extra_attenuation_db, 0),
                        carrier_ghz: toNumber(placement.params.carrier_ghz, 0.9),
                      }
                      const ranges = deriveReaderRanges(readerRf, deviceDefaults, placement.params.include_d2r !== false)
                      return (
                        <g key={`reader-range-${placement.id}`}>
                          {DEVICE_SUBTYPES.map((subtype) => {
                            if (!readerRingVisible(placement.params, subtype)) return null
                            const raw = ranges[subtype]
                            if (!Number.isFinite(raw) || raw <= 0) return null
                            const r = outer ? raw : Math.min(raw, diagonal)
                            return (
                              <circle
                                key={`r-${placement.id}-${subtype}`}
                                cx={placement.x_m}
                                cy={placement.y_m}
                                r={r}
                                fill={RANGE_STROKE[subtype]}
                                fillOpacity={0.08}
                                stroke={RANGE_STROKE[subtype]}
                                strokeOpacity={0.55}
                                strokeWidth={1.25}
                                vectorEffect="non-scaling-stroke"
                              />
                            )
                          })}
                        </g>
                      )
                    })}
                  </g>
                )
              })}
              {selectedDevice ? (
                <g className="pointer-events-none">
                  {selectedLinks.map((link) =>
                    link.inside ? (
                      <g key={`link-${link.id}`}>
                        <line
                          x1={selectedDevice.x_m}
                          y1={selectedDevice.y_m}
                          x2={link.x_m}
                          y2={link.y_m}
                          stroke={link.disabled ? '#a1a1aa' : '#eab308'}
                          strokeWidth={link.disabled ? 1.25 : 2}
                          strokeDasharray={link.disabled ? '4 4' : undefined}
                          vectorEffect="non-scaling-stroke"
                        />
                        <circle
                          cx={link.x_m}
                          cy={link.y_m}
                          r={1.6 * markerScale}
                          fill="none"
                          stroke={link.disabled ? '#a1a1aa' : '#eab308'}
                          strokeWidth={2}
                          strokeDasharray={link.disabled ? '3 3' : undefined}
                          vectorEffect="non-scaling-stroke"
                        />
                      </g>
                    ) : null,
                  )}
                </g>
              ) : null}
              {scene.placements.map((placement) => {
                if (placement.kind === 'device') return null
                if (!layerVisible(placement, layers)) return null
                const beacon = true
                const tone = beaconTone(placement)
                const picked = pickedIds.includes(String(placement.id))
                const isFocus = focusReaderId != null && placement.id === focusReaderId
                const dimmed = focusReaderId != null && !isFocus
                const size = 0.85 * markerScale * (selectedId === String(placement.id) || isFocus ? 1.3 : 1)
                return (
                  <g
                    key={placement.id}
                    data-placement={placement.id}
                    transform={`translate(${placement.x_m} ${placement.y_m})`}
                    className="cursor-pointer"
                    opacity={dimmed ? 0.18 : 1}
                    onClick={(event) => {
                      event.stopPropagation()
                      if (selecting && placement.kind !== 'device') {
                        onTogglePick?.(placement.id)
                        return
                      }
                      if (placement.kind === 'radar' && onSelectReader && typeof placement.id === 'number') {
                        onSelectReader(placement.id)
                        return
                      }
                      onEdit(placement.id, event.clientX, event.clientY)
                    }}
                  >
                    {picked ? (
                      <circle r={size * 2.2} className="fill-none stroke-foreground" strokeWidth={2} vectorEffect="non-scaling-stroke" />
                    ) : null}
                    {beacon && !dimmed ? (
                      <>
                        <PulseRing size={size} tone={tone} delay={beaconDelay(placement.id)} />
                        <PulseRing size={size} tone={tone} delay={beaconDelay(placement.id) + 1400} />
                      </>
                    ) : null}
                    <g opacity={beacon ? 0.85 : 1}>
                      {beacon && !dimmed ? (
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
                        className={dimmed ? 'fill-foreground' : fillClass(placement)}
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
      {hover && scene ? (
        <DeviceHoverTip
          left={hover.sx}
          top={hover.sy}
          placement={scene.placements.find((p) => p.id === hover.id) ?? null}
          state={(() => {
            const idx = live?.indexById.get(hover.id)
            return idx != null && live ? RUN_STATE_LABELS[live.codes[idx]] : null
          })()}
          energyJ={(() => {
            const idx = live?.indexById.get(hover.id)
            return idx != null && live ? live.energy[idx] : null
          })()}
        />
      ) : null}
      <div
        ref={layersRef}
        className="absolute top-3 right-14 overflow-hidden bg-background/80 text-foreground shadow-sm ring-1 ring-foreground/10 backdrop-blur-md transition-[width,height,border-radius] duration-[420ms] ease-[cubic-bezier(0.22,1,0.36,1)]"
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

function DeviceHoverTip({
  left,
  top,
  placement,
  state,
  energyJ,
}: {
  left: number
  top: number
  placement: Placement | null
  state: string | null
  energyJ: number | null
}) {
  const { t } = useTranslation()
  if (!placement) return null
  return (
    <div
      className="pointer-events-none absolute z-10 rounded-md bg-popover/95 px-2 py-1 text-[11px] text-popover-foreground shadow-md ring-1 ring-foreground/10"
      style={{ left: left + 12, top: top + 12 }}
    >
      <div className="font-medium">
        #{placement.id} · {t(`thesis.kind.device${placement.subtype}`)}
      </div>
      {state ? <div>{t(`thesis.live.state.${state}`)}</div> : null}
      {energyJ != null ? <div className="tabular-nums text-muted-foreground">{(energyJ * 1e6).toFixed(2)} µJ</div> : null}
      <div className="text-muted-foreground">{t('thesis.inspector.clickHint')}</div>
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

function toNumber(value: unknown, fallback: number): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return parsed
  }
  return fallback
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
