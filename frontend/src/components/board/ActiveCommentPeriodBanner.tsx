/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { MessageSquare, Clock } from 'lucide-react'
import { getCurrentLocale } from '@/i18n'
import {
  getActiveCommentPeriods,
  type CommentPeriod,
} from '../../api/board-public-comments-api'

export default function ActiveCommentPeriodBanner() {
  const [periods, setPeriods] = useState<CommentPeriod[]>([])

  useEffect(() => {
    getActiveCommentPeriods()
      .then((data) => setPeriods(data))
      .catch(() => {
        // Silently fail - banner is non-critical
      })
  }, [])

  if (periods.length === 0) return null

  const formatDeadline = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(getCurrentLocale(), {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  }

  return (
    <div className="bg-lsc-rose/10 dark:bg-lsc-rose/15 border border-lsc-rose/30 dark:border-lsc-rose/40 rounded-xl p-4 mb-6">
      <div className="flex items-start gap-3">
        <MessageSquare className="h-5 w-5 text-lsc-rose flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <h2 className="font-serif font-semibold text-lsc-rose dark:text-lsc-rose-light">
            Public Comment Period Open
          </h2>
          <div className="mt-1 space-y-2">
            {periods.map((period) => (
              <div key={period.id} className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                <span className="font-medium">{period.title}</span>
                {period.description && (
                  <span className="ml-1">— {period.description}</span>
                )}
                <div className="flex items-center gap-1 mt-0.5 text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                  <Clock className="h-3 w-3" />
                  <span>Closes {formatDeadline(period.closes_at)}</span>
                </div>
              </div>
            ))}
          </div>
          <Link
            to="/board/public-comments"
            className="inline-block mt-3 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light hover:underline"
          >
            Submit Comment &rarr;
          </Link>
        </div>
      </div>
    </div>
  )
}
