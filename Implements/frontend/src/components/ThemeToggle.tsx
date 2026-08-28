import { MoonIcon, SunIcon } from 'lucide-react'
import { useTheme } from 'next-themes'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'

enum ColorMode {
  Light = 'light',
  Dark = 'dark',
}

export function ThemeToggle() {
  const { t } = useTranslation()
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return <div className="h-8 w-[9.5rem]" />
  }

  const mode = theme === ColorMode.Light ? ColorMode.Light : ColorMode.Dark

  return (
    <div className="flex rounded-lg border border-border p-0.5">
      <Button
        size="sm"
        variant={mode === ColorMode.Light ? 'default' : 'ghost'}
        aria-pressed={mode === ColorMode.Light}
        onClick={() => setTheme(ColorMode.Light)}
      >
        <SunIcon />
        {t('theme.light')}
      </Button>
      <Button
        size="sm"
        variant={mode === ColorMode.Dark ? 'default' : 'ghost'}
        aria-pressed={mode === ColorMode.Dark}
        onClick={() => setTheme(ColorMode.Dark)}
      >
        <MoonIcon />
        {t('theme.dark')}
      </Button>
    </div>
  )
}
