import { STATE_COLORS } from '@/components/aperiodic/plotLayout'
import { cn } from '@/lib/utils'
import type { StepDeviceRound, StepDeviceStatic, StepRound, TraceSegment } from '@/types/aperiodicSimulation'
import { useTranslation } from 'react-i18next'
import type { StepPhase } from './stepModel'

// Paper Fig. 3: power state of a device along the round (Type 2a/2b monitor
// with a WuRX, Type 1 with its main receiver), with the stored energy between
// E_low and E_up drawn on top.

const LANE_H = 64
const MSG_COLORS: Record<string, string> = {
  paging: 'bg-sky-500/70',
  msg1: 'bg-orange-400/70',
  ei: 'bg-violet-500/60',
  msg2: 'bg-sky-600/60',
  msg3: 'bg-orange-500/70',
}

function level(state: string, type: string) {
  switch (state) {
    case 'TX':
      return 1
    case 'RX':
      return 0.62
    case 'MONITOR':
      return type === '1' ? 0.62 : 0.3
    case 'INTRA_ROUND_SLEEP':
    case 'INTERROUND_SYNC_SLEEP':
      return 0.14
    default:
      return 0.04
  }
}

function stateLabel(state: string, type: string, t: (k: string) => string) {
  if (state === 'MONITOR') return type === '1' ? `RX (${t('ap.states.MONITOR')})` : `WuRX (${t('ap.states.MONITOR')})`
  if (state === 'INTRA_ROUND_SLEEP' || state === 'INTERROUND_SYNC_SLEEP') return t('ap.step.sleep')
  if (state === 'OFF') return 'Off'
  return state
}

function phaseWindow(p: StepPhase, r: StepRound, v0: number): [number, number] | null {
  const tl = r.timeline
  switch (p) {
    case 'before':
      return [v0, r.t_start_s]
    case 'paging':
      return tl.paging
    case 'access':
      return [tl.paging[1] - 1e-4, tl.paging[1] + 1e-4]
    case 'msg1':
      return tl.msg1
    case 'ei':
      return tl.ei
    case 'msg2':
      return tl.msg2
    case 'msg3':
      return tl.msg3
    case 'after':
      return [tl.msg3[1], r.t_end_s]
  }
}

function Lane({
  dev,
  stat,
  segs,
  v0,
  v1,
}: {
  dev: StepDeviceRound
  stat: StepDeviceStatic | undefined
  segs: TraceSegment[]
  v0: number
  v1: number
}) {
  const { t } = useTranslation()
  const span = v1 - v0
  const x = (tt: number) => ((Math.min(Math.max(tt, v0), v1) - v0) / span) * 100
  const eUp = stat?.E_up_uJ ?? 1
  const eLow = stat?.E_low_uJ ?? 0
  const ey = (e: number | undefined) => (e == null ? null : 100 - ((e - eLow) / Math.max(eUp - eLow, 1e-9)) * 100)
  const pts: string[] = []
  for (const s of segs) {
    if (s.t1 < v0 || s.state === 'DONE') continue
    const y0 = ey(s.e0_uJ)
    const y1 = ey(s.e1_uJ)
    if (y0 == null || y1 == null) continue
    const a = Math.max(s.t0, v0)
    const frac = s.t1 > s.t0 ? (a - s.t0) / (s.t1 - s.t0) : 0
    pts.push(`${x(a)},${y0 + (y1 - y0) * frac}`, `${x(s.t1)},${y1}`)
  }
  return (
    <div className="grid grid-cols-[7.5rem_minmax(0,1fr)] items-stretch gap-2">
      <div className="text-[11px] leading-tight">
        <div className="font-medium">
          {t('ap.step.device')} {dev.id} · {t(`ap.terms.type${dev.type}`)}
        </div>
        <div className="text-muted-foreground">{dev.type === '1' ? t('ap.step.monitorRx') : t('ap.step.monitorWurx')}</div>
        <div className="text-muted-foreground">{dev.fate ? t(`ap.step.fate.${dev.fate}`) : '—'}</div>
      </div>
      <div className="relative border-b border-l border-border" style={{ height: LANE_H }}>
        {segs.map((s, i) => {
          if (s.t1 < v0 || s.state === 'DONE') return null
          const l = x(s.t0)
          const w = Math.max(x(s.t1) - l, 0.15)
          const lv = level(s.state, dev.type)
          return (
            <div
              key={i}
              title={`${stateLabel(s.state, dev.type, t)}${s.stage ? ` · ${s.stage}` : ''} · ${((s.t1 - s.t0) * 1e3).toFixed(1)} ms${s.e0_uJ != null ? ` · E ${s.e0_uJ.toFixed(2)} → ${(s.e1_uJ ?? 0).toFixed(2)} µJ` : ''}`}
              className="absolute bottom-0 overflow-hidden rounded-t-[2px] border border-black/10 text-center text-[9px] leading-tight text-white"
              style={{ left: `${l}%`, width: `${w}%`, height: `${lv * 100}%`, background: STATE_COLORS[s.state] ?? '#888' }}
            >
              {w > 5 && <span className="block truncate px-0.5 pt-0.5 drop-shadow">{stateLabel(s.state, dev.type, t)}</span>}
            </div>
          )
        })}
        <svg className="pointer-events-none absolute inset-0 h-full w-full overflow-visible" viewBox="0 0 100 100" preserveAspectRatio="none">
          <line x1="0" x2="100" y1="0" y2="0" stroke="currentColor" strokeDasharray="2 2" vectorEffect="non-scaling-stroke" className="text-emerald-600/60" />
          <line x1="0" x2="100" y1="100" y2="100" stroke="currentColor" strokeDasharray="2 2" vectorEffect="non-scaling-stroke" className="text-red-600/60" />
          {pts.length > 1 && (
            <polyline points={pts.join(' ')} fill="none" stroke="currentColor" strokeWidth="1.6" vectorEffect="non-scaling-stroke" className="text-foreground" />
          )}
        </svg>
        <span className="absolute -top-1 right-0 translate-x-full pl-1 text-[9px] text-emerald-700 dark:text-emerald-400">E_up</span>
        <span className="absolute right-0 -bottom-1 translate-x-full pl-1 text-[9px] text-red-700 dark:text-red-400">E_low</span>
      </div>
    </div>
  )
}

export function PowerTimeline({
  r,
  phase,
  selectedId,
  statics,
}: {
  r: StepRound
  phase: StepPhase
  selectedId: number | null
  statics: StepDeviceStatic[]
}) {
  const { t } = useTranslation()
  const part = r.devices.filter((d) => d.access === 'transmit')
  const sel = r.devices.find((d) => d.id === selectedId && d.paged_via != null) ?? part[0] ?? r.devices.find((d) => d.paged_via != null)
  if (!sel) return <p className="text-xs text-muted-foreground">{t('ap.step.noPaged')}</p>
  const isT1 = (d: StepDeviceRound) => d.type === '1'
  const other = part.find((d) => d.id !== sel.id && isT1(d) !== isT1(sel))
  const lanes = [sel, ...(other ? [other] : [])].sort((a, b) => Number(isT1(a)) - Number(isT1(b)))

  const t0 = r.t_start_s
  const pre = Math.min(
    Math.max(...lanes.map((d) => (d.segments[0] && d.segments[0].t0 < t0 ? t0 - d.segments[0].t0 : 0))),
    0.18 * (r.t_end_s - t0),
  )
  const v0 = t0 - Math.max(pre, 0.04 * (r.t_end_s - t0))
  const v1 = r.t_end_s
  const span = v1 - v0
  const x = (tt: number) => ((Math.min(Math.max(tt, v0), v1) - v0) / span) * 100
  const win = phaseWindow(phase, r, v0)
  const byId = new Map(statics.map((s) => [s.id, s]))

  return (
    <div className="grid gap-2">
      <div className="grid grid-cols-[7.5rem_minmax(0,1fr)] gap-2">
        <div className="text-[11px] text-muted-foreground">{t('ap.step.reader')}</div>
        <div className="relative h-6">
          {(['paging', 'msg1', 'ei', 'msg2', 'msg3'] as const).map((k) => {
            const [a, b] = r.timeline[k]
            const l = x(a)
            const w = x(b) - l
            return (
              <div
                key={k}
                className={cn('absolute inset-y-0 overflow-hidden rounded-[2px] text-center text-[10px] leading-6 text-white', MSG_COLORS[k])}
                style={{ left: `${l}%`, width: `${Math.max(w, 0.2)}%` }}
                title={`${k} · ${((b - a) * 1e3).toFixed(1)} ms`}
              >
                {w > 4 ? (k === 'ei' ? 'EI' : k === 'paging' ? t('ap.cbra.paging') : k.replace('msg', 'Msg')) : ''}
              </div>
            )
          })}
        </div>
      </div>
      <div className="relative grid gap-3 pr-8">
        {win && (
          <div
            className="pointer-events-none absolute inset-y-0 z-10 rounded-sm bg-fuchsia-500/15 ring-1 ring-fuchsia-500/60"
            style={{ left: `calc(7.5rem + 0.5rem + (100% - 7.5rem - 0.5rem - 2rem) * ${x(win[0]) / 100})`, width: `max(2px, calc((100% - 7.5rem - 0.5rem - 2rem) * ${(x(win[1]) - x(win[0])) / 100}))` }}
          />
        )}
        {lanes.map((d) => (
          <Lane key={d.id} dev={d} stat={byId.get(d.id)} segs={d.segments} v0={v0} v1={v1} />
        ))}
      </div>
      <div className="grid grid-cols-[7.5rem_minmax(0,1fr)] gap-2 pr-8 text-[10px] text-muted-foreground">
        <span />
        <div className="relative h-3 font-mono">
          {x(t0) > 25 && <span className="absolute left-0">−{((t0 - v0) * 1e3).toFixed(0)} ms</span>}
          <span className="absolute whitespace-nowrap" style={{ left: `${x(t0)}%`, transform: x(t0) > 25 ? 'translateX(-50%)' : 'translateX(-0.3rem)' }}>
            ▲ t0 = {t0.toFixed(3)} s
          </span>
          <span className="absolute right-0">+{((v1 - t0) * 1e3).toFixed(0)} ms</span>
        </div>
      </div>
      <p className="text-[10px] text-muted-foreground">{t('ap.step.timelineHint')}</p>
    </div>
  )
}
