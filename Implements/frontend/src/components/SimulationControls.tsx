import { FieldLabel, ParamHint } from '@/components/ParamHint'
import { TermHelp } from '@/components/TermHelp'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { DicesIcon } from 'lucide-react'
import { Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { DeviceType, StrategyKey, type SimulateRequest } from '@/types/simulation'
import { TermId } from '@/explain/ids'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

const STRATEGY_HINT: Record<StrategyKey, string> = {
  [StrategyKey.EM]: 'hints.em',
  [StrategyKey.DCM_1_GROUP]: 'hints.dcm1',
  [StrategyKey.DCM_4_GROUP]: 'hints.dcm4',
}

const STRATEGY_LABEL: Record<StrategyKey, string> = {
  [StrategyKey.EM]: 'strategy.em',
  [StrategyKey.DCM_1_GROUP]: 'strategy.dcm_1_group',
  [StrategyKey.DCM_4_GROUP]: 'strategy.dcm_4_group',
}

function parseSleepNetMinNw(raw: string): number | null | undefined {
  const s = raw.trim().replace(/−/g, '-').replace(/∞/g, 'inf').toLowerCase()
  if (s === '' || s === '-inf' || s === '-infinity') return null
  if (s === '-' || s === '.' || s === '-.') return undefined
  const n = Number(s)
  if (!Number.isFinite(n)) return undefined
  return n
}

interface Props {
  request: SimulateRequest
  setRequest: (next: SimulateRequest) => void
  busy: boolean
  backendUp: boolean | null
  onRun: () => void
  onPaper: () => void
}

export function SimulationControls({
  request,
  setRequest,
  busy,
  backendUp,
  onRun,
  onPaper,
}: Props) {
  const { t } = useTranslation()
  const patch = (partial: Partial<SimulateRequest>) => setRequest({ ...request, ...partial })
  const [sleepMinDraft, setSleepMinDraft] = useState(
    request.sleep_net_power_min_nw == null ? '' : String(request.sleep_net_power_min_nw),
  )
  useEffect(() => {
    setSleepMinDraft(
      request.sleep_net_power_min_nw == null ? '' : String(request.sleep_net_power_min_nw),
    )
  }, [request.sleep_net_power_min_nw])

  const toggle = (id: StrategyKey) => {
    const has = request.strategies.includes(id)
    const next = has ? request.strategies.filter((s) => s !== id) : [...request.strategies, id]
    patch({ strategies: next.length ? next : [id] })
  }

  const apiLabel =
    backendUp == null ? t('common.checking') : backendUp ? t('common.apiUp') : t('common.apiDown')

  return (
    <Card className="bg-card/90 backdrop-blur-md" size="sm">
      <CardHeader>
        <CardTitle>{t('sim.title')}</CardTitle>
        <CardAction>
          <Badge variant={backendUp ? 'default' : 'destructive'}>{apiLabel}</Badge>
        </CardAction>
        <CardDescription>{t('sim.description')}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        <div className="grid gap-1.5">
          <FieldLabel htmlFor="n-devices" hint={t('hints.numDevices')}>
            {t('sim.numDevices')}
          </FieldLabel>
          <Input
            id="n-devices"
            type="number"
            min={1}
            max={2000}
            value={request.num_devices}
            onChange={(e) => patch({ num_devices: Number(e.target.value) })}
          />
        </div>
        <div className="grid gap-1.5">
          <FieldLabel htmlFor="device-type" hint={t('hints.deviceType')}>
            {t('sim.deviceType')}
          </FieldLabel>
          <Select
            value={String(request.device_type)}
            items={{
              [String(DeviceType.Device1)]: t('sim.device1'),
              [String(DeviceType.Device2)]: t('sim.device2'),
            }}
            onValueChange={(v) => {
              if (v === String(DeviceType.Device1)) patch({ device_type: DeviceType.Device1 })
              if (v === String(DeviceType.Device2)) patch({ device_type: DeviceType.Device2 })
            }}
          >
            <SelectTrigger id="device-type" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent alignItemWithTrigger className="z-[80]">
              <SelectItem value={String(DeviceType.Device1)}>{t('sim.device1')}</SelectItem>
              <SelectItem value={String(DeviceType.Device2)}>{t('sim.device2')}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <fieldset className="grid gap-2">
          <legend className="flex items-center gap-1.5 text-sm font-medium">
            {t('sim.strategies')}
            <ParamHint text={t('hints.strategies')} />
          </legend>
          {Object.values(StrategyKey).map((id) => (
            <label key={id} className="flex items-center gap-2 text-sm font-normal">
              <Checkbox
                checked={request.strategies.includes(id)}
                onCheckedChange={() => toggle(id)}
              />
              <span className="flex flex-1 items-center gap-1">
                {t(STRATEGY_LABEL[id])}
                {id === StrategyKey.EM ? <TermHelp term={TermId.Em} /> : <TermHelp term={TermId.Dcm} />}
              </span>
              <ParamHint text={t(STRATEGY_HINT[id])} />
            </label>
          ))}
        </fieldset>
        <label className="flex items-start gap-2 text-sm font-normal">
          <Checkbox
            id="early-sleep"
            className="mt-0.5"
            checked={request.sleep_when_not_attempting}
            onCheckedChange={(v) => patch({ sleep_when_not_attempting: v === true })}
          />
          <span className="flex flex-1 items-center gap-1">
            {t('sim.earlySleep')}
            <ParamHint text={t('hints.earlySleep')} />
          </span>
        </label>
        <div className="grid gap-1.5">
          <FieldLabel htmlFor="sleep-net-min" hint={t('hints.sleepNetMin')}>
            {t('sim.sleepNetMin')}
          </FieldLabel>
          <Input
            id="sleep-net-min"
            type="text"
            inputMode="decimal"
            autoComplete="off"
            placeholder={t('sim.sleepNetMinPlaceholder')}
            value={sleepMinDraft}
            onChange={(e) => {
              const raw = e.target.value
              setSleepMinDraft(raw)
              const parsed = parseSleepNetMinNw(raw)
              if (parsed === undefined) return
              patch({ sleep_net_power_min_nw: parsed })
            }}
            onBlur={() => {
              const parsed = parseSleepNetMinNw(sleepMinDraft)
              if (parsed === undefined) {
                setSleepMinDraft(
                  request.sleep_net_power_min_nw == null
                    ? ''
                    : String(request.sleep_net_power_min_nw),
                )
                return
              }
              patch({ sleep_net_power_min_nw: parsed })
              setSleepMinDraft(parsed == null ? '' : String(parsed))
            }}
          />
        </div>
        <div className="grid gap-1.5">
          <FieldLabel htmlFor="seed" hint={t('hints.seed')}>
            {t('sim.seed')}
          </FieldLabel>
          <div className="flex gap-2">
            <Input
              id="seed"
              type="number"
              min={0}
              value={request.seed}
              onChange={(e) => patch({ seed: Number(e.target.value) })}
            />
            <Button
              type="button"
              variant="outline"
              size="icon"
              disabled={busy}
              title={t('sim.reshuffleSeed')}
              aria-label={t('sim.reshuffleSeed')}
              onClick={() => patch({ seed: Math.floor(Math.random() * 1_000_000_000) })}
            >
              <DicesIcon />
            </Button>
          </div>
        </div>
        <div className="grid gap-1.5">
          <FieldLabel htmlFor="max-t" hint={t('hints.maxTime')}>
            {t('sim.maxTime')}
          </FieldLabel>
          <Input
            id="max-t"
            type="number"
            min={1}
            max={60}
            value={request.max_time_s}
            onChange={(e) => patch({ max_time_s: Number(e.target.value) })}
          />
        </div>
      </CardContent>
      <CardFooter className="flex flex-col gap-2">
        <Button className="w-full" disabled={busy} onClick={onRun}>
          {busy ? t('common.running') : t('sim.run')}
        </Button>
        <Button className="w-full" variant="outline" disabled={busy} onClick={onPaper}>
          {t('sim.paper')}
        </Button>
      </CardFooter>
    </Card>
  )
}
