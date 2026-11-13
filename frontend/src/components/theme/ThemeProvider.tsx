import { useEffect } from 'react'
import { useThemeStore } from '@/store'
import type { ThemePreference } from '@/store'

function resolveTheme(preference: ThemePreference): 'light' | 'dark' {
  if (preference === 'light') return 'light'
  if (preference === 'dark') return 'dark'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(theme: 'light' | 'dark') {
  document.documentElement.setAttribute('data-theme', theme)
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { preference } = useThemeStore()

  useEffect(() => {
    // Apply immediately on preference change
    applyTheme(resolveTheme(preference))

    if (preference !== 'system') return

    // Listen for OS-level changes when in system mode
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => applyTheme(resolveTheme('system'))
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [preference])

  return <>{children}</>
}
