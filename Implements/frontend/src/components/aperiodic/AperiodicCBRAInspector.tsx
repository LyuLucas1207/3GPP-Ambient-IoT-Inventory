import { PaperRef } from '@/components/aperiodic/PaperRef'
import { TimeFrequencyLegend, TimeFrequencyMap } from '@/components/aperiodic/TimeFrequencyMap'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import type { CbraInspectRound } from '@/types/aperiodicSimulation'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

const OBS = ['idle', 'success', 'collision'] as const

function Stat({ label, ms, children }: { label: string; ms: number; children: React.ReactNode }) {
  return (
    <div className="grid min-w-0 gap-0.5 rounded-md border border-border/60 p-1.5">
      <div className="flex items-baseline justify-between gap-2 text-[11px] font-medium">
        <span>{label}</span>
        <span className="font-mono text-[10px] text-muted-foreground">{ms.toFixed(1)} ms</span>
      </div>
      <div className="grid text-[10px] text-muted-foreground">{children}</div>
    </div>
  )
}

export function AperiodicCBRAInspector({ rounds }: { rounds: CbraInspectRound[] }) {
  const { t } = useTranslation()
  const [i, setI] = useState(0)
  const [toScale, setToScale] = useState(false)
  if (!rounds.length) return null
  const r = rounds[Math.min(i, rounds.length - 1)]
  const c = r.components_s
  const wasted = r.k_alloc - r.k_served
  const obsCount = OBS.map((_, k) => r.observed.filter((o) => o === k).length)
  return (
    <Card plain size="sm">
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          {t('ap.cbra.title')} <PaperRef id="tf" />
        </CardTitle>
        <CardDescription>
          {t('ap.cbra.subtitle', { round: r.round, L: r.L, F: r.F, mode: t(r.periodic ? 'ap.terms.periodicBaseline' : 'ap.terms.aperiodic') })}
        </CardDescription>
        <CardAction>
          <label className="flex items-center gap-2 text-xs text-muted-foreground">
            {t('ap.tf.toScale')}
            <Switch checked={toScale} onCheckedChange={setToScale} />
          </label>
        </CardAction>
      </CardHeader>
      <CardContent className="grid gap-3">
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">{t('ap.cbra.round')}</span>
          <Slider
            className="flex-1"
            min={0}
            max={rounds.length - 1}
            value={[Math.min(i, rounds.length - 1)]}
            onValueChange={(v) => setI(Array.isArray(v) ? v[0] : v)}
          />
          <span className="w-10 text-right font-mono text-xs">{r.round}</span>
        </div>
        <TimeFrequencyMap r={r} toScale={toScale} />
        <div className="grid gap-1.5 sm:grid-cols-5">
          <Stat label={t('ap.cbra.paging')} ms={c.paging_s * 1e3}>
            <span>{t('ap.cbra.paged', { n: r.n_paged })}</span>
            <span>{t('ap.cbra.rejected', { n: r.n_rejected })}</span>
          </Stat>
          <Stat label="Msg1" ms={c.msg1_s * 1e3}>
            <span>{t('ap.tf.msg1Grid', { L: r.L, F: r.F, n: r.L * r.F })}</span>
            <span>
              {t('ap.cbra.participants', { n: r.n_participants })} · I={obsCount[0]} S={obsCount[1]} C={obsCount[2]}
            </span>
          </Stat>
          <Stat label={t('ap.cbra.ei')} ms={c.ei_s * 1e3}>
            <span>{t('ap.cbra.eiFlags', { n: r.k_served })}</span>
            <span>{t('ap.cbra.eiNote')}</span>
          </Stat>
          <Stat label="Msg2" ms={c.msg2_s * 1e3}>
            <span>{t('ap.cbra.msg2Slots', { used: r.k_served, alloc: r.k_alloc, decoded: r.k_decoded })}</span>
            <span>{t('ap.tf.msg2Freq')}</span>
          </Stat>
          <Stat label="Msg3" ms={c.msg3_s * 1e3}>
            <span>{t('ap.cbra.identified', { n: r.identified })}</span>
            <span>{t('ap.cbra.msg3Slots', { n: r.msg3_slots.toFixed(r.periodic ? 1 : 0) })} · {t('ap.tf.msg3Freq')}</span>
          </Stat>
        </div>
        <p className="text-[11px] text-muted-foreground">
          {r.periodic ? t('ap.cbra.periodicNote', { wasted: wasted.toFixed(1) }) : t('ap.cbra.aperiodicNote')}
        </p>
        <TimeFrequencyLegend />
      </CardContent>
    </Card>
  )
}
