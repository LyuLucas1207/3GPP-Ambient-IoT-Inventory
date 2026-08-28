import { MathText } from '@/components/MathText'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
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
import { TERM_SOURCE, TermId } from '@/explain/ids'
import { CircleHelpIcon, XIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface Props {
  term: TermId
}

export function TermHelp({ term }: Props) {
  const { t } = useTranslation()
  const source = TERM_SOURCE[term]
  return (
    <Popover>
      <PopoverTrigger
        render={
          <Button
            type="button"
            variant="ghost"
            size="icon-xs"
            className="size-7 shrink-0"
            aria-label={t('explain.termAria', { term: t(`terms.${term}.short`) })}
          />
        }
      >
        <CircleHelpIcon className="size-3.5" aria-hidden />
      </PopoverTrigger>
      <PopoverPortal>
        <PopoverPositioner side="bottom" align="start">
          <PopoverPopup>
            <div className="flex items-start justify-between gap-2">
              <PopoverTitle>
                <MathText text={t(`terms.${term}.full`)} />
              </PopoverTitle>
              <PopoverClose
                className="rounded-md p-1 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
                aria-label={t('explain.close')}
              >
                <XIcon className="size-3.5" />
              </PopoverClose>
            </div>
            <div className="mt-1.5 flex flex-wrap gap-1">
              <Badge variant="outline">{t(`explain.source.${source}`)}</Badge>
              <Badge variant="secondary">{t(`terms.${term}.unit`)}</Badge>
            </div>
            <PopoverDescription className="mt-2">
              <MathText text={t(`terms.${term}.body`)} />
            </PopoverDescription>
            <p className="mt-2 text-xs leading-relaxed">
              <MathText text={t(`terms.${term}.effect`)} />
            </p>
          </PopoverPopup>
        </PopoverPositioner>
      </PopoverPortal>
    </Popover>
  )
}
