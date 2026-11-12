/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import { getCurrentLocale } from '@/i18n'

type DashboardTone = 'calm' | 'standard' | 'full'

interface ToneContextValue {
  tone: DashboardTone
  setTone: (tone: DashboardTone) => void
  formatDeadline: (dateStr: string) => string
  showUrgencyColors: boolean
  showCountBadges: boolean
}

const ToneContext = createContext<ToneContextValue | null>(null)

export function ToneProvider({ initialTone = 'standard', onToneChange, children }: {
  initialTone?: DashboardTone
  onToneChange?: (tone: DashboardTone) => void
  children: ReactNode
}) {
  const [tone, setToneState] = useState<DashboardTone>(initialTone)

  // Sync when the saved tone changes (e.g. after the settings panel persists a new
  // tone). useState only reads initialTone at mount, so without this the dashboard
  // panels wouldn't update until a full page reload.
  useEffect(() => {
    setToneState(initialTone)
  }, [initialTone])

  const setTone = useCallback((newTone: DashboardTone) => {
    setToneState(newTone)
    onToneChange?.(newTone)
  }, [onToneChange])

  const formatDeadline = useCallback((dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = date.getTime() - now.getTime()
    const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24))

    if (tone === 'calm') {
      return date.toLocaleDateString(getCurrentLocale(), { month: 'short', day: 'numeric' })
    }

    if (tone === 'full') {
      if (diffDays < 0) return `OVERDUE ${Math.abs(diffDays)} DAY${Math.abs(diffDays) !== 1 ? 'S' : ''}`
      if (diffDays === 0) return 'TODAY'
      return `IN ${diffDays} DAY${diffDays !== 1 ? 'S' : ''}`
    }

    if (diffDays < 0) return `${Math.abs(diffDays)}d overdue`
    if (diffDays === 0) return 'today'
    if (diffDays === 1) return 'tomorrow'
    return `in ${diffDays} days`
  }, [tone])

  return (
    <ToneContext.Provider value={{
      tone,
      setTone,
      formatDeadline,
      showUrgencyColors: tone !== 'calm',
      showCountBadges: tone === 'full',
    }}>
      {children}
    </ToneContext.Provider>
  )
}

export function useTone(): ToneContextValue {
  const ctx = useContext(ToneContext)
  if (!ctx) throw new Error('useTone must be used within a ToneProvider')
  return ctx
}
