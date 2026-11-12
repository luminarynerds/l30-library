/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import FocusTrap from 'focus-trap-react'
import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BookOpen, Clock, TrendingUp, Users, X } from 'lucide-react'
import { ReadingProgram, ReadingRegistration } from '@/api/api'
import { getProgramTypeConfig } from '@/config/program-types'
import { t, getCurrentLocale } from '@/i18n'
import { parseDate } from '@/utils/format-utils'
import { getProgramBooklist } from '@/api/domains/content/reading-programs-api'
import BooklistItemCard from '@/components/programs/BooklistItemCard'
import { downloadPaperLogPdf } from '@/api/domains/content/reading-programs-api'
import { useAuth } from '@/contexts/AuthContext'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import { Printer } from 'lucide-react'

interface ProgramDetailModalProps {
  program: ReadingProgram
  registration?: ReadingRegistration
  onClose: () => void
  onRegister: (program: ReadingProgram) => void
  isRegistered: boolean
}

type TabKey = 'overview' | 'booklist'

export default function ProgramDetailModal({
  program,
  registration,
  onClose,
  onRegister,
  isRegistered,
}: ProgramDetailModalProps): React.ReactElement {
  const [activeTab, setActiveTab] = useState<TabKey>('overview')
  const [printing, setPrinting] = useState(false)
  const [printError, setPrintError] = useState<string | null>(null)
  const { token } = useAuth()
  const { features } = useOrganizationFeatures()
  const paperLogEnabled = features?.reading_programs_paper_log_enabled === true

  const handlePrintLog = async () => {
    if (!registration || !token) return
    setPrintError(null)
    setPrinting(true)
    try {
      await downloadPaperLogPdf(token, program.id, registration.id)
    } catch (err) {
      setPrintError(err instanceof Error ? err.message : 'Failed to download log')
    } finally {
      setPrinting(false)
    }
  }

  // Probe booklist to decide whether to show the tab. Cheap GET; cached.
  const { data: booklistData } = useQuery({
    queryKey: ['program-booklist', program.id],
    queryFn: () => getProgramBooklist(program.id),
    staleTime: 60_000,
    retry: false,
  })
  const booklistItems = booklistData?.items ?? []
  const hasBooklist = booklistItems.length > 0

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])
  const getDaysRemaining = () => {
    const now = new Date()
    const end = new Date(program.end_date)
    const diff = Math.ceil((end.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
    return diff
  }

  const daysRemaining = getDaysRemaining()
  const isEndingSoon = daysRemaining > 0 && daysRemaining <= 7

  return (

    // eslint-disable-next-line jsx-a11y/click-events-have-key-events
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: true }}>
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
      <div role="dialog" aria-modal="true" aria-labelledby="program-detail-title" className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="sticky top-0 bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 p-4 flex items-center justify-between">
          <h2 id="program-detail-title" className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            {program.name}
          </h2>
          <button
            onClick={onClose}
            className="p-2 min-w-[44px] min-h-[44px] flex items-center justify-center hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-full transition-colors touch-manipulation"
            aria-label={t('aria.authModals.close')}
          >
            <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
          </button>
        </div>

        {hasBooklist && (
          <div
            role="tablist"
            aria-label={t('programs.booklist.tablistLabel') || 'Program detail tabs'}
            className="flex border-b border-lsc-border dark:border-earth-700 px-4 bg-lsc-white dark:bg-earth-800"
          >
            <button
              role="tab"
              type="button"
              aria-selected={activeTab === 'overview'}
              onClick={() => setActiveTab('overview')}
              className={`px-4 py-2 min-h-[44px] text-sm font-medium border-b-2 ${
                activeTab === 'overview'
                  ? 'border-lsc-rose text-lsc-dark dark:text-lsc-cream'
                  : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/70'
              }`}
            >
              {t('programs.booklist.tabOverview') || 'Overview'}
            </button>
            <button
              role="tab"
              type="button"
              aria-selected={activeTab === 'booklist'}
              onClick={() => setActiveTab('booklist')}
              data-testid="booklist-tab"
              className={`px-4 py-2 min-h-[44px] text-sm font-medium border-b-2 ${
                activeTab === 'booklist'
                  ? 'border-lsc-rose text-lsc-dark dark:text-lsc-cream'
                  : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/70'
              }`}
            >
              {t('programs.booklist.tab') || 'Suggested reads'}
            </button>
          </div>
        )}

        {activeTab === 'booklist' && hasBooklist ? (
          <div className="p-6 space-y-3">
            <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">
              {t('programs.booklist.tab') || 'Suggested reads'}
            </h3>
            {booklistItems.map((it) => (
              <BooklistItemCard key={it.id} item={it} />
            ))}
          </div>
        ) : (
        <div className="p-6 space-y-5">
          {isEndingSoon && program.is_active && (
            <div className="px-4 py-3 bg-status-warning-50 dark:bg-status-warning-900/20 text-status-warning-700 dark:text-status-warning-400 text-sm font-medium rounded-xl flex items-center gap-2">
              <Clock className="w-4 h-4" aria-hidden="true" />
              {daysRemaining === 1 ? 'This program ends tomorrow!' : `Only ${daysRemaining} days left to join!`}
            </div>
          )}

          {isRegistered && registration && (
            <div className="bg-gradient-to-r from-lsc-rose/10 to-lsc-cream dark:from-lsc-brown/50 dark:to-earth-700 rounded-xl p-4 space-y-3">
              <div className="flex items-center gap-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                <TrendingUp className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
                Your Progress
              </div>
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <div className="h-3 bg-lsc-cream dark:bg-lsc-brown/50 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-lsc-rose to-lsc-rose-light rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(registration.progress_percentage, 100)}%` }}
                    />
                  </div>
                </div>
                <div className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">
                  {Math.round(registration.progress_percentage)}%
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3 pt-2">
                <div className="text-center">
                  <div className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{registration.total_books}</div>
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Books</div>
                </div>
                <div className="text-center">
                  <div className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{registration.total_minutes}</div>
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Minutes</div>
                </div>
                <div className="text-center">
                  <div className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{registration.total_pages}</div>
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Pages</div>
                </div>
              </div>
            </div>
          )}

          {isRegistered && registration && paperLogEnabled && (
            <div className="flex flex-col gap-2">
              <button
                type="button"
                onClick={handlePrintLog}
                disabled={printing}
                className="flex items-center justify-center gap-2 px-4 py-3 min-h-[48px] border-2 border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-all font-medium shadow-sm hover:shadow disabled:opacity-60 touch-manipulation"
              >
                <Printer className="w-4 h-4" aria-hidden="true" />
                {printing
                  ? (t('programs.printLog.generating') || "Preparing log...")
                  : (t('programs.printLog.button') || "Print reading log")}
              </button>
              {printError && (
                <div role="alert" className="text-sm text-status-danger-600 dark:text-status-danger-400">
                  {printError}
                </div>
              )}
            </div>
          )}

          {program.description && (
            <div>
              <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">About this program</h3>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{program.description}</p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-lsc-cream dark:bg-lsc-brown/30 rounded-lg">
              <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Program Type</div>
              <div className="font-medium text-lsc-dark dark:text-lsc-cream">
                {getProgramTypeConfig(program.program_type).label}
              </div>
            </div>
            <div className="p-3 bg-lsc-cream dark:bg-lsc-brown/30 rounded-lg">
              <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Age Group</div>
              <div className="font-medium text-lsc-dark dark:text-lsc-cream">
                {program.target_age_min && program.target_age_max
                  ? `${program.target_age_min}–${program.target_age_max} years`
                  : program.age_group || 'All ages'}
              </div>
            </div>
            <div className="p-3 bg-lsc-cream dark:bg-lsc-brown/30 rounded-lg">
              <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Duration</div>
              <div className="font-medium text-lsc-dark dark:text-lsc-cream">
                {parseDate(program.start_date)?.toLocaleDateString() ?? '-'} –{' '}
                {parseDate(program.end_date)?.toLocaleDateString() ?? '-'}
              </div>
            </div>
            <div className="p-3 bg-lsc-cream dark:bg-lsc-brown/30 rounded-lg">
              <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Reading Goal</div>
              <div className="font-medium text-lsc-dark dark:text-lsc-cream">
                {program.reading_goal_value && program.reading_goal_type
                  ? `${program.reading_goal_value} ${program.reading_goal_type}`
                  : 'No set goal'}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-6 py-3 px-4 bg-lsc-cream/50 dark:bg-lsc-brown/20 rounded-xl">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                <strong>{program.registration_count}</strong> participants
              </span>
            </div>
            <div className="flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                <strong>{program.total_books_read}</strong> books read
              </span>
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-3 min-h-[48px] border-2 border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-all font-medium shadow-sm hover:shadow touch-manipulation"
            >
              Close
            </button>
            {!isRegistered && program.is_active && (() => {
              const now = new Date()
              const start = new Date(program.start_date)
              const hasStarted = now >= start
              return hasStarted ? (
                <button
                  onClick={() => onRegister(program)}
                  className="flex-1 px-4 py-3 min-h-[48px] bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl shadow-md hover:shadow-lg active:shadow-sm transition-all font-semibold touch-manipulation"
                >
                  Join Program
                </button>
              ) : (
                <div className="flex-1 px-4 py-3 min-h-[48px] bg-lsc-cream dark:bg-lsc-brown/30 text-lsc-dark/70 dark:text-lsc-cream/70 rounded-xl text-center font-medium flex items-center justify-center">
                  Registration opens {start.toLocaleDateString(getCurrentLocale(), { month: 'short', day: 'numeric' })}
                </div>
              )
            })()}
          </div>
        </div>
        )}
      </div>
      </FocusTrap>
    </div>
  )
}
