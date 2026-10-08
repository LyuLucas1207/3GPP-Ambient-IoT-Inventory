import { MathText } from '@/components/MathText'
import { ParamHint } from '@/components/ParamHint'
import { Badge } from '@/components/ui/badge'
import { texToPlain } from '@/lib/tex'
import { useTranslation } from 'react-i18next'

export type PaperRefId =
  | 'fig4'
  | 'fig5a'
  | 'fig5b'
  | 'fig6a'
  | 'fig6b'
  | 'fig7'
  | 'fig8'
  | 'tab4'
  | 'tab5'
  | 'tab6'
  | 'tf'
  | 'inventory'
  | 'controller'
  | 'trace'
  | 'factory'
  | 'metrics'

/** Badge naming the paper figure/table/equation a view corresponds to; the caption is the hover text. */
export function PaperRef({ id }: { id: PaperRefId }) {
  const { t } = useTranslation()
  return (
    <Badge variant="outline" className="cursor-help font-normal" title={texToPlain(t(`ap.paperRef.${id}.caption`))}>
      {t('ap.paperRef.prefix')} {t(`ap.paperRef.${id}.label`)}
    </Badge>
  )
}

export function PaperCaption({ id, hint }: { id: PaperRefId; hint?: string }) {
  const { t } = useTranslation()
  return (
    <p className="text-xs leading-snug">
      <span className="font-medium">
        {t('ap.paperRef.prefix')} {t(`ap.paperRef.${id}.label`)}.
      </span>{' '}
      {hint && (
        <span className="mr-1 inline-flex align-middle">
          <ParamHint text={hint} title={t(`ap.paperRef.${id}.label`)} />
        </span>
      )}
      <MathText className="text-muted-foreground" text={t(`ap.paperRef.${id}.caption`)} />
    </p>
  )
}
