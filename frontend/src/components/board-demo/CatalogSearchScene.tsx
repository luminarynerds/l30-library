/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Search, BookOpen, CheckCircle2, Sparkles } from 'lucide-react'
import { useTranslation } from '@/i18n'

export function CatalogSearchScene() {
  const { t } = useTranslation()
  const [showResults, setShowResults] = useState(false)
  const [typed, setTyped] = useState(0)
  const searchText = 'mystery books like Louise Penny'
  const query = searchText.slice(0, typed)

  useEffect(() => {
    if (typed >= searchText.length) {
      const timer = setTimeout(() => setShowResults(true), 600)
      return () => clearTimeout(timer)
    }
    const timer = setTimeout(() => setTyped((n) => n + 1), 60)
    return () => clearTimeout(timer)
  }, [typed, searchText.length])

  const results = [
    { title: 'Still Life', author: 'Louise Penny', year: 2005, available: true, holds: 0, format: 'Book' },
    { title: t('boardDemo.theMadnessOfCrowds'), author: 'Louise Penny', year: 2021, available: true, holds: 0, format: 'Book' },
    { title: 'A Fatal Grace', author: 'Louise Penny', year: 2007, available: false, holds: 2, format: 'Book' },
    { title: 'In the Woods', author: 'Tana French', year: 2007, available: true, holds: 0, format: 'Book' },
    { title: t('boardDemo.theThursdayMurderClub'), author: 'Richard Osman', year: 2020, available: true, holds: 1, format: 'Book' },
    { title: t('boardDemo.theDeathsOfEvelynHardcastle'), author: 'Stuart Turton', year: 2018, available: true, holds: 0, format: 'eBook' },
  ]

  return (
    <div className="space-y-6">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border-2 border-sky-300 dark:border-sky-700 p-4 shadow-lg">
        <div className="flex items-center gap-3">
          <Search className="w-5 h-5 text-sky-500" />
          <div className="flex-1 text-lg text-lsc-dark dark:text-lsc-cream">
            {query}
            {typed < searchText.length && <span className="inline-block w-0.5 h-5 bg-sky-500 motion-safe:animate-pulse ml-0.5" />}
          </div>
        </div>
        <div className="flex gap-2 mt-3">
          {['All Formats', 'Available Now', 'At My Branch'].map((f) => (
            <span key={f} className="text-xs px-2.5 py-1 rounded-full bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 border border-lsc-border dark:border-earth-700">
              {f}
            </span>
          ))}
        </div>
      </div>

      {showResults && (
        <div className="space-y-2">
          <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center justify-between">
            <span>6 results &middot; Sorted by relevance</span>
            <span className="text-sky-600 dark:text-sky-400 flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5" /> Semantic search active
            </span>
          </div>
          {results.map((r, i) => (
            <div
              key={i}
              className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700 flex items-center gap-4 transition-all duration-300 hover:shadow-sm"
              style={{ animationDelay: `${i * 100}ms` }}
            >
              <div className="w-10 h-14 bg-sky-100 dark:bg-sky-900/30 rounded flex items-center justify-center shrink-0">
                <BookOpen className="w-5 h-5 text-sky-500" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-lsc-dark dark:text-lsc-cream">{r.title}</div>
                <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{r.author} &middot; {r.year} &middot; {r.format}</div>
              </div>
              <div className="text-right shrink-0">
                {r.available ? (
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-status-success-700 dark:text-status-success-400 bg-status-success-50 dark:bg-status-success-900/20 px-2 py-1 rounded-full">
                    <CheckCircle2 className="w-3 h-3" /> Available
                  </span>
                ) : (
                  <span className="text-xs text-status-warning-600 dark:text-status-warning-400">{r.holds} holds</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
