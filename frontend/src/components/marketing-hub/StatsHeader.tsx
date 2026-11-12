/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Sparkles, Star, TrendingUp } from 'lucide-react'
import {
  getSavedContent,
  type SavedContent,
  type SavedContentListResponse,
} from '@/api/marketing-hub-api'
import {
  getMarketingAnalytics,
  type MarketingAnalytics,
} from '@/api/marketing-api'

type TabId = 'create' | 'history' | 'analytics'

interface StatsHeaderProps {
  token: string
  onSelectTab?: (tab: TabId) => void
}

interface TileSpec {
  key: string
  label: string
  icon: React.ElementType
  value: string | null
  isLoading: boolean
  isError: boolean
  ariaValue: string
  tab: TabId
  /** When onSelectTab is not wired, navigate here instead. If undefined, tile is inert. */
  fallbackHref?: string
}

const STALE_TIME_MS = 60_000

function isCurrentMonth(iso: string, now: Date): boolean {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return false
  return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth()
}

export default function StatsHeader({
  token,
  onSelectTab,
}: StatsHeaderProps): React.ReactElement {
  const savedQuery = useQuery<SavedContentListResponse>({
    queryKey: ['marketing-hub', 'saved-content', 'stats'],
    queryFn: () => getSavedContent(token, { limit: 200 }),
    staleTime: STALE_TIME_MS,
  })

  const analyticsQuery = useQuery<MarketingAnalytics>({
    queryKey: ['marketing-hub', 'analytics', 'stats', 30],
    queryFn: () => getMarketingAnalytics(token, { days: 30 }),
    staleTime: STALE_TIME_MS,
  })

  const now = new Date()
  const savedItems: SavedContent[] = savedQuery.data?.items ?? []
  const draftsThisMonth = savedItems.filter((item) =>
    isCurrentMonth(item.created_at, now),
  ).length
  const favorites = savedItems.filter((item) => item.is_favorite === true).length
  const openRate = analyticsQuery.data?.average_open_rate

  const tiles: TileSpec[] = [
    {
      key: 'drafts',
      label: 'Drafts saved this month',
      icon: Sparkles,
      value: savedQuery.isError ? null : draftsThisMonth.toLocaleString(),
      isLoading: savedQuery.isLoading,
      isError: savedQuery.isError,
      ariaValue: savedQuery.isError
        ? 'data unavailable'
        : `${draftsThisMonth.toLocaleString()}`,
      tab: 'history',
      // No fallbackHref: when onSelectTab isn't wired, this tile is inert (still shows stat).
    },
    {
      key: 'favorites',
      label: 'Favorites',
      icon: Star,
      value: savedQuery.isError ? null : favorites.toLocaleString(),
      isLoading: savedQuery.isLoading,
      isError: savedQuery.isError,
      ariaValue: savedQuery.isError
        ? 'data unavailable'
        : `${favorites.toLocaleString()}`,
      tab: 'history',
    },
    {
      key: 'open-rate',
      label: '30-day open rate',
      icon: TrendingUp,
      value:
        analyticsQuery.isError || openRate === undefined
          ? null
          : `${openRate.toFixed(1)}%`,
      isLoading: analyticsQuery.isLoading,
      isError: analyticsQuery.isError,
      ariaValue:
        analyticsQuery.isError || openRate === undefined
          ? 'data unavailable'
          : `${openRate.toFixed(1)} percent`,
      tab: 'analytics',
      fallbackHref: '/staff/marketing',
    },
  ]

  return (
    <header className="mb-8">
      <div className="flex items-center gap-3 mb-2">
        <Sparkles aria-hidden="true" className="w-7 h-7 text-lsc-rose" />
        <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          Marketing Hub
        </h1>
      </div>
      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
        Create marketing materials with AI assistance using your library programs
        and events.
      </p>

      <ul
        role="list"
        className="grid grid-cols-2 md:grid-cols-3 gap-4 list-none p-0 m-0"
        aria-label="Marketing Hub at-a-glance stats"
      >
        {tiles.map((tile) => (
          <li key={tile.key}>
            <StatTile tile={tile} {...(onSelectTab !== undefined ? { onSelectTab } : {})} />
          </li>
        ))}
      </ul>
    </header>
  )
}

interface StatTileProps {
  tile: TileSpec
  onSelectTab?: (tab: TabId) => void
}

function StatTile({ tile, onSelectTab }: StatTileProps): React.ReactElement {
  const { label, icon: Icon, value, isLoading, isError, ariaValue, tab } = tile
  const display = isError || value === null ? '—' : value

  // a11y: full sentence so each tile reads sensibly in isolation.
  const actionHint =
    onSelectTab !== undefined
      ? `Open ${tabLabel(tab)} tab.`
      : tile.fallbackHref !== undefined
        ? `Open ${tabLabel(tab)} page.`
        : ''
  const fullSentence = `${label}: ${
    isLoading ? 'loading' : ariaValue
  }. ${actionHint}`.trim()

  const innerContent = (
    <>
      <span className="flex items-start justify-between gap-2">
        <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
          {label}
        </span>
        <Icon aria-hidden="true" className="w-5 h-5 text-lsc-rose shrink-0" />
      </span>
      <span className="mt-2 block text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
        {isLoading ? (
          <>
            <span
              aria-hidden="true"
              className="inline-block h-7 w-16 rounded-lg bg-lsc-cream dark:bg-earth-700 motion-safe:animate-pulse"
            />
            <span className="sr-only">Loading {label}…</span>
          </>
        ) : (
          <>
            <span aria-hidden="true">{display}</span>
            <span className="sr-only">{fullSentence}</span>
          </>
        )}
      </span>
    </>
  )

  const baseClasses =
    'block w-full text-left rounded-xl p-4 border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 transition-colors'
  const interactiveClasses =
    'hover:border-lsc-rose focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-earth-900 cursor-pointer'

  const ariaProps = {
    'aria-busy': isLoading || undefined,
    'aria-label': isError ? 'data unavailable' : undefined,
  }

  // Interactive: tab-switch callback present (works for all tiles)
  if (onSelectTab !== undefined) {
    return (
      <button
        type="button"
        onClick={() => onSelectTab(tab)}
        className={`${baseClasses} ${interactiveClasses}`}
        {...ariaProps}
      >
        {innerContent}
      </button>
    )
  }

  // Interactive: fallback to a route Link (no callback wired)
  if (onSelectTab === undefined && tile.fallbackHref !== undefined) {
    return (
      <Link
        to={tile.fallbackHref}
        className={`${baseClasses} ${interactiveClasses}`}
        {...ariaProps}
      >
        {innerContent}
      </Link>
    )
  }

  // Inert: just display the stat
  return (
    <div className={baseClasses} {...ariaProps}>
      {innerContent}
    </div>
  )
}

function tabLabel(tab: TabId): string {
  switch (tab) {
    case 'create':
      return 'Create'
    case 'history':
      return 'History'
    case 'analytics':
      return 'Analytics'
  }
}
