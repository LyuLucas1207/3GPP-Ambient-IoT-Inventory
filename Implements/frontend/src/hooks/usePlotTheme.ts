import { useTheme } from 'next-themes'
import { useEffect, useState } from 'react'

export function usePlotTheme() {
  const { resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => {
    setMounted(true)
  }, [])
  const dark = mounted && resolvedTheme === 'dark'
  return {
    dark,
    paper: 'rgba(0,0,0,0)',
    plot: dark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)',
    font: dark ? '#fafafa' : '#171717',
    grid: dark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.12)',
    line: dark ? '#d4d4d8' : '#3f3f46',
  }
}
