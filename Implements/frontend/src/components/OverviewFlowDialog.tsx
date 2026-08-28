import {
  Dialog,
  DialogBackdrop,
  DialogClose,
  DialogDescription,
  DialogPopup,
  DialogPortal,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { StrategyFlow } from '@/components/StrategyFlow'
import { overviewMap } from '@/strategyMaps/overview'
import { WorkflowIcon, XIcon } from 'lucide-react'
import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

export function OverviewFlowButton() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const btn = useRef<HTMLButtonElement>(null)

  return (
    <>
      <Button
        ref={btn}
        type="button"
        variant="outline"
        size="xs"
        className="gap-1"
        aria-label={t('overview.buttonAria')}
        onClick={() => setOpen(true)}
      >
        <WorkflowIcon className="size-3.5" aria-hidden />
        {t('overview.button')}
      </Button>
      <Dialog
        modal
        open={open}
        onOpenChange={(next) => {
          setOpen(next)
        }}
      >
        <DialogPortal>
          <DialogBackdrop />
          <DialogPopup
            className="h-[calc(100dvh-12px)] w-[calc(100vw-12px)] max-h-[calc(100dvh-12px)] max-w-[1920px]"
            finalFocus={btn}
            aria-modal="true"
          >
            <div className="flex shrink-0 items-start justify-between gap-3 border-b px-4 py-3">
              <div className="min-w-0">
                <DialogTitle>{t('overview.title')}</DialogTitle>
                <DialogDescription>{t('overview.lead')}</DialogDescription>
              </div>
              <DialogClose
                className="rounded-md p-1 outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                aria-label={t('explain.close')}
              >
                <XIcon className="size-4" />
              </DialogClose>
            </div>
            <div className="grid min-h-0 flex-1 overflow-hidden lg:grid-cols-[minmax(0,1fr)_minmax(22rem,26rem)]">
              <div className="h-full min-h-0 border-b lg:border-r lg:border-b-0">
                <StrategyFlow key="overview" def={overviewMap} />
              </div>
              <aside className="grid gap-4 overflow-auto p-5 text-sm">
                <section>
                  <h3 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                    {t('maps.how')}
                  </h3>
                  <ol className="mt-1.5 list-decimal space-y-1.5 pl-4 text-sm">
                    {t('overview.steps')
                      .split('\n')
                      .filter(Boolean)
                      .map((line) => (
                        <li key={line}>{line}</li>
                      ))}
                  </ol>
                </section>
                <p className="text-xs leading-relaxed text-muted-foreground">{t('maps.clickNode')}</p>
                <p className="text-xs leading-relaxed text-muted-foreground">{t('maps.legend')}</p>
                <pre className="overflow-auto rounded-md bg-muted/60 p-3 text-[11px] leading-tight text-muted-foreground">
                  {t('overview.ascii')}
                </pre>
              </aside>
            </div>
          </DialogPopup>
        </DialogPortal>
      </Dialog>
    </>
  )
}
