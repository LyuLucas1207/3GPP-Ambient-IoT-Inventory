import { MathText } from '@/components/MathText'
import {
  Popover,
  PopoverClose,
  PopoverDescription,
  PopoverPopup,
  PopoverPortal,
  PopoverPositioner,
  PopoverTitle,
  PopoverTrigger,
} from '@/components/ui/popover'
import { cn } from '@/lib/utils'
import { XIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

interface Props {
  title: string
  body: string
  ariaLabel?: string
  className?: string
  children: ReactNode
}

export function ClickHelp({ title, body, ariaLabel, className, children }: Props) {
  const { t } = useTranslation()
  return (
    <Popover>
      <PopoverTrigger
        render={
          <button
            type="button"
            className={cn(
              'inline-flex items-center gap-1 rounded-md text-left outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
              className,
            )}
            aria-label={ariaLabel ?? t('explain.termAria', { term: title })}
          />
        }
      >
        {children}
      </PopoverTrigger>
      <PopoverPortal>
        <PopoverPositioner side="bottom" align="start">
          <PopoverPopup>
            <div className="flex items-start justify-between gap-2">
              <PopoverTitle>
                <MathText text={title} />
              </PopoverTitle>
              <PopoverClose
                className="rounded-md p-1 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
                aria-label={t('explain.close')}
              >
                <XIcon className="size-3.5" />
              </PopoverClose>
            </div>
            <PopoverDescription className="mt-2">
              <MathText text={body} />
            </PopoverDescription>
          </PopoverPopup>
        </PopoverPositioner>
      </PopoverPortal>
    </Popover>
  )
}
