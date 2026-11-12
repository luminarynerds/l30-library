/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
import { Star, Calendar, Leaf, BookOpen } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import type { ReviewType, ModerationStatus } from '@/api/review-response-api'

export const REVIEW_TYPE_LABELS: Record<ReviewType, string> = {
  'event': 'Event Reviews',
  'strain': 'Strain Reviews',
  'indie-ebook': 'Indie Ebook Reviews',
}

export const REVIEW_TYPE_ICONS: Record<ReviewType, React.ReactNode> = {
  'event': <Calendar className="w-4 h-4" />,
  'strain': <Leaf className="w-4 h-4" />,
  'indie-ebook': <BookOpen className="w-4 h-4" />,
}

export const STATUS_COLORS: Record<ModerationStatus, string> = {
  'pending': 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300',
  'approved': 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300',
  'rejected': 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300',
}

export function StarRating({ rating }: { rating: number }): React.ReactElement {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          className={clsx(
            'w-3.5 h-3.5',
            star <= rating
              ? 'fill-status-warning-400 text-status-warning-400'
              : 'text-lsc-dark/20 dark:text-lsc-cream/20'
          )}
        />
      ))}
    </div>
  )
}
