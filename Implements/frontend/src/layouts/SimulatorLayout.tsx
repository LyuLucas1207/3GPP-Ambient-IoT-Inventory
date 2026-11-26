import { ArrowLeftIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { cn } from '@/utils/utils'

/** Shared way back from a simulator to the home chooser. */
export function HomeLink({ className }: { className?: string }) {
  const { t } = useTranslation()
  return (
    <Link
      to="/"
      className={cn(
        'inline-flex items-center gap-1 rounded-md px-1 py-0.5 text-xs font-medium text-muted-foreground hover:text-foreground',
        className,
      )}
    >
      <ArrowLeftIcon className="size-3.5" aria-hidden />
      {t('nav.home')}
    </Link>
  )
}
