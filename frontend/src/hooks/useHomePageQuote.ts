/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useMemo, useState } from 'react'
import { useHomepageQuotes } from '@/hooks/useHomepageQuotes'
import { useUnifiedAccessibility } from '@/features/accessibility'
import type { HomepageQuotePublic } from '@/api/domains/services/homepage-quotes-api'

const ROTATION_INTERVAL_MS = 12000

function pickDailyQuoteIndex(quoteCount: number, language: string): number {
  if (quoteCount === 0) return 0
  const today = new Date().toISOString().slice(0, 10)
  const storageKey = `lsc-homepage-quote-${language}-${today}`
  try {
    const cached = sessionStorage.getItem(storageKey)
    const cachedNum = cached === null ? NaN : parseInt(cached, 10)
    if (Number.isInteger(cachedNum) && cachedNum >= 0 && cachedNum < quoteCount) {
      return cachedNum
    }
    const pick = Math.floor(Math.random() * quoteCount)
    sessionStorage.setItem(storageKey, String(pick))
    return pick
  } catch {
    return Math.floor(Math.random() * quoteCount)
  }
}

export function useHomePageQuote(language: string): HomepageQuotePublic | null {
  const { data: libraryQuotes = [] } = useHomepageQuotes(language)
  const { settings, getCurrentPreset } = useUnifiedAccessibility()
  const hideQuotes = getCurrentPreset() === 'calm'
  const staticQuote = settings.reduceMotion

  const dailyStaticIndex = useMemo(
    () => pickDailyQuoteIndex(libraryQuotes.length, language),
    [libraryQuotes.length, language],
  )

  const [rotateOffset, setRotateOffset] = useState(() => Math.floor(Math.random() * 1000))

  useEffect(() => {
    if (hideQuotes || staticQuote || libraryQuotes.length <= 1) return
    const id = window.setInterval(() => {
      setRotateOffset((o) => o + 1)
    }, ROTATION_INTERVAL_MS)
    return () => window.clearInterval(id)
  }, [hideQuotes, staticQuote, libraryQuotes.length])

  if (hideQuotes || libraryQuotes.length === 0) return null
  const idx = staticQuote ? dailyStaticIndex : rotateOffset % libraryQuotes.length
  return libraryQuotes[idx] ?? null
}
