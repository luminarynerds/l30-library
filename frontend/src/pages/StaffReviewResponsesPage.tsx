/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  MessageSquare,
  CheckCircle,
  AlertCircle,
  Clock,
  Filter,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Send,
  Calendar,
  Leaf,
  BookOpen,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '@/contexts/AuthContext'
import {
  reviewResponseStaffAPI,
  eventReviewResponseAPI,
  strainReviewResponseAPI,
  indieEbookReviewResponseAPI,
  type ReviewType,
  type PendingResponseItem,
  type PendingReviewItem,
  type CreateReviewResponseRequest,
} from '@/api/review-response-api'
import { clsx } from '@/utils/helpers'
import { useTranslation} from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import { REVIEW_TYPE_LABELS } from '../components/review-responses/ReviewResponsesShared'
import { PendingResponseCard } from '../components/review-responses/PendingResponseCard'
import { ReviewNeedingResponseCard } from '../components/review-responses/ReviewNeedingResponseCard'
import { ComposeResponseModal } from '../components/review-responses/ComposeResponseModal'
import { RejectionModal } from '../components/review-responses/RejectionModal'
import { ResponseDetailModal } from '../components/review-responses/ResponseDetailModal'
import PageContainer from '@/components/layout/PageContainer'

function StatsCard({ icon, label, value, subtext, color }: {
  icon: React.ReactNode
  label: string
  value: number | string
  subtext?: string
  color?: string
}): React.ReactElement {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
      <div className="flex items-center gap-2 mb-2">
        <span className={color || 'text-lsc-rose'}>{icon}</span>
        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{label}</span>
      </div>
      <div className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
        {value}
      </div>
      {subtext && (
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{subtext}</p>
      )}
    </div>
  )
}

export default function StaffReviewResponsesPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user } = useAuth()
  const queryClient = useQueryClient()

  const [activeTab, setActiveTab] = useState<'pending' | 'needing-response'>('pending')
  const [typeFilter, setTypeFilter] = useState<ReviewType | ''>('')
  const [page, setPage] = useState(1)
  const [selectedResponses, setSelectedResponses] = useState<number[]>([])
  const [showRejectionModal, setShowRejectionModal] = useState(false)
  const [composeReview, setComposeReview] = useState<PendingReviewItem | null>(null)
  const [viewResponse, setViewResponse] = useState<PendingResponseItem | null>(null)
  const [respondingTo, setRespondingTo] = useState<{ id: number; type: ReviewType } | null>(null)

  const perPage = 20

  const isStaff = user?.role === 'staff' || user?.role === 'admin' || user?.role === 'super_admin'

  const { data: stats } = useQuery({
    queryKey: ['review-response-stats'],
    queryFn: () => reviewResponseStaffAPI.getStats(),
    enabled: isStaff,
  })

  const { data: pendingData, isLoading: pendingLoading } = useQuery({
    queryKey: ['pending-responses', page],
    queryFn: () => reviewResponseStaffAPI.getPendingResponses(page, perPage),
    enabled: isStaff && activeTab === 'pending',
  })

  const { data: needingResponseData, isLoading: needingResponseLoading } = useQuery({
    queryKey: ['reviews-needing-response', typeFilter, page],
    queryFn: () => reviewResponseStaffAPI.getReviewsNeedingResponse(
      typeFilter || undefined,
      page,
      perPage
    ),
    enabled: isStaff && activeTab === 'needing-response',
  })

  const approveMutation = useMutation({
    mutationFn: async ({ responseId, reviewType }: { responseId: number; reviewType: ReviewType }) => {
      switch (reviewType) {
        case 'event':
          return eventReviewResponseAPI.approve(responseId, { approved: true })
        case 'strain':
          return strainReviewResponseAPI.approve(responseId, { approved: true })
        case 'indie-ebook':
          return indieEbookReviewResponseAPI.approve(responseId, { approved: true })
      }
    },
    onSuccess: () => {
      toast.success(t('toast.staffReviewResponses.responseApproved'))
      queryClient.invalidateQueries({ queryKey: ['pending-responses'] })
      queryClient.invalidateQueries({ queryKey: ['review-response-stats'] })
      setViewResponse(null)
    },
    onError: () => {
      toast.error(t('staffReviewResponses.failedToApproveResponse'))
    },
  })

  const rejectMutation = useMutation({
    mutationFn: async ({ responseId, reviewType, reason }: { responseId: number; reviewType: ReviewType; reason: string }) => {
      switch (reviewType) {
        case 'event':
          return eventReviewResponseAPI.approve(responseId, { approved: false, reason })
        case 'strain':
          return strainReviewResponseAPI.approve(responseId, { approved: false, reason })
        case 'indie-ebook':
          return indieEbookReviewResponseAPI.approve(responseId, { approved: false, reason })
      }
    },
    onSuccess: () => {
      toast.success(t('toast.staffReviewResponses.responseRejected'))
      queryClient.invalidateQueries({ queryKey: ['pending-responses'] })
      queryClient.invalidateQueries({ queryKey: ['review-response-stats'] })
      setShowRejectionModal(false)
      setSelectedResponses([])
      setViewResponse(null)
    },
    onError: () => {
      toast.error(t('staffReviewResponses.failedToRejectResponse'))
    },
  })

  const createResponseMutation = useMutation({
    mutationFn: async ({ reviewId, reviewType, content }: { reviewId: number; reviewType: ReviewType; content: string }) => {
      const data: CreateReviewResponseRequest = { content }
      switch (reviewType) {
        case 'event':
          return eventReviewResponseAPI.create(reviewId, data)
        case 'strain':
          return strainReviewResponseAPI.create(reviewId, data)
        case 'indie-ebook':
          return indieEbookReviewResponseAPI.create(reviewId, data)
      }
    },
    onSuccess: () => {
      toast.success(t('toast.staffReviewResponses.responseSubmittedSuccessfully'))
      queryClient.invalidateQueries({ queryKey: ['reviews-needing-response'] })
      queryClient.invalidateQueries({ queryKey: ['review-response-stats'] })
      setComposeReview(null)
    },
    onError: () => {
      toast.error(t('staffReviewResponses.failedToSubmitResponse'))
    },
  })

  const handleApprove = useCallback((response: PendingResponseItem) => {
    approveMutation.mutate({ responseId: response.id, reviewType: response.review_type })
  }, [approveMutation])

  const handleBatchReject = useCallback((reason: string) => {
    if (selectedResponses.length === 0 || !pendingData) return
    const firstResponse = pendingData.items.find((r: { id: number }) => selectedResponses.includes(r.id))
    if (firstResponse) {
      selectedResponses.forEach((id) => {
        const response = pendingData.items.find((r: { id: number }) => r.id === id)
        if (response) {
          rejectMutation.mutate({ responseId: id, reviewType: response.review_type, reason })
        }
      })
    }
  }, [selectedResponses, pendingData, rejectMutation])

  const handleComposeSubmit = useCallback((content: string) => {
    if (!composeReview) return
    createResponseMutation.mutate({
      reviewId: composeReview.review_id,
      reviewType: composeReview.review_type,
      content,
    })
  }, [composeReview, createResponseMutation])

  const toggleResponseSelection = useCallback((id: number, selected: boolean) => {
    if (selected) {
      setSelectedResponses(prev => [...prev, id])
    } else {
      setSelectedResponses(prev => prev.filter(r => r !== id))
    }
  }, [])

  if (!user) {
    return (
      <div className="max-w-lg mx-auto text-center py-12">
        <AlertCircle className="w-16 h-16 mx-auto mb-4 text-status-warning-500" />
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          Sign In Required
        </h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          Please sign in to access this page.
        </p>
        <Link to="/login" className="inline-block px-6 py-3 bg-lsc-rose text-white rounded-lg">
          Sign In
        </Link>
      </div>
    )
  }

  if (!isStaff) {
    return (
      <div className="max-w-lg mx-auto text-center py-12">
        <AlertCircle className="w-16 h-16 mx-auto mb-4 text-status-danger-500" />
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          Staff Only
        </h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          This page is only accessible to library staff.
        </p>
        <Link to="/" className="inline-block px-6 py-3 bg-lsc-rose text-white rounded-lg">
          Go Home
        </Link>
      </div>
    )
  }

  return (
    <AdminShell title="Review Responses">    <PageContainer width="wide" className="py-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
            <MessageSquare className="w-8 h-8 text-lsc-rose" />
            Review Responses
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            Manage and moderate author/staff responses to reviews
          </p>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatsCard
            icon={<Clock className="w-5 h-5" />}
            label="Pending Moderation"
            value={stats.pending_moderation}
            color="text-status-warning-500"
          />
          <StatsCard
            icon={<MessageSquare className="w-5 h-5" />}
            label="Total Responses"
            value={stats.total_responses}
          />
          <StatsCard
            icon={<Calendar className="w-5 h-5" />}
            label="Event Responses"
            value={stats.responses_by_type.event}
            color="text-earth-600"
          />
          <StatsCard
            icon={<Leaf className="w-5 h-5" />}
            label="Strain Responses"
            value={stats.responses_by_type.strain}
            color="text-status-success-500"
          />
          <StatsCard
            icon={<BookOpen className="w-5 h-5" />}
            label="Indie Ebook Responses"
            value={stats.responses_by_type['indie-ebook']}
            color="text-category-500"
          />
        </div>
      )}

      <div className="flex gap-2 border-b border-lsc-border dark:border-earth-700">
        <button
          onClick={() => { setActiveTab('pending'); setPage(1); setSelectedResponses([]); }}
          className={clsx(
            'px-4 py-2 font-medium transition-colors relative',
            activeTab === 'pending'
              ? 'text-lsc-rose'
              : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
          )}
        >
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Pending Moderation
            {stats && stats.pending_moderation > 0 && (
              <span className="px-2 py-0.5 bg-status-warning-500 text-white text-xs rounded-full">
                {stats.pending_moderation}
              </span>
            )}
          </div>
          {activeTab === 'pending' && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-lsc-rose" />
          )}
        </button>
        <button
          onClick={() => { setActiveTab('needing-response'); setPage(1); }}
          className={clsx(
            'px-4 py-2 font-medium transition-colors relative',
            activeTab === 'needing-response'
              ? 'text-lsc-rose'
              : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
          )}
        >
          <div className="flex items-center gap-2">
            <Send className="w-4 h-4" />
            Reviews Needing Response
          </div>
          {activeTab === 'needing-response' && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-lsc-rose" />
          )}
        </button>
      </div>

      {activeTab === 'pending' && (
        <>
          {selectedResponses.length > 0 && (
            <div className="bg-lsc-cream dark:bg-earth-800 rounded-xl p-4 flex items-center justify-between">
              <span className="text-lsc-dark dark:text-lsc-cream font-medium">
                {selectedResponses.length} response{selectedResponses.length !== 1 ? 's' : ''} selected
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSelectedResponses([])}
                  className="px-3 py-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-white dark:hover:bg-earth-700 rounded-lg"
                >
                  Clear
                </button>
                <button
                  onClick={() => setShowRejectionModal(true)}
                  className="px-3 py-1.5 text-sm text-status-danger-600 dark:text-status-danger-400 border border-status-danger-300 dark:border-status-danger-800 rounded-lg hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/20"
                >
                  Reject Selected
                </button>
                <button
                  onClick={() => {
                    selectedResponses.forEach(id => {
                      const response = pendingData?.items.find((r: { id: number }) => r.id === id)
                      if (response) {
                        approveMutation.mutate({ responseId: id, reviewType: response.review_type })
                      }
                    })
                    setSelectedResponses([])
                  }}
                  className="px-3 py-1.5 text-sm bg-status-success-600 text-white rounded-lg hover:bg-status-success-700"
                >
                  Approve Selected
                </button>
              </div>
            </div>
          )}

          {pendingLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
            </div>
          ) : pendingData && pendingData.items.length > 0 ? (
            <div className="space-y-4">
              {pendingData.items.map((response) => (
                <PendingResponseCard
                  key={response.id}
                  response={response}
                  onApprove={() => handleApprove(response)}
                  onReject={() => {
                    setRespondingTo({ id: response.id, type: response.review_type })
                    setShowRejectionModal(true)
                  }}
                  onView={() => setViewResponse(response)}
                  isSelected={selectedResponses.includes(response.id)}
                  onSelect={(selected) => toggleResponseSelection(response.id, selected)}
                />
              ))}

              {pendingData.pages > 1 && (
                <div className="flex items-center justify-between pt-4">
                  <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    Page {page} of {pendingData.pages} ({pendingData.total} total)
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-50"
                    >
                      <ChevronLeft className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => setPage(p => Math.min(pendingData.pages, p + 1))}
                      disabled={page >= pendingData.pages}
                      className="p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-50"
                    >
                      <ChevronRight className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12 bg-lsc-cream dark:bg-earth-800 rounded-xl">
              <CheckCircle className="w-16 h-16 mx-auto mb-4 text-status-success-500/50" />
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                All caught up!
              </h3>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                No responses waiting for moderation.
              </p>
            </div>
          )}
        </>
      )}

      {activeTab === 'needing-response' && (
        <>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2">
                <Filter className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Filter by type:</span>
              </div>
              <select
                value={typeFilter}
                onChange={(e) => {
                  setTypeFilter(e.target.value as ReviewType | '')
                  setPage(1)
                }}
                className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              >
                <option value="">All Types</option>
                <option value="event">Event Reviews</option>
                <option value="strain">Strain Reviews</option>
                <option value="indie-ebook">Indie Ebook Reviews</option>
              </select>
            </div>
          </div>

          {needingResponseLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
            </div>
          ) : needingResponseData && needingResponseData.items.length > 0 ? (
            <div className="space-y-4">
              {needingResponseData.items.map((review) => (
                <ReviewNeedingResponseCard
                  key={`${review.review_type}-${review.review_id}`}
                  review={review}
                  onCompose={() => setComposeReview(review)}
                />
              ))}

              {needingResponseData.pages > 1 && (
                <div className="flex items-center justify-between pt-4">
                  <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    Page {page} of {needingResponseData.pages} ({needingResponseData.total} total)
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-50"
                    >
                      <ChevronLeft className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => setPage(p => Math.min(needingResponseData.pages, p + 1))}
                      disabled={page >= needingResponseData.pages}
                      className="p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-50"
                    >
                      <ChevronRight className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12 bg-lsc-cream dark:bg-earth-800 rounded-xl">
              <CheckCircle className="w-16 h-16 mx-auto mb-4 text-status-success-500/50" />
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                All caught up!
              </h3>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                {typeFilter
                  ? `No ${REVIEW_TYPE_LABELS[typeFilter].toLowerCase()} need a staff response.`
                  : 'No reviews need a staff response right now.'}
              </p>
            </div>
          )}
        </>
      )}

      {composeReview && (
        <ComposeResponseModal
          review={composeReview}
          onClose={() => setComposeReview(null)}
          onSubmit={handleComposeSubmit}
          isSubmitting={createResponseMutation.isPending}
        />
      )}

      {showRejectionModal && (
        <RejectionModal
          onClose={() => {
            setShowRejectionModal(false)
            setRespondingTo(null)
          }}
          onSubmit={(reason) => {
            if (respondingTo) {
              rejectMutation.mutate({
                responseId: respondingTo.id,
                reviewType: respondingTo.type,
                reason
              })
            } else if (selectedResponses.length > 0) {
              handleBatchReject(reason)
            }
          }}
          isSubmitting={rejectMutation.isPending}
          count={respondingTo ? 1 : selectedResponses.length}
        />
      )}

      {viewResponse && (
        <ResponseDetailModal
          response={viewResponse}
          onClose={() => setViewResponse(null)}
          onApprove={() => handleApprove(viewResponse)}
          onReject={() => {
            setRespondingTo({ id: viewResponse.id, type: viewResponse.review_type })
            setShowRejectionModal(true)
          }}
          onEdit={() => {
            toast.error(t('staffReviewResponses.editFunctionalityNotYetImplemented'))
          }}
          onDelete={() => {
            toast.error(t('staffReviewResponses.deleteFunctionalityNotYetImplemented'))
          }}
          isProcessing={approveMutation.isPending}
        />
      )}
    </PageContainer>
  </AdminShell>
  )
}
