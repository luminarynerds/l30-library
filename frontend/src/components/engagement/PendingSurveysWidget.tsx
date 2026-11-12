/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ClipboardList } from 'lucide-react'
import {
  listMyPendingSurveys,
  type PendingSurvey,
} from '@/api/domains/engagement'

interface Props {
  courseId?: number
  // limit how many to show in compact dashboard placements
  max?: number
}

export function PendingSurveysWidget({ courseId, max }: Props) {
  const [items, setItems] = useState<PendingSurvey[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    listMyPendingSurveys(courseId)
      .then((data) => {
        if (!cancelled) {
          setItems(data)
          setLoading(false)
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Failed to load surveys')
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [courseId])

  if (loading || error) return null
  if (items.length === 0) return null

  const visible = max ? items.slice(0, max) : items

  return (
    <section className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow border border-lsc-border dark:border-earth-700 p-5">
      <header className="flex items-center gap-2 mb-3">
        <ClipboardList className="w-5 h-5 text-lsc-rose" />
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Quick check-ins
        </h2>
      </header>
      <ul className="space-y-2">
        {visible.map((s) => (
          <li
            key={s.survey_id}
            className="flex items-start justify-between gap-3 p-3 rounded-lg bg-lsc-cream dark:bg-earth-900 border border-lsc-border dark:border-earth-700"
          >
            <div className="min-w-0">
              <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate">
                {s.title}
              </p>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                {s.estimated_minutes
                  ? `${s.estimated_minutes} min`
                  : 'Quick'}
                {s.placement === 'longitudinal' ? ' · Follow-up' : ''}
              </p>
              {s.consent_copy && (
                <p className="mt-1 text-xs text-lsc-dark/60 dark:text-lsc-cream/60 italic">
                  {s.consent_copy}
                </p>
              )}
            </div>
            <Link
              to={surveyLink(s)}
              className="shrink-0 px-3 py-1.5 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 text-lsc-white text-sm font-medium"
            >
              Start
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}

function surveyLink(s: PendingSurvey): string {
  // Magic-link path takes precedence: token is bound to the response row.
  if (s.delivery_token) return `/survey/respond/${s.delivery_token}`
  return `/learn/surveys/${s.survey_id}`
}
