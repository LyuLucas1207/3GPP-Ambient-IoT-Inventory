import { RotateCcw } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { findCatalog } from '@/lib/thesisGeometry'
import { DEVICE_SUBTYPES, deriveReaderRanges } from '@/lib/thesisPhysics'
import type {
  CatalogEntry,
  DerivedRanges,
  DeviceSubtype,
  Kind,
  Params,
  ParamValue,
  Placement,
  PlacementInput,
} from '@/types/thesis'

export function PlacementMenu({
  placement,
  catalog,
  pristineCatalog,
  anchor,
  busy,
  onClose,
  onApply,
  onDelete,
}: {
  placement: Placement
  catalog: CatalogEntry[]
  pristineCatalog: CatalogEntry[]
  anchor: { x: number; y: number }
  busy: boolean
  onClose: () => void
  onApply: (input: PlacementInput) => void
  onDelete: () => void
}) {
  const { t } = useTranslation()
  const kind = placement.kind
  const [subtype, setSubtype] = useState<string | null>(placement.subtype)
  const [x, setX] = useState(String(placement.x_m))
  const [y, setY] = useState(String(placement.y_m))
  const [draft, setDraft] = useState<Record<string, string>>(() => stringifyParams(placement.params))
  const [formError, setFormError] = useState<string | null>(null)
  const sample = findCatalog(catalog, kind, kind === 'device' ? subtype : null)?.defaults ?? placement.params
  const pristine = findCatalog(pristineCatalog, kind, kind === 'device' ? subtype : null)?.defaults ?? sample
  const pos = clampAnchor(anchor.x, anchor.y)

  const deviceDefaults = useMemo(() => catalogDeviceDefaults(catalog), [catalog])
  const derivedRanges = useMemo<DerivedRanges | null>(() => {
    if (kind === 'device') return null
    const rf = draftToRf(draft, sample)
    const includeD2r = kind === 'radar' ? draft.include_d2r !== 'false' : true
    return deriveReaderRanges(rf, deviceDefaults, includeD2r)
  }, [kind, draft, sample, deviceDefaults])

  function convertKind() {
    const next: Kind = kind === 'radar' ? 'station' : 'radar'
    const x_m = Number(x)
    const y_m = Number(y)
    if (!Number.isFinite(x_m) || !Number.isFinite(y_m)) {
      setFormError(t('thesis.errors.bad_param'))
      return
    }
    const nextSample = findCatalog(catalog, next, null)?.defaults ?? sample
    try {
      onApply({ kind: next, subtype: null, x_m, y_m, params: parseParams(draft, nextSample) })
    } catch {
      setFormError(t('thesis.errors.bad_param'))
    }
  }

  function setParam(key: string, value: string) {
    setDraft((prev) => ({ ...prev, [key]: value }))
  }

  function resetParam(key: string) {
    setParam(key, formatDefault(pristine[key]))
  }

  function resetAll() {
    setDraft(stringifyParams(pristine))
  }

  function changeDevice(next: string) {
    const entry = findCatalog(catalog, 'device', next)
    setSubtype(next)
    if (entry) setDraft(stringifyParams(entry.defaults))
  }

  function apply() {
    const x_m = Number(x)
    const y_m = Number(y)
    if (!Number.isFinite(x_m) || !Number.isFinite(y_m)) {
      setFormError(t('thesis.errors.bad_param'))
      return
    }
    try {
      const params = parseParams(draft, sample)
      onApply({ kind, subtype: kind === 'device' ? subtype : null, x_m, y_m, params })
    } catch {
      setFormError(t('thesis.errors.bad_param'))
    }
  }

  const keys = orderedKeys(sample, draft).filter(
    (key) => !(kind !== 'device' && (key === 'show_range' || key === 'show_outer' || key === 'include_d2r')),
  )

  return (
    <>
      <button type="button" className="fixed inset-0 z-40 cursor-default" aria-label={t('thesis.closeMenu')} onClick={onClose} />
      <Card className="fixed z-50 w-96" style={pos} size="sm">
        <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
          <CardTitle>{t(`thesis.kind.${kind}`)}</CardTitle>
          <Button type="button" size="xs" variant="ghost" onClick={resetAll} aria-label={t('thesis.resetAll')}>
            <RotateCcw className="mr-1 size-3" />
            {t('thesis.resetAll')}
          </Button>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-2">
          {kind === 'device' ? (
            <div className="col-span-2 flex gap-1">
              {['1', '2a', '2b'].map((item) => (
                <Button
                  key={item}
                  type="button"
                  size="xs"
                  variant={subtype === item ? 'default' : 'outline'}
                  onClick={() => changeDevice(item)}
                >
                  {t(`thesis.kind.device${item === '1' ? '1' : item}`)}
                </Button>
              ))}
            </div>
          ) : (
            <>
              <label className="col-span-2 flex items-center gap-2 text-sm">
                <Checkbox
                  checked={draft.show_range === 'true'}
                  onCheckedChange={(value) => setParam('show_range', value === true ? 'true' : 'false')}
                />
                {t('thesis.params.show_range')}
              </label>
              <label className="col-span-2 flex items-center gap-2 text-sm">
                <Checkbox
                  checked={draft.show_outer === 'true'}
                  onCheckedChange={(value) => setParam('show_outer', value === true ? 'true' : 'false')}
                />
                {t('thesis.params.show_outer')}
              </label>
              {kind === 'radar' ? (
                <label className="col-span-2 flex items-center gap-2 text-sm">
                  <Checkbox
                    checked={draft.include_d2r !== 'false'}
                    onCheckedChange={(value) => setParam('include_d2r', value === true ? 'true' : 'false')}
                  />
                  {t('thesis.params.include_d2r')}
                </label>
              ) : null}
              <Button type="button" size="sm" variant="outline" className="col-span-2" onClick={convertKind}>
                {kind === 'radar' ? t('thesis.toStation') : t('thesis.toRadar')}
              </Button>
            </>
          )}
          <div className="col-span-2 grid grid-cols-2 gap-2">
            <Field label={t('thesis.x')} value={x} onChange={setX} />
            <Field label={t('thesis.y')} value={y} onChange={setY} />
          </div>
          {keys.map((key) =>
            isBool(sample[key], draft[key]) ? (
              <label key={key} className="col-span-2 flex items-center gap-2 text-sm">
                <Checkbox
                  checked={draft[key] === 'true'}
                  onCheckedChange={(value) => setParam(key, value === true ? 'true' : 'false')}
                />
                <span className="flex-1">
                  {paramLabel(t, key)} <DefaultHint value={pristine[key]} />
                </span>
                <ResetButton onClick={() => resetParam(key)} label={t('thesis.resetToDefault')} />
              </label>
            ) : (
              <FieldWithReset
                key={key}
                label={paramLabel(t, key)}
                defaultValue={pristine[key]}
                value={draft[key] ?? ''}
                onChange={(value) => setParam(key, value)}
                onReset={() => resetParam(key)}
                resetLabel={t('thesis.resetToDefault')}
              />
            ),
          )}
          {derivedRanges ? (
            <section className="col-span-2 rounded-md border border-dashed p-2 text-xs">
              <h4 className="mb-1 font-medium text-muted-foreground">{t('thesis.effectiveRange.title')}</h4>
              <ul className="space-y-0.5">
                {DEVICE_SUBTYPES.map((subtype) => (
                  <li key={subtype} className="flex justify-between tabular-nums">
                    <span>{t(`thesis.effectiveRange.device${subtype}`)}</span>
                    <span>
                      {derivedRanges[subtype as DeviceSubtype].toFixed(2)} {t('thesis.effectiveRange.unit')}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
          {formError ? <p className="col-span-2 text-xs text-destructive">{formError}</p> : null}
          <div className="col-span-2 flex gap-2">
            <Button type="button" size="sm" disabled={busy} onClick={apply}>
              {t('thesis.apply')}
            </Button>
            <Button type="button" size="sm" variant="destructive" disabled={busy} onClick={onDelete}>
              {t('thesis.delete')}
            </Button>
          </div>
        </CardContent>
      </Card>
    </>
  )
}

export function PlaceMenu({
  anchor,
  onClose,
  onPick,
}: {
  anchor: { x: number; y: number }
  onClose: () => void
  onPick: (kind: Kind, subtype: string | null) => void
}) {
  const { t } = useTranslation()
  const pos = clampAnchor(anchor.x, anchor.y)
  const items: Array<{ kind: Kind; subtype: string | null; label: string }> = [
    { kind: 'device', subtype: '1', label: t('thesis.kind.device1') },
    { kind: 'device', subtype: '2a', label: t('thesis.kind.device2a') },
    { kind: 'device', subtype: '2b', label: t('thesis.kind.device2b') },
    { kind: 'station', subtype: null, label: t('thesis.kind.station') },
  ]
  return (
    <>
      <button type="button" className="fixed inset-0 z-40 cursor-default" aria-label={t('thesis.closeMenu')} onClick={onClose} />
      <Card className="fixed z-50 w-52" style={pos} size="sm">
        <CardHeader>
          <CardTitle>{t('thesis.placeHere')}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-1">
          {items.map((item) => (
            <Button key={`${item.kind}-${item.subtype}`} type="button" size="sm" variant="outline" onClick={() => onPick(item.kind, item.subtype)}>
              {item.label}
            </Button>
          ))}
        </CardContent>
      </Card>
    </>
  )
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="text-muted-foreground">{label}</span>
      <Input value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  )
}

function FieldWithReset({
  label,
  defaultValue,
  value,
  onChange,
  onReset,
  resetLabel,
}: {
  label: string
  defaultValue: ParamValue | undefined
  value: string
  onChange: (value: string) => void
  onReset: () => void
  resetLabel: string
}) {
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="flex items-center justify-between text-muted-foreground">
        <span>
          {label} <DefaultHint value={defaultValue} />
        </span>
        <ResetButton onClick={onReset} label={resetLabel} />
      </span>
      <Input value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  )
}

function ResetButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className="rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
    >
      <RotateCcw className="size-3" />
    </button>
  )
}

function DefaultHint({ value }: { value: ParamValue | undefined }) {
  if (value === undefined) return null
  return <span className="text-muted-foreground/80">({formatDefault(value)})</span>
}

function paramLabel(t: (key: string) => string, key: string) {
  const i18nKey = `thesis.params.${key}`
  const translated = t(i18nKey)
  return translated === i18nKey ? key : translated
}

function isBool(sample: ParamValue | undefined, raw: string | undefined) {
  return typeof sample === 'boolean' || raw === 'true' || raw === 'false'
}

function stringifyParams(params: Params) {
  const draft: Record<string, string> = {}
  for (const [key, value] of Object.entries(params)) {
    draft[key] = formatDefault(value)
  }
  return draft
}

function formatDefault(value: ParamValue | undefined): string {
  if (value == null) return ''
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  return String(value)
}

function orderedKeys(sample: Params, draft: Record<string, string>) {
  const extras = Object.keys(draft).filter((key) => !(key in sample))
  return [...Object.keys(sample), ...extras]
}

function parseParams(draft: Record<string, string>, sample: Params): Params {
  const out: Params = {}
  for (const key of orderedKeys(sample, draft)) {
    out[key] = parseValue(draft[key] ?? '', sample[key])
  }
  return out
}

function parseValue(raw: string, sample: ParamValue | undefined): ParamValue {
  if (typeof sample === 'boolean' || raw === 'true' || raw === 'false') return raw === 'true'
  if (typeof sample === 'string') return raw
  if ((sample == null || typeof sample === 'number') && raw.trim() === '') {
    if (sample == null) return null
    throw new Error('bad_param')
  }
  const number = Number(raw)
  if (!Number.isFinite(number)) throw new Error('bad_param')
  return number
}

function draftToRf(draft: Record<string, string>, sample: Params) {
  function num(key: string, fallback: number) {
    const raw = draft[key] ?? ''
    if (raw.trim() === '') {
      const value = sample[key]
      return typeof value === 'number' ? value : fallback
    }
    const parsed = Number(raw)
    return Number.isFinite(parsed) ? parsed : fallback
  }
  return {
    tx_power_dbm: num('tx_power_dbm', 33),
    antenna_gain_dbi: num('antenna_gain_dbi', 6),
    extra_attenuation_db: num('extra_attenuation_db', 0),
    carrier_ghz: num('carrier_ghz', 0.9),
  }
}

function catalogDeviceDefaults(catalog: CatalogEntry[]): Partial<Record<DeviceSubtype, Params>> {
  const out: Partial<Record<DeviceSubtype, Params>> = {}
  for (const subtype of DEVICE_SUBTYPES) {
    const entry = catalog.find((item) => item.kind === 'device' && item.subtype === subtype)
    if (entry) out[subtype] = entry.defaults
  }
  return out
}

function clampAnchor(x: number, y: number) {
  return {
    left: Math.max(8, Math.min(x, window.innerWidth - 384)),
    top: Math.max(8, Math.min(y, window.innerHeight - 480)),
  }
}
