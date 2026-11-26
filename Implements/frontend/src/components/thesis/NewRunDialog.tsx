import { DicesIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ParamHint } from '@/components/ParamHint'
import {
  ControllerSection,
  DEFAULT_RESOURCE,
  defaultTermination,
  ResourceSection,
  TerminationSection,
  terminationLabel,
} from '@/components/thesis/MultiReaderOptions'
import {
  compactGroups,
  groupColor,
  StartGroupsDialog,
  type StartAssignment,
  type StartReader,
} from '@/components/thesis/StartGroupsDialog'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Dialog, DialogBackdrop, DialogDescription, DialogPopup, DialogPortal, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Dropdown } from '@/components/ui/dropdown'
import { SPEED_OPTIONS } from '@/lib/thesisRunStates'
import type { ControllerSpec, ResourceSpec, RunCreateInput, RunScheme, TerminationSpec } from '@/types/thesis'

const STEPS = ['paging', 'frame', 'readers', 'stop', 'preview'] as const

export function NewRunDialog({
  open,
  busy,
  readers,
  floor = null,
  onClose,
  onCreate,
}: {
  open: boolean
  busy: boolean
  readers: StartReader[]
  floor?: { width: number; height: number } | null
  onClose: () => void
  onCreate: (config: RunCreateInput) => Promise<void> | void
}) {
  const { t } = useTranslation()
  const [name, setName] = useState('')
  const [scheme, setScheme] = useState<RunScheme>('aperiodic')
  const [speed, setSpeed] = useState('1')
  const [stallTimeout, setStallTimeout] = useState('300')
  const [kInitial, setKInitial] = useState('128')
  const [pFixed, setPFixed] = useState('1')
  const [g, setG] = useState('1')
  const [useGrouping, setUseGrouping] = useState(false)
  const [useCapture, setUseCapture] = useState(true)
  const [useEbi, setUseEbi] = useState(true)
  const [includeD2r, setIncludeD2r] = useState(true)
  const [singleReply, setSingleReply] = useState(false)
  const [seed, setSeed] = useState('')
  const [disabledReaders, setDisabledReaders] = useState<Set<number>>(new Set())
  const [stagger, setStagger] = useState(false)
  const [intervalMs, setIntervalMs] = useState('100')
  const [assignment, setAssignment] = useState<StartAssignment>({})
  const [groupsOpen, setGroupsOpen] = useState(false)
  const [controller, setController] = useState<ControllerSpec>({ kind: 'fixed', policy_id: null, deterministic: true })
  const [resource, setResource] = useState<ResourceSpec>(DEFAULT_RESOURCE)
  const [termination, setTermination] = useState<TerminationSpec>(defaultTermination('oracle'))
  const [fFreq, setFFreq] = useState('')
  const [step, setStep] = useState(0)

  useEffect(() => {
    if (open) setStep(0)
  }, [open])

  const periodic = scheme === 'periodic'
  const enabledReaders = readers.filter((r) => !disabledReaders.has(r.id))
  const startGroups = compactGroups(enabledReaders, assignment)
  const interval = Math.max(0, Number(intervalMs) || 0)
  const staggered = stagger && readers.length > 1

  const policyMissing = controller.kind === 'policy' && !controller.policy_id

  async function submit() {
    const trimmed = name.trim()
    const config: RunCreateInput = {
      scheme,
      name: trimmed || null,
      // Interactive runs have no time cap: they end when every reachable device is
      // identified, on the stall guard, or when the user pauses / stops them.
      max_time_s: null,
      speed: speed === 'max' ? null : Number(speed),
      stall_timeout_s: positiveOrNull(stallTimeout),
      // Adaptive: K is only the cold-start (e.g. 256); later rounds follow Schoute.
      // Fixed: every round uses that same K.
      k_initial: Number(kInitial) || null,
      p_fixed: controller.kind === 'fixed' ? fixedP(pFixed) : null,
      // Stored beside the controller so older readers of this config still see one answer.
      // fixed → every round uses K; dfsa → K is only the first round; policy ignores the flag.
      adaptive_k: controller.kind === 'dfsa',
      g: periodic ? Number(g) || null : 1,
      use_grouping: periodic && useGrouping,
      use_capture: useCapture,
      use_ebi: useEbi,
      include_d2r: includeD2r,
      single_reply: singleReply,
      seed: seed === '' ? null : Number(seed),
      disabled_reader_ids: Array.from(disabledReaders),
      f_freq: positiveOrNull(fFreq),
      controller: controller.kind === 'policy' ? controller : { kind: controller.kind },
      resource,
      termination,
    }
    if (staggered) {
      config.reader_start_groups = startGroups
      config.reader_start_interval_s = interval / 1000
      config.reader_start_offsets = Object.fromEntries(
        startGroups.flatMap((ids, g) => ids.map((id) => [String(id), (g * interval) / 1000])),
      )
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
        <DialogPopup className="flex h-[min(84vh,800px)] max-h-[calc(100dvh-32px)] w-[min(680px,calc(100vw-32px))] flex-col gap-4 overflow-visible p-5">
          <DialogTitle>{t('thesis.newRun.title')}</DialogTitle>
          <DialogDescription>{t('thesis.newRun.hint')}</DialogDescription>
          <div className="flex min-h-0 flex-1 gap-5">
            <nav aria-label={t('thesis.newRun.wizard.steps')} className="flex w-36 shrink-0 flex-col pt-1">
              {STEPS.map((id, index) => {
                const active = index === step
                const done = index < step
                return (
                  <div key={id} className="flex gap-2.5">
                    <div className="flex flex-col items-center">
                      <button
                        type="button"
                        aria-current={active ? 'step' : undefined}
                        onClick={() => setStep(index)}
                        className={`flex size-6 shrink-0 items-center justify-center rounded-full border text-[11px] ${
                          active
                            ? 'border-foreground bg-foreground text-background'
                            : done
                              ? 'border-foreground text-foreground'
                              : 'border-border text-muted-foreground'
                        }`}
                      >
                        {index + 1}
                      </button>
                      {index < STEPS.length - 1 ? <span className={`my-1 w-px flex-1 ${done ? 'bg-foreground' : 'bg-border'}`} /> : null}
                    </div>
                    <button
                      type="button"
                      onClick={() => setStep(index)}
                      className={`text-left text-sm leading-6 ${index < STEPS.length - 1 ? 'pb-5' : ''} ${active ? 'font-medium text-foreground' : 'text-muted-foreground'}`}
                    >
                      {t(`thesis.newRun.tabs.${id}`)}
                    </button>
                  </div>
                )
              })}
            </nav>
            <div className="min-h-0 flex-1 overflow-x-auto overflow-y-auto px-4">
            {step === 0 ? (
            <div className="grid w-full min-w-0 max-w-md grid-cols-2 content-start gap-3">
            <label className="col-span-2 flex flex-col gap-1 text-xs">
              <span className="text-muted-foreground">{t('thesis.newRun.name')}</span>
              <Input
                value={name}
                maxLength={80}
                onChange={(e) => setName(e.target.value)}
                placeholder={t('thesis.newRun.namePlaceholder')}
              />
            </label>
            <label className="col-span-2 flex flex-col gap-1 text-xs">
              <span className="text-muted-foreground">{t('thesis.newRun.scheme')}</span>
              <Dropdown
                value={scheme}
                options={[
                  { value: 'periodic', label: t('thesis.newRun.schemePeriodic') },
                  { value: 'aperiodic', label: t('thesis.newRun.schemeAperiodic') },
                ]}
                onChange={setScheme}
              />
            </label>
            <label className="flex flex-col gap-1 text-xs">
              <span className="text-muted-foreground">{t('thesis.live.speed')}</span>
              <Dropdown
                value={speed}
                options={SPEED_OPTIONS.map((v) => {
                  const id = v == null ? 'max' : String(v)
                  return { value: id, label: v == null ? t('thesis.live.max') : `${v}×` }
                })}
                onChange={setSpeed}
              />
            </label>
            {periodic ? (
              <label className="flex flex-col gap-1 text-xs">
                <span className="text-muted-foreground">{t('thesis.newRun.g')}</span>
                <Input value={g} onChange={(e) => setG(e.target.value)} disabled={!useGrouping} />
              </label>
            ) : null}
            <label className="flex flex-col gap-1 text-xs">
              <span className="text-muted-foreground">{t('thesis.newRun.seed')}</span>
              <div className="flex gap-1">
                <Input value={seed} onChange={(e) => setSeed(e.target.value)} placeholder="auto" />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  title={t('thesis.newRun.randomSeed')}
                  aria-label={t('thesis.newRun.randomSeed')}
                  onClick={() => setSeed(String(Math.floor(Math.random() * 1_000_000_000)))}
                >
                  <DicesIcon />
                </Button>
              </div>
            </label>
            {periodic ? (
              <OptionToggle
                checked={useGrouping}
                onChange={setUseGrouping}
                label={t('thesis.newRun.useGrouping')}
                hint={t('thesis.newRun.useGroupingHint')}
              />
            ) : null}
            <OptionToggle
              checked={useCapture}
              onChange={setUseCapture}
              label={t('thesis.newRun.useCapture')}
              hint={t('thesis.newRun.useCaptureHint')}
            />
            <OptionToggle
              checked={useEbi}
              onChange={setUseEbi}
              label={t('thesis.newRun.useEbi')}
              hint={t('thesis.newRun.useEbiHint')}
            />
            <OptionToggle
              checked={includeD2r}
              onChange={setIncludeD2r}
              label={t('thesis.newRun.includeD2r')}
              hint={t('thesis.newRun.includeD2rHint')}
            />
            <OptionToggle
              checked={singleReply}
              onChange={setSingleReply}
              label={t('thesis.newRun.singleReply')}
              hint={t('thesis.newRun.singleReplyHint')}
            />
            </div>
            ) : null}
            {step === 1 ? (
            <div className="grid w-full min-w-0 max-w-md grid-cols-2 content-start gap-3">
            <label className={`flex flex-col gap-1 text-xs ${controller.kind === 'fixed' ? '' : 'col-span-2 max-w-xs'}`}>
              <span className="text-muted-foreground">
                {controller.kind === 'fixed' ? t('thesis.newRun.k') : t('thesis.newRun.kInitial')}
              </span>
              <Input value={kInitial} onChange={(e) => setKInitial(e.target.value)} placeholder="128" />
            </label>
            {controller.kind === 'fixed' ? (
              <label className="flex flex-col gap-1 text-xs">
                <span className="flex items-center gap-1 text-muted-foreground">
                  {t('thesis.newRun.pFixed')}
                  <ParamHint text={t('thesis.newRun.pFixedHint')} title={t('thesis.newRun.pFixed')} />
                </span>
                <Input
                  value={pFixed}
                  inputMode="decimal"
                  onChange={(e) => setPFixed(e.target.value)}
                  placeholder="1"
                />
              </label>
            ) : null}
            <ControllerSection value={controller} onChange={setController} />
            </div>
            ) : null}
            {step === 2 ? (
            <div className="grid w-full min-w-0 max-w-md grid-cols-2 content-start gap-3">
            {readers.length > 1 ? (
              <>
                <OptionToggle
                  checked={stagger}
                  onChange={setStagger}
                  label={t('thesis.newRun.stagger')}
                  hint={t('thesis.newRun.staggerHint')}
                />
                {stagger ? (
                  <div className="col-span-2 flex flex-wrap items-end gap-2 rounded-md border p-2 text-xs">
                    <label className="flex w-32 flex-col gap-1">
                      <span className="text-muted-foreground">{t('thesis.newRun.staggerInterval')}</span>
                      <Input value={intervalMs} onChange={(e) => setIntervalMs(e.target.value)} inputMode="decimal" />
                    </label>
                    <Button type="button" size="sm" variant="outline" onClick={() => setGroupsOpen(true)}>
                      {t('thesis.newRun.staggerAssign')}
                    </Button>
                    <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1">
                      {startGroups.map((ids, g) => (
                        <span key={g} className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5">
                          <span className="size-2 rounded-full" style={{ background: groupColor(g) }} />
                          G{g + 1} · {ids.length} · +{g * interval} ms
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}
              </>
            ) : null}
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
            <ResourceSection
              value={resource}
              fFreq={fFreq}
              readerCount={enabledReaders.length}
              onChange={setResource}
              onFFreq={setFFreq}
            />
            </div>
            ) : null}
            {step === 3 ? (
            <div className="grid w-full min-w-0 max-w-md grid-cols-2 content-start gap-3">
            <label className="flex flex-col gap-1 text-xs">
              <span className="text-muted-foreground">{t('thesis.newRun.stallTimeout')}</span>
              <Input value={stallTimeout} onChange={(e) => setStallTimeout(e.target.value)} placeholder={t('thesis.newRun.off')} />
            </label>
            <p className="col-span-2 text-[11px] text-muted-foreground">{t('thesis.newRun.endHint')}</p>
            <TerminationSection value={termination} onChange={setTermination} />
            </div>
            ) : null}
            {step === 4 ? (
              <RunPreview
                name={name}
                scheme={scheme}
                periodic={periodic}
                speed={speed}
                seed={seed}
                useGrouping={useGrouping}
                g={g}
                useCapture={useCapture}
                useEbi={useEbi}
                includeD2r={includeD2r}
                singleReply={singleReply}
                kInitial={kInitial}
                pFixed={pFixed}
                controller={controller}
                readers={readers}
                disabledReaders={disabledReaders}
                staggered={staggered}
                interval={interval}
                groupCount={startGroups.length}
                resource={resource}
                fFreq={fFreq}
                stallTimeout={stallTimeout}
                termination={termination}
                policyMissing={policyMissing}
                onEdit={setStep}
              />
            ) : null}
            </div>
          </div>
          <div className="flex items-center justify-between gap-2 border-t pt-3">
            <Button type="button" variant="outline" disabled={busy} onClick={onClose}>
              {t('thesis.newRun.cancel')}
            </Button>
            <div className="flex gap-2">
              <Button type="button" variant="outline" disabled={busy || step === 0} onClick={() => setStep((current) => current - 1)}>
                {t('thesis.newRun.wizard.back')}
              </Button>
              {step < STEPS.length - 1 ? (
                <Button type="button" onClick={() => setStep((current) => current + 1)}>
                  {t('thesis.newRun.wizard.next')}
                </Button>
              ) : (
                <Button type="button" disabled={busy || policyMissing} onClick={() => void submit()}>
                  {t('thesis.newRun.start')}
                </Button>
              )}
            </div>
          </div>
        </DialogPopup>
      </DialogPortal>
      <StartGroupsDialog
        open={groupsOpen}
        readers={enabledReaders}
        floor={floor}
        intervalMs={interval}
        value={assignment}
        onClose={() => setGroupsOpen(false)}
        onApply={(next) => {
          setAssignment(next)
          setGroupsOpen(false)
        }}
      />
    </Dialog>
  )
}

function OptionToggle({
  checked,
  onChange,
  label,
  hint,
}: {
  checked: boolean
  onChange: (checked: boolean) => void
  label: string
  hint: string
}) {
  return (
    <div className="col-span-2 flex items-center gap-1.5 text-sm">
      <label className="flex items-center gap-2">
        <Checkbox checked={checked} onCheckedChange={(v) => onChange(v === true)} />
        {label}
      </label>
      <ParamHint text={hint} title={label} />
    </div>
  )
}

function fixedP(raw: string): number {
  const n = Number(raw)
  if (!Number.isFinite(n) || n <= 0) return 1
  return Math.min(1, n)
}

function positiveOrNull(raw: string): number | null {
  const n = Number(raw)
  return raw.trim() === '' || !Number.isFinite(n) || n <= 0 ? null : n
}

function RunPreview({
  name,
  scheme,
  periodic,
  speed,
  seed,
  useGrouping,
  g,
  useCapture,
  useEbi,
  includeD2r,
  singleReply,
  kInitial,
  pFixed,
  controller,
  readers,
  disabledReaders,
  staggered,
  interval,
  groupCount,
  resource,
  fFreq,
  stallTimeout,
  termination,
  policyMissing,
  onEdit,
}: {
  name: string
  scheme: RunScheme
  periodic: boolean
  speed: string
  seed: string
  useGrouping: boolean
  g: string
  useCapture: boolean
  useEbi: boolean
  includeD2r: boolean
  singleReply: boolean
  kInitial: string
  pFixed: string
  controller: ControllerSpec
  readers: StartReader[]
  disabledReaders: Set<number>
  staggered: boolean
  interval: number
  groupCount: number
  resource: ResourceSpec
  fFreq: string
  stallTimeout: string
  termination: TerminationSpec
  policyMissing: boolean
  onEdit: (step: number) => void
}) {
  const { t } = useTranslation()
  const flag = (on: boolean) => (on ? t('thesis.newRun.on') : t('thesis.newRun.off'))
  const active = readers.length - disabledReaders.size
  return (
    <div className="flex w-full min-w-0 max-w-md flex-col gap-4">
      <p className="text-xs text-muted-foreground">{t('thesis.newRun.wizard.previewHint')}</p>
      <PreviewGroup title={t('thesis.newRun.tabs.paging')} onEdit={() => onEdit(0)} editLabel={t('thesis.newRun.wizard.edit')}>
        <PreviewRow label={t('thesis.newRun.name')} value={name.trim() || '—'} />
        <PreviewRow label={t('thesis.newRun.scheme')} value={t(scheme === 'periodic' ? 'thesis.newRun.schemePeriodic' : 'thesis.newRun.schemeAperiodic')} />
        <PreviewRow label={t('thesis.live.speed')} value={speed === 'max' ? t('thesis.live.max') : `${speed}×`} />
        <PreviewRow label={t('thesis.newRun.seed')} value={seed.trim() || 'auto'} />
        {periodic ? <PreviewRow label={t('thesis.newRun.useGrouping')} value={useGrouping ? `${flag(true)} · N_g=${g || '1'}` : flag(false)} /> : null}
        <PreviewRow label={t('thesis.newRun.useCapture')} value={flag(useCapture)} />
        <PreviewRow label={t('thesis.newRun.useEbi')} value={flag(useEbi)} />
        <PreviewRow label={t('thesis.newRun.includeD2r')} value={flag(includeD2r)} />
        <PreviewRow label={t('thesis.newRun.singleReply')} value={flag(singleReply)} />
      </PreviewGroup>
      <PreviewGroup title={t('thesis.newRun.tabs.frame')} onEdit={() => onEdit(1)} editLabel={t('thesis.newRun.wizard.edit')}>
        <PreviewRow label={t('thesis.newRun.controller.kind')} value={t(`thesis.newRun.controller.kinds.${controller.kind}`)} />
        <PreviewRow label={controller.kind === 'fixed' ? t('thesis.newRun.k') : t('thesis.newRun.kInitial')} value={kInitial || '128'} />
        {controller.kind === 'fixed' ? <PreviewRow label={t('thesis.newRun.pFixed')} value={String(fixedP(pFixed))} /> : null}
        {controller.kind === 'policy' ? (
          <PreviewRow label={t('thesis.newRun.controller.policy')} value={policyMissing ? t('thesis.newRun.controller.noPolicies') : (controller.policy_id ?? '—')} />
        ) : null}
      </PreviewGroup>
      <PreviewGroup title={t('thesis.newRun.tabs.readers')} onEdit={() => onEdit(2)} editLabel={t('thesis.newRun.wizard.edit')}>
        <PreviewRow label={t('thesis.newRun.disableReaders')} value={`${active} / ${readers.length}`} />
        <PreviewRow label={t('thesis.newRun.stagger')} value={staggered ? `${groupCount} · ${interval} ms` : flag(false)} />
        <PreviewRow label={t('thesis.newRun.resource.mode')} value={t(`thesis.newRun.resource.modes.${resource.mode}`)} />
        <PreviewRow label={t('thesis.newRun.resource.fFreq')} value={fFreq.trim() || '8'} />
      </PreviewGroup>
      <PreviewGroup title={t('thesis.newRun.tabs.stop')} onEdit={() => onEdit(3)} editLabel={t('thesis.newRun.wizard.edit')}>
        <PreviewRow label={t('thesis.newRun.stallTimeout')} value={positiveOrNull(stallTimeout) == null ? t('thesis.newRun.off') : `${stallTimeout} s`} />
        <PreviewRow label={t('thesis.newRun.termination.title')} value={terminationLabel(termination)} />
      </PreviewGroup>
    </div>
  )
}

function PreviewGroup({ title, editLabel, onEdit, children }: { title: string; editLabel: string; onEdit: () => void; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">{title}</h3>
        <Button type="button" variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={onEdit}>
          {editLabel}
        </Button>
      </div>
      <div className="rounded-md border px-3">{children}</div>
    </section>
  )
}

function PreviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-border/60 py-1.5 text-xs last:border-b-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right">{value}</span>
    </div>
  )
}
