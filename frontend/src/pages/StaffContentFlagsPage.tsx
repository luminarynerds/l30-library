/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import {
  Flag,
  RefreshCw,
  Loader2,
  Eye,
  Filter,
  ChevronLeft,
  ChevronRight,
  BarChart3,
  TrendingUp,
  TrendingDown,
} from "lucide-react"
import toast from "react-hot-toast"
import {
  contentFlagService,
  ContentFlag,
  FlagStatistics,
  FlagListResponse,
  FlagsFeedback,
} from "../api/contentFlagService"
import { useTranslation } from '@/i18n'
import FlagDetailModal from '../components/content-flags/FlagDetailModal'
import { STATUS_OPTIONS, REVIEW_TYPE_OPTIONS } from '../components/content-flags/content-flags-data'
import { getStatusConfig, getFlagTypeConfig } from '../components/content-flags/FlagConfig'

export default function StaffContentFlagsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(true)
  const [flags, setFlags] = useState<ContentFlag[]>([])
  const [stats, setStats] = useState<FlagStatistics | null>(null)
  const [totalFlags, setTotalFlags] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [perPage] = useState(20)

  const [statusFilter, setStatusFilter] = useState("")
  const [reviewTypeFilter, setReviewTypeFilter] = useState("")
  const [minScoreFilter, setMinScoreFilter] = useState(70)
  const [showFilters, setShowFilters] = useState(false)

  const [selectedFlag, setSelectedFlag] = useState<ContentFlag | null>(null)

  useEffect(() => {
    if (!authLoading && (!user || !["staff", "admin", "super_admin"].includes(user.role))) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, isAuthenticated, user, navigate, t])

  const fetchFlags = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const response: FlagListResponse = await contentFlagService.getFlaggedContent(
        currentPage,
        perPage,
        {
          ...(statusFilter && { status: statusFilter }),
          ...(reviewTypeFilter && { review_type: reviewTypeFilter }),
          min_score: minScoreFilter,
        }
      )
      setFlags(response.items)
      setTotalFlags(response.total)
      setTotalPages(response.total_pages)
    } catch (_error: unknown) {
      toast.error(t('staffContentFlags.failedToLoadFlaggedContent'))
    } finally {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, currentPage, perPage, statusFilter, reviewTypeFilter, minScoreFilter])

  const fetchStats = useCallback(async () => {
    if (!token) return
    try {
      const statsData = await contentFlagService.getStatistics(30)
      setStats(statsData)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }, [token])

  useEffect(() => {
    if (token && isAuthenticated) {
      fetchFlags()
      fetchStats()
    }
  }, [token, isAuthenticated, fetchFlags, fetchStats])

  const handleResolveFlag = async (flagId: number, feedback: FlagsFeedback) => {
    try {
      await contentFlagService.resolveFlag(flagId, feedback)
      toast.success(t('toast.staffContentFlags.flagResolvedSuccessfully'))
      fetchFlags()
      fetchStats()
    } catch (error: unknown) {
      toast.error(t('staffContentFlags.failedToResolveFlag'))
      throw error
    }
  }

  const handleModerateReview = async (
    reviewId: number,
    action: "approve" | "reject" | "remove",
    reason?: string
  ) => {
    try {
      await contentFlagService.moderateEventReview(reviewId, action, reason)
      const pastTense: Record<string, string> = { approve: 'approved', reject: 'rejected', remove: 'removed' }
      toast.success(t('toast.staffContentFlags.reviewPasttenseactionactionSuccessfully', { pastTenseactionaction: pastTense[action] ?? action }))
      await fetchFlags()
      await fetchStats()
      if (selectedFlag) {
        await handleViewDetails(selectedFlag.id)
      }
    } catch (error: unknown) {
      toast.error(t('toast.staffContentFlags.failedToActionReview', { action: action }))
      throw error
    }
  }

  const handleEditReview = async (reviewId: number, comment: string, reason?: string) => {
    try {
      await contentFlagService.editEventReview(reviewId, {
        comment,
        ...(reason && { reason }),
      })
      toast.success(t('toast.staffContentFlags.reviewUpdatedSuccessfully'))
      await fetchFlags()
      await fetchStats()
      if (selectedFlag) {
        await handleViewDetails(selectedFlag.id)
      }
    } catch (error: unknown) {
      toast.error(t('staffContentFlags.failedToUpdateReview'))
      throw error
    }
  }

  const handleViewDetails = async (flagId: number) => {
    try {
      const flagDetails = await contentFlagService.getFlagDetails(flagId)
      setSelectedFlag(flagDetails)
    } catch (_error: unknown) {
      toast.error(t('staffContentFlags.failedToLoadFlagDetails'))
    }
  }

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (!user || !["staff", "admin", "super_admin"].includes(user.role)) {
    return <></>
  }

  return (
    <AdminShell title="Content Moderation">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                Content Moderation
              </h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                Review and act on AI-flagged content
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-colors ${
                  showFilters
                    ? "bg-lsc-rose text-white"
                    : "text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20"
                }`}
              >
                <Filter className="w-4 h-4" />
                Filters
              </button>
              <button
                onClick={() => { fetchFlags(); fetchStats(); }}
                className="flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? "motion-safe:animate-spin" : ""}`} />
                Refresh
              </button>
            </div>
          </div>

          {stats && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <Flag className="w-4 h-4" />
                  <span className="text-xs uppercase">Total Flags</span>
                </div>
                <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{stats.total_flags}</p>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Last 30 days</p>
              </div>

              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <BarChart3 className="w-4 h-4" />
                  <span className="text-xs uppercase">Avg Confidence</span>
                </div>
                <p className={`text-2xl font-bold ${
                  stats.avg_confidence >= 80 ? "text-status-success-600 dark:text-status-success-400" :
                  stats.avg_confidence >= 60 ? "text-status-warning-600 dark:text-status-warning-400" :
                  "text-status-danger-600 dark:text-status-danger-400"
                }`}>
                  {stats.avg_confidence}%
                </p>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">AI accuracy</p>
              </div>

              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <TrendingDown className="w-4 h-4" />
                  <span className="text-xs uppercase">False Positives</span>
                </div>
                <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">{stats.false_positives}</p>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{stats.false_positive_rate}% rate</p>
              </div>

              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <TrendingUp className="w-4 h-4" />
                  <span className="text-xs uppercase">High Confidence</span>
                </div>
                <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">{stats.high_confidence_flags}</p>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Score above 70%</p>
              </div>
            </div>
          )}

          {showFilters && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Status</label>
                  <select
                    value={statusFilter}
                    onChange={(e) => { setStatusFilter(e.target.value); setCurrentPage(1); }}
                    className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  >
                    {STATUS_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Review Type</label>
                  <select
                    value={reviewTypeFilter}
                    onChange={(e) => { setReviewTypeFilter(e.target.value); setCurrentPage(1); }}
                    className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  >
                    {REVIEW_TYPE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                    Min Score: {minScoreFilter}%
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={minScoreFilter}
                    onChange={(e) => { setMinScoreFilter(Number(e.target.value)); setCurrentPage(1); }}
                    className="w-full accent-lsc-rose"
                  />
                </div>
              </div>
            </div>
          )}

          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : flags.length === 0 ? (
              <div className="p-8 text-center">
                <Flag className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">No flagged content found</h3>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                  {statusFilter || reviewTypeFilter ? "Try adjusting your filters" : "No content has been flagged for review"}
                </p>
              </div>
            ) : (
              <>
                <div className="hidden md:block overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-lsc-cream/50 dark:bg-earth-700 border-b border-lsc-border dark:border-earth-700">
                        <th className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">ID</th>
                        <th className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Review Type</th>
                        <th className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Flag Type</th>
                        <th className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Score</th>
                        <th className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Status</th>
                        <th className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Created</th>
                        <th className="px-6 py-4 text-right text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {flags.map((flag, idx) => {
                        const statusConfig = getStatusConfig(flag.status)
                        const flagTypeConfig = getFlagTypeConfig(flag.flag_type)
                        return (
                          <tr
                            key={flag.id}
                            className={`border-b border-lsc-border dark:border-earth-700 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/50 transition-colors ${
                              idx % 2 === 0 ? "bg-lsc-white dark:bg-earth-800" : "bg-lsc-cream/20 dark:bg-earth-700/30"
                            }`}
                          >
                            <td className="px-6 py-4 text-sm text-lsc-dark dark:text-lsc-cream">#{flag.id}</td>
                            <td className="px-6 py-4 text-sm text-lsc-dark dark:text-lsc-cream capitalize">
                              {flag.review_type.replace("_", " ")}
                            </td>
                            <td className="px-6 py-4">
                              <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium text-white ${flagTypeConfig.color}`}>
                                {flagTypeConfig.label}
                              </span>
                            </td>
                            <td className="px-6 py-4">
                              <div className="flex items-center gap-2">
                                <div className="w-16 h-2 bg-lsc-cream dark:bg-earth-700 rounded-full overflow-hidden">
                                  <div
                                    className={`h-full rounded-full ${
                                      flag.confidence_score >= 90 ? "bg-status-danger-500" :
                                      flag.confidence_score >= 70 ? "bg-status-warning-500" :
                                      "bg-status-success-500"
                                    }`}
                                    style={{ width: `${flag.confidence_score}%` }}
                                  />
                                </div>
                                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                                  {flag.confidence_score}%
                                </span>
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${statusConfig.bg} ${statusConfig.text}`}>
                                {statusConfig.icon}
                                {flag.status.replace("_", " ")}
                              </span>
                            </td>
                            <td className="px-6 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                              {new Date(flag.created_at).toLocaleDateString()}
                            </td>
                            <td className="px-6 py-4 text-right">
                              <button
                                onClick={() => handleViewDetails(flag.id)}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-xl transition-colors"
                              >
                                <Eye className="w-4 h-4" />
                                View
                              </button>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>

                <div className="md:hidden divide-y divide-lsc-border dark:divide-earth-700">
                  {flags.map((flag) => {
                    const statusConfig = getStatusConfig(flag.status)
                    const flagTypeConfig = getFlagTypeConfig(flag.flag_type)
                    return (
                      <div key={flag.id} className="p-4 space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">#{flag.id}</span>
                            <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium text-white ${flagTypeConfig.color}`}>
                              {flagTypeConfig.label}
                            </span>
                          </div>
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${statusConfig.bg} ${statusConfig.text}`}>
                            {statusConfig.icon}
                            {flag.status.replace("_", " ")}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">
                            {flag.review_type.replace("_", " ")}
                          </span>
                          <span className={`font-medium ${
                            flag.confidence_score >= 90 ? "text-status-danger-600 dark:text-status-danger-400" :
                            flag.confidence_score >= 70 ? "text-status-warning-600 dark:text-status-warning-400" :
                            "text-status-success-600 dark:text-status-success-400"
                          }`}>
                            {flag.confidence_score}% confidence
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                            {new Date(flag.created_at).toLocaleDateString()}
                          </span>
                          <button
                            onClick={() => handleViewDetails(flag.id)}
                            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-lsc-rose hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-xl transition-colors"
                          >
                            <Eye className="w-4 h-4" />
                            View
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>

                <div className="flex items-center justify-between p-4 border-t border-lsc-border dark:border-earth-700">
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    Showing {((currentPage - 1) * perPage) + 1} to {Math.min(currentPage * perPage, totalFlags)} of {totalFlags} flags
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                      aria-label={t('aria.staffContentFlags.previousPage', 'Previous page')}
                      className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronLeft className="w-5 h-5 text-lsc-dark dark:text-lsc-cream" />
                    </button>
                    <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                      Page {currentPage} of {totalPages}
                    </span>
                    <button
                      onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                      disabled={currentPage === totalPages}
                      aria-label={t('aria.staffContentFlags.nextPage', 'Next page')}
                      className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronRight className="w-5 h-5 text-lsc-dark dark:text-lsc-cream" />
                    </button>
                  </div>
                </div>
              </>
            )}
      </div>

      <FlagDetailModal
        flag={selectedFlag}
        onClose={() => setSelectedFlag(null)}
        onResolve={handleResolveFlag}
        onModerateReview={handleModerateReview}
        onEditReview={handleEditReview}
      />
    </AdminShell>
  )
}
