import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { findCatalog } from '@/lib/thesisGeometry'
import type { CatalogEntry, Kind, Params, ParamValue, Placement, PlacementInput } from '@/types/thesis'

const RANGE_KEYS = new Set(['radius_m', 'show_range'])

export function PlacementMenu({
  placement,
  catalog,
  anchor,
  busy,
  onClose,
  onApply,
  onDelete,
}: {
  placement: Placement
  catalog: CatalogEntry[]
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
  const pos = clampAnchor(anchor.x, anchor.y)

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
      onApply({ kind: next, subtype: null, x_m, y_m, params: parseParams(draft, nextSample, next) })
    } catch {
      setFormError(t('thesis.errors.bad_param'))
    }
  }

  function setParam(key: string, value: string) {
    setDraft((prev) => ({ ...prev, [key]: value }))
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
      const params = parseParams(draft, sample, kind)
      onApply({ kind, subtype: kind === 'device' ? subtype : null, x_m, y_m, params })
    } catch {
      setFormError(t('thesis.errors.bad_param'))
    }
  }

  const keys = orderedKeys(sample, draft).filter((key) => !(kind !== 'device' && RANGE_KEYS.has(key)))

  return (
    <>
      <button type="button" className="fixed inset-0 z-40 cursor-default" aria-label={t('thesis.closeMenu')} onClick={onClose} />
      <Card className="fixed z-50 w-80" style={pos} size="sm">
        <CardHeader>
          <CardTitle>{t(`thesis.kind.${kind}`)}</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-2">
          {kind === 'device' ? (
            <div className="col-span-2 flex gap-1">
              {['1', '2a', '2b'].map((item) => (
                <Button key={item} type="button" size="xs" variant={subtype === item ? 'default' : 'outline'} onClick={() => changeDevice(item)}>
                  {t(`thesis.kind.device${item === '1' ? '1' : item}`)}
                </Button>
              ))}
            </div>
          ) : (
            <>
              <label className="col-span-2 flex items-center gap-2 text-sm">
                <Checkbox
                  checked={draft.show_range === 'true'}
                  onCheckedChange={(value) => {
                    setParam('show_range', value === true ? 'true' : 'false')
                    if (value === true && !draft.radius_m) setParam('radius_m', kind === 'radar' ? '30' : '20')
                  }}
                />
                {t('thesis.params.show_range')}
              </label>
              <Field label={t('thesis.params.radius_m')} value={draft.radius_m ?? (kind === 'radar' ? '30' : '20')} onChange={(value) => setParam('radius_m', value)} />
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="col-span-2"
                onClick={convertKind}
              >
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
                <Checkbox checked={draft[key] === 'true'} onCheckedChange={(value) => setParam(key, value === true ? 'true' : 'false')} />
                {paramLabel(t, key)}
              </label>
            ) : (
              <Field key={key} label={paramLabel(t, key)} value={draft[key] ?? ''} onChange={(value) => setParam(key, value)} />
            ),
          )}
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
    if (typeof value === 'boolean') draft[key] = value ? 'true' : 'false'
    else if (value == null) draft[key] = ''
    else draft[key] = String(value)
  }
  return draft
}

function orderedKeys(sample: Params, draft: Record<string, string>) {
  const extras = Object.keys(draft).filter((key) => !(key in sample))
  return [...Object.keys(sample), ...extras]
}

function parseParams(draft: Record<string, string>, sample: Params, kind: Kind): Params {
  const out: Params = {}
  for (const key of orderedKeys(sample, draft)) {
    out[key] = parseValue(draft[key] ?? '', sample[key])
  }
  if (kind !== 'device') {
    const radius = Number(out.radius_m)
    if (!Number.isFinite(radius) || radius <= 0 || radius > 10_000) throw new Error('bad_radius')
    out.show_range = draft.show_range === 'true'
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

function clampAnchor(x: number, y: number) {
  return {
    left: Math.max(8, Math.min(x, window.innerWidth - 300)),
    top: Math.max(8, Math.min(y, window.innerHeight - 360)),
  }
}
