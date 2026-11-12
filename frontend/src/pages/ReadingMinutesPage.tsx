/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  Clock,
  Loader2,
  BookOpen,
  Trophy,
  CheckCircle,
  AlertCircle,
  TrendingUp,
  Star,
  Sparkles,
  Timer,
  PenLine,
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import {
  getReadingMinutesStatus,
  logReadingTime,
  getReadingLeaderboard,
  type ReadingMinutesStatus,
  type LeaderboardEntry,
} from '@/api/reading-minutes-api'
import { useTranslation } from '@/i18n'
import { clean } from '@/lib/utils'
import PageContainer from '@/components/layout/PageContainer'

type ViewTab = 'status' | 'log' | 'leaderboard'

export default function ReadingMinutesPage(): React.ReactElement {
  const { t } = useTranslation()
  const { token, isAuthenticated, user } = useAuth()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<ViewTab>('status')
  const [minutes, setMinutes] = useState<number>(15)
  const [note, setNote] = useState<string>('')

  // Fetch reading minutes status
  const {
    data: status,
    isLoading: isLoadingStatus,
    error: statusError,
    refetch: refetchStatus,
  } = useQuery({
    queryKey: ['reading-minutes-status'],
    queryFn: () => (token ? getReadingMinutesStatus(token) : Promise.reject('No token')),
    enabled: isAuthenticated && !!token,
  })

  // Fetch leaderboard
  const {
    data: leaderboard,
    isLoading: isLoadingLeaderboard,
    error: leaderboardError,
  } = useQuery({
    queryKey: ['reading-minutes-leaderboard'],
    queryFn: () => (token ? getReadingLeaderboard(token) : Promise.reject('No token')),
    enabled: isAuthenticated && !!token && activeTab === 'leaderboard',
  })

  // Log reading mutation
  const logMutation = useMutation({
    mutationFn: () => {
      if (!token) throw new Error('Not authenticated')
      return logReadingTime(token, clean({ minutes, note: note.trim() || undefined }))
    },
    onSuccess: (data) => {
      toast.success(data.message)
      queryClient.invalidateQueries({ queryKey: ['reading-minutes-status'] })
      queryClient.invalidateQueries({ queryKey: ['reading-minutes-leaderboard'] })
      setMinutes(15)
      setNote('')
      setActiveTab('status')
    },
    onError: (error: Error) => {
      toast.error(error.message)
    },
  })

  // Not authenticated view
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark py-20">
        <PageContainer className="text-center">
          <Clock className="w-16 h-16 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-4" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
            Reading Minutes
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Please log in to view and track your reading minutes.
          </p>
        </PageContainer>
      </div>
    )
  }

  const tabs = [
    { id: 'status' as const, label: 'My Status', icon: TrendingUp },
    { id: 'log' as const, label: 'Log Reading', icon: PenLine },
    { id: 'leaderboard' as const, label: 'Leaderboard', icon: Trophy },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="relative overflow-hidden bg-gradient-to-br from-lsc-rose/10 via-lsc-cream to-lsc-rose/5 dark:from-lsc-brown/50 dark:via-earth-800 dark:to-lsc-brown/30 rounded-xl p-6 md:p-8">
        <div className="relative z-10">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1 className="text-3xl md:text-4xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
                Reading Minutes
              </h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 max-w-xl">
                Track your reading time to clear any owed minutes. Read, log, and climb the leaderboard!
              </p>
            </div>

            {/* Quick stats */}
            {status && !status.is_clear && (
              <div className="flex gap-3">
                <div className="bg-lsc-white/80 dark:bg-earth-800/80 backdrop-blur-sm rounded-xl p-3 text-center min-w-[80px]">
                  <div className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">
                    {status.minutes_remaining}
                  </div>
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Remaining</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Decorative elements */}
        <div
          className="absolute top-0 right-0 w-64 h-64 bg-lsc-rose/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2"
          aria-hidden="true"
        />
        <div
          className="absolute bottom-0 left-0 w-48 h-48 bg-lsc-rose/5 rounded-full blur-2xl translate-y-1/2 -translate-x-1/2"
          aria-hidden="true"
        />
      </div>

      {/* Info banner */}
      <div className="bg-lsc-cream dark:bg-lsc-brown/30 border border-lsc-border dark:border-lsc-brown rounded-xl p-4 flex gap-3">
        <AlertCircle
          className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5"
          aria-hidden="true"
        />
        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <p className="font-medium text-lsc-dark dark:text-lsc-cream mb-1">How it works:</p>
          <ul className="space-y-1 text-xs list-disc list-inside">
            <li>{t('readingMinutes.insteadOfFinesYoungReaders')}</li>
            <li>{t('readingMinutes.logYourReadingTimeMinutes')}</li>
            <li>{t('readingMinutes.trackYourProgressAndSee')}</li>
            <li>{t('readingMinutes.onceYouVeLoggedEnough')}</li>
          </ul>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 p-1 bg-lsc-cream dark:bg-earth-800 rounded-xl">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium transition-all ${
                isActive
                  ? 'bg-lsc-rose text-white shadow-md'
                  : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-white dark:hover:bg-lsc-brown'
              }`}
            >
              <Icon className="w-5 h-5" aria-hidden="true" />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          )
        })}
      </div>

      {/* Content */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
        {/* Status Tab */}
        {activeTab === 'status' && (
          <StatusView
            {...(status ? { status } : {})}
            isLoading={isLoadingStatus}
            error={statusError}
            onRefresh={() => { refetchStatus() }}
            onLogReading={() => setActiveTab('log')}
          />
        )}

        {/* Log Reading Tab */}
        {activeTab === 'log' && (
          <LogReadingView
            {...(status ? { status } : {})}
            minutes={minutes}
            setMinutes={setMinutes}
            note={note}
            setNote={setNote}
            isSubmitting={logMutation.isPending}
            onSubmit={() => logMutation.mutate()}
          />
        )}

        {/* Leaderboard Tab */}
        {activeTab === 'leaderboard' && (
          <LeaderboardView
            {...(leaderboard ? { leaderboard } : {})}
            isLoading={isLoadingLeaderboard}
            error={leaderboardError}
            {...(user?.id != null ? { currentUserId: user.id } : {})}
          />
        )}
      </div>
    </div>
  )
}

// Status View Component
function StatusView({
  status,
  isLoading,
  error,
  onRefresh,
  onLogReading,
}: {
  status?: ReadingMinutesStatus
  isLoading: boolean
  error: Error | null
  onRefresh: () => void
  onLogReading: () => void
}): React.ReactElement {
  const { t } = useTranslation()
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose mb-4" />
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Loading your status...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-12 h-12 text-status-danger-500 mx-auto mb-4" aria-hidden="true" />
        <p className="text-status-danger-600 dark:text-status-danger-400 mb-4">{t('readingMinutes.failedToLoadReadingMinutes')}</p>
        <button
          onClick={onRefresh}
          className="px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors"
        >
          Try Again
        </button>
      </div>
    )
  }

  if (!status) {
    return (
      <div className="text-center py-12">
        <Clock className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-4" aria-hidden="true" />
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No status available</p>
      </div>
    )
  }

  // All caught up view
  if (status.is_clear) {
    return (
      <div className="text-center py-8">
        <div className="inline-flex items-center justify-center w-20 h-20 bg-status-success-100 dark:bg-status-success-900/30 rounded-full mb-6">
          <Sparkles className="w-10 h-10 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />
        </div>
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          You're All Caught Up!
        </h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6 max-w-md mx-auto">
          {status.message}
        </p>

        {status.minutes_logged > 0 && (
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-cream dark:bg-lsc-brown/30 rounded-full text-sm">
            <BookOpen className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
            <span className="text-lsc-dark dark:text-lsc-cream">
              Total logged: <strong>{status.minutes_logged} minutes</strong>
            </span>
          </div>
        )}
      </div>
    )
  }

  // Has minutes to pay off
  const progressPercent = Math.min(
    100,
    status.minutes_owed > 0 ? (status.minutes_logged / status.minutes_owed) * 100 : 0
  )

  return (
    <div className="space-y-6">
      {/* Progress card */}
      <div className="bg-gradient-to-br from-lsc-rose/5 to-lsc-cream dark:from-lsc-brown/30 dark:to-earth-700 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <Timer className="w-6 h-6 text-lsc-rose" aria-hidden="true" />
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Your Progress</h2>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="text-center p-3 bg-lsc-white/50 dark:bg-earth-800/50 rounded-xl">
            <div className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
              {status.minutes_owed}
            </div>
            <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Minutes Owed</div>
          </div>
          <div className="text-center p-3 bg-lsc-white/50 dark:bg-earth-800/50 rounded-xl">
            <div className="text-2xl font-bold text-status-success-600 dark:text-status-success-400">
              {status.minutes_logged}
            </div>
            <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Minutes Logged</div>
          </div>
          <div className="text-center p-3 bg-lsc-white/50 dark:bg-earth-800/50 rounded-xl">
            <div className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">
              {status.minutes_remaining}
            </div>
            <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Remaining</div>
          </div>
        </div>

        {/* Progress bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Progress</span>
            <span className="font-medium text-lsc-dark dark:text-lsc-cream">
              {progressPercent.toFixed(0)}%
            </span>
          </div>
          <div className="h-4 bg-lsc-cream dark:bg-lsc-brown/50 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-lsc-rose to-lsc-rose-light rounded-full transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
              role="progressbar"
              aria-valuenow={progressPercent}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${progressPercent.toFixed(0)}% of reading minutes completed`}
            />
          </div>
        </div>
      </div>

      {/* Message */}
      <div className="p-4 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl">
        <p className="text-lsc-dark dark:text-lsc-cream">{status.message}</p>
      </div>

      {/* CTA */}
      <button
        onClick={onLogReading}
        className="w-full flex items-center justify-center gap-2 px-6 py-4 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-semibold transition-colors shadow-md hover:shadow-lg"
      >
        <BookOpen className="w-5 h-5" aria-hidden="true" />
        Log Reading Time
      </button>
    </div>
  )
}

// Log Reading View Component
function LogReadingView({
  status,
  minutes,
  setMinutes,
  note,
  setNote,
  isSubmitting,
  onSubmit,
}: {
  status?: ReadingMinutesStatus
  minutes: number
  setMinutes: (m: number) => void
  note: string
  setNote: (n: string) => void
  isSubmitting: boolean
  onSubmit: () => void
}): React.ReactElement {
  const { t } = useTranslation()
  const canLog = status && !status.is_clear && status.minutes_remaining > 0

  // Quick select options
  const quickMinutes = [5, 15, 30, 45, 60, 90, 120]

  if (!canLog) {
    return (
      <div className="text-center py-12">
        <CheckCircle className="w-16 h-16 text-status-success-500 mx-auto mb-4" aria-hidden="true" />
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          Nothing to Log
        </h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          You don't have any reading minutes to pay off. You're all caught up!
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
          Log Your Reading Time
        </h2>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          How many minutes did you read? Be honest - this is based on the honor system.
        </p>
      </div>

      {/* Quick select buttons */}
      <div className="space-y-3">
        <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream">
          Quick Select
        </label>
        <div className="flex flex-wrap gap-2">
          {quickMinutes.map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMinutes(m)}
              className={`px-4 py-2 rounded-lg font-medium transition-all ${
                minutes === m
                  ? 'bg-lsc-rose text-white shadow-md'
                  : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream hover:bg-lsc-border dark:hover:bg-lsc-brown/80'
              }`}
            >
              {m} min
            </button>
          ))}
        </div>
      </div>

      {/* Custom minutes input */}
      <div className="space-y-2">
        <label
          htmlFor="minutes-input"
          className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream"
        >
          Or enter custom minutes (5-120)
        </label>
        <input
          id="minutes-input"
          type="number"
          min={5}
          max={120}
          value={minutes}
          onChange={(e) => setMinutes(Math.min(120, Math.max(5, parseInt(e.target.value) || 5)))}
          className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
        />
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
          You have {status?.minutes_remaining} minutes remaining. Logging {minutes} minutes.
        </p>
      </div>

      {/* Note input */}
      <div className="space-y-2">
        <label
          htmlFor="note-input"
          className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream"
        >
          Note (optional)
        </label>
        <textarea
          id="note-input"
          value={note}
          onChange={(e) => setNote(e.target.value.slice(0, 200))}
          placeholder={t('readingMinutes.whatDidYouReadAny')}
          rows={3}
          className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-none"
        />
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 text-right">
          {note.length}/200 characters
        </p>
      </div>

      {/* Submit button */}
      <button
        onClick={onSubmit}
        disabled={isSubmitting || minutes < 5 || minutes > 120}
        className="w-full flex items-center justify-center gap-2 px-6 py-4 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-semibold transition-colors shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isSubmitting ? (
          <>
            <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
            Logging...
          </>
        ) : (
          <>
            <CheckCircle className="w-5 h-5" aria-hidden="true" />
            Log {minutes} Minutes
          </>
        )}
      </button>

      {/* Honor system reminder */}
      <div className="p-4 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl">
        <p className="text-sm text-status-warning-800 dark:text-status-warning-200 flex items-start gap-2">
          <Star className="w-5 h-5 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <span>
            <strong>Honor System:</strong> We trust you to log your actual reading time. Reading is
            its own reward - enjoy your books!
          </span>
        </p>
      </div>
    </div>
  )
}

// Leaderboard View Component
function LeaderboardView({
  leaderboard,
  isLoading,
  error,
  currentUserId: _currentUserId,
}: {
  leaderboard?: LeaderboardEntry[]
  isLoading: boolean
  error: Error | null
  currentUserId?: number
}): React.ReactElement {
  const { t } = useTranslation()
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose mb-4" />
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Loading leaderboard...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-12 h-12 text-status-danger-500 mx-auto mb-4" aria-hidden="true" />
        <p className="text-status-danger-600 dark:text-status-danger-400">{t('readingMinutes.failedToLoadLeaderboard')}</p>
      </div>
    )
  }

  if (!leaderboard || leaderboard.length === 0) {
    return (
      <div className="text-center py-12">
        <Trophy className="w-16 h-16 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-4" aria-hidden="true" />
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
          No Readers Yet
        </h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          Be the first to log reading minutes and appear on the leaderboard!
        </p>
      </div>
    )
  }

  const getMedalColor = (rank: number) => {
    switch (rank) {
      case 1:
        return 'bg-status-warning-400 text-status-warning-900 dark:text-status-warning-200'
      case 2:
        return 'bg-earth-300 text-lsc-dark/70 dark:text-lsc-cream/70'
      case 3:
        return 'bg-status-warning-600 text-status-warning-100'
      default:
        return 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream'
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-1">
          Top Readers
        </h2>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          See who's reading the most in our community
        </p>
      </div>

      {/* Top 3 podium */}
      {leaderboard.length >= 3 && (
        <div className="flex justify-center items-end gap-4 pb-4">
          {/* 2nd place */}
          <div className="text-center">
            <div
              className={`w-16 h-16 rounded-full flex items-center justify-center text-xl font-bold mx-auto mb-2 ${getMedalColor(
                2
              )}`}
            >
              2
            </div>
            <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate max-w-[5rem]" title={leaderboard[1]!.name}>
              {leaderboard[1]!.name}
            </p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              {leaderboard[1]!.minutes_logged} min
            </p>
          </div>

          {/* 1st place */}
          <div className="text-center -mt-4">
            <div
              className={`w-20 h-20 rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-2 shadow-lg ${getMedalColor(
                1
              )}`}
            >
              <Trophy className="w-8 h-8" />
            </div>
            <p className="text-sm font-bold text-lsc-dark dark:text-lsc-cream truncate max-w-[6.25rem]" title={leaderboard[0]!.name}>
              {leaderboard[0]!.name}
            </p>
            <p className="text-xs text-lsc-rose font-medium">
              {leaderboard[0]!.minutes_logged} min
            </p>
          </div>

          {/* 3rd place */}
          <div className="text-center">
            <div
              className={`w-16 h-16 rounded-full flex items-center justify-center text-xl font-bold mx-auto mb-2 ${getMedalColor(
                3
              )}`}
            >
              3
            </div>
            <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate max-w-[5rem]" title={leaderboard[2]!.name}>
              {leaderboard[2]!.name}
            </p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              {leaderboard[2]!.minutes_logged} min
            </p>
          </div>
        </div>
      )}

      {/* Full list */}
      <div className="space-y-2">
        {leaderboard.map((entry) => (
          <div
            key={entry.rank}
            className={`flex items-center gap-4 p-4 rounded-xl transition-colors ${
              entry.is_you
                ? 'bg-lsc-rose/10 dark:bg-lsc-rose/20 border-2 border-lsc-rose'
                : 'bg-lsc-cream dark:bg-lsc-brown/30 hover:bg-lsc-border dark:hover:bg-lsc-brown/50'
            }`}
          >
            {/* Rank */}
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm ${getMedalColor(
                entry.rank
              )}`}
            >
              {entry.rank <= 3 ? (
                entry.rank === 1 ? (
                  <Trophy className="w-5 h-5" />
                ) : (
                  entry.rank
                )
              ) : (
                entry.rank
              )}
            </div>

            {/* Name */}
            <div className="flex-1 min-w-0">
              <p
                className={`font-medium truncate ${
                  entry.is_you
                    ? 'text-lsc-rose dark:text-lsc-rose-light'
                    : 'text-lsc-dark dark:text-lsc-cream'
                }`}
              >
                {entry.name}
                {entry.is_you && (
                  <span className="ml-2 text-xs bg-lsc-rose text-white px-2 py-0.5 rounded-full">
                    You
                  </span>
                )}
              </p>
            </div>

            {/* Minutes */}
            <div className="text-right">
              <p className="font-bold text-lsc-dark dark:text-lsc-cream">
                {entry.minutes_logged.toLocaleString()}
              </p>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">minutes</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
