import type { CbraInspectRound } from '@/types/aperiodicSimulation'
import { useTranslation } from 'react-i18next'

// One CBRA round drawn like the paper's Fig. 1(b)/2(b): frequency resources on
// the vertical axis, the round's message sequence along the time axis.

const PHYS = ['idle', 'single', 'captured', 'collision'] as const
const PHYS_COLOR = ['bg-muted', 'bg-emerald-500', 'bg-sky-500', 'bg-red-500']
const OBS = ['idle', 'success', 'collision'] as const
const MAX_COLS = 160
const ROW_PX = 9

type Cell = { cls: string; title?: string; ring?: boolean } | null

interface Block {
  key: string
  label: string
  ms: number
  cols: number
  hidden: number
  span?: string
  cell?: (col: number, f: number) => Cell
  note?: string
}

function GridBlock({ b, F, toScale }: { b: Block; F: number; toScale: boolean }) {
  const grow = toScale ? Math.max(b.ms, 0.5) : Math.max(b.cols, 1)
  return (
    <div className="flex min-w-0 flex-col" style={{ flex: `${grow} 1 0`, minWidth: b.span ? 14 : Math.min(b.cols, 40) * 2 + 6 }}>
      <div className="rounded-[2px] border border-border/70 p-px" style={{ height: F * ROW_PX + 4 }}>
        {b.span ? (
          <div className={`h-full w-full rounded-[1px] ${b.span}`} />
        ) : b.cols === 0 ? (
          <div className="h-full w-full bg-[repeating-linear-gradient(45deg,transparent,transparent_3px,var(--color-border)_3px,var(--color-border)_4px)] opacity-60" />
        ) : (
          <div
            className="grid h-full gap-px"
            style={{ gridTemplateColumns: `repeat(${b.cols}, minmax(1px, 1fr))`, gridTemplateRows: `repeat(${F}, minmax(0, 1fr))` }}
          >
            {Array.from({ length: F }, (_, row) => {
              const f = F - 1 - row
              return Array.from({ length: b.cols }, (_, col) => {
                const c = b.cell!(col, f)
                return (
                  <span
                    key={`${row}-${col}`}
                    title={c?.title}
                    className={`rounded-[1px] ${c ? c.cls : ''} ${c?.ring ? 'ring-2 ring-fuchsia-500 ring-inset' : ''}`}
                  />
                )
              })
            })}
          </div>
        )}
      </div>
      <div className="mt-0.5 min-w-0 text-center leading-tight">
        <div className="truncate text-[10px] font-medium">{b.label}</div>
        <div className="truncate font-mono text-[9px] text-muted-foreground">
          {b.ms.toFixed(b.ms < 10 ? 1 : 0)} ms{b.hidden > 0 ? ` · +${b.hidden}` : ''}
        </div>
        {b.note && <div className="truncate text-[9px] text-muted-foreground">{b.note}</div>}
      </div>
    </div>
  )
}

export function TimeFrequencyMap({ r, toScale = false, compact = false }: { r: CbraInspectRound; toScale?: boolean; compact?: boolean }) {
  const { t } = useTranslation()
  const F = r.F
  const c = r.components_s
  const kAlloc = Math.max(0, Math.round(r.k_alloc))
  const msg2Cols = Math.min(kAlloc, MAX_COLS)
  const msg3Cols = Math.ceil(Math.max(r.msg3_slots, kAlloc > 0 ? kAlloc / F : 0) - 1e-9)

  const blocks: Block[] = [
    { key: 'paging', label: t('ap.cbra.paging'), ms: c.paging_s * 1e3, cols: 1, hidden: 0, span: 'bg-sky-500/70' },
    {
      key: 'msg1',
      label: `Msg1 · L=${r.L}`,
      ms: c.msg1_s * 1e3,
      cols: r.L,
      hidden: 0,
      cell: (l, f) => {
        const ao = l * F + f
        const ph = r.physical[ao]
        const ob = r.observed[ao]
        return {
          cls: PHYS_COLOR[ph],
          ring: (ph === 0 && ob !== 0) || (ph !== 0 && ob === 0),
          title: `AO (t=${l + 1}, f=${f + 1}): ${r.occupancy[ao]} dev · ${t(`ap.cbra.phys.${PHYS[ph]}`)} → ${t(`ap.cbra.obs.${OBS[ob]}`)}`,
        }
      },
    },
    { key: 'ei', label: t('ap.cbra.ei'), ms: c.ei_s * 1e3, cols: 1, hidden: 0, span: 'bg-violet-500/60' },
    {
      key: 'msg2',
      label: 'Msg2',
      ms: c.msg2_s * 1e3,
      cols: msg2Cols,
      hidden: kAlloc - msg2Cols,
      note: compact ? undefined : t('ap.tf.msg2Freq'),
      cell: (i, f) =>
        f !== 0
          ? null
          : i < r.k_served
            ? { cls: 'bg-emerald-500', title: `Msg2 #${i + 1}` }
            : { cls: 'bg-amber-400/80', title: t('ap.cbra.wasted') },
    },
    {
      key: 'msg3',
      label: 'Msg3',
      ms: c.msg3_s * 1e3,
      cols: Math.min(msg3Cols, MAX_COLS),
      hidden: Math.max(0, msg3Cols - MAX_COLS),
      note: compact ? undefined : t('ap.tf.msg3Freq'),
      cell: (col, f) => {
        const i = col * F + f
        if (i < r.identified) return { cls: 'bg-emerald-500', title: `Msg3 → ${t('ap.cbra.identifiedOne')}` }
        if (i < r.k_served) return { cls: 'bg-red-500/70', title: t('ap.tf.msg3Lost') }
        if (i < kAlloc) return { cls: 'bg-amber-400/80', title: t('ap.cbra.wasted') }
        return null
      },
    },
  ]

  const ticks = F <= 16 ? Array.from({ length: F }, (_, i) => F - i) : [F, 1]
  return (
    <div className="grid gap-1" aria-label={t('ap.tf.aria')}>
      <div className="flex items-stretch gap-1">
        <div className="flex shrink-0 items-start gap-0.5">
          <span className="text-[10px] text-muted-foreground [writing-mode:vertical-rl] rotate-180 self-center">
            {t('ap.tf.freqAxis', { F })} ↑
          </span>
          <div className="flex flex-col justify-between py-[3px] font-mono text-[8px] leading-none text-muted-foreground" style={{ height: F * ROW_PX + 4 }}>
            {ticks.map((f) => (
              <span key={f}>f{f}</span>
            ))}
          </div>
        </div>
        <div className="flex min-w-0 flex-1 gap-1">
          {blocks.map((b) => (
            <GridBlock key={b.key} b={b} F={F} toScale={toScale} />
          ))}
        </div>
      </div>
      <div className="flex items-center gap-2 pl-8 text-[10px] text-muted-foreground">
        <span className="h-px flex-1 bg-border" />
        <span>{t('ap.tf.timeAxis')} →</span>
      </div>
    </div>
  )
}

export function TimeFrequencyLegend() {
  const { t } = useTranslation()
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
      {PHYS.map((p, k) => (
        <span key={p} className="flex items-center gap-1">
          <span className={`size-2.5 rounded-[1px] ${PHYS_COLOR[k]}`} /> Msg1 {t(`ap.cbra.phys.${p}`)}
        </span>
      ))}
      <span className="flex items-center gap-1">
        <span className="size-2.5 rounded-[1px] ring-2 ring-fuchsia-500 ring-inset" /> {t('ap.cbra.mismatch')}
      </span>
      <span className="flex items-center gap-1">
        <span className="size-2.5 rounded-[1px] bg-emerald-500" /> {t('ap.tf.used')}
      </span>
      <span className="flex items-center gap-1">
        <span className="size-2.5 rounded-[1px] bg-red-500/70" /> {t('ap.tf.msg3Lost')}
      </span>
      <span className="flex items-center gap-1">
        <span className="size-2.5 rounded-[1px] bg-amber-400/80" /> {t('ap.cbra.wasted')}
      </span>
    </div>
  )
}
