/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BookOpen, Loader2, TrendingUp, Award, Calendar, Trophy, Star, RefreshCw, AlertCircle } from 'lucide-react'
import { getMyRegistrations, getProgramProgress } from '@/api/api'
import { useAuth } from '@/contexts/AuthContext'
import ReadingLogEntryForm from '@/components/ReadingLogEntryForm'
import { useTranslation } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

export default function ReadingLogsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { token, isAuthenticated } = useAuth()
  const [selectedRegistrationId, setSelectedRegistrationId] = useState<number | null>(null)
  const [showForm, setShowForm] = useState(false)
  const previousProgressRef = useRef<typeof progress>(null)

  // Fetch user registrations
  const { data: registrations = [], isLoading: isLoadingRegistrations, error: registrationsError, refetch: refetchRegistrations } = useQuery({
    queryKey: ['my-registrations'],
    queryFn: () => (token ? getMyRegistrations(token) : Promise.resolve([])),
    enabled: isAuthenticated && !!token,
  })

  // Fetch progress for selected registration
  const selectedReg = registrations.find((r) => r.id === selectedRegistrationId)
  const { data: progress, isLoading: isLoadingProgress, error: progressError, refetch: refetchProgress } = useQuery({
    queryKey: ['program-progress', selectedRegistrationId],
    queryFn: () => (token && selectedRegistrationId ? getProgramProgress(token, selectedRegistrationId) : null),
    enabled: isAuthenticated && !!token && !!selectedRegistrationId,
  })

  // Keep reference to previous progress for smooth transitions
  if (progress) {
    previousProgressRef.current = progress
  }
  const displayProgress = progress || previousProgressRef.current

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark py-20">
        <PageContainer className="text-center">
          <BookOpen className="w-16 h-16 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-4" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">Reading Logs</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Please log in to view and manage your reading logs.
          </p>
        </PageContainer>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">My Reading Logs</h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          Track your reading activity across all programs
        </p>
      </div>

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Programs list */}
        <div className="lg:col-span-1">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
            <h2 className="font-medium text-lsc-dark dark:text-lsc-cream mb-4">My Programs</h2>

            {isLoadingRegistrations ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : registrationsError ? (
              <div className="py-6 text-center space-y-3" role="alert">
                <AlertCircle className="w-8 h-8 text-status-danger-500 mx-auto" aria-hidden="true" />
                <p className="text-sm text-status-danger-600 dark:text-status-danger-400">
                  Failed to load reading programs. Please refresh or try again later.
                </p>
                <button
                  onClick={() => refetchRegistrations()}
                  className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-lsc-rose hover:text-lsc-rose/80 border border-lsc-rose/30 rounded-lg transition-colors"
                >
                  <RefreshCw className="w-4 h-4" aria-hidden="true" />
                  Retry
                </button>
              </div>
            ) : registrations.length === 0 ? (
              <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
                <BookOpen className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Join a reading program to start tracking your progress</p>
                <a
                  href="/programs"
                  className="mt-3 inline-block text-lsc-rose hover:text-lsc-rose/80 font-medium text-sm"
                >
                  View available programs →
                </a>
              </div>
            ) : (
              <div className="space-y-2">
                {registrations.map((reg) => (
                  <button
                    key={reg.id}
                    onClick={() => {
                      setSelectedRegistrationId(reg.id)
                      setShowForm(false)
                    }}
                    className={`w-full text-left p-3 rounded-lg transition-colors ${
                      selectedRegistrationId === reg.id
                        ? 'bg-lsc-rose text-white'
                        : 'bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-border dark:hover:bg-lsc-brown/80 text-lsc-dark dark:text-lsc-cream'
                    }`}
                  >
                    <div className="text-sm font-medium">Program {reg.program_id}</div>
                    <div className="text-xs opacity-75 mt-1">
                      {reg.progress_percentage?.toFixed(0)}% complete
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Detail and form area */}
        <div className="lg:col-span-2 space-y-6">
          {/* Progress error state */}
          {progressError && selectedRegistrationId && (
            <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-4 flex items-center gap-3" role="alert">
              <AlertCircle className="w-5 h-5 text-status-danger-500 flex-shrink-0" aria-hidden="true" />
              <div className="flex-1">
                <p className="text-sm text-status-danger-700 dark:text-status-danger-300">
                  Failed to load program progress. Please try again.
                </p>
              </div>
              <button
                onClick={() => refetchProgress()}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-status-danger-700 dark:text-status-danger-300 hover:bg-status-danger-100 dark:hover:bg-status-danger-900/30 rounded-lg transition-colors"
              >
                <RefreshCw className="w-4 h-4" aria-hidden="true" />
                Retry
              </button>
            </div>
          )}

          {selectedRegistrationId && selectedReg && displayProgress ? (
            <div className={`space-y-6 transition-opacity duration-200 ${isLoadingProgress ? 'opacity-50' : 'opacity-100'}`}>
              {/* Program details card */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 space-y-4">
                <div>
                  <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                    {displayProgress.program.name}
                  </h2>
                  {displayProgress.program.description && (
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{displayProgress.program.description}</p>
                  )}
                </div>

                {/* Stats grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="p-3 bg-lsc-cream dark:bg-lsc-brown/30 rounded-lg">
                    <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Progress</div>
                    <div className="text-xl font-bold text-lsc-rose dark:text-lsc-rose-light mt-1">
                      {displayProgress.completion_percentage.toFixed(0)}%
                    </div>
                  </div>

                  {displayProgress.program.reading_goal_type === 'minutes' && (
                    <div className="p-3 bg-lsc-cream dark:bg-lsc-brown/30 rounded-lg">
                      <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Minutes</div>
                      <div className="text-xl font-bold text-lsc-dark dark:text-lsc-cream mt-1">
                        {displayProgress.total_minutes}
                        <span className="text-xs font-normal opacity-75">/{displayProgress.registration.goal_target}</span>
                      </div>
                    </div>
                  )}

                  {displayProgress.program.reading_goal_type === 'books' && (
                    <div className="p-3 bg-lsc-cream dark:bg-lsc-brown/30 rounded-lg">
                      <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Books</div>
                      <div className="text-xl font-bold text-lsc-dark dark:text-lsc-cream mt-1">
                        {displayProgress.total_books}
                        <span className="text-xs font-normal opacity-75">/{displayProgress.registration.goal_target}</span>
                      </div>
                    </div>
                  )}

                  {displayProgress.program.reading_goal_type === 'pages' && (
                    <div className="p-3 bg-lsc-cream dark:bg-lsc-brown/30 rounded-lg">
                      <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Pages</div>
                      <div className="text-xl font-bold text-lsc-dark dark:text-lsc-cream mt-1">
                        {displayProgress.total_pages}
                        <span className="text-xs font-normal opacity-75">/{displayProgress.registration.goal_target}</span>
                      </div>
                    </div>
                  )}

                  <div className="p-3 bg-lsc-cream dark:bg-lsc-brown/30 rounded-lg">
                    <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Days Active</div>
                    <div className="text-xl font-bold text-lsc-dark dark:text-lsc-cream mt-1">
                      {displayProgress.days_participated}
                    </div>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="space-y-2">
                  <div className="w-full bg-lsc-cream dark:bg-lsc-brown/30 rounded-full h-3 overflow-hidden">
                    <div
                      className="bg-lsc-rose h-full transition-all duration-300 rounded-full"
                      style={{ width: `${Math.min(displayProgress.completion_percentage, 100)}%` }}
                      role="progressbar"
                      aria-valuenow={Math.min(displayProgress.completion_percentage, 100)}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={`${displayProgress.completion_percentage.toFixed(1)}% toward goal`}
                    />
                  </div>
                </div>

                {/* Achievements */}
                {displayProgress.achievements && displayProgress.achievements.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-lsc-border dark:border-earth-700">
                    <div className="flex items-center gap-2">
                      <Award className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
                      <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Achievements</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {displayProgress.achievements.map((badge) => (
                        <div
                          key={badge.id}
                          className="px-3 py-1 bg-lsc-rose/20 text-lsc-rose rounded-full text-xs font-medium flex items-center gap-1"
                          role="img"
                          aria-label={badge.badge_name + ': ' + (badge.badge_description || 'Achievement badge')}
                          title={badge.badge_description || ''}
                        >
                          <Trophy className="w-3 h-3" aria-hidden="true" />
                          {badge.badge_name}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Form toggle */}
              {!showForm && (
                <button
                  onClick={() => setShowForm(true)}
                  className="w-full px-4 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium transition-colors flex items-center justify-center gap-2"
                >
                  <BookOpen className="w-5 h-5" />
                  Log Reading
                </button>
              )}

              {/* Entry form */}
              {showForm && (
                <ReadingLogEntryForm
                  registration={selectedReg}
                  program={displayProgress.program}
                  onSuccess={() => {
                    setShowForm(false)
                    // Refetch progress
                  }}
                  onCancel={() => setShowForm(false)}
                />
              )}

              {/* Recent logs */}
              {displayProgress.log_entries && displayProgress.log_entries.length > 0 && (
                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 space-y-4">
                  <h3 className="font-medium text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                    <Calendar className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
                    Recent Logs
                  </h3>

                  <div className="space-y-3">
                    {displayProgress.log_entries.slice(0, 5).map((entry) => (
                      <div
                        key={entry.id}
                        className="p-3 bg-lsc-cream dark:bg-lsc-brown/30 rounded-lg space-y-2"
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            {entry.title && (
                              <div className="font-medium text-lsc-dark dark:text-lsc-cream flex items-center gap-1">
                                {entry.title}
                                {entry.rating && (
                                  <span className="ml-2 inline-flex items-center" aria-label={`Rating: ${entry.rating} out of 5 stars`}>
                                    {Array.from({ length: entry.rating }).map((_, i) => (
                                      <Star key={i} className="w-3 h-3 fill-yellow-400 text-status-warning-400" aria-hidden="true" />
                                    ))}
                                  </span>
                                )}
                              </div>
                            )}
                            {entry.author && (
                              <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">by {entry.author}</div>
                            )}
                          </div>
                          <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                            {new Date(entry.logged_at).toLocaleDateString()}
                          </div>
                        </div>

                        <div className="flex gap-3 text-sm">
                          {entry.minutes_read > 0 && (
                            <span className="text-lsc-rose dark:text-lsc-rose-light font-medium">
                              {entry.minutes_read} min
                            </span>
                          )}
                          {entry.books_read > 0 && (
                            <span className="text-lsc-rose dark:text-lsc-rose-light font-medium">
                              {entry.books_read} book{entry.books_read > 1 ? 's' : ''}
                            </span>
                          )}
                          {entry.pages_read > 0 && (
                            <span className="text-lsc-rose dark:text-lsc-rose-light font-medium">
                              {entry.pages_read} pages
                            </span>
                          )}
                        </div>

                        {entry.notes && (
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 italic">"{entry.notes}"</p>
                        )}
                      </div>
                    ))}

                    {displayProgress.log_entries.length > 5 && (
                      <div className="text-center pt-2">
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          +{displayProgress.log_entries.length - 5} more entries
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : selectedRegistrationId && isLoadingProgress && !displayProgress ? (
            <div className="flex justify-center py-20">
              <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
            </div>
          ) : (
            <div className="text-center py-20 text-lsc-dark/70 dark:text-lsc-cream/70">
              <TrendingUp className="w-16 h-16 mx-auto mb-4 opacity-50" aria-hidden="true" />
              <p>{t('readingLogs.selectAProgramToView')}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
