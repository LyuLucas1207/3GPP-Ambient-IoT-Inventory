import { MathText } from '@/components/MathText'
import { Badge } from '@/components/ui/badge'
import {
  Popover,
  PopoverDescription,
  PopoverPopup,
  PopoverPortal,
  PopoverPositioner,
  PopoverTitle,
  PopoverTrigger,
} from '@/components/ui/popover'
import { cn } from '@/lib/utils'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

interface Props {
  title: string
  paper: string
  ui: string
  source: 'paper' | 'viz'
  className?: string
  children: ReactNode
}

export function HoverHelp({ title, paper, ui, source, className, children }: Props) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const closeTimer = useRef(0)
  const cancelClose = () => window.clearTimeout(closeTimer.current)
  const show = () => {
    cancelClose()
    setOpen(true)
  }
  const hideSoon = () => {
    cancelClose()
    closeTimer.current = window.setTimeout(() => setOpen(false), 160)
  }

  useEffect(() => () => cancelClose(), [])

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        render={
          <button
            type="button"
            onPointerEnter={show}
            onPointerLeave={hideSoon}
            className={cn(
              'inline-flex cursor-help items-center rounded-md text-left outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
              className,
            )}
            aria-label={t('explain.termAria', { term: title })}
          />
        }
      >
        {children}
      </PopoverTrigger>
      <PopoverPortal>
        <PopoverPositioner side="bottom" align="start" className="z-[220]">
          <PopoverPopup onPointerEnter={show} onPointerLeave={hideSoon}>
            <PopoverTitle>
              <MathText text={title} />
            </PopoverTitle>
            <div className="mt-1.5">
              <Badge variant="outline">{t(`explain.source.${source}`)}</Badge>
            </div>
            <p className="mt-2 text-[11px] tracking-wide text-muted-foreground uppercase">
              {t('factory.paperWording')}
            </p>
            <PopoverDescription className="mt-1">
              <MathText text={paper} />
            </PopoverDescription>
            <p className="mt-2 text-[11px] tracking-wide text-muted-foreground uppercase">
              {t('factory.thisColour')}
            </p>
            <p className="mt-1 text-sm leading-relaxed">
              <MathText text={ui} />
            </p>
          </PopoverPopup>
        </PopoverPositioner>
      </PopoverPortal>
    </Popover>
  )
}
