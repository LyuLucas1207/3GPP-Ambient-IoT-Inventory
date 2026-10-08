import { cn } from '@/lib/utils'
import type { StepRound } from '@/types/aperiodicSimulation'
import { useTranslation } from 'react-i18next'
import { PHASE_BLOCK, type StepPhase } from './stepModel'

// One CBRA round as in paper Fig. 2(b): frequency on the vertical axis, the
// message sequence along time. Blocks are revealed as the step advances and
// every resource cell names the device(s) using it.

const PHYS = ['idle', 'single', 'captured', 'collision'] as const
const PHYS_CLS = [
  'bg-muted text-muted-foreground',
  'bg-emerald-500/85 text-white',
  'bg-sky-500/85 text-white',
  'bg-red-500/85 text-white',
]
const CELL_W = 30
const CELL_H = 18
const MAX_LABEL_COLS = 40
const MAX_MSG2_COLS = 64

interface Props {
  r: StepRound
  phase: StepPhase
  selectedId: number | null
  onSelect: (id: number) => void
}

function ids(list: number[]) {
  if (list.length === 0) return ''
  if (list.length <= 2) return list.join(',')
  return `${list[0]},+${list.length - 1}`
}

function Block({
  title,
  ms,
  shown,
  current,
  children,
  note,
}: {
  title: string
  ms: number
  shown: boolean
  current: boolean
  children: React.ReactNode
  note?: string
}) {
  const { t } = useTranslation()
  return (
    <div className="flex shrink-0 flex-col items-stretch">
      <div
        className={cn(
          'rounded-sm border p-0.5 transition-opacity',
          current ? 'border-fuchsia-500 ring-2 ring-fuchsia-500/60' : 'border-border/70',
          !shown && 'border-dashed opacity-30',
        )}
      >
        {shown ? children : <div className="grid place-items-center text-[10px] text-muted-foreground" style={{ minWidth: 48 }}>{children}</div>}
      </div>
      <div className="mt-0.5 text-center leading-tight">
        <div className="text-[11px] font-medium">{title}</div>
        <div className="font-mono text-[10px] text-muted-foreground">{ms.toFixed(ms < 10 ? 1 : 0)} ms</div>
        {note && <div className="text-[10px] text-muted-foreground">{shown ? note : t('ap.step.pending')}</div>}
      </div>
    </div>
  )
}

export function StepTfMap({ r, phase, selectedId, onSelect }: Props) {
  const { t } = useTranslation()
  const F = r.F
  const upto = PHASE_BLOCK[phase]
  const c = r.components_s
  const rows = Array.from({ length: F }, (_, i) => F - 1 - i)
  const labels = r.L <= MAX_LABEL_COLS
  const msg2ByAo = new Map(r.msg2.map((m) => [m.ao, m.index]))
  const kAlloc = Math.max(0, Math.floor(r.counts.k_alloc + 1e-9))
  const msg2Cols = Math.min(kAlloc, MAX_MSG2_COLS)
  const msg3Cols = Math.max(Math.ceil(kAlloc / F - 1e-9), 0)
  const msg3By = new Map(r.msg3.map((m) => [m.index, m]))
  const h = F * (CELL_H + 1) + 2

  const cellBtn = (key: string, cls: string, label: string, title: string, devs: number[], extra?: string) => (
    <button
      key={key}
      type="button"
      title={title}
      onClick={() => devs[0] != null && onSelect(devs[0])}
      className={cn(
        'truncate rounded-[2px] px-0.5 font-mono text-[9px] leading-[18px]',
        cls,
        selectedId != null && devs.includes(selectedId) && 'outline-2 outline-offset-[-2px] outline-fuchsia-500',
        extra,
      )}
      style={{ width: CELL_W, height: CELL_H }}
    >
      {label}
    </button>
  )

  return (
    <div className="grid gap-1" aria-label={t('ap.tf.aria')}>
      <div className="flex items-start gap-1.5 overflow-x-auto pb-1">
        <div className="flex shrink-0 items-start gap-0.5">
          <span className="rotate-180 self-center text-[10px] text-muted-foreground [writing-mode:vertical-rl]">
            {t('ap.tf.freqAxis', { F })} ↑
          </span>
          <div className="flex flex-col justify-between py-[3px] font-mono text-[9px] leading-none text-muted-foreground" style={{ height: h }}>
            {rows.map((f) => (
              <span key={f}>f{f + 1}</span>
            ))}
          </div>
        </div>

        <Block title={t('ap.cbra.paging')} ms={c.paging_s * 1e3} shown={upto >= 0} current={upto === 0}>
          <div className="grid place-items-center rounded-[2px] bg-sky-500/70 px-1 text-[10px] text-white" style={{ height: h - 2, minWidth: 44 }}>
            {upto >= 0 ? t('ap.step.pagedN', { n: r.counts.paged }) : '…'}
          </div>
        </Block>

        <Block
          title={`Msg1 · L_s=${r.L}`}
          ms={c.msg1_s * 1e3}
          shown={upto >= 1}
          current={upto === 1}
          note={t('ap.tf.msg1Grid', { L: r.L, F, n: r.L * F })}
        >
          {upto >= 1 ? (
            <div className="grid gap-px" style={{ gridTemplateColumns: `repeat(${r.L}, ${labels ? CELL_W : 8}px)` }}>
              {rows.flatMap((f) =>
                Array.from({ length: r.L }, (_, l) => {
                  const ao = l * F + f
                  const ph = r.ao.physical[ao]
                  const ob = r.ao.observed[ao]
                  const devs = r.ao.devices[ao]
                  const mismatch = (ph === 0 && ob !== 0) || (ph !== 0 && ob === 0)
                  const flag = upto >= 2 && msg2ByAo.has(ao)
                  const title = `AO (t=${l + 1}, f=${f + 1}) · ${devs.length ? `dev ${devs.join(', ')}` : t('ap.cbra.phys.idle')} · ${t(`ap.cbra.phys.${PHYS[ph]}`)} → ${t(`ap.cbra.obs.${['idle', 'success', 'collision'][ob]}`)}${flag ? ` · EI ✓ Msg2 #${msg2ByAo.get(ao)! + 1}` : ''}`
                  if (!labels)
                    return (
                      <span
                        key={ao}
                        title={title}
                        className={cn('rounded-[1px]', PHYS_CLS[ph], mismatch && 'ring-2 ring-fuchsia-500 ring-inset')}
                        style={{ height: CELL_H }}
                      />
                    )
                  return cellBtn(
                    String(ao),
                    PHYS_CLS[ph],
                    `${flag ? '✓' : ''}${ids(devs)}`,
                    title,
                    devs,
                    mismatch ? 'ring-2 ring-fuchsia-500 ring-inset' : undefined,
                  )
                }),
              )}
            </div>
          ) : (
            '…'
          )}
        </Block>

        <Block title={t('ap.cbra.ei')} ms={c.ei_s * 1e3} shown={upto >= 2} current={upto === 2} note={upto >= 2 ? t('ap.step.eiFlags', { n: r.msg2.length }) : undefined}>
          <div className="grid place-items-center rounded-[2px] bg-violet-500/60 px-1 text-[10px] text-white" style={{ height: h - 2, minWidth: 36 }}>
            {upto >= 2 ? `K=${r.counts.k_decoded}` : '…'}
          </div>
        </Block>

        <Block
          title="Msg2"
          ms={c.msg2_s * 1e3}
          shown={upto >= 3}
          current={upto === 3}
          note={`${t('ap.tf.msg2Freq')}${kAlloc > msg2Cols ? ` · +${kAlloc - msg2Cols}` : ''}`}
        >
          {upto >= 3 ? (
            kAlloc === 0 ? (
              <div className="grid place-items-center text-[10px] text-muted-foreground" style={{ height: h - 2, minWidth: 40 }}>
                K = 0
              </div>
            ) : (
              <div className="grid gap-px" style={{ gridTemplateColumns: `repeat(${msg2Cols}, ${CELL_W}px)` }}>
                {rows.flatMap((f) =>
                  Array.from({ length: msg2Cols }, (_, i) => {
                    if (f !== 0) return <span key={`${f}-${i}`} style={{ height: CELL_H }} />
                    const m = r.msg2[i]
                    if (!m) return cellBtn(`m2-${i}`, 'bg-amber-400/80 text-amber-950', '—', t('ap.cbra.wasted'), [])
                    return cellBtn(`m2-${i}`, 'bg-emerald-500/85 text-white', String(m.device), `Msg2 #${i + 1} → dev ${m.device} (AO ${m.ao})`, [m.device])
                  }),
                )}
              </div>
            )
          ) : (
            '…'
          )}
        </Block>

        <Block title="Msg3" ms={c.msg3_s * 1e3} shown={upto >= 4} current={upto === 4} note={t('ap.tf.msg3Freq')}>
          {upto >= 4 ? (
            msg3Cols === 0 ? (
              <div className="grid place-items-center text-[10px] text-muted-foreground" style={{ height: h - 2, minWidth: 40 }}>
                —
              </div>
            ) : (
              <div className="grid gap-px" style={{ gridTemplateColumns: `repeat(${msg3Cols}, ${CELL_W}px)` }}>
                {rows.flatMap((f) =>
                  Array.from({ length: msg3Cols }, (_, j) => {
                    const idx = j * F + f
                    const m = msg3By.get(idx)
                    if (idx >= kAlloc) return <span key={`${f}-${j}`} style={{ height: CELL_H }} />
                    if (!m) return cellBtn(`m3-${idx}`, 'bg-amber-400/80 text-amber-950', '—', t('ap.cbra.wasted'), [])
                    return cellBtn(
                      `m3-${idx}`,
                      m.identified ? 'bg-emerald-500/85 text-white' : 'bg-red-500/70 text-white',
                      String(m.device),
                      `Msg3 slot ${j + 1}, f${f + 1} → dev ${m.device} ${m.identified ? `· ${t('ap.cbra.identifiedOne')}` : `· ${t('ap.tf.msg3Lost')}`}`,
                      [m.device],
                    )
                  }),
                )}
              </div>
            )
          ) : (
            '…'
          )}
        </Block>
      </div>
      <div className="flex items-center gap-2 pl-8 text-[10px] text-muted-foreground">
        <span className="h-px flex-1 bg-border" />
        <span>{t('ap.tf.timeAxis')} →</span>
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
        {PHYS.map((p, k) => (
          <span key={p} className="flex items-center gap-1">
            <span className={cn('size-2.5 rounded-[1px]', PHYS_CLS[k])} /> Msg1 {t(`ap.cbra.phys.${p}`)}
          </span>
        ))}
        <span className="flex items-center gap-1">
          <span className="size-2.5 rounded-[1px] ring-2 ring-fuchsia-500 ring-inset" /> {t('ap.cbra.mismatch')}
        </span>
        <span className="flex items-center gap-1">✓ {t('ap.step.eiLegend')}</span>
        <span className="flex items-center gap-1">
          <span className="size-2.5 rounded-[1px] bg-amber-400/80" /> {t('ap.cbra.wasted')}
        </span>
        <span className="flex items-center gap-1">
          <span className="size-2.5 rounded-[1px] bg-red-500/70" /> {t('ap.tf.msg3Lost')}
        </span>
      </div>
    </div>
  )
}
