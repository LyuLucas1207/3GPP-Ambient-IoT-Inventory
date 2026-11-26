import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { LanguageToggle } from '@/components/LanguageToggle'
import { HomeLink } from '@/layouts/SimulatorLayout'
import { StrategyFlow } from '@/components/strategy/StrategyFlow'
import { ThemeToggle } from '@/components/ThemeToggle'
import { ThesisSubNav } from '@/features/thesis/components/ThesisSubNav'
import { rlPolicyMap } from '@/features/thesis/maps/rlPolicy'

/** Multi-reader RL decision, drawn with the same React Flow maps as the paper overviews. */
export default function ThesisRlPage() {
  const { t } = useTranslation()

  useEffect(() => {
    document.title = t('thesis.rl.title')
  }, [t])

  return (
    <div className="flex h-dvh w-screen flex-col overflow-hidden bg-background">
      <header className="flex w-full shrink-0 items-center gap-4 border-b bg-card px-4 py-2">
        <div className="min-w-0">
          <HomeLink className="mb-1" />
          <div className="flex items-center gap-3">
            <h1 className="truncate text-lg font-medium">{t('thesis.rl.title')}</h1>
            <ThesisSubNav />
          </div>
          <p className="truncate text-xs text-muted-foreground">{t('thesis.rl.subtitle')}</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <LanguageToggle />
          <ThemeToggle />
        </div>
      </header>
      <div className="min-h-0 flex-1">
        <StrategyFlow
          def={rlPolicyMap}
          fit={{
            padding: 0.16,
            minZoom: 0.8,
            maxZoom: 1,
            nodes: [{ id: 'sample' }, { id: 'who' }, { id: 'decision' }, { id: 'cold' }],
          }}
        />
      </div>
    </div>
  )
}
