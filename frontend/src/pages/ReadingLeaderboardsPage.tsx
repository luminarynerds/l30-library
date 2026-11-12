/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Trophy,
  Medal,
  TrendingUp,
  TrendingDown,
  Minus,
  Loader2,
  AlertCircle,
  RefreshCw,
  BookOpen,
  Crown,
  Sparkles,
} from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import { useBranding } from '@/contexts/BrandingContext'
import {
  listActiveLeaderboards,
  getLeaderboardEntries,
  type Leaderboard,
  type LeaderboardWithEntries,
} from '@/api/domains/reading/reading-leaderboards-api'

function RankChange({ change }: { change: number | null }) {
  if (change === null || change === 0) {
    return <Minus className="w-4 h-4 text-earth-600 dark:text-earth-500" aria-hidden="true" />
  }
  if (change > 0) {
    return (
      <span className="flex items-center gap-0.5 text-status-success-600 dark:text-status-success-400 text-xs font-medium">
        <TrendingUp className="w-3.5 h-3.5" aria-hidden="true" />
        {change}
      </span>
    )
  }
  return (
    <span className="flex items-center gap-0.5 text-status-danger-500 dark:text-status-danger-400 text-xs font-medium">
      <TrendingDown className="w-3.5 h-3.5" aria-hidden="true" />
      {Math.abs(change)}
    </span>
  )
}

function RankBadge({ rank }: { rank: number }) {
  if (rank === 1) {
    return (
      <div className="w-10 h-10 rounded-full bg-status-warning-500 text-status-warning-900 flex items-center justify-center font-bold text-lg">
        <Crown className="w-5 h-5" aria-hidden="true" />
      </div>
    )
  }
  if (rank === 2) {
    return (
      <div className="w-10 h-10 rounded-full bg-earth-400 text-lsc-dark dark:text-lsc-cream flex items-center justify-center font-bold text-lg">
        {rank}
      </div>
    )
  }
  if (rank === 3) {
    return (
      <div className="w-10 h-10 rounded-full bg-status-warning-600 text-status-warning-100 flex items-center justify-center font-bold text-lg">
        {rank}
      </div>
    )
  }
  return (
    <div className="w-10 h-10 rounded-full bg-earth-200 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center justify-center font-bold text-lg">
      {rank}
    </div>
  )
}

function metricLabel(metric: string): string {
  switch (metric) {
    case 'books_read': return 'books'
    case 'pages_read': return 'pages'
    case 'minutes_read': return 'minutes'
    default: return 'points'
  }
}

function LeaderboardCard({
  leaderboard,
  isSelected,
  onSelect,
}: {
  leaderboard: Leaderboard
  isSelected: boolean
  onSelect: () => void
}) {
  return (
    <button
      onClick={onSelect}
      className={`w-full text-left p-4 rounded-xl border transition-colors min-h-[44px] ${
        isSelected
          ? 'bg-lsc-rose/10 dark:bg-lsc-rose/20 border-lsc-rose'
          : 'bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700 hover:border-lsc-rose/50'
      }`}
    >
      <div className="flex items-start gap-3">
        <Trophy
          className={`w-5 h-5 mt-0.5 flex-shrink-0 ${
            isSelected ? 'text-lsc-rose' : 'text-earth-600 dark:text-earth-500'
          }`}
          aria-hidden="true"
        />
        <div className="flex-1 min-w-0">
          <h3 className={`font-medium truncate ${
            isSelected
              ? 'text-lsc-rose dark:text-lsc-rose-light'
              : 'text-lsc-dark dark:text-lsc-cream'
          }`}>
            {leaderboard.name}
          </h3>
          {leaderboard.description && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 line-clamp-2">
              {leaderboard.description}
            </p>
          )}
          <div className="flex items-center gap-3 mt-2 text-xs text-earth-600 dark:text-earth-400">
            <span>{leaderboard.participant_count} participants</span>
            <span>{leaderboard.leaderboard_type.replace(/_/g, ' ')}</span>
          </div>
        </div>
      </div>
    </button>
  )
}

function EntriesTable({ data }: { data: LeaderboardWithEntries }) {
  if (!data.entries || data.entries.length === 0) {
    return (
      <div className="text-center py-12">
        <BookOpen className="w-12 h-12 text-earth-300 dark:text-earth-600 mx-auto mb-3" aria-hidden="true" />
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No entries yet. Start reading to join the leaderboard!</p>
      </div>
    )
  }

  return (
    <div className="divide-y divide-earth-200 dark:divide-earth-700">
      {data.entries.map((entry) => (
        <div
          key={entry.id}
          className={`flex items-center gap-4 p-4 min-h-[44px] ${
            entry.rank <= 3
              ? 'bg-lsc-rose/5 dark:bg-lsc-rose/10'
              : ''
          }`}
        >
          <RankBadge rank={entry.rank} />
          <div className="flex-1 min-w-0">
            <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate">
              {entry.display_name || 'Anonymous Reader'}
              {entry.rank === 1 && (
                <Sparkles className="w-4 h-4 text-status-warning-500 inline ml-1.5" aria-label="Champion" />
              )}
            </p>
          </div>
          <div className="text-right flex items-center gap-3">
            <RankChange change={null} />
            <div>
              <p className="text-lg font-bold text-lsc-rose dark:text-lsc-rose-light">
                {entry.score.toLocaleString()}
              </p>
              <p className="text-xs text-earth-600 dark:text-earth-400">
                {metricLabel(data.leaderboard_type)}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default function ReadingLeaderboardsPage(): React.ReactElement {
  const branding = useBranding()
  usePageTitle('Reading Leaderboards', `See top readers and compete in reading challenges at ${branding.library_short_name}.`)
  const { isFeatureEnabled, loading: featuresLoading } = useOrganizationFeatures()
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const {
    data: leaderboardsData,
    isLoading: loadingList,
    error: listError,
    refetch: refetchList,
  } = useQuery({
    queryKey: ['reading-leaderboards'],
    queryFn: () => listActiveLeaderboards(),
    enabled: isFeatureEnabled('gamification_enabled'),
  })

  const {
    data: entriesData,
    isLoading: loadingEntries,
    error: entriesError,
    refetch: refetchEntries,
  } = useQuery({
    queryKey: ['reading-leaderboard-entries', selectedId],
    queryFn: () => getLeaderboardEntries(selectedId!),
    enabled: !!selectedId,
  })

  const leaderboards = leaderboardsData?.items ?? []

  // Auto-select first leaderboard
  if (leaderboards.length > 0 && selectedId === null) {
    const first = leaderboards[0]
    if (first) setSelectedId(first.id)
  }

  if (featuresLoading) {
    return (
      <StandardPageLayout title="Reading Leaderboards" icon={Trophy} isLoading>
        <div />
      </StandardPageLayout>
    )
  }

  if (!isFeatureEnabled('gamification_enabled')) {
    return (
      <StandardPageLayout
        title="Reading Leaderboards"
        icon={Trophy}
        isEmpty
        emptyMessage="Reading leaderboards are not currently available."
      >
        <div />
      </StandardPageLayout>
    )
  }

  return (
    <StandardPageLayout
      title="Reading Leaderboards"
      subtitle="See how you stack up against fellow readers. Compete in challenges and climb the ranks!"
      icon={Trophy}
      isLoading={loadingList}
      isEmpty={!loadingList && leaderboards.length === 0}
      emptyMessage="No active leaderboards right now. Check back soon!"
      emptyAction={{ label: 'Browse Reading Programs', href: '/programs' }}
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Leaderboard selector */}
        <div className="lg:col-span-1 space-y-3">
          <h2 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide flex items-center gap-2">
            <Medal className="w-4 h-4" aria-hidden="true" />
            Active Leaderboards
          </h2>
          <div className="space-y-2">
            {leaderboards.map((lb) => (
              <LeaderboardCard
                key={lb.id}
                leaderboard={lb}
                isSelected={selectedId === lb.id}
                onSelect={() => setSelectedId(lb.id)}
              />
            ))}
          </div>
        </div>

        {/* Entries panel */}
        <div className="lg:col-span-2">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
            {/* Header */}
            {selectedId && leaderboards.find((lb) => lb.id === selectedId) && (
              <div className="p-4 border-b border-lsc-border dark:border-earth-700">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                  {leaderboards.find((lb) => lb.id === selectedId)?.name}
                </h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  {leaderboards.find((lb) => lb.id === selectedId)?.description}
                </p>
              </div>
            )}

            {/* Content */}
            {entriesError ? (
              <div className="p-6 text-center space-y-3" role="alert">
                <AlertCircle className="w-8 h-8 text-status-danger-500 mx-auto" aria-hidden="true" />
                <p className="text-sm text-status-danger-600 dark:text-status-danger-400">
                  Failed to load leaderboard entries. Please try again.
                </p>
                <button
                  onClick={() => refetchEntries()}
                  className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-lsc-rose hover:text-lsc-rose/80 border border-lsc-rose/30 rounded-lg transition-colors min-h-[44px]"
                >
                  <RefreshCw className="w-4 h-4" aria-hidden="true" />
                  Retry
                </button>
              </div>
            ) : loadingEntries ? (
              <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : entriesData ? (
              <EntriesTable data={entriesData} />
            ) : (
              <div className="text-center py-16 text-lsc-dark/70 dark:text-lsc-cream/70">
                <Trophy className="w-12 h-12 mx-auto mb-3 opacity-50" aria-hidden="true" />
                <p>Select a leaderboard to view rankings</p>
              </div>
            )}
          </div>

          {/* List error */}
          {listError && (
            <div className="mt-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-4 flex items-center gap-3" role="alert">
              <AlertCircle className="w-5 h-5 text-status-danger-500 flex-shrink-0" aria-hidden="true" />
              <p className="text-sm text-status-danger-700 dark:text-status-danger-300 flex-1">
                Failed to load leaderboards.
              </p>
              <button
                onClick={() => refetchList()}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-status-danger-700 dark:text-status-danger-300 hover:bg-status-danger-100 dark:hover:bg-status-danger-900/30 rounded-lg transition-colors min-h-[44px]"
              >
                <RefreshCw className="w-4 h-4" aria-hidden="true" />
                Retry
              </button>
            </div>
          )}
        </div>
      </div>
    </StandardPageLayout>
  )
}
