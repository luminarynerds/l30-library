/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Renders the EDI transactions + shipment notice metadata for a single PO.
 * Pure presentational component — shared between the badge drawer and the
 * inline section embedded in EditPurchaseOrderModal.
 */
import { ArrowUpRight, ArrowDownLeft, Truck } from 'lucide-react'
import { useTranslation } from '@/i18n'
import type {
  EDITransaction,
  EDIShipmentNotice,
} from '@/api/domains/admin/edi-api'

interface EDITransactionsListProps {
  transactions: EDITransaction[]
  shipmentNotices?: EDIShipmentNotice[]
}

function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function formatShipDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export default function EDITransactionsList({
  transactions,
  shipmentNotices,
}: EDITransactionsListProps) {
  const { t } = useTranslation()

  if (transactions.length === 0) {
    return (
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        {t('acquisitionsEdi.noTransactions', 'No EDI transactions for this purchase order.')}
      </p>
    )
  }

  // Most recent first.
  const sorted = [...transactions].sort((a, b) => {
    const at = a.created_at ? new Date(a.created_at).getTime() : 0
    const bt = b.created_at ? new Date(b.created_at).getTime() : 0
    return bt - at
  })

  return (
    <div className="space-y-4">
      {shipmentNotices && shipmentNotices.length > 0 && (
        <section
          aria-labelledby="edi-shipment-heading"
          className="rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-cream/50 dark:bg-lsc-brown/50 p-4"
        >
          <h4
            id="edi-shipment-heading"
            className="flex items-center gap-2 text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-3"
          >
            <Truck aria-hidden="true" className="w-4 h-4" />
            {t('acquisitionsEdi.shipmentHeading', 'Shipment notice (DESADV)')}
          </h4>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2 text-sm">
            {shipmentNotices.map((notice) => (
              <div key={notice.id} className="contents">
                <div className="flex justify-between gap-2 sm:col-span-1">
                  <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('acquisitionsEdi.carrier', 'Carrier')}
                  </dt>
                  <dd className="text-lsc-dark dark:text-lsc-cream text-right">
                    {notice.carrier_name || '—'}
                  </dd>
                </div>
                <div className="flex justify-between gap-2 sm:col-span-1">
                  <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('acquisitionsEdi.trackingNumber', 'Tracking #')}
                  </dt>
                  <dd className="text-lsc-dark dark:text-lsc-cream font-mono text-right break-all">
                    {notice.tracking_number || '—'}
                  </dd>
                </div>
                <div className="flex justify-between gap-2 sm:col-span-1">
                  <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('acquisitionsEdi.shipDate', 'Ship date')}
                  </dt>
                  <dd className="text-lsc-dark dark:text-lsc-cream text-right">
                    {formatShipDate(notice.ship_date)}
                  </dd>
                </div>
                <div className="flex justify-between gap-2 sm:col-span-1">
                  <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('acquisitionsEdi.itemsShipped', 'Items shipped')}
                  </dt>
                  <dd className="text-lsc-dark dark:text-lsc-cream text-right">
                    {notice.total_items_shipped}
                  </dd>
                </div>
              </div>
            ))}
          </dl>
        </section>
      )}

      <section aria-labelledby="edi-transactions-heading">
        <h4
          id="edi-transactions-heading"
          className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2"
        >
          {t('acquisitionsEdi.transactionsHeading', 'EDI transactions')}
        </h4>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-lsc-cream dark:bg-lsc-brown/50">
              <tr>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold uppercase text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('acquisitionsEdi.colId', 'ID')}
                </th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold uppercase text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('acquisitionsEdi.colType', 'Type')}
                </th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold uppercase text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('acquisitionsEdi.colDirection', 'Direction')}
                </th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold uppercase text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('acquisitionsEdi.colStatus', 'Status')}
                </th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold uppercase text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('acquisitionsEdi.colCreatedAt', 'Created')}
                </th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold uppercase text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('acquisitionsEdi.colFilename', 'Filename')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
              {sorted.map((tx) => (
                <tr key={tx.id}>
                  <td className="px-3 py-2 font-mono text-lsc-dark/80 dark:text-lsc-cream/80">{tx.id}</td>
                  <td className="px-3 py-2 uppercase text-lsc-dark dark:text-lsc-cream">{tx.message_type}</td>
                  <td className="px-3 py-2 text-lsc-dark/80 dark:text-lsc-cream/80">
                    <span className="inline-flex items-center gap-1">
                      {tx.direction === 'outbound' ? (
                        <ArrowUpRight aria-hidden="true" className="w-3.5 h-3.5" />
                      ) : (
                        <ArrowDownLeft aria-hidden="true" className="w-3.5 h-3.5" />
                      )}
                      {tx.direction}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-lsc-dark dark:text-lsc-cream">{tx.status}</td>
                  <td className="px-3 py-2 text-lsc-dark/80 dark:text-lsc-cream/80 whitespace-nowrap">
                    {formatTimestamp(tx.created_at)}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-lsc-dark/70 dark:text-lsc-cream/70 break-all">
                    {tx.filename || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
