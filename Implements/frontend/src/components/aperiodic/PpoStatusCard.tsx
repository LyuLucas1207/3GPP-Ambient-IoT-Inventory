import { Badge } from '@/components/ui/badge'
import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { PpoStatus } from '@/types/aperiodicSimulation'
import { useTranslation } from 'react-i18next'

export function PpoStatusCard({ ppo }: { ppo: PpoStatus | null }) {
  const { t } = useTranslation()
  const ok = ppo?.available === true
  const partial = ok && ppo.fully_trained === false
  return (
    <Card plain size="sm">
      <CardHeader>
        <CardTitle>{t('ap.ppo.title')}</CardTitle>
        <CardAction>
          <Badge variant={ok ? (partial ? 'secondary' : 'default') : 'destructive'}>
            {ok ? (partial ? t('ap.ppo.smoke') : t('ap.ppo.ready')) : t('ap.ppo.unavailable')}
          </Badge>
        </CardAction>
      </CardHeader>
      <CardContent className="grid gap-1 text-xs">
        {ok ? (
          <>
            <Row k={t('ap.ppo.steps')} v={`${ppo.training_steps?.toLocaleString()} / ${ppo.paper_training_steps?.toLocaleString() ?? '1,000,000'}`} />
            <Row k={t('ap.ppo.arch')} v={ppo.architecture ?? '—'} />
            <Row k={t('ap.ppo.scenario')} v={ppo.trained_scenario ?? '—'} />
            <Row k="α" v={ppo.alphas.join(', ')} />
            <Row k="seed" v={String(ppo.seed ?? '—')} />
            <Row k="sha256" v={(ppo.sha256 ?? '').slice(0, 16) + '…'} />
            {partial && <p className="mt-1 text-amber-700 dark:text-amber-300">{t('ap.ppo.smokeNote')}</p>}
          </>
        ) : (
          <p className="text-muted-foreground">{ppo?.reason ?? t('ap.ppo.missing')}</p>
        )}
        <p className="mt-1 text-muted-foreground">
          {t('ap.ppo.trainWith')} <code className="font-mono break-all">{ppo?.train_command}</code>
        </p>
      </CardContent>
    </Card>
  )
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-2">
      <span className="text-muted-foreground">{k}</span>
      <span className="truncate text-right font-mono" title={v}>{v}</span>
    </div>
  )
}
