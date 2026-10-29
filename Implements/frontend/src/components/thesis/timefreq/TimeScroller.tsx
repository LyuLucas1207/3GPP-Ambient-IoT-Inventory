import { ChevronFirst, ChevronLast, ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from 'lucide-react'
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'

/** Width of the sticky row-label gutter on the left of every time-frequency canvas. */
export const GUTTER_PX = 72
/** Browsers stop laying out elements somewhere above 33M px. */
const MAX_CONTENT_PX = 30_000_000
const MIN_PX_PER_S = 5
/** On-screen width of a collapsed idle gap. */
const GAP_PX = 58
/** Gaps narrower than this at the current zoom are drawn to scale. */
const MIN_GAP_PX = 2 * GAP_PX
const COLLAPSE_KEY = 'thesis.tf.collapse'

export type TimeView = {
  /** first visible time (s) at x = GUTTER_PX */
  t0: number
  t1: number
  pxPerS: number
  width: number
  height: number
  dark: boolean
  /** x (CSS px) of time t */
  x: (t: number) => number
  /** on-screen width of [a, b]; shorter than (b − a) · pxPerS when it spans a collapsed gap */
  w: (a: number, b: number) => number
}

type Gap = { a: number; b: number; xa: number }

/**
 * Maps time to content pixels with every long idle gap squeezed to GAP_PX,
 * and back. Without gaps it is plain t · pxPerS.
 */
function buildWarp(gaps: [number, number][] | undefined, pxPerS: number, enabled: boolean) {
  const kept: Gap[] = []
  if (enabled && gaps?.length) {
    let removed = 0
    for (const [a, b] of mergeGaps(gaps)) {
      const natural = (b - a) * pxPerS
      if (natural <= MIN_GAP_PX) continue
      kept.push({ a, b, xa: a * pxPerS - removed })
      removed += natural - GAP_PX
    }
  }
  const lastBefore = <T,>(arr: T[], ok: (g: T) => boolean) => {
    let lo = 0
    let hi = arr.length - 1
    let found = -1
    while (lo <= hi) {
      const mid = (lo + hi) >> 1
      if (ok(arr[mid])) {
        found = mid
        lo = mid + 1
      } else hi = mid - 1
    }
    return found
  }
  const X = (t: number) => {
    const i = lastBefore(kept, (g) => g.a <= t)
    if (i < 0) return t * pxPerS
    const g = kept[i]
    if (t < g.b) return g.xa + ((t - g.a) / (g.b - g.a)) * GAP_PX
    return g.xa + GAP_PX + (t - g.b) * pxPerS
  }
  const T = (x: number) => {
    const i = lastBefore(kept, (g) => g.xa <= x)
    if (i < 0) return x / pxPerS
    const g = kept[i]
    if (x < g.xa + GAP_PX) return g.a + ((x - g.xa) / GAP_PX) * (g.b - g.a)
    return g.b + (x - g.xa - GAP_PX) / pxPerS
  }
  const gapAt = (x: number) => {
    const i = lastBefore(kept, (g) => g.xa <= x)
    return i >= 0 && x < kept[i].xa + GAP_PX ? kept[i] : null
  }
  return { gaps: kept, X, T, gapAt }
}

function mergeGaps(gaps: [number, number][]): [number, number][] {
  const sorted = gaps.filter(([a, b]) => b > a).sort((p, q) => p[0] - q[0])
  const out: [number, number][] = []
  for (const [a, b] of sorted) {
    const last = out[out.length - 1]
    if (last && a <= last[1] + 1e-9) last[1] = Math.max(last[1], b)
    else out.push([a, b])
  }
  return out
}

/** Complement of ``busy`` inside [0, tEnd]: the stretches where nothing happens. */
export function idleGaps(busy: [number, number][], tEnd: number): [number, number][] {
  const out: [number, number][] = []
  let cursor = 0
  for (const [a, b] of mergeGaps(busy.map(([a, b]) => [a, Math.max(b, a + 1e-9)]))) {
    if (a > cursor) out.push([cursor, a])
    cursor = Math.max(cursor, b)
  }
  if (tEnd > cursor) out.push([cursor, tEnd])
  return out
}

function readCollapse(): boolean {
  try {
    return localStorage.getItem(COLLAPSE_KEY) !== '0'
  } catch {
    return true
  }
}

/**
 * Horizontally scrollable time axis drawn on one canvas: only the visible
 * window is painted, so a run of any length scrolls smoothly. The caller
 * draws rows with ``draw`` and explains a point with ``hit``; ``gaps`` are
 * idle stretches that may be collapsed to a short break.
 */
export function TimeScroller({
  tEnd,
  height,
  draw,
  hit,
  onWindow,
  jumps,
  gaps,
  initialPxPerS = 2000,
  redrawKey,
  toolbar,
  globalKeys = false,
}: {
  tEnd: number
  height: number
  draw: (ctx: CanvasRenderingContext2D, view: TimeView) => void
  hit?: (t: number, y: number) => string | null
  onWindow?: (t0: number, t1: number) => void
  /** sorted times the prev / next buttons jump between (e.g. the frames a device took part in) */
  jumps?: number[]
  gaps?: [number, number][]
  initialPxPerS?: number
  /** changes when the data behind ``draw`` changes */
  redrawKey?: unknown
  toolbar?: React.ReactNode
  /** listen to arrow keys on the whole window (for a modal); otherwise only while focused */
  globalKeys?: boolean
}) {
  const { t } = useTranslation()
  const scrollRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [width, setWidth] = useState(0)
  const [scrollLeft, setScrollLeft] = useState(0)
  const maxPx = Math.max(MIN_PX_PER_S, MAX_CONTENT_PX / Math.max(tEnd, 1e-3))
  const [pxPerS, setPxPerS] = useState(Math.min(initialPxPerS, maxPx))
  const [collapse, setCollapse] = useState(readCollapse)
  const [tip, setTip] = useState<{ x: number; y: number; text: string } | null>(null)
  const pendingAnchor = useRef<{ t: number; offset: number } | null>(null)
  const leftTime = useRef(0)

  const total = Math.max(tEnd, 0)
  const warp = useMemo(() => buildWarp(gaps, pxPerS, collapse), [gaps, pxPerS, collapse])
  const contentW = GUTTER_PX + warp.X(total) + 24
  const viewW = Math.max(0, width - GUTTER_PX)
  const t0 = warp.T(scrollLeft)
  const t1 = warp.T(scrollLeft + viewW)

  useEffect(() => {
    const node = scrollRef.current
    if (!node) return
    const ro = new ResizeObserver(() => setWidth(node.clientWidth))
    ro.observe(node)
    setWidth(node.clientWidth)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    onWindow?.(t0, t1)
  }, [onWindow, t0, t1])

  // Whenever the time → pixel mapping changes (zoom, collapse, newly loaded gaps),
  // keep the time under the cursor (or the left edge) where it was.
  useLayoutEffect(() => {
    const node = scrollRef.current
    if (!node) return
    const anchor = pendingAnchor.current ?? { t: leftTime.current, offset: 0 }
    pendingAnchor.current = null
    node.scrollLeft = Math.max(0, warp.X(anchor.t) - anchor.offset)
    setScrollLeft(node.scrollLeft)
  }, [warp])

  const zoom = useCallback(
    (factor: number, offsetPx?: number) => {
      const node = scrollRef.current
      if (!node) return
      const offset = offsetPx ?? 0
      const anchorT = warp.T(node.scrollLeft + offset)
      const next = Math.min(maxPx, Math.max(MIN_PX_PER_S, pxPerS * factor))
      if (next === pxPerS) return
      pendingAnchor.current = { t: anchorT, offset }
      setPxPerS(next)
    },
    [pxPerS, maxPx, warp],
  )

  useEffect(() => {
    const node = scrollRef.current
    if (!node) return
    const onWheel = (event: WheelEvent) => {
      if (event.ctrlKey || event.metaKey) {
        event.preventDefault()
        const rect = node.getBoundingClientRect()
        zoom(event.deltaY < 0 ? 1.25 : 0.8, Math.max(0, event.clientX - rect.left - GUTTER_PX))
        return
      }
      if (Math.abs(event.deltaY) > Math.abs(event.deltaX)) {
        event.preventDefault()
        node.scrollLeft += event.deltaY
      }
    }
    node.addEventListener('wheel', onWheel, { passive: false })
    return () => node.removeEventListener('wheel', onWheel)
  }, [zoom])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || width <= 0) return
    const dpr = window.devicePixelRatio || 1
    canvas.width = Math.round(width * dpr)
    canvas.height = Math.round(height * dpr)
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, width, height)
    const dark = document.documentElement.classList.contains('dark')
    const x = (tt: number) => GUTTER_PX + warp.X(tt) - scrollLeft
    const view: TimeView = { t0, t1, pxPerS, width, height, dark, x, w: (a, b) => x(b) - x(a) }
    draw(ctx, view)
    drawGaps(ctx, view, warp.gaps, scrollLeft)
    drawAxis(ctx, view, warp.gaps)
  }, [draw, width, height, t0, t1, pxPerS, redrawKey, warp, scrollLeft])

  function scrollToTime(time: number, frac = 0.15) {
    const node = scrollRef.current
    if (!node) return
    node.scrollLeft = Math.max(0, warp.X(time) - frac * viewW)
  }

  function jump(dir: 1 | -1) {
    if (!jumps?.length) return
    const ref = warp.T(scrollLeft + 0.15 * viewW)
    const eps = 1 / pxPerS
    const target = dir > 0 ? jumps.find((j) => j > ref + eps) : [...jumps].reverse().find((j) => j < ref - eps)
    if (target != null) scrollToTime(target)
  }

  const onKey = (event: KeyboardEvent | React.KeyboardEvent) => {
    const node = scrollRef.current
    if (!node || event.altKey || event.ctrlKey || event.metaKey) return
    const target = event.target as HTMLElement | null
    if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) return
    const step = (event.shiftKey ? 0.9 : 0.2) * viewW
    let handled = true
    switch (event.key) {
      case 'ArrowRight':
        node.scrollLeft += step
        break
      case 'ArrowLeft':
        node.scrollLeft -= step
        break
      case 'PageDown':
        node.scrollLeft += 0.9 * viewW
        break
      case 'PageUp':
        node.scrollLeft -= 0.9 * viewW
        break
      case 'Home':
        scrollToTime(0, 0)
        break
      case 'End':
        scrollToTime(total, 0.85)
        break
      case '+':
      case '=':
        zoom(1.5, viewW / 2)
        break
      case '-':
      case '_':
        zoom(1 / 1.5, viewW / 2)
        break
      case ']':
        jump(1)
        break
      case '[':
        jump(-1)
        break
      default:
        handled = false
    }
    if (handled) event.preventDefault()
  }
  const onKeyRef = useRef(onKey)
  onKeyRef.current = onKey
  useEffect(() => {
    if (!globalKeys) return
    const listener = (event: KeyboardEvent) => onKeyRef.current(event)
    // capture phase: the dialog stops keydown propagation before it reaches window
    window.addEventListener('keydown', listener, true)
    return () => window.removeEventListener('keydown', listener, true)
  }, [globalKeys])

  function toggleCollapse(next: boolean) {
    setCollapse(next)
    try {
      localStorage.setItem(COLLAPSE_KEY, next ? '1' : '0')
    } catch {
      // storage unavailable: the choice just isn't remembered
    }
  }

  return (
    <div
      className="grid gap-1.5 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
      tabIndex={globalKeys ? undefined : 0}
      onKeyDown={globalKeys ? undefined : onKey}
    >
      <div className="flex flex-wrap items-center gap-1 text-[11px] text-muted-foreground">
        <Button type="button" size="icon-xs" variant="outline" onClick={() => scrollToTime(0, 0)} aria-label={t('thesis.tf.start')}>
          <ChevronFirst />
        </Button>
        {jumps?.length ? (
          <>
            <Button type="button" size="icon-xs" variant="outline" onClick={() => jump(-1)} aria-label={t('thesis.tf.prev')}>
              <ChevronLeft />
            </Button>
            <Button type="button" size="icon-xs" variant="outline" onClick={() => jump(1)} aria-label={t('thesis.tf.next')}>
              <ChevronRight />
            </Button>
          </>
        ) : null}
        <Button type="button" size="icon-xs" variant="outline" onClick={() => scrollToTime(total, 0.85)} aria-label={t('thesis.tf.end')}>
          <ChevronLast />
        </Button>
        <Button type="button" size="icon-xs" variant="outline" onClick={() => zoom(0.5)} aria-label={t('thesis.tf.zoomOut')}>
          <ZoomOut />
        </Button>
        <Button type="button" size="icon-xs" variant="outline" onClick={() => zoom(2)} aria-label={t('thesis.tf.zoomIn')}>
          <ZoomIn />
        </Button>
        {gaps ? (
          <label className="ml-1 inline-flex cursor-pointer items-center gap-1 select-none">
            <input type="checkbox" className="size-3.5 accent-foreground" checked={collapse} onChange={(e) => toggleCollapse(e.target.checked)} />
            {t('thesis.tf.collapse')}
            {collapse && warp.gaps.length ? <span className="tabular-nums">({warp.gaps.length})</span> : null}
          </label>
        ) : null}
        <span className="tabular-nums">
          {fmtTime(t0)} – {fmtTime(Math.min(t1, total))} / {fmtTime(total)} · {fmtScale(pxPerS)}
        </span>
        {toolbar ? <span className="ml-auto flex items-center gap-1">{toolbar}</span> : null}
      </div>
      <div
        ref={scrollRef}
        className="relative overflow-x-auto overflow-y-hidden rounded-md border bg-background"
        onScroll={(event) => {
          const left = event.currentTarget.scrollLeft
          leftTime.current = warp.T(left)
          setScrollLeft(left)
        }}
        onMouseMove={(event) => {
          const rect = event.currentTarget.getBoundingClientRect()
          const x = event.clientX - rect.left
          const y = event.clientY - rect.top
          if (x < GUTTER_PX) return setTip(null)
          const cx = scrollLeft + x - GUTTER_PX
          const gap = warp.gapAt(cx)
          if (gap) {
            return setTip({ x, y, text: t('thesis.tf.collapsedTip', { a: fmtTime(gap.a), b: fmtTime(gap.b), d: fmtTime(gap.b - gap.a) }) })
          }
          if (!hit) return
          const text = hit(warp.T(cx), y)
          setTip(text ? { x, y, text } : null)
        }}
        onMouseLeave={() => setTip(null)}
      >
        <div style={{ width: contentW, height }}>
          <canvas ref={canvasRef} className="sticky left-0 top-0 block" style={{ width, height }} />
        </div>
        {tip ? (
          <div
            className="pointer-events-none absolute z-10 max-w-72 rounded-md border bg-popover px-2 py-1 text-[11px] whitespace-pre-line text-popover-foreground shadow-md"
            style={{ left: Math.min(tip.x + 12, Math.max(0, width - 260)), top: Math.min(tip.y + 12, height - 40) }}
          >
            {tip.text}
          </div>
        ) : null}
      </div>
      <p className="text-[10px] text-muted-foreground">{t('thesis.tf.scrollHint')}</p>
    </div>
  )
}

/** A collapsed gap: a faded band between two zig-zag cuts, labelled with the time it hides. */
function drawGaps(ctx: CanvasRenderingContext2D, v: TimeView, gaps: Gap[], scrollLeft: number) {
  const bottom = v.height - AXIS_PX
  ctx.save()
  ctx.beginPath()
  ctx.rect(GUTTER_PX, 0, v.width - GUTTER_PX, v.height)
  ctx.clip()
  for (const g of gaps) {
    const x0 = GUTTER_PX + g.xa - scrollLeft
    const x1 = x0 + GAP_PX
    if (x1 < GUTTER_PX || x0 > v.width) continue
    ctx.fillStyle = v.dark ? 'rgba(24,24,27,0.9)' : 'rgba(250,250,250,0.92)'
    ctx.fillRect(x0, 0, GAP_PX, bottom)
    ctx.strokeStyle = v.dark ? 'rgba(255,255,255,0.45)' : 'rgba(0,0,0,0.4)'
    ctx.lineWidth = 1
    for (const xe of [x0 + 3, x1 - 3]) {
      ctx.beginPath()
      for (let y = 0, i = 0; y <= bottom; y += 5, i++) {
        const xx = xe + (i % 2 ? 2 : -2)
        if (i) ctx.lineTo(xx, y)
        else ctx.moveTo(xx, y)
      }
      ctx.stroke()
    }
    ctx.fillStyle = v.dark ? '#d4d4d8' : '#52525b'
    ctx.font = '9px ui-sans-serif, system-ui, sans-serif'
    ctx.textAlign = 'center'
    const cx = x0 + GAP_PX / 2
    const mid = bottom / 2
    ctx.fillText(fmtTime(g.a), cx, mid - 8)
    ctx.fillText('~', cx, mid + 2)
    ctx.fillText(fmtTime(g.b), cx, mid + 12)
    ctx.textAlign = 'start'
  }
  ctx.restore()
}

const TICK_STEPS = [1e-4, 2e-4, 5e-4, 1e-3, 2e-3, 5e-3, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 30, 60, 120, 300, 600]

export const AXIS_PX = 18

function drawAxis(ctx: CanvasRenderingContext2D, v: TimeView, gaps: Gap[]) {
  const y = v.height - AXIS_PX
  const step = TICK_STEPS.find((s) => s * v.pxPerS >= 90) ?? 600
  ctx.strokeStyle = v.dark ? 'rgba(255,255,255,0.35)' : 'rgba(0,0,0,0.35)'
  ctx.fillStyle = v.dark ? '#d4d4d8' : '#52525b'
  ctx.font = '10px ui-sans-serif, system-ui, sans-serif'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(GUTTER_PX, y + 0.5)
  ctx.lineTo(v.width, y + 0.5)
  ctx.stroke()
  const inGap = (tt: number) => gaps.some((g) => tt > g.a && tt < g.b)
  // Ticks restart after each collapsed gap so labels never sit inside one.
  const starts = [v.t0, ...gaps.filter((g) => g.b > v.t0 && g.b < v.t1).map((g) => g.b)]
  const drawn = new Set<number>()
  for (const [i, s] of starts.entries()) {
    const first = (i === 0 ? Math.floor(s / step - 1e-9) : Math.ceil(s / step - 1e-9)) * step
    for (let tt = first; tt <= v.t1 + step; tt += step) {
      if (inGap(tt)) break
      const key = Math.round(tt / step)
      if (drawn.has(key)) continue
      drawn.add(key)
      const x = v.x(tt)
      if (x < GUTTER_PX - 0.5 || x > v.width) continue
      ctx.beginPath()
      ctx.moveTo(x + 0.5, y)
      ctx.lineTo(x + 0.5, y + 4)
      ctx.stroke()
      ctx.fillText(fmtTime(tt, step), x + 2, y + 13)
    }
  }
  ctx.clearRect(0, y, GUTTER_PX, AXIS_PX)
  ctx.fillText('t', GUTTER_PX - 12, y + 13)
}

export function fmtTime(t: number, step?: number): string {
  const s = step ?? (t < 1 ? 1e-3 : 1e-2)
  if (s < 1e-3) return `${(t * 1000).toFixed(1)} ms`
  if (s < 1 && t < 1) return `${(t * 1000).toFixed(0)} ms`
  const digits = s >= 1 ? 0 : s >= 0.1 ? 1 : s >= 0.01 ? 2 : 3
  return `${t.toFixed(digits)} s`
}

function fmtScale(pxPerS: number): string {
  const msPer100 = 100 / pxPerS * 1000
  return msPer100 >= 1000 ? `100 px = ${(msPer100 / 1000).toFixed(1)} s` : `100 px = ${msPer100.toFixed(msPer100 < 10 ? 1 : 0)} ms`
}

/** Fill + optional centred label clipped to the box. */
export function box(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  fill: string,
  label?: string,
  stroke?: string,
  textColor = '#18181b',
) {
  if (w <= 0 || h <= 0) return
  ctx.fillStyle = fill
  ctx.fillRect(x, y, w, h)
  if (stroke && w >= 3) {
    ctx.strokeStyle = stroke
    ctx.lineWidth = 1
    ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1)
  }
  if (label && w >= ctx.measureText(label).width + 4) {
    ctx.fillStyle = textColor
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(label, x + w / 2, y + h / 2 + 0.5)
    ctx.textAlign = 'start'
    ctx.textBaseline = 'alphabetic'
  }
}

/** Row labels on the sticky gutter (drawn last so content never covers them). */
export function gutterLabels(ctx: CanvasRenderingContext2D, v: TimeView, rows: { y: number; h: number; label: string }[]) {
  ctx.fillStyle = v.dark ? '#18181b' : '#ffffff'
  ctx.fillRect(0, 0, GUTTER_PX, v.height - AXIS_PX)
  ctx.strokeStyle = v.dark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.12)'
  ctx.beginPath()
  ctx.moveTo(GUTTER_PX - 0.5, 0)
  ctx.lineTo(GUTTER_PX - 0.5, v.height - AXIS_PX)
  ctx.stroke()
  ctx.fillStyle = v.dark ? '#d4d4d8' : '#52525b'
  ctx.font = '10px ui-sans-serif, system-ui, sans-serif'
  ctx.textBaseline = 'middle'
  for (const r of rows) ctx.fillText(r.label, 6, r.y + r.h / 2)
  ctx.textBaseline = 'alphabetic'
}
