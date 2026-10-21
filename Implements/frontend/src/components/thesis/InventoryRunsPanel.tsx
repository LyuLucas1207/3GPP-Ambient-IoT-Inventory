import { Loader2, PanelRightClose, PanelRightOpen, Plus, Trash2, X } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { NewRunDialog } from '@/components/thesis/NewRunDialog'
import { Button } from '@/components/ui/button'
import { Dialog, DialogBackdrop, DialogDescription, DialogPopup, DialogPortal, DialogTitle } from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { RunCreateInput, RunStatus, RunSummary } from '@/types/thesis'

export function InventoryRunsPanel({
  runs,
  selectedRunId,
  onSelect,
  onCreate,
  onDelete,
  onStop,
  busy,
}: {
  runs: RunSummary[]
  selectedRunId: number | null
  onSelect: (id: number | null) => void
  onCreate: (config: RunCreateInput) => Promise<void> | void
  onDelete: (id: number) => Promise<void> | void
  onStop: (id: number) => Promise<void> | void
  busy: boolean
}) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)

  return (
    <div
      className={`relative h-full shrink-0 transition-[width] duration-300 ease-out ${
        open ? 'w-72 max-w-[40vw]' : 'w-0'
      }`}
    >
      <div className="h-full overflow-hidden">
        <aside
          className={`flex h-full w-72 max-w-[40vw] flex-col overflow-hidden bg-card ${open ? 'border-l' : ''}`}
          aria-hidden={!open}
          inert={!open}
        >
          <div className="flex shrink-0 items-center justify-between gap-2 border-b px-3 py-2">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-medium">{t('thesis.runsPanel.title', { count: runs.length })}</h2>
              {busy ? <span className="text-[11px] text-muted-foreground">⏳ {t('thesis.runsPanel.working')}</span> : null}
            </div>
            <Button
              type="button"
              size="xs"
              variant="outline"
              disabled={busy}
              onClick={() => setDialogOpen(true)}
            >
              <Plus className="mr-1 size-3" />
              {t('thesis.runsPanel.newRun')}
            </Button>
          </div>
          <ScrollArea className="min-h-0 flex-1">
            <div className="flex flex-col gap-2 p-2">
              {runs.length === 0 ? (
                <p className="px-1 text-xs text-muted-foreground">{t('thesis.runsPanel.empty')}</p>
              ) : null}
              {runs.map((run) => {
                const active = selectedRunId === run.run_id
                return (
                  <div
                    key={run.run_id}
                    className={`rounded-lg border px-2 py-2 text-xs ${
                      active ? 'border-foreground bg-muted/60' : 'hover:bg-muted/40'
                    }`}
                  >
                    <button
                      type="button"
                      className="flex w-full flex-col items-start gap-1"
                      onClick={() => onSelect(active ? null : run.run_id)}
                    >
                      <div className="flex w-full items-center justify-between gap-2">
                        <span className="font-medium">#{run.run_id}</span>
                        <StatusChip status={run.status} />
                      </div>
                      <div className="flex w-full justify-between text-muted-foreground">
                        <span>{t(`thesis.newRun.scheme${run.scheme === 'periodic' ? 'Periodic' : 'Aperiodic'}`)}</span>
                        <span className="tabular-nums">
                          {run.identified_total}/{run.total_devices}
                        </span>
                      </div>
                      <div className="flex w-full justify-between text-muted-foreground">
                        <span>{t('thesis.runsPanel.rounds', { count: run.rounds_total })}</span>
                        <span className="tabular-nums">{run.wall_duration_s.toFixed(2)} s</span>
                      </div>
                    </button>
                    {active ? (
                      <div className="mt-2 flex gap-1 border-t pt-2">
                        {run.status === 'running' || run.status === 'pending' ? (
                          <Button
                            type="button"
                            size="xs"
                            variant="outline"
                            disabled={busy}
                            onClick={() => void onStop(run.run_id)}
                          >
                            <X className="mr-1 size-3" />
                            {t('thesis.runsPanel.stop')}
                          </Button>
                        ) : null}
                        <Button
                          type="button"
                          size="xs"
                          variant="destructive"
                          disabled={busy}
                          onClick={() => void onDelete(run.run_id)}
                        >
                          <Trash2 className="mr-1 size-3" />
                          {t('thesis.runsPanel.delete')}
                        </Button>
                      </div>
                    ) : null}
                  </div>
                )
              })}
            </div>
          </ScrollArea>
          <p className="shrink-0 border-t px-3 py-2 text-[11px] text-muted-foreground">{t('thesis.runsPanel.hint')}</p>
        </aside>
      </div>
      <Button
        type="button"
        size="icon-sm"
        variant="outline"
        className="absolute top-3 right-full z-30 mr-2 bg-background shadow-sm"
        aria-expanded={open}
        aria-label={open ? t('thesis.runsPanel.collapse') : t('thesis.runsPanel.expand')}
        onClick={() => setOpen((v) => !v)}
      >
        {open ? <PanelRightClose /> : <PanelRightOpen />}
      </Button>
      <NewRunDialog
        open={dialogOpen}
        busy={busy}
        onClose={() => setDialogOpen(false)}
        onCreate={(cfg) => {
          setDialogOpen(false)
          void onCreate(cfg)
        }}
      />
      <Dialog open={busy} onOpenChange={() => undefined}>
        <DialogPortal>
          <DialogBackdrop />
          <DialogPopup className="w-[min(360px,calc(100vw-32px))] items-center gap-3 p-5 text-center">
            <Loader2 className="size-6 animate-spin text-foreground/70" />
            <DialogTitle>{t('thesis.runsPanel.workingTitle')}</DialogTitle>
            <DialogDescription>{t('thesis.runsPanel.workingHint')}</DialogDescription>
          </DialogPopup>
        </DialogPortal>
      </Dialog>
    </div>
  )
}

function StatusChip({ status }: { status: RunStatus }) {
  const { t } = useTranslation()
  const tone =
    status === 'completed'
      ? 'bg-green-500/15 text-green-700'
      : status === 'running' || status === 'pending'
      ? 'bg-blue-500/15 text-blue-700'
      : status === 'stopped'
      ? 'bg-yellow-500/15 text-yellow-700'
      : status === 'failed'
      ? 'bg-destructive/15 text-destructive'
      : 'bg-muted text-muted-foreground'
  return <span className={`rounded px-1.5 py-0.5 text-[10px] uppercase ${tone}`}>{t(`thesis.runsPanel.status.${status}`)}</span>
}
