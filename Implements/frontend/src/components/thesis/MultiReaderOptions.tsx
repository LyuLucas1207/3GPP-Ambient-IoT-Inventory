import { useTranslation } from 'react-i18next'
import { ParamHint } from '@/components/ParamHint'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { usePolicies } from '@/hooks/useMultiReader'
import type {
  ControllerKind,
  ControllerSpec,
  PolicyInfo,
  ResourceMode,
  ResourceSpec,
  TerminationKind,
  TerminationSpec,
} from '@/types/thesis'

export const CONTROLLER_KINDS: ControllerKind[] = ['auto', 'fixed', 'dfsa', 'policy']
export const RESOURCE_MODES: ResourceMode[] = ['independent', 'shared', 'fdma', 'tdma', 'hybrid', 'lbt']
export const TERMINATION_KINDS: TerminationKind[] = ['oracle', 'quiet_rounds', 'id_rate', 'energy_bound', 'combined']

export const DEFAULT_RESOURCE: ResourceSpec = {
  mode: 'independent',
  interference: true,
  cross_msg1: true,
  conflict_distance_m: null,
  n_colors: null,
  tdma_window_s: 0.5,
  freq_groups: 2,
  lbt_backoff_s: 0.05,
  lbt_max_on_s: 4,
  lbt_pause_s: 0.1,
  r2d_sir_db: 6,
  d2r_sinr_db: 0.5,
  other_cw_suppression_db: 61,
}

export function defaultTermination(kind: TerminationKind): TerminationSpec {
  switch (kind) {
    case 'quiet_rounds':
      return { kind, quiet_rounds: 10 }
    case 'id_rate':
      return { kind, window_mode: 'rounds', window: 20, ewma_alpha: 0.1, r_min: null, r_rel: 0.01, min_frames: 5 }
    case 'energy_bound':
      return { kind, margin: 0, energy_source: 'edge' }
    case 'combined':
      return { kind, combine: 'all', rules: [defaultTermination('quiet_rounds'), defaultTermination('energy_bound')] }
    default:
      return { kind: 'oracle' }
  }
}

/** Readable label of a rule, matching the backend's ``TerminationSpec.label``. */
export function terminationLabel(s: TerminationSpec): string {
  switch (s.kind) {
    case 'quiet_rounds':
      return `quiet_rounds(n=${s.quiet_rounds ?? 10})`
    case 'id_rate': {
      const thr = [s.r_min != null ? `r_min=${s.r_min}` : null, s.r_rel != null ? `r_rel=${s.r_rel}` : null].filter(Boolean).join(', ')
      const win = s.window_mode === 'ewma' ? `alpha=${s.ewma_alpha ?? 0.1}` : `${s.window_mode ?? 'rounds'}=${s.window ?? 20}`
      return `id_rate(${win}, ${thr})`
    }
    case 'energy_bound':
      return `energy_bound(${s.energy_source ?? 'edge'}, margin=${s.margin ?? 0})`
    case 'combined':
      return `${s.combine ?? 'all'}(${(s.rules ?? []).map(terminationLabel).join(', ')})`
    default:
      return 'oracle'
  }
}

function num(raw: string, fallback: number): number {
  const n = Number(raw)
  return raw.trim() === '' || !Number.isFinite(n) ? fallback : n
}

function numOrNull(raw: string): number | null {
  const n = Number(raw)
  return raw.trim() === '' || !Number.isFinite(n) ? null : n
}

function Field({ label, hint, children, wide = false }: { label: string; hint?: string; children: React.ReactNode; wide?: boolean }) {
  return (
    <label className={`flex flex-col gap-1 text-xs ${wide ? 'col-span-2' : ''}`}>
      <span className="flex items-center gap-1 text-muted-foreground">
        {label}
        {hint ? <ParamHint text={hint} title={label} /> : null}
      </span>
      {children}
    </label>
  )
}

function Toggle({ checked, onChange, label, hint }: { checked: boolean; onChange: (v: boolean) => void; label: string; hint?: string }) {
  return (
    <div className="col-span-2 flex items-center gap-1.5 text-sm">
      <label className="flex items-center gap-2">
        <Checkbox checked={checked} onCheckedChange={(v) => onChange(v === true)} />
        {label}
      </label>
      {hint ? <ParamHint text={hint} title={label} /> : null}
    </div>
  )
}

function Choice<T extends string>({ value, options, label, onChange }: { value: T; options: [T, string][]; label: (v: T) => string; onChange: (v: T) => void }) {
  return (
    <Select value={value} items={Object.fromEntries(options)} onValueChange={(v) => onChange((v ?? value) as T)}>
      <SelectTrigger className="h-8 w-full">
        <SelectValue />
      </SelectTrigger>
      <SelectContent align="start">
        {options.map(([v]) => (
          <SelectItem key={v} value={v}>
            {label(v)}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

export function Section({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <fieldset className="col-span-2 grid grid-cols-2 gap-2 rounded-md border p-2">
      <legend className="flex items-center gap-1 px-1 text-xs font-medium">
        {title}
        {hint ? <ParamHint text={hint} title={title} /> : null}
      </legend>
      {children}
    </fieldset>
  )
}

// ------------------------------------------------------------------ controller

export function ControllerSection({ value, adaptiveK, onChange }: { value: ControllerSpec; adaptiveK: boolean; onChange: (v: ControllerSpec) => void }) {
  const { t } = useTranslation()
  const policies = usePolicies()
  const available = (policies.data ?? []).filter((p) => p.available)
  const selected = (policies.data ?? []).find((p) => p.policy_id === value.policy_id) ?? null
  const kindLabel = (k: ControllerKind) => t(`thesis.newRun.controller.kinds.${k}`)
  return (
    <Section title={t('thesis.newRun.controller.title')} hint={t('thesis.newRun.controller.hint')}>
      <Field label={t('thesis.newRun.controller.kind')} wide>
        <Choice
          value={value.kind}
          options={CONTROLLER_KINDS.map((k) => [k, kindLabel(k)])}
          label={kindLabel}
          onChange={(kind) => onChange({ ...value, kind, policy_id: kind === 'policy' ? value.policy_id ?? available[0]?.policy_id ?? null : null })}
        />
      </Field>
      <p className="col-span-2 text-[11px] text-muted-foreground">
        {value.kind === 'auto'
          ? t(adaptiveK ? 'thesis.newRun.controller.autoDfsa' : 'thesis.newRun.controller.autoFixed')
          : t(`thesis.newRun.controller.desc.${value.kind}`)}
      </p>
      {value.kind === 'policy' ? (
        <>
          <Field label={t('thesis.newRun.controller.policy')} wide>
            {available.length === 0 ? (
              <p className="text-destructive">{policies.isLoading ? t('thesis.timeline.loading') : t('thesis.newRun.controller.noPolicies')}</p>
            ) : (
              <Choice
                value={value.policy_id ?? ''}
                options={available.map((p) => [p.policy_id, p.policy_id])}
                label={(v) => v}
                onChange={(policy_id) => onChange({ ...value, policy_id })}
              />
            )}
          </Field>
          {selected ? <PolicyCard policy={selected} /> : null}
          <Toggle
            checked={value.deterministic ?? true}
            onChange={(deterministic) => onChange({ ...value, deterministic })}
            label={t('thesis.newRun.controller.deterministic')}
            hint={t('thesis.newRun.controller.deterministicHint')}
          />
        </>
      ) : null}
    </Section>
  )
}

export function PolicyCard({ policy }: { policy: PolicyInfo }) {
  const { t } = useTranslation()
  const ev = policy.eval_summary?.policy
  const rows: [string, string][] = [
    [t('thesis.training.algo'), t(`thesis.training.algos.${policy.algo}`, { defaultValue: policy.algo ?? '—' })],
    ['α / β', `${policy.alpha ?? '—'} / ${policy.beta ?? '—'}`],
    [t('thesis.training.scale'), policy.scale ?? '—'],
    [t('thesis.training.steps'), policy.training_steps != null ? policy.training_steps.toLocaleString() : '—'],
    [t('thesis.training.t99VsDfsa'), ev?.geo_mean_t99_vs_dfsa != null ? `${ev.geo_mean_t99_vs_dfsa.toFixed(2)}×` : '—'],
  ]
  return (
    <div className="col-span-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 rounded bg-muted/40 px-2 py-1 text-[11px]">
      {rows.map(([k, v]) => (
        <div key={k} className="contents">
          <span className="text-muted-foreground">{k}</span>
          <span className="truncate tabular-nums">{v}</span>
        </div>
      ))}
      {policy.notes ? <p className="col-span-2 text-muted-foreground">{policy.notes}</p> : null}
    </div>
  )
}

// ------------------------------------------------------------------ resource

export function ResourceSection({
  value,
  fFreq,
  readerCount,
  onChange,
  onFFreq,
}: {
  value: ResourceSpec
  fFreq: string
  readerCount: number
  onChange: (v: ResourceSpec) => void
  onFFreq: (v: string) => void
}) {
  const { t } = useTranslation()
  const set = (patch: Partial<ResourceSpec>) => onChange({ ...value, ...patch })
  const modeLabel = (m: ResourceMode) => t(`thesis.newRun.resource.modes.${m}`)
  const linkBudget = value.conflict_distance_m == null
  const coordinated = value.mode !== 'independent' && value.mode !== 'shared'
  return (
    <Section title={t('thesis.newRun.resource.title')} hint={t('thesis.newRun.resource.hint')}>
      <Field label={t('thesis.newRun.resource.mode')} wide>
        <Choice value={value.mode} options={RESOURCE_MODES.map((m) => [m, modeLabel(m)])} label={modeLabel} onChange={(mode) => set({ mode })} />
      </Field>
      <p className="col-span-2 text-[11px] text-muted-foreground">{t(`thesis.newRun.resource.desc.${value.mode}`)}</p>
      {readerCount < 2 && value.mode !== 'independent' ? (
        <p className="col-span-2 text-[11px] text-amber-600">{t('thesis.newRun.resource.singleReader')}</p>
      ) : null}
      <Field label={t('thesis.newRun.resource.fFreq')} hint={t('thesis.newRun.resource.fFreqHint')}>
        <Input value={fFreq} onChange={(e) => onFFreq(e.target.value)} placeholder="8" inputMode="numeric" />
      </Field>
      {value.mode === 'tdma' || value.mode === 'hybrid' ? (
        <Field label={t('thesis.newRun.resource.tdmaWindow')} hint={t('thesis.newRun.resource.tdmaWindowHint')}>
          <Input value={String(value.tdma_window_s ?? 0.5)} onChange={(e) => set({ tdma_window_s: num(e.target.value, 0.5) })} inputMode="decimal" />
        </Field>
      ) : null}
      {value.mode === 'hybrid' ? (
        <Field label={t('thesis.newRun.resource.freqGroups')} hint={t('thesis.newRun.resource.freqGroupsHint')}>
          <Input value={String(value.freq_groups ?? 2)} onChange={(e) => set({ freq_groups: Math.max(1, Math.round(num(e.target.value, 2))) })} inputMode="numeric" />
        </Field>
      ) : null}
      {value.mode === 'lbt' ? (
        <>
          <Field label={t('thesis.newRun.resource.lbtBackoff')} hint={t('thesis.newRun.resource.lbtBackoffHint')}>
            <Input value={String(value.lbt_backoff_s ?? 0.05)} onChange={(e) => set({ lbt_backoff_s: num(e.target.value, 0.05) })} inputMode="decimal" />
          </Field>
          <Field label={t('thesis.newRun.resource.lbtMaxOn')} hint={t('thesis.newRun.resource.lbtDwellHint')}>
            <Input value={String(value.lbt_max_on_s ?? 4)} onChange={(e) => set({ lbt_max_on_s: num(e.target.value, 4) })} inputMode="decimal" />
          </Field>
          <Field label={t('thesis.newRun.resource.lbtPause')} hint={t('thesis.newRun.resource.lbtDwellHint')}>
            <Input value={String(value.lbt_pause_s ?? 0.1)} onChange={(e) => set({ lbt_pause_s: num(e.target.value, 0.1) })} inputMode="decimal" />
          </Field>
        </>
      ) : null}
      {coordinated ? (
        <>
          <Toggle
            checked={linkBudget}
            onChange={(on) => set({ conflict_distance_m: on ? null : 60 })}
            label={t('thesis.newRun.resource.linkBudget')}
            hint={t('thesis.newRun.resource.linkBudgetHint')}
          />
          {!linkBudget ? (
            <Field label={t('thesis.newRun.resource.conflictDistance')}>
              <Input
                value={String(value.conflict_distance_m ?? '')}
                onChange={(e) => set({ conflict_distance_m: num(e.target.value, 60) })}
                inputMode="decimal"
              />
            </Field>
          ) : null}
          {value.mode !== 'lbt' ? (
            <Field label={t('thesis.newRun.resource.nColors')} hint={t('thesis.newRun.resource.nColorsHint')}>
              <Input
                value={value.n_colors == null ? '' : String(value.n_colors)}
                onChange={(e) => set({ n_colors: numOrNull(e.target.value) })}
                placeholder={t('thesis.newRun.resource.auto')}
                inputMode="numeric"
              />
            </Field>
          ) : null}
        </>
      ) : null}
      <Toggle
        checked={value.interference ?? true}
        onChange={(interference) => set({ interference })}
        label={t('thesis.newRun.resource.interference')}
        hint={t('thesis.newRun.resource.interferenceHint')}
      />
      {value.interference ?? true ? (
        <>
          <Toggle
            checked={value.cross_msg1 ?? true}
            onChange={(cross_msg1) => set({ cross_msg1 })}
            label={t('thesis.newRun.resource.crossMsg1')}
            hint={t('thesis.newRun.resource.crossMsg1Hint')}
          />
          <Field label={t('thesis.newRun.resource.r2dSir')}>
            <Input value={String(value.r2d_sir_db ?? 6)} onChange={(e) => set({ r2d_sir_db: num(e.target.value, 6) })} inputMode="decimal" />
          </Field>
          <Field label={t('thesis.newRun.resource.d2rSinr')}>
            <Input value={String(value.d2r_sinr_db ?? 0.5)} onChange={(e) => set({ d2r_sinr_db: num(e.target.value, 0.5) })} inputMode="decimal" />
          </Field>
          <Field label={t('thesis.newRun.resource.cwSuppression')} hint={t('thesis.newRun.resource.cwSuppressionHint')} wide>
            <Input
              value={String(value.other_cw_suppression_db ?? 61)}
              onChange={(e) => set({ other_cw_suppression_db: num(e.target.value, 61) })}
              inputMode="decimal"
            />
          </Field>
        </>
      ) : null}
    </Section>
  )
}

// ------------------------------------------------------------------ termination

export function TerminationSection({ value, onChange }: { value: TerminationSpec; onChange: (v: TerminationSpec) => void }) {
  const { t } = useTranslation()
  return (
    <Section title={t('thesis.newRun.termination.title')} hint={t('thesis.newRun.termination.hint')}>
      <TerminationEditor value={value} onChange={onChange} allowCombined />
      <p className="col-span-2 font-mono text-[10px] text-muted-foreground">{terminationLabel(value)}</p>
    </Section>
  )
}

export function TerminationEditor({
  value,
  onChange,
  allowCombined,
  onRemove,
}: {
  value: TerminationSpec
  onChange: (v: TerminationSpec) => void
  allowCombined: boolean
  onRemove?: () => void
}) {
  const { t } = useTranslation()
  const set = (patch: Partial<TerminationSpec>) => onChange({ ...value, ...patch })
  const kinds = TERMINATION_KINDS.filter((k) => allowCombined || (k !== 'combined' && k !== 'oracle'))
  const kindLabel = (k: TerminationKind) => t(`thesis.newRun.termination.kinds.${k}`)
  return (
    <>
      <Field label={t('thesis.newRun.termination.kind')} wide={!onRemove}>
        <Choice value={value.kind} options={kinds.map((k) => [k, kindLabel(k)])} label={kindLabel} onChange={(k) => onChange(defaultTermination(k))} />
      </Field>
      {onRemove ? (
        <div className="flex items-end">
          <Button type="button" size="sm" variant="outline" onClick={onRemove}>
            {t('thesis.newRun.termination.remove')}
          </Button>
        </div>
      ) : null}
      <p className="col-span-2 text-[11px] text-muted-foreground">{t(`thesis.newRun.termination.desc.${value.kind}`)}</p>
      {value.kind === 'quiet_rounds' ? (
        <Field label={t('thesis.newRun.termination.quietRounds')}>
          <Input value={String(value.quiet_rounds ?? 10)} onChange={(e) => set({ quiet_rounds: Math.max(1, Math.round(num(e.target.value, 10))) })} inputMode="numeric" />
        </Field>
      ) : null}
      {value.kind === 'id_rate' ? (
        <>
          <Field label={t('thesis.newRun.termination.windowMode')}>
            <Choice
              value={value.window_mode ?? 'rounds'}
              options={(['rounds', 'seconds', 'ewma'] as const).map((m) => [m, t(`thesis.newRun.termination.windowModes.${m}`)])}
              label={(m) => t(`thesis.newRun.termination.windowModes.${m}`)}
              onChange={(window_mode) => set({ window_mode })}
            />
          </Field>
          {value.window_mode === 'ewma' ? (
            <Field label={t('thesis.newRun.termination.ewmaAlpha')}>
              <Input value={String(value.ewma_alpha ?? 0.1)} onChange={(e) => set({ ewma_alpha: num(e.target.value, 0.1) })} inputMode="decimal" />
            </Field>
          ) : (
            <Field label={t(value.window_mode === 'seconds' ? 'thesis.newRun.termination.windowS' : 'thesis.newRun.termination.windowRounds')}>
              <Input value={String(value.window ?? 20)} onChange={(e) => set({ window: num(e.target.value, 20) })} inputMode="decimal" />
            </Field>
          )}
          <Field label={t('thesis.newRun.termination.rMin')} hint={t('thesis.newRun.termination.rMinHint')}>
            <Input value={value.r_min == null ? '' : String(value.r_min)} onChange={(e) => set({ r_min: numOrNull(e.target.value) })} placeholder="—" inputMode="decimal" />
          </Field>
          <Field label={t('thesis.newRun.termination.rRel')} hint={t('thesis.newRun.termination.rRelHint')}>
            <Input value={value.r_rel == null ? '' : String(value.r_rel)} onChange={(e) => set({ r_rel: numOrNull(e.target.value) })} placeholder="—" inputMode="decimal" />
          </Field>
          <Field label={t('thesis.newRun.termination.minFrames')}>
            <Input value={String(value.min_frames ?? 5)} onChange={(e) => set({ min_frames: Math.max(0, Math.round(num(e.target.value, 5))) })} inputMode="numeric" />
          </Field>
        </>
      ) : null}
      {value.kind === 'energy_bound' ? (
        <>
          <Field label={t('thesis.newRun.termination.energySource')} hint={t('thesis.newRun.termination.energySourceHint')}>
            <Choice
              value={value.energy_source ?? 'edge'}
              options={(['edge', 'actual'] as const).map((m) => [m, t(`thesis.newRun.termination.energySources.${m}`)])}
              label={(m) => t(`thesis.newRun.termination.energySources.${m}`)}
              onChange={(energy_source) => set({ energy_source })}
            />
          </Field>
          <Field label={t('thesis.newRun.termination.margin')} hint={t('thesis.newRun.termination.marginHint')}>
            <Input value={String(value.margin ?? 0)} onChange={(e) => set({ margin: Math.max(0, num(e.target.value, 0)) })} inputMode="decimal" />
          </Field>
        </>
      ) : null}
      {value.kind === 'combined' ? (
        <>
          <Field label={t('thesis.newRun.termination.combine')} wide>
            <Choice
              value={value.combine ?? 'all'}
              options={(['all', 'any'] as const).map((m) => [m, t(`thesis.newRun.termination.combineModes.${m}`)])}
              label={(m) => t(`thesis.newRun.termination.combineModes.${m}`)}
              onChange={(combine) => set({ combine })}
            />
          </Field>
          {(value.rules ?? []).map((rule, i) => (
            <div key={i} className="col-span-2 grid grid-cols-2 gap-2 rounded border border-dashed p-2">
              <TerminationEditor
                value={rule}
                allowCombined={false}
                onChange={(next) => set({ rules: (value.rules ?? []).map((r, j) => (j === i ? next : r)) })}
                onRemove={(value.rules ?? []).length > 1 ? () => set({ rules: (value.rules ?? []).filter((_, j) => j !== i) }) : undefined}
              />
            </div>
          ))}
          {(value.rules ?? []).length < 4 ? (
            <div className="col-span-2">
              <Button type="button" size="sm" variant="outline" onClick={() => set({ rules: [...(value.rules ?? []), defaultTermination('id_rate')] })}>
                {t('thesis.newRun.termination.addRule')}
              </Button>
            </div>
          ) : null}
        </>
      ) : null}
    </>
  )
}
