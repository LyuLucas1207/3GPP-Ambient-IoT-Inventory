import { ParamHint } from '@/components/ParamHint'
import { TermHelp } from '@/components/TermHelp'
import { MathInline, MathText } from '@/components/MathText'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PAPER_TERM, PAPER_TEX, PAPER_UNIT } from '@/lib/paperSymbols'
import { useTranslation } from 'react-i18next'

interface Props {
  paper: Record<string, number> | null
  assumptions: Record<string, string | boolean> | null
}

export function AssumptionsPanel({ paper, assumptions }: Props) {
  const { t } = useTranslation()
  return (
    <Card className="bg-card/90 backdrop-blur-md" size="sm">
      <CardHeader>
        <CardTitle>{t('assumptions.title')}</CardTitle>
      </CardHeader>
      <CardContent>
        <details>
          <summary className="cursor-pointer text-sm text-muted-foreground">{t('assumptions.summary')}</summary>
          <div className="mt-3 grid gap-4">
            <div>
              <h3 className="mb-1 text-sm font-medium">{t('assumptions.paperSpecified')}</h3>
              {paper == null ? (
                <p className="text-sm text-muted-foreground">{t('assumptions.loadPaper')}</p>
              ) : (
                <ul className="space-y-1 text-xs text-muted-foreground">
                  {Object.entries(paper).map(([k, v]) => {
                    const term = PAPER_TERM[k]
                    return (
                    <li key={k} className="flex items-start justify-between gap-2">
                        <span className="flex items-center gap-1.5">
                          {PAPER_TEX[k] ? <MathInline tex={PAPER_TEX[k]} /> : <code className="text-foreground">{k}</code>}
                          {term ? (
                            <TermHelp term={term} />
                          ) : (
                            <ParamHint text={t(`paperHints.${k}`, { defaultValue: k })} />
                          )}
                        </span>
                        <span>
                          {v}
                          {PAPER_UNIT[k] ? ` ${PAPER_UNIT[k]}` : ''}
                        </span>
                    </li>
                    )
                  })}
                </ul>
              )}
            </div>
            <div>
              <h3 className="mb-1 text-sm font-medium">{t('assumptions.repro')}</h3>
              {assumptions == null ? (
                <p className="text-sm text-muted-foreground">{t('assumptions.notLoaded')}</p>
              ) : (
                <ul className="space-y-1 text-xs text-muted-foreground">
                  {Object.entries(assumptions).map(([k, v]) => (
                    <li key={k} className="grid grid-cols-[1fr_auto] items-start gap-2">
                      <MathText text={t(`assumptionHints.${k}`, { defaultValue: k })} />
                      <span className="shrink-0 text-foreground">{String(v)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </details>
      </CardContent>
    </Card>
  )
}
