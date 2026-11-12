/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Trophy,
  Award,
  Users,
  Clock,
  BookOpen,
  TrendingUp,
  Medal,
  Star,
  Flame,
  Target,
  Loader2,
  Calendar,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  getReadingBalance,
  getMyReadingStats,
  getReadingAchievements,
  getCommunityReadingData,
  getReadingLeaderboard,
  logReading,
} from '@/api/reading-gamification-api'
import { useAuth } from '@/contexts/AuthContext'
import { useTranslation} from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import PageContainer from '@/components/layout/PageContainer'

type TabType = 'overview' | 'leaderboard' | 'achievements' | 'community'
type LeaderboardPeriod = 'day' | 'week' | 'month' | 'year' | 'all'

// eslint-disable-next-line complexity
export default function ReadingGamificationPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user } = useAuth()
  const queryClient = useQueryClient()

  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const [leaderboardPeriod, setLeaderboardPeriod] = useState<LeaderboardPeriod>('month')
  const [showLogModal, setShowLogModal] = useState(false)
  const [logMinutes, setLogMinutes] = useState('')
  const [logBookTitle, setLogBookTitle] = useState('')
  const [logNotes, setLogNotes] = useState('')

  // Queries
  const { data: balance } = useQuery({
    queryKey: ['reading', 'balance'],
    queryFn: getReadingBalance,
    enabled: !!user,
  })

  const { data: stats, isLoading: loadingStats } = useQuery({
    queryKey: ['reading', 'my-stats'],
    queryFn: getMyReadingStats,
    enabled: !!user && activeTab === 'overview',
  })

  const { data: achievements, isLoading: loadingAchievements } = useQuery({
    queryKey: ['reading', 'achievements'],
    queryFn: getReadingAchievements,
    enabled: !!user && activeTab === 'achievements',
  })

  const { data: community, isLoading: loadingCommunity } = useQuery({
    queryKey: ['reading', 'community'],
    queryFn: getCommunityReadingData,
    enabled: activeTab === 'community',
  })

  const { data: leaderboard, isLoading: loadingLeaderboard } = useQuery({
    queryKey: ['reading', 'leaderboard', leaderboardPeriod],
    queryFn: () => getReadingLeaderboard({ period: leaderboardPeriod, limit: 20 }),
    enabled: activeTab === 'leaderboard',
  })

  // Mutations
  const logMutation = useMutation({
    mutationFn: logReading,
    onSuccess: () => {
      toast.success(t('toast.readingGamification.readingLogged'))
      queryClient.invalidateQueries({ queryKey: ['reading'] })
      setShowLogModal(false)
      setLogMinutes('')
      setLogBookTitle('')
      setLogNotes('')
    },
    onError: () => toast.error(t('readingGamification.failedToLogReading')),
  })

  const handleLogSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const minutes = parseInt(logMinutes, 10)
    if (isNaN(minutes) || minutes < 1) return
    logMutation.mutate({
      minutes,
      reading_date: new Date().toISOString(),
      ...(logBookTitle ? { book_title: logBookTitle } : {}),
      ...(logNotes ? { notes: logNotes } : {}),
    })
  }

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900">
      <PageContainer className="py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center justify-center gap-3">
            <Trophy className="w-8 h-8 text-lsc-rose" />
            Reading Challenge
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{t('readingGamification.trackYourReadingEarnAchievements')}</p>
        </div>

        {/* Quick Stats & Log Button */}
        {user && balance && (
          <div className="mb-8 bg-gradient-to-r from-lsc-rose to-orange-600 rounded-xl p-6 text-white">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-6">
                <div className="text-center">
                  <p className="text-status-warning-200 text-sm">Minutes Logged</p>
                  <p className="text-3xl font-bold">{balance?.minutes_logged?.toLocaleString() ?? 0}</p>
                </div>
                <div className="text-center">
                  <p className="text-status-warning-200 text-sm">Balance Owed</p>
                  <p className="text-3xl font-bold">{balance?.balance?.toLocaleString() ?? 0}</p>
                </div>
                {(balance?.pending_logs ?? 0) > 0 && (
                  <div className="text-center">
                    <p className="text-status-warning-200 text-sm">Pending Logs</p>
                    <p className="text-3xl font-bold">{balance?.pending_logs ?? 0}</p>
                  </div>
                )}
              </div>
              <button
                onClick={() => setShowLogModal(true)}
                className="flex items-center gap-2 px-6 py-3 bg-lsc-white dark:bg-earth-800 text-lsc-rose rounded-lg font-semibold hover:bg-status-warning-100 transition-colors"
              >
                <Clock className="w-5 h-5" />
                Log Reading
              </button>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex justify-center gap-2 mb-8" role="tablist">
          {[
            { id: 'overview' as const, label: 'My Stats', icon: TrendingUp },
            { id: 'leaderboard' as const, label: 'Leaderboard', icon: Trophy },
            { id: 'achievements' as const, label: 'Achievements', icon: Award },
            { id: 'community' as const, label: 'Community', icon: Users },
          ].map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-lsc-rose text-white'
                  : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-700'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div role="tabpanel">
            {loadingStats ? (
              <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : stats ? (
              <div className="space-y-6">
                {/* Stats Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-5">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-full bg-earth-100 dark:bg-earth-800/30">
                        <Clock className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
                      </div>
                      <div>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Minutes</p>
                        <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{(stats?.total_approved_minutes ?? 0).toLocaleString()}</p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-5">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-full bg-status-success-100 dark:bg-status-success-900/30">
                        <BookOpen className="w-5 h-5 text-status-success-600 dark:text-status-success-400" />
                      </div>
                      <div>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Books Read</p>
                        <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{stats?.unique_books ?? 0}</p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-5">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-full bg-status-warning-100 dark:bg-status-warning-900/30">
                        <Flame className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400" />
                      </div>
                      <div>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Current Streak</p>
                        <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{stats?.streak ?? 0} days</p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-5">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-full bg-category-100 dark:bg-category-900/30">
                        <Target className="w-5 h-5 text-category-600 dark:text-category-400" />
                      </div>
                      <div>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">XP / Level</p>
                        <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{stats?.xp ?? 0} XP (Lv {stats?.level ?? 1})</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* XP Progress to Next Level */}
                <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-6">
                  <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                    <Star className="w-5 h-5 text-lsc-rose" />
                    Level {stats?.level ?? 1} Progress
                  </h3>
                  <div className="mb-2">
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                        {stats?.xp ?? 0} / {(stats?.xp ?? 0) + (stats?.xp_to_next_level ?? 100)} XP
                      </span>
                      <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                        {stats?.xp_to_next_level != null && (stats.xp ?? 0) + stats.xp_to_next_level > 0
                          ? (((stats.xp ?? 0) / ((stats.xp ?? 0) + stats.xp_to_next_level)) * 100).toFixed(0)
                          : 0}%
                      </span>
                    </div>
                    <div className="bg-earth-200 dark:bg-earth-700 rounded-full h-4">
                      <div
                        className="bg-gradient-to-r from-lsc-rose to-orange-500 h-4 rounded-full transition-all"
                        style={{ width: `${stats?.xp_to_next_level != null && (stats.xp ?? 0) + stats.xp_to_next_level > 0 ? Math.min(100, ((stats.xp ?? 0) / ((stats.xp ?? 0) + stats.xp_to_next_level)) * 100) : 0}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Additional Stats */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-5 text-center">
                    <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{stats?.longest_streak ?? 0}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Longest Streak (days)</p>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-5 text-center">
                    <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{stats?.total_submissions ?? 0}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Submissions</p>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-5 text-center">
                    <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{stats?.notes_written ?? 0}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Notes Written</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-12">
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('readingGamification.logInToSeeYour')}</p>
              </div>
            )}
          </div>
        )}

        {/* Leaderboard Tab */}
        {activeTab === 'leaderboard' && (
          <div role="tabpanel" className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700">
            <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
              <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Top Readers</h3>
              <select
                value={leaderboardPeriod}
                onChange={(e) => setLeaderboardPeriod(e.target.value as LeaderboardPeriod)}
                className="px-3 py-1.5 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
              >
                <option value="day">Today</option>
                <option value="week">This Week</option>
                <option value="month">This Month</option>
                <option value="year">This Year</option>
                <option value="all">All Time</option>
              </select>
            </div>

            {loadingLeaderboard ? (
              <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : (
              <div className="divide-y divide-earth-200 dark:divide-earth-700">
                {leaderboard?.map((entry, index) => (
                  <div
                    key={entry.rank}
                    className="p-4 flex items-center gap-4"
                  >
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg ${
                      index === 0 ? 'bg-status-warning-500 text-status-warning-900 dark:text-status-warning-200' :
                      index === 1 ? 'bg-earth-400 text-lsc-dark dark:text-lsc-cream' :
                      index === 2 ? 'bg-status-warning-600 text-status-warning-100' :
                      'bg-earth-200 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'
                    }`}>
                      {entry.rank}
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream">{entry?.display_name ?? 'Reader'}</p>
                      <div className="flex items-center gap-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        <span>{entry?.books_completed ?? 0} books</span>
                        <span>{entry?.achievements_count ?? 0} badges</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-lsc-rose">{(entry?.minutes_read ?? 0).toLocaleString()}</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">minutes</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Achievements Tab */}
        {activeTab === 'achievements' && (
          <div role="tabpanel">
            {loadingAchievements ? (
              <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {achievements?.map((achievement) => (
                  <div
                    key={achievement.id}
                    className={`bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border p-5 ${
                      achievement?.earned
                        ? 'border-lsc-rose'
                        : 'border-lsc-border dark:border-earth-700 opacity-60'
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      <div className={`w-14 h-14 rounded-full flex items-center justify-center ${
                        achievement?.earned ? 'bg-lsc-rose text-white' : 'bg-earth-200 dark:bg-earth-700'
                      }`}>
                        <Medal className={`w-7 h-7 ${achievement?.earned ? '' : 'text-lsc-dark/70 dark:text-lsc-cream/70'}`} />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{achievement?.name}</h4>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{achievement?.description}</p>
                        <p className="text-xs text-earth-600 dark:text-earth-400 mt-1">{achievement?.xp ?? 0} XP</p>
                        {achievement?.earned && achievement?.earned_at ? (
                          <p className="text-xs text-status-success-600 dark:text-status-success-400 mt-2 flex items-center gap-1">
                            <Star className="w-3 h-3" />
                            Earned {new Date(achievement.earned_at).toLocaleDateString()}
                          </p>
                        ) : !achievement?.earned ? (
                          <p className="text-xs text-earth-600 dark:text-earth-400 mt-2">Not yet earned</p>
                        ) : null}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Community Tab */}
        {activeTab === 'community' && (
          <div role="tabpanel">
            {loadingCommunity ? (
              <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : community ? (
              <div className="space-y-6">
                {/* Community Message */}
                {community?.message && (
                  <div className="bg-gradient-to-r from-lsc-rose to-orange-600 rounded-xl p-6 text-white text-center">
                    <p className="text-xl font-semibold">{community.message}</p>
                  </div>
                )}

                {/* Community Stats */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-5 text-center">
                    <div className="w-12 h-12 rounded-full bg-earth-100 dark:bg-earth-800/30 mx-auto mb-3 flex items-center justify-center">
                      <Clock className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
                    </div>
                    <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{(community?.total_minutes ?? 0).toLocaleString()}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Minutes Read</p>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-5 text-center">
                    <div className="w-12 h-12 rounded-full bg-status-success-100 dark:bg-status-success-900/30 mx-auto mb-3 flex items-center justify-center">
                      <Calendar className="w-6 h-6 text-status-success-600 dark:text-status-success-400" />
                    </div>
                    <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{(community?.monthly_minutes ?? 0).toLocaleString()}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Minutes This Month</p>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-5 text-center">
                    <div className="w-12 h-12 rounded-full bg-status-warning-100 dark:bg-status-warning-900/30 mx-auto mb-3 flex items-center justify-center">
                      <Users className="w-6 h-6 text-status-warning-600 dark:text-status-warning-400" />
                    </div>
                    <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{community?.active_readers_this_month ?? 0}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Active Readers This Month</p>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        )}

        {/* Log Reading Modal */}
        {showLogModal && (
          <ModalBackdrop onClose={() => setShowLogModal(false)} title="Log Reading Time">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-md w-full">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Log Reading Time</h3>
              </div>
              <form onSubmit={handleLogSubmit} className="p-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Minutes Read *</label>
                  <input
                    type="number"
                    value={logMinutes}
                    onChange={(e) => setLogMinutes(e.target.value)}
                    required
                    min="1"
                    placeholder={t('placeholder.readingLogEntryForm.30')}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Book Title (optional)</label>
                  <input
                    type="text"
                    value={logBookTitle}
                    onChange={(e) => setLogBookTitle(e.target.value)}
                    placeholder={t('readingGamification.whatAreYouReading')}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Notes (optional)</label>
                  <textarea
                    value={logNotes}
                    onChange={(e) => setLogNotes(e.target.value)}
                    rows={2}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div className="pt-2 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowLogModal(false)}
                    className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={logMutation.isPending || !logMinutes}
                    className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50"
                  >
                    {logMutation.isPending ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" /> : 'Log Reading'}
                  </button>
                </div>
              </form>
            </div>
          </ModalBackdrop>
        )}
      </PageContainer>
    </div>
  )
}
