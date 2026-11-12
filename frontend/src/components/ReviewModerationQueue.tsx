/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, EyeOff, Star } from "lucide-react"
import toast from "react-hot-toast"
import { fetchApi } from "@/lib/api-client"
import { useAuth } from "@/contexts/AuthContext"
import { getAccessToken } from "@/utils/tokenStore"
import { hideEventReview } from "@/api/events-api"

interface QueueItem {
  id: number
  event_id: number
  event_title: string
  patron_email: string
  rating: number
  comment: string | null
  created_at: string
  moderation_status: string
}

interface QueueResponse {
  data: QueueItem[]
  pagination: { total: number }
}

const STAFF_ROLES = new Set(["super_admin", "admin", "director", "staff"])
const STATUS_OPTIONS = ["APPROVED", "PENDING", "REJECTED"] as const
type StatusFilter = (typeof STATUS_OPTIONS)[number]

export const ReviewModerationQueue: React.FC = () => {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("APPROVED")

  const isStaff = !!user && STAFF_ROLES.has(user.role)

  const { data, isLoading, isError } = useQuery({
    queryKey: ["event-review-moderation-queue", statusFilter],
    queryFn: () =>
      fetchApi<QueueResponse>(
        `/events/moderation/queue?status_filter=${statusFilter}&page=1&page_size=50`,
      ),
    enabled: isStaff,
  })

  const hideMutation = useMutation({
    mutationFn: (reviewId: number) => {
      const token = getAccessToken() || ""
      return hideEventReview(token, reviewId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["event-review-moderation-queue"] })
      toast.success("Review hidden.")
    },
    onError: () => {
      toast.error("Could not hide review.")
    },
  })

  if (!isStaff) {
    return (
      <div className="p-6 bg-lsc-white dark:bg-earth-800 rounded-lg shadow">
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          Staff access required.
        </p>
      </div>
    )
  }

  const reviews = data?.data ?? []

  return (
    <div className="p-6 bg-lsc-white dark:bg-earth-800 rounded-lg shadow">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Event Reviews
        </h2>
        <label className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          Status
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
            className="px-2 py-1 rounded border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
      </div>

      {isLoading && (
        <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
          <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
          Loading reviews...
        </div>
      )}

      {isError && (
        <p className="text-status-danger-600">Failed to load reviews.</p>
      )}

      {!isLoading && !isError && reviews.length === 0 && (
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          No reviews with status {statusFilter.toLowerCase()}.
        </p>
      )}

      <ul className="space-y-3">
        {reviews.map((review) => (
          <li
            key={review.id}
            className="p-4 border border-lsc-border dark:border-earth-700 rounded-lg"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                  {review.event_title}
                </p>
                <div className="flex items-center gap-1 my-1" aria-label={`Rating: ${review.rating} of 5`}>
                  {[1, 2, 3, 4, 5].map((s) => (
                    <Star
                      key={s}
                      aria-hidden="true"
                      className={`w-4 h-4 ${s <= review.rating ? "text-status-warning-400 fill-yellow-400" : "text-lsc-border dark:text-earth-300"}`}
                    />
                  ))}
                </div>
                {review.comment && (
                  <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mt-1">
                    {review.comment}
                  </p>
                )}
                <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-2">
                  {review.patron_email} - {new Date(review.created_at).toLocaleString()}
                </p>
              </div>
              {statusFilter !== "REJECTED" && (
                <button
                  type="button"
                  onClick={() => {
                    if (window.confirm("Hide this review from public display?")) {
                      hideMutation.mutate(review.id)
                    }
                  }}
                  disabled={hideMutation.isPending}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm rounded border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown disabled:opacity-50"
                  aria-label={`Hide review ${review.id}`}
                >
                  <EyeOff className="w-4 h-4" aria-hidden="true" />
                  Hide
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

interface Review {
  id: number
  event_id: number
  event_title: string
  patron_email: string
  rating: number
  comment: string | null
  created_at: string
  moderation_status: string
}

interface ModerationStats {
  by_status: Record<string, number>
  removed_count: number
  total: number
  pending: number
  approved: number
  rejected: number
}

export type { Review, ModerationStats }

export default ReviewModerationQueue
