import { ParamHint } from '@/components/ParamHint'
import { TermHelp } from '@/components/TermHelp'
import { ExplainButton } from '@/components/ViewExplanationDialog'
import { MathInline } from '@/components/MathText'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { TermId, ViewId } from '@/explain/ids'
import { DeviceVizState, type DeviceStats, type Snapshot, type StaticDevice } from '@/types/simulation'
import { useTranslation } from 'react-i18next'
import type { ReactNode } from 'react'

interface Props {
  device: StaticDevice | null
  stats: DeviceStats | null
  snapshot: Snapshot | null
}

function Row({
  label,
  value,
  hint,
  term,
}: {
  label: ReactNode
  value: string
  hint: string
  term?: TermId
}) {
  return (
    <div className="flex items-center justify-between gap-3 py-1 text-sm">
      <span className="flex items-center gap-1.5 text-muted-foreground">
        {label}
        {term ? <TermHelp term={term} /> : <ParamHint text={hint} />}
      </span>
      <span className="font-medium">{value}</span>
    </div>
  )
}

export function DeviceInspector({ device, stats, snapshot }: Props) {
  const { t } = useTranslation()
  if (device == null) {
    return (
      <Card className="bg-card/90 backdrop-blur-md" size="sm">
        <CardHeader>
          <CardTitle>{t('inspect.title')}</CardTitle>
          <CardAction>
            <ExplainButton view={ViewId.Inspector} />
          </CardAction>
          <CardDescription>{t('inspect.empty')}</CardDescription>
        </CardHeader>
      </Card>
    )
  }
  const energy = snapshot?.energy_nj[device.id]
  const state = snapshot?.state[device.id] ?? DeviceVizState.OFF
  return (
    <Card className="bg-card/90 backdrop-blur-md" size="sm">
      <CardHeader>
        <CardTitle>{t('inspect.device', { id: device.id })}</CardTitle>
        <CardAction>
          <ExplainButton view={ViewId.Inspector} />
        </CardAction>
        <CardDescription>{t(`state.${state}`)}</CardDescription>
      </CardHeader>
      <CardContent>
        <Row
          label={<MathInline tex="e_{\mathrm{ES}}" />}
          value={energy == null ? '—' : `${energy.toFixed(1)} / 500 nJ`}
          hint={t('inspect.energyHint')}
          term={TermId.Ees}
        />
        <Separator />
        <Row
          label={<MathInline tex="p_{\mathrm{in}}" />}
          value={`${device.pin_dbm.toFixed(2)} dBm`}
          hint={t('inspect.pinHint')}
          term={TermId.Pin}
        />
        <Row
          label={<MathInline tex="P_{\mathrm{eh}}" />}
          value={`${device.harvest_power_nw.toFixed(2)} nW`}
          hint={t('inspect.pehHint')}
          term={TermId.Peh}
        />
        <Separator />
        <Row
          label={t('inspect.group')}
          value={stats?.group == null ? '—' : String(stats.group)}
          hint={t('inspect.groupHint')}
          term={TermId.Group}
        />
        <Row
          label={t('inspect.attempts')}
          value={String(stats?.attempts ?? 0)}
          hint={t('inspect.attemptsHint')}
        />
        <Row
          label={t('inspect.collisions')}
          value={String(stats?.collisions ?? 0)}
          hint={t('inspect.collisionsHint')}
          term={TermId.Collision}
        />
        <Row
          label={t('inspect.inventoried')}
          value={stats?.inventoried ? t('common.yes') : t('common.no')}
          hint={t('inspect.inventoriedHint')}
        />
        <Row
          label={t('inspect.completion')}
          value={stats?.completion_time_s == null ? '—' : `${stats.completion_time_s.toFixed(3)} s`}
          hint={t('inspect.completionHint')}
        />
        <Row
          label={t('inspect.firstPaging')}
          value={stats?.first_paging_time_s == null ? '—' : `${stats.first_paging_time_s.toFixed(3)} s`}
          hint={t('inspect.firstPagingHint')}
        />
        <Row
          label={t('inspect.lastSync')}
          value={stats?.last_sync_time_s == null ? '—' : `${stats.last_sync_time_s.toFixed(3)} s`}
          hint={t('inspect.lastSyncHint')}
        />
        <Row
          label={t('inspect.syncCount')}
          value={`${stats?.sync_count ?? 0} / ${stats?.lost_sync_count ?? 0}`}
          hint={t('inspect.syncCountHint')}
        />
      </CardContent>
    </Card>
  )
}
