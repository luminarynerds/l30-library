/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import api from '@/lib/api-client'
import { normalizeStats } from '@/components/ban-tracker/ban-tracker-data'
import type { BanStatsRaw, BanStats, MostBannedBook, LetterTemplate } from '@/components/ban-tracker/types'

export function useBanContextData(enabled: boolean): {
  banStats: BanStats | null
  mostBanned: MostBannedBook[]
  loading: boolean
} {
  const [banStats, setBanStats] = useState<BanStats | null>(null)
  const [mostBanned, setMostBanned] = useState<MostBannedBook[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!enabled) {
      setLoading(false)
      return
    }
    let cancelled = false
    const load = async (): Promise<void> => {
      try {
        const [statsRaw, banned] = await Promise.all([
          api.get('/api/v1/ban-tracker/public/stats'),
          api.get('/api/v1/ban-tracker/public/most-banned?limit=5'),
        ])
        if (cancelled) return
        const stats = normalizeStats(statsRaw as BanStatsRaw)
        stats.by_state.sort((a, b) => b.count - a.count)
        setBanStats(stats)
        setMostBanned(Array.isArray(banned) ? banned : [])
      } catch {
        // Ban data not available; sections will gracefully hide
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [enabled])

  return { banStats, mostBanned, loading }
}

export function useLetterTemplates(): { templates: LetterTemplate[]; loading: boolean } {
  const [templates, setTemplates] = useState<LetterTemplate[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    const load = async (): Promise<void> => {
      try {
        const data = await api.get('/api/v1/advocacy/letter-templates')
        if (cancelled) return
        setTemplates(Array.isArray(data) ? data : data.templates ?? [])
      } catch {
        if (!cancelled) setTemplates([])
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  return { templates, loading }
}
