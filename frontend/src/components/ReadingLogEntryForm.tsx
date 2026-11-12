/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Loader2, CheckCircle, BookOpen, Clock, Award } from 'lucide-react'
import { createLogEntry, type ReadingRegistration, type ReadingProgram, type ReadingLogEntry } from '@/api/api'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/Button'
import { useTranslation} from '@/i18n'

interface ReadingLogEntryFormProps {
  registration: ReadingRegistration
  program: ReadingProgram
  onSuccess?: () => void
  onCancel?: () => void
}

type EntryMode = 'quick' | 'detailed'

export default function ReadingLogEntryForm({
  registration,
  program,
  onSuccess,
  onCancel,
}: ReadingLogEntryFormProps): React.ReactElement {
  const { t } = useTranslation()
  const { token } = useAuth()
  const [mode, setMode] = useState<EntryMode>('quick')
  const [success, setSuccess] = useState(false)
  const [successData, setSuccessData] = useState<ReadingLogEntry | null>(null)

  // Quick entry fields
  const [minutesRead, setMinutesRead] = useState<string>('')

  // Detailed entry fields
  const [booksRead, setBooksRead] = useState<string>('')
  const [pagesRead, setPagesRead] = useState<string>('')
  const [title, setTitle] = useState<string>('')
  const [author, setAuthor] = useState<string>('')
  const [rating, setRating] = useState<string>('')
  const [notes, setNotes] = useState<string>('')

  const mutation = useMutation({
    mutationFn: (data: Parameters<typeof createLogEntry>[1]) => createLogEntry(token!, data),
    onSuccess: (data) => {
      setSuccessData(data)
      setSuccess(true)
    },
  })

  const handleQuickEntry = (e: React.FormEvent) => {
    e.preventDefault()
    if (!minutesRead) return

    mutation.mutate({
      registration_id: registration.id,
      minutes_read: parseInt(minutesRead, 10),
    })
  }

  const handleDetailedEntry = (e: React.FormEvent) => {
    e.preventDefault()

    const hasAnyReading =
      parseInt(minutesRead || '0', 10) > 0 ||
      parseInt(booksRead || '0', 10) > 0 ||
      parseInt(pagesRead || '0', 10) > 0

    if (!hasAnyReading) {
      toast.error(t('components.readingLogEntryForm.pleaseEnterAtLeastOne'))
      return
    }

    mutation.mutate({
      registration_id: registration.id,
      minutes_read: parseInt(minutesRead || '0', 10),
      books_read: parseInt(booksRead || '0', 10),
      pages_read: parseInt(pagesRead || '0', 10),
      ...(title ? { title } : {}),
      ...(author ? { author } : {}),
      ...(rating ? { rating: parseInt(rating, 10) } : {}),
      ...(notes ? { notes } : {}),
    })
  }

  if (success) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700 text-center space-y-4" role="status" aria-live="polite">
        <CheckCircle className="w-16 h-16 text-lsc-rose dark:text-lsc-rose-light mx-auto" aria-hidden="true" />
        <h3 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
          Reading logged!
        </h3>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          Great job! You've added {successData?.minutes_read}
          {successData?.minutes_read ? ' minutes' : ''}
          {successData?.books_read && successData?.minutes_read ? ', ' : ''}
          {successData?.books_read ? `${successData.books_read} book${successData.books_read > 1 ? 's' : ''}` : ''}
          {successData?.pages_read && (successData?.minutes_read || successData?.books_read) ? ', ' : ''}
          {successData?.pages_read ? `${successData.pages_read} pages` : ''} to {program.name}.
        </p>

        <div className="bg-lsc-cream dark:bg-lsc-brown/30 p-4 rounded-lg space-y-2">
          <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">What's next?</p>
          <ul className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 space-y-1 list-disc list-inside">
            <li>{t('components.readingLogEntryForm.yourProgressHasBeenUpdated')}</li>
            <li>{t('components.readingLogEntryForm.keepLoggingToReachYour')}</li>
            <li>{t('components.readingLogEntryForm.youMayEarnBadgesAs')}</li>
          </ul>
        </div>

        <div className="flex gap-3 pt-4">
          <Button variant="primary"
            onClick={() => {
              // Reset form for next entry
              setSuccess(false)
              setMinutesRead('')
              setBooksRead('')
              setPagesRead('')
              setTitle('')
              setAuthor('')
              setRating('')
              setNotes('')
            }}
          >
            Log More Reading
          </Button>
          {onSuccess && (
            <Button variant="secondary"
              onClick={() => {
                onSuccess()
              }}
            >
              Done
            </Button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700 space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-1">
          Log Your Reading
        </h2>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          for {program.name}
        </p>
      </div>

      {/* Progress indicator */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Your Progress</span>
          <span className="text-sm text-lsc-rose dark:text-lsc-rose-light font-medium">
            {registration.progress_percentage?.toFixed(1) || '0'}%
          </span>
        </div>
        <div className="w-full bg-lsc-cream dark:bg-lsc-brown/30 rounded-full h-3 overflow-hidden">
          <div
            className="bg-lsc-rose h-full transition-all duration-300 rounded-full"
            style={{ width: `${Math.min(registration.progress_percentage || 0, 100)}%` }}
            role="progressbar"
            aria-valuenow={Math.min(registration.progress_percentage || 0, 100)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`${(registration.progress_percentage || 0).toFixed(1)}% toward goal`}
          />
        </div>
        {registration.goal_target && (
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            {registration.total_minutes} / {registration.goal_target} {program.reading_goal_type}
          </p>
        )}
      </div>

      {/* Mode selector */}
      <div className="space-y-3">
        <p id="entry-mode-label" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream">{t('components.readingLogEntryForm.howMuchDidYouRead')}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3" role="group" aria-labelledby="entry-mode-label">
          <Button variant="secondary"
            onClick={() => {
              setMode('quick')
              setBooksRead('')
              setPagesRead('')
              setTitle('')
              setAuthor('')
              setRating('')
              setNotes('')
            }}
          >
            <Clock aria-hidden="true" />
            <div>Quick Entry</div>
            <div>Minutes only</div>
          </Button>

          <Button variant="secondary"
            onClick={() => setMode('detailed')}
          >
            <BookOpen aria-hidden="true" />
            <div>Detailed Entry</div>
            <div>Add book info</div>
          </Button>
        </div>
      </div>

      {/* Quick Entry Form */}
      {mode === 'quick' && (
        <form onSubmit={handleQuickEntry} className="space-y-4">
          <div>
            <label htmlFor="quick_minutes" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
              <div>Minutes Read *</div>
              <div className="text-xs font-normal text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                How many minutes did you read today?
              </div>
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                id="quick_minutes"
                value={minutesRead}
                onChange={(e) => setMinutesRead(e.target.value)}
                min="1"
                max="1440"
                required
                className="flex-1 px-4 py-3 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                placeholder={t('placeholder.readingLogEntryForm.30')}
              />
              <div className="flex items-center px-4 py-3 bg-lsc-cream dark:bg-lsc-brown rounded-xl text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
                min
              </div>
            </div>
          </div>

          {mutation.isError && (
            <div
              role="alert"
              aria-live="polite"
              className="p-3 bg-status-danger-50 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300 rounded-xl text-sm"
            >
              {mutation.error?.message || 'Failed to log reading'}
            </div>
          )}

          <div className="flex gap-3">
            {onCancel && (
              <Button variant="secondary"
                type="button"
                onClick={onCancel}
              >
                Cancel
              </Button>
            )}
            <button
              type="submit"
              disabled={mutation.isPending || !minutesRead}
              className="flex-1 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose disabled:opacity-50 text-white rounded-xl transition-colors flex items-center justify-center gap-2 font-medium"
            >
              {mutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
                  Logging...
                </>
              ) : (
                'Log Reading'
              )}
            </button>
          </div>
        </form>
      )}

      {/* Detailed Entry Form */}
      {mode === 'detailed' && (
        <form onSubmit={handleDetailedEntry} className="space-y-4">
          {/* Reading amounts grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label htmlFor="det_minutes" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                <Clock className="w-4 h-4 inline mr-1" aria-hidden="true" />
                Minutes
              </label>
              <input
                type="number"
                id="det_minutes"
                value={minutesRead}
                onChange={(e) => setMinutesRead(e.target.value)}
                min="0"
                max="1440"
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent text-sm"
                placeholder={t('placeholder.readingLogEntryForm.0')}
              />
            </div>

            <div>
              <label htmlFor="det_books" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                <BookOpen className="w-4 h-4 inline mr-1" aria-hidden="true" />
                Books
              </label>
              <input
                type="number"
                id="det_books"
                value={booksRead}
                onChange={(e) => setBooksRead(e.target.value)}
                min="0"
                max="100"
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent text-sm"
                placeholder={t('placeholder.readingLogEntryForm.0')}
              />
            </div>

            <div>
              <label htmlFor="det_pages" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                <Award className="w-4 h-4 inline mr-1" aria-hidden="true" />
                Pages
              </label>
              <input
                type="number"
                id="det_pages"
                value={pagesRead}
                onChange={(e) => setPagesRead(e.target.value)}
                min="0"
                max="10000"
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent text-sm"
                placeholder={t('placeholder.readingLogEntryForm.0')}
              />
            </div>
          </div>

          {/* Book details */}
          <div className="bg-lsc-cream dark:bg-lsc-brown/20 p-4 rounded-lg space-y-3">
            <h4 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Book Details (optional)</h4>

            <div>
              <label htmlFor="title" className="block text-xs font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
                Book Title
              </label>
              <input
                type="text"
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent text-sm"
                placeholder={t('placeholder.readingLogEntryForm.egTheGreatGatsby')}
              />
            </div>

            <div>
              <label htmlFor="author" className="block text-xs font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
                Author
              </label>
              <input
                type="text"
                id="author"
                value={author}
                onChange={(e) => setAuthor(e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent text-sm"
                placeholder={t('placeholder.readingLogEntryForm.egFScottFitzgerald')}
              />
            </div>

            <div>
              <label htmlFor="rating" className="block text-xs font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
                Rating (1-5 stars)
              </label>
              <select
                id="rating"
                value={rating}
                onChange={(e) => setRating(e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent text-sm"
              >
                <option value="">No rating</option>
                <option value="1">1 star - Not my thing</option>
                <option value="2">2 stars - Okay</option>
                <option value="3">3 stars - Good</option>
                <option value="4">4 stars - Really good</option>
                <option value="5">5 stars - Loved it!</option>
              </select>
            </div>

            <div>
              <label htmlFor="notes" className="block text-xs font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
                Notes
              </label>
              <textarea
                id="notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent text-sm resize-none"
                placeholder={t('components.readingLogEntryForm.whatDidYouThinkAny')}
                rows={2}
              />
            </div>
          </div>

          {mutation.isError && (
            <div
              role="alert"
              aria-live="polite"
              className="p-3 bg-status-danger-50 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300 rounded-xl text-sm"
            >
              {mutation.error?.message || 'Failed to log reading'}
            </div>
          )}

          <div className="flex gap-3">
            {onCancel && (
              <Button variant="secondary"
                type="button"
                onClick={onCancel}
              >
                Cancel
              </Button>
            )}
            <button
              type="submit"
              disabled={mutation.isPending}
              className="flex-1 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose disabled:opacity-50 text-white rounded-xl transition-colors flex items-center justify-center gap-2 font-medium"
            >
              {mutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
                  Logging...
                </>
              ) : (
                'Log Reading'
              )}
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
