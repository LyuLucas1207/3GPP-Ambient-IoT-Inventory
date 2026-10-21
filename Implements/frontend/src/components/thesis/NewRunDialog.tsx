import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Dialog, DialogBackdrop, DialogDescription, DialogPopup, DialogPortal, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { RunCreateInput, RunScheme } from '@/types/thesis'

export function NewRunDialog({
  open,
  busy,
  onClose,
  onCreate,
}: {
  open: boolean
  busy: boolean
  onClose: () => void
  onCreate: (config: RunCreateInput) => Promise<void> | void
}) {
  const { t } = useTranslation()
  const [scheme, setScheme] = useState<RunScheme>('periodic')
  const [maxTime, setMaxTime] = useState('10')
  const [kInitial, setKInitial] = useState('128')
  const [g, setG] = useState('1')
  const [useGrouping, setUseGrouping] = useState(false)
  const [useCapture, setUseCapture] = useState(true)
  const [useEbi, setUseEbi] = useState(true)
  const [includeD2r, setIncludeD2r] = useState(true)
  const [seed, setSeed] = useState('')

  async function submit() {
    const config: RunCreateInput = {
      scheme,
      max_time_s: Math.max(0.1, Number(maxTime) || 60),
      k_initial: Number(kInitial) || null,
      g: Number(g) || null,
      use_grouping: useGrouping,
      use_capture: useCapture,
      use_ebi: useEbi,
      include_d2r: includeD2r,
      seed: seed === '' ? null : Number(seed),
    }
    await onCreate(config)
  }

  return (
    <Dialog open={open} onOpenChange={(next) => { if (!next) onClose() }}>
      <DialogPortal>
        <DialogBackdrop />
        <DialogPopup className="w-[min(520px,calc(100vw-32px))] gap-3 p-4">
          <DialogTitle>{t('thesis.newRun.title')}</DialogTitle>
          <DialogDescription>{t('thesis.newRun.hint')}</DialogDescription>
          <div className="grid grid-cols-2 gap-3">
            <label className="col-span-2 flex flex-col gap-1 text-xs">
              <span className="text-muted-foreground">{t('thesis.newRun.scheme')}</span>
              <Select
                value={scheme}
                items={{ periodic: t('thesis.newRun.schemePeriodic'), aperiodic: t('thesis.newRun.schemeAperiodic') }}
                onValueChange={(v) => setScheme((v ?? 'periodic') as RunScheme)}
              >
                <SelectTrigger className="h-8 w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent align="start">
                  <SelectItem value="periodic">{t('thesis.newRun.schemePeriodic')}</SelectItem>
                  <SelectItem value="aperiodic">{t('thesis.newRun.schemeAperiodic')}</SelectItem>
                </SelectContent>
              </Select>
            </label>
            <label className="flex flex-col gap-1 text-xs">
              <span className="text-muted-foreground">{t('thesis.newRun.maxTime')}</span>
              <Input value={maxTime} onChange={(e) => setMaxTime(e.target.value)} />
            </label>
            <label className="flex flex-col gap-1 text-xs">
              <span className="text-muted-foreground">{t('thesis.newRun.k')}</span>
              <Input value={kInitial} onChange={(e) => setKInitial(e.target.value)} />
            </label>
            <label className="flex flex-col gap-1 text-xs">
              <span className="text-muted-foreground">{t('thesis.newRun.g')}</span>
              <Input value={g} onChange={(e) => setG(e.target.value)} />
            </label>
            <label className="flex flex-col gap-1 text-xs">
              <span className="text-muted-foreground">{t('thesis.newRun.seed')}</span>
              <Input value={seed} onChange={(e) => setSeed(e.target.value)} placeholder="auto" />
            </label>
            <label className="col-span-2 flex items-center gap-2 text-sm">
              <Checkbox checked={useGrouping} onCheckedChange={(v) => setUseGrouping(v === true)} />
              {t('thesis.newRun.useGrouping')}
            </label>
            <label className="col-span-2 flex items-center gap-2 text-sm">
              <Checkbox checked={useCapture} onCheckedChange={(v) => setUseCapture(v === true)} />
              {t('thesis.newRun.useCapture')}
            </label>
            <label className="col-span-2 flex items-center gap-2 text-sm">
              <Checkbox checked={useEbi} onCheckedChange={(v) => setUseEbi(v === true)} />
              {t('thesis.newRun.useEbi')}
            </label>
            <label className="col-span-2 flex items-center gap-2 text-sm">
              <Checkbox checked={includeD2r} onCheckedChange={(v) => setIncludeD2r(v === true)} />
              {t('thesis.newRun.includeD2r')}
            </label>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" disabled={busy} onClick={onClose}>
              {t('thesis.newRun.cancel')}
            </Button>
            <Button type="button" disabled={busy} onClick={() => void submit()}>
              {t('thesis.newRun.start')}
            </Button>
          </div>
        </DialogPopup>
      </DialogPortal>
    </Dialog>
  )
}
