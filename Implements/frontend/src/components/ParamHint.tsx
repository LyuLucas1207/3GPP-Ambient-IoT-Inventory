import { ClickHelp } from '@/components/ClickHelp'
import { MathText } from '@/components/MathText'
import { cn } from '@/lib/utils'
import { CircleHelpIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface HintProps {
  text: string
  title?: string
  iconClassName?: string
}

export function ParamHint({ text, title, iconClassName }: HintProps) {
  const { t } = useTranslation()
  return (
    <ClickHelp title={title ?? t('explain.button')} body={text} ariaLabel={title ? t('explain.termAria', { term: title.replace(/\$/g, '') }) : t('explain.button')}>
      <CircleHelpIcon className={cn('size-3.5 shrink-0 text-muted-foreground', iconClassName)} aria-hidden />
    </ClickHelp>
  )
}

interface FieldLabelProps {
  htmlFor?: string
  hint: string
  children: string
}

export function FieldLabel({ htmlFor, hint, children }: FieldLabelProps) {
  return (
    <div className="flex items-center gap-1.5">
      <label htmlFor={htmlFor} className="text-sm font-medium">
        <MathText text={children} />
      </label>
      <ParamHint text={hint} title={children} />
    </div>
  )
}
