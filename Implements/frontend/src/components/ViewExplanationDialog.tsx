import { MathText } from '@/components/MathText'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogBackdrop,
  DialogClose,
  DialogDescription,
  DialogPopup,
  DialogPortal,
  DialogTitle,
} from '@/components/ui/dialog'
import { ViewId } from '@/explain/ids'
import { CircleHelpIcon, XIcon } from 'lucide-react'
import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

interface Props {
  view: ViewId
  example?: string
}

export function ExplainButton({ view, example }: Props) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const btn = useRef<HTMLButtonElement>(null)
  const paragraphs = t(`views.${view}.body`)
    .split('\n')
    .filter(Boolean)

  return (
    <>
      <Button
        ref={btn}
        type="button"
        variant="outline"
        size="xs"
        className="gap-1"
        aria-label={t('explain.buttonAria', { view: t(`views.${view}.title`) })}
        onClick={() => setOpen(true)}
      >
        <CircleHelpIcon className="size-3.5" aria-hidden />
        {t('explain.button')}
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
            className="w-[min(40rem,calc(100vw-24px))] max-h-[min(85dvh,720px)]"
            finalFocus={btn}
            aria-modal="true"
          >
            <div className="flex shrink-0 items-start justify-between gap-3 border-b px-4 py-3">
              <div className="min-w-0">
                <DialogTitle>{t(`views.${view}.title`)}</DialogTitle>
                <DialogDescription>{t(`views.${view}.lead`)}</DialogDescription>
              </div>
              <DialogClose
                className="rounded-md p-1 outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                aria-label={t('explain.close')}
              >
                <XIcon className="size-4" />
              </DialogClose>
            </div>
            <div className="min-h-0 flex-1 overflow-auto px-4 py-3">
              <div className="grid gap-3 text-sm leading-relaxed">
                {paragraphs.map((p) => (
                  <p key={p}>
                    <MathText text={p} />
                  </p>
                ))}
                {example ? (
                  <section className="rounded-md border bg-muted/40 p-3">
                    <h3 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                      {t('explain.example')}
                    </h3>
                    <p className="mt-1.5">
                      <MathText text={example} />
                    </p>
                  </section>
                ) : null}
              </div>
            </div>
          </DialogPopup>
        </DialogPortal>
      </Dialog>
    </>
  )
}
