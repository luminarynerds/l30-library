/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Barcode, History } from 'lucide-react'

import { getInventoryCopy, getCopyConditionHistory } from '@/api/domains/catalog/inventory-api'
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
    available: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
    checked_out: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    on_hold: 'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-400',
    in_transit: 'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-400',
    in_repair: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    lost: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    withdrawn: 'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300',
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

export default function StaffCopyLifecyclePage() {
  const { copyId } = useParams<{ copyId: string }>()
  const id = Number(copyId)
  const valid = Number.isFinite(id) && id > 0

  const copyQ = useQuery({
    queryKey: ['copy-lifecycle', id],
    queryFn: () => getInventoryCopy(id),
    enabled: valid,
  })
  const historyQ = useQuery({
    queryKey: ['copy-condition-history', id],
    queryFn: () => getCopyConditionHistory(id),
    enabled: valid,
  })

  const copy = copyQ.data
  const history = historyQ.data ?? []
  const errorMessage = !valid
    ? 'Invalid copy id.'
    : copyQ.isError
      ? (copyQ.error instanceof Error ? copyQ.error.message : 'Could not load this copy.')
      : null

  const title = copy?.catalog_title ?? copy?.catalog_item?.title ?? copy?.barcode ?? 'Copy'
  const author = copy?.catalog_author ?? copy?.catalog_item?.author ?? null

  return (
    <AdminShell
      title={copy ? `Copy ${copy.barcode}` : 'Copy'}
      subtitle={author ? `${title} — ${author}` : title}
      loading={valid && copyQ.isLoading}
      error={errorMessage}
    >
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        <Link
          to="/staff/lifecycle"
          className="inline-flex items-center gap-1.5 text-sm text-earth-600 hover:text-earth-900 dark:text-earth-400 dark:hover:text-earth-100"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Lifecycle
        </Link>

        {copy && (
          <>
            <section className="rounded-xl border border-earth-200 dark:border-earth-700 bg-white dark:bg-earth-900 p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-2">
                  <Barcode className="h-5 w-5 text-earth-600" />
                  <h2 className="font-mono text-base font-semibold text-earth-900 dark:text-earth-100">{copy.barcode}</h2>
                </div>
                <StatusBadge status={copy.status} />
              </div>
              <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
                <Field
                  label="Title"
                  value={
                    copy.catalog_item_id ? (
                      <Link to={`/staff/cataloging/${copy.catalog_item_id}`} className="text-status-info-600 hover:underline dark:text-status-info-400">
                        {title}
                      </Link>
                    ) : title
                  }
                />
                <Field label="Author" value={author} />
                <Field label="Call number" value={copy.call_number} />
                <Field label="Location" value={copy.location} />
                <Field label="Condition" value={<span className="capitalize">{copy.condition}</span>} />
                <Field label="Acquired" value={fmtDate(copy.acquisition_date)} />
                <Field label="Replacement cost" value={copy.replacement_cost != null ? `$${Number(copy.replacement_cost).toFixed(2)}` : null} />
              </dl>
              {copy.notes && (
                <div className="mt-4">
                  <dt className="text-xs font-medium uppercase tracking-wide text-earth-600 dark:text-earth-400">Notes</dt>
                  <dd className="mt-0.5 text-sm text-earth-700 dark:text-earth-300">{copy.notes}</dd>
                </div>
              )}
            </section>

            <section className="rounded-xl border border-earth-200 dark:border-earth-700 bg-white dark:bg-earth-900 p-5">
              <div className="flex items-center gap-2">
                <History className="h-5 w-5 text-earth-600" />
                <h2 className="text-base font-semibold text-earth-900 dark:text-earth-100">
                  Condition history <span className="text-earth-600 font-normal">({history.length})</span>
                </h2>
              </div>
              {historyQ.isLoading ? (
                <p className="mt-3 text-sm text-earth-600">Loading history…</p>
              ) : history.length === 0 ? (
                <p className="mt-3 text-sm text-earth-600">No condition changes recorded.</p>
              ) : (
                <ul className="mt-4 space-y-3">
                  {history.map((h) => (
                    <li key={h.id} className="flex items-start gap-3 text-sm">
                      <span className="mt-1.5 h-1.5 w-1.5 flex-none rounded-full bg-earth-300 dark:bg-earth-600" />
                      <div>
                        <p className="text-earth-900 dark:text-earth-100">
                          <span className="capitalize">{h.old_condition}</span> → <span className="capitalize font-medium">{h.new_condition}</span>
                        </p>
                        <p className="text-xs text-earth-600 dark:text-earth-400">
                          {fmtDate(h.changed_at)}{h.changed_by_name ? ` · ${h.changed_by_name}` : ''}
                        </p>
                        {h.notes && <p className="mt-0.5 text-earth-600 dark:text-earth-300">{h.notes}</p>}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </div>
    </AdminShell>
  )
}
