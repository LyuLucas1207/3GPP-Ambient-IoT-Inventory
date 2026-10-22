import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Dialog, DialogBackdrop, DialogDescription, DialogPopup, DialogPortal, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { SPEED_OPTIONS } from '@/lib/thesisRunStates'
import type { RunCreateInput, RunScheme } from '@/types/thesis'

export function NewRunDialog({
  open,
  busy,
  readers,
  onClose,
  onCreate,
}: {
  open: boolean
  busy: boolean
  readers: { id: number; label: string }[]
  onClose: () => void
  onCreate: (config: RunCreateInput) => Promise<void> | void
}) {
  const { t } = useTranslation()
  const [scheme, setScheme] = useState<RunScheme>('periodic')
  const [speed, setSpeed] = useState('1')
  const [stallTimeout, setStallTimeout] = useState('300')
  const [kInitial, setKInitial] = useState('128')
  const [g, setG] = useState('1')
  const [useGrouping, setUseGrouping] = useState(false)
  const [useCapture, setUseCapture] = useState(true)
  const [useEbi, setUseEbi] = useState(true)
  const [includeD2r, setIncludeD2r] = useState(true)
  const [seed, setSeed] = useState('')
  const [disabledReaders, setDisabledReaders] = useState<Set<number>>(new Set())

  async function submit() {
    const config: RunCreateInput = {
      scheme,
      // Interactive runs have no time cap: they end when every reachable device is
      // identified, on the stall guard, or when the user pauses / stops them.
      max_time_s: null,
      speed: speed === 'max' ? null : Number(speed),
      stall_timeout_s: positiveOrNull(stallTimeout),
      k_initial: Number(kInitial) || null,
      g: Number(g) || null,
      use_grouping: useGrouping,
      use_capture: useCapture,
      use_ebi: useEbi,
      include_d2r: includeD2r,
      seed: seed === '' ? null : Number(seed),
      disabled_reader_ids: Array.from(disabledReaders),
    }
    await onCreate(config)
  }

  function toggleReader(id: number) {
    setDisabledReaders((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
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
              <span className="text-muted-foreground">{t('thesis.newRun.stallTimeout')}</span>
              <Input value={stallTimeout} onChange={(e) => setStallTimeout(e.target.value)} placeholder={t('thesis.newRun.off')} />
            </label>
            <label className="flex flex-col gap-1 text-xs">
              <span className="text-muted-foreground">{t('thesis.live.speed')}</span>
              <Select
                value={speed}
                items={Object.fromEntries(SPEED_OPTIONS.map((v) => [v == null ? 'max' : String(v), v == null ? t('thesis.live.max') : `${v}×`]))}
                onValueChange={(v) => setSpeed(String(v ?? '1'))}
              >
                <SelectTrigger className="h-8 w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent align="start">
                  {SPEED_OPTIONS.map((v) => (
                    <SelectItem key={String(v)} value={v == null ? 'max' : String(v)}>
                      {v == null ? t('thesis.live.max') : `${v}×`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </label>
            <p className="col-span-2 -mt-1 text-[11px] text-muted-foreground">{t('thesis.newRun.endHint')}</p>
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
            {readers.length > 0 ? (
              <fieldset className="col-span-2 flex flex-col gap-1 rounded-md border p-2 text-xs">
                <legend className="px-1 text-muted-foreground">{t('thesis.newRun.disableReaders')}</legend>
                <p className="text-muted-foreground">{t('thesis.newRun.disableReadersHint')}</p>
                <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
                  {readers.map((r) => (
                    <label key={r.id} className="flex items-center gap-1">
                      <Checkbox
                        checked={disabledReaders.has(r.id)}
                        onCheckedChange={() => toggleReader(r.id)}
                      />
                      <span>{r.label}</span>
                    </label>
                  ))}
                </div>
                {disabledReaders.size === readers.length ? (
                  <p className="text-destructive">{t('thesis.newRun.allReadersDisabledWarning')}</p>
                ) : null}
              </fieldset>
            ) : null}
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

function positiveOrNull(raw: string): number | null {
  const n = Number(raw)
  return raw.trim() === '' || !Number.isFinite(n) || n <= 0 ? null : n
}
