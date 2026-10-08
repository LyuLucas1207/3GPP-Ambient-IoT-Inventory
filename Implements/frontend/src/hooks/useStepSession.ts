import { useCallback, useEffect, useRef, useState } from 'react'
import { createStepSession, deleteStepSession, nextStepRound } from '@/api/aperiodicSimulator'
import { STEP_PHASES } from '@/components/aperiodic/step/stepModel'
import type { AperiodicSimulateRequest, StepRound, StepSessionInfo } from '@/types/aperiodicSimulation'

const LAST = STEP_PHASES.length - 1

/** Client of one backend step session; keeps every fetched round so Prev can go back. */
export function useStepSession() {
  const [info, setInfo] = useState<StepSessionInfo | null>(null)
  const [rounds, setRounds] = useState<StepRound[]>([])
  const [roundIdx, setRoundIdx] = useState(-1)
  const [phase, setPhase] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [finished, setFinished] = useState(false)
  const [skipEmpty, setSkipEmpty] = useState(true)
  const sid = useRef<string | null>(null)

  const close = useCallback(() => {
    if (sid.current) deleteStepSession(sid.current)
    sid.current = null
  }, [])

  useEffect(() => close, [close])

  const start = useCallback(
    async (config: AperiodicSimulateRequest, nDevices: number) => {
      close()
      setBusy(true)
      setError(null)
      setRounds([])
      setRoundIdx(-1)
      setPhase(0)
      setFinished(false)
      try {
        const s = await createStepSession({ ...config, runtime_mode: 'interactive', num_episodes: 1 }, nDevices)
        sid.current = s.session_id
        setInfo(s)
      } catch (e) {
        setInfo(null)
        setError(e instanceof Error ? e.message : String(e))
      } finally {
        setBusy(false)
      }
    },
    [close],
  )

  const fetchRound = useCallback(async (): Promise<boolean> => {
    if (!sid.current || finished) return false
    setBusy(true)
    setError(null)
    try {
      const r = await nextStepRound(sid.current, skipEmpty)
      if (!('round' in r)) {
        setFinished(true)
        setInfo((cur) => (cur ? { ...cur, now: r.now } : cur))
        return false
      }
      setRounds((rs) => [...rs, r])
      setRoundIdx((i) => i + 1)
      setPhase(0)
      if (r.finished) setFinished(true)
      return true
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      return false
    } finally {
      setBusy(false)
    }
  }, [finished, skipEmpty])

  const nextRound = useCallback(async () => {
    if (roundIdx < rounds.length - 1) {
      setRoundIdx(roundIdx + 1)
      setPhase(0)
      return true
    }
    return fetchRound()
  }, [fetchRound, roundIdx, rounds.length])

  const next = useCallback(async () => {
    if (roundIdx >= 0 && phase < LAST) {
      setPhase(phase + 1)
      return true
    }
    return nextRound()
  }, [nextRound, phase, roundIdx])

  const prev = useCallback(() => {
    if (phase > 0) setPhase(phase - 1)
    else if (roundIdx > 0) {
      setRoundIdx(roundIdx - 1)
      setPhase(LAST)
    }
  }, [phase, roundIdx])

  const round = roundIdx >= 0 ? rounds[roundIdx] : null
  const canNext = !busy && !!info && !(finished && roundIdx === rounds.length - 1 && phase === LAST)
  const canPrev = phase > 0 || roundIdx > 0

  return {
    info,
    rounds,
    round,
    roundIdx,
    phase,
    setPhase,
    busy,
    error,
    finished,
    skipEmpty,
    setSkipEmpty,
    start,
    next,
    prev,
    nextRound,
    canNext,
    canPrev,
    close,
  }
}

export type StepSessionApi = ReturnType<typeof useStepSession>
