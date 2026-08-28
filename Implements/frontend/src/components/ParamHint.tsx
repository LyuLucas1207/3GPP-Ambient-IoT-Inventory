import { ClickHelp } from '@/components/ClickHelp'
import { MathText } from '@/components/MathText'
import { CircleHelpIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface HintProps {
  text: string
}

export function ParamHint({ text }: HintProps) {
  const { t } = useTranslation()
  return (
    <ClickHelp title={t('explain.button')} body={text} ariaLabel={t('explain.button')}>
      <CircleHelpIcon className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
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
      <ParamHint text={hint} />
    </div>
  )
}
