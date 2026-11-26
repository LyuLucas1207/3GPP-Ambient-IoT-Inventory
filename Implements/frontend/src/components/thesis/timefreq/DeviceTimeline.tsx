import { useQuery } from '@tanstack/react-query'
import { useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchDeviceTrace } from '@/api/thesisRuns'
import { thesisKeys } from '@/lib/thesisQueryKeys'
import type { DeviceEvent, DeviceTrace, EnergySegment } from '@/types/thesis'
import { Legend } from './ReaderTimeFreq'
import { AXIS_PX, box, fmtTime, GUTTER_PX, gutterLabels, idleGaps, TimeScroller, type TimeView } from './TimeScroller'

const EN_TOP = 8
const EN_H = 128
const BAT_X = 8
const BAT_W = 18
const ACT_TOP = EN_TOP + EN_H + 10
const ACT_H = 40
const MSG_TOP = ACT_TOP + ACT_H + 4
const MSG_H = 16
const HEIGHT = MSG_TOP + MSG_H + 6 + AXIS_PX

/** Bar height per power class, as in the paper's Fig. 2 (TX > RX > on/WuRX > sleep > off). */
const LEVEL = { tx: 1, rx: 0.7, on: 0.32, sleep: 0.18, off: 0.08 } as const
const FILL = { tx: '#f8cecc', rx: '#dae8fc', on: '#e1d5e7', sleep: '#d5e8d4', off: '#e4e4e7' } as const
const STROKE = { tx: '#b85450', rx: '#6c8ebf', on: '#9673a6', sleep: '#82b366', off: '#a1a1aa' } as const

type Kind = keyof typeof LEVEL
type Act = { a: number; b: number; kind: Kind; label: string; detail: string; reader: number | null; frame: number | null }
type Marker = { t: number; text: string; color: string; detail: string }

/**
 * One device from t = 0 to the end of the run: energy (rebuilt with the
 * engine's on/off model between events), its power state, and every message it
 * sent or received, framed by the readers' rounds it took part in.
 */
export function DeviceTimeline({
  runId,
  deviceId,
  live,
  wide = false,
  energyJ = null,
  nowS = null,
}: {
  runId: number
  deviceId: number
  live: boolean
  wide?: boolean
  /** Charge at the replay cursor or the live frame. The battery uses this. */
  energyJ?: number | null
  /** Simulation time to draw up to. While a run is going this is the live clock. */
  nowS?: number | null
}) {
  const { t } = useTranslation()
  const query = useQuery({
    queryKey: thesisKeys.deviceTrace(runId, deviceId),
    queryFn: () => fetchDeviceTrace(runId, deviceId),
    refetchInterval: live ? 2000 : false,
    staleTime: live ? 0 : Infinity,
  })
  const trace = query.data ?? null
  const model = useMemo(() => (trace ? buildModel(trace, t) : null), [trace, t])
  const clock = nowS != null && Number.isFinite(nowS) ? Math.max(0, nowS) : null
  const tEnd = Math.max(trace?.t_end ?? 0, model?.lastT ?? 0, clock ?? 0, 1e-3)
  const gaps = useMemo(() => {
    if (!model) return []
    const busy: [number, number][] = model.acts.filter((a) => a.kind !== 'sleep').map((a) => [a.a, a.b])
    for (const m of model.markers) busy.push([m.t, m.t])
    return idleGaps(busy, tEnd)
  }, [model, tEnd])

  const draw = useCallback(
    (ctx: CanvasRenderingContext2D, v: TimeView) => {
      if (!trace || !model) return
      const { ecap, eoff, lo, hi, yE } = energyFrame(trace, energyJ)
      const tip = liveTip(trace, clock, energyJ)
      const ink = v.dark ? '#e4e4e7' : '#3f3f46'
      const grid = v.dark ? 'rgba(255,255,255,0.25)' : 'rgba(0,0,0,0.25)'

      for (const r of model.rounds) {
        if (clock != null && r.t_start_s > clock) continue
        if (r.t_end_s < v.t0 || r.t_start_s > v.t1) continue
        const x0 = v.x(r.t_start_s)
        const end = clock != null ? Math.min(r.t_end_s, clock) : r.t_end_s
        const x1 = v.x(end)
        ctx.fillStyle = v.dark ? 'rgba(157,195,230,0.08)' : 'rgba(157,195,230,0.16)'
        ctx.fillRect(x0, EN_TOP, x1 - x0, MSG_TOP + MSG_H - EN_TOP)
        if (x1 - x0 > 70) {
          ctx.fillStyle = ink
          ctx.font = '9px ui-sans-serif, system-ui, sans-serif'
          ctx.fillText(`R#${r.reader_id} · #${r.round_index}`, Math.max(x0, GUTTER_PX) + 3, EN_TOP + 9)
        }
      }

      // E(t): solid while the device is on and draining, dashed while it is off and harvesting.
      ctx.save()
      ctx.beginPath()
      ctx.rect(GUTTER_PX, EN_TOP, v.width - GUTTER_PX, EN_H)
      ctx.clip()
      ctx.beginPath()
      let pen = false
      const plotted = tip ? [...trace.segments, tip] : trace.segments
      for (const raw of plotted) {
        const s = clipTo(raw, clock)
        if (!s) continue
        const x0 = v.x(s[0])
        const y0 = yE(s[2])
        const x1 = v.x(s[1])
        const y1 = yE(s[3])
        if (!pen) {
          ctx.moveTo(x0, y0)
          pen = true
        }
        ctx.lineTo(x1, y1)
      }
      if (pen && plotted.length > 0) {
        const last = clipTo(plotted[plotted.length - 1], clock) ?? plotted[plotted.length - 1]
        const first = plotted[0]
        ctx.lineTo(v.x(last[1]), EN_TOP + EN_H)
        ctx.lineTo(v.x(first[0]), EN_TOP + EN_H)
        ctx.closePath()
        ctx.fillStyle = v.dark ? 'rgba(34,197,94,0.16)' : 'rgba(34,197,94,0.18)'
        ctx.fill()
      }
      ctx.restore()
      ctx.setLineDash([4, 3])
      ctx.strokeStyle = grid
      ctx.lineWidth = 1
      for (const [e, label] of [[ecap, 'E_up'], [eoff, 'E_low']] as const) {
        if (e < lo || e > hi) continue
        const y = Math.round(yE(e)) + 0.5
        ctx.beginPath()
        ctx.moveTo(GUTTER_PX, y)
        ctx.lineTo(v.width, y)
        ctx.stroke()
        ctx.fillStyle = ink
        ctx.font = '10px ui-sans-serif, system-ui, sans-serif'
        ctx.fillText(label, GUTTER_PX + 4, y - 3)
      }
      ctx.setLineDash([])

      // Power state bars: OFF / ON from the energy model, protocol activity on top.
      const base = ACT_TOP + ACT_H
      for (const raw of trace.segments) {
        const s = clipTo(raw, clock)
        if (!s || s[1] < v.t0 || s[0] > v.t1) continue
        const kind: Kind = s[4] === 'on' ? 'on' : 'off'
        const x = v.x(s[0])
        const w = v.w(s[0], s[1])
        const h = ACT_H * LEVEL[kind]
        box(ctx, x, base - h, w, h, FILL[kind], kind === 'off' ? 'Off' : 'On', undefined, '#52525b')
      }
      ctx.font = '9px ui-sans-serif, system-ui, sans-serif'
      for (const a of model.acts) {
        if (clock != null && a.a > clock) continue
        const b = clock != null ? Math.min(a.b, clock) : a.b
        if (b < v.t0 || a.a > v.t1) continue
        const x = v.x(a.a)
        const w = Math.max(1, v.w(a.a, b))
        const h = ACT_H * LEVEL[a.kind]
        box(ctx, x, base - h, w, h, FILL[a.kind], a.label, STROKE[a.kind])
      }
      ctx.fillStyle = grid
      ctx.fillRect(GUTTER_PX, base, v.width, 1)

      const pts = model.samples
      if (!trace.energy_exact && pts.length > 1) {
        ctx.strokeStyle = v.dark ? '#a1a1aa' : '#71717a'
        ctx.setLineDash([2, 3])
        ctx.beginPath()
        pts.forEach(([tt, e], i) => (i ? ctx.lineTo(v.x(tt), yE(e)) : ctx.moveTo(v.x(tt), yE(e))))
        ctx.stroke()
        ctx.setLineDash([])
      }
      ctx.fillStyle = '#1d4ed8'
      for (const [tt, e] of pts) {
        if (tt < v.t0 || tt > v.t1 || (clock != null && tt > clock)) continue
        ctx.beginPath()
        ctx.arc(v.x(tt), yE(e), 2, 0, Math.PI * 2)
        ctx.fill()
      }

      for (const m of model.markers) {
        if (clock != null && m.t > clock) continue
        if (m.t < v.t0 || m.t > v.t1) continue
        const x = v.x(m.t)
        ctx.fillStyle = m.color
        ctx.fillRect(Math.round(x), EN_TOP, 1.5, MSG_TOP - EN_TOP)
        ctx.fillText(m.text, x + 2, MSG_TOP + 11)
      }

      gutterLabels(ctx, v, [
        { y: ACT_TOP, h: ACT_H, label: t('thesis.tf.state') },
        { y: MSG_TOP, h: MSG_H, label: t('thesis.tf.messages') },
      ])
      // Drawn after the gutter fill, which repaints the whole left column.
      const now = energyJ ?? trace.segments.at(-1)?.[3] ?? 0
      drawBattery(ctx, BAT_X, EN_TOP, BAT_W, EN_H, trace.energy.ecap > 0 ? now / trace.energy.ecap : 0, v.dark)
    },
    [trace, model, t, energyJ, clock],
  )

  // Drawn after the idle zig-zags, which otherwise paint over the Off segments
  // and leave the On slopes looking disconnected.
  const overlay = useCallback(
    (ctx: CanvasRenderingContext2D, v: TimeView) => {
      const tip = trace ? liveTip(trace, clock, energyJ) : null
      const plotted = trace ? (tip ? [...trace.segments, tip] : trace.segments) : []
      if (trace && plotted.length > 0) {
        const { yE } = energyFrame(trace, energyJ)
        ctx.save()
        ctx.beginPath()
        ctx.rect(GUTTER_PX, EN_TOP, Math.max(0, v.width - GUTTER_PX), EN_H)
        ctx.clip()
        ctx.lineWidth = 2
        ctx.lineJoin = 'round'
        ctx.lineCap = 'round'
        for (const raw of plotted) {
          const s = clipTo(raw, clock)
          if (!s || s[1] < v.t0 || s[0] > v.t1) continue
          const on = s[4] === 'on'
          ctx.strokeStyle = on ? '#1d4ed8' : v.dark ? '#e4e4e7' : '#18181b'
          ctx.setLineDash(on ? [] : [4, 3])
          ctx.beginPath()
          ctx.moveTo(v.x(s[0]), yE(s[2]))
          ctx.lineTo(v.x(s[1]), yE(s[3]))
          ctx.stroke()
        }
        ctx.restore()
        ctx.setLineDash([])
      }
      if (clock != null) {
        const x = Math.round(v.x(clock)) + 0.5
        if (x >= GUTTER_PX && x <= v.width) {
          ctx.save()
          ctx.strokeStyle = '#16a34a'
          ctx.lineWidth = 1.5
          ctx.setLineDash([])
          ctx.beginPath()
          ctx.moveTo(x, EN_TOP)
          ctx.lineTo(x, MSG_TOP + MSG_H)
          ctx.stroke()
          ctx.fillStyle = '#15803d'
          ctx.font = '10px ui-sans-serif, system-ui, sans-serif'
          ctx.fillText(fmtTime(clock), Math.min(x + 3, v.width - 36), EN_TOP + 12)
          ctx.restore()
        }
      }
    },
    [trace, clock, energyJ],
  )

  const hit = useCallback(
    (time: number, y: number) => {
      if (!trace || !model) return null
      const tol = 4 / 1000
      const marker = y >= MSG_TOP ? model.markers.find((m) => Math.abs(m.t - time) < tol) : null
      if (marker) return `${fmtTime(marker.t)} · ${marker.detail}`
      const act = model.acts.find((a) => time >= a.a && time <= a.b)
      const energy = energyAt(trace, model.samples, time)
      const eLine = energy != null ? `E ≈ ${(energy * 1e6).toFixed(3)} µJ` : ''
      if (act) {
        const where = act.reader != null ? ` · R#${act.reader}${act.frame != null ? ` #${act.frame}` : ''}` : ''
        return [`${act.detail}${where}`, `${fmtTime(act.a)} → ${fmtTime(act.b)}`, eLine].filter(Boolean).join('\n')
      }
      const seg = trace.segments.find((s) => time >= s[0] && time <= s[1])
      if (seg) return [t(seg[4] === 'on' ? 'thesis.tf.on' : 'thesis.tf.off'), eLine].join('\n')
      return eLine || null
    },
    [trace, model, t],
  )

  if (!trace && clock == null) {
    return query.isLoading ? <p className="text-xs text-muted-foreground">{t('thesis.timeline.loading')}</p> : null
  }
  return (
    <div className="grid gap-1.5">
      <TimeScroller
        tEnd={tEnd}
        height={HEIGHT}
        draw={draw}
        overlay={overlay}
        hit={hit}
        jumps={model?.jumps}
        gaps={gaps}
        globalKeys={wide}
        followLatest={live && clock != null}
        initialPxPerS={1000}
        redrawKey={query.dataUpdatedAt}
        toolbar={
          clock != null ? (
            <span className="font-medium text-foreground tabular-nums">
              {t('thesis.live.simTime')} {fmtTime(clock)}
            </span>
          ) : query.isFetching ? (
            <span>{t('thesis.timeline.loading')}</span>
          ) : null
        }
      />
      <Legend
        items={[
          [FILL.tx, 'TX'],
          [FILL.rx, 'RX'],
          [FILL.sleep, t('thesis.tf.sleep')],
          [FILL.on, t('thesis.tf.onShort')],
          [FILL.off, t('thesis.tf.offShort')],
          ['rgba(157,195,230,0.4)', t('thesis.tf.readerFrame')],
        ]}
      />
      {trace && !trace.energy_exact ? <p className="text-[10px] text-muted-foreground">{t('thesis.tf.energyApprox')}</p> : null}
    </div>
  )
}

/** Keep the part of a segment that has already happened by `now`. */
function clipTo(s: EnergySegment, now: number | null): EnergySegment | null {
  if (now == null || s[1] <= now) return s
  if (s[0] >= now) return null
  const u = (now - s[0]) / Math.max(s[1] - s[0], 1e-12)
  return [s[0], now, s[2], s[2] + (s[3] - s[2]) * u, s[4]]
}

/** Straight connector from the last recorded point to the live clock and charge. */
function liveTip(trace: DeviceTrace, now: number | null, energyJ: number | null): EnergySegment | null {
  if (now == null || energyJ == null) return null
  const last = trace.segments[trace.segments.length - 1]
  if (last) {
    if (now <= last[1] + 1e-4) return null
    return [last[1], now, last[3], energyJ, energyJ >= last[3] ? 'off' : 'on']
  }
  if (now <= 0) return null
  return [0, now, trace.energy.ecap, energyJ, energyJ >= trace.energy.ecap ? 'off' : 'on']
}

/** Vertical scale of the energy row, fitted to the energy this device actually reaches. */
function energyFrame(trace: DeviceTrace, extraE?: number | null) {
  const { ecap, eoff } = trace.energy
  let emin = Infinity
  let emax = -Infinity
  for (const s of trace.segments) {
    emin = Math.min(emin, s[2], s[3])
    emax = Math.max(emax, s[2], s[3])
  }
  if (extraE != null && Number.isFinite(extraE)) {
    emin = Math.min(emin, extraE)
    emax = Math.max(emax, extraE)
  }
  if (!Number.isFinite(emin)) {
    emin = eoff
    emax = ecap
  }
  const pad = Math.max((emax - emin) * 0.22, Math.abs(emax) * 0.01, 1e-12)
  const lo = emin - pad
  const hi = emax + pad
  const yE = (e: number) => EN_TOP + EN_H * (1 - (e - lo) / (hi - lo))
  return { ecap, eoff, lo, hi, yE }
}

/** Battery glyph: green fill rises from the bottom with the fraction of E_cap still stored. */
function drawBattery(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, frac: number, dark: boolean) {
  const f = Math.min(1, Math.max(0, frac))
  const capH = 5
  const capW = w * 0.46
  ctx.fillStyle = dark ? '#a1a1aa' : '#52525b'
  ctx.fillRect(x + (w - capW) / 2, y, capW, capH)
  const bodyY = y + capH + 2
  const bodyH = h - capH - 2
  ctx.fillStyle = dark ? '#27272a' : '#f4f4f5'
  ctx.fillRect(x, bodyY, w, bodyH)
  const fillH = Math.max(0, (bodyH - 4) * f)
  ctx.fillStyle = '#22c55e'
  ctx.fillRect(x + 2, bodyY + bodyH - 2 - fillH, w - 4, fillH)
  ctx.strokeStyle = dark ? '#e4e4e7' : '#3f3f46'
  ctx.lineWidth = 1.5
  ctx.strokeRect(x + 0.75, bodyY + 0.75, w - 1.5, bodyH - 1.5)
}

function buildModel(trace: DeviceTrace, t: (k: string, o?: Record<string, unknown>) => string) {
  const c = trace.consts
  const roundById = new Map(trace.rounds.map((r) => [r.id, r]))
  const byRound = new Map<number, DeviceEvent[]>()
  const markers: Marker[] = []
  const samples: [number, number][] = []
  for (const e of trace.events) {
    if (e.energy_j != null) samples.push([e.t_s, e.energy_j])
    if (e.round_id != null) {
      const list = byRound.get(e.round_id) ?? []
      list.push(e)
      byRound.set(e.round_id, list)
    }
    const m = markerOf(e, t)
    if (m) markers.push(m)
  }
  const acts: Act[] = []
  for (const [roundId, events] of byRound) {
    const r = roundById.get(roundId)
    const t0 = r?.t_start_s ?? events[0].t_s
    const tPg = r?.timing.paging ?? c.t_paging
    const tEbi = r?.timing.ebi ?? 0
    const frame = r?.round_index ?? null
    const reader = r?.reader_id ?? events[0].reader_id
    const mine: Act[] = []
    const outcome = events.find((e) => M1_OUTCOMES.has(e.event_type))
    const grant = r?.subbands ?? null
    for (const e of events) {
      const slot = (e.payload?.slot as number | undefined) ?? null
      switch (e.event_type) {
        case 'paged':
          mine.push({ a: t0, b: t0 + tPg, kind: 'rx', label: 'Paging', detail: t('thesis.tf.act.paged'), reader, frame })
          break
        case 'missed_page':
          mine.push({ a: t0, b: t0 + tPg, kind: 'rx', label: 'Paging', detail: t('thesis.tf.act.missedPage'), reader, frame })
          break
        case 'm1_tx':
          mine.push({
            a: e.t_s,
            b: e.t_s + c.t_m1,
            kind: 'tx',
            label: 'Msg1',
            detail: t('thesis.tf.act.m1', {
              slot,
              f: slot != null ? (grant?.length ? grant[slot % grant.length] : slot % c.f) : '',
              result: outcome ? t(`thesis.live.event.${outcome.event_type}`, { defaultValue: outcome.event_type }) : '—',
            }),
            reader,
            frame,
          })
          break
        case 'ebi_received':
          mine.push({ a: e.t_s - tEbi, b: e.t_s, kind: 'rx', label: 'EI', detail: t('thesis.tf.act.ei'), reader, frame })
          break
        case 'm2_rx':
          mine.push({ a: e.t_s - c.t_m2, b: e.t_s, kind: 'rx', label: 'Msg2', detail: t('thesis.tf.act.m2', { i: Number(e.payload?.m2_index ?? 0) + 1 }), reader, frame })
          break
        case 'm3_tx':
          mine.push({ a: e.t_s, b: e.t_s + c.t_m3, kind: 'tx', label: 'Msg3', detail: t('thesis.tf.act.m3'), reader, frame })
          break
      }
    }
    mine.sort((x, y) => x.a - y.a)
    for (let i = 0; i < mine.length; i++) {
      acts.push(mine[i])
      const next = mine[i + 1]
      if (next && next.a > mine[i].b + 1e-9) {
        acts.push({ a: mine[i].b, b: next.a, kind: 'sleep', label: 'Sleep', detail: t('thesis.tf.act.sleep'), reader, frame })
      }
    }
  }
  acts.sort((x, y) => x.a - y.a)
  const rounds = [...trace.rounds].sort((a, b) => a.t_start_s - b.t_start_s)
  const lastT = Math.max(0, ...trace.events.map((e) => e.t_s), ...acts.map((a) => a.b))
  return { acts, markers, samples, rounds, jumps: rounds.map((r) => r.t_start_s), lastT }
}

const M1_OUTCOMES = new Set(['m1_success', 'm1_collision', 'm1_empty', 'm1_interfered'])

function markerOf(e: DeviceEvent, t: (k: string, o?: Record<string, unknown>) => string): Marker | null {
  const label = t(`thesis.live.event.${e.event_type}`, { defaultValue: e.event_type })
  const detail = e.cause ? `${label} (${e.cause})` : label
  switch (e.event_type) {
    case 'identified':
      return { t: e.t_s, text: '✓', color: '#4d7c0f', detail }
    case 'depleted':
      return { t: e.t_s, text: '⚡', color: '#ec4899', detail }
    case 'dropped':
      return { t: e.t_s, text: '✗', color: '#ef4444', detail }
    case 'budget_drop':
      return { t: e.t_s, text: '⌀', color: '#d95319', detail }
    case 'm1_collision':
      return { t: e.t_s, text: '×', color: '#d95319', detail }
    case 'm1_empty':
      return { t: e.t_s, text: '?', color: '#71717a', detail }
    case 'latched':
      return { t: e.t_s, text: 'L', color: '#7e2f8e', detail }
    case 'm1_interfered':
    case 'm2_interfered':
    case 'm3_interfered':
      return { t: e.t_s, text: '≋', color: '#a2142f', detail }
    default:
      return null
  }
}

function energyAt(trace: DeviceTrace, samples: [number, number][], time: number): number | null {
  const seg = trace.segments.find((s) => time >= s[0] && time <= s[1])
  if (seg) {
    const f = seg[1] > seg[0] ? (time - seg[0]) / (seg[1] - seg[0]) : 0
    return seg[2] + f * (seg[3] - seg[2])
  }
  let prev: [number, number] | null = null
  for (const s of samples) {
    if (s[0] > time) break
    prev = s
  }
  return prev ? prev[1] : null
}
