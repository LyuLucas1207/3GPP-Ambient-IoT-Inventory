import { ParamHint } from '@/components/ParamHint'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { MathText } from '@/components/MathText'
import { DeviceType } from '@/types/simulation'
import { useTranslation } from 'react-i18next'

interface Props {
  deviceType: DeviceType
}

export function DeviceAnatomy({ deviceType }: Props) {
  const { t } = useTranslation()
  const wurActive = deviceType === DeviceType.Device2

  return (
    <Card className="bg-card/90 backdrop-blur-md" size="sm">
      <CardHeader>
        <CardTitle>{t('anatomy.title')}</CardTitle>
        <CardDescription>{t('anatomy.subtitle')}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="rounded-lg border border-border bg-muted/30 p-3">
          <p className="mb-2 text-[10px] tracking-[0.16em] text-muted-foreground uppercase">
            {t('anatomy.device')}
          </p>
          <Antenna />
          <Block
            kicker="WUR"
            title={t('anatomy.wur')}
            role={t('anatomy.wurRole')}
            hint={t('anatomy.wurHint')}
            dimmed={!wurActive}
            badge={wurActive ? t('anatomy.inUse') : t('anatomy.notThisFig')}
          />
          <WakeArrow label={t('anatomy.wake')} />
          <Block
            kicker="IC"
            title={t('anatomy.ic')}
            role={t('anatomy.icRole')}
            hint={t('anatomy.icHint')}
            dimmed={false}
            badge={t('anatomy.inUse')}
          />
        </div>
        <p className="mt-2 text-xs leading-5 text-muted-foreground">
          <MathText text={wurActive ? t('anatomy.d2Note') : t('anatomy.d1Note')} />
        </p>
      </CardContent>
    </Card>
  )
}

function Antenna() {
  return (
    <svg viewBox="0 0 200 18" className="mb-2 h-4 w-full text-muted-foreground" aria-hidden>
      <path
        d="M20 16 C40 2 70 2 100 16 C130 2 160 2 180 16"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
      />
      <circle cx="100" cy="16" r="1.8" fill="currentColor" />
    </svg>
  )
}

function WakeArrow({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 py-1.5 pl-3">
      <span className="flex w-4 flex-col items-center" aria-hidden>
        <i className="h-3 w-px bg-border" />
        <i className="size-0 border-x-4 border-t-[6px] border-x-transparent border-t-border" />
      </span>
      <span className="text-[10px] tracking-[0.14em] text-muted-foreground uppercase">{label}</span>
    </div>
  )
}

function Block({
  kicker,
  title,
  role,
  hint,
  dimmed,
  badge,
}: {
  kicker: string
  title: string
  role: string
  hint: string
  dimmed: boolean
  badge: string
}) {
  return (
    <div
      className={
        dimmed
          ? 'rounded-md border border-dashed border-border bg-background/40 px-2.5 py-2 opacity-70'
          : 'rounded-md border border-border bg-background/80 px-2.5 py-2'
      }
    >
      <div className="flex items-start justify-between gap-2">
        <p className="font-mono text-[10px] tracking-[0.14em] text-muted-foreground uppercase">{kicker}</p>
        <Badge variant={dimmed ? 'outline' : 'secondary'}>{badge}</Badge>
      </div>
      <p className="mt-1 flex items-start gap-1.5 text-sm font-medium leading-5">
        {title}
        <ParamHint text={hint} />
      </p>
      <p className="mt-0.5 text-xs text-muted-foreground">
        <MathText text={role} />
      </p>
    </div>
  )
}
