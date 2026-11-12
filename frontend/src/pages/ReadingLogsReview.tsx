/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from "react"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import { Book, CheckCircle, XCircle, Loader2, RefreshCw, Clock, User, Users, Trophy, Calendar } from "lucide-react"
import toast from "react-hot-toast"
import { fetchApi } from '@/api/fetchApi'
import { useTranslation} from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { parseDate } from '@/utils/format-utils'

interface ReadingLog {
  id: number
  user_id: number
  minutes: number
  book_title: string | null
  book_author: string | null
  notes: string | null
  status: "pending" | "approved" | "rejected"
  reading_date: string
  created_at: string
  patron_name: string | null
}

interface ReadingStats {
  pending_reviews: number
  approved_minutes_this_month: number
  active_participants: number
}

interface ReadingProgram {
  id: number
  name: string
  description: string | null
  program_type: string
  age_group: string | null
  start_date: string
  end_date: string
  is_active: boolean
  registration_count: number
  total_minutes_read: number
  total_books_read: number
}

type ReviewTab = "read-to-reduce" | "programs"

export default function ReadingLogsReviewPage(): React.ReactElement {
  const { t } = useTranslation()
  const { token, isAuthenticated, isLoading: authLoading } = useAuth()
  const [logs, setLogs] = useState<ReadingLog[]>([])
  const [stats, setStats] = useState<ReadingStats | null>(null)
  const [programs, setPrograms] = useState<ReadingProgram[]>([])
  const [activeTab, setActiveTab] = useState<ReviewTab>("read-to-reduce")
  const [isLoading, setIsLoading] = useState(true)
  const [reviewingId, setReviewingId] = useState<number | null>(null)
  const [rejectionReason, setRejectionReason] = useState("")
  const [showRejectModal, setShowRejectModal] = useState<number | null>(null)
  const [hasMore, setHasMore] = useState(false)

  const fetchData = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const [logsRes, statsRes, programsRes] = await Promise.all([
        fetchApi('/reading/pending'),
        fetchApi('/reading/stats'),
        fetchApi('/reading-programs?active_only=true&limit=20').catch(() => ({ items: [] })),
      ])
      setLogs(logsRes)
      setHasMore(Array.isArray(logsRes) && logsRes.length >= 50)
      setStats(statsRes)
      setPrograms(programsRes.items || [])
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)))
      toast.error(t('readingLogsReview.failedToLoadReadingLogs'))
    } finally {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  useEffect(() => {
    if (isAuthenticated && token) fetchData()
  }, [isAuthenticated, token, fetchData])

  const handleReview = async (logId: number, approved: boolean, reason?: string) => {
    if (!token) return
    setReviewingId(logId)
    try {
      await fetchApi(`/reading/${logId}/review`, {
        method: "POST",
        body: JSON.stringify({
          approved,
          rejection_reason: reason || null,
        }),
      })
      toast.success(approved ? t('toast.readingLogsReview.readingLogApproved') : t('toast.readingLogsReview.readingLogRejected'))
      setShowRejectModal(null)
      setRejectionReason("")
      fetchData()
    } catch (_err) {
      toast.error(t('readingLogsReview.failedToReviewReadingLog'))
    } finally {
      setReviewingId(null)
    }
  }

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (!isAuthenticated) return <></>

  return (
    <AdminShell title="Reading Review">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                Reading Review
              </h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                Review reading logs and monitor reading program activity
              </p>
            </div>
            <button
              onClick={fetchData}
              className="flex items-center gap-2 px-4 py-2 text-lsc-rose hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
            >
              <RefreshCw aria-hidden="true" className="w-4 h-4" />
              Refresh
            </button>
          </div>

          {/* Tab Navigation */}
          <div className="flex border-b border-lsc-border dark:border-earth-700">
            <button
              onClick={() => setActiveTab("read-to-reduce")}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors -mb-px ${
                activeTab === "read-to-reduce"
                  ? "border-b-2 border-lsc-rose text-lsc-rose font-semibold bg-lsc-rose/5 dark:bg-lsc-rose/10"
                  : "border-b-2 border-transparent text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream hover:border-lsc-border dark:hover:border-earth-600"
              }`}
            >
              <Book aria-hidden="true" className="w-4 h-4" />
              Read to Reduce
              {stats && stats.pending_reviews > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-xs font-bold bg-lsc-rose text-white rounded-full">
                  {stats.pending_reviews}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab("programs")}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors -mb-px ${
                activeTab === "programs"
                  ? "border-b-2 border-lsc-rose text-lsc-rose font-semibold bg-lsc-rose/5 dark:bg-lsc-rose/10"
                  : "border-b-2 border-transparent text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream hover:border-lsc-border dark:hover:border-earth-600"
              }`}
            >
              <Trophy aria-hidden="true" className="w-4 h-4" />
              Reading Programs
              {programs.length > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-xs font-bold bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 rounded-full">
                  {programs.length}
                </span>
              )}
            </button>
          </div>

          {activeTab === "read-to-reduce" && (
            <>
              {/* Stats */}
              {stats && (
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-dark/30 rounded-xl flex items-center justify-center">
                        <Clock aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
                      </div>
                      <div>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Pending Reviews</p>
                        <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{stats.pending_reviews}</p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl flex items-center justify-center">
                        <Book aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
                      </div>
                      <div>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Approved This Month</p>
                        <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{stats.approved_minutes_this_month} min</p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-lsc-cream dark:bg-earth-800/30 rounded-xl flex items-center justify-center">
                        <User aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
                      </div>
                      <div>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Active Participants</p>
                        <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{stats.active_participants}</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Pending Logs */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700">
                <div className="p-4 border-b border-lsc-border dark:border-earth-700">
                  <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                    Pending Reading Logs
                  </h2>
                </div>

                {logs.length > 0 ? (
                  <>
                  <div className="divide-y divide-lsc-border dark:divide-earth-700">
                    {logs.map((log) => (
                      <div key={log.id} className="p-4 hover:bg-lsc-cream dark:hover:bg-lsc-brown/50">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            {log.patron_name && (
                              <p className="text-sm font-medium text-lsc-dark/80 dark:text-lsc-cream/80 flex items-center gap-1 mb-1">
                                <User className="w-3.5 h-3.5 text-lsc-rose" aria-hidden="true" />
                                {log.patron_name}
                              </p>
                            )}
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                                {log.minutes} minutes
                              </span>
                              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                                on {parseDate(log.reading_date)?.toLocaleDateString() ?? '-'}
                              </span>
                            </div>
                            {log.book_title && (
                              <p className="text-lsc-dark dark:text-lsc-cream/80 flex items-center gap-1">
                                <Book className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
                                {log.book_title}
                                {log.book_author && <span className="text-lsc-dark/70 dark:text-lsc-cream/70"> by {log.book_author}</span>}
                              </p>
                            )}
                            {log.notes && (
                              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 italic">
                                "{log.notes}"
                              </p>
                            )}
                            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                              Submitted {new Date(log.created_at).toLocaleString()}
                            </p>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleReview(log.id, true)}
                              disabled={reviewingId === log.id}
                              className="p-2 bg-lsc-cream hover:bg-lsc-border dark:bg-lsc-brown/30 dark:hover:bg-lsc-brown/50 text-lsc-rose dark:text-lsc-cream/70 rounded-xl transition-colors disabled:opacity-50"
                              title="Approve"
                            >
                              {reviewingId === log.id ? (
                                <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
                              ) : (
                                <CheckCircle aria-hidden="true" className="w-5 h-5" />
                              )}
                            </button>
                            <button
                              onClick={() => setShowRejectModal(log.id)}
                              disabled={reviewingId === log.id}
                              className="p-2 bg-status-danger-100 hover:bg-status-danger-200 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/50 text-status-danger-700 dark:text-status-danger-300 rounded-xl transition-colors disabled:opacity-50"
                              title="Reject"
                            >
                              <XCircle aria-hidden="true" className="w-5 h-5" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  {hasMore && (
                    <div className="p-3 text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/60 border-t border-lsc-border dark:border-earth-700">
                      Showing first 50 pending logs
                    </div>
                  )}
                  </>
                ) : (
                  <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                    <CheckCircle aria-hidden="true" className="w-12 h-12 mx-auto mb-2 text-lsc-rose" />
                    <p className="font-medium">All caught up!</p>
                    <p className="text-sm">{t('readingLogsReview.noPendingReadingLogsTo')}</p>
                  </div>
                )}
              </div>
            </>
          )}

          {activeTab === "programs" && (
            <>
              {/* Programs Summary Stats */}
              {programs.length > 0 && (
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-dark/30 rounded-xl flex items-center justify-center">
                        <Trophy aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
                      </div>
                      <div>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Active Programs</p>
                        <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{programs.length}</p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl flex items-center justify-center">
                        <Users aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
                      </div>
                      <div>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Registrations</p>
                        <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                          {programs.reduce((sum, p) => sum + (p.registration_count || 0), 0)}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-lsc-cream dark:bg-earth-800/30 rounded-xl flex items-center justify-center">
                        <Book aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
                      </div>
                      <div>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Minutes Read</p>
                        <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                          {programs.reduce((sum, p) => sum + (p.total_minutes_read || 0), 0).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Active Programs List */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700">
                <div className="p-4 border-b border-lsc-border dark:border-earth-700">
                  <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                    Active Reading Programs
                  </h2>
                </div>

                {programs.length > 0 ? (
                  <div className="divide-y divide-lsc-border dark:divide-earth-700">
                    {programs.map((program) => (
                      <div key={program.id} className="p-4 hover:bg-lsc-cream dark:hover:bg-lsc-brown/50">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                              {program.name}
                            </h3>
                            {program.description && (
                              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5 line-clamp-2" title={program.description}>
                                {program.description}
                              </p>
                            )}
                            <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded-full capitalize">
                                {program.program_type.replace("_", " ")}
                              </span>
                              {program.age_group && (
                                <span className="inline-flex items-center gap-1">
                                  <Users className="w-3 h-3" aria-hidden="true" />
                                  {program.age_group}
                                </span>
                              )}
                              <span className="inline-flex items-center gap-1">
                                <Calendar className="w-3 h-3" aria-hidden="true" />
                                {parseDate(program.start_date)?.toLocaleDateString() ?? '-'} &ndash; {parseDate(program.end_date)?.toLocaleDateString() ?? '-'}
                              </span>
                            </div>
                          </div>
                          <div className="text-right flex-shrink-0 space-y-1">
                            <p className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                              {program.registration_count || 0} <span className="font-normal text-lsc-dark/70 dark:text-lsc-cream/70">readers</span>
                            </p>
                            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                              {(program.total_minutes_read || 0).toLocaleString()} min
                            </p>
                            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                              {program.total_books_read || 0} books
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                    <Trophy aria-hidden="true" className="w-12 h-12 mx-auto mb-2 opacity-30" />
                    <p className="font-medium">No active programs</p>
                    <p className="text-sm">{t('readingLogsReview.readingProgramsWillAppearHere')}</p>
                  </div>
                )}
              </div>
            </>
          )}

      {/* Reject Modal */}
      {showRejectModal && (
        <ModalBackdrop onClose={() => { setShowRejectModal(null); setRejectionReason("") }} title="Reject Reading Log" role="alertdialog">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-md w-full p-6 shadow-lg">
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
              Reject Reading Log
            </h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
              Please provide a reason for rejection (optional but helpful):
            </p>
            <textarea
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder={t('placeholder.readingLogsReview.egPleaseTryTo')}
              rows={3}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 resize-none mb-4"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setShowRejectModal(null)
                  setRejectionReason("")
                }}
                className="px-4 py-2 text-lsc-dark/70 hover:bg-lsc-cream dark:text-lsc-cream/70 dark:hover:bg-lsc-brown rounded-xl transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleReview(showRejectModal, false, rejectionReason)}
                disabled={reviewingId === showRejectModal}
                className="px-4 py-2 bg-status-danger-600 hover:bg-status-danger-700 text-white rounded-xl transition-colors disabled:opacity-50"
              >
                Reject
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </AdminShell>
  )
}