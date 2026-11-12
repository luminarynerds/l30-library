/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'
import api from '@/api/api'

interface NudgeContent {
  title: string | null
  body: string
  cta_label: string | null
  cta_route: string | null
}

interface ActiveNudge {
  id: number
  slug: string
  delivery_type: 'toast' | 'inline' | 'panel' | 'modal_lite'
  delivery_placement: string
  content: NudgeContent
  priority: number
}

interface NudgeContextType {
  activeNudges: ActiveNudge[]
  dismissNudge: (nudgeId: number) => void
  actOnNudge: (nudgeId: number) => void
  markShown: (nudgeId: number) => void
  getNudgesForPlacement: (placement: string) => ActiveNudge[]
}

const NudgeContext = createContext<NudgeContextType | null>(null)

export function NudgeProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  const location = useLocation()
  const [activeNudges, setActiveNudges] = useState<ActiveNudge[]>([])
  const shownRef = useRef<Set<number>>(new Set())

  const fetchNudges = useCallback(async () => {
    if (!user) {
      setActiveNudges([])
      return
    }
    try {
      const pageContext = location.pathname.replace(/^\//, '').split('/')[0] || 'global'
      const nudges = await api.get<ActiveNudge[]>('/nudges/active', {
        params: { page_context: pageContext },
      })
      setActiveNudges(nudges || [])
    } catch {
      // Nudges are non-critical
    }
  }, [user, location.pathname])

  useEffect(() => {
    fetchNudges()
  }, [fetchNudges])

  const markShown = useCallback((nudgeId: number) => {
    if (shownRef.current.has(nudgeId)) return
    shownRef.current.add(nudgeId)
    api.post(`/nudges/${nudgeId}/event`, { action: 'shown' }).catch(() => {})
  }, [])

  const dismissNudge = useCallback((nudgeId: number) => {
    setActiveNudges(prev => prev.filter(n => n.id !== nudgeId))
    api.post(`/nudges/${nudgeId}/event`, { action: 'dismissed' }).catch(() => {})
  }, [])

  const actOnNudge = useCallback((nudgeId: number) => {
    setActiveNudges(prev => prev.filter(n => n.id !== nudgeId))
    api.post(`/nudges/${nudgeId}/event`, { action: 'acted_on' }).catch(() => {})
  }, [])

  const getNudgesForPlacement = useCallback((placement: string) => {
    return activeNudges.filter(n => n.delivery_placement === placement)
  }, [activeNudges])

  return (
    <NudgeContext.Provider value={{ activeNudges, dismissNudge, actOnNudge, markShown, getNudgesForPlacement }}>
      {children}
    </NudgeContext.Provider>
  )
}

export function useNudges() {
  const ctx = useContext(NudgeContext)
  if (!ctx) throw new Error('useNudges must be used within NudgeProvider')
  return ctx
}

export type { ActiveNudge, NudgeContent }
