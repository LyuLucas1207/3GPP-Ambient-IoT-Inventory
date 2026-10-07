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

/** Drop binary noise such as 0.1e-6 * 1e6 → 0.09999999999999999. */
function formatPaperValue(value: number): string {
  if (!Number.isFinite(value)) return String(value)
  if (Number.isInteger(value)) return String(value)
  return String(Number(value.toPrecision(6)))
}

export function AssumptionsPanel({ paper, assumptions }: Props) {
  const { t } = useTranslation()
  return (
    <Card plain size="sm">
      <CardHeader>
        <CardTitle>{t('assumptions.title')}</CardTitle>
      </CardHeader>
      <CardContent>
        <details className="min-w-0 max-w-full">
          <summary className="cursor-pointer text-sm text-muted-foreground">{t('assumptions.summary')}</summary>
          <div className="mt-3 grid w-full min-w-0 max-w-full grid-cols-1 gap-4">
            <section className="min-w-0">
              <h3 className="mb-1 text-sm font-medium">{t('assumptions.paperSpecified')}</h3>
              {paper == null ? (
                <p className="text-sm text-muted-foreground">{t('assumptions.loadPaper')}</p>
              ) : (
                <dl className="w-full divide-y divide-border/70">
                  {Object.entries(paper).map(([k, v]) => {
                    const term = PAPER_TERM[k]
                    const unit = PAPER_UNIT[k]
                    return (
                      <div key={k} className="flex w-full min-w-0 items-center justify-between gap-3 py-1.5">
                        <dt className="flex min-w-0 items-center gap-1 text-muted-foreground">
                          {PAPER_TEX[k] ? (
                            <MathInline tex={PAPER_TEX[k]} className="text-foreground" />
                          ) : (
                            <code className="text-foreground">{k}</code>
                          )}
                          {term ? (
                            <TermHelp term={term} />
                          ) : (
                            <ParamHint text={t(`paperHints.${k}`, { defaultValue: k })} />
                          )}
                        </dt>
                        <dd className="shrink-0 text-right text-xs font-medium tabular-nums text-foreground">
                          {formatPaperValue(v)}
                          {unit ? <span className="ml-1 font-normal text-muted-foreground">{unit}</span> : null}
                        </dd>
                      </div>
                    )
                  })}
                </dl>
              )}
            </section>
            <section className="min-w-0">
              <h3 className="mb-1 text-sm font-medium">{t('assumptions.repro')}</h3>
              {assumptions == null ? (
                <p className="text-sm text-muted-foreground">{t('assumptions.notLoaded')}</p>
              ) : (
                <ul className="w-full min-w-0 divide-y divide-border/70">
                  {Object.entries(assumptions).map(([k, v]) => (
                    <li key={k} className="min-w-0 py-2">
                      <p className="text-[11px] leading-4 break-words text-muted-foreground">
                        <MathText text={t(`assumptionHints.${k}`, { defaultValue: k })} />
                      </p>
                      <p className="mt-1 text-xs font-medium break-all text-foreground">{String(v)}</p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </details>
      </CardContent>
    </Card>
  )
}
