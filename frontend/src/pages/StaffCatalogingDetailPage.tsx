/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, BookOpen, ExternalLink, Pencil } from 'lucide-react'

import { getCatalogItem } from '@/api/domains/catalog/catalog-api'
import { getInventoryCopies, type ItemCopy } from '@/api/domains/catalog/inventory-api'
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
    reference: 'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300',
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

export default function StaffCatalogingDetailPage() {
  const { id } = useParams<{ id: string }>()
  const itemId = Number(id)
  const valid = Number.isFinite(itemId) && itemId > 0

  const itemQ = useQuery({
    queryKey: ['cataloging-item', itemId],
    queryFn: () => getCatalogItem(itemId),
    enabled: valid,
  })
  const copiesQ = useQuery({
    queryKey: ['cataloging-item-copies', itemId],
    queryFn: () => getInventoryCopies({ catalog_item_id: itemId, per_page: 100 }),
    enabled: valid,
  })

  const item = itemQ.data
  const copies: ItemCopy[] = copiesQ.data?.items ?? []
  const errorMessage = !valid
    ? 'Invalid item id.'
    : itemQ.isError
      ? (itemQ.error instanceof Error ? itemQ.error.message : 'Could not load this item.')
      : null

  return (
    <AdminShell
      title={item?.title ?? 'Catalog item'}
      subtitle={item?.author ? `by ${item.author}` : undefined}
      loading={valid && itemQ.isLoading}
      error={errorMessage}
    >
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        <Link
          to="/staff/cataloging"
          className="inline-flex items-center gap-1.5 text-sm text-earth-600 hover:text-earth-900 dark:text-earth-400 dark:hover:text-earth-100"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Cataloging
        </Link>

        {item && (
          <>
            <section className="rounded-xl border border-earth-200 dark:border-earth-700 bg-white dark:bg-earth-900 p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-2">
                  <BookOpen className="h-5 w-5 text-earth-600" />
                  <h2 className="text-base font-semibold text-earth-900 dark:text-earth-100">Bibliographic record</h2>
                </div>
                <StatusBadge status={item.status} />
              </div>
              <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
                <Field label="Author" value={item.author} />
                <Field label="ISBN" value={item.isbn} />
                <Field label="Publisher" value={item.publisher} />
                <Field label="Year" value={item.publication_year} />
                <Field label="Call number" value={item.call_number} />
                <Field label="Dewey" value={item.dewey_decimal} />
                <Field label="Item type" value={item.item_type} />
                <Field
                  label="Series"
                  value={item.series_name ? `${item.series_name}${item.series_number ? ` #${item.series_number}` : ''}` : null}
                />
                <Field label="Total checkouts" value={item.total_checkouts} />
              </dl>
              {item.subjects && (
                <div className="mt-4">
                  <dt className="text-xs font-medium uppercase tracking-wide text-earth-600 dark:text-earth-400">Subjects</dt>
                  <dd className="mt-0.5 text-sm text-earth-900 dark:text-earth-100">{item.subjects}</dd>
                </div>
              )}
              {item.description && (
                <div className="mt-4">
                  <dt className="text-xs font-medium uppercase tracking-wide text-earth-600 dark:text-earth-400">Description</dt>
                  <dd className="mt-0.5 text-sm leading-relaxed text-earth-700 dark:text-earth-300">{item.description}</dd>
                </div>
              )}
            </section>

            <section className="rounded-xl border border-earth-200 dark:border-earth-700 bg-white dark:bg-earth-900 p-5">
              <h2 className="text-base font-semibold text-earth-900 dark:text-earth-100">
                Copies <span className="text-earth-600 font-normal">({copies.length})</span>
              </h2>
              {copiesQ.isLoading ? (
                <p className="mt-3 text-sm text-earth-600">Loading copies…</p>
              ) : copies.length === 0 ? (
                <p className="mt-3 text-sm text-earth-600">No copies recorded for this title.</p>
              ) : (
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs uppercase tracking-wide text-earth-600 dark:text-earth-400 border-b border-earth-200 dark:border-earth-700">
                        <th className="py-2 pr-4 font-medium">Barcode</th>
                        <th className="py-2 pr-4 font-medium">Location</th>
                        <th className="py-2 pr-4 font-medium">Condition</th>
                        <th className="py-2 pr-4 font-medium">Acquired</th>
                        <th className="py-2 font-medium" />
                      </tr>
                    </thead>
                    <tbody>
                      {copies.map((c) => (
                        <tr key={c.id} className="border-b border-earth-100 dark:border-earth-800 last:border-0">
                          <td className="py-2 pr-4 font-mono text-earth-900 dark:text-earth-100">{c.barcode}</td>
                          <td className="py-2 pr-4 text-earth-700 dark:text-earth-300">{c.location || '—'}</td>
                          <td className="py-2 pr-4 text-earth-700 dark:text-earth-300 capitalize">{c.condition || '—'}</td>
                          <td className="py-2 pr-4 text-earth-700 dark:text-earth-300">{fmtDate(c.acquisition_date)}</td>
                          <td className="py-2">
                            <Link to={`/staff/lifecycle/copy/${c.id}`} className="text-status-info-600 hover:underline dark:text-status-info-400">
                              History
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <div className="flex flex-wrap gap-3">
              <Link
                to={`/catalog/${item.id}`}
                className="inline-flex items-center gap-1.5 rounded-lg border border-earth-200 dark:border-earth-700 px-3 py-1.5 text-sm text-earth-700 dark:text-earth-200 hover:bg-earth-50 dark:hover:bg-earth-800"
              >
                <ExternalLink className="h-4 w-4" /> View public page
              </Link>
              <Link
                to={`/staff/cataloging?q=${encodeURIComponent(item.title)}`}
                className="inline-flex items-center gap-1.5 rounded-lg border border-earth-200 dark:border-earth-700 px-3 py-1.5 text-sm text-earth-700 dark:text-earth-200 hover:bg-earth-50 dark:hover:bg-earth-800"
              >
                <Pencil className="h-4 w-4" /> Open in Cataloging
              </Link>
            </div>
          </>
        )}
      </div>
    </AdminShell>
  )
}
