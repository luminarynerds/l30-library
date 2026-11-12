/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQueryClient, useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Button } from '../ui'
import { Search, Plus, RefreshCw, ChevronDown, ChevronRight, Loader2 } from 'lucide-react'
import {
  addToSelectionList,
  addInsightToPurchaseConsideration,
  searchExternalCatalogs,
} from '../../api/domains/admin/acquisition-api'
import type {
  CollectionIntelligenceReport,
  CollectionInsightItem,
  ExternalSearchResult,
} from '../../api/domains/admin/acquisition-api'
import { useTranslation } from '@/i18n'

function formatCurrency(n: number | null | undefined): string {
  if (n == null) return '—'
  return `$${n.toFixed(2)}`
}

const INSIGHT_LABELS: Record<string, string> = {
  patrons_searched_missing: 'Patron Searches Not Found',
  popular_titles_not_owned: 'Popular Titles Not Owned',
  series_missing_volumes: 'Series Missing Volumes',
  high_hold_ratio_items: 'High Hold-to-Copy Ratio',
  outdated_subjects: 'Outdated Subject Areas',
  peer_library_gaps: 'Peer Library Gaps',
  missing_award_winners: 'Missing Award Winners',
  trending_topics_without_coverage: 'Trending Topics Gap',
}

export function IntelligencePanel({ report }: { report: CollectionIntelligenceReport | null }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [searchResults, setSearchResults] = useState<ExternalSearchResult[]>([])
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set())

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    setIsSearching(true)
    try {
      const result = await searchExternalCatalogs({ q: searchQuery })
      setSearchResults(result.results)
    } catch {
      toast.error(t('toast.selectionList.searchFailed'))
    } finally {
      setIsSearching(false)
    }
  }

  const addSearchResultMut = useMutation({
    mutationFn: (item: ExternalSearchResult) => {
      const data: Parameters<typeof addToSelectionList>[0] = {
        title: item.title,
        source: item.source,
      }
      if (item.author) data.author = item.author
      if (item.isbn) data.isbn = item.isbn
      if (item.publisher) data.publisher = item.publisher
      if (item.publication_year) data.publication_year = item.publication_year
      if (item.price != null) data.price = item.price
      if (item.format) data.format = item.format
      return addToSelectionList(data)
    },
    onSuccess: () => {
      toast.success(t('selectorDashboard.addedToSelectionList'))
      queryClient.invalidateQueries({ queryKey: ['selectors', 'selection-list'] })
    },
    onError: () => toast.error(t('toast.indieBookDetail.failedToAdd')),
  })

  const buildInsightData = (item: CollectionInsightItem) => {
    const data: Parameters<typeof addInsightToPurchaseConsideration>[0] = {
      title: item.title,
      notes: item.reason,
      source: item.source,
      source_id: item.key,
    }
    if (item.author) data.author = item.author
    if (item.isbn) data.isbn = item.isbn
    return data
  }

  const addInsightMut = useMutation({
    mutationFn: (item: CollectionInsightItem) =>
      addInsightToPurchaseConsideration(buildInsightData(item)),
    onSuccess: () => {
      toast.success(t('selectorDashboard.addedToSelectionList2'))
      queryClient.invalidateQueries({ queryKey: ['selectors', 'selection-list'] })
    },
    onError: () => toast.error(t('selectorDashboard.failedToAddInsight')),
  })

  const addAllInsightsMut = useMutation({
    mutationFn: async (items: CollectionInsightItem[]) => {
      for (const item of items) {
        await addInsightToPurchaseConsideration(buildInsightData(item))
      }
    },
    onSuccess: () => {
      toast.success(t('selectorDashboard.allItemsAddedToSelection'))
      queryClient.invalidateQueries({ queryKey: ['selectors', 'selection-list'] })
    },
    onError: () => toast.error(t('selectorDashboard.failedToAddSomeItems')),
  })

  const toggleCard = (key: string) => {
    setExpandedCards(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  return (
    <div className="space-y-6">
      {/* ─── External search ─────────────────────────────────── */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4">
        <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-3">Search External Catalogs</h3>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              placeholder={t('selectorDashboard.searchByTitleAuthorOr')}
              className="w-full pl-10 pr-4 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-sm text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>
          <Button onClick={handleSearch} isLoading={isSearching} leftIcon={<Search className="w-4 h-4" />}>
            Search
          </Button>
        </div>

        {/* Search results */}
        {searchResults.length > 0 && (
          <div className="mt-4 space-y-2 max-h-80 overflow-y-auto">
            {searchResults.map((r, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-earth-50 dark:bg-earth-700/50 border border-lsc-border dark:border-earth-600">
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-sm text-lsc-dark dark:text-lsc-cream truncate" title={r.title}>{r.title}</p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                    {r.author ?? 'Unknown'} {r.isbn ? `· ${r.isbn}` : ''} {r.price != null ? `· ${formatCurrency(r.price)}` : ''}
                  </p>
                  <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{r.source}</span>
                </div>
                <Button
                  size="sm"
                  onClick={() => addSearchResultMut.mutate(r)}
                  leftIcon={<Plus className="w-3.5 h-3.5" />}
                >
                  Add
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ─── Intelligence cards ──────────────────────────────── */}
      {!report ? (
        <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" /></div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Collection Intelligence</h3>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => queryClient.invalidateQueries({ queryKey: ['selectors', 'intelligence'] })}
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              Refresh
            </Button>
          </div>

          {(Object.entries(report) as [string, CollectionInsightItem[]][]).map(([key, items]) => {
            if (!Array.isArray(items) || items.length === 0) return null
            const expanded = expandedCards.has(key)
            return (
              <div key={key} className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 overflow-hidden">
                <button
                  onClick={() => toggleCard(key)}
                  className="w-full flex items-center justify-between px-4 py-3 hover:bg-earth-50 dark:hover:bg-earth-700/30 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    {expanded ? <ChevronDown className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" /> : <ChevronRight className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />}
                    <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{INSIGHT_LABELS[key] ?? key}</span>
                    <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-lsc-rose/10 text-lsc-rose">
                      {items.length}
                    </span>
                  </div>
                  {expanded && (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={e => { e.stopPropagation(); addAllInsightsMut.mutate(items) }}
                      isLoading={addAllInsightsMut.isPending}
                    >
                      Add All
                    </Button>
                  )}
                </button>
                {expanded && (
                  <div className="border-t border-lsc-border dark:border-earth-700 divide-y divide-earth-100 dark:divide-earth-700/50">
                    {items.map((item, i) => (
                      <div key={i} className="flex items-center justify-between px-4 py-2.5 hover:bg-earth-50 dark:hover:bg-earth-700/20">
                        <div className="min-w-0 flex-1 mr-3">
                          <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate" title={item.title}>{item.title}</p>
                          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 truncate" title={`${item.author ?? ''} — ${item.reason}`}>{item.author ?? ''} — {item.reason}</p>
                        </div>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => addInsightMut.mutate(item)}
                          leftIcon={<Plus className="w-3.5 h-3.5" />}
                        >
                          Add
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
