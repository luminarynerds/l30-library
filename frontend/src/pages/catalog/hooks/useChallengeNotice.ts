/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { getPublicChallenges } from '@/api/domains/content/book-challenges-api'
import { API_BASE } from '@/api/types'
import api from '@/lib/api-client'
import type { BanReport } from '@/components/ban-tracker/types'

interface ChallengeNoticeResult {
  hasChallengeOrBan: boolean
  isLoading: boolean
}

export function useChallengeNotice(
  catalogItemId: number | undefined,
  featureEnabled: boolean
): ChallengeNoticeResult {
  const [hasChallengeOrBan, setHasChallengeOrBan] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!catalogItemId || !featureEnabled) {
      setHasChallengeOrBan(false)
      return
    }

    let cancelled = false
    setIsLoading(true)

    Promise.all([
      getPublicChallenges().catch(() => [] as { catalog_item_id: number | null }[]),
      api.get<BanReport[]>(`${API_BASE}/ban-tracker/public/catalog-matches`).catch(() => [] as BanReport[]),
    ]).then(([challenges, matches]) => {
      if (cancelled) return
      const hasChallenge = challenges.some(
        (c) => c.catalog_item_id === catalogItemId
      )
      const hasBan = matches.some(
        (m) => m.catalog_item_id === catalogItemId
      )
      setHasChallengeOrBan(hasChallenge || hasBan)
    }).finally(() => {
      if (!cancelled) setIsLoading(false)
    })

    return () => { cancelled = true }
  }, [catalogItemId, featureEnabled])

  return { hasChallengeOrBan, isLoading }
}
