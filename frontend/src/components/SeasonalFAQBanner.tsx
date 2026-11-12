/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback } from "react"
import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { Calendar, X, ChevronRight } from "lucide-react"
import { getSeasonalFAQs, type SeasonalFAQ } from "@/api/faq-chatbot-api"

const STORAGE_KEY = "lsc_seasonal_faq_dismissed"

const SEASON_LABELS: Record<string, string> = {
  spring: "Spring",
  summer: "Summer",
  fall: "Fall",
  winter: "Winter",
  tax_season: "Tax Season",
  holiday: "Holiday",
  custom: "Seasonal",
}

function getDismissedIds(): Set<string> {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) return new Set(JSON.parse(stored))
  } catch { /* ignore */ }
  return new Set()
}

function saveDismissedIds(ids: Set<string>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(ids)))
  } catch { /* ignore */ }
}

export default function SeasonalFAQBanner() {
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(getDismissedIds)

  const { data: seasonalFaqs } = useQuery({
    queryKey: ["seasonal-faqs"],
    queryFn: getSeasonalFAQs,
    staleTime: 5 * 60 * 1000,
  })

  const handleDismiss = useCallback((id: number) => {
    setDismissedIds((prev) => {
      const next = new Set(prev)
      next.add(String(id))
      saveDismissedIds(next)
      return next
    })
  }, [])

  const visible = seasonalFaqs?.filter(
    (faq: SeasonalFAQ) => faq.is_active && !dismissedIds.has(String(faq.id))
  )

  if (!visible?.length) return null

  return (
    <div className="space-y-3 mb-6">
      {visible.map((faq: SeasonalFAQ) => (
        <div
          key={faq.id}
          className="relative bg-gradient-to-r from-lsc-rose/10 to-lsc-cream dark:from-lsc-rose/20 dark:to-earth-800 rounded-xl p-4 border border-lsc-rose/20"
          role="region"
          aria-label={`${SEASON_LABELS[faq.season] ?? faq.season} update`}
        >
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-lsc-rose/20 flex items-center justify-center">
              <Calendar className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
            </div>
            <div className="flex-1 min-w-0">
              <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-lsc-rose/10 text-lsc-rose mb-1">
                {SEASON_LABELS[faq.season] ?? faq.season}
              </span>
              {faq.seasonal_note && (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  {faq.seasonal_note}
                </p>
              )}
              <Link
                to="/help"
                className="inline-flex items-center gap-1 mt-2 text-sm text-lsc-rose hover:text-lsc-rose/80 font-medium"
              >
                View FAQ
                <ChevronRight className="w-4 h-4" aria-hidden="true" />
              </Link>
            </div>
            <button
              onClick={() => handleDismiss(faq.id)}
              className="flex-shrink-0 p-2.5 rounded-lg text-lsc-dark/70 hover:text-lsc-dark hover:bg-lsc-dark/10 dark:text-lsc-cream/70 dark:hover:text-lsc-cream dark:hover:bg-lsc-cream/10 transition-colors"
              aria-label={`Dismiss ${SEASON_LABELS[faq.season] ?? faq.season} update`}
            >
              <X className="w-5 h-5" aria-hidden="true" />
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
