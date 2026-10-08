import { MathText } from '@/components/MathText'
import { FieldLabel, ParamHint } from '@/components/ParamHint'
import { Segmented } from '@/components/aperiodic/Segmented'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { curvesFor, PAPER_FIGURES, type PaperCurve, type PaperFigure } from '@/components/aperiodic/paperPresets'
import type { AperiodicSimulateRequest, ControllerName, PpoStatus } from '@/types/aperiodicSimulation'
import { cn } from '@/lib/utils'
import { ChevronDownIcon, DicesIcon } from 'lucide-react'
import { useState } from 'react'
import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'

const L_PRESETS = [1, 8, 16, 32]

interface Props {
  request: AperiodicSimulateRequest
  setRequest: (r: AperiodicSimulateRequest) => void
  busy: boolean
  backendUp: boolean | null
  ppo: PpoStatus | null
  lmax: number
  onRun: () => void
  paperFig: PaperFigure
  setPaperFig: (f: PaperFigure) => void
  paperCurve: PaperCurve
  setPaperCurve: (c: PaperCurve) => void
  onPaper: (run: boolean) => void
}

function PaperConfigSection({
  fig,
  setFig,
  curve,
  setCurve,
  onPaper,
  busy,
  ppo,
}: {
  fig: PaperFigure
  setFig: (f: PaperFigure) => void
  curve: PaperCurve
  setCurve: (c: PaperCurve) => void
  onPaper: (run: boolean) => void
  busy: boolean
  ppo: PpoStatus | null
}) {
  const { t } = useTranslation()
  const rlBlocked = curve === 'recurrent_ppo' && !(ppo?.available && ppo.alphas.includes(0.5))
  const [open, setOpen] = useState(() => localStorage.getItem(PAPER_OPEN_KEY) !== '0')
  const toggle = () =>
    setOpen((v) => {
      localStorage.setItem(PAPER_OPEN_KEY, v ? '0' : '1')
      return !v
    })
  const useButtons = (
    <div className="grid grid-cols-2 gap-2">
      <Button variant="outline" size="sm" disabled={busy} onClick={() => onPaper(false)}>
        {t('ap.paperConfig.apply')}
      </Button>
      <Button size="sm" disabled={busy || rlBlocked} onClick={() => onPaper(true)}>
        {busy ? t('ap.common.running') : t('ap.paperConfig.applyRun')}
      </Button>
    </div>
  )
  return (
    <Section
      title={
        <button
          type="button"
          onClick={toggle}
          aria-expanded={open}
          className="flex items-center gap-1 rounded-sm uppercase outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring/50"
        >
          <ChevronDownIcon className={cn('size-3.5 transition-transform', !open && '-rotate-90')} aria-hidden />
          {t('ap.paperConfig.title')}
        </button>
      }
    >
      {!open ? (
        <>
          <p className="text-xs text-muted-foreground">
            <MathText text={t('ap.paperConfig.collapsed', { fig: t(`ap.paperRef.${fig}.label`), curve: t(`ap.paperConfig.curves.${curve}`) })} />
          </p>
          {useButtons}
        </>
      ) : (
        <>
          <div className="grid gap-1">
            <FieldLabel hint={t('ap.paperConfig.hint')}>{t('ap.paperConfig.figure')}</FieldLabel>
            <Segmented
              value={fig}
              onChange={(f) => {
                setFig(f)
                if (!curvesFor(f).includes(curve)) setCurve(curvesFor(f)[0])
              }}
              options={PAPER_FIGURES.map((f) => ({ value: f, label: t(`ap.paperRef.${f}.label`), hint: t(`ap.help.fig.${f}`) }))}
            />
          </div>
          <div className="grid gap-1">
            <FieldLabel hint={t('ap.paperConfig.curveHint')}>{t('ap.paperConfig.curve')}</FieldLabel>
            <Segmented
              value={curve}
              onChange={setCurve}
              options={curvesFor(fig).map((c) => ({ value: c, label: t(`ap.paperConfig.curves.${c}`), hint: curveHint(t, c) }))}
            />
          </div>
          <p className="text-[11px] leading-snug text-muted-foreground">
            <MathText text={t(`ap.paperConfig.setup.${fig}`)} />
          </p>
          <SymbolsBlock />
          {rlBlocked && <p className="text-[11px] text-amber-700 dark:text-amber-300">{t('ap.ppo.missing')}</p>}
          {useButtons}
        </>
      )}
    </Section>
  )
}

const PAPER_OPEN_KEY = 'ap.paperConfig.open'

function curveHint(t: TFunction, c: PaperCurve): string {
  const base = c.replace(/_wo_depletion$/, '')
  const text = t(`ap.help.curve.${base}`)
  return base === c ? text : `${text}\n\n${t('ap.help.symbols.dep')}`
}

const SYMBOLS = ['N_tot', 'N_g', 'L_s', 'p_s', 'F', 'E', 'alpha', 'pfsa', 'dep'] as const

function SymbolsBlock() {
  const { t } = useTranslation()
  return (
    <details className="rounded-md border bg-muted/30 px-2 py-1 text-[11px] leading-snug" open>
      <summary className="cursor-pointer select-none font-medium text-muted-foreground">{t('ap.help.symbols.title')}</summary>
      <ul className="mt-1 grid gap-1">
        {SYMBOLS.map((s) => (
          <li key={s}>
            <MathText text={t(`ap.help.symbols.${s}`)} />
          </li>
        ))}
      </ul>
    </details>
  )
}

function Section({ title, children }: { title: React.ReactNode; children: React.ReactNode }) {
  return (
    <fieldset className="grid gap-2 rounded-lg border border-border/60 p-2.5">
      <legend className="px-1 text-[11px] font-medium tracking-wider text-muted-foreground uppercase">{title}</legend>
      {children}
    </fieldset>
  )
}

export function AperiodicControls({
  request: r,
  setRequest,
  busy,
  backendUp,
  ppo,
  lmax,
  onRun,
  paperFig,
  setPaperFig,
  paperCurve,
  setPaperCurve,
  onPaper,
}: Props) {
  const { t } = useTranslation()
  const [advanced, setAdvanced] = useState(false)
  const patch = (p: Partial<AperiodicSimulateRequest>) => setRequest({ ...r, ...p })
  const ppoOn = r.ppo_enabled
  const ppoAvailable = ppo?.available === true
  const customL = !L_PRESETS.includes(r.L_fixed)

  return (
    <Card plain size="sm">
      <CardHeader>
        <CardTitle>{t('ap.controls.title')}</CardTitle>
        <CardAction>
          <Badge variant={backendUp ? 'default' : 'destructive'}>
            {backendUp == null ? t('ap.common.checking') : backendUp ? t('ap.common.apiUp') : t('ap.common.apiDown')}
          </Badge>
        </CardAction>
        <CardDescription>{t('ap.controls.description')}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        <PaperConfigSection
          fig={paperFig}
          setFig={setPaperFig}
          curve={paperCurve}
          setCurve={setPaperCurve}
          onPaper={onPaper}
          busy={busy}
          ppo={ppo}
        />
        <Section title={t('ap.controls.scenario')}>
          <div className="grid grid-cols-2 gap-2">
            <div className="grid gap-1">
              <FieldLabel htmlFor="ap-n" hint={t('ap.hints.nTot')}>{t('ap.controls.nTot')}</FieldLabel>
              <Input
                id="ap-n"
                type="number"
                min={10}
                max={15000}
                value={r.num_devices}
                onChange={(e) => patch({ num_devices: Number(e.target.value) })}
              />
            </div>
            <div className="grid gap-1">
              <FieldLabel htmlFor="ap-seed" hint={t('ap.hints.seed')}>
                {t('ap.controls.seed')}
              </FieldLabel>
              <div className="flex gap-1">
                <Input id="ap-seed" type="number" min={0} value={r.seed} onChange={(e) => patch({ seed: Number(e.target.value) })} />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  aria-label={t('ap.controls.reshuffle')}
                  onClick={() => patch({ seed: Math.floor(Math.random() * 1_000_000) })}
                >
                  <DicesIcon />
                </Button>
              </div>
            </div>
          </div>
          <div className="grid gap-1">
            <FieldLabel hint={t('ap.hints.runtime')}>{t('ap.controls.runtime')}</FieldLabel>
            <Segmented
              value={r.runtime_mode}
              onChange={(v) => patch({ runtime_mode: v })}
              options={[
                { value: 'interactive', label: t('ap.controls.interactive') },
                { value: 'paper_batch', label: t('ap.controls.paperBatch') },
              ]}
            />
          </div>
          {r.runtime_mode === 'paper_batch' && (
            <div className="grid gap-1">
              <FieldLabel htmlFor="ap-ep" hint={t('ap.hints.episodes')}>
                {t('ap.controls.episodes')}
              </FieldLabel>
              <Input
                id="ap-ep"
                type="number"
                min={1}
                max={100}
                value={r.num_episodes}
                onChange={(e) => patch({ num_episodes: Number(e.target.value) })}
              />
            </div>
          )}
          <div className="grid gap-1">
            <FieldLabel hint={t('ap.hints.harvesting')}>{t('ap.controls.harvesting')}</FieldLabel>
            <Segmented
              value={r.harvesting_scenario}
              onChange={(v) => patch({ harvesting_scenario: v })}
              options={[
                { value: 'single_source', label: t('ap.terms.singleSource') },
                { value: 'multi_source', label: t('ap.terms.multiSource') },
              ]}
            />
          </div>
          <div className="grid gap-1">
            <FieldLabel hint={t('ap.hints.typeMix')}>{t('ap.controls.typeMix')}</FieldLabel>
            <Segmented
              value={r.type_mix}
              onChange={(v) => patch({ type_mix: v })}
              options={[
                { value: 'mixed', label: t('ap.controls.mixed') },
                { value: '1', label: t('ap.terms.type1') },
                { value: '2a', label: t('ap.terms.type2a') },
                { value: '2b', label: t('ap.terms.type2b') },
              ]}
            />
          </div>
        </Section>

        <Section title={t('ap.controls.protocol')}>
          <Segmented
            value={r.paging_mode}
            disabled={ppoOn || r.controller === 'dfsa_schoute' || r.controller === 'cmebe'}
            onChange={(v) => patch({ paging_mode: v })}
            options={[
              { value: 'aperiodic', label: t('ap.terms.aperiodic') },
              { value: 'periodic', label: t('ap.terms.periodicBaseline') },
            ]}
          />
          {r.paging_mode === 'periodic' && (
            <>
              <div className="grid gap-1">
                <FieldLabel hint={t('ap.hints.ng')}>{t('ap.controls.ng')}</FieldLabel>
                <Segmented value={r.N_g} onChange={(v) => patch({ N_g: v })} options={[1, 2, 4, 8].map((n) => ({ value: n, label: String(n) }))} />
              </div>
              <label className="flex items-center justify-between gap-2 text-sm">
                <span className="flex items-center gap-1">
                  {t('ap.controls.depletion')}
                  <ParamHint text={t('ap.hints.depletion')} title={t('ap.controls.depletion')} />
                </span>
                <Switch
                  checked={r.enforce_midround_depletion}
                  onCheckedChange={(v) => patch({ enforce_midround_depletion: v })}
                />
              </label>
            </>
          )}
        </Section>

        <Section title={t('ap.controls.resources')}>
          <div className="flex items-center justify-between gap-2 rounded-md bg-muted/50 px-2 py-1.5">
            <span className="flex items-center gap-1 text-sm font-medium">
              {t('ap.terms.recurrentPpo')}
              <ParamHint text={t('ap.hints.ppo')} title={t('ap.terms.recurrentPpo')} />
            </span>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">{ppoOn ? t('ap.controls.on') : t('ap.controls.off')}</span>
              <Switch
                checked={ppoOn}
                disabled={!ppoAvailable && !ppoOn}
                onCheckedChange={(v) => patch({ ppo_enabled: v })}
                aria-label={t('ap.terms.recurrentPpo')}
              />
            </div>
          </div>
          {!ppoAvailable && (
            <p className="rounded-md border border-amber-500/40 bg-amber-500/10 px-2 py-1 text-[11px] text-amber-700 dark:text-amber-300">
              {t('ap.ppo.missing')} <code className="font-mono">{ppo?.train_command ?? 'python backend/scripts/aperiodic/train_ppo/train_ppo.py --steps 1000000 --seed 42'}</code>
            </p>
          )}
          {ppoOn ? (
            <div className="grid gap-1 text-xs">
              <p>
                <MathText text={t('ap.controls.lAdaptivePpo')} />
              </p>
              <p>
                <MathText text={t('ap.controls.pAdaptivePpo')} />
              </p>
              <p className="text-muted-foreground">
                L<sub>max</sub> = {lmax}
              </p>
              <div className="grid gap-1">
                <FieldLabel htmlFor="ap-l1" hint={t('ap.hints.lInitial')}>
                  {t('ap.controls.lInitial')}
                </FieldLabel>
                <Segmented value={r.L_initial} onChange={(v) => patch({ L_initial: v })} options={[1, 2, 4, 8, 16, 32].map((n) => ({ value: n, label: String(n) }))} />
              </div>
            </div>
          ) : (
            <>
              <div className="grid gap-1">
                <FieldLabel hint={t('ap.hints.controller')}>{t('ap.controls.controller')}</FieldLabel>
                <Segmented<ControllerName>
                  value={r.controller}
                  onChange={(v) => patch({ controller: v })}
                  options={[
                    { value: 'pfsa_pze', label: t('ap.terms.pfsaPze') },
                    ...(advanced || r.controller !== 'pfsa_pze'
                      ? [
                          { value: 'dfsa_schoute' as const, label: t('ap.terms.dfsaSchoute') },
                          { value: 'cmebe' as const, label: t('ap.terms.cmebe') },
                        ]
                      : []),
                  ]}
                />
              </div>
              {r.controller === 'pfsa_pze' ? (
                <div className="grid gap-1">
                  <FieldLabel hint={t('ap.hints.lFixed', { lmax })}>{t('ap.controls.lFixed')}</FieldLabel>
                  <div className="flex items-center gap-1">
                    <Segmented
                      value={customL ? -1 : r.L_fixed}
                      onChange={(v) => v > 0 && patch({ L_fixed: v })}
                      options={[...L_PRESETS.map((n) => ({ value: n, label: String(n) })), { value: -1, label: t('ap.controls.custom') }]}
                    />
                    <Input
                      className="w-16"
                      type="number"
                      min={1}
                      max={lmax}
                      value={r.L_fixed}
                      aria-label={t('ap.controls.lFixed')}
                      onChange={(e) => patch({ L_fixed: Math.min(lmax, Math.max(1, Number(e.target.value))) })}
                    />
                  </div>
                </div>
              ) : (
                <div className="grid gap-1">
                  <FieldLabel hint={t('ap.hints.lInitial')}>{t('ap.controls.lInitial')}</FieldLabel>
                  <Segmented value={r.L_initial} onChange={(v) => patch({ L_initial: v })} options={[1, 2, 4, 8, 16, 32].map((n) => ({ value: n, label: String(n) }))} />
                </div>
              )}
            </>
          )}
          {(ppoOn || advanced) && (
            <div className="grid gap-1">
              <FieldLabel htmlFor="ap-alpha" hint={t('ap.hints.alpha')}>{t('ap.controls.alpha')}</FieldLabel>
              <Segmented
                value={r.alpha}
                onChange={(v) => patch({ alpha: v })}
                options={[0, 0.25, 0.5, 0.75].map((a) => ({
                  value: a,
                  label: a.toFixed(2),
                  disabled: ppoOn && !!ppo && !ppo.alphas.includes(a),
                }))}
              />
            </div>
          )}
        </Section>

        <label className="flex items-center justify-between text-sm">
          <span>{t('ap.controls.advanced')}</span>
          <Switch checked={advanced} onCheckedChange={setAdvanced} />
        </label>
        {advanced && (
          <Section title={t('ap.controls.physical')}>
            <div className="grid grid-cols-2 gap-2">
              {(
                [
                  ['F', 'ap-f', 1, 32, 1],
                  ['capture_ratio_db', 'ap-cap', 0, 30, 0.5],
                  ['missed_detection_rate', 'ap-md', 0, 0.5, 0.001],
                  ['false_alarm_rate', 'ap-fa', 0, 0.5, 0.0001],
                  ['max_time_s', 'ap-tmax', 1, 3600, 10],
                ] as const
              ).map(([key, id, min, max, step]) => (
                <div key={key} className="grid gap-1">
                  <FieldLabel htmlFor={id} hint={t(`ap.hints.${key}`)}>
                    {t(`ap.controls.${key}`)}
                  </FieldLabel>
                  <Input
                    id={id}
                    type="number"
                    min={min}
                    max={max}
                    step={step}
                    value={r[key]}
                    onChange={(e) => patch({ [key]: Number(e.target.value) } as Partial<AperiodicSimulateRequest>)}
                  />
                </div>
              ))}
            </div>
            <label className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-1">
                {t('ap.controls.impairments')}
                <ParamHint text={t('ap.hints.impairments')} title={t('ap.controls.impairments')} />
              </span>
              <Switch checked={r.impairments_enabled} onCheckedChange={(v) => patch({ impairments_enabled: v })} />
            </label>
            <p className="text-[11px] text-muted-foreground">{t('ap.controls.eiAlways')}</p>
          </Section>
        )}
      </CardContent>
      <CardFooter>
        <Button className="w-full" disabled={busy || (ppoOn && !ppoAvailable)} onClick={onRun}>
          {busy ? t('ap.common.running') : t('ap.controls.run')}
        </Button>
      </CardFooter>
    </Card>
  )
}
