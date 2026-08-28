import { MathText } from '@/components/MathText'
import { LanguageToggle } from '@/components/LanguageToggle'
import { ThemeToggle } from '@/components/ThemeToggle'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  GLOSSARY,
  GLOSSARY_KINDS,
  GLOSSARY_PATH,
  type GlossaryDef,
  type GlossaryKind,
} from '@/explain/glossary'
import { TERM_SOURCE } from '@/explain/ids'
import { ArrowLeftIcon } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router-dom'

function termKey(def: GlossaryDef) {
  return def.termId ? `terms.${def.termId}` : `glossary.entries.${def.id}`
}

function matches(def: GlossaryDef, q: string, t: (k: string) => string) {
  if (!q) return true
  const key = termKey(def)
  const blob = [
    def.id,
    def.kind,
    ...def.aliases,
    t(`${key}.short`),
    t(`${key}.full`),
    t(`${key}.body`),
    t(`glossary.kind.${def.kind}`),
  ]
    .join(' ')
    .toLowerCase()
  return blob.includes(q)
}

function TermCard({ def }: { def: GlossaryDef }) {
  const { t } = useTranslation()
  const key = termKey(def)
  const source = def.termId ? TERM_SOURCE[def.termId] : null
  const title = def.kind === 'symbol' && def.tex ? `$${def.tex}$` : t(`${key}.short`)
  return (
    <li id={def.id}>
      <Card size="sm" className="h-full scroll-mt-24">
        <CardHeader>
          <CardTitle className={def.kind === 'symbol' ? 'text-lg' : 'font-mono text-base'}>
            <MathText text={title} />
          </CardTitle>
          <CardDescription>
            <MathText text={t(`${key}.full`)} />
          </CardDescription>
          <div className="flex flex-wrap gap-1">
            <Badge variant="outline">{t(`glossary.kind.${def.kind}`)}</Badge>
            <Badge variant="secondary">{t(`${key}.unit`)}</Badge>
            {source ? <Badge variant="outline">{t(`explain.source.${source}`)}</Badge> : null}
          </div>
        </CardHeader>
        <CardContent className="grid gap-2 text-sm leading-relaxed">
          <p>
            <MathText text={t(`${key}.body`)} />
          </p>
          <p className="text-xs text-muted-foreground">
            <MathText text={t(`${key}.effect`)} />
          </p>
        </CardContent>
      </Card>
    </li>
  )
}

export default function GlossaryPage() {
  const { t, i18n } = useTranslation()
  const location = useLocation()
  const [query, setQuery] = useState('')
  const [kind, setKind] = useState<GlossaryKind | 'all'>('all')
  const q = query.trim().toLowerCase()

  useEffect(() => {
    document.title = t('glossary.documentTitle')
  }, [t, i18n.language])

  useEffect(() => {
    const id = decodeURIComponent(location.hash.replace(/^#/, ''))
    if (!id) return
    document.getElementById(id)?.scrollIntoView({ block: 'start' })
  }, [location.hash])

  const rows = useMemo(() => {
    return GLOSSARY.filter((def) => (kind === 'all' || def.kind === kind) && matches(def, q, t))
  }, [kind, q, t, i18n.language])

  const abbrRows = rows.filter((d) => d.kind === 'abbr')
  const symbolRows = rows.filter((d) => d.kind === 'symbol')

  return (
    <div className="min-h-dvh bg-background text-foreground">
      <header className="sticky top-0 z-20 border-b bg-card/90 backdrop-blur-md">
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="min-w-0">
            <p className="text-[11px] tracking-[0.16em] text-muted-foreground uppercase">{GLOSSARY_PATH}</p>
            <h1 className="text-lg font-medium">{t('glossary.title')}</h1>
            <p className="text-sm text-muted-foreground">
              <MathText text={t('glossary.lead')} />
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" nativeButton={false} render={<Link to="/" />}>
              <ArrowLeftIcon className="size-3.5" aria-hidden />
              {t('glossary.back')}
            </Button>
            <LanguageToggle />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="grid gap-6 px-4 py-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <Input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('glossary.search')}
            aria-label={t('glossary.search')}
            className="w-full sm:flex-1"
          />
          <p className="shrink-0 text-xs text-muted-foreground">{t('glossary.count', { n: rows.length })}</p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <Button
            type="button"
            size="xs"
            variant={kind === 'all' ? 'default' : 'outline'}
            onClick={() => setKind('all')}
          >
            {t('glossary.all')}
          </Button>
          {GLOSSARY_KINDS.map((id) => (
            <Button
              key={id}
              type="button"
              size="xs"
              variant={kind === id ? 'default' : 'outline'}
              onClick={() => setKind(id)}
            >
              {t(`glossary.kind.${id}`)}
            </Button>
          ))}
        </div>

        {rows.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t('glossary.empty')}</p>
        ) : kind === 'all' ? (
          <div className="grid gap-8">
            <section className="grid gap-3">
              <h2 className="text-sm font-medium tracking-wide text-muted-foreground uppercase">
                {t('glossary.kind.abbr')} · {abbrRows.length}
              </h2>
              <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {abbrRows.map((def) => (
                  <TermCard key={def.id} def={def} />
                ))}
              </ul>
            </section>
            <section className="grid gap-3">
              <h2 className="text-sm font-medium tracking-wide text-muted-foreground uppercase">
                {t('glossary.kind.symbol')} · {symbolRows.length}
              </h2>
              <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {symbolRows.map((def) => (
                  <TermCard key={def.id} def={def} />
                ))}
              </ul>
            </section>
          </div>
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {rows.map((def) => (
              <TermCard key={def.id} def={def} />
            ))}
          </ul>
        )}
      </main>
    </div>
  )
}
