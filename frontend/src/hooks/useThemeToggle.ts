/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useMemo } from 'react'
import { useAccessibility } from '../features/accessibility/hooks/useAccessibility'

interface UseThemeToggleReturn {
  isDark: boolean
  toggleTheme: () => void
}

export function useThemeToggle(): UseThemeToggleReturn {
  const { settings, updateSetting } = useAccessibility()

  // Determine if dark mode is active
  const isDark = useMemo(() => {
    return settings.theme === 'dark' ||
      (settings.theme === 'system' && typeof window !== 'undefined' &&
       window.matchMedia('(prefers-color-scheme: dark)').matches)
  }, [settings.theme])

  // Toggle theme between light and dark
  const toggleTheme = useCallback(() => {
    updateSetting('theme', isDark ? 'light' : 'dark')
  }, [isDark, updateSetting])

  return { isDark, toggleTheme }
}
