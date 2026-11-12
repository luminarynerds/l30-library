/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { getPublicChallenges } from '@/api/domains/content/book-challenges-api'
import { API_BASE } from '@/api/types'
import api from '@/lib/api-client'
import type { BanReport } from '@/components/ban-tracker/types'

export function useChallengedItemIds(featureEnabled: boolean): Set<number> {
  const [ids, setIds] = useState<Set<number>>(new Set())

  useEffect(() => {
    if (!featureEnabled) {
      setIds(new Set())
      return
    }

    let cancelled = false

    Promise.all([
      getPublicChallenges().catch(() => [] as { catalog_item_id: number | null }[]),
      api.get<BanReport[]>(`${API_BASE}/ban-tracker/public/catalog-matches`).catch(() => [] as BanReport[]),
    ]).then(([challenges, matches]) => {
      if (cancelled) return
      const result = new Set<number>()
      for (const c of Array.isArray(challenges) ? challenges : []) {
        if (c.catalog_item_id) result.add(c.catalog_item_id)
      }
      for (const m of Array.isArray(matches) ? matches : []) {
        if (m.catalog_item_id) result.add(m.catalog_item_id)
      }
      setIds(result)
    })

    return () => { cancelled = true }
  }, [featureEnabled])

  return ids
}
