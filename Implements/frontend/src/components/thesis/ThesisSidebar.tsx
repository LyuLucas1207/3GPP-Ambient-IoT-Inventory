import { PanelLeftClose, PanelLeftOpen, Plus, Trash2 } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { ShapeGlyph } from '@/components/thesis/MarkerShape'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  Dialog,
  DialogBackdrop,
  DialogDescription,
  DialogPopup,
  DialogPortal,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Slider } from '@/components/ui/slider'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  DEFAULT_HEIGHT_M,
  DEFAULT_WIDTH_M,
} from '@/lib/thesisGeometry'
import type { CatalogEntry, DeviceMix, ParamValue, Scene, SectionSummary } from '@/types/thesis'

export function ThesisSidebar({
  catalog,
  sections,
  scene,
  busy,
  onCreate,
  onOpen,
  onDelete,
  onApplySize,
  onMarkerScale,
  onAddDevices,
  onAddStations,
  onAddStationGrid,
  onClearDevices,
  onClearInfra,
  onCatalogValue,
  onApplyKind,
  selecting,
  pickedCount,
  onToggleSelecting,
  onPickEvery,
  onConvert,
  onClearPicked,
  onLeaveSelect,
}: {
  catalog: CatalogEntry[]
  sections: SectionSummary[]
  scene: Scene | null
  busy: boolean
  onCreate: (name: string) => Promise<boolean>
  onOpen: (id: number) => void
  onDelete: (id: number) => Promise<void>
  onApplySize: (width: number, height: number) => void
  onMarkerScale: (scale: number) => void
  onAddDevices: (count: number, mix: DeviceMix) => void
  onAddStations: (count: number) => void
  onAddStationGrid: (spacingX: number, spacingY: number) => void
  onClearDevices: () => void
  onClearInfra: () => void
  onCatalogValue: (kind: CatalogEntry['kind'], subtype: string | null, key: string, value: CatalogEntry['defaults'][string]) => void
  onApplyKind: (kind: CatalogEntry['kind'], subtype: string | null, params: CatalogEntry['defaults']) => void
  selecting: boolean
  pickedCount: number
  onToggleSelecting: () => void
  onPickEvery: (gapX: number, gapY: number) => void
  onConvert: (kind: 'station' | 'radar') => void
  onClearPicked: () => void
  onLeaveSelect: () => void
}) {
  const { t } = useTranslation()
  const locked = !scene || scene.status === 'initialized'
  const deviceCount = scene?.placements.filter((item) => item.kind === 'device').length ?? 0
  const stationOnly = scene?.placements.filter((item) => item.kind === 'station').length ?? 0
  const readerCount = scene?.placements.filter((item) => item.kind === 'radar').length ?? 0
  const [deviceMix, setDeviceMix] = useState<DeviceMix>('mixed')
  const [pendingDelete, setPendingDelete] = useState<SectionSummary | null>(null)
  const [pendingClear, setPendingClear] = useState<'device' | 'infra' | null>(null)
  const [open, setOpen] = useState(true)

  return (
    <div className={`relative h-full shrink-0 ${open ? 'w-80 max-w-[40vw]' : 'w-0'}`}>
      <aside className={`flex h-full flex-col overflow-hidden bg-card ${open ? 'w-full border-r' : 'hidden'}`}>
      {open ? (
      <Tabs
        defaultValue="section"
        className="min-h-0 w-full flex-1 flex-col gap-0"
        onValueChange={(value) => {
          if (value !== 'warehouse') onLeaveSelect()
        }}
      >
        <TabsList className="mx-3 mt-3 grid h-9 w-[calc(100%-1.5rem)] shrink-0 grid-cols-3">
          <TabsTrigger value="section" className="min-w-0 px-1 text-xs">{t('thesis.tabs.section')}</TabsTrigger>
          <TabsTrigger value="warehouse" className="min-w-0 px-1 text-xs">{t('thesis.tabs.warehouse')}</TabsTrigger>
          <TabsTrigger value="catalog" className="min-w-0 px-1 text-xs">{t('thesis.tabs.catalog')}</TabsTrigger>
        </TabsList>
        <TabsContent value="section" className="min-h-0 flex-1">
          <ScrollArea className="h-full">
            <div className="flex flex-col gap-3 p-3">
              <NewSectionRow busy={busy} onCreate={onCreate} />
              <div className="flex flex-col gap-1">
                {sections.length === 0 ? <p className="text-xs text-muted-foreground">{t('thesis.noSections')}</p> : null}
                {sections.map((item) => (
                  <div
                    key={item.id}
                    className={`flex items-start gap-1 rounded-lg border px-2 py-1.5 ${
                      scene?.id === item.id ? 'border-foreground bg-muted' : ''
                    }`}
                  >
                    <button type="button" className="min-w-0 flex-1 text-left" onClick={() => onOpen(item.id)}>
                      <span className="block text-sm font-medium">{item.name}</span>
                      <span className="block text-xs text-muted-foreground">{t(`thesis.sectionStatus.${item.status}`)}</span>
                      <span className="text-xs text-muted-foreground">
                        {t('thesis.sectionMeta', {
                          width: item.width_m,
                          height: item.height_m,
                          count: item.placement_count,
                        })}
                      </span>
                    </button>
                    <Button
                      type="button"
                      size="icon-sm"
                      variant="ghost"
                      aria-label={t('thesis.deleteSection')}
                      disabled={busy}
                      onClick={() => setPendingDelete(item)}
                    >
                      <Trash2 />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          </ScrollArea>
        </TabsContent>
        <TabsContent value="warehouse" className="flex min-h-0 flex-1 flex-col">
          <div className="flex shrink-0 items-start justify-between border-b px-3 py-3">
            <Stat value={deviceCount} label={t('thesis.devices')} align="start" />
            <Stat value={stationOnly} label={t('thesis.stations')} align="center" />
            <Stat value={readerCount} label={t('thesis.readers')} align="end" />
          </div>
          <ScrollArea className="min-h-0 flex-1">
            <div className="flex flex-col gap-3 p-3">
              <Panel title={t('thesis.group.floor')}>
                <SizeFields
                  key={`${scene?.nonce ?? 'empty'}:${scene?.width_m ?? 0}:${scene?.height_m ?? 0}`}
                  scene={scene}
                  disabled={!scene || busy}
                  onApply={onApplySize}
                />
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{t('thesis.markerScale')}</span>
                    <span className="tabular-nums">{(scene?.markerScale ?? 1).toFixed(1)}</span>
                  </div>
                  <Slider
                    min={0}
                    max={5}
                    step={0.1}
                    disabled={!scene || busy}
                    value={[scene?.markerScale ?? 1]}
                    onValueChange={(value) => {
                      const next = Array.isArray(value) ? value[0] : value
                      if (typeof next === 'number') onMarkerScale(next)
                    }}
                  />
                </div>
              </Panel>
              {!locked ? (
                <Panel title={t('thesis.group.place')}>
                  <p className="text-xs text-muted-foreground">{t('thesis.bulkHint')}</p>
                  <CountAction
                    label={t('thesis.addDevices')}
                    actionLabel={t('thesis.add')}
                    disabled={busy}
                    extra={
                      <MenuSelect
                        value={deviceMix}
                        label={t('thesis.mixed')}
                        options={[
                          { value: 'mixed', label: t('thesis.mixed') },
                          { value: '1', label: t('thesis.kind.device1') },
                          { value: '2a', label: t('thesis.kind.device2a') },
                          { value: '2b', label: t('thesis.kind.device2b') },
                        ]}
                        onChange={setDeviceMix}
                      />
                    }
                    onRun={(count) => onAddDevices(count, deviceMix)}
                  />
                  <StationPlace disabled={busy} onRandom={onAddStations} onInterval={onAddStationGrid} />
                  <div className="grid grid-cols-2 gap-2">
                    <Button type="button" size="sm" variant="outline" disabled={busy} onClick={() => setPendingClear('device')}>
                      {t('thesis.clearDevices')}
                    </Button>
                    <Button type="button" size="sm" variant="outline" disabled={busy} onClick={() => setPendingClear('infra')}>
                      {t('thesis.clearInfra')}
                    </Button>
                  </div>
                </Panel>
              ) : null}
              <Panel title={t('thesis.group.readers')}>
                <StationSelect
                  selecting={selecting}
                  pickedCount={pickedCount}
                  disabled={!scene || busy}
                  onToggle={onToggleSelecting}
                  onPickEvery={onPickEvery}
                  onConvert={onConvert}
                  onClear={onClearPicked}
                />
              </Panel>
              <Panel title={t('thesis.group.range')}>
                <ClassRange
                  label={t('thesis.kind.station')}
                  radius={Number(catalog.find((entry) => entry.kind === 'station')?.defaults.radius_m ?? 20)}
                  disabled={!scene || busy}
                  applyLabel={t('thesis.apply')}
                  onApply={(radius) => {
                    onCatalogValue('station', null, 'radius_m', radius)
                    onApplyKind('station', null, { radius_m: radius })
                  }}
                />
                <ClassRange
                  label={t('thesis.kind.radar')}
                  radius={Number(catalog.find((entry) => entry.kind === 'radar')?.defaults.radius_m ?? 30)}
                  disabled={!scene || busy}
                  applyLabel={t('thesis.apply')}
                  onApply={(radius) => {
                    onCatalogValue('radar', null, 'radius_m', radius)
                    onApplyKind('radar', null, { radius_m: radius })
                  }}
                />
              </Panel>
            </div>
          </ScrollArea>
        </TabsContent>
        <TabsContent value="catalog" className="min-h-0 flex-1">
          <ScrollArea className="h-full">
            <div className="flex flex-col gap-3 p-3">
              {catalog.map((entry) => (
                <article key={`${entry.kind}-${entry.subtype}`} className="rounded-xl border p-3">
                  <div className="mb-2 flex items-center gap-2">
                    <ShapeGlyph shape={entry.kind === 'device' ? 'circle' : entry.shape} className={`size-6 ${glyphClass(entry)}`} />
                    <h3 className="text-sm font-medium">{cardTitle(t, entry)}</h3>
                  </div>
                  <div className="flex flex-col gap-2">
                    {Object.entries(entry.defaults).map(([key, value]) =>
                      typeof value === 'boolean' ? (
                        <label key={key} className="flex items-center gap-2 text-xs">
                          <Checkbox checked={value} onCheckedChange={(next) => onCatalogValue(entry.kind, entry.subtype, key, next === true)} />
                          <span>{paramLabel(t, key)}</span>
                        </label>
                      ) : (
                        <label key={key} className="grid grid-cols-[1fr_7.5rem] items-center gap-2 text-xs">
                          <span className="text-muted-foreground">{paramLabel(t, key)}</span>
                          <CatalogInput
                            value={value}
                            onCommit={(next) => onCatalogValue(entry.kind, entry.subtype, key, next)}
                          />
                        </label>
                      ),
                    )}
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="mt-3 w-full"
                    disabled={!scene || busy}
                    onClick={() => onApplyKind(entry.kind, entry.subtype, entry.defaults)}
                  >
                    {t('thesis.applyToPlaced')}
                  </Button>
                </article>
              ))}
            </div>
          </ScrollArea>
        </TabsContent>
      </Tabs>
      ) : null}
      <Dialog open={pendingDelete != null} onOpenChange={(next) => { if (!next) setPendingDelete(null) }}>
        <DialogPortal>
          <DialogBackdrop />
          <DialogPopup className="w-[min(420px,calc(100vw-32px))] gap-3 p-4">
            <DialogTitle>{t('thesis.deleteSectionTitle')}</DialogTitle>
            <DialogDescription>
              {t('thesis.deleteSectionBody', { name: pendingDelete?.name ?? '' })}
            </DialogDescription>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setPendingDelete(null)}>
                {t('thesis.cancel')}
              </Button>
              <Button
                type="button"
                variant="destructive"
                disabled={busy}
                onClick={() => {
                  if (!pendingDelete) return
                  const id = pendingDelete.id
                  setPendingDelete(null)
                  void onDelete(id)
                }}
              >
                {t('thesis.delete')}
              </Button>
            </div>
          </DialogPopup>
        </DialogPortal>
      </Dialog>
      <Dialog open={pendingClear != null} onOpenChange={(next) => { if (!next) setPendingClear(null) }}>
        <DialogPortal>
          <DialogBackdrop />
          <DialogPopup className="w-[min(420px,calc(100vw-32px))] gap-3 p-4">
            <DialogTitle>
              {t(pendingClear === 'device' ? 'thesis.clearDevicesTitle' : 'thesis.clearInfraTitle')}
            </DialogTitle>
            <DialogDescription>
              {t(pendingClear === 'device' ? 'thesis.clearDevicesConfirm' : 'thesis.clearInfraConfirm')}
            </DialogDescription>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setPendingClear(null)}>
                {t('thesis.cancel')}
              </Button>
              <Button
                type="button"
                variant="destructive"
                disabled={busy || pendingClear == null}
                onClick={() => {
                  const which = pendingClear
                  setPendingClear(null)
                  if (which === 'device') onClearDevices()
                  else if (which === 'infra') onClearInfra()
                }}
              >
                {t('thesis.delete')}
              </Button>
            </div>
          </DialogPopup>
        </DialogPortal>
      </Dialog>
    </aside>
      <Button
        type="button"
        size="icon-sm"
        variant="outline"
        className="absolute top-3 left-full z-30 ml-2 bg-background shadow-sm"
        aria-expanded={open}
        aria-label={open ? t('thesis.collapseSidebar') : t('thesis.expandSidebar')}
        onClick={() => setOpen((value) => !value)}
      >
        {open ? <PanelLeftClose /> : <PanelLeftOpen />}
      </Button>
    </div>
  )
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3 rounded-xl border bg-card p-3">
      <h3 className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">{title}</h3>
      {children}
    </section>
  )
}

function Stat({ value, label, align }: { value: number; label: string; align: 'start' | 'center' | 'end' }) {
  const items = align === 'start' ? 'items-start' : align === 'end' ? 'items-end' : 'items-center'
  return (
    <div className={`flex flex-col ${items}`}>
      <div className="text-2xl font-semibold tabular-nums leading-none">{value}</div>
      <div className="mt-1 text-[11px] text-muted-foreground">{label}</div>
    </div>
  )
}

function NewSectionRow({ busy, onCreate }: { busy: boolean; onCreate: (name: string) => Promise<boolean> }) {
  const { t } = useTranslation()
  const [name, setName] = useState('')

  async function submit() {
    if (!name.trim() || busy) return
    const created = await onCreate(name)
    if (created) setName('')
  }

  return (
    <form
      className="flex items-center gap-1 rounded-lg border border-dashed px-2 py-1"
      onSubmit={(event) => {
        event.preventDefault()
        void submit()
      }}
    >
      <Input
        value={name}
        disabled={busy}
        placeholder={t('thesis.namePlaceholder')}
        aria-label={t('thesis.sectionName')}
        className="h-8 border-0 bg-transparent px-1 shadow-none focus-visible:ring-0"
        onChange={(event) => setName(event.target.value)}
      />
      <Button
        type="submit"
        size="icon-sm"
        variant="ghost"
        disabled={busy || !name.trim()}
        aria-label={t('thesis.addSection')}
      >
        <Plus />
      </Button>
    </form>
  )
}

function SizeFields({
  scene,
  disabled,
  onApply,
}: {
  scene: Scene | null
  disabled: boolean
  onApply: (width: number, height: number) => void
}) {
  const { t } = useTranslation()
  const [width, setWidth] = useState(String(scene?.width_m ?? DEFAULT_WIDTH_M))
  const [height, setHeight] = useState(String(scene?.height_m ?? DEFAULT_HEIGHT_M))
  return (
    <div className="grid grid-cols-[1fr_1fr_auto] items-end gap-2">
      <label className="flex flex-col gap-1 text-xs">
        <span className="text-muted-foreground">{t('thesis.length')}</span>
        <Input value={width} disabled={disabled} onChange={(event) => setWidth(event.target.value)} />
      </label>
      <label className="flex flex-col gap-1 text-xs">
        <span className="text-muted-foreground">{t('thesis.width')}</span>
        <Input value={height} disabled={disabled} onChange={(event) => setHeight(event.target.value)} />
      </label>
      <Button
        type="button"
        size="sm"
        variant="outline"
        disabled={disabled}
        onClick={() => onApply(Number(width), Number(height))}
      >
        {t('thesis.apply')}
      </Button>
    </div>
  )
}

function StationPlace({
  disabled,
  onRandom,
  onInterval,
}: {
  disabled: boolean
  onRandom: (count: number) => void
  onInterval: (spacingX: number, spacingY: number) => void
}) {
  const { t } = useTranslation()
  const [mode, setMode] = useState<'interval' | 'random'>('interval')
  const [spacingX, setSpacingX] = useState('10')
  const [spacingY, setSpacingY] = useState('10')
  const [count, setCount] = useState('10')
  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs text-muted-foreground">{t('thesis.addStations')}</span>
      <MenuSelect
        value={mode}
        disabled={disabled}
        label={t('thesis.addStations')}
        options={[
          { value: 'interval', label: t('thesis.stationInterval') },
          { value: 'random', label: t('thesis.stationRandom') },
        ]}
        onChange={setMode}
      />
      {mode === 'interval' ? (
        <div className="flex items-center gap-2">
          <Input className="w-16" value={spacingX} disabled={disabled} onChange={(event) => setSpacingX(event.target.value)} aria-label={t('thesis.spacingX')} />
          <span className="text-xs text-muted-foreground">{t('thesis.spacingX')}</span>
          <Input className="w-16" value={spacingY} disabled={disabled} onChange={(event) => setSpacingY(event.target.value)} aria-label={t('thesis.spacingY')} />
          <span className="text-xs text-muted-foreground">{t('thesis.spacingY')}</span>
          <Button type="button" size="sm" disabled={disabled} onClick={() => onInterval(Number(spacingX), Number(spacingY))}>
            {t('thesis.add')}
          </Button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <Input className="w-24" value={count} disabled={disabled} onChange={(event) => setCount(event.target.value)} />
          <Button type="button" size="sm" disabled={disabled} onClick={() => onRandom(Number(count))}>
            {t('thesis.add')}
          </Button>
        </div>
      )}
    </div>
  )
}

function MenuSelect<T extends string>({
  value,
  options,
  disabled,
  label,
  onChange,
}: {
  value: T
  options: { value: T; label: string }[]
  disabled?: boolean
  label: string
  onChange: (value: T) => void
}) {
  const items = Object.fromEntries(options.map((option) => [option.value, option.label]))
  return (
    <Select
      value={value}
      items={items}
      disabled={disabled}
      onValueChange={(next) => {
        if (next == null) return
        onChange(String(next) as T)
      }}
    >
      <SelectTrigger className="h-8 w-full min-w-0" aria-label={label}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent align="start" alignItemWithTrigger={false}>
        {options.map((option) => (
          <SelectItem key={option.value} value={option.value}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

function CountAction({
  label,
  actionLabel,
  disabled,
  extra,
  onRun,
}: {
  label: string
  actionLabel: string
  disabled: boolean
  extra?: ReactNode
  onRun: (count: number) => void
}) {
  const [count, setCount] = useState('100')
  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs text-muted-foreground">{label}</span>
      {extra}
      <div className="flex items-center gap-2">
        <Input className="w-24" value={count} disabled={disabled} onChange={(event) => setCount(event.target.value)} />
        <Button type="button" size="sm" disabled={disabled} onClick={() => onRun(Number(count))}>
          {actionLabel}
        </Button>
      </div>
    </div>
  )
}

function cardTitle(t: (key: string, options?: Record<string, unknown>) => string, entry: CatalogEntry) {
  if (entry.kind === 'device') return t(`thesis.kind.device${entry.subtype}`)
  return t(`thesis.kind.${entry.kind}`)
}

function glyphClass(entry: CatalogEntry) {
  if (entry.subtype === '1') return 'text-[#1d4ed8]'
  if (entry.subtype === '2a') return 'text-[#0f766e]'
  if (entry.subtype === '2b') return 'text-[#c2410c]'
  if (entry.kind === 'station') return 'text-[#6d28d9]'
  return 'text-[#b91c1c]'
}

function paramLabel(t: (key: string) => string, key: string) {
  const i18nKey = `thesis.params.${key}`
  const translated = t(i18nKey)
  return translated === i18nKey ? key : translated
}

function StationSelect({
  selecting,
  pickedCount,
  disabled,
  onToggle,
  onPickEvery,
  onConvert,
  onClear,
}: {
  selecting: boolean
  pickedCount: number
  disabled: boolean
  onToggle: () => void
  onPickEvery: (gapX: number, gapY: number) => void
  onConvert: (kind: 'station' | 'radar') => void
  onClear: () => void
}) {
  const { t } = useTranslation()
  const [gapX, setGapX] = useState('1')
  const [gapY, setGapY] = useState('1')
  return (
    <div className="flex flex-col gap-2">
      <Button type="button" size="sm" variant={selecting ? 'default' : 'outline'} disabled={disabled} onClick={onToggle}>
        {t('thesis.selectMode')}
      </Button>
      <p className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{t('thesis.selectedCount', { count: pickedCount })}</span>
        <button type="button" className="underline-offset-2 hover:underline disabled:opacity-40" disabled={disabled || pickedCount === 0} onClick={onClear}>
          {t('thesis.clearSelection')}
        </button>
      </p>
      <div className="flex items-center gap-2">
        <Input className="w-14" value={gapX} disabled={disabled} aria-label={t('thesis.gapX')} onChange={(event) => setGapX(event.target.value)} />
        <span className="text-xs text-muted-foreground">{t('thesis.gapX')}</span>
        <Input className="w-14" value={gapY} disabled={disabled} aria-label={t('thesis.gapY')} onChange={(event) => setGapY(event.target.value)} />
        <span className="text-xs text-muted-foreground">{t('thesis.gapY')}</span>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={disabled}
          onClick={() =>
            onPickEvery(Math.max(0, Math.floor(Number(gapX))), Math.max(0, Math.floor(Number(gapY))))
          }
        >
          {t('thesis.pickEvery')}
        </Button>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button type="button" size="sm" disabled={disabled || pickedCount === 0} onClick={() => onConvert('radar')}>
          {t('thesis.toRadar')}
        </Button>
        <Button type="button" size="sm" variant="outline" disabled={disabled || pickedCount === 0} onClick={() => onConvert('station')}>
          {t('thesis.toStation')}
        </Button>
      </div>
    </div>
  )
}

function ClassRange({
  label,
  radius,
  disabled,
  applyLabel,
  onApply,
}: {
  label: string
  radius: number
  disabled: boolean
  applyLabel: string
  onApply: (radius: number) => void
}) {
  const [text, setText] = useState(String(radius))
  useEffect(() => {
    setText(String(radius))
  }, [radius])
  return (
    <div className="flex items-end gap-2">
      <label className="flex min-w-0 flex-1 flex-col gap-1 text-xs">
        <span className="text-muted-foreground">{label}</span>
        <Input value={text} disabled={disabled} onChange={(event) => setText(event.target.value)} />
      </label>
      <Button
        type="button"
        size="sm"
        variant="outline"
        disabled={disabled || !(Number(text) > 0)}
        onClick={() => onApply(Number(text))}
      >
        {applyLabel}
      </Button>
    </div>
  )
}

function CatalogInput({ value, onCommit }: { value: ParamValue; onCommit: (value: ParamValue) => void }) {
  const [text, setText] = useState(value == null ? '' : String(value))
  useEffect(() => {
    setText(value == null ? '' : String(value))
  }, [value])
  return (
    <Input
      className="h-7"
      value={text}
      onChange={(event) => setText(event.target.value)}
      onBlur={() => {
        if (typeof value === 'string') {
          onCommit(text)
          return
        }
        if (text.trim() === '') {
          onCommit(null)
          return
        }
        const number = Number(text)
        if (Number.isFinite(number)) onCommit(number)
        else setText(value == null ? '' : String(value))
      }}
    />
  )
}
