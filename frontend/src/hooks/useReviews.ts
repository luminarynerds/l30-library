/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useAuth } from '@/contexts/AuthContext'
import { useUnifiedAccessibility } from '@/features/accessibility/hooks/useUnifiedAccessibility'
import {
  getCatalogItemReviews,
  upsertReview,
  deleteReview,
} from '@/api/domains/content/reviews-api'

export function useReviews(catalogItemId?: number) {
  const { token } = useAuth()
  const { announceToScreenReader } = useUnifiedAccessibility()
  const queryClient = useQueryClient()
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { data: reviewData, isError: reviewsLoadError } = useQuery({
    queryKey: ['catalog-reviews', catalogItemId, token],
    queryFn: () => getCatalogItemReviews(catalogItemId!, token || undefined),
    enabled: !!catalogItemId,
    retry: 1,
  })

  const handleRate = async (rating: number) => {
    if (!token || !catalogItemId) return
    setIsSubmitting(true)
    try {
      await upsertReview(token, catalogItemId, { rating })
      toast.success(`Rated ${rating} star${rating !== 1 ? 's' : ''}`)
      announceToScreenReader(`Rated ${rating} star${rating !== 1 ? 's' : ''}`)
      queryClient.invalidateQueries({ queryKey: ['catalog-reviews', catalogItemId] })
    } catch {
      toast.error('Failed to submit rating')
      announceToScreenReader('Failed to submit rating')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDeleteRating = async () => {
    if (!token || !catalogItemId) return
    setIsSubmitting(true)
    try {
      await deleteReview(token, catalogItemId)
      toast.success('Rating removed')
      announceToScreenReader('Rating removed')
      queryClient.invalidateQueries({ queryKey: ['catalog-reviews', catalogItemId] })
    } catch {
      toast.error('Failed to remove rating')
    } finally {
      setIsSubmitting(false)
    }
  }

  return {
    aggregate: reviewData?.aggregate ?? { average_rating: null, rating_count: 0 },
    staffReviews: reviewData?.staff_reviews ?? [],
    userRating: reviewData?.user_rating ?? null,
    isSubmitting,
    reviewsLoadError,
    handleRate,
    handleDeleteRating,
  }
}
