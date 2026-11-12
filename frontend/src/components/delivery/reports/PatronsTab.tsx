/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Loader2, Star } from "lucide-react"
import { useTranslation, getCurrentLocale } from "@/i18n"

function formatDate(d: string): string {
  return new Date(d).toLocaleDateString(getCurrentLocale(), { month: 'short', day: 'numeric', year: 'numeric' })
}

interface PatronReport {
  patron_id: number
  patron_name: string
  patron_library_card: string
  enrollment_status: string
  enrolled_at: string
  total_deliveries: number
  total_items_delivered: number
  average_items_per_delivery?: number
  average_rating?: number
  next_scheduled_delivery?: string
}

interface Props {
  patronReports: PatronReport[] | undefined
  patronReportsLoading: boolean
}

export function PatronsTab({ patronReports, patronReportsLoading }: Props) {
  const { t } = useTranslation()

  return (
    <div className="space-y-4">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-lsc-border dark:border-earth-700">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Patron Service Statistics</h3>
        </div>
        {patronReportsLoading ? (
          <div className="flex items-center justify-center py-6">
            <Loader2 className="w-5 h-5 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : patronReports && patronReports.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-lsc-border dark:border-earth-700 bg-lsc-cream/50 dark:bg-earth-700/50">
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Patron</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Status</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Enrolled</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Total Deliveries</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Items Delivered</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Avg Rating</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Next Delivery</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {patronReports.map((patron) => (
                  <tr key={patron.patron_id} className="hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30">
                    <td className="px-4 py-3">
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream">{patron.patron_name}</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{patron.patron_library_card}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                        patron.enrollment_status === 'active'
                          ? 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400'
                          : 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400'
                      }`}>
                        {patron.enrollment_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">{formatDate(patron.enrolled_at)}</td>
                    <td className="px-4 py-3 text-lsc-dark/80 dark:text-lsc-cream/80">{patron.total_deliveries}</td>
                    <td className="px-4 py-3 text-lsc-dark/80 dark:text-lsc-cream/80">
                      {patron.total_items_delivered}
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 ml-1">
                        ({patron.average_items_per_delivery?.toFixed(1)} avg)
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {patron.average_rating ? (
                        <span className="flex items-center gap-1">
                          <Star className="w-3.5 h-3.5 text-status-warning-500" />
                          {patron.average_rating.toFixed(1)}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">
                      {patron.next_scheduled_delivery ? formatDate(patron.next_scheduled_delivery) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-6 text-lsc-dark/70 dark:text-lsc-cream/70">{t('homeDeliveryReports.noPatronDataAvailable')}</div>
        )}
      </div>
    </div>
  )
}
