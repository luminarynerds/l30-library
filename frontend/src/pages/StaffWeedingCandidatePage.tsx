/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Scissors, ExternalLink } from 'lucide-react'

import { getCandidate } from '@/api/weeding-api'
import { getAccessToken } from '@/utils/tokenStore'
import { AdminShell } from '../components/shells/AdminShell'
import { parseDate } from '@/utils/format-utils'
import { getCurrentLocale } from '@/i18n'

function fmtDate(d: string | null | undefined): string {
  const p = d ? parseDate(d) : null
  return p ? p.toLocaleDateString(getCurrentLocale(), { month: 'short', day: 'numeric', year: 'numeric' }) : '—'
}

function StatusBadge({ status }: { status: string | null | undefined }) {
  const base = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize'
  const s = (status || '').toLowerCase()
  const colors: Record<string, string> = {
    candidate: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    under_review: 'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-400',
    approved: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
    rejected: 'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300',
    disposed: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
  }
  return (
    <span className={`${base} ${colors[s] ?? 'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300'}`}>
      {s ? s.replace(/_/g, ' ') : '—'}
    </span>
  )
}

function Field({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-earth-600 dark:text-earth-400">{label}</dt>
      <dd className="mt-0.5 text-sm text-earth-900 dark:text-earth-100">{value === null || value === undefined || value === '' ? '—' : value}</dd>
    </div>
  )
}

export default function StaffWeedingCandidatePage() {
  const { id } = useParams<{ id: string }>()
  const candidateId = Number(id)
  const token = getAccessToken()
  const valid = Number.isFinite(candidateId) && candidateId > 0

  const q = useQuery({
    queryKey: ['weeding-candidate', candidateId],
    queryFn: () => getCandidate(token ?? '', candidateId),
    enabled: valid && !!token,
  })

  const c = q.data
  const errorMessage = !valid
    ? 'Invalid candidate id.'
    : q.isError
      ? (q.error instanceof Error ? q.error.message : 'Could not load this weeding candidate.')
      : null

  const flags: string[] = []
  if (c?.is_outdated_content) flags.push('Outdated content')
  if (c?.is_duplicate) flags.push(`Duplicate${c.duplicate_count ? ` (${c.duplicate_count})` : ''}`)
  if (c?.is_superseded) flags.push('Superseded edition')
  if (c?.never_circulated) flags.push('Never circulated')

  return (
    <AdminShell
      title={c?.item_title ?? 'Weeding candidate'}
      subtitle={c?.item_author ?? undefined}
      loading={valid && q.isLoading}
      error={errorMessage}
    >
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        <Link
          to="/staff/weeding"
          className="inline-flex items-center gap-1.5 text-sm text-earth-600 hover:text-earth-900 dark:text-earth-400 dark:hover:text-earth-100"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Weeding
        </Link>

        {c && (
          <>
            <section className="rounded-xl border border-earth-200 dark:border-earth-700 bg-white dark:bg-earth-900 p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Scissors className="h-5 w-5 text-earth-600" />
                  <h2 className="text-base font-semibold text-earth-900 dark:text-earth-100">Weeding recommendation</h2>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge status={c.status} />
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-300">
                    {(c.reason || '').replace(/_/g, ' ') || '—'}
                  </span>
                </div>
              </div>
              {c.reason_notes && (
                <p className="mt-3 text-sm text-earth-700 dark:text-earth-300">{c.reason_notes}</p>
              )}
              <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
                <Field label="Barcode" value={c.item_barcode ? <span className="font-mono">{c.item_barcode}</span> : null} />
                <Field label="Location" value={c.item_location} />
                <Field label="Item type" value={c.item_type} />
                <Field label="Condition" value={c.item_condition ? <span className="capitalize">{c.item_condition}</span> : null} />
                <Field label="Year" value={c.publication_year} />
                <Field label="ISBN" value={c.isbn} />
              </dl>
            </section>

            <section className="rounded-xl border border-earth-200 dark:border-earth-700 bg-white dark:bg-earth-900 p-5">
              <h2 className="text-base font-semibold text-earth-900 dark:text-earth-100">Why it was flagged</h2>
              <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
                <Field label="Last checkout" value={fmtDate(c.last_checkout_date)} />
                <Field label="Days since circ" value={c.days_since_last_circulation} />
                <Field label="Total checkouts" value={c.total_checkouts} />
                <Field label="Years held" value={c.years_since_acquisition} />
                <Field label="Condition score" value={c.condition_score} />
                <Field label="CREW" value={c.crew_category ? `${c.crew_category}${c.crew_score != null ? ` · ${c.crew_score}` : ''}` : null} />
              </dl>
              {flags.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {flags.map((f) => (
                    <span key={f} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400">
                      {f}
                    </span>
                  ))}
                </div>
              )}
              {c.outdated_flags && (
                <p className="mt-3 text-xs text-earth-600 dark:text-earth-400">{c.outdated_flags}</p>
              )}
            </section>

            {(c.disposition_recommendation || c.disposition_rationale) && (
              <section className="rounded-xl border border-earth-200 dark:border-earth-700 bg-white dark:bg-earth-900 p-5">
                <h2 className="text-base font-semibold text-earth-900 dark:text-earth-100">Disposition</h2>
                {c.disposition_recommendation && (
                  <p className="mt-2 text-sm capitalize text-earth-900 dark:text-earth-100">{c.disposition_recommendation.replace(/_/g, ' ')}</p>
                )}
                {c.disposition_rationale && (
                  <p className="mt-1 text-sm text-earth-600 dark:text-earth-300">{c.disposition_rationale}</p>
                )}
              </section>
            )}

            {c.item_copy_id ? (
              <Link
                to={`/staff/lifecycle/copy/${c.item_copy_id}`}
                className="inline-flex items-center gap-1.5 rounded-lg border border-earth-200 dark:border-earth-700 px-3 py-1.5 text-sm text-earth-700 dark:text-earth-200 hover:bg-earth-50 dark:hover:bg-earth-800"
              >
                <ExternalLink className="h-4 w-4" /> View copy
              </Link>
            ) : null}
          </>
        )}
      </div>
    </AdminShell>
  )
}
