import { Loader2, PanelRightClose, PanelRightOpen, Pause, Pencil, Play, Plus, Square, Trash2, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { NewRunDialog } from '@/components/thesis/NewRunDialog'
import { Button } from '@/components/ui/button'
import { Dialog, DialogBackdrop, DialogDescription, DialogPopup, DialogPortal, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { runDisplayName } from '@/lib/thesisRunStates'
import type { Placement, PlacementId, RunCreateInput, RunStatus, RunSummary, Scene } from '@/types/thesis'

/** Right-hand sidebar of the simulation page: one collapsible panel with Readers / Runs tabs. */
export function ThesisRightPanel({
  scene,
  focusReaderId,
  onFocus,
  runs,
  selectedRunId,
  runsBusy,
  onSelectRun,
  onCreateRun,
  onDeleteRun,
  onRenameRun,
  onStopRun,
  onPauseRun,
  onResumeRun,
}: {
  scene: Scene | null
  focusReaderId: PlacementId | null
  onFocus: (id: PlacementId | null) => void
  runs: RunSummary[]
  selectedRunId: number | null
  runsBusy: boolean
  onSelectRun: (id: number | null) => void
  onCreateRun: (config: RunCreateInput) => Promise<void> | void
  onDeleteRun: (id: number) => Promise<void> | void
  onRenameRun: (id: number, name: string | null) => Promise<void> | void
  onStopRun: (id: number) => Promise<void> | void
  onPauseRun: (id: number) => Promise<void> | void
  onResumeRun: (id: number) => Promise<void> | void
}) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const readers = useMemo<Placement[]>(() => scene?.placements.filter((p) => p.kind === 'radar') ?? [], [scene])
  const readerOptions = useMemo(
    () =>
      readers
        .filter((p) => typeof p.id === 'number')
        .map((p) => ({ id: p.id as number, label: `#${p.id} (${p.x_m.toFixed(1)}, ${p.y_m.toFixed(1)})`, x_m: p.x_m, y_m: p.y_m })),
    [readers],
  )
  const canRun = scene?.locked === true

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
          <Tabs defaultValue="readers" className="min-h-0 w-full flex-1 flex-col gap-0">
            <TabsList className="mx-3 mt-3 grid h-9 w-[calc(100%-1.5rem)] shrink-0 grid-cols-2">
              <TabsTrigger value="readers" className="min-w-0 px-1 text-xs">
                {t('thesis.readerList.title', { count: readers.length })}
              </TabsTrigger>
              <TabsTrigger value="runs" className="min-w-0 px-1 text-xs">
                {t('thesis.runsPanel.title', { count: runs.length })}
              </TabsTrigger>
            </TabsList>

            <TabsContent value="readers" className="flex min-h-0 flex-1 flex-col">
              <div className="flex h-8 shrink-0 items-center justify-end px-3">
                {focusReaderId != null ? (
                  <Button type="button" size="xs" variant="ghost" aria-label={t('thesis.readerList.clear')} onClick={() => onFocus(null)}>
                    <X className="mr-1 size-3" />
                    {t('thesis.readerList.clear')}
                  </Button>
                ) : null}
              </div>
              <ScrollArea className="min-h-0 flex-1">
                <div className="flex flex-col gap-1 p-2 pt-0">
                  {readers.length === 0 ? (
                    <p className="px-1 text-xs text-muted-foreground">{t('thesis.readerList.empty')}</p>
                  ) : null}
                  {readers.map((reader) => {
                    const active = focusReaderId != null && reader.id === focusReaderId
                    return (
                      <button
                        key={reader.id}
                        type="button"
                        className={`flex flex-col items-start rounded-lg border px-2 py-1.5 text-left text-xs transition ${
                          active ? 'border-[#b91c1c] bg-[#b91c1c]/10' : 'hover:bg-muted'
                        }`}
                        onClick={() => onFocus(active ? null : reader.id)}
                      >
                        <span className="font-medium">#{reader.id}</span>
                        <span className="text-muted-foreground tabular-nums">
                          ({reader.x_m.toFixed(1)}, {reader.y_m.toFixed(1)}) m
                        </span>
                      </button>
                    )
                  })}
                </div>
              </ScrollArea>
              <p className="shrink-0 border-t px-3 py-2 text-[11px] text-muted-foreground">{t('thesis.readerList.hint')}</p>
            </TabsContent>

            <TabsContent value="runs" className="flex min-h-0 flex-1 flex-col">
              <div className="flex h-8 shrink-0 items-center justify-between gap-2 px-3">
                <span className="text-[11px] text-muted-foreground">
                  {runsBusy ? `⏳ ${t('thesis.runsPanel.working')}` : null}
                </span>
                <Button
                  type="button"
                  size="xs"
                  variant="outline"
                  disabled={runsBusy || !canRun}
                  title={canRun ? undefined : t('thesis.runsPanel.needInit')}
                  onClick={() => setDialogOpen(true)}
                >
                  <Plus className="mr-1 size-3" />
                  {t('thesis.runsPanel.newRun')}
                </Button>
              </div>
              <ScrollArea className="min-h-0 flex-1">
                <div className="flex flex-col gap-2 p-2 pt-0">
                  {!canRun ? <p className="px-1 text-xs text-muted-foreground">{t('thesis.runsPanel.needInit')}</p> : null}
                  {canRun && runs.length === 0 ? (
                    <p className="px-1 text-xs text-muted-foreground">{t('thesis.runsPanel.empty')}</p>
                  ) : null}
                  {runs.map((run) => {
                    const active = selectedRunId === run.run_id
                    return (
                      <div
                        key={run.run_id}
                        className={`relative rounded-lg border px-2 py-2 text-xs ${active ? 'border-foreground bg-muted/60' : 'hover:bg-muted/40'}`}
                      >
                        {/* Sibling of the card button (a button cannot nest inside a button). */}
                        <Button
                          type="button"
                          size="icon-xs"
                          variant="ghost"
                          className="absolute top-1.5 right-1.5 text-muted-foreground hover:text-destructive"
                          aria-label={t('thesis.runsPanel.delete')}
                          title={t('thesis.runsPanel.delete')}
                          disabled={runsBusy}
                          onClick={(event) => {
                            event.stopPropagation()
                            void onDeleteRun(run.run_id)
                          }}
                        >
                          <Trash2 className="size-3" />
                        </Button>
                        <div className="flex w-full items-center justify-between gap-2 pr-6">
                          <RunNameLabel
                            run={run}
                            busy={runsBusy}
                            onSelect={() => onSelectRun(active ? null : run.run_id)}
                            onRename={(name) => onRenameRun(run.run_id, name)}
                          />
                          <button type="button" onClick={() => onSelectRun(active ? null : run.run_id)}>
                            <StatusChip status={run.status} />
                          </button>
                        </div>
                        <button
                          type="button"
                          className="mt-1 flex w-full flex-col items-start gap-1"
                          onClick={() => onSelectRun(active ? null : run.run_id)}
                        >
                          <div className="flex w-full justify-between text-muted-foreground">
                            <span>{t(`thesis.newRun.scheme${run.scheme === 'periodic' ? 'Periodic' : 'Aperiodic'}`)}</span>
                            <span className="tabular-nums">
                              {run.identified_total}/{run.total_devices}
                            </span>
                          </div>
                          <div className="flex w-full justify-between text-muted-foreground">
                            <span>{t('thesis.runsPanel.rounds', { count: run.rounds_total })}</span>
                            {run.sim_time_s ? (
                              <span className="tabular-nums" title={t('thesis.live.simTime')}>
                                {run.sim_time_s.toFixed(2)} s
                              </span>
                            ) : (
                              <span className="tabular-nums" title={t('thesis.analysis.cols.duration')}>
                                {(run.duration_s ?? run.wall_duration_s ?? 0).toFixed(2)} s
                              </span>
                            )}
                          </div>
                        </button>
                        {active && (run.status === 'running' || run.status === 'pending' || run.status === 'paused') ? (
                          <div className="mt-2 flex gap-1 border-t pt-2">
                            {run.status === 'running' || run.status === 'pending' ? (
                              <Button type="button" size="xs" variant="outline" disabled={runsBusy} onClick={() => void onPauseRun(run.run_id)}>
                                <Pause className="mr-1 size-3" />
                                {t('thesis.live.pause')}
                              </Button>
                            ) : null}
                            {run.status === 'paused' ? (
                              <Button type="button" size="xs" variant="outline" disabled={runsBusy} onClick={() => void onResumeRun(run.run_id)}>
                                <Play className="mr-1 size-3" />
                                {t('thesis.live.resume')}
                              </Button>
                            ) : null}
                            {run.status === 'running' || run.status === 'pending' || run.status === 'paused' ? (
                              <Button type="button" size="xs" variant="outline" disabled={runsBusy} onClick={() => void onStopRun(run.run_id)}>
                                <Square className="mr-1 size-3" />
                                {t('thesis.runsPanel.stop')}
                              </Button>
                            ) : null}
                          </div>
                        ) : null}
                      </div>
                    )
                  })}
                </div>
              </ScrollArea>
              <p className="shrink-0 border-t px-3 py-2 text-[11px] text-muted-foreground">{t('thesis.runsPanel.hint')}</p>
            </TabsContent>
          </Tabs>
        </aside>
      </div>
      <Button
        type="button"
        size="icon-sm"
        variant="outline"
        className="absolute top-3 right-full z-30 mr-2 bg-background shadow-sm"
        aria-expanded={open}
        aria-label={open ? t('thesis.rightPanel.collapse') : t('thesis.rightPanel.expand')}
        onClick={() => setOpen((value) => !value)}
      >
        {open ? <PanelRightClose /> : <PanelRightOpen />}
      </Button>
      <NewRunDialog
        open={dialogOpen}
        busy={runsBusy}
        readers={readerOptions}
        floor={scene ? { width: scene.width_m, height: scene.height_m } : null}
        onClose={() => setDialogOpen(false)}
        onCreate={(cfg) => {
          setDialogOpen(false)
          void onCreateRun(cfg)
        }}
      />
      <Dialog open={runsBusy} onOpenChange={() => undefined}>
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

function RunNameLabel({
  run,
  busy,
  onSelect,
  onRename,
}: {
  run: RunSummary
  busy: boolean
  onSelect: () => void
  onRename: (name: string | null) => Promise<void> | void
}) {
  const { t } = useTranslation()
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(run.name ?? '')

  useEffect(() => {
    if (!editing) setDraft(run.name ?? '')
  }, [run.name, editing])

  async function commit() {
    const next = draft.trim() || null
    const current = run.name?.trim() || null
    setEditing(false)
    if (next === current) return
    await onRename(next)
  }

  if (editing) {
    return (
      <Input
        autoFocus
        value={draft}
        maxLength={80}
        className="h-6 min-w-0 flex-1 px-1 text-xs font-medium"
        aria-label={t('thesis.runsPanel.rename')}
        onClick={(event) => event.stopPropagation()}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={() => void commit()}
        onKeyDown={(event) => {
          event.stopPropagation()
          if (event.key === 'Enter') {
            event.preventDefault()
            void commit()
          } else if (event.key === 'Escape') {
            event.preventDefault()
            setDraft(run.name ?? '')
            setEditing(false)
          }
        }}
      />
    )
  }

  const label = runDisplayName(run)
  return (
    <span className="flex min-w-0 items-center gap-0.5">
      <button
        type="button"
        className="truncate font-medium text-left"
        title={run.name?.trim() ? `#${run.run_id}` : undefined}
        onClick={onSelect}
        onDoubleClick={(event) => {
          event.preventDefault()
          if (!busy) setEditing(true)
        }}
      >
        {label}
      </button>
      <Button
        type="button"
        size="icon-xs"
        variant="ghost"
        className="size-5 shrink-0 text-muted-foreground"
        aria-label={t('thesis.runsPanel.rename')}
        title={t('thesis.runsPanel.rename')}
        disabled={busy}
        onClick={() => setEditing(true)}
      >
        <Pencil className="size-2.5" />
      </Button>
    </span>
  )
}

export function StatusChip({ status }: { status: RunStatus }) {
  const { t } = useTranslation()
  const tone =
    status === 'completed'
      ? 'bg-green-500/15 text-green-700'
      : status === 'running' || status === 'pending'
        ? 'bg-blue-500/15 text-blue-700'
        : status === 'paused'
          ? 'bg-violet-500/15 text-violet-700'
          : status === 'stopped'
          ? 'bg-yellow-500/15 text-yellow-700'
          : status === 'failed'
            ? 'bg-destructive/15 text-destructive'
            : 'bg-muted text-muted-foreground'
  return <span className={`rounded px-1.5 py-0.5 text-[10px] uppercase ${tone}`}>{t(`thesis.runsPanel.status.${status}`)}</span>
}
