import { Maximize2, X } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Dialog, DialogBackdrop, DialogClose, DialogPopup, DialogPortal, DialogTitle } from '@/components/ui/dialog'

/** Inspector section holding a time-frequency chart, with a full-width view for long runs. */
export function TimeFreqSection({ title, children }: { title: string; children: (wide: boolean) => React.ReactNode }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  return (
    <section className="grid gap-1.5">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-medium">{title}</h3>
        <Button type="button" size="xs" variant="ghost" onClick={() => setOpen(true)}>
          <Maximize2 />
          {t('thesis.tf.expand')}
        </Button>
      </div>
      {open ? null : children(false)}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogPortal>
          <DialogBackdrop />
          <DialogPopup className="w-[calc(100vw-32px)] max-w-none gap-3 p-4">
            <div className="flex items-center justify-between gap-2">
              <DialogTitle>{title}</DialogTitle>
              <DialogClose render={<Button type="button" size="icon-sm" variant="ghost" aria-label={t('thesis.inspector.close')} />}>
                <X />
              </DialogClose>
            </div>
            <div className="min-h-0 overflow-y-auto">{children(true)}</div>
          </DialogPopup>
        </DialogPortal>
      </Dialog>
    </section>
  )
}
