import { PauseIcon, PlayIcon, RotateCcwIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { PaperRef } from '@/components/aperiodic/PaperRef'
import { Segmented } from '@/components/aperiodic/Segmented'
import { TimeFrequencyMap } from '@/components/aperiodic/TimeFrequencyMap'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Slider } from '@/components/ui/slider'
import type { AperiodicPlayback } from '@/hooks/useAperiodicPlayback'
import type { AperiodicSimulationResult } from '@/types/aperiodicSimulation'

const SPEEDS = [1, 2, 4, 8]

export function PlaybackControls({ pb, result, busy }: { pb: AperiodicPlayback; result: AperiodicSimulationResult | null; busy: boolean }) {
  const { t } = useTranslation()
  return (
    <Card plain size="sm">
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          {t('ap.stage.title')} <PaperRef id="factory" />
        </CardTitle>
        <CardDescription>
          {pb.interactive
            ? t('ap.stage.subtitle', { n: result?.devices?.length ?? 0, neff: result?.metrics.n_eff ?? 0 })
            : result
              ? t('ap.stage.batchNote')
              : busy
                ? t('ap.common.running')
                : t('ap.stage.empty')}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          size="icon"
          disabled={!pb.interactive}
          aria-label={pb.playing ? t('ap.stage.pause') : t('ap.stage.play')}
          onClick={pb.togglePlay}
        >
          {pb.playing ? <PauseIcon /> : <PlayIcon />}
        </Button>
        <Button variant="ghost" size="icon" disabled={!pb.interactive} aria-label={t('ap.stage.restart')} onClick={pb.restart}>
          <RotateCcwIcon />
        </Button>
        <Slider
          className="min-w-32 flex-1"
          min={0}
          max={Math.max(1, pb.frames - 1)}
          disabled={pb.frames < 2}
          value={[pb.idx]}
          onValueChange={(v) => {
            const n = Array.isArray(v) ? v[0] : v
            if (typeof n === 'number') pb.seek(n)
          }}
        />
        <Segmented value={pb.speed} onChange={pb.setSpeed} options={SPEEDS.map((s) => ({ value: s, label: `${s}×` }))} />
      </CardContent>
    </Card>
  )
}

export function CurrentRoundCard({ pb }: { pb: AperiodicPlayback }) {
  const { t } = useTranslation()
  const { row, inspect } = pb
  return (
    <Card plain size="sm">
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          {t('ap.stage.currentRound')} <PaperRef id="tf" />
        </CardTitle>
        <CardDescription>{t('ap.stage.currentRoundHint', { t: pb.time.toFixed(1) })}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-2">
        {!row ? (
          <p className="text-xs text-muted-foreground">{t('ap.stage.noRoundYet')}</p>
        ) : (
          <>
            <div className="flex flex-wrap gap-1.5 text-[11px]">
              <Badge variant="secondary">{t('ap.stage.round', { r: row.round })}</Badge>
              <Badge variant="outline">L = {row.L}</Badge>
              <Badge variant="outline">p = {row.p.toFixed(3)}</Badge>
              <Badge variant="outline">S = {row.S ?? (row.S1 ?? 0) + (row.S2a ?? 0) + (row.S2b ?? 0)}</Badge>
              <Badge variant="outline">I = {row.idle}</Badge>
              <Badge variant="outline">C = {row.collision}</Badge>
              <Badge variant="outline">{t('ap.stage.roundLen', { ms: ((row.t_end_s - row.t_start_s) * 1e3).toFixed(0) })}</Badge>
            </div>
            {inspect && (
              <div className="grid gap-1">
                <p className="text-[10px] text-muted-foreground">
                  {inspect.round === row.round ? t('ap.stage.mapNow') : t('ap.stage.mapNearest', { r: inspect.round })}
                </p>
                <TimeFrequencyMap r={inspect} compact />
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
