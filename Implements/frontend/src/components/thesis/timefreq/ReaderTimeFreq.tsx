import { useQueries } from '@tanstack/react-query'
import { useCallback, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchReaderTimeFreq } from '@/api/thesisRuns'
import { thesisKeys } from '@/lib/thesisQueryKeys'
import type { FrameConsts, ReaderTimeFreq as ReaderTimeFreqData, TimeFreqFrame } from '@/types/thesis'
import { AXIS_PX, box, fmtTime, GUTTER_PX, gutterLabels, TimeScroller, type TimeView } from './TimeScroller'

/** Simulated seconds fetched per request; frames are drawn only once their chunk is in. */
const CHUNK_S = 10
const TOP = 16
const ROW = 14
const GAP = 6
const DL_ROW = 20

export const TF_COLORS = {
  paging: '#9dc3e6',
  ei: '#9dc3e6',
  m2: '#bdd7ee',
  m2Unused: 'rgba(157,195,230,0.18)',
  idle: '#fafafa',
  idleDark: '#27272a',
  single: '#ffe699',
  captured: '#ffd34d',
  collision: '#f4b183',
  missed: '#d4d4d8',
  m3: '#ffe699',
  identified: '#4d7c0f',
}

const SLOT_FILL = [TF_COLORS.idle, TF_COLORS.single, TF_COLORS.captured, TF_COLORS.collision, TF_COLORS.missed]

/**
 * One reader's frames on the paper's time-frequency grid (Fig. 1b), from the
 * first frame to the last: uplink subbands carry the K Msg1 slots and the
 * parallel Msg3s, the downlink row paging, EI and the Msg2s one after another.
 */
export function ReaderTimeFreq({
  runId,
  readerId,
  live,
  wide = false,
}: {
  runId: number
  readerId: number
  live: boolean
  wide?: boolean
}) {
  const { t } = useTranslation()
  const [chunks, setChunks] = useState<[number, number]>([0, 0])

  const { frames, meta, tEnd, loading, dataKey } = useQueries({
    queries: range(chunks[0], chunks[1]).map((c) => ({
      queryKey: thesisKeys.readerTimeFreq(runId, readerId, c),
      queryFn: () => fetchReaderTimeFreq(runId, readerId, c * CHUNK_S, (c + 1) * CHUNK_S),
      staleTime: live ? 0 : Infinity,
      refetchInterval: live ? 1500 : (false as const),
    })),
    combine: combineChunks,
  })
  const consts = meta?.consts ?? null
  const F = consts?.f ?? 8
  const height = TOP + F * ROW + GAP + DL_ROW + GAP + AXIS_PX
  const dlTop = TOP + F * ROW + GAP
  const jumps = useMemo(() => frames.map((f) => f.t_start_s).sort((a, b) => a - b), [frames])
  const gaps = useMemo(() => (consts ? frameGaps(frames, consts) : []), [frames, consts])

  const onWindow = useCallback((t0: number, t1: number) => {
    const a = Math.max(0, Math.floor(t0 / CHUNK_S))
    const b = Math.max(a, Math.floor(t1 / CHUNK_S)) + 1
    setChunks((prev) => (prev[0] === a && prev[1] === b ? prev : [a, b]))
  }, [])

  const draw = useCallback(
    (ctx: CanvasRenderingContext2D, v: TimeView) => {
      if (!consts) return
      ctx.font = '9px ui-sans-serif, system-ui, sans-serif'
      const gridStroke = v.dark ? 'rgba(255,255,255,0.18)' : 'rgba(0,0,0,0.18)'
      for (let f = 0; f <= F; f++) {
        ctx.fillStyle = gridStroke
        ctx.fillRect(GUTTER_PX, TOP + f * ROW, v.width, f === 0 || f === F ? 1 : 0.5)
      }
      ctx.fillRect(GUTTER_PX, dlTop + DL_ROW, v.width, 1)
      for (const fr of frames) {
        if (fr.t_end_s < v.t0 || fr.t_start_s > v.t1) continue
        drawFrame(ctx, v, fr, consts, dlTop)
      }
      gutterLabels(ctx, v, [
        { y: 0, h: TOP, label: t('thesis.tf.frame') },
        ...range(0, F - 1).map((f) => ({ y: TOP + f * ROW, h: ROW, label: `UL f${f}` })),
        { y: dlTop, h: DL_ROW, label: 'DL' },
      ])
    },
    [frames, consts, F, dlTop, t],
  )

  const hit = useCallback(
    (time: number, y: number) => {
      if (!consts) return null
      const fr = frames.find((f) => time >= f.t_start_s && time <= f.t_end_s)
      if (!fr) return null
      return describe(fr, consts, time, y, dlTop, t)
    },
    [frames, consts, dlTop, t],
  )

  if (!meta && loading) return <p className="text-xs text-muted-foreground">{t('thesis.timeline.loading')}</p>
  if (meta && meta.t_end <= 0 && frames.length === 0) return <p className="text-xs text-muted-foreground">{t('thesis.tf.noFrames')}</p>
  return (
    <div className="grid gap-1.5">
      <TimeScroller
        tEnd={tEnd}
        height={height}
        draw={draw}
        hit={hit}
        onWindow={onWindow}
        redrawKey={dataKey}
        jumps={jumps}
        gaps={gaps}
        globalKeys={wide}
        initialPxPerS={consts ? Math.min(20000, 14 / consts.t_m1) : 2000}
        toolbar={loading ? <span>{t('thesis.timeline.loading')}</span> : null}
      />
      <Legend
        items={[
          [TF_COLORS.paging, t('thesis.tf.legend.dl')],
          [TF_COLORS.single, t('thesis.tf.legend.single')],
          [TF_COLORS.captured, t('thesis.tf.legend.captured')],
          [TF_COLORS.collision, t('thesis.tf.legend.collision')],
          [TF_COLORS.missed, t('thesis.tf.legend.missed')],
          [TF_COLORS.idle, t('thesis.tf.legend.idle')],
          [TF_COLORS.m2Unused, t('thesis.tf.legend.m2Unused')],
        ]}
      />
    </div>
  )
}

function drawFrame(ctx: CanvasRenderingContext2D, v: TimeView, fr: TimeFreqFrame, c: FrameConsts, dlTop: number) {
  const F = Math.max(1, fr.f || c.f)
  const tm = fr.timing
  const tPg = tm.paging ?? c.t_paging
  const tM1 = fr.t_start_s + tPg
  const tEbi = tM1 + (tm.m1 ?? Math.ceil(fr.k / F) * c.t_m1)
  const tM2 = tEbi + (tm.ebi ?? 0)
  const px = v.pxPerS
  const x0 = v.x(fr.t_start_s)
  const x1 = v.x(fr.t_end_s)
  const ink = v.dark ? '#e4e4e7' : '#3f3f46'

  ctx.fillStyle = v.dark ? 'rgba(255,255,255,0.25)' : 'rgba(0,0,0,0.25)'
  ctx.fillRect(Math.round(x0), 0, 1, v.height - AXIS_PX)
  ctx.font = '10px ui-sans-serif, system-ui, sans-serif'
  const label = `#${fr.round_index} · K=${fr.k}${fr.group != null ? ` · g${fr.group}` : ''}${fr.pstar != null ? ` · p*=${fr.pstar.toFixed(2)}` : ''}`
  if (x1 - x0 > 60) {
    ctx.save()
    ctx.beginPath()
    ctx.rect(x0 + 2, 0, x1 - x0 - 4, 15)
    ctx.clip()
    ctx.fillStyle = ink
    ctx.fillText(label, Math.max(x0 + 3, GUTTER_PX + 3), 11)
    ctx.restore()
  }
  ctx.font = '9px ui-sans-serif, system-ui, sans-serif'

  box(ctx, x0, dlTop + 2, v.w(fr.t_start_s, tM1), DL_ROW - 4, TF_COLORS.paging, 'Paging', '#5b9bd5')
  if ((tm.ebi ?? 0) > 0) box(ctx, v.x(tEbi), dlTop + 2, v.w(tEbi, tM2), DL_ROW - 4, TF_COLORS.ei, 'EI', '#5b9bd5')
  if ((tm.m2 ?? 0) > 0) box(ctx, v.x(tM2), dlTop + 2, v.w(tM2, tM2 + (tm.m2 ?? 0)), DL_ROW - 4, TF_COLORS.m2Unused)
  fr.m2.forEach((dev, i) => {
    const ta = tM2 + i * c.t_m2
    const xs = v.x(ta)
    const w = v.w(ta, ta + c.t_m2)
    if (xs > v.width || xs + w < GUTTER_PX) return
    box(ctx, xs, dlTop + 2, w, DL_ROW - 4, TF_COLORS.m2, String(dev), '#5b9bd5')
  })

  const cellW = c.t_m1 * px
  if (cellW < 2) {
    const s = fr.res.filter((r) => r === 1 || r === 2).length
    const col = fr.res.filter((r) => r === 3).length
    box(ctx, v.x(tM1), TOP, v.w(tM1, tEbi), F * ROW, TF_COLORS.collision, `${s}✓ ${col}✗`)
  } else {
    const idleFill = v.dark ? TF_COLORS.idleDark : TF_COLORS.idle
    for (let s = 0; s < fr.k; s++) {
      const col = Math.floor(s / F)
      const xs = v.x(tM1 + col * c.t_m1)
      if (xs > v.width || xs + cellW < GUTTER_PX) continue
      const res = fr.res[s] ?? 0
      const win = fr.winners[String(s)]
      const text = win ? String(win[0]) : res === 3 ? `×${fr.occ[s] ?? ''}` : res === 4 ? 'miss' : ''
      box(ctx, xs, TOP + (s % F) * ROW, cellW, ROW, res === 0 ? idleFill : SLOT_FILL[res] ?? idleFill, text, 'rgba(0,0,0,0.25)')
    }
  }

  for (const [ts, row, dev, ident] of fr.m3) {
    const xs = v.x(ts)
    const m3W = v.w(ts, ts + c.t_m3)
    if (xs > v.width || xs + m3W < GUTTER_PX) continue
    box(ctx, xs, TOP + (row % F) * ROW, m3W, ROW, TF_COLORS.m3, String(dev), ident ? TF_COLORS.identified : 'rgba(0,0,0,0.3)')
  }
}

/**
 * Stretches where the reader is on air for nothing: the reserved Msg2 time
 * nobody was served in (before Msg3 starts), the tail after the last Msg3,
 * and any wait between frames.
 */
function frameGaps(frames: TimeFreqFrame[], c: FrameConsts): [number, number][] {
  const out: [number, number][] = []
  let prevEnd: number | null = null
  // a frame in the first chunk is the reader's first frame (e.g. a staggered start)
  if (frames.length && frames[0].t_start_s > 0 && frames[0].t_start_s < CHUNK_S) out.push([0, frames[0].t_start_s])
  for (const fr of frames) {
    if (prevEnd != null && fr.t_start_s > prevEnd) out.push([prevEnd, fr.t_start_s])
    prevEnd = Math.max(prevEnd ?? 0, fr.t_end_s)
    const F = Math.max(1, fr.f || c.f)
    const tm = fr.timing
    const tM1 = fr.t_start_s + (tm.paging ?? c.t_paging)
    const tM2 = tM1 + (tm.m1 ?? Math.ceil(fr.k / F) * c.t_m1) + (tm.ebi ?? 0)
    const tM3 = tM2 + (tm.m2 ?? 0)
    const m2End = tM2 + fr.m2.length * c.t_m2
    if (tM3 > m2End) out.push([m2End, tM3])
    const m3End = fr.m3.length ? Math.max(...fr.m3.map(([ts]) => ts)) + c.t_m3 : tM3
    if (fr.t_end_s > Math.max(m3End, m2End)) out.push([Math.max(m3End, m2End), fr.t_end_s])
  }
  return out
}

function describe(
  fr: TimeFreqFrame,
  c: FrameConsts,
  time: number,
  y: number,
  dlTop: number,
  t: (k: string, o?: Record<string, unknown>) => string,
): string {
  const F = Math.max(1, fr.f || c.f)
  const tm = fr.timing
  const tPg = tm.paging ?? c.t_paging
  const tM1 = fr.t_start_s + tPg
  const tEbi = tM1 + (tm.m1 ?? Math.ceil(fr.k / F) * c.t_m1)
  const tM2 = tEbi + (tm.ebi ?? 0)
  const tM3 = tM2 + (tm.m2 ?? 0)
  const head = `${t('thesis.tf.frame')} #${fr.round_index} · ${fmtTime(fr.t_start_s)} → ${fmtTime(fr.t_end_s)} · K=${fr.k}`
  const success = fr.res.filter((r) => r === 1 || r === 2).length
  const collisions = fr.res.filter((r) => r === 3).length
  const summary = t('thesis.tf.frameSummary', {
    success,
    collisions,
    idle: fr.res.filter((r) => r === 0).length,
    served: fr.m2.length,
    dropped: fr.budget_dropped,
  })
  let part = ''
  if (y >= dlTop && y <= dlTop + DL_ROW) {
    if (time < tM1) part = t('thesis.tf.part.paging')
    else if (time >= tEbi && time < tM2) part = t('thesis.tf.part.ei')
    else if (time >= tM2 && time < tM3) {
      const i = Math.floor((time - tM2) / c.t_m2)
      part = fr.m2[i] != null ? t('thesis.tf.part.m2', { i: i + 1, dev: fr.m2[i] }) : t('thesis.tf.part.m2Unused')
    }
  } else if (y >= TOP && y < TOP + F * ROW) {
    const f = Math.floor((y - TOP) / ROW)
    if (time >= tM1 && time < tEbi) {
      const s = Math.floor((time - tM1) / c.t_m1) * F + f
      if (s < fr.k) {
        const res = fr.res[s] ?? 0
        const win = fr.winners[String(s)]
        part = t(`thesis.tf.slot.${['idle', 'single', 'captured', 'collision', 'missed'][res] ?? 'idle'}`, {
          s,
          f,
          n: fr.occ[s] ?? 0,
          dev: win ? win[0] : '',
        })
      }
    } else if (time >= tM3) {
      const m3 = fr.m3.find(([ts, row]) => row === f && time >= ts && time < ts + c.t_m3)
      if (m3) part = t(m3[3] ? 'thesis.tf.part.m3Identified' : 'thesis.tf.part.m3', { dev: m3[2], f })
    }
  }
  return [head, summary, part].filter(Boolean).join('\n')
}

function combineChunks(results: { data?: ReaderTimeFreqData; isFetching: boolean; dataUpdatedAt: number }[]) {
  const loaded = results.map((r) => r.data).filter((d): d is ReaderTimeFreqData => d != null)
  const byId = new Map<number, TimeFreqFrame>()
  for (const c of loaded) for (const f of c.frames) byId.set(f.id, f)
  return {
    frames: [...byId.values()].sort((a, b) => a.t_start_s - b.t_start_s),
    meta: loaded[0] ?? null,
    tEnd: Math.max(1e-3, ...loaded.map((d) => d.t_end)),
    loading: results.some((r) => r.isFetching && !r.data),
    dataKey: results.map((r) => r.dataUpdatedAt).join(','),
  }
}

function range(a: number, b: number): number[] {
  const out: number[] = []
  for (let i = a; i <= b; i++) out.push(i)
  return out
}

export function Legend({ items }: { items: [string, string][] }) {
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
      {items.map(([color, label]) => (
        <span key={label} className="inline-flex items-center gap-1">
          <span className="inline-block size-2.5 rounded-[2px] border border-black/20" style={{ background: color }} />
          {label}
        </span>
      ))}
    </div>
  )
}
