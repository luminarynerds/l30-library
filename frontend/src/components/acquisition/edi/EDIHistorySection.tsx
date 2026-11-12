/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Inline (non-modal) EDI history block for the PO edit/detail modal.
 * Fetches its own transactions + shipment notices for the given PO and
 * renders the same list component used by the badge drawer.
 *
 * Silently renders nothing when the PO has no EDI activity at all
 * (manual vendor) — keeps the edit modal uncluttered.
 */
import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { useTranslation } from '@/i18n'
import {
  getEDITransactions,
  getShipmentNotices,
  type EDITransaction,
  type EDIShipmentNotice,
} from '@/api/domains/admin/edi-api'
import EDITransactionsList from './EDITransactionsList'

interface EDIHistorySectionProps {
  poId: number
}

export default function EDIHistorySection({ poId }: EDIHistorySectionProps) {
  const { t } = useTranslation()
  const [transactions, setTransactions] = useState<EDITransaction[] | null>(null)
  const [notices, setNotices] = useState<EDIShipmentNotice[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot fetch trigger
    setLoading(true)
    setError(null)

    Promise.all([
      getEDITransactions({ purchase_order_id: poId, per_page: 100 }),
      getShipmentNotices({ purchase_order_id: poId, per_page: 50 }),
    ])
      .then(([txRes, noticesRes]) => {
        if (cancelled) return
        setTransactions(txRes.items)
        setNotices(noticesRes.items)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : String(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [poId])

  // Manual-vendor case: no EDI activity, hide the whole section.
  if (!loading && !error && transactions !== null && transactions.length === 0) {
    return null
  }

  return (
    <section aria-labelledby={`edi-history-section-${poId}`}>
      <h3
        id={`edi-history-section-${poId}`}
        className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4"
      >
        {t('acquisitionsEdi.sectionHeading', 'EDI History')}
      </h3>
      {loading && (
        <p className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <Loader2 aria-hidden="true" className="w-4 h-4 motion-safe:animate-spin" />
          {t('acquisitionsEdi.loadingHistory', 'Loading EDI history…')}
        </p>
      )}
      {error && (
        <p
          role="alert"
          className="text-sm text-status-danger-700 dark:text-status-danger-300"
        >
          {t('acquisitionsEdi.historyLoadFailed', {
            error,
            defaultValue: `Failed to load EDI history: ${error}`,
          })}
        </p>
      )}
      {!loading && !error && transactions !== null && transactions.length > 0 && (
        <EDITransactionsList transactions={transactions} shipmentNotices={notices} />
      )}
    </section>
  )
}
