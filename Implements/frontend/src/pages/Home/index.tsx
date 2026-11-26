import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { LanguageToggle } from '@/components/LanguageToggle'
import { ThemeToggle } from '@/components/ThemeToggle'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { APERIODIC_PAGING_PATH, GLOSSARY_PATH, PERIODIC_PAGING_PATH, THESIS_SIMULATION_PATH } from '@/navigations/paths'

export default function HomePage() {
  const { t } = useTranslation()
  useEffect(() => {
    document.title = t('app.documentTitle')
  }, [t])
  const cards = [
    { to: PERIODIC_PAGING_PATH, title: t('nav.periodicPaper'), body: t('app.kicker') },
    { to: APERIODIC_PAGING_PATH, title: t('nav.aperiodicPaper'), body: t('aperiodic.kicker') },
    { to: THESIS_SIMULATION_PATH, title: t('nav.thesisSimulation'), body: t('thesis.subtitle') },
  ]
  return (
    <main className="min-h-svh bg-background px-6 py-10 text-foreground">
      <div className="mx-auto flex max-w-5xl flex-col gap-8">
        <header className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-medium">{t('app.title')}</h1>
            <p className="mt-1 text-sm text-muted-foreground">{t('home.lead')}</p>
          </div>
          <div className="flex items-center gap-2">
            <LanguageToggle />
            <ThemeToggle />
          </div>
        </header>
        <div className="grid gap-4 md:grid-cols-3">
          {cards.map((card) => (
            <Link
              key={card.to}
              to={card.to}
              className="block rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Card className="h-full transition-colors hover:bg-muted/40">
                <CardHeader>
                  <CardTitle>{card.title}</CardTitle>
                  <CardDescription>{card.body}</CardDescription>
                </CardHeader>
              </Card>
            </Link>
          ))}
        </div>
        <p className="text-sm">
          <Link to={GLOSSARY_PATH} className="text-muted-foreground underline-offset-4 hover:text-foreground hover:underline">
            {t('home.glossary')}
          </Link>
        </p>
      </div>
    </main>
  )
}
