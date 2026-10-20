import { PanelRightClose, PanelRightOpen, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { Placement, PlacementId, Scene } from '@/types/thesis'

export function ReaderListPanel({
  scene,
  focusReaderId,
  onFocus,
}: {
  scene: Scene | null
  focusReaderId: PlacementId | null
  onFocus: (id: PlacementId | null) => void
}) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(true)
  const readers = useMemo<Placement[]>(() => {
    if (!scene) return []
    return scene.placements.filter((p) => p.kind === 'radar')
  }, [scene])

  return (
    <div
      className={`relative h-full shrink-0 transition-[width] duration-300 ease-out ${
        open ? 'w-64 max-w-[35vw]' : 'w-0'
      }`}
    >
      <div className="h-full overflow-hidden">
      <aside
        className={`flex h-full w-64 max-w-[35vw] flex-col overflow-hidden bg-card ${open ? 'border-l' : ''}`}
        aria-hidden={!open}
        inert={!open}
      >
        <div className="flex min-h-0 flex-1 flex-col">
            <div className="flex shrink-0 items-center justify-between gap-2 border-b px-3 py-2">
              <h2 className="text-sm font-medium">{t('thesis.readerList.title', { count: readers.length })}</h2>
              {focusReaderId != null ? (
                <Button
                  type="button"
                  size="xs"
                  variant="ghost"
                  aria-label={t('thesis.readerList.clear')}
                  onClick={() => onFocus(null)}
                >
                  <X className="mr-1 size-3" />
                  {t('thesis.readerList.clear')}
                </Button>
              ) : null}
            </div>
            <ScrollArea className="min-h-0 flex-1">
              <div className="flex flex-col gap-1 p-2">
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
            <p className="shrink-0 border-t px-3 py-2 text-[11px] text-muted-foreground">
              {t('thesis.readerList.hint')}
            </p>
          </div>
      </aside>
      </div>
      <Button
        type="button"
        size="icon-sm"
        variant="outline"
        className="absolute top-3 right-full z-30 mr-2 bg-background shadow-sm"
        aria-expanded={open}
        aria-label={open ? t('thesis.readerList.collapse') : t('thesis.readerList.expand')}
        onClick={() => setOpen((value) => !value)}
      >
        {open ? <PanelRightClose /> : <PanelRightOpen />}
      </Button>
    </div>
  )
}
