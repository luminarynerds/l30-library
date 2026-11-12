/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
import * as Sentry from "@/lib/sentry-lazy"
import { createContext, useContext, useState, useEffect, useCallback, useMemo, ReactNode } from 'react'
import { useAuth } from './AuthContext'
import api from '@/lib/api-client'
import { API_BASE } from '@/api/types'

interface EssentialsModeContextType {
  isEssentialsMode: boolean
  toggleMode: () => Promise<void>
  isLoading: boolean
}

const EssentialsModeContext = createContext<EssentialsModeContextType | undefined>(undefined)

export function EssentialsModeProvider({ children }: { children: ReactNode }) {
  const { user, token, isAuthenticated } = useAuth()
  const [isEssentialsMode, setIsEssentialsMode] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  // Load preference on mount or when user changes
  useEffect(() => {
    if (isAuthenticated && user) {
      setIsEssentialsMode(user.ui_mode === 'essentials')
    } else {
      // L30: Guests see the full editorial experience
      setIsEssentialsMode(false)
    }
    setIsLoading(false)
  }, [user, isAuthenticated])

  const toggleMode = useCallback(async () => {
    const newMode = isEssentialsMode ? 'full' : 'essentials'

    // Guests can still switch modes for the current session
    if (!isAuthenticated || !token) {
      setIsEssentialsMode(prev => !prev)
      return
    }

    setIsLoading(true)
    try {
      await api.patch(`${API_BASE}/auth/me/ui-mode`, { ui_mode: newMode })
      setIsEssentialsMode(!isEssentialsMode)
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      // Silently fail, user can try again
    } finally {
      setIsLoading(false)
    }
  }, [isEssentialsMode, isAuthenticated, token])

  const contextValue = useMemo(() => ({
    isEssentialsMode, toggleMode, isLoading,
  }), [isEssentialsMode, toggleMode, isLoading])

  return (
    <EssentialsModeContext.Provider value={contextValue}>
      {children}
    </EssentialsModeContext.Provider>
  )
}

export function useEssentialsMode() {
  const context = useContext(EssentialsModeContext)
  if (!context) {
    throw new Error('useEssentialsMode must be used within EssentialsModeProvider')
  }
  return context
}