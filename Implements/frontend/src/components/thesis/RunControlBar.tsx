import { Pause, Play, Radio, Square } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { StatusChip } from '@/components/thesis/ThesisRightPanel'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import type { LiveRunState } from '@/hooks/useLiveRun'
import { RUN_STATE_COLOR, RUN_STATE_LABELS, SPEED_OPTIONS, runDisplayName } from '@/lib/thesisRunStates'
import type { RunStatus, RunSummary } from '@/types/thesis'

const LIVE: ReadonlySet<RunStatus> = new Set(['pending', 'running'])
const REPLAY_TICK_MS = 250
const REPLAY_MAX_SPEED = 100
const IDENTIFIED_CODE = RUN_STATE_LABELS.indexOf('identified')

/** Bottom HUD of the simulation page for the selected run. */
export function RunControlBar({
  run,
  config = null,
  live,
  busy,
  onPause,
  onResume,
  onStop,
  onSpeed,
}: {
  run: RunSummary
  /** Frozen create-run settings from GET /runs/{id} (null while loading). */
  config?: Record<string, unknown> | null
  live: LiveRunState
  busy: boolean
  onPause: () => void
  onResume: () => void
  onStop: () => void
  onSpeed: (speed: number | null) => void
}) {
  const { t } = useTranslation()
  const status: RunStatus = live.status ?? run.status
  const isLive = LIVE.has(status)
  const configChips = useMemo(() => runConfigChips(run, config, t), [run, config, t])
  // null speed means "as fast as possible", so only trust the stream once it has reported.
  const speed = live.status != null ? live.speed : run.speed
  const c = live.counters
  const counts = live.devices ? countStates(live.devices.codes) : null
  const replayingView = live.viewTime != null
  const total = c.total ?? run.total_devices
  // While replaying, count from the shown snapshot rather than the final counters.
  const identified = replayingView && counts ? counts[IDENTIFIED_CODE] : (c.identified ?? run.identified_total)
  const pct = total > 0 ? (100 * identified) / total : 0
  // Rounds / depletions up to the replay time (final counters otherwise).
  const upTo = useMemo(() => {
    const vt = live.viewTime
    if (vt == null) return null
    let rounds = 0
    let depletions = 0
    for (const r of live.rounds) {
      if (r.t_start_s > vt) continue
      rounds++
      for (const stage of Object.values(r.deaths ?? {})) for (const v of Object.values(stage)) depletions += v
    }
    return { rounds, depletions }
  }, [live.rounds, live.viewTime])

  // Replay (paused or finished runs): scrub with the slider or play it back.
  const [scrub, setScrub] = useState<number | null>(null)
  const [playing, setPlaying] = useState(false)
  const [replaySpeed, setReplaySpeed] = useState<number | null>(5)
  useEffect(() => {
    setScrub(null)
    setPlaying(false)
  }, [run.run_id, isLive])
  const maxT = Math.max(replayingView ? 0 : live.simTime, run.sim_time_s ?? 0)
  const shownT = scrub ?? live.viewTime ?? maxT
  const shownRef = useRef(shownT)
  useEffect(() => {
    shownRef.current = shownT
  }, [shownT])
  const seek = live.seek

  useEffect(() => {
    if (!playing) return
    const step = (REPLAY_TICK_MS / 1000) * (replaySpeed ?? REPLAY_MAX_SPEED)
    const id = window.setInterval(() => {
      const next = shownRef.current + step
      if (next >= maxT) {
        setPlaying(false)
        void seek(null)
      } else {
        void seek(next)
      }
    }, REPLAY_TICK_MS)
    return () => window.clearInterval(id)
  }, [playing, replaySpeed, maxT, seek])

  function togglePlay() {
    if (playing) {
      setPlaying(false)
      return
    }
    setScrub(null)
    // From the end, start over at t = 0.
    if (live.viewTime == null || live.viewTime >= maxT) void seek(0)
    setPlaying(true)
  }

  return (
    <div className="flex shrink-0 flex-col gap-2 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium" title={`#${run.run_id}`}>
          {runDisplayName(run)}
        </span>
        <StatusChip status={status} />
        {isLive && live.connected ? (
          <span className="inline-flex items-center gap-1 text-[10px] text-blue-600">
            <Radio className="size-3 animate-pulse" />
            {t('thesis.live.streaming')}
          </span>
        ) : null}
        <div className="ml-auto flex items-center gap-1">
          {isLive ? (
            <Button type="button" size="xs" variant="outline" disabled={busy} onClick={onPause}>
              <Pause className="mr-1 size-3" />
              {t('thesis.live.pause')}
            </Button>
          ) : null}
          {status === 'paused' ? (
            <Button type="button" size="xs" disabled={busy} onClick={onResume}>
              <Play className="mr-1 size-3" />
              {t('thesis.live.resume')}
            </Button>
          ) : null}
          {isLive || status === 'paused' ? (
            <Button type="button" size="xs" variant="outline" disabled={busy} onClick={onStop}>
              <Square className="mr-1 size-3" />
              {t('thesis.runsPanel.stop')}
            </Button>
          ) : null}
        </div>
      </div>

      {configChips.length > 0 ? (
        <div className="flex flex-wrap gap-1" aria-label={t('thesis.live.config')}>
          {configChips.map((chip) => (
            <span
              key={chip.key}
              className="rounded-md border bg-muted/50 px-1.5 py-0.5 text-[10px] text-muted-foreground"
              title={chip.title}
            >
              {chip.label}
            </span>
          ))}
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 tabular-nums">
        <span>
          {t('thesis.live.simTime')}: <b>{live.simTime.toFixed(2)} s</b>
        </span>
        <span title={t('thesis.charts.terms.identified')}>
          {t('thesis.live.identified')}: <b>{identified}</b>/{total} ({pct.toFixed(1)}%)
        </span>
        <span title={t('thesis.charts.terms.rounds')}>
          {t('thesis.live.rounds')}: {upTo?.rounds ?? c.rounds ?? run.rounds_total}
        </span>
        <span title={t('thesis.charts.terms.depletions')}>
          {t('thesis.live.depletions')}: {upTo?.depletions ?? c.depletions ?? run.died_count}
        </span>
        <span title={t('thesis.charts.terms.unreachable')}>
          {t('thesis.live.unreachable')}: {c.unreachable ?? run.unreachable_count}
        </span>
        {c.no_progress ? (
          <span title={t('thesis.charts.terms.no_progress')}>
            {t('thesis.live.noProgress')}: {c.no_progress}
          </span>
        ) : null}
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div className="h-full bg-[#77ac30] transition-[width]" style={{ width: `${pct}%` }} />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-muted-foreground">{t('thesis.live.speed')}</span>
        <ToggleGroup
          size="sm"
          variant="outline"
          value={[speedKey(isLive ? speed : replaySpeed)]}
          onValueChange={(v) => {
            const key = v[0]
            if (key == null) return
            const next = key === 'max' ? null : Number(key)
            // Live: simulation pace on the backend. Otherwise: replay pace.
            if (isLive) onSpeed(next)
            else setReplaySpeed(next)
          }}
        >
          {SPEED_OPTIONS.map((s) => (
            <ToggleGroupItem key={speedKey(s)} value={speedKey(s)} className="px-2 text-[11px]">
              {s == null ? t('thesis.live.max') : `${s}×`}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
        {!isLive && maxT > 0 ? (
          <div className="flex min-w-48 flex-1 items-center gap-2">
            <Button
              type="button"
              size="icon-sm"
              variant="outline"
              aria-label={playing ? t('thesis.live.pauseReplay') : t('thesis.live.playReplay')}
              title={playing ? t('thesis.live.pauseReplay') : t('thesis.live.playReplay')}
              onClick={togglePlay}
            >
              {playing ? <Pause /> : <Play />}
            </Button>
            <span className="text-muted-foreground">{t('thesis.live.replay')}</span>
            <Slider
              className="min-w-32 flex-1"
              min={0}
              max={maxT}
              step={0.5}
              value={[shownT]}
              onValueChange={(v) => {
                setPlaying(false)
                setScrub(Array.isArray(v) ? v[0] : v)
              }}
              onValueCommitted={(v) => {
                const tt = Array.isArray(v) ? v[0] : v
                setScrub(null)
                void seek(tt >= maxT ? null : tt)
              }}
            />
            <span className="w-24 text-right tabular-nums">
              {shownT.toFixed(1)} / {maxT.toFixed(1)} s
            </span>
          </div>
        ) : null}
      </div>

      {counts ? (
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-muted-foreground">
          {RUN_STATE_LABELS.map((label, code) =>
            counts[code] ? (
              <span
                key={label}
                className="inline-flex items-center gap-1"
                title={['identified', 'dropped', 'unreachable'].includes(label) ? t(`thesis.charts.terms.${label}`) : undefined}
              >
                <span className="size-2 rounded-full" style={{ background: RUN_STATE_COLOR[label] }} />
                {t(`thesis.live.state.${label}`)} {counts[code]}
              </span>
            ) : null,
          )}
        </div>
      ) : null}
    </div>
  )
}

function speedKey(speed: number | null | undefined): string {
  return speed == null ? 'max' : String(speed)
}

function countStates(codes: Uint8Array): number[] {
  const out = new Array<number>(RUN_STATE_LABELS.length).fill(0)
  for (const c of codes) out[c] = (out[c] ?? 0) + 1
  return out
}

type ConfigChip = { key: string; label: string; title?: string }

/** Compact chips mirroring the New Run dialog fields frozen on the run. */
function runConfigChips(
  run: RunSummary,
  config: Record<string, unknown> | null | undefined,
  t: (key: string, opts?: Record<string, unknown>) => string,
): ConfigChip[] {
  const cfg = config ?? {}
  const bool = (key: string, fallback = false) => {
    const v = cfg[key]
    return typeof v === 'boolean' ? v : fallback
  }
  const num = (key: string): number | null => {
    const v = cfg[key]
    return typeof v === 'number' && Number.isFinite(v) ? v : null
  }

  const scheme = run.scheme
  const adaptive =
    typeof cfg.adaptive_k === 'boolean' ? cfg.adaptive_k : cfg.k_initial == null
  const k0 = num('k_initial')
  const g = num('g')
  const grouping = bool('use_grouping') && scheme === 'periodic'
  const stall = num('stall_timeout_s')
  const seed = num('seed')
  const disabled = Array.isArray(cfg.disabled_reader_ids)
    ? (cfg.disabled_reader_ids as unknown[]).map(Number).filter((n) => Number.isFinite(n))
    : (run.disabled_reader_ids ?? [])
  const startGroups = Array.isArray(cfg.reader_start_groups)
    ? (cfg.reader_start_groups as unknown[])
    : (run.reader_start_groups ?? [])
  const startInterval =
    num('reader_start_interval_s') ??
    (typeof run.reader_start_interval_s === 'number' ? run.reader_start_interval_s : null)

  const chips: ConfigChip[] = [
    {
      key: 'scheme',
      label: t(`thesis.newRun.scheme${scheme === 'periodic' ? 'Periodic' : 'Aperiodic'}`),
    },
  ]

  if (adaptive) {
    chips.push({
      key: 'k',
      label: k0 != null ? t('thesis.live.configAdaptiveK', { k: k0 }) : t('thesis.live.configAdaptiveKDefault'),
      title: t('thesis.newRun.adaptiveKHint'),
    })
  } else {
    chips.push({
      key: 'k',
      label: t('thesis.live.configFixedK', { k: k0 ?? 128 }),
    })
  }

  if (grouping) {
    chips.push({
      key: 'g',
      label: t('thesis.live.configGroups', { g: g ?? 1 }),
      title: t('thesis.newRun.useGroupingHint'),
    })
  } else if (scheme === 'periodic') {
    chips.push({ key: 'g', label: t('thesis.live.configNoGrouping') })
  }

  chips.push({
    key: 'capture',
    label: bool('use_capture', true) ? t('thesis.live.configOn', { name: 'Capture' }) : t('thesis.live.configOff', { name: 'Capture' }),
  })
  chips.push({
    key: 'ebi',
    label: bool('use_ebi', true) ? t('thesis.live.configOn', { name: 'EBI' }) : t('thesis.live.configOff', { name: 'EBI' }),
  })
  chips.push({
    key: 'd2r',
    label: bool('include_d2r', run.include_d2r !== false)
      ? t('thesis.live.configOn', { name: 'D2R' })
      : t('thesis.live.configOff', { name: 'D2R' }),
  })

  if (stall != null && stall > 0) {
    chips.push({ key: 'stall', label: t('thesis.live.configStall', { s: stall }) })
  } else if (cfg.stall_timeout_s === null) {
    chips.push({ key: 'stall', label: t('thesis.live.configStallOff') })
  }

  if (seed != null) chips.push({ key: 'seed', label: t('thesis.live.configSeed', { seed }) })

  if (startGroups.length > 1 && startInterval != null) {
    chips.push({
      key: 'stagger',
      label: t('thesis.live.configStagger', {
        groups: startGroups.length,
        ms: Math.round(startInterval * 1000),
      }),
    })
  }

  if (disabled.length > 0) {
    chips.push({
      key: 'disabled',
      label: t('thesis.live.configDisabledReaders', { count: disabled.length }),
      title: disabled.map((id) => `#${id}`).join(', '),
    })
  }

  return chips
}
