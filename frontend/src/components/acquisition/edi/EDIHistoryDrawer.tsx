/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Contents rendered inside the badge's Modal. Receives the transactions
 * already fetched at the page level and lazy-fetches shipment notices
 * (DESADV metadata) when first opened.
 */
import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { useTranslation } from '@/i18n'
import {
  getShipmentNotices,
  type EDITransaction,
  type EDIShipmentNotice,
} from '@/api/domains/admin/edi-api'
import EDITransactionsList from './EDITransactionsList'

interface EDIHistoryDrawerProps {
  poId: number
  initialTransactions: EDITransaction[]
  /** id used by the parent Modal title (kept for downstream a11y wiring) */
  titleId?: string
}

export default function EDIHistoryDrawer({
  poId,
  initialTransactions,
}: EDIHistoryDrawerProps) {
  const { t } = useTranslation()
  const hasDesadv = initialTransactions.some(
    (tx) => tx.message_type === 'desadv' && tx.direction === 'inbound',
  )

  const [notices, setNotices] = useState<EDIShipmentNotice[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!hasDesadv) return
    let cancelled = false
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot fetch trigger
    setLoading(true)
    setError(null)
    getShipmentNotices({ purchase_order_id: poId, per_page: 50 })
      .then((res) => {
        if (cancelled) return
        setNotices(res.items)
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
  }, [poId, hasDesadv])

  return (
    <div className="space-y-4">
      {loading && (
        <p className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <Loader2 aria-hidden="true" className="w-4 h-4 motion-safe:animate-spin" />
          {t('acquisitionsEdi.loadingShipment', 'Loading shipment notice…')}
        </p>
      )}
      {error && (
        <p
          role="alert"
          className="text-sm text-status-danger-700 dark:text-status-danger-300"
        >
          {t('acquisitionsEdi.shipmentLoadFailed', {
            error,
            defaultValue: `Failed to load shipment notice: ${error}`,
          })}
        </p>
      )}
      <EDITransactionsList
        transactions={initialTransactions}
        shipmentNotices={notices ?? undefined}
      />
    </div>
  )
}
