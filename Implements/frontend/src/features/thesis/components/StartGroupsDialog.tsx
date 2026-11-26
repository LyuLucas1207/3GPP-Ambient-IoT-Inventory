import { Plus } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Dialog, DialogBackdrop, DialogDescription, DialogPopup, DialogPortal, DialogTitle } from '@/components/ui/dialog'

export type StartReader = { id: number; label: string; x_m: number; y_m: number }
/** reader id -> start group (0 = starts first) */
export type StartAssignment = Record<number, number>

export const GROUP_COLORS = ['#2563eb', '#d97706', '#059669', '#db2777', '#7c3aed', '#0891b2', '#65a30d', '#dc2626']
export const groupColor = (g: number) => GROUP_COLORS[g % GROUP_COLORS.length]

/** Readers in reading order: rows from the top of the floor, left to right. */
export function orderReaders(readers: StartReader[]): StartReader[] {
  return [...readers].sort((a, b) => Math.round((b.y_m - a.y_m) * 1000) || a.x_m - b.x_m)
}

/** Drop empty groups so the start times have no gaps. */
export function compactGroups(readers: StartReader[], assignment: StartAssignment): number[][] {
  const used = [...new Set(readers.map((r) => assignment[r.id] ?? 0))].sort((a, b) => a - b)
  return used.map((g) => orderReaders(readers.filter((r) => (assignment[r.id] ?? 0) === g)).map((r) => r.id))
}

type Preset = 'together' | 'checkerboard' | 'rows' | 'columns' | 'sequential'

function presetAssignment(readers: StartReader[], preset: Preset): StartAssignment {
  const rowsOf = distinctLevels(readers.map((r) => r.y_m)).reverse()
  const colsOf = distinctLevels(readers.map((r) => r.x_m))
  const row = (r: StartReader) => rowsOf.findIndex((y) => Math.abs(y - Math.round(r.y_m * 1000) / 1000) < 1e-6)
  const col = (r: StartReader) => colsOf.findIndex((x) => Math.abs(x - Math.round(r.x_m * 1000) / 1000) < 1e-6)
  const ordered = orderReaders(readers)
  const rankInRow = (r: StartReader) => ordered.filter((o) => row(o) === row(r)).indexOf(r)
  const out: StartAssignment = {}
  ordered.forEach((r, i) => {
    out[r.id] =
      preset === 'together' ? 0
        : preset === 'checkerboard' ? (row(r) + rankInRow(r)) % 2
          : preset === 'rows' ? row(r)
            : preset === 'columns' ? col(r)
              : i
  })
  return out
}

function distinctLevels(values: number[]): number[] {
  return [...new Set(values.map((v) => Math.round(v * 1000) / 1000))].sort((a, b) => a - b)
}

/**
 * Pick which readers start together. The map shows the readers where they
 * stand; choose a group, then click readers to move them into it. Group n
 * starts n × interval after group 1.
 */
export function StartGroupsDialog({
  open,
  readers,
  floor,
  intervalMs,
  value,
  onClose,
  onApply,
}: {
  open: boolean
  readers: StartReader[]
  floor: { width: number; height: number } | null
  intervalMs: number
  value: StartAssignment
  onClose: () => void
  onApply: (assignment: StartAssignment) => void
}) {
  const { t } = useTranslation()
  const [draft, setDraft] = useState<StartAssignment>(value)
  const [active, setActive] = useState(0)
  const [openKey, setOpenKey] = useState(open)
  if (open !== openKey) {
    setOpenKey(open)
    if (open) {
      setDraft(value)
      setActive(0)
    }
  }
  const ordered = useMemo(() => orderReaders(readers), [readers])
  const groupCount = Math.max(active + 1, 1 + Math.max(0, ...readers.map((r) => draft[r.id] ?? 0)))
  const counts = Array.from({ length: groupCount }, (_, g) => readers.filter((r) => (draft[r.id] ?? 0) === g).length)

  const W = floor?.width || Math.max(1, ...readers.map((r) => r.x_m)) * 1.1
  const H = floor?.height || Math.max(1, ...readers.map((r) => r.y_m)) * 1.1
  const pad = Math.max(W, H) * 0.04
  const r = Math.max(W, H) * 0.028

  function assign(id: number) {
    setDraft((prev) => ({ ...prev, [id]: active }))
  }

  return (
    <Dialog open={open} onOpenChange={(next) => { if (!next) onClose() }}>
      <DialogPortal>
        <DialogBackdrop />
        <DialogPopup className="w-[min(760px,calc(100vw-32px))] gap-3 p-4">
          <DialogTitle>{t('thesis.stagger.title')}</DialogTitle>
          <DialogDescription>{t('thesis.stagger.hint', { ms: intervalMs })}</DialogDescription>

          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="text-muted-foreground">{t('thesis.stagger.preset')}</span>
            {(['together', 'checkerboard', 'rows', 'columns', 'sequential'] as const).map((p) => (
              <Button key={p} type="button" size="xs" variant="outline" onClick={() => setDraft(presetAssignment(readers, p))}>
                {t(`thesis.stagger.presets.${p}`)}
              </Button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            {counts.map((n, g) => (
              <button
                key={g}
                type="button"
                onClick={() => setActive(g)}
                className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 ${active === g ? 'border-foreground bg-muted font-medium' : 'border-border'}`}
              >
                <span className="size-2.5 rounded-full" style={{ background: groupColor(g) }} />
                {t('thesis.stagger.group', { n: g + 1 })}
                <span className="text-muted-foreground tabular-nums">
                  {n} · +{g * intervalMs} ms
                </span>
              </button>
            ))}
            <Button type="button" size="xs" variant="ghost" onClick={() => setActive(groupCount)}>
              <Plus />
              {t('thesis.stagger.addGroup')}
            </Button>
          </div>
          <p className="text-[11px] text-muted-foreground">{t('thesis.stagger.clickHint', { n: active + 1 })}</p>

          <div className="grid gap-3 md:grid-cols-[1fr_220px]">
            <svg
              viewBox={`${-pad} ${-pad} ${W + 2 * pad} ${H + 2 * pad}`}
              className="max-h-[46vh] w-full rounded-md border bg-muted/30"
              role="group"
              aria-label={t('thesis.stagger.map')}
            >
              <g transform={`translate(0 ${H}) scale(1 -1)`}>
                <rect width={W} height={H} fill="none" className="stroke-foreground/50" strokeDasharray="4 3" vectorEffect="non-scaling-stroke" />
                {ordered.map((rd) => {
                  const g = draft[rd.id] ?? 0
                  return (
                    <g key={rd.id} transform={`translate(${rd.x_m} ${rd.y_m})`} className="cursor-pointer" onClick={() => assign(rd.id)}>
                      <circle r={r} fill={groupColor(g)} fillOpacity={0.85} stroke="white" strokeWidth={1.5} vectorEffect="non-scaling-stroke">
                        <title>{rd.label}</title>
                      </circle>
                      <text transform="scale(1 -1)" textAnchor="middle" dominantBaseline="central" fontSize={r * 1.1} fill="white" className="pointer-events-none font-medium">
                        {g + 1}
                      </text>
                    </g>
                  )
                })}
              </g>
            </svg>
            <ol className="grid max-h-[46vh] content-start gap-1 overflow-y-auto text-xs">
              {ordered.map((rd, i) => {
                const g = draft[rd.id] ?? 0
                return (
                  <li key={rd.id}>
                    <button
                      type="button"
                      onClick={() => assign(rd.id)}
                      className="flex w-full items-center gap-2 rounded-md border px-2 py-1 text-left hover:bg-muted"
                    >
                      <span className="w-4 text-muted-foreground tabular-nums">{i + 1}</span>
                      <span className="min-w-0 flex-1 truncate">{rd.label}</span>
                      <span className="rounded-full px-1.5 text-[10px] text-white" style={{ background: groupColor(g) }}>
                        G{g + 1}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ol>
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>
              {t('thesis.newRun.cancel')}
            </Button>
            <Button type="button" onClick={() => onApply(draft)}>
              {t('thesis.stagger.apply')}
            </Button>
          </div>
        </DialogPopup>
      </DialogPortal>
    </Dialog>
  )
}
